from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any, Literal


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")


def _probability(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{field_name} must be a finite number between 0 and 1.")


class MissionStatus(str, Enum):
    RECEIVED = "received"; VALIDATING = "validating"; PLANNING = "planning"
    RESEARCHING = "researching"; VERIFYING = "verifying"; MODELING = "modeling"
    STRATEGIZING = "strategizing"; WAITING_FOR_APPROVAL = "waiting_for_approval"
    SUBMITTED = "submitted"; COMPLETED = "completed"; PAUSED = "paused"
    FAILED = "failed"; ARCHIVED = "archived"; CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    PENDING = "pending"; READY = "ready"; RUNNING = "running"; COMPLETED = "completed"
    BLOCKED = "blocked"; FAILED = "failed"; CANCELLED = "cancelled"


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


@dataclass(frozen=True)
class SourcePolicy:
    allowed_source_types: frozenset[str] = frozenset({"web", "api", "marketplace", "supplier", "internal"})
    allow_paid_sources: bool = False

    def __post_init__(self) -> None:
        allowed = {"web", "api", "marketplace", "supplier", "internal"}
        if not self.allowed_source_types or not self.allowed_source_types <= allowed:
            raise ValueError("Source policy must contain only supported source types.")


@dataclass
class ResearchMission:
    mission_id: str
    objective: str
    requested_by: Literal["orchestrator", "strategy_manager", "human"]
    markets: list[str]
    business_models: list[str]
    risk_tolerance: Literal["low", "medium", "high"]
    required_evidence_level: Literal["basic", "standard", "high"]
    allowed_sources: SourcePolicy = field(default_factory=SourcePolicy)
    capital_limit: Money | None = None
    time_limit_days: int | None = None
    required_margin_percent: float | None = None
    created_at: datetime = field(default_factory=now_utc)
    status: MissionStatus = MissionStatus.RECEIVED

    def __post_init__(self) -> None:
        _non_empty(self.mission_id, "mission_id"); _non_empty(self.objective, "objective")
        if self.requested_by not in {"orchestrator", "strategy_manager", "human"}: raise ValueError("requested_by is invalid.")
        if self.risk_tolerance not in {"low", "medium", "high"}: raise ValueError("risk_tolerance is invalid.")
        if self.required_evidence_level not in {"basic", "standard", "high"}: raise ValueError("required_evidence_level is invalid.")
        if not self.markets or not self.business_models: raise ValueError("missions require at least one market and business model.")
        if any(not isinstance(value, str) or not value.strip() for value in self.markets + self.business_models): raise ValueError("markets and business_models must contain non-empty strings.")
        if self.time_limit_days is not None and (isinstance(self.time_limit_days, bool) or not isinstance(self.time_limit_days, int) or self.time_limit_days <= 0): raise ValueError("time_limit_days must be a positive integer.")
        if self.required_margin_percent is not None and (isinstance(self.required_margin_percent, bool) or not isinstance(self.required_margin_percent, (int, float)) or not isfinite(self.required_margin_percent) or not 0 <= self.required_margin_percent <= 100): raise ValueError("required_margin_percent must be between 0 and 100.")
        if not isinstance(self.status, MissionStatus): raise ValueError("status must be a MissionStatus.")
        if self.created_at.tzinfo is None: raise ValueError("created_at must be timezone-aware.")


@dataclass
class ResearchTask:
    task_id: str
    mission_id: str
    agent_type: str
    objective: str
    dependencies: list[str]
    allowed_tools: list[str]
    output_schema: str
    timeout_seconds: int
    maximum_retries: int = 1
    priority: int = 0
    required_evidence_threshold: float = 0.0
    budget_limit: Money | None = None
    required: bool = True
    status: TaskStatus = TaskStatus.PENDING
    attempts: int = 0
    blocked_reason: str | None = None
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        for name in ("task_id", "mission_id", "agent_type", "objective", "output_schema"): _non_empty(getattr(self, name), name)
        if self.task_id in self.dependencies: raise ValueError("A task cannot depend on itself.")
        if len(set(self.dependencies)) != len(self.dependencies): raise ValueError("Task dependencies must be unique.")
        if any(not isinstance(item, str) or not item.strip() for item in self.dependencies + self.allowed_tools): raise ValueError("Dependencies and tools must be non-empty strings.")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, int) or self.timeout_seconds <= 0: raise ValueError("timeout_seconds must be a positive integer.")
        if isinstance(self.maximum_retries, bool) or not isinstance(self.maximum_retries, int) or self.maximum_retries < 0: raise ValueError("maximum_retries must be a non-negative integer.")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int): raise ValueError("priority must be an integer.")
        _probability(self.required_evidence_threshold, "required_evidence_threshold")
        if not isinstance(self.status, TaskStatus): raise ValueError("status must be a TaskStatus.")


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    source_type: Literal["web", "api", "marketplace", "supplier", "internal"]
    source_reference: str
    retrieved_at: datetime
    claim: str
    evidence_type: Literal["observed", "calculated", "inferred"]
    confidence: float
    freshness: Literal["current", "aging", "stale", "unknown"]
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _non_empty(self.evidence_id, "evidence_id"); _non_empty(self.source_reference, "source_reference"); _non_empty(self.claim, "claim")
        if self.source_type not in {"web", "api", "marketplace", "supplier", "internal"}: raise ValueError("source_type is invalid.")
        if self.evidence_type not in {"observed", "calculated", "inferred"}: raise ValueError("evidence_type is invalid.")
        if self.freshness not in {"current", "aging", "stale", "unknown"}: raise ValueError("freshness is invalid.")
        if self.retrieved_at.tzinfo is None: raise ValueError("retrieved_at must be timezone-aware.")
        _probability(self.confidence, "Evidence confidence")


