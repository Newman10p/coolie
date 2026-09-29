from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Literal

from research_room.models import Money


def _non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")


def _probability(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{field_name} must be a finite number between 0 and 1.")


@dataclass(frozen=True)
class ActivationProposal:
    proposal_id: str
    objective: str
    owner: str
    planned_spend: Money
    expected_revenue: Money
    time_horizon_days: int
    confidence: float
    risk_tolerance: Literal["low", "medium", "high"] = "medium"
    required_margin_percent: float = 0.0
    approval_required: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _non_empty(self.proposal_id, "proposal_id")
        _non_empty(self.objective, "objective")
        _non_empty(self.owner, "owner")
        if not isinstance(self.planned_spend, Money):
            raise ValueError("planned_spend must be a Money value.")
        if self.planned_spend.amount <= 0:
            raise ValueError("planned_spend must be greater than zero.")
        if not isinstance(self.expected_revenue, Money):
            raise ValueError("expected_revenue must be a Money value.")
        if self.expected_revenue.amount < 0:
            raise ValueError("expected_revenue cannot be negative.")
        if isinstance(self.time_horizon_days, bool) or not isinstance(self.time_horizon_days, int) or self.time_horizon_days <= 0:
            raise ValueError("time_horizon_days must be a positive integer.")
        _probability(self.confidence, "confidence")
        if self.risk_tolerance not in {"low", "medium", "high"}:
            raise ValueError("risk_tolerance must be low, medium, or high.")
        if isinstance(self.required_margin_percent, bool) or not isinstance(self.required_margin_percent, (int, float)) or not isfinite(self.required_margin_percent):
            raise ValueError("required_margin_percent must be a finite number.")
        if not 0 <= float(self.required_margin_percent) <= 100:
            raise ValueError("required_margin_percent must be between 0 and 100.")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")

    @property
    def projected_roi(self) -> float:
        spent = float(self.planned_spend.amount)
        revenue = float(self.expected_revenue.amount)
        if spent <= 0:
            return 0.0
        return ((revenue - spent) / spent) * 100.0

    @property
    def projected_margin(self) -> float:
        revenue = float(self.expected_revenue.amount)
        if revenue <= 0:
            return 0.0
        return ((revenue - float(self.planned_spend.amount)) / revenue) * 100.0


class ActivationDecisionCode(str, Enum):
    APPROVE = "approve"
    HOLD = "hold"
    PAUSE = "pause"
    REJECT = "reject"
    REQUEST_OWNER_APPROVAL = "request_owner_approval"
    SCALE = "scale"


@dataclass(frozen=True)
class SpendRecommendation:
    recommendation_id: str
    proposal_id: str
    code: ActivationDecisionCode
    summary: str
    reason: str
    recommended_spend: Money
    expected_roi: float
    payback_days: int
    approval_required: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _non_empty(self.recommendation_id, "recommendation_id")
        _non_empty(self.proposal_id, "proposal_id")
        _non_empty(self.summary, "summary")
        _non_empty(self.reason, "reason")
        if not isinstance(self.code, ActivationDecisionCode):
            raise ValueError("code must be an ActivationDecisionCode.")
        if not isinstance(self.recommended_spend, Money):
            raise ValueError("recommended_spend must be a Money value.")
        if isinstance(self.payback_days, bool) or not isinstance(self.payback_days, int) or self.payback_days < 0:
            raise ValueError("payback_days must be a non-negative integer.")
        if not isinstance(self.approval_required, bool):
            raise ValueError("approval_required must be a boolean.")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")


__all__ = [
    "ActivationDecisionCode",
    "ActivationProposal",
    "SpendRecommendation",
]
