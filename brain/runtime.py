"""Brain inference orchestration with isolated credentials and per-request policy checks."""

from __future__ import annotations

from dataclasses import asdict
from copy import deepcopy
import json
from threading import RLock
import time
from typing import Any
import secrets

from research_room.models import Money
from reliability import ReliabilityRuntime, default_reliability_runtime

from .budget import BudgetExceeded, BudgetManager
from .delegation import DelegationManager
from .events import EventBus
from .identity import AgentRegistry, SessionManager
from .memory import ContextBuilder, MemoryStore
from .models import (
    AgentDefinition,
    AgentSession,
    BrainEvent,
    BrainOperation,
    Delegation,
    DelegationRequest,
    InferenceAudit,
    InferenceRequest,
    InferenceResponse,
    MemoryRecord,
    ModelProfile,
    ProviderRequest,
    ProviderResponse,
    UsageRecord,
)
from .policy import authorize_inference, canonical_json, content_hash, validate_output, validate_schema_definition
from .provider import ProviderAdapter, ProviderError, ScopedCredential, SecretAccessError, SecretManager
from .routing import ModelRegistry


class SecretLeakError(ProviderError):
    pass


class SecretInRequestError(PermissionError):
    pass


class ProviderOutputError(ProviderError):
    pass


class EmergencyPause:
    def __init__(self) -> None:
        self._paused = False
        self._reason: str | None = None
        self._lock = RLock()

    def pause(self, reason: str) -> None:
        if not reason.strip():
            raise ValueError("Emergency-pause reason is required.")
        with self._lock:
            self._paused = True
            self._reason = reason

    def resume(self, *, authority: str) -> None:
        if not authority.strip():
            raise PermissionError("Explicit restart authority is required.")
        with self._lock:
            self._paused = False
            self._reason = None

    def check(self) -> None:
        with self._lock:
            if self._paused:
                raise PermissionError("Brain inference is emergency-paused.")

    @property
    def reason(self) -> str | None:
        with self._lock:
            return self._reason


class CircuitBreaker:
    def __init__(self, *, failure_threshold: int = 3, reset_after_seconds: float = 30) -> None:
        if isinstance(failure_threshold, bool) or not isinstance(failure_threshold, int) or failure_threshold <= 0:
            raise ValueError("failure_threshold must be a positive integer.")
        if isinstance(reset_after_seconds, bool) or not isinstance(reset_after_seconds, (int, float)) or reset_after_seconds <= 0:
            raise ValueError("reset_after_seconds must be positive.")
        self._threshold = failure_threshold
        self._reset_after = reset_after_seconds
        self._failures = 0
        self._opened_at: float | None = None

    def can_attempt(self) -> bool:
        return self._opened_at is None or time.monotonic() - self._opened_at >= self._reset_after

    def success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            self._opened_at = time.monotonic()

    @property
    def state(self) -> str:
        if self._opened_at is None:
            return "healthy"
        return "degraded" if self.can_attempt() else "open"


