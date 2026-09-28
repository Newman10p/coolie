"""Outcome & feedback models — document §5.8 (Measurement feeds Research/Strategy)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .shared import RiskSeverity, now_utc, _non_empty


class OutcomeVerdict(str, Enum):
    SUCCESS = "success"; PARTIAL = "partial"; FAILURE = "failure"; INVALIDATED = "invalidated"


@dataclass(frozen=True)
class BusinessMetricSnapshot:
    metric_id: str
    business_id: str
    execution_id: str | None
    name: str      # views | add_to_cart | checkout | purchases | inquiries | returns | refunds | ad_spend | search_rank | incidents | supplier_delays | support_volume | delivery_days
    value: float
    unit: str
    captured_at: datetime

    def __post_init__(self) -> None:
        for name in ("metric_id", "business_id", "name"): _non_empty(getattr(self, name), name)
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)): raise ValueError("Metric value must be numeric.")
        if self.captured_at.tzinfo is None: raise ValueError("captured_at must be timezone-aware.")


@dataclass(frozen=True)
class AnomalyDetection:
    anomaly_id: str
    execution_id: str
    metric: str
    observed: float
    expected: float
    severity: RiskSeverity
    suggested_action: str          # descriptive only; autonomous action requires a stop-condition match
    stop_condition_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("anomaly_id", "execution_id", "metric", "suggested_action"): _non_empty(getattr(self, name), name)
        if not isinstance(self.severity, RiskSeverity): raise ValueError("Anomaly severity must be a RiskSeverity.")


@dataclass(frozen=True)
class OutcomeReport:
    """Sent to Orchestrator AND back into the Research Room (§5.8, §9 phase 11)."""
    report_id: str
    execution_id: str
    business_id: str
    opportunity_id: str | None
    verdict: OutcomeVerdict
    metrics_achieved: tuple[dict[str, float], ...]
    assumptions_wrong: tuple[str, ...]
    lessons: tuple[str, ...]
    invalidation_conditions_observed: tuple[str, ...]
    reported_at: datetime = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        for name in ("report_id", "execution_id", "business_id"): _non_empty(getattr(self, name), name)
        if not isinstance(self.verdict, OutcomeVerdict): raise ValueError("verdict must be an OutcomeVerdict.")
        if self.reported_at.tzinfo is None: raise ValueError("reported_at must be timezone-aware.")
