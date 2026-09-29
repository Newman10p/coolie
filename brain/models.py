"""Provider-neutral contracts for Coolie's Brain control plane."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from math import isfinite
from typing import Any

from research_room.models import Money


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _required(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required.")


class BrainOperation(str, Enum):
    COMPLETE = "complete"
    EXTRACT = "extract"
    CLASSIFY = "classify"
    SUMMARIZE = "summarize"
    COMPARE = "compare"
    GENERATE_VARIANTS = "generate_variants"
    EMBED = "embed"
    RETRIEVE = "retrieve"
    MEMORY_WRITE = "memory_write"
    MEMORY_FORGET = "memory_forget"
    CREATE_PLAN = "create_plan"
    DECOMPOSE_TASK = "decompose_task"
    DELEGATE_TASK = "delegate_task"


class DataSensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"


@dataclass(frozen=True)
class AgentDefinition:
    agent_id: str
    sector: str
    role: str
    allowed_operations: frozenset[BrainOperation]
    allowed_models: frozenset[str]
    allowed_memory_namespaces: frozenset[str]
    max_tokens_per_task: int
    max_cost_per_task: Money
    max_delegation_depth: int = 0
    allowed_delegate_types: frozenset[str] = frozenset()
    requires_approval_for_delegation: bool = True
    maximum_sensitivity: DataSensitivity = DataSensitivity.INTERNAL
    status: str = "active"

    def __post_init__(self) -> None:
        for name in ("agent_id", "sector", "role"):
            _required(getattr(self, name), name)
        if any(not isinstance(values, frozenset) for values in (
            self.allowed_operations, self.allowed_models, self.allowed_memory_namespaces, self.allowed_delegate_types,
        )):
            raise ValueError("Agent grants must be immutable frozensets.")
        if not self.allowed_operations:
            raise ValueError("Agents must be granted at least one operation.")
        if any(not isinstance(operation, BrainOperation) for operation in self.allowed_operations):
            raise ValueError("Agent operations must use registered BrainOperation values.")
        if any(not isinstance(value, str) or not value.strip() for value in self.allowed_models | self.allowed_memory_namespaces | self.allowed_delegate_types):
            raise ValueError("Agent model and namespace grants must be non-empty strings.")
        if not isinstance(self.maximum_sensitivity, DataSensitivity):
            raise ValueError("maximum_sensitivity must be a DataSensitivity.")
        if not isinstance(self.requires_approval_for_delegation, bool):
            raise ValueError("requires_approval_for_delegation must be a boolean.")
        if isinstance(self.max_tokens_per_task, bool) or not isinstance(self.max_tokens_per_task, int) or self.max_tokens_per_task <= 0:
            raise ValueError("max_tokens_per_task must be a positive integer.")
        if isinstance(self.max_delegation_depth, bool) or not isinstance(self.max_delegation_depth, int) or self.max_delegation_depth < 0:
            raise ValueError("max_delegation_depth must be a non-negative integer.")
        if self.status not in {"active", "paused", "revoked"}:
            raise ValueError("Agent status must be active, paused, or revoked.")


@dataclass(frozen=True)
class ModelProfile:
    profile_id: str
    provider_id: str
    model_name: str
    capabilities: frozenset[BrainOperation]
    allowed_sectors: frozenset[str]
    context_window: int
    cost_per_1k_input_tokens: float
    cost_per_1k_output_tokens: float
    reliability_score: float = 1.0
    cost_class: str = "standard"
    currency: str = "USD"

    def __post_init__(self) -> None:
        for name in ("profile_id", "provider_id", "model_name"):
            _required(getattr(self, name), name)
        if isinstance(self.context_window, bool) or not isinstance(self.context_window, int) or self.context_window <= 0:
            raise ValueError("context_window must be a positive integer.")
        if not self.capabilities or not self.allowed_sectors:
            raise ValueError("Model profiles require capabilities and allowed sectors.")
        if not isinstance(self.capabilities, frozenset) or not isinstance(self.allowed_sectors, frozenset):
            raise ValueError("Model capabilities and sector grants must be immutable frozensets.")
        if any(not isinstance(value, BrainOperation) for value in self.capabilities):
            raise ValueError("Model capabilities must use registered BrainOperation values.")
        if any(not isinstance(sector, str) or not sector.strip() for sector in self.allowed_sectors):
            raise ValueError("Model profile sectors must be non-empty strings.")
        if len(self.currency) != 3 or not self.currency.isalpha() or self.currency != self.currency.upper():
            raise ValueError("Model profile currency must be a three-letter uppercase code.")
        costs = (self.cost_per_1k_input_tokens, self.cost_per_1k_output_tokens)
        if any(isinstance(cost, bool) or not isinstance(cost, (int, float)) or not isfinite(cost) or cost < 0 for cost in costs):
            raise ValueError("Model token costs must be finite non-negative numbers.")
        if isinstance(self.reliability_score, bool) or not isinstance(self.reliability_score, (int, float)) or not isfinite(self.reliability_score) or not 0 <= self.reliability_score <= 1:
            raise ValueError("reliability_score must be between 0 and 1.")


@dataclass(frozen=True)
class InferenceRequest:
    request_id: str
    agent_id: str
    sector: str
    task_id: str
    operation: BrainOperation
    input: Any
    max_tokens: int
    max_cost: Money
    model_profile: str | None = None
    schema_name: str | None = None
    context_refs: tuple[str, ...] = ()
    timeout_ms: int = 60_000

    def __post_init__(self) -> None:
        for name in ("request_id", "agent_id", "sector", "task_id"):
            _required(getattr(self, name), name)
        if not isinstance(self.operation, BrainOperation):
            raise ValueError("operation must be a BrainOperation.")
        if isinstance(self.max_tokens, bool) or not isinstance(self.max_tokens, int) or self.max_tokens <= 0:
            raise ValueError("max_tokens must be a positive integer.")
        if isinstance(self.timeout_ms, bool) or not isinstance(self.timeout_ms, int) or self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be a positive integer.")
        if self.model_profile is not None:
            _required(self.model_profile, "model_profile")
        if self.schema_name is not None:
            _required(self.schema_name, "schema_name")
        if not isinstance(self.context_refs, tuple) or any(not isinstance(reference, str) or not reference.strip() for reference in self.context_refs):
            raise ValueError("context_refs must be a tuple of non-empty strings.")
        if not self.max_cost.amount > 0:
            raise ValueError("max_cost must be positive.")


@dataclass(frozen=True)
class ProviderRequest:
    request_id: str
    model: str
    operation: BrainOperation
    input: Any
    context: tuple[dict[str, Any], ...]
    max_tokens: int
    timeout_ms: int
    schema: dict[str, Any] | None = None


@dataclass(frozen=True)
class ProviderResponse:
    output: Any
    input_tokens: int
    output_tokens: int

    def __post_init__(self) -> None:
        for name in ("input_tokens", "output_tokens"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")


@dataclass(frozen=True)
class UsageRecord:
    request_id: str
    agent_id: str
    sector: str
    task_id: str
    provider_id: str
    model_profile: str
    input_tokens: int
    output_tokens: int
    cost: Money
    timestamp: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class InferenceResponse:
    request_id: str
    status: str
    output: Any
    warnings: tuple[str, ...]
    usage: UsageRecord
    model_profile: str
    audit_id: str


@dataclass(frozen=True)
class InferenceAudit:
    audit_id: str
    request_id: str
    agent_id: str
    sector: str
    task_id: str
    context_refs: tuple[str, ...]
    operation: BrainOperation
    model_profile: str
    input_hash: str
    output_hash: str | None
    status: str
    reason: str | None
    timestamp: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class AgentSession:
    session_id: str
    agent_id: str
    sector: str
    task_id: str
    allowed_operations: frozenset[BrainOperation]
    allowed_memory_namespaces: frozenset[str]
    token_limit: int
    cost_limit: Money
    expires_at: datetime
    status: str = "active"


@dataclass(frozen=True)
class SessionGrant:
    session: AgentSession
    token: str = field(repr=False)


@dataclass(frozen=True)
class ContextItem:
    reference: str
    namespace: str
    content: Any
    sensitivity: DataSensitivity
    source_reference: str
    created_at: datetime
    untrusted: bool = True


@dataclass(frozen=True)
class ContextPackage:
    context_id: str
    task_id: str
    items: tuple[ContextItem, ...]
    source_refs: tuple[str, ...]
    sensitivity: DataSensitivity
    estimated_tokens: int
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    namespace: str
    content: Any
    sensitivity: DataSensitivity
    source_reference: str
    created_at: datetime = field(default_factory=utc_now)
    expires_at: datetime | None = None

    def __post_init__(self) -> None:
        for name in ("memory_id", "namespace", "source_reference"):
            _required(getattr(self, name), name)
        if not isinstance(self.sensitivity, DataSensitivity):
            raise ValueError("sensitivity must be a DataSensitivity.")
        if self.created_at.tzinfo is None or (self.expires_at is not None and self.expires_at.tzinfo is None):
            raise ValueError("Memory timestamps must be timezone-aware.")
        json.dumps(self.content, allow_nan=False)


@dataclass(frozen=True)
class BrainEvent:
    event_id: str
    event_type: str
    source: str
    payload: dict[str, Any]
    correlation_id: str
    sensitivity: DataSensitivity
    timestamp: datetime = field(default_factory=utc_now)


@dataclass(frozen=True)
class Delegation:
    delegation_id: str
    parent_agent_id: str
    target_agent_type: str
    task: str
    context_refs: tuple[str, ...]
    budget: Money
    deadline: datetime
    depth: int
    expected_schema: str
    status: str
    approval_required: bool
    result: Any = None


@dataclass(frozen=True)
class DelegationRequest:
    delegation_id: str
    requesting_agent_id: str
    target_agent_type: str
    task: str
    context_refs: tuple[str, ...]
    budget: Money
    deadline: datetime
    max_depth: int
    expected_schema: str
    approval_required: bool

    def __post_init__(self) -> None:
        for name in ("delegation_id", "requesting_agent_id", "target_agent_type", "task", "expected_schema"):
            _required(getattr(self, name), name)
        if not isinstance(self.context_refs, tuple) or any(not isinstance(reference, str) or not reference.strip() for reference in self.context_refs):
            raise ValueError("Delegation context_refs must be a tuple of non-empty strings.")
        if isinstance(self.max_depth, bool) or not isinstance(self.max_depth, int) or self.max_depth <= 0:
            raise ValueError("max_depth must be a positive integer.")
        if not isinstance(self.approval_required, bool):
            raise ValueError("approval_required must be a boolean.")
