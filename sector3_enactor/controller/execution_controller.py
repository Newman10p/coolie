"""Execution Controller — document §6.2, §10.

Owns the full lifecycle: receive → validate → plan → prepare → execute tasks in
dependency order → monitor stop conditions → handle approvals/denials/retries →
quality gate → completion handoff + outcome report. It is the only component that
changes execution state; agents can never move the state machine themselves.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4

from reliability import ReliabilityRuntime, default_reliability_runtime

from ..agents.analytics.metric_collector import MetricCollectorAgent
from ..agents.builders.web_developer import WebDeveloperAgent
from ..agents.commerce.catalog_manager import CatalogManagerAgent
from ..agents.commerce.returns_processor import ReturnsProcessorAgent
from ..agents.designers.graphic_designer import GraphicDesignerAgent
from ..agents.marketers.campaign_manager import CampaignManagerAgent
from ..agents.messengers.supply_communications import SupplyCommunicationsAgent
from ..agents.messengers.support_triage import SupportTriageAgent
from ..agents.qa.quality_gate_agent import QualityGateAgent
from ..agents.seo.seo_specialist import SeoSpecialistAgent
from ..config.loader import SectorConfig
from ..evaluation.quality_gate import QualityGate
from ..handoffs.inbound import validate_request
from ..handoffs.outbound import completion_payload, outcome_payload
from ..models.approval import ApprovalLevel
from ..models.execution import Escalation, ExecutionRequest, ExecutionResult, ExecutionStatus, TaskLifecycleStatus
from ..models.shared import RiskSeverity, now_utc
from ..models.task import EnactorTask, ExecutionPlan
from ..policy.approval_policy import ApprovalPolicy
from ..policy.authorization_engine import AuthorizationEngine
from ..policy.hashing import digest
from ..runtime.artifact_store import ArtifactStore
from ..runtime.budget import BudgetTracker
from ..runtime.task_graph import CycleError, topological_order
from ..storage.audit_repository import AuditRepository
from ..storage.repositories import Storefront
from ..tools.gateway import ConnectorAccount, GatewayContext, ToolGateway
from ..tools.registry import ToolRegistry
from .state_machine import ExecutionStateMachine

ROLE_TO_AGENT = {
    "messengers.support_triage": SupportTriageAgent,
    "messengers.supply_communications": SupplyCommunicationsAgent,
    "designers.graphic_designer": GraphicDesignerAgent,
    "builders.web_developer": WebDeveloperAgent,
    "marketers.campaign_manager": CampaignManagerAgent,
    "seo.seo_specialist": SeoSpecialistAgent,
    "commerce.catalog_manager": CatalogManagerAgent,
    "commerce.returns_processor": ReturnsProcessorAgent,
    "qa.quality_gate": QualityGateAgent,
    "analytics.metric_collector": MetricCollectorAgent,
}

LEVEL_RANK = {"A0": 0, "A1": 1, "A2": 2, "A3": 3, "A4": 4}


@dataclass
class RunOutcome:
    result: ExecutionResult
    audit_events: int
    chain_valid: bool


def _plan_payload(plan: ExecutionPlan) -> dict[str, Any]:
    return {"executionId": plan.execution_id, "planId": plan.plan_id,
            "tasks": [{"id": t.task_id, "role": t.agent_role, "tool": t.tool, "mode": t.mode.value,
                       "deps": list(t.dependencies), "allowedTools": list(t.allowed_tools),
                       "gate": None if t.approval_gate is None else
                       {"id": t.approval_gate.gate_id, "level": t.approval_gate.required_level.value}}
                      for t in plan.tasks]}


class ExecutionController:
    def __init__(self, *, config: SectorConfig, registry: ToolRegistry, store: Storefront | None = None,
                 artifacts: ArtifactStore | None = None, audit: AuditRepository | None = None,
                 gateway: ToolGateway | None = None, reliability: ReliabilityRuntime | None = None) -> None:
        self.config = config
        self.registry = registry
        self.store = store or Storefront()
        self.artifacts = artifacts or ArtifactStore()
        self.audit = audit or AuditRepository()
        self.budgets = BudgetTracker(config.budgets["warning_threshold_percent"])
        self.authorizer = AuthorizationEngine(config, registry)
        self.approval_policy = ApprovalPolicy(config, self.store.approvals, self.audit)
        self.state_machine = ExecutionStateMachine(self.audit)
        self.quality_gate = QualityGate()
        if reliability is not None and gateway is not None and gateway.reliability is not reliability:
            raise ValueError("ExecutionController and ToolGateway must share one ReliabilityRuntime.")
        self.reliability = reliability or (
            gateway.reliability if gateway is not None else default_reliability_runtime()
        )
        self.gateway = gateway or ToolGateway(registry=registry, authorizer=self.authorizer,
                                              approvals=self.store.approvals, approval_policy=self.approval_policy,
                                              audit=self.audit, budgets=self.budgets,
                                              rate_limit_per_minute=config.rate_limits.get("default_calls_per_minute", 60),
                                              reliability=self.reliability)
        self._plan_registry: dict[str, ExecutionPlan] = {}   # plan_hash → immutable compiled plan (§8.1 rule 3)
        self.research_sink: list[dict[str, Any]] = []       # fake Research Room peer queue
        self.orchestrator_sink: list[dict[str, Any]] = []   # fake Orchestrator queue

    # -- wiring ----------------------------------------------------------------
    def attach_connector(self, account_name: str, tool_names: tuple[str, ...],
                         handler: Callable[[str, dict], dict]) -> None:
        account = ConnectorAccount(name=account_name, allowed_tools=frozenset(tool_names),
                                   scopes=frozenset({"read", "write"}))
        self.gateway.register_connector(account, tool_names, handler)

    # -- planning (§10 step 2–3) -------------------------------------------------
    def compile_plan(self, request: ExecutionRequest, tasks: tuple[EnactorTask, ...]) -> ExecutionPlan:
        for task in tasks:
            if task.approval_gate is not None and task.tool is not None:
                floor = self.registry.require(task.tool).approval_level
                if LEVEL_RANK[floor.value] > LEVEL_RANK[task.approval_gate.required_level.value]:
                    raise ValueError(f"Task {task.task_id} gate {task.approval_gate.required_level.value} "
                                     f"is below the tool floor {floor.value}.")
        probe = ExecutionPlan(execution_id=request.execution_id, plan_id=request.plan_id,
                              objective=request.objective, tasks=tasks)
        try:
            topological_order(probe)
        except CycleError as error:
            raise ValueError(str(error)) from error
        plan_hash = digest(_plan_payload(probe))
        plan = ExecutionPlan(execution_id=request.execution_id, plan_id=request.plan_id, objective=request.objective,
                             tasks=tasks, constraints=request.constraints, audience=request.audience,
                             approved_claims=request.approved_claims, required_assets=request.required_assets,
                             success_metric_ids=tuple(m.metric_id for m in request.success_metrics),
                             stop_condition_ids=tuple(c.condition_id for c in request.stop_conditions),
                             budget_summary={"budget": None if request.budget is None else request.budget.amount},
                             plan_hash=plan_hash)
        self._plan_registry[plan.plan_hash] = plan
        return plan

    def _verify_plan_integrity(self, plan: ExecutionPlan) -> None:
        """§8.1 rule 3: a tampered plan (removed gate/task) no longer hashes to the
        registered version → refuse to run it."""
        if digest(_plan_payload(plan)) != plan.plan_hash or self._plan_registry.get(plan.plan_hash) is not plan:
            raise PermissionError("Plan hash does not match any registered compiled plan; execution refused.")

    def _agent_for(self, role: str, execution_id: str):
        cls = ROLE_TO_AGENT.get(role)
        if cls is None: raise ValueError(f"No agent class registered for role {role}.")
        return cls(agent_id=f"{role}@{execution_id}", role=role, division=role.split(".", 1)[0],
                   gateway=self.gateway, registry=self.registry, approval_policy=self.approval_policy,
                   artifacts=self.artifacts, audit=self.audit, quality_gate=self.quality_gate)

    # -- main run loop (§10 steps 1–11) ------------------------------------------
    def submit(self, request: ExecutionRequest, plan: ExecutionPlan, context: dict[str, Any]) -> RunOutcome:
        self.reliability.ensure_work_allowed("Enactor execution")
        self.store.executions.put(request)
        self.state_machine.transition(request, ExecutionStatus.VALIDATING, event="received")
        validation = validate_request(request)
        request.risk_flags = validation.risk_flags
        if not validation.valid:
            self.state_machine.transition(request, ExecutionStatus.REJECTED, event="validation_failed",
                                          reason="; ".join(validation.errors))
            result = ExecutionResult(execution_id=request.execution_id, status=ExecutionStatus.REJECTED,
                                     summary=f"Rejected: {'; '.join(validation.errors)}", completed_at=now_utc())
            self.orchestrator_sink.append(completion_payload(result))
            return RunOutcome(result, len(self.audit.all_events()), self.audit.verify_chain())
        self.state_machine.transition(request, ExecutionStatus.PLANNING, event="validated")
        self._verify_plan_integrity(plan)
        self.budgets.open_ledger(request.execution_id, self.config.budgets)

        state = {"business_id": request.business_id, "plan_hash": plan.plan_hash, "request": request,
                 "store": self.store, "context": context,
                 "restricted_intents": tuple(self.config.communication.restricted_intents)}
        escalations: list[Escalation] = []
        artifact_refs: dict[str, Any] = {}
        blocked_by_gate = False
        failed = False
        awaiting = False

        self.state_machine.transition(request, ExecutionStatus.PREPARING_RESOURCES, event="planning_complete")
        self.state_machine.transition(request, ExecutionStatus.EXECUTING, event="resources_ready")
        ordered = topological_order(plan)
        done: set[str] = set()
        for task in ordered:
            if any(dep not in done for dep in task.dependencies):
                task.status = TaskLifecycleStatus.BLOCKED
                task.blocked_reason = "upstream dependency did not complete"
                blocked_by_gate = True
                continue
            agent = self._agent_for(task.agent_role, request.execution_id)
            attempts = 0
            while True:
                task.status = TaskLifecycleStatus.RUNNING
                task.attempts += 1
                attempts += 1
                status, message, outputs = agent.run(task, state)
                if status.value == "failed" and task.attempts <= task.maximum_retries:
                    continue
                break
            for key in ("asset_id", "campaign_id", "artifact_key"):
                value = outputs.get(key)
                if value:
                    for k in self.artifacts.keys():
                        if str(value) in k: artifact_refs[k] = self.artifacts.put(k, self.artifacts.get(k))
            if status.value == "awaiting_approval":
                task.status = TaskLifecycleStatus.WAITING_HUMAN
                escalations.append(Escalation(escalation_id=f"ESC-{uuid4().hex[:8]}", execution_id=request.execution_id,
                                              reason=message, severity=RiskSeverity.MEDIUM, routed_to="human",
                                              approval_request_id=outputs.get("approval_id")))
                awaiting = True
                continue
            if status.value == "blocked":
                task.status = TaskLifecycleStatus.BLOCKED
                task.blocked_reason = message
                blocked_by_gate = True
                escalations.append(Escalation(escalation_id=f"ESC-{uuid4().hex[:8]}", execution_id=request.execution_id,
                                              reason=message, severity=RiskSeverity.HIGH, routed_to="human"))
                continue
            if status.value == "failed":
                task.status = TaskLifecycleStatus.FAILED
                task.failure_reason = message
                failed = True
                self.gateway.open_circuit(request.execution_id, f"task {task.task_id} failed: {message}")
                continue
            task.status = TaskLifecycleStatus.COMPLETED
            done.add(task.task_id)

        self.state_machine.transition(request, ExecutionStatus.MONITORING, event="tasks_finished")

        if failed:
            target = ExecutionStatus.FAILED
        elif blocked_by_gate or awaiting:
            target = ExecutionStatus.AWAITING_APPROVAL
        else:
            target = ExecutionStatus.COMPLETED
        self.state_machine.transition(request, target, event="monitoring_decision")

        metrics = tuple(self.store.metrics.for_execution(request.execution_id))
        outcome_reports = tuple(r for r in self.store.outcomes.all() if r.execution_id == request.execution_id)
        for report in outcome_reports:
            payload = outcome_payload(report)
            self.research_sink.append(payload)
            self.orchestrator_sink.append(payload)
        result = ExecutionResult(execution_id=request.execution_id, status=target,
                                 artifacts=tuple(artifact_refs.values()), metrics=metrics,
                                 escalations=tuple(escalations),
                                 summary=f"Executed {len(ordered)} tasks; awaiting={awaiting}; blocked={blocked_by_gate}; failed={failed}",
                                 completed_at=now_utc() if target in {ExecutionStatus.COMPLETED,
                                                                      ExecutionStatus.PARTIALLY_COMPLETED,
                                                                      ExecutionStatus.FAILED} else None)
        self.orchestrator_sink.append(completion_payload(result))
        return RunOutcome(result, len(self.audit.all_events()), self.audit.verify_chain())

    # -- approval decisions feed back into runs (§10 step 4) ----------------------
    def approve(self, approval_id: str, *, decided_by: str, level: ApprovalLevel = ApprovalLevel.A4_STRICT):
        return self.approval_policy.decide(approval_id, approve=True, decided_by=decided_by, approver_level=level)

    def deny(self, approval_id: str, *, decided_by: str, level: ApprovalLevel = ApprovalLevel.A4_STRICT):
        return self.approval_policy.decide(approval_id, approve=False, decided_by=decided_by, approver_level=level)

    def resume(self, request: ExecutionRequest, plan: ExecutionPlan, context: dict[str, Any]) -> RunOutcome:
        """Re-run after approvals land: waiting/blocked tasks get another attempt (§10 step 4)."""
        self.reliability.ensure_work_allowed("Enactor execution resume")
        if request.status is ExecutionStatus.AWAITING_APPROVAL:
            self.state_machine.transition(request, ExecutionStatus.EXECUTING, event="approvals_updated")
        for task in plan.tasks:
            if task.status in {TaskLifecycleStatus.WAITING_HUMAN, TaskLifecycleStatus.BLOCKED}:
                task.status = TaskLifecycleStatus.PENDING
        # A resumed run may act again → the execution-level circuit breaker must be
        # explicitly closed by the operator (no silent reset; §8.1 rule 7).
        state = {"business_id": request.business_id, "plan_hash": plan.plan_hash, "request": request,
                 "store": self.store, "context": context,
                 "restricted_intents": tuple(self.config.communication.restricted_intents)}
        results: list[tuple[str, str, dict]] = []
        escalations: list[Escalation] = []
        for task in plan.tasks:
            if task.status is not TaskLifecycleStatus.PENDING:
                continue
            if any(dep not in {t.task_id for t in plan.tasks if t.status is TaskLifecycleStatus.COMPLETED}
                   for dep in task.dependencies):
                task.status = TaskLifecycleStatus.BLOCKED
                task.blocked_reason = "upstream dependency did not complete"
                continue
            agent = self._agent_for(task.agent_role, request.execution_id)
            task.attempts += 1
            status, message, outputs = agent.run(task, state)
            if status.value in {"success", "partial"}:
                task.status = TaskLifecycleStatus.COMPLETED
            elif status.value == "awaiting_approval":
                task.status = TaskLifecycleStatus.WAITING_HUMAN
                escalations.append(Escalation(escalation_id=f"ESC-{uuid4().hex[:8]}", execution_id=request.execution_id,
                                              reason=message, severity=RiskSeverity.MEDIUM, routed_to="human",
                                              approval_request_id=outputs.get("approval_id")))
            elif status.value == "blocked":
                task.status = TaskLifecycleStatus.BLOCKED
                task.blocked_reason = message
                escalations.append(Escalation(escalation_id=f"ESC-{uuid4().hex[:8]}", execution_id=request.execution_id,
                                              reason=message, severity=RiskSeverity.HIGH, routed_to="human"))
            else:
                task.status = TaskLifecycleStatus.FAILED
                task.failure_reason = message
                self.gateway.open_circuit(request.execution_id, f"task {task.task_id} failed on resume: {message}")
            results.append((task.task_id, message, outputs))
        still_waiting = any(t.status is TaskLifecycleStatus.WAITING_HUMAN for t in plan.tasks)
        any_blocked = any(t.status is TaskLifecycleStatus.BLOCKED for t in plan.tasks)
        any_failed = any(t.status is TaskLifecycleStatus.FAILED for t in plan.tasks)
        any_completed = any(t.status is TaskLifecycleStatus.COMPLETED for t in plan.tasks)
        if any_failed:
            target_status = ExecutionStatus.FAILED
        elif still_waiting or any_blocked:
            target_status = ExecutionStatus.AWAITING_APPROVAL
        elif any_completed:
            target_status = ExecutionStatus.COMPLETED
        else:
            target_status = ExecutionStatus.FAILED
        self.state_machine.transition(request, target_status, event="resume_decision")
        for report in tuple(r for r in self.store.outcomes.all() if r.execution_id == request.execution_id):
            payload = outcome_payload(report)
            if payload not in self.research_sink: self.research_sink.append(payload)
        result = ExecutionResult(execution_id=request.execution_id, status=target_status,
                                 escalations=tuple(escalations),
                                 summary=f"Resumed run: {len(results)} tasks re-attempted.",
                                 completed_at=(now_utc() if target_status in {ExecutionStatus.COMPLETED,
                                                                               ExecutionStatus.FAILED} else None))
        self.orchestrator_sink.append(completion_payload(result))
        return RunOutcome(result, len(self.audit.all_events()), self.audit.verify_chain())

    def close_execution_circuit(self, execution_id: str) -> None:
        """Operator action: reset the breaker once the underlying problem is fixed."""
        self.gateway.close_circuit(execution_id)
