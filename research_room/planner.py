"""Deterministic mission planner for product, service, and existing-business missions."""
from __future__ import annotations

from .models import ResearchMission, ResearchTask


class MissionPlanner:
    def plan(self, mission: ResearchMission) -> list[ResearchTask]:
        product = any(model in {"dropshipping", "resale", "ecommerce", "marketplace"} for model in mission.business_models)
        roles = ["market_discovery", "demand_validation", "competitor_intelligence"]
        roles += ["supplier_fulfillment"] if product else ["audience_customer", "marketing_intelligence"]
        roles += ["risk_policy", "evidence_verification", "synthesis"]
        tasks: list[ResearchTask] = []
        for index, role in enumerate(roles, 1):
            dependencies = [tasks[-1].task_id] if role in {"evidence_verification", "synthesis"} and tasks else []
            task_id = f"{mission.mission_id}-{index:02d}-{role}"
            tasks.append(ResearchTask(task_id, mission.mission_id, role, f"{role.replace('_', ' ')} for: {mission.objective}", dependencies, ["research:web:search"], "agent_result", 300, priority=len(roles) - index, required_evidence_threshold=.5))
        return tasks
