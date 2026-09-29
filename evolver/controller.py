from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from research_room.models import Money

from .models import CapabilityExtensionPlan, ExpansionRequest


@dataclass(frozen=True)
class EvolverReview:
    request_id: str
    plan: CapabilityExtensionPlan
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EvolverController:
    def __init__(self) -> None:
        self._history: dict[str, CapabilityExtensionPlan] = {}

    def assess(self, request: ExpansionRequest, *, existing_capabilities: tuple[str, ...] = ()) -> EvolverReview:
        known = tuple(sorted(set(existing_capabilities or ())))
        missing = tuple(cap for cap in request.required_capabilities if cap not in known)
        required_agents = tuple(f"{request.business_domain}-agent" for _ in missing) if missing else ()
        required_tools = tuple(f"{cap}-tool" for cap in missing)
        required_connectors = tuple(f"{cap}-connector" for cap in missing if cap.lower() in {"payments", "messaging", "analytics"})
        required_policies = tuple(f"{cap}-policy" for cap in missing)
        required_data_models = tuple(f"{cap}-model" for cap in missing)
        estimated_cost = self._estimate_cost(len(missing), len(required_tools), len(required_connectors), request)
        revenue = request.expected_monthly_revenue or Money(estimated_cost.amount * 1.5, estimated_cost.currency)
        financially_viable = True
        if request.max_budget is not None and estimated_cost.amount > request.max_budget.amount:
            financially_viable = False
        elif revenue.amount <= 0:
            financially_viable = False
        elif request.expected_monthly_revenue is not None and revenue.amount < estimated_cost.amount:
            financially_viable = False
        reusability = "business_specific"
        if not missing:
            reusability = "temporary"
        elif len(missing) <= 2:
            reusability = "business_specific"
        else:
            reusability = "reusable"
        plan = CapabilityExtensionPlan(
            plan_id=f"plan-{request.request_id}",
            request_id=request.request_id,
            business_domain=request.business_domain,
            currently_supported=known,
            missing_capabilities=missing,
            required_agents=required_agents,
            required_tools=required_tools,
            required_connectors=required_connectors,
            required_policies=required_policies,
            required_data_models=required_data_models,
            estimated_cost=estimated_cost,
            expected_revenue=revenue,
            test_plan=(
                "unit validation for new models and policies",
                "integration test for the new business workflow",
                "acceptance check against the target domain KPI",
            ),
            reusability=reusability,
            financially_viable=financially_viable,
        )
        self._history[request.request_id] = plan
        return EvolverReview(request.request_id, plan)

    @staticmethod
    def _estimate_cost(missing_count: int, tool_count: int, connector_count: int, request: ExpansionRequest) -> Money:
        currency = (request.max_budget or request.expected_monthly_revenue or Money(1_000.0, "USD")).currency
        base = 2_000.0 + missing_count * 1_500.0 + tool_count * 300.0 + connector_count * 500.0
        if request.risk_tolerance == "high":
            base += 1_500.0
        elif request.risk_tolerance == "low":
            base *= 0.85
        return Money(base, currency)

    def history(self, request_id: str) -> CapabilityExtensionPlan | None:
        return self._history.get(request_id)
