"""The Tool Gateway — document §8.1: THE single chokepoint every agent action
passes through. Checks, in order: registration → permission intersection → mode
boundary → approval binding re-validation → budget reservation → rate limit →
dry-run requirement → connector execution → audit (allow AND deny).
Agents hold no credentials; only this gateway talks to connectors (§8.2)."""
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable

from reliability import ReliabilityRuntime, default_reliability_runtime

from ..models.approval import ApprovalLevel, ApprovalRequest, ApprovalStatus
from ..models.execution import ActionRequest, ActionResult
from ..models.shared import MODE_ORDER, Money, ToolMode, now_utc
from ..policy.approval_policy import ApprovalPolicy
from ..policy.authorization_engine import AuthorizationEngine
from ..policy.hashing import digest
from ..runtime.budget import BudgetTracker
from ..storage.audit_repository import AuditRepository
from ..storage.repositories import ApprovalRepository
from .registry import EnactorToolDefinition, ToolRegistry


@dataclass
class ConnectorAccount:
    """Scoped credential held ONLY by the gateway (§8.2)."""
    name: str
    allowed_tools: frozenset[str]
    scopes: frozenset[str]
    dry_run_supported: bool = True


class RateLimiter:
    def __init__(self, calls_per_minute: int) -> None:
        self._limit = calls_per_minute
        self._windows: dict[str, list] = {}

    def allow(self, key: str, at) -> bool:
        bucket = [stamp for stamp in self._windows.get(key, []) if (at - stamp).total_seconds() < 60]
        if len(bucket) >= self._limit:
            self._windows[key] = bucket
            return False
        bucket.append(at)
        self._windows[key] = bucket
        return True


