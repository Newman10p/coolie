"""Typed, internal-only downstream handoff contracts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import OpportunityRecord, RecommendationPacket


@dataclass(frozen=True)
class FinancialEvaluationRequest:
    opportunity_id: str
    financial_input: object
    assumptions: tuple[str, ...]
    evidence_references: tuple[str, ...]


@dataclass(frozen=True)
class StrategyReviewRequest:
    opportunity_id: str
    customer_problem: str
    business_model: str
    risks: tuple[object, ...]
    validation_plan: tuple[str, ...]


class FinancialEvaluator(Protocol):
    def evaluate_financials(self, request: FinancialEvaluationRequest) -> dict[str, object]: ...


class StrategyReviewer(Protocol):
    def review_strategy(self, request: StrategyReviewRequest) -> dict[str, object]: ...


class OrchestratorSink(Protocol):
    def submit_recommendation(self, packet: RecommendationPacket) -> str: ...


def financial_request(opportunity: OpportunityRecord) -> FinancialEvaluationRequest:
    return FinancialEvaluationRequest(opportunity.opportunity_id, opportunity.financial_input, tuple(opportunity.open_questions), tuple(item.evidence_id for item in opportunity.demand_evidence))


def strategy_request(opportunity: OpportunityRecord) -> StrategyReviewRequest:
    return StrategyReviewRequest(opportunity.opportunity_id, opportunity.customer_problem, opportunity.business_model, tuple(opportunity.risks), ("Define success metric.", "Stop if validation budget is exhausted."))
