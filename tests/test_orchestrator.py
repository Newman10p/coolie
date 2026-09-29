import unittest

from orchestrator import DecisionCode, OrchestratorController, OrchestratorService, OwnerObjective, ShariaStatus
from research_room.models import Money


class OrchestratorModelTests(unittest.TestCase):
    def test_objective_validation_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            OwnerObjective("", "owner", "summary", "outcome")
        with self.assertRaises(ValueError):
            OwnerObjective("OBJ-1", "owner", "", "outcome")
        with self.assertRaises(ValueError):
            OwnerObjective("OBJ-1", "owner", "summary", "outcome", max_budget=Money(0, "USD"))


class OrchestratorControllerTests(unittest.TestCase):
    def test_non_compliant_and_uncertain_sharia_are_blocked(self):
        objective = OwnerObjective("OBJ-1", "owner", "Launch pilot", "Ship the feature", max_budget=Money(100, "USD"))
        controller = OrchestratorController()
        review = controller.review_objective(
            objective,
            sharia_status=ShariaStatus.NON_COMPLIANT,
            evidence_confidence=0.9,
            budget_approved=True,
            operational_risk="low",
        )
        self.assertEqual(review.decision.code, DecisionCode.REJECT)

        pause = controller.review_objective(
            objective,
            sharia_status=ShariaStatus.UNCERTAIN,
            evidence_confidence=0.9,
            budget_approved=True,
            operational_risk="low",
        )
        self.assertEqual(pause.decision.code, DecisionCode.PAUSE)

    def test_weak_evidence_and_budget_gate_require_more_review(self):
        objective = OwnerObjective("OBJ-2", "owner", "Increase revenue", "Reach 3x ROI", max_budget=Money(50, "USD"))
        controller = OrchestratorController()
        weak = controller.review_objective(
            objective,
            sharia_status=ShariaStatus.COMPLIANT,
            evidence_confidence=0.5,
            budget_approved=True,
            operational_risk="low",
        )
        self.assertEqual(weak.decision.code, DecisionCode.RESEARCH_MORE)

        budget_gate = controller.review_objective(
            objective,
            sharia_status=ShariaStatus.COMPLIANT,
            evidence_confidence=0.9,
            budget_approved=False,
            operational_risk="low",
        )
        self.assertEqual(budget_gate.decision.code, DecisionCode.REQUEST_OWNER_APPROVAL)

    def test_safe_objectives_can_issue_a_mandate(self):
        objective = OwnerObjective("OBJ-3", "owner", "Expand to a new market", "Local acquisition", max_budget=Money(200, "USD"), approval_required=True)
        controller = OrchestratorController()
        review = controller.review_objective(
            objective,
            sharia_status=ShariaStatus.COMPLIANT,
            evidence_confidence=0.95,
            budget_approved=True,
            operational_risk="low",
            approved_actions=("research", "monitor", "pause", "launch"),
        )
        self.assertIn(review.decision.code, {DecisionCode.APPROVE_LIMITED_LAUNCH, DecisionCode.CONTINUE})
        self.assertIsNotNone(review.mandate)
        self.assertIn("launch", review.mandate.allowed_actions)


class OrchestratorServiceTests(unittest.TestCase):
    def test_service_routes_safe_decisions_and_tracks_history(self):
        service = OrchestratorService()
        objective = OwnerObjective("OBJ-4", "owner", "Run a controlled pilot", "Proof of demand", max_budget=Money(75, "USD"))
        decision = service.decide(
            objective,
            sharia_status=ShariaStatus.COMPLIANT,
            evidence_confidence=0.82,
            budget_approved=True,
            operational_risk="medium",
            approved_actions=("research", "monitor", "pause"),
        )
        self.assertIn(decision.code, {DecisionCode.RUN_CONTROLLED_TEST, DecisionCode.CONTINUE})
        self.assertEqual(len(service.history(objective.objective_id)), 1)
        self.assertEqual(service.last_decision(objective.objective_id).objective_id, objective.objective_id)


if __name__ == "__main__":
    unittest.main()