def _estimate_input_tokens(value: Any, context: tuple[dict[str, Any], ...]) -> int:
    serialized = json.dumps({"input": value, "context": context}, ensure_ascii=False, default=str, allow_nan=False)
    return max(1, (len(serialized) + 3) // 4)


class BrainService:
    def __init__(
        self,
        *,
        agents: AgentRegistry,
        sessions: SessionManager,
        models: ModelRegistry,
        providers: dict[str, ProviderAdapter],
        secrets: SecretManager,
        memory: MemoryStore | None = None,
        schemas: dict[str, dict[str, Any]] | None = None,
        budgets: BudgetManager | None = None,
        events: EventBus | None = None,
        circuit_breaker_factory: Any = CircuitBreaker,
        failure_threshold: int = 3,
        circuit_reset_seconds: float = 30,
        delegations: DelegationManager | None = None,
        reliability: ReliabilityRuntime | None = None,
        persistence=None,
    ) -> None:
        self._agents = agents
        self._sessions = sessions
        self._models = models
        self._providers = dict(providers)
        self._secrets = secrets
        self._memory = memory or MemoryStore()
        self._context = ContextBuilder(self._memory)
        self._schemas = default_schema_registry() if schemas is None else deepcopy(schemas)
        for schema in self._schemas.values():
            validate_schema_definition(schema)
        self._budgets = budgets or BudgetManager()
        self._events = events or EventBus()
        self._delegations = delegations or DelegationManager()
        self._delegation_reservations: dict[str, str] = {}
        self._pause_controller = EmergencyPause()
        self.reliability = reliability or default_reliability_runtime()
        self._audits: list[InferenceAudit] = []
        self._usage: list[UsageRecord] = []
        self._circuits = {
            provider_id: circuit_breaker_factory(
                failure_threshold=failure_threshold, reset_after_seconds=circuit_reset_seconds,
            )
            for provider_id in self._providers
        }
        self._lock = RLock()
        self._request_ids: set[str] = set()
        self._persistence = persistence
        if persistence is not None:
            self._audits.extend(persistence.events("brain_audits", InferenceAudit))
            self._usage.extend(persistence.events("brain_usage", UsageRecord))
            self._request_ids.update(persistence.record_ids("brain_request_ids"))
            self._delegation_reservations.update(
                {
                    delegation_id: persistence.get_payload(
                        "brain_delegation_reservations", delegation_id
                    )["reservation_id"]
                    for delegation_id in persistence.record_ids(
                        "brain_delegation_reservations"
                    )
                }
            )

    def agent_definition(self, agent_id: str) -> AgentDefinition:
        return self._agents.get(agent_id)

    def bind_persistence(self, persistence, *, budgets) -> None:
        """Bind durable state before this Brain instance begins processing work."""
        if (
            self._audits
            or self._usage
            or self._request_ids
            or self._memory._records
            or self._events.events()
            or self._delegations._records
            or self._budgets._reservations
            or self._budgets._reserved
            or self._budgets._spent
        ):
            raise RuntimeError(
                "Supabase persistence must be bound before Brain has stored runtime state."
            )
        self._persistence = persistence
        self._memory = MemoryStore(persistence)
        self._context = ContextBuilder(self._memory)
        self._events = EventBus(persistence)
        self._budgets = budgets
        self._delegations = DelegationManager(
            maximum_children=self._delegations._maximum_children,
            persistence=persistence,
        )
        self._audits = list(persistence.events("brain_audits", InferenceAudit))
        self._usage = list(persistence.events("brain_usage", UsageRecord))
        self._request_ids = set(persistence.record_ids("brain_request_ids"))
        self._delegation_reservations = {
            delegation_id: persistence.get_payload(
                "brain_delegation_reservations", delegation_id
            )["reservation_id"]
            for delegation_id in persistence.record_ids(
                "brain_delegation_reservations"
            )
        }

    def event_log(self) -> tuple[BrainEvent, ...]:
        return self._events.events()

    def emergency_stop(self, reason: str, *, authority: str) -> tuple[AgentSession, ...]:
        if not isinstance(authority, str) or not authority.strip():
            raise PermissionError("Emergency-pause authority is required.")
        self.reliability.emergency_pause(reason, authority=authority)
        self._pause_controller.pause(reason)
        revoked = self._sessions.revoke_all()
        self._events.publish(
            "brain.emergency_paused", source="brain",
            payload={"revoked_sessions": len(revoked)},
            correlation_id=secrets.token_urlsafe(18),
        )
        return revoked

    def restart(self, *, authority: str) -> None:
        if self.reliability.failsafe.paused:
            self.reliability.resume(authority=authority)
        self._pause_controller.resume(authority=authority)
        self._events.publish(
            "brain.emergency_restarted", source="brain", payload={},
            correlation_id=secrets.token_urlsafe(18),
        )

    def set_agent_status(self, agent_id: str, status: str, *, authority: str) -> AgentDefinition:
        if not authority.strip():
            raise PermissionError("Agent status-change authority is required.")
        agent = self._agents.set_status(agent_id, status)
        revoked = self._sessions.revoke_agent(agent_id) if status != "active" else ()
        self._events.publish(
            f"brain.agent.{status}", source="brain",
            payload={"agent_id": agent_id, "revoked_sessions": len(revoked)},
            correlation_id=agent_id,
        )
        return agent

    def create_session(
        self,
        agent_id: str,
        *,
        task_id: str,
        duration_seconds: int = 300,
        operations: frozenset[BrainOperation] | None = None,
        memory_namespaces: frozenset[str] | None = None,
        token_limit: int | None = None,
        cost_limit: Money | None = None,
    ):
        self.reliability.ensure_work_allowed("Brain session creation")
        self._pause_controller.check()
        agent = self._agents.get(agent_id)
        grant = self._sessions.create(
            agent, task_id=task_id, duration_seconds=duration_seconds, operations=operations,
            memory_namespaces=memory_namespaces, token_limit=token_limit, cost_limit=cost_limit,
        )
        try:
            self._pause_controller.check()
        except PermissionError:
            self._sessions.revoke(grant.session.session_id)
            raise
        self._events.publish(
            "brain.session.created", source="brain", payload={"session_id": grant.session.session_id, "agent_id": agent_id},
            correlation_id=grant.session.session_id,
        )
        return grant

    def revoke_session(self, session_id: str, *, authority: str):
        if not authority.strip():
            raise PermissionError("Session revocation authority is required.")
        session = self._sessions.revoke(session_id)
        self._events.publish(
            "brain.session.revoked", source="brain", payload={"session_id": session_id, "agent_id": session.agent_id},
            correlation_id=session_id,
        )
        return session

    def request_delegation(
        self,
        request: DelegationRequest,
        *,
        session_id: str,
        session_token: str,
        parent_depth: int = 0,
    ) -> Delegation:
        session = self._sessions.validate(session_id, session_token)
        parent = self._agents.get(request.requesting_agent_id)
        if session.agent_id != parent.agent_id or session.sector != parent.sector:
            raise PermissionError("Delegation requester does not match the active session.")
        if BrainOperation.DELEGATE_TASK not in session.allowed_operations:
            raise PermissionError("Session is not authorized to delegate tasks.")
        if not any(
            agent.role == request.target_agent_type and agent.status == "active"
            for agent in self._agents.definitions()
        ):
            raise PermissionError("Delegation target agent type is not registered.")
        for reference in request.context_refs:
            memory_record = self._memory.get(parent, reference)
            if memory_record.namespace not in session.allowed_memory_namespaces:
                raise PermissionError("Delegation cannot include memory outside the requesting session scope.")
        reservation = self._budgets.reserve(
            agent_id=parent.agent_id,
            task_id=session.task_id,
            amount=request.budget,
            limit=Money(min(parent.max_cost_per_task.amount, session.cost_limit.amount), parent.max_cost_per_task.currency),
        )
        try:
            delegation = self._delegations.create(parent, request, parent_depth=parent_depth)
        except (PermissionError, ValueError):
            self._budgets.release_if_active(reservation.reservation_id)
            raise
        self._delegation_reservations[delegation.delegation_id] = reservation.reservation_id
        if self._persistence is not None:
            self._persistence.put_record(
                "brain_delegation_reservations",
                delegation.delegation_id,
                {"reservation_id": reservation.reservation_id},
            )
        self._events.publish(
            "brain.delegation.created", source="brain",
            payload={"delegation_id": delegation.delegation_id, "agent_id": parent.agent_id, "status": delegation.status},
            correlation_id=delegation.delegation_id,
        )
        return delegation

    def cancel_delegation(self, delegation_id: str, *, authority: str) -> Delegation:
        cancelled = self._delegations.cancel(delegation_id, authority=authority)
        reservation_id = self._delegation_reservations.pop(delegation_id, None)
        if reservation_id is not None:
            self._budgets.release_if_active(reservation_id)
            if self._persistence is not None:
                self._persistence.delete_record(
                    "brain_delegation_reservations", delegation_id
                )
        self._events.publish(
            "brain.delegation.cancelled", source="brain",
            payload={"delegation_id": delegation_id},
            correlation_id=delegation_id,
        )
        return cancelled

    def approve_delegation(self, delegation_id: str, *, authority: str) -> Delegation:
        delegation = self._delegations.approve(delegation_id, authority=authority)
        self._events.publish(
            "brain.delegation.approved", source="brain",
            payload={"delegation_id": delegation_id},
            correlation_id=delegation_id,
        )
        return delegation

    def complete_delegation(
        self,
        delegation_id: str,
        *,
        target_agent_id: str,
        session_id: str,
        session_token: str,
        result: Any,
    ) -> Delegation:
        delegation = self._delegations.get(delegation_id)
        session = self._sessions.validate(session_id, session_token)
        target = self._agents.get(target_agent_id)
        if (
            target.role != delegation.target_agent_type
            or session.agent_id != target_agent_id
            or session.task_id != delegation_id
            or BrainOperation.COMPLETE not in session.allowed_operations
        ):
            raise PermissionError("Delegated result does not match its authorized target session.")
        schema = self._schemas.get(delegation.expected_schema)
        if schema is None:
            raise ValueError(f"Unknown output schema: {delegation.expected_schema}")
        from .policy import validate_output
        validate_output(result, schema)
        completed = self._delegations.complete(delegation_id, target_agent_type=target.role, result=result)
        reservation_id = self._delegation_reservations.pop(delegation_id, None)
        if reservation_id is not None:
            parent = self._agents.get(delegation.parent_agent_id)
            self._budgets.commit(reservation_id, delegation.budget, limit=parent.max_cost_per_task)
            if self._persistence is not None:
                self._persistence.delete_record(
                    "brain_delegation_reservations", delegation_id
                )
        self._events.publish(
            "brain.delegation.completed", source="brain",
            payload={"delegation_id": delegation_id, "target_agent_id": target_agent_id},
            correlation_id=delegation_id,
        )
        return completed

    def complete(self, request: InferenceRequest, *, session_id: str, session_token: str) -> InferenceResponse:
        self.reliability.ensure_work_allowed("Brain inference")
        self._pause_controller.check()
        input_data = json.loads(canonical_json(request.input))
        request_hash = content_hash(input_data)
        try:
            session = self._sessions.validate(session_id, session_token)
            agent = self._agents.get(request.agent_id)
            authorize_inference(agent, session, request)
        except (KeyError, PermissionError):
            self._audit(request, request_hash, None, "blocked", "authorization_denied", request.model_profile or "unrouted")
            raise
        if request.operation in {
            BrainOperation.RETRIEVE, BrainOperation.MEMORY_WRITE, BrainOperation.MEMORY_FORGET,
            BrainOperation.DELEGATE_TASK,
        }:
            self._audit(request, request_hash, None, "blocked", "control_operation_not_inference", request.model_profile or "unrouted")
            raise ValueError("Use the Brain memory or delegation service for this operation.")
        schema = self._schemas.get(request.schema_name) if request.schema_name is not None else None
        if request.schema_name is not None and schema is None:
            self._audit(request, request_hash, None, "blocked", "unknown_schema", request.model_profile or "unrouted")
            raise ValueError(f"Unknown output schema: {request.schema_name}")
        try:
            context = self._context.build(
                agent, task_id=request.task_id, references=request.context_refs,
                max_tokens=max(0, request.max_tokens // 2),
                allowed_namespaces=session.allowed_memory_namespaces,
            )
        except (KeyError, PermissionError, ValueError):
            self._audit(request, request_hash, None, "blocked", "context_rejected", request.model_profile or "unrouted")
            raise
        context_items = tuple(asdict(item) for item in context.items)
        estimated_input_tokens = _estimate_input_tokens(input_data, context_items)
        try:
            profiles = self._models.route(agent, request)
        except PermissionError:
            self._audit(request, request_hash, None, "blocked", "model_policy_denied", request.model_profile or "unrouted")
            raise
        profiles = tuple(
            profile for profile in profiles
            if estimated_input_tokens + request.max_tokens <= profile.context_window
        )
        if not profiles:
            self._audit(request, request_hash, None, "blocked", "context_window_exceeded", request.model_profile or "unrouted")
            raise PermissionError("No authorized model profile has enough context for this request.")
        affordable = tuple(
            profile for profile in profiles
            if (
                estimated_input_tokens * profile.cost_per_1k_input_tokens
                + request.max_tokens * profile.cost_per_1k_output_tokens
            ) / 1000 <= request.max_cost.amount
        )
        if not affordable:
            self._audit(request, request_hash, None, "blocked", "budget_estimate_exceeded", profiles[0].profile_id)
            raise BudgetExceeded("Estimated inference cost exceeds the request budget.")
        profiles = affordable
        with self._lock:
            if request.request_id in self._request_ids:
                self._audit(request, request_hash, None, "blocked", "duplicate_request_id", profiles[0].profile_id)
                raise ValueError("request_id has already been used.")
            if self._persistence is not None:
                try:
                    self._persistence.insert_record(
                        "brain_request_ids",
                        request.request_id,
                        {"request_id": request.request_id},
                    )
                except ValueError:
                    self._audit(
                        request,
                        request_hash,
                        None,
                        "blocked",
                        "duplicate_request_id",
                        profiles[0].profile_id,
                    )
                    raise ValueError("request_id has already been used.") from None
            self._request_ids.add(request.request_id)
        try:
            reservation = self._budgets.reserve(
                agent_id=agent.agent_id, task_id=request.task_id,
                amount=request.max_cost,
                limit=Money(min(agent.max_cost_per_task.amount, session.cost_limit.amount), agent.max_cost_per_task.currency),
                tokens=estimated_input_tokens + request.max_tokens,
                token_limit=min(agent.max_tokens_per_task, session.token_limit),
            )
        except BudgetExceeded:
            self._audit(request, request_hash, None, "blocked", "budget_exceeded", profiles[0].profile_id)
            self._events.publish(
                "brain.budget.exceeded", source="brain",
                payload={"request_id": request.request_id, "agent_id": agent.agent_id, "task_id": request.task_id},
                correlation_id=request.request_id,
            )
            raise
        try:
            return self._execute_reserved(
                request, request_hash, input_data, session, session_token, agent, schema, context, context_items,
                profiles, reservation.reservation_id,
            )
        finally:
            self._budgets.release_if_active(reservation.reservation_id)

    def _execute_reserved(
        self,
        request: InferenceRequest,
        request_hash: str,
        input_data: Any,
        session: AgentSession,
        session_token: str,
        agent: AgentDefinition,
        schema: dict[str, Any] | None,
        context,
        context_items: tuple[dict[str, Any], ...],
        profiles: tuple[ModelProfile, ...],
        reservation_id: str,
    ) -> InferenceResponse:
        self._events.publish(
            "brain.inference.requested", source="brain",
            payload={"request_id": request.request_id, "agent_id": agent.agent_id, "sector": agent.sector, "task_id": request.task_id},
            correlation_id=request.request_id,
        )
        attempted: list[str] = []
        response_data = None
        for profile in profiles:
            try:
                self._pause_controller.check()
                self._sessions.validate(session.session_id, session_token)
                self._agents.get(agent.agent_id)
            except (KeyError, PermissionError):
                self._audit(request, request_hash, None, "blocked", "identity_or_pause_revoked", profile.profile_id)
                raise
            attempted.append(profile.profile_id)
            adapter = self._providers.get(profile.provider_id)
            circuit = self._circuits.get(profile.provider_id)
            if adapter is None or circuit is None or not circuit.can_attempt():
                continue
            if adapter.provider_id != profile.provider_id:
                raise ProviderError("Provider adapter identity does not match its registered profile.")
            credential = None
            try:
                try:
                    granted_credential = self._secrets.get_scoped_credential(
                        requester_id="brain-provider-gateway", resource=profile.provider_id,
                        purpose="inference", duration_seconds=60,
                    )
                except SecretAccessError:
                    circuit.failure()
                    continue
                if not isinstance(granted_credential, ScopedCredential):
                    raise TypeError("Secret manager returned an invalid provider credential.")
                credential = granted_credential
                serialized_input = json.dumps(
                    {"input": input_data, "context": context_items}, ensure_ascii=False, default=str, allow_nan=False,
                )
                if credential.contains(serialized_input):
                    self._audit(request, request_hash, None, "blocked", "secret_in_request", profile.profile_id)
                    self._events.publish(
                        "brain.policy.violation", source="brain",
                        payload={"request_id": request.request_id, "agent_id": agent.agent_id, "reason": "secret_in_request"},
                        correlation_id=request.request_id,
                    )
                    raise SecretInRequestError("Request was rejected by secret-leak controls.")
                provider_request = ProviderRequest(
                    request.request_id, profile.model_name, request.operation, input_data,
                    context_items, request.max_tokens,
                    request.timeout_ms, deepcopy(schema),
                )
                candidate = adapter.complete(provider_request, credential)
                if not isinstance(candidate, ProviderResponse):
                    raise ProviderError("Provider adapter returned an invalid response.") from None
                candidate = ProviderResponse(
                    json.loads(json.dumps(candidate.output, ensure_ascii=False, allow_nan=False)),
                    candidate.input_tokens,
                    candidate.output_tokens,
                )
                if candidate.input_tokens + candidate.output_tokens > profile.context_window:
                    raise ProviderError("Provider response exceeded the model context window.")
                content_hash(candidate.output)
                output_contains_secret = credential.contains(json.dumps(candidate.output, ensure_ascii=False, default=str))
                circuit.success()
                response_data = (profile, candidate, output_contains_secret)
                break
            except SecretLeakError:
                raise
            except SecretInRequestError:
                raise
            except (ProviderError, PermissionError, ValueError, TypeError, TimeoutError, ConnectionError):
                circuit.failure()
                continue
            finally:
                if credential is not None:
                    credential.revoke()
        if response_data is None:
            self._audit(request, request_hash, None, "failed", "provider_unavailable", profiles[0].profile_id)
            self._events.publish(
                "brain.inference.failed", source="brain",
                payload={"request_id": request.request_id, "agent_id": agent.agent_id, "reason": "provider_unavailable"},
                correlation_id=request.request_id,
            )
            raise ProviderError("All eligible providers failed or are unavailable.") from None

        profile, provider_response, output_contains_secret = response_data
        cost = Money(
            provider_response.input_tokens * profile.cost_per_1k_input_tokens / 1000
            + provider_response.output_tokens * profile.cost_per_1k_output_tokens / 1000,
            profile.currency,
        )
        usage = UsageRecord(
            request.request_id, agent.agent_id, agent.sector, request.task_id, profile.provider_id,
            profile.profile_id, provider_response.input_tokens, provider_response.output_tokens, cost,
        )
        self._record_usage(usage)
        try:
            task_limit = Money(
                min(agent.max_cost_per_task.amount, session.cost_limit.amount),
                agent.max_cost_per_task.currency,
            )
            self._budgets.commit(
                reservation_id, cost, limit=task_limit,
                actual_tokens=provider_response.input_tokens + provider_response.output_tokens,
                token_limit=min(agent.max_tokens_per_task, session.token_limit),
            )
        except BudgetExceeded:
            self._audit(request, request_hash, None, "blocked", "budget_exceeded", profile.profile_id)
            self._events.publish(
                "brain.budget.exceeded", source="brain",
                payload={"request_id": request.request_id, "agent_id": agent.agent_id, "task_id": request.task_id},
                correlation_id=request.request_id,
            )
            raise

        try:
            self._sessions.validate(session.session_id, session_token)
            self._agents.get(agent.agent_id)
        except (KeyError, PermissionError):
            self._audit(request, request_hash, None, "blocked", "identity_revoked", profile.profile_id)
            self._events.publish(
                "brain.policy.violation", source="brain",
                payload={"request_id": request.request_id, "agent_id": agent.agent_id, "reason": "identity_revoked"},
                correlation_id=request.request_id,
            )
            raise PermissionError("Agent or session was revoked during inference.") from None

        if output_contains_secret:
            return self._reject(request, request_hash, profile, "secret_leak")
        try:
            if schema is not None:
                validate_output(provider_response.output, schema)
        except (ValueError, TypeError):
            return self._reject(request, request_hash, profile, "output_schema_invalid")
        if provider_response.output_tokens > request.max_tokens:
            return self._reject(request, request_hash, profile, "output_token_limit_exceeded")
        try:
            self._pause_controller.check()
        except PermissionError:
            self._audit(request, request_hash, None, "blocked", "emergency_pause", profile.profile_id)
            raise

        audit = self._audit(request, request_hash, content_hash(provider_response.output), "success", None, profile.profile_id)
        self._events.publish(
            "brain.inference.completed", source="brain",
            payload={
                "request_id": request.request_id, "agent_id": agent.agent_id, "sector": agent.sector,
                "task_id": request.task_id, "provider_id": profile.provider_id, "model_profile": profile.profile_id,
                "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens, "cost": cost.amount,
                "audit_id": audit.audit_id,
            },
            correlation_id=request.request_id,
        )
        warnings = tuple(
            (["Model fallback selected after earlier provider failures."] if attempted.index(profile.profile_id) > 0 else [])
            + (["A different model profile was selected to satisfy the request budget."] if request.model_profile and profile.profile_id != request.model_profile else [])
            + list(context.limitations)
        )
        return InferenceResponse(request.request_id, "success", provider_response.output, warnings, usage, profile.profile_id, audit.audit_id)

    def _reject(self, request: InferenceRequest, request_hash: str, profile: ModelProfile, reason: str):
        self._audit(request, request_hash, None, "blocked", reason, profile.profile_id)
        self._events.publish(
            "brain.output.rejected", source="brain",
            payload={"request_id": request.request_id, "agent_id": request.agent_id, "reason": reason},
            correlation_id=request.request_id,
        )
        if reason == "secret_leak":
            raise SecretLeakError("Provider output was rejected by secret-leak controls.")
        if reason == "output_schema_invalid":
            raise ProviderOutputError("Provider output did not satisfy its registered schema.")
        raise ProviderOutputError("Provider output exceeded the request token limit.")

    def _audit(self, request, input_hash: str, output_hash: str | None, status: str, reason: str | None, model_profile: str) -> InferenceAudit:
        audit = InferenceAudit(
            secrets.token_urlsafe(18), request.request_id, request.agent_id, request.sector, request.task_id,
            request.context_refs, request.operation, model_profile, input_hash, output_hash, status, reason,
        )
        with self._lock:
            self._audits.append(audit)
            if self._persistence is not None:
                self._persistence.append_event(
                    "brain_audits", request.request_id, audit.audit_id, audit
                )
        return audit

    def _record_usage(self, usage: UsageRecord) -> None:
        with self._lock:
            if self._persistence is not None:
                self._persistence.append_event(
                    "brain_usage", usage.request_id, usage.request_id, usage
                )
            self._usage.append(usage)

    def write_memory(self, record: MemoryRecord, *, session_id: str, session_token: str) -> MemoryRecord:
        session = self._sessions.validate(session_id, session_token)
        agent = self._agents.get(session.agent_id)
        if BrainOperation.MEMORY_WRITE not in session.allowed_operations or BrainOperation.MEMORY_WRITE not in agent.allowed_operations:
            raise PermissionError("Session is not authorized to write memory.")
        if record.namespace not in session.allowed_memory_namespaces:
            raise PermissionError("Session cannot write to this memory namespace.")
        created = self._memory.write(agent, record)
        self._events.publish(
            "brain.memory.written", source="brain",
            payload={"memory_id": record.memory_id, "agent_id": agent.agent_id, "namespace": record.namespace, "sensitivity": record.sensitivity.value},
            correlation_id=session.session_id,
        )
        return created

    def retrieve_memory(
        self,
        *,
        namespace: str,
        query: str,
        session_id: str,
        session_token: str,
        top_k: int = 10,
    ) -> tuple[MemoryRecord, ...]:
        session = self._sessions.validate(session_id, session_token)
        agent = self._agents.get(session.agent_id)
        if BrainOperation.RETRIEVE not in session.allowed_operations or BrainOperation.RETRIEVE not in agent.allowed_operations:
            raise PermissionError("Session is not authorized to retrieve memory.")
        if namespace not in session.allowed_memory_namespaces:
            raise PermissionError("Session cannot read this memory namespace.")
        records = self._memory.retrieve(agent, namespace=namespace, query=query, top_k=top_k)
        self._events.publish(
            "brain.memory.read", source="brain",
            payload={"agent_id": agent.agent_id, "namespace": namespace, "result_count": len(records)},
            correlation_id=session.session_id,
        )
        return records

    def forget_memory(self, memory_id: str, *, session_id: str, session_token: str) -> None:
        session = self._sessions.validate(session_id, session_token)
        agent = self._agents.get(session.agent_id)
        if BrainOperation.MEMORY_FORGET not in session.allowed_operations or BrainOperation.MEMORY_FORGET not in agent.allowed_operations:
            raise PermissionError("Session is not authorized to forget memory.")
        record = self._memory.get(agent, memory_id)
        if record.namespace not in session.allowed_memory_namespaces:
            raise PermissionError("Session cannot forget memory in this namespace.")
        self._memory.forget(agent, memory_id)
        self._events.publish(
            "brain.memory.forgotten", source="brain",
            payload={"memory_id": memory_id, "agent_id": agent.agent_id, "namespace": record.namespace},
            correlation_id=session.session_id,
        )

    def audit_log(self) -> tuple[InferenceAudit, ...]:
        with self._lock:
            return tuple(self._audits)

    def usage_log(self) -> tuple[UsageRecord, ...]:
        with self._lock:
            return tuple(self._usage)

    def health(self) -> dict[str, Any]:
        allowed_states = {"healthy", "degraded", "rate_limited", "unavailable", "auth_failure"}
        providers = {}
        for provider_id, adapter in self._providers.items():
            try:
                provider_health = adapter.health_check()
            except (ProviderError, TimeoutError, ConnectionError):
                provider_health = "unavailable"
            if provider_health not in allowed_states:
                provider_health = "unknown"
            providers[provider_id] = {
                "state": self._circuits[provider_id].state,
                "health": provider_health,
            }
        usable_provider = any(
            provider["health"] in {"healthy", "degraded", "rate_limited"}
            and provider["state"] != "open"
            for provider in providers.values()
        )
        is_paused = self._pause_controller.reason is not None or self.reliability.failsafe.paused
        status = "paused" if is_paused else (
            "ready" if usable_provider else "not_ready"
        )
        if usable_provider and any(
            provider["health"] != "healthy" or provider["state"] != "healthy"
            for provider in providers.values()
        ):
            status = "degraded"
        return {
            "status": status,
            "live": True,
            "ready": usable_provider and not is_paused,
            "dependencies": providers,
            "providers": providers,
        }


def default_schema_registry() -> dict[str, dict[str, Any]]:
    return {
        "agent_result": {
            "type": "object",
            "required": ["result"],
            "properties": {"result": {"type": "string", "minLength": 1}},
            "additionalProperties": False,
        }
    }
