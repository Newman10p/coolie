from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from research_room.models import Money


def _nonempty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ShariaStatus(str, Enum):
    COMPLIANT = "compliant"
    UNCERTAIN = "uncertain"
    NON_COMPLIANT = "non_compliant"


class DecisionCode(str, Enum):
    REJECT = "reject"
    RESEARCH_MORE = "research_more"
    REQUEST_SCHOLAR_REVIEW = "request_scholar_review"
    REQUEST_OWNER_APPROVAL = "request_owner_approval"
    RUN_CONTROLLED_TEST = "run_controlled_test"
    APPROVE_LIMITED_LAUNCH = "approve_limited_launch"
    CONTINUE = "continue"
    PAUSE = "pause"
    STOP = "stop"
    SCALE = "scale"
    ARCHIVE = "archive"
    APPROVE_MANDATE = "approve_mandate"


@dataclass(frozen=True)
class OwnerObjective:
    objective_id: str
    owner: str
    summary: str
    desired_outcome: str
    risk_tolerance: Literal["low", "medium", "high"] = "medium"
    max_budget: Money | None = None
    approval_required: bool = False
    created_at: datetime = field(default_factory=_now_utc)

    def __post_init__(self) -> None:
        _nonempty(self.objective_id, "objective_id")
        _nonempty(self.owner, "owner")
        _nonempty(self.summary, "summary")
        _nonempty(self.desired_outcome, "desired_outcome")
        if self.risk_tolerance not in {"low", "medium", "high"}:
            raise ValueError("risk_tolerance must be low, medium, or high.")
        if self.max_budget is not None and not isinstance(self.max_budget, Money):
            raise ValueError("max_budget must be a Money value when provided.")
        if self.max_budget is not None and self.max_budget.amount <= 0:
            raise ValueError("max_budget must be positive when provided.")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")


@dataclass(frozen=True)
class OrchestratorDecision:
    decision_id: str
    objective_id: str
    code: DecisionCode
    summary: str
    reason: str
    requires_owner_approval: bool = False
    budget_approved: bool = False
    created_at: datetime = field(default_factory=_now_utc)

    def __post_init__(self) -> None:
        _nonempty(self.decision_id, "decision_id")
        _nonempty(self.objective_id, "objective_id")
        _nonempty(self.summary, "summary")
        _nonempty(self.reason, "reason")
        if not isinstance(self.code, DecisionCode):
            raise ValueError("code must be a DecisionCode.")
        if not isinstance(self.requires_owner_approval, bool):
            raise ValueError("requires_owner_approval must be a boolean.")
        if not isinstance(self.budget_approved, bool):
            raise ValueError("budget_approved must be a boolean.")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")


@dataclass(frozen=True)
class EnactorMandate:
    mandate_id: str
    objective_id: str
    action: str
    allowed_actions: tuple[str, ...]
    constraints: tuple[str, ...]
    budget_cap: Money | None = None
    approval_reference: str | None = None
    created_at: datetime = field(default_factory=_now_utc)

    def __post_init__(self) -> None:
        _nonempty(self.mandate_id, "mandate_id")
        _nonempty(self.objective_id, "objective_id")
        _nonempty(self.action, "action")
        if not isinstance(self.allowed_actions, tuple) or not self.allowed_actions:
            raise ValueError("allowed_actions must be a non-empty tuple of strings.")
        if any(not isinstance(item, str) or not item.strip() for item in self.allowed_actions):
            raise ValueError("allowed_actions must contain non-empty strings.")
        if not isinstance(self.constraints, tuple):
            raise ValueError("constraints must be a tuple of strings.")
        if any(not isinstance(item, str) or not item.strip() for item in self.constraints):
            raise ValueError("constraints must contain non-empty strings.")
        if self.budget_cap is not None and not isinstance(self.budget_cap, Money):
            raise ValueError("budget_cap must be a Money value when provided.")
        if self.approval_reference is not None:
            _nonempty(self.approval_reference, "approval_reference")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")


@dataclass(frozen=True)
class DecisionAudit:
    objective_id: str
    decision_id: str
    code: DecisionCode
    sharia_status: ShariaStatus
    evidence_confidence: float
    budget_approved: bool
    operational_risk: str
    created_at: datetime = field(default_factory=_now_utc)

    def __post_init__(self) -> None:
        _nonempty(self.objective_id, "objective_id")
        _nonempty(self.decision_id, "decision_id")
        _nonempty(self.operational_risk, "operational_risk")
        if not isinstance(self.code, DecisionCode):
            raise ValueError("code must be a DecisionCode.")
        if not isinstance(self.sharia_status, ShariaStatus):
            raise ValueError("sharia_status must be a ShariaStatus.")
        if not isinstance(self.evidence_confidence, (int, float)) or not 0 <= float(self.evidence_confidence) <= 1:
            raise ValueError("evidence_confidence must be a number between 0 and 1.")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")
