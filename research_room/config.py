"""Versioned, validated configuration for the Research Room."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from math import isfinite
from typing import Any

from .evaluation import DEFAULT_WEIGHTS
from .models import Money


@dataclass(frozen=True)
class ScoringModel:
    version: str
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    evidence_threshold: float = 0.6

    def __post_init__(self) -> None:
        if not self.version.strip(): raise ValueError("Scoring model version is required.")
        if set(self.weights) != set(DEFAULT_WEIGHTS) or round(sum(self.weights.values()), 8) != 1:
            raise ValueError("Scoring weights must contain every component and sum to 1.")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0 for value in self.weights.values()):
            raise ValueError("Scoring weights must be finite non-negative numbers.")
        if not 0 <= self.evidence_threshold <= 1: raise ValueError("Evidence threshold must be between 0 and 1.")


@dataclass(frozen=True)
class BudgetPolicy:
    version: str
    model_token_limit: int
    api_request_limit: int
    web_request_limit: int
    paid_source_limit: Money | None
    enactor_request_limit: int

    def __post_init__(self) -> None:
        if not self.version.strip(): raise ValueError("Budget policy version is required.")
        limits = (self.model_token_limit, self.api_request_limit, self.web_request_limit, self.enactor_request_limit)
        if any(isinstance(limit, bool) or not isinstance(limit, int) or limit < 0 for limit in limits):
            raise ValueError("Budget limits must be non-negative integers.")


@dataclass(frozen=True)
class AgentPolicy:
    agent_type: str
    allowed_permissions: tuple[str, ...]
    supported_business_models: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.agent_type.strip(): raise ValueError("agent_type is required.")
        if any(not value.startswith("research:") for value in self.allowed_permissions):
            raise ValueError("Agent permissions must use the research: namespace.")


@dataclass(frozen=True)
class SectorConfiguration:
    version: str
    scoring_model: ScoringModel
    budget_policy: BudgetPolicy
    agent_policies: tuple[AgentPolicy, ...]
    source_quality: dict[str, float]
    retention_days: int

    def __post_init__(self) -> None:
        if not self.version.strip(): raise ValueError("Sector configuration version is required.")
        if len({agent.agent_type for agent in self.agent_policies}) != len(self.agent_policies): raise ValueError("Agent policies must be unique by agent type.")
        if isinstance(self.retention_days, bool) or not isinstance(self.retention_days, int) or self.retention_days <= 0: raise ValueError("retention_days must be a positive integer.")
        if any(source not in {"web", "api", "marketplace", "supplier", "internal"} or isinstance(score, bool) or not isinstance(score, (int, float)) or not isfinite(score) or not 0 <= score <= 1 for source, score in self.source_quality.items()):
            raise ValueError("Source quality values must use supported sources and values between 0 and 1.")

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, default=str, separators=(",", ":"))

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "SectorConfiguration":
        scoring = ScoringModel(**value["scoring_model"])
        budget_data = dict(value["budget_policy"])
        if budget_data.get("paid_source_limit") is not None: budget_data["paid_source_limit"] = Money(**budget_data["paid_source_limit"])
        agents = tuple(AgentPolicy(**agent) for agent in value["agent_policies"])
        return cls(value["version"], scoring, BudgetPolicy(**budget_data), agents, dict(value["source_quality"]), value["retention_days"])
