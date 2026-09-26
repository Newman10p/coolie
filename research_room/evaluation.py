from __future__ import annotations

from dataclasses import dataclass
from .evidence import important_claims_have_sources
from .models import Money, OpportunityRecord, RiskSeverity


@dataclass(frozen=True)
class Evaluation:
    score: float
    recommendation: str
    reasons: tuple[str, ...]


DEFAULT_WEIGHTS = {"demand": .20, "competition": .15, "margin": .20, "fulfillment": .15, "marketing": .10, "strategy": .10, "evidence": .10}


def _currencies(opportunity: OpportunityRecord, capital_limit: Money | None) -> set[str]:
    costs = opportunity.financial_input
    values = (costs.selling_price, costs.product_cost, costs.shipping_cost, costs.acquisition_cost, capital_limit)
    return {value.currency for value in values if value is not None}


def evaluate(opportunity: OpportunityRecord, *, required_margin_percent: float | None, capital_limit: Money | None, evidence_threshold: float = .6, weights: dict[str, float] | None = None) -> Evaluation:
    weights = weights or DEFAULT_WEIGHTS
    if set(weights) != set(DEFAULT_WEIGHTS) or round(sum(weights.values()), 8) != 1:
        raise ValueError("Scoring weights must include each score component and sum to 1.")
    if not 0 <= evidence_threshold <= 1: raise ValueError("evidence_threshold must be between 0 and 1.")
    if required_margin_percent is not None and not 0 <= required_margin_percent <= 100: raise ValueError("required_margin_percent must be between 0 and 100.")
    missing = set(weights) - set(opportunity.scores)
    score = sum(weights[key] * opportunity.scores.get(key, 0) for key in weights)
    if any(risk.severity is RiskSeverity.CRITICAL for risk in opportunity.risks):
        return Evaluation(score, "reject", ("Critical risk requires rejection or human review.",))
    if missing:
        return Evaluation(score, "research_more", (f"Missing score components: {', '.join(sorted(missing))}.",))
    if not important_claims_have_sources(opportunity.demand_evidence) or opportunity.confidence < evidence_threshold:
        return Evaluation(score, "research_more", ("Evidence confidence or source coverage is below threshold.",))
    costs = opportunity.financial_input
    if not costs.selling_price or not costs.product_cost:
        return Evaluation(score, "research_more", ("Selling price or product cost is missing.",))
    currencies = _currencies(opportunity, capital_limit)
    if len(currencies) != 1:
        return Evaluation(score, "research_more", ("Financial inputs and capital limit must use one normalized currency.",))
    total_cost = costs.product_cost.amount + (costs.shipping_cost.amount if costs.shipping_cost else 0) + (costs.acquisition_cost.amount if costs.acquisition_cost else 0)
    margin = (costs.selling_price.amount - total_cost) / costs.selling_price.amount * 100
    if required_margin_percent is not None and margin < required_margin_percent:
        return Evaluation(score, "reject", (f"Expected margin {margin:.1f}% is below the mission requirement.",))
    if capital_limit is not None and total_cost > capital_limit.amount:
        return Evaluation(score, "request_approval", ("Estimated unit cost exceeds the mission capital limit.",))
    if costs.acquisition_cost is None:
        return Evaluation(score, "run_validation", ("Customer acquisition cost is unknown; validate before commitment.",))
    return Evaluation(score, "run_validation", ("Candidate passed preliminary research gates.",))