class ToolGateway:
    def __init__(self, *, registry: ToolRegistry, authorizer: AuthorizationEngine, approvals: ApprovalRepository,
                 approval_policy: ApprovalPolicy, audit: AuditRepository, budgets: BudgetTracker,
                 rate_limit_per_minute: int = 60, reliability: ReliabilityRuntime | None = None,
                 idempotency_store=None) -> None:
        self._registry = registry
        self._authorizer = authorizer
        self._approvals = approvals
        self._approval_policy = approval_policy
        self._audit = audit
        self._budgets = budgets
        self._accounts: dict[str, ConnectorAccount] = {}
        self._handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}
        self._dry_run_previews: set[str] = set()   # keys: execution|task|tool
        self._circuit_open: dict[str, str] = {}     # execution_id -> reason
        self._limiter = RateLimiter(rate_limit_per_minute)
        self.reliability = reliability or default_reliability_runtime()
        # Idempotency ledger (§8.1 rule 7): a retried external action with the same
        # key returns the recorded result and NEVER touches the connector twice.
        self._executed: dict[str, tuple[str, ActionResult | None]] = {}
        self._idempotency_store = idempotency_store
        self._idempotency_lock = RLock()

    def bind_persistence(
        self, *, approvals, approval_policy, audit, budgets, idempotency_store
    ) -> None:
        self._approvals = approvals
        self._approval_policy = approval_policy
        self._audit = audit
        self._budgets = budgets
        self._idempotency_store = idempotency_store

    def _known_execution(self, replay_key: str) -> tuple[str, ActionResult | None] | None:
        known = self._executed.get(replay_key)
        if known is None and self._idempotency_store is not None:
            known = self._idempotency_store.get(replay_key)
            if known is not None:
                self._executed[replay_key] = known
        return known

    # -- wiring -------------------------------------------------------------
    def register_connector(self, account: ConnectorAccount, tool_names: tuple[str, ...],
                           handler: Callable[[str, dict[str, Any]], dict[str, Any]]) -> None:
        for name in tool_names:
            self._registry.require(name)
        self._accounts[account.name] = account
        for name in tool_names:
            self._handlers[name] = lambda arguments, tool=name: handler(tool, arguments)

    def open_circuit(self, execution_id: str, reason: str) -> None:
        self._circuit_open[execution_id] = reason

    def close_circuit(self, execution_id: str) -> None:
        self._circuit_open.pop(execution_id, None)

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    # -- core ---------------------------------------------------------------
    def execute(self, context: "GatewayContext", request: ActionRequest) -> ActionResult:
        try:
            self.reliability.ensure_work_allowed("Enactor tool execution")
        except PermissionError as error:
            return self._deny(context, request, "system_pause", str(error))
        tool_name = request.tool
        definition = self._registry.get(tool_name)
        if definition is None:
            return self._deny(context, request, "unregistered_tool", f"Tool {tool_name} is not registered.")
        if context.execution_id in self._circuit_open:
            return self._deny(context, request, "circuit_breaker",
                              f"Circuit breaker open: {self._circuit_open[context.execution_id]}")

        permission = self._authorizer.authorize(agent_role=context.agent_role,
                                                task_allowed_tools=context.allowed_tools, tool=definition)
        if not permission.allowed:
            return self._deny(context, request, "permission", permission.reason)

        if MODE_ORDER[definition.mode] > MODE_ORDER[context.requested_mode]:
            return self._deny(context, request, "mode_boundary",
                              f"Task mode {context.requested_mode.value} cannot perform {definition.mode.value} via {tool_name}.")

        if definition.mode is ToolMode.EXTERNAL_ACTION and not request.idempotency_key:
            return self._deny(context, request, "idempotency", "External actions require an idempotency key.")

        target = str(request.arguments.get(definition.target_argument, ""))
        if definition.mode is ToolMode.EXTERNAL_ACTION and not target:
            return self._deny(context, request, "target_missing", "External actions must declare an explicit target.")

        # Idempotent replay (§8.1 rule 7): same execution+task+tool+key already ran →
        # return the recorded result without re-invoking the connector or re-spending.
        replay_key: str | None = None
        request_hash: str | None = None
        if definition.mode is ToolMode.EXTERNAL_ACTION and request.idempotency_key:
            replay_key = f"{context.execution_id}|{context.task_id}|{tool_name}|{request.idempotency_key}"
            request_hash = digest({
                "tool": tool_name,
                "arguments": request.arguments,
                "approval_id": context.approval_id,
                "amount": context.amount,
                "requested_mode": context.requested_mode,
            })
            with self._idempotency_lock:
                prior = self._known_execution(replay_key)
            if prior is not None:
                if prior[0] != request_hash:
                    return self._deny(
                        context, request, "idempotency_conflict",
                        "Idempotency key was previously used with a different action binding.",
                    )
                if prior[1] is None:
                    return self._deny(
                        context, request, "idempotency_in_progress",
                        "Action outcome is unresolved; reconcile it before retrying.",
                    )
                return self._replay(context, request, request.idempotency_key, prior[1])

        # Dry-run-before-irreversible rule (§8.1 rule 9): external irreversible actions
        # must have a recorded dry-run preview for the same binding first.
        preview_key = f"{context.execution_id}|{context.task_id}|{tool_name}"
        wants_dry_run = bool(request.arguments.get("dryRun"))
        if definition.mode is ToolMode.EXTERNAL_ACTION and not definition.reversible:
            if wants_dry_run:
                preview = self._invoke(context, request, definition, dry_run=True)
                if preview.status == "success":
                    self._dry_run_previews.add(preview_key)
                return preview
            if preview_key not in self._dry_run_previews:
                return self._deny(context, request, "dry_run_required",
                                  "Irreversible external action requires a prior dry-run preview of the same binding.")

        # Approval binding re-validation (§8.1 rules 1–2)
        approval: ApprovalRequest | None = None
        required = definition.approval_level
        if required is not ApprovalLevel.A0_NONE:
            escalated = self._approval_policy.required_level(
                _Gate(definition.approval_level), context_flags=context.context_flags)
            required = escalated
        if required is not ApprovalLevel.A0_NONE:
            if not context.approval_id:
                return self._deny(context, request, "approval_missing",
                                  f"{tool_name} requires {required.value} approval bound to this exact action.")
            approval = self._approvals.maybe(context.approval_id)
            if approval is None:
                return self._deny(context, request, "approval_unknown", f"Unknown approval {context.approval_id}.")
            valid, reason = self._approval_policy.validate_binding(
                approval, task=_StubTask(context.execution_id, context.task_id), agent_id=context.agent_id,
                tool=tool_name, target=target, exact_arguments=request.arguments, amount=context.amount,
                approver_level=None)
            if not valid:
                return self._deny(context, request, "approval_invalid", reason)
            if approval.status is ApprovalStatus.CONSUMED:
                return self._deny(context, request, "approval_consumed", "Approvals are single-use.")

        # Budget reservation (§8.4)
        cost = float(definition.cost_estimate(request.arguments))
        try:
            ledger = self._budgets.ledger(context.execution_id)
        except KeyError:
            return self._deny(context, request, "budget", f"No budget ledger open for {context.execution_id}.")
        allowed, reason = ledger.check(definition.budget_type, cost,
                                       currency=context.amount.currency if context.amount else None)
        if not allowed:
            ledger.exhausted = True
            return self._deny(context, request, "budget", reason)
        if not self._limiter.allow(f"{context.execution_id}:{tool_name}", now_utc()):
            return self._deny(context, request, "rate_limit", f"Rate limit exceeded for {tool_name}.")

        if replay_key is not None and request_hash is not None:
            with self._idempotency_lock:
                prior = self._known_execution(replay_key)
                if prior is not None:
                    if prior[0] != request_hash:
                        return self._deny(
                            context, request, "idempotency_conflict",
                            "Idempotency key was previously used with a different action binding.",
                        )
                    if prior[1] is None:
                        return self._deny(
                            context, request, "idempotency_in_progress",
                            "Action outcome is unresolved; reconcile it before retrying.",
                        )
                    return self._replay(context, request, request.idempotency_key, prior[1])
                if self._idempotency_store is not None:
                    prior = self._idempotency_store.claim(replay_key, request_hash)
                    if prior is not None:
                        self._executed[replay_key] = prior
                        if prior[0] != request_hash:
                            return self._deny(
                                context, request, "idempotency_conflict",
                                "Idempotency key was previously used with a different action binding.",
                            )
                        if prior[1] is None:
                            return self._deny(
                                context, request, "idempotency_in_progress",
                                "Action outcome is unresolved; reconcile it before retrying.",
                            )
                        return self._replay(
                            context, request, request.idempotency_key, prior[1]
                        )
                self._executed[replay_key] = (request_hash, None)
        ledger.reserve(definition.budget_type, cost)
        try:
            result = self._invoke(context, request, definition, dry_run=wants_dry_run)
            if result.status == "success":
                ledger.commit(definition.budget_type, cost)
                if not wants_dry_run:
                    if replay_key is not None and request_hash is not None:
                        with self._idempotency_lock:
                            self._executed[replay_key] = (request_hash, result)
                            if self._idempotency_store is not None:
                                self._idempotency_store.complete(
                                    replay_key, request_hash, result
                                )
                    self._dry_run_previews.discard(preview_key)
                    if approval is not None and definition.mode is ToolMode.EXTERNAL_ACTION:
                        self._approval_policy.consume(approval)
            else:
                ledger.rollback(definition.budget_type, cost)
                if result.status == "failed":
                    self.open_circuit(context.execution_id, f"connector failure on {tool_name}: {result.error}")
            return result
        except Exception as error:  # connector crash: roll back and trip circuit breaker
            ledger.rollback(definition.budget_type, cost)
            self.open_circuit(context.execution_id, f"connector exception on {tool_name}")
            return self._deny(context, request, "connector_exception", str(error))

    def _replay(
        self,
        context: "GatewayContext",
        request: ActionRequest,
        idempotency_key: str,
        prior: ActionResult,
    ) -> ActionResult:
        self._audit.append(
            event_type="gateway_replay",
            business_id=context.business_id,
            execution_id=context.execution_id,
            task_id=context.task_id,
            agent_id=context.agent_id,
            tool=request.tool,
            approval_id=context.approval_id,
            external_operation_id=prior.external_operation_id,
            detail={"idempotencyKey": idempotency_key, "deduplicated": True},
        )
        return ActionResult(
            action_id=request.action_id,
            status=prior.status,
            output={**prior.output, "deduplicated": True},
            error=prior.error,
            external_operation_id=prior.external_operation_id,
        )

    def _invoke(self, context: "GatewayContext", request: ActionRequest, definition: EnactorToolDefinition,
                dry_run: bool) -> ActionResult:
        account = next((acc for acc in self._accounts.values() if request.tool in acc.allowed_tools), None)
        if account is None:
            return self._deny(context, request, "no_account", f"No connector account serves {request.tool}.")
        handler = self._handlers[request.tool]
        payload = dict(request.arguments)
        payload["__dryRun__"] = dry_run
        payload["__idempotencyKey__"] = None if dry_run else request.idempotency_key
        output = handler(payload)
        status = str(output.get("status", "success"))
        operation_id = output.get("externalOperationId")
        self._audit.append(event_type="gateway_call", business_id=context.business_id, execution_id=context.execution_id,
                           task_id=context.task_id, agent_id=context.agent_id, tool=request.tool,
                           connector_account=account.name, approval_id=context.approval_id,
                           external_operation_id=operation_id,
                           detail={"actionId": request.action_id, "dryRun": dry_run, "status": status,
                                   "planHash": context.plan_hash,
                                   "output": {k: v for k, v in output.items() if k != "status"},
                                   "mode": definition.mode.value, "budgetType": definition.budget_type,
                                   "cost": float(definition.cost_estimate(request.arguments))})
        final = status if status in {"success", "failed", "blocked"} else "success"
        return ActionResult(action_id=request.action_id, status=final, output=output,
                            error=output.get("error"), external_operation_id=operation_id)

    def _deny(self, context: "GatewayContext", request: ActionRequest, denial_type: str, reason: str) -> ActionResult:
        """Denials are audited too (§8.5); they never touch connectors."""
        self._audit.append(event_type="denial", business_id=context.business_id, execution_id=context.execution_id,
                           task_id=context.task_id, agent_id=context.agent_id, tool=request.tool,
                           approval_id=context.approval_id,
                           detail={"actionId": request.action_id, "denialType": denial_type, "reason": reason,
                                   "planHash": context.plan_hash})
        return ActionResult(action_id=request.action_id, status="denied", error=f"{denial_type}: {reason}")


@dataclass
class GatewayContext:
    business_id: str
    execution_id: str
    task_id: str
    agent_role: str
    agent_id: str
    allowed_tools: tuple[str, ...]
    plan_hash: str
    requested_mode: ToolMode
    approval_id: str | None = None
    amount: Money | None = None
    context_flags: tuple[str, ...] = ()


class _Gate:
    def __init__(self, level: ApprovalLevel) -> None:
        self.required_level = level
        self.gate_id = "tool-floor"
        self.description = "gateway-derived gate"


class _StubTask:
    def __init__(self, execution_id: str, task_id: str) -> None:
        self.execution_id = execution_id
        self.task_id = task_id
