"""Execution state machine — document §4.2 (all 15 states). Illegal transitions
raise; every transition is audited with from/to and the triggering event."""
from __future__ import annotations

from ..models.execution import ExecutionStatus
from ..storage.audit_repository import AuditRepository

ALLOWED_TRANSITIONS: dict[ExecutionStatus, frozenset[ExecutionStatus]] = {
    ExecutionStatus.RECEIVED: frozenset({ExecutionStatus.VALIDATING, ExecutionStatus.REJECTED, ExecutionStatus.CANCELLED}),
    ExecutionStatus.VALIDATING: frozenset({ExecutionStatus.PLANNING, ExecutionStatus.REJECTED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED}),
    ExecutionStatus.PLANNING: frozenset({ExecutionStatus.AWAITING_APPROVAL, ExecutionStatus.PREPARING_RESOURCES, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED}),
    ExecutionStatus.AWAITING_APPROVAL: frozenset({ExecutionStatus.PREPARING_RESOURCES, ExecutionStatus.REJECTED, ExecutionStatus.CANCELLED, ExecutionStatus.FAILED}),
    ExecutionStatus.PREPARING_RESOURCES: frozenset({ExecutionStatus.EXECUTING, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED}),
    ExecutionStatus.EXECUTING: frozenset({ExecutionStatus.MONITORING, ExecutionStatus.AWAITING_APPROVAL, ExecutionStatus.PAUSED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED, ExecutionStatus.ROLLING_BACK}),
    ExecutionStatus.MONITORING: frozenset({ExecutionStatus.EXECUTING, ExecutionStatus.PAUSED, ExecutionStatus.AWAITING_APPROVAL, ExecutionStatus.ROLLING_BACK, ExecutionStatus.COMPLETED, ExecutionStatus.PARTIALLY_COMPLETED, ExecutionStatus.FAILED}),
    ExecutionStatus.PAUSED: frozenset({ExecutionStatus.EXECUTING, ExecutionStatus.CANCELLED, ExecutionStatus.ROLLING_BACK, ExecutionStatus.FAILED}),
    ExecutionStatus.ROLLING_BACK: frozenset({ExecutionStatus.FAILED, ExecutionStatus.CANCELLED, ExecutionStatus.COMPLETED}),
    ExecutionStatus.COMPLETED: frozenset({ExecutionStatus.ARCHIVED}),
    ExecutionStatus.PARTIALLY_COMPLETED: frozenset({ExecutionStatus.ARCHIVED}),
    ExecutionStatus.FAILED: frozenset({ExecutionStatus.ARCHIVED}),
    ExecutionStatus.CANCELLED: frozenset({ExecutionStatus.ARCHIVED}),
    ExecutionStatus.REJECTED: frozenset({ExecutionStatus.ARCHIVED}),
    ExecutionStatus.ARCHIVED: frozenset(),
}

TERMINAL = frozenset({ExecutionStatus.COMPLETED, ExecutionStatus.PARTIALLY_COMPLETED, ExecutionStatus.FAILED,
                      ExecutionStatus.CANCELLED, ExecutionStatus.REJECTED})


class IllegalTransition(ValueError):
    pass


class ExecutionStateMachine:
    def __init__(self, audit: AuditRepository) -> None:
        self._audit = audit

    def transition(self, request, to: ExecutionStatus, *, event: str, reason: str = "") -> ExecutionStatus:
        from_state = request.status
        if to not in ALLOWED_TRANSITIONS[from_state]:
            self._audit.append(event_type="illegal_transition_attempt", business_id=request.business_id,
                               execution_id=request.execution_id,
                               detail={"from": from_state.value, "attemptedTo": to.value, "event": event})
            raise IllegalTransition(f"Illegal execution transition {from_state.value} -> {to.value} ({event}).")
        request.status = to
        self._audit.append(event_type="state_transition", business_id=request.business_id,
                           execution_id=request.execution_id,
                           detail={"from": from_state.value, "to": to.value, "event": event, "reason": reason})
        return to
