from __future__ import annotations

from research_room.models import Money

from .controller import FinanceReview, MoneyCalculatorController
from .models import ActivationProposal, SpendRecommendation


class MoneyCalculatorService:
    def __init__(self, controller: MoneyCalculatorController | None = None) -> None:
        self.controller = controller or MoneyCalculatorController()

    @staticmethod
    def health() -> dict[str, str]:
        return {"status": "ok"}

    def assess(self, proposal: ActivationProposal, *, budget_limit: Money | None = None) -> SpendRecommendation:
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
