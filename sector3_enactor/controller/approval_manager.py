"""Approval manager compatibility wrapper for the architecture doc."""
from __future__ import annotations

from dataclasses import dataclass

from ..models.approval import ApprovalLevel, ApprovalRequest
from ..policy.approval_policy import ApprovalPolicy


@dataclass
class ApprovalManager:
    policy: ApprovalPolicy

    def create(self, **kwargs) -> ApprovalRequest:
        return self.policy.request(**kwargs)

    def list(self, execution_id: str) -> tuple[ApprovalRequest, ...]:
        return self.policy._approvals.for_execution(execution_id)

    def resolve(self, approval_id: str, *, approve: bool, decided_by: str, level: ApprovalLevel = ApprovalLevel.A4_STRICT):
        return self.policy.decide(approval_id, approve=approve, decided_by=decided_by, approver_level=level)


__all__ = ["ApprovalManager"]