@dataclass(frozen=True)
class Risk:
    category: str
    severity: RiskSeverity
    description: str
    mitigation: str | None = None

    def __post_init__(self) -> None:
        _non_empty(self.category, "category"); _non_empty(self.description, "description")
        if not isinstance(self.severity, RiskSeverity): raise ValueError("severity must be a RiskSeverity.")


@dataclass(frozen=True)
class FinancialInput:
    selling_price: Money | None
    product_cost: Money | None
    shipping_cost: Money | None
    acquisition_cost: Money | None = None


@dataclass
class OpportunityRecord:
    opportunity_id: str
    mission_id: str
    name: str
    business_model: str
    customer_problem: str
    demand_evidence: list[Evidence]
    risks: list[Risk]
    financial_input: FinancialInput
    confidence: float
    status: str = "draft"
    scores: dict[str, float] = field(default_factory=dict)
    open_questions: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for name in ("opportunity_id", "mission_id", "name", "business_model", "customer_problem", "status"): _non_empty(getattr(self, name), name)
        _probability(self.confidence, "Opportunity confidence")
        for component, score in self.scores.items():
            _non_empty(component, "score component")
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not isfinite(score) or not 0 <= score <= 100: raise ValueError("Opportunity scores must be finite numbers between 0 and 100.")


@dataclass(frozen=True)
class RecommendationPacket:
    opportunity_id: str
    recommendation: Literal["reject", "archive", "research_more", "run_validation", "request_approval", "limited_launch"]
    reasons: tuple[str, ...]
    evidence_references: tuple[str, ...]
    assumptions: tuple[str, ...]
    required_approvals: tuple[str, ...]
    risks: tuple[Risk, ...]
    invalidation_conditions: tuple[str, ...]


@dataclass(frozen=True)
class AgentResult:
    status: Literal["success", "partial", "blocked", "failed"]
    data: dict[str, Any] | None
    evidence: tuple[Evidence, ...]
    warnings: tuple[str, ...]
    missing_information: tuple[str, ...]
    confidence: float
    tool_calls: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if self.status not in {"success", "partial", "blocked", "failed"}: raise ValueError("Agent result status is invalid.")
        _probability(self.confidence, "Agent result confidence")
