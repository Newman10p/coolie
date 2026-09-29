from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from research_room.models import Money


def _nonempty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ExpansionRequest:
    request_id: str
    business_domain: str
    idea: str
    required_capabilities: tuple[str, ...]
    expected_monthly_revenue: Money | None = None
    max_budget: Money | None = None
    risk_tolerance: Literal["low", "medium", "high"] = "medium"
    created_at: datetime = field(default_factory=_now_utc)

    def __post_init__(self) -> None:
        _nonempty(self.request_id, "request_id")
        _nonempty(self.business_domain, "business_domain")
        _nonempty(self.idea, "idea")
        if not isinstance(self.required_capabilities, tuple) or not self.required_capabilities:
            raise ValueError("required_capabilities must be a non-empty tuple.")
        if any(not isinstance(cap, str) or not cap.strip() for cap in self.required_capabilities):
            raise ValueError("required_capabilities must contain non-empty strings.")
        if self.expected_monthly_revenue is not None and not isinstance(self.expected_monthly_revenue, Money):
            raise ValueError("expected_monthly_revenue must be a Money value when provided.")
        if self.max_budget is not None and not isinstance(self.max_budget, Money):
            raise ValueError("max_budget must be a Money value when provided.")
        if self.risk_tolerance not in {"low", "medium", "high"}:
            raise ValueError("risk_tolerance must be low, medium, or high.")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")


@dataclass(frozen=True)
class CapabilityExtensionPlan:
    plan_id: str
    request_id: str
    business_domain: str
    currently_supported: tuple[str, ...]
    missing_capabilities: tuple[str, ...]
    required_agents: tuple[str, ...]
    required_tools: tuple[str, ...]
    required_connectors: tuple[str, ...]
    required_policies: tuple[str, ...]
    required_data_models: tuple[str, ...]
    estimated_cost: Money
    expected_revenue: Money | None
    test_plan: tuple[str, ...]
    reusability: Literal["temporary", "business_specific", "reusable"] = "business_specific"
    financially_viable: bool = True
    created_at: datetime = field(default_factory=_now_utc)

    def __post_init__(self) -> None:
        _nonempty(self.plan_id, "plan_id")
        _nonempty(self.request_id, "request_id")
        _nonempty(self.business_domain, "business_domain")
        if not isinstance(self.estimated_cost, Money):
            raise ValueError("estimated_cost must be a Money value.")
        if self.expected_revenue is not None and not isinstance(self.expected_revenue, Money):
            raise ValueError("expected_revenue must be a Money value when provided.")
        if self.reusability not in {"temporary", "business_specific", "reusable"}:
            raise ValueError("reusability must be temporary, business_specific, or reusable.")
        if not isinstance(self.financially_viable, bool):
            raise ValueError("financially_viable must be a boolean.")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")

    @property
    def projected_roi(self) -> float:
        if self.expected_revenue is None:
            return 0.0
        revenue = float(self.expected_revenue.amount)
        cost = float(self.estimated_cost.amount)
        if cost <= 0:
            return 0.0
        return ((revenue - cost) / cost) * 100.0
