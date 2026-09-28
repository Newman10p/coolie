"""Shared primitives for Sector 3 (Enactor).

Mirrors the shapes used by research_room.models without importing its internals,
so the two sectors stay independently deployable peers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from math import isfinite


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")


def _probability(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{field_name} must be a finite number between 0 and 1.")


class RiskSeverity(str, Enum):
    LOW = "low"; MEDIUM = "medium"; HIGH = "high"; CRITICAL = "critical"


@dataclass(frozen=True)
class Money:
    amount: float
    currency: str

    def __post_init__(self) -> None:
        if isinstance(self.amount, bool) or not isinstance(self.amount, (int, float)) or not isfinite(self.amount) or self.amount < 0:
            raise ValueError("Money amount must be a finite non-negative number.")
        if not isinstance(self.currency, str) or len(self.currency) != 3 or not self.currency.isalpha() or self.currency != self.currency.upper():
            raise ValueError("Money currency must be a three-letter uppercase currency code.")

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money) or other.currency != self.currency:
            raise ValueError("Can only add money of the same currency.")
        return Money(self.amount + other.amount, self.currency)


class ToolMode(str, Enum):
    """Document §7: capability modes ordered by blast radius."""
    READ = "read"; DRAFT = "draft"; WRITE = "write"; EXTERNAL_ACTION = "external_action"


MODE_ORDER = {ToolMode.READ: 0, ToolMode.DRAFT: 1, ToolMode.WRITE: 2, ToolMode.EXTERNAL_ACTION: 3}


class AgentStatus(str, Enum):
    """Document §12 result statuses."""
    SUCCESS = "success"; PARTIAL = "partial"; BLOCKED = "blocked"; FAILED = "failed"; AWAITING_APPROVAL = "awaiting_approval"


@dataclass(frozen=True)
class SuccessMetric:
    metric_id: str
    name: str
    target: float
    unit: str
    measurement_window_days: int = 7

    def __post_init__(self) -> None:
        _non_empty(self.metric_id, "metric_id"); _non_empty(self.name, "name"); _non_empty(self.unit, "unit")
        if isinstance(self.target, bool) or not isinstance(self.target, (int, float)) or not isfinite(self.target):
            raise ValueError("Metric target must be a finite number.")
        if isinstance(self.measurement_window_days, bool) or not isinstance(self.measurement_window_days, int) or self.measurement_window_days <= 0:
            raise ValueError("measurement_window_days must be a positive integer.")


@dataclass(frozen=True)
class StopCondition:
    condition_id: str
    description: str
    metric: str
    operator: str  # one of: < <= > >= ==
    threshold: float

    def __post_init__(self) -> None:
        _non_empty(self.condition_id, "condition_id"); _non_empty(self.description, "description"); _non_empty(self.metric, "metric")
        if self.operator not in {"<", "<=", ">", ">=", "=="}:
            raise ValueError("Stop condition operator must be one of < <= > >= ==.")
        if isinstance(self.threshold, bool) or not isinstance(self.threshold, (int, float)) or not isfinite(self.threshold):
            raise ValueError("Stop condition threshold must be a finite number.")

    def evaluate(self, observed: float) -> bool:
        if self.operator == "<": return observed < self.threshold
        if self.operator == "<=": return observed <= self.threshold
        if self.operator == ">": return observed > self.threshold
        if self.operator == ">=": return observed >= self.threshold
        return observed == self.threshold
