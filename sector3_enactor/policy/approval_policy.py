"""Approval workflow — document §4.5, §8.1 rules 1–2, §10 step 4.

Approvals bind to (execution, task, agent, tool, target, exact arguments, level,
optional amount). They expire, are single-use, and cannot be reused across tasks,
agents or executions (defeats confused-deputy replay).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from ..config.loader import SectorConfig
from ..models.approval import ApprovalLevel, ApprovalRequest, ApprovalStatus, LEVEL_ORDER, level_at_least
from ..models.shared import Money, RiskSeverity, now_utc
from ..models.task import ApprovalGate, EnactorTask
from ..storage.audit_repository import AuditRepository
from ..storage.repositories import ApprovalRepository
from ..policy.hashing import digest


class ApprovalPolicy:
    def __init__(self, config: SectorConfig, approvals: ApprovalRepository, audit: AuditRepository) -> None:
        self._config = config
        self._approvals = approvals
        self._audit = audit

    def required_level(self, gate: ApprovalGate, *, context_flags: tuple[str, ...] = ()) -> ApprovalLevel:
        """Context rules may raise a level, never lower it (§4.5)."""
        level = gate.required_level
        for flag in context_flags:
            escalated = self._config.approval_escalations.get(flag)
            if escalated is not None and LEVEL_ORDER[escalated] > LEVEL_ORDER[level]:
                level = escalated
        return level

    def request(self, *, execution_id: str, business_id: str, task: EnactorTask, agent_id: str,
                tool: str, target: str, exact_arguments: dict, level: ApprovalLevel,
                risk: RiskSeverity, reason: str, amount: Money | None = None,
                expires_at: datetime | None = None) -> ApprovalRequest:
        if level is ApprovalLevel.A0_NONE: raise ValueError("A0 actions do not need approvals.")
        expiry_hours = self._config.approval_expiry_hours.get(level)
        if expires_at is None and expiry_hours is not None:
            expires_at = now_utc() + timedelta(hours=expiry_hours)
        request = ApprovalRequest(
            approval_id=f"APR-{uuid4().hex[:10]}", execution_id=execution_id, task_id=task.task_id,
            agent_id=agent_id, business_id=business_id, tool=tool, target=target,
            exact_arguments=dict(exact_arguments), requested_level=level, risk_level=risk,
            reason=reason, amount=amount, expires_at=expires_at)
        self._approvals.put(request)
        self._audit.append(event_type="approval_requested", business_id=business_id, execution_id=execution_id,
                           task_id=task.task_id, agent_id=agent_id, tool=tool, approval_id=request.approval_id,
                           detail={"level": level.value, "bindingHash": digest(request.binding_payload()),
                                   "reason": reason, "expiresAt": expires_at.isoformat() if expires_at else None})
        return request

    def decide(self, approval_id: str, *, approve: bool, decided_by: str, approver_level: ApprovalLevel,
               at: datetime | None = None) -> ApprovalRequest:
        request = self._approvals.get(approval_id)
        if request.status is not ApprovalStatus.REQUESTED: raise ValueError("Only pending approvals can be decided.")
        if not decided_by.strip(): raise ValueError("Approver identity is required.")
        if approve and not level_at_least(approver_level, request.requested_level):
            raise PermissionError(f"Approver level {approver_level.value} below required {request.requested_level.value}.")
        decided = ApprovalRequest(
            **{**request.__dict__, "status": ApprovalStatus.APPROVED if approve else ApprovalStatus.DENIED,
               "decided_by": decided_by, "decided_at": at or now_utc()})
        self._approvals.put(decided)
        self._audit.append(event_type="approval_decided", business_id=request.business_id,
                           execution_id=request.execution_id, task_id=request.task_id, agent_id=request.agent_id,
                           tool=request.tool, approval_id=approval_id,
                           detail={"decision": decided.status.value, "decidedBy": decided_by,
                                   "level": request.requested_level.value})
        return decided

    def validate_binding(self, request: ApprovalRequest, *, task: EnactorTask, agent_id: str, tool: str,
                         target: str, exact_arguments: dict, amount: Money | None,
                         approver_level: ApprovalLevel | None, at: datetime | None = None) -> tuple[bool, str]:
        """The gateway re-checks EVERY binding dimension before letting an action through."""
        now = at or now_utc()
        valid, reason = request.is_valid_for(now=now, approver_level=approver_level)
        if not valid: return False, reason
        if request.execution_id != task.execution_id: return False, "Approval belongs to another execution."
        if request.task_id != task.task_id: return False, "Approval belongs to another task (no cross-task reuse)."
        if request.agent_id != agent_id: return False, "Approval was granted to a different agent (confused-deputy denied)."
        if request.tool != tool: return False, f"Approval bound to tool {request.tool}, called with {tool}."
        if request.target != target: return False, "Action target drifted from the approved target."
        if digest(request.exact_arguments) != digest(exact_arguments): return False, "Argument drift: payload differs from approved hash."
        if request.amount is not None:
            if amount is None: return False, "Approved amount missing from executed action."
            if amount.currency != request.amount.currency: return False, "Currency mismatch against approved amount."
            if amount.amount > request.amount.amount: return False, "Executed amount exceeds the approved amount."
        return True, ""

    def consume(self, request: ApprovalRequest) -> None:
        """Single-use enforcement: mark consumed after a successful external action."""
        consumed = ApprovalRequest(**{**request.__dict__, "status": ApprovalStatus.CONSUMED})
        self._approvals.put(consumed)
        self._audit.append(event_type="approval_consumed", business_id=request.business_id,
                           execution_id=request.execution_id, task_id=request.task_id, agent_id=request.agent_id,
                           tool=request.tool, approval_id=request.approval_id, detail={"singleUse": True})
