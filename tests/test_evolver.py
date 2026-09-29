import unittest

from evolver import CapabilityExtensionPlan, EvolverController, ExpansionRequest
from research_room.models import Money


class EvolverTests(unittest.TestCase):
    def test_request_validation(self):
        with self.assertRaises(ValueError):
            ExpansionRequest("REQ-1", "online tutoring", "Add tutoring", ())

    def test_assess_reports_missing_capabilities_and_cost(self):
        request = ExpansionRequest(
            request_id="REQ-2",
            business_domain="online tutoring",
            idea="Add tutoring operations",
            required_capabilities=("payments", "scheduling", "analytics"),
            expected_monthly_revenue=Money(12000, "USD"),
            max_budget=Money(8000, "USD"),
        )
        plan = EvolverController().assess(request, existing_capabilities=("payments",)).plan
        self.assertIn("scheduling", plan.missing_capabilities)
        self.assertTrue(plan.financially_viable)
        self.assertIsInstance(plan.estimated_cost, Money)
        self.assertIsNotNone(plan.required_tools)


if __name__ == "__main__":
    unittest.main()
