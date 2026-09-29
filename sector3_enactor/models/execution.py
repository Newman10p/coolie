"""Execution domain models — document §4.1, §4.2."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .shared import Money, RiskSeverity, StopCondition, SuccessMetric, now_utc, _non_empty, _probability


class ExecutionStatus(str, Enum):
    """All 15 lifecycle states from document §4.2."""
    RECEIVED = "received"; VALIDATING = "validating"; PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"; PREPARING_RESOURCES = "preparing_resources"
    EXECUTING = "executing"; MONITORING = "monitoring"; PAUSED = "paused"
    ROLLING_BACK = "rolling_back"; COMPLETED = "completed"; PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"; CANCELLED = "cancelled"; REJECTED = "rejected"; ARCHIVED = "archived"


class TaskLifecycleStatus(str, Enum):
    PENDING = "pending"; READY = "ready"; RUNNING = "running"; COMPLETED = "completed"
    BLOCKED = "blocked"; FAILED = "failed"; CANCELLED = "cancelled"; WAITING_HUMAN = "waiting_human"


@dataclass(frozen=True)
class ActionRequest:
    action_id: str
    tool: str
    arguments: dict[str, Any]
    risk_level: RiskSeverity
    required_approval_level: str
    reversible: bool
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        _non_empty(self.action_id, "action_id"); _non_empty(self.tool, "tool")
        if not isinstance(self.risk_level, RiskSeverity): raise ValueError("risk_level must be a RiskSeverity.")
        if not isinstance(self.arguments, dict): raise ValueError("Action arguments must be a mapping.")


@dataclass(frozen=True)
class ActionResult:
    action_id: str
    status: str  # success | failed | denied | blocked
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    external_operation_id: str | None = None

    def __post_init__(self) -> None:
        _non_empty(self.action_id, "action_id")
        if self.status not in {"success", "failed", "denied", "blocked"}: raise ValueError("ActionResult status is invalid.")


@dataclass(frozen=True)
class ArtifactReference:
    artifact_key: str
    content_hash: str
    content_type: str

    def __post_init__(self) -> None:
        _non_empty(self.artifact_key, "artifact_key"); _non_empty(self.content_hash, "content_hash")


@dataclass(frozen=True)
class ExecutionMetric:
    metric_id: str
    name: str
    value: float
    unit: str
    recorded_at: datetime

    def __post_init__(self) -> None:
        _non_empty(self.name, "name")
        if self.recorded_at.tzinfo is None: raise ValueError("recorded_at must be timezone-aware.")


@dataclass(frozen=True)
class Escalation:
    escalation_id: str
    execution_id: str
    reason: str
    severity: RiskSeverity
    routed_to: str  # human | finance | orchestrator | strategy_manager
    approval_request_id: str | None = None

    @property
    def approval_id(self) -> str | None:
        return self.approval_request_id

    @approval_id.setter
    def approval_id(self, value: str | None) -> None:
        object.__setattr__(self, "approval_request_id", value)

    def __repr__(self) -> str:
        return (
            "Escalation("
            f"escalation_id={self.escalation_id!r}, "
            f"execution_id={self.execution_id!r}, "
            f"reason={self.reason!r}, "
            f"severity={self.severity!r}, "
            f"routed_to={self.routed_to!r}, "
            f"approval_id={self.approval_request_id!r}"
            ")"
        )

    __str__ = __repr__

    def __post_init__(self) -> None:
        _non_empty(self.reason, "reason"); _non_empty(self.routed_to, "routed_to")
        if self.routed_to not in {"human", "finance", "orchestrator", "strategy_manager"}:
            raise ValueError("Escalation must route to human, finance, orchestrator or strategy_manager.")


@dataclass
class ExecutionRequest:
    execution_id: str
    business_id: str
    plan_id: str
    objective: str
    opportunity_id: str | None = None
    strategy_id: str | None = None
    requested_by: str = "orchestrator"
    constraints: tuple[str, ...] = ()
    audience: str | None = None
    approved_claims: tuple[str, ...] = ()
    required_assets: tuple[str, ...] = ()
    success_metrics: tuple[SuccessMetric, ...] = ()
    stop_conditions: tuple[StopCondition, ...] = ()
    budget: Money | None = None
    maximum_automatic_spend: Money | None = None
    approval_requirements: tuple[str, ...] = ()
    risk_flags: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=now_utc)
    status: ExecutionStatus = ExecutionStatus.RECEIVED

    def __post_init__(self) -> None:
        for name in ("execution_id", "business_id", "plan_id", "objective", "requested_by"):
            _non_empty(getattr(self, name), name)
        if self.created_at.tzinfo is None: raise ValueError("created_at must be timezone-aware.")
        if not isinstance(self.status, ExecutionStatus): raise ValueError("status must be an ExecutionStatus.")
        if self.budget is not None and not isinstance(self.budget, Money): raise ValueError("budget must be Money.")
        if self.maximum_automatic_spend is not None and not isinstance(self.maximum_automatic_spend, Money):
            raise ValueError("maximum_automatic_spend must be Money.")
        if self.budget and self.maximum_automatic_spend and self.maximum_automatic_spend.currency != self.budget.currency:
            raise ValueError("Budget and automatic-spend cap must share a currency.")
        if self.budget and self.maximum_automatic_spend and self.maximum_automatic_spend.amount > self.budget.amount:
            raise ValueError("Automatic spend cap cannot exceed the total budget.")


@dataclass
class ExecutionResult:
    execution_id: str
    status: ExecutionStatus
    artifacts: tuple[ArtifactReference, ...] = ()
    actions: tuple[ActionResult, ...] = ()
    metrics: tuple[ExecutionMetric, ...] = ()
    escalations: tuple[Escalation, ...] = ()
    summary: str = ""
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        _non_empty(self.execution_id, "execution_id")
        if not isinstance(self.status, ExecutionStatus): raise ValueError("status must be an ExecutionStatus.")
