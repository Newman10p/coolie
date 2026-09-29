import unittest

from money_calculator import (
    ActivationDecisionCode,
    ActivationProposal,
    MoneyCalculatorController,
    MoneyCalculatorService,
)
from research_room.models import Money


class MoneyCalculatorModelTests(unittest.TestCase):
    def test_proposal_validation_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            ActivationProposal("P-1", "A/B test", "team", Money(0, "USD"), Money(0, "USD"), 30, 0.9)
        with self.assertRaises(ValueError):
            ActivationProposal("", "A/B test", "team", Money(100, "USD"), Money(200, "USD"), 30, 0.9)
        with self.assertRaises(ValueError):
            ActivationProposal("P-3", "A/B test", "team", Money(100, "USD"), Money(200, "USD"), 30, 1.5)

    def test_approve_and_budget_gate_logic(self):
        proposal = ActivationProposal(
            "P-4",
            "Expand paid acquisition",
            "growth-team",
            Money(200, "USD"),
            Money(300, "USD"),
            30,
            0.9,
            required_margin_percent=15.0,
        )
        review = MoneyCalculatorController().assess(proposal)
        self.assertEqual(review.decision.code, ActivationDecisionCode.APPROVE)

        capped = MoneyCalculatorController().assess(
            proposal,
            budget_limit=Money(150, "USD"),
        )
        self.assertEqual(capped.decision.code, ActivationDecisionCode.REQUEST_OWNER_APPROVAL)

    def test_rejects_negative_cashflow_and_tracks_history(self):
        proposal = ActivationProposal(
            "P-5",
            "Launch a low-converting paid channel",
            "growth-team",
            Money(1000, "USD"),
            Money(800, "USD"),
            21,
            0.8,
            required_margin_percent=5.0,
        )
        service = MoneyCalculatorService()
        recommendation = service.assess(proposal)
        self.assertEqual(recommendation.code, ActivationDecisionCode.REJECT)
        self.assertEqual(len(service.history(proposal.proposal_id)), 1)
        self.assertEqual(service.last_recommendation(proposal.proposal_id).proposal_id, proposal.proposal_id)


if __name__ == "__main__":
    unittest.main()
