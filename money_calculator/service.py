from __future__ import annotations

from reliability import ReliabilityRuntime, default_reliability_runtime

from research_room.models import Money

from .controller import FinanceReview, MoneyCalculatorController
from .models import ActivationProposal, SpendRecommendation


class MoneyCalculatorService:
    def __init__(
        self,
        controller: MoneyCalculatorController | None = None,
        *,
        reliability: ReliabilityRuntime | None = None,
    ) -> None:
        self.controller = controller or MoneyCalculatorController()
        self.reliability = reliability or default_reliability_runtime()

    def health(self) -> dict[str, object]:
        paused = self.reliability.failsafe.paused
        return {
            "service": "money-calculator",
            "status": "paused" if paused else "ok",
            "ready": not paused,
            "reason": self.reliability.failsafe.reason,
        }

    def assess(self, proposal: ActivationProposal, *, budget_limit: Money | None = None) -> SpendRecommendation:
        self.reliability.ensure_work_allowed("financial activation assessment")
        review = self.controller.assess(proposal, budget_limit=budget_limit)
        return review.decision

    def history(self, proposal_id: str) -> tuple[SpendRecommendation, ...]:
        return self.controller.history(proposal_id)

    def last_recommendation(self, proposal_id: str) -> SpendRecommendation:
        recommendations = self.history(proposal_id)
        if not recommendations:
            raise ValueError(f"No finance recommendation history found for {proposal_id}.")
        return recommendations[-1]


__all__ = ["MoneyCalculatorService"]
