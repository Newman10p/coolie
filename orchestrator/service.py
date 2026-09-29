from __future__ import annotations

from typing import Any

from .controller import OrchestratorController
from .models import DecisionCode, EnactorMandate, OrchestratorDecision, OwnerObjective, ShariaStatus


class OrchestratorService:
    def __init__(self, controller: OrchestratorController | None = None) -> None:
        self.controller = controller or OrchestratorController()

    def create_objective(self, objective: OwnerObjective) -> OwnerObjective:
        return objective

    def decide(
        self,
        objective: OwnerObjective,
        *,
        sharia_status: ShariaStatus,
        evidence_confidence: float,
        budget_approved: bool,
        operational_risk: str,
        approved_actions: tuple[str, ...] | None = None,
    ) -> OrchestratorDecision:
        review = self.controller.review_objective(
            objective,
            sharia_status=sharia_status,
            evidence_confidence=evidence_confidence,
            budget_approved=budget_approved,
            operational_risk=operational_risk,
            approved_actions=approved_actions,
        )
        return review.decision

    def issue_mandate(
        self,
        objective: OwnerObjective,
        *,
        sharia_status: ShariaStatus,
        evidence_confidence: float,
        budget_approved: bool,
        operational_risk: str,
        approved_actions: tuple[str, ...] | None = None,
    ) -> EnactorMandate:
        review = self.controller.review_objective(
            objective,
            sharia_status=sharia_status,
            evidence_confidence=evidence_confidence,
            budget_approved=budget_approved,
            operational_risk=operational_risk,
            approved_actions=approved_actions,
        )
        if review.mandate is None:
            raise ValueError("A mandate can only be issued when the decision permits execution.")
        return review.mandate

    def history(self, objective_id: str) -> tuple[OrchestratorDecision, ...]:
        return self.controller.history(objective_id)

    def last_decision(self, objective_id: str) -> OrchestratorDecision:
        decisions = self.history(objective_id)
        if not decisions:
            raise ValueError(f"No decision history found for {objective_id}.")
        return decisions[-1]
