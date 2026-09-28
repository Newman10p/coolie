"""Approval models — document §4.5 (A0–A4) and §8.1 (exact binding)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .shared import Money, RiskSeverity, now_utc, _non_empty


class ApprovalLevel(str, Enum):
    """Document §4.5 table."""
    A0_NONE = "A0"            # read-only, no approval required
    A1_INTERNAL = "A1"        # internal draft, logged only
    A2_LIGHTWEIGHT = "A2"     # low-risk reversible action, pre-approved policy envelope
    A3_STANDARD = "A3"        # standard external action, explicit approval per action-binding
    A4_STRICT = "A4"          # irreversible / financial / production, named human approver


LEVEL_ORDER = {ApprovalLevel.A0_NONE: 0, ApprovalLevel.A1_INTERNAL: 1, ApprovalLevel.A2_LIGHTWEIGHT: 2,
               ApprovalLevel.A3_STANDARD: 3, ApprovalLevel.A4_STRICT: 4}


def level_at_least(level: ApprovalLevel, minimum: ApprovalLevel) -> bool:
    return LEVEL_ORDER[level] >= LEVEL_ORDER[minimum]


class ApprovalStatus(str, Enum):
    REQUESTED = "requested"; APPROVED = "approved"; DENIED = "denied"; EXPIRED = "expired"; CONSUMED = "consumed"


@dataclass(frozen=True)
class ApprovalRequest:
    """An approval is bound to exactness: tool + target + exact arguments (+ optional amount).

    The gateway re-hashes these fields at execution time; any drift invalidates the
    approval and forces a fresh request (document §8.1 rule 2).
    """
    approval_id: str
    execution_id: str
    task_id: str
    agent_id: str
    business_id: str
    tool: str
    target: str
    exact_arguments: dict[str, Any]
    requested_level: ApprovalLevel
    risk_level: RiskSeverity
    reason: str
    amount: Money | None = None
    expires_at: datetime | None = None
    status: ApprovalStatus = ApprovalStatus.REQUESTED
    decided_by: str | None = None
    decided_at: datetime | None = None
    requested_at: datetime = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        for name in ("approval_id", "execution_id", "task_id", "agent_id", "business_id", "tool", "target", "reason"):
            _non_empty(getattr(self, name), name)
        if not isinstance(self.requested_level, ApprovalLevel): raise ValueError("requested_level must be an ApprovalLevel.")
        if self.requested_level is ApprovalLevel.A0_NONE: raise ValueError("A0 actions never generate approval requests.")
        if not isinstance(self.risk_level, RiskSeverity): raise ValueError("risk_level must be a RiskSeverity.")
        if not isinstance(self.status, ApprovalStatus): raise ValueError("status must be an ApprovalStatus.")
        if not isinstance(self.exact_arguments, dict) or not self.exact_arguments:
            raise ValueError("Approval requires non-empty exact_arguments binding.")
        if self.amount is not None and not isinstance(self.amount, Money): raise ValueError("amount must be Money.")
        for stamp in ("expires_at", "decided_at", "requested_at"):
            value = getattr(self, stamp)
            if value is not None and value.tzinfo is None: raise ValueError(f"{stamp} must be timezone-aware.")
        if self.status is ApprovalStatus.APPROVED and not self.decided_by:
            raise ValueError("Approved requests must record decided_by.")

    def binding_payload(self) -> dict[str, Any]:
        """The canonical payload whose hash defines what was approved."""
        payload: dict[str, Any] = {
            "tool": self.tool,
            "target": self.target,
            "exactArguments": self.exact_arguments,
            "level": self.requested_level.value,
        }
        if self.amount is not None:
            payload["amount"] = {"amount": self.amount.amount, "currency": self.amount.currency}
        return payload

    def is_valid_for(self, *, now: datetime, approver_level: ApprovalLevel | None) -> tuple[bool, str]:
        if self.status is not ApprovalStatus.APPROVED:
            return False, f"Approval {self.approval_id} is {self.status.value}, not approved."
        if self.expires_at is not None and now >= self.expires_at:
            return False, f"Approval {self.approval_id} expired at {self.expires_at.isoformat()}."
        if approver_level is not None and not level_at_least(approver_level, self.requested_level):
            return False, f"Approver level {approver_level.value} is below required {self.requested_level.value}."
        return True, ""
