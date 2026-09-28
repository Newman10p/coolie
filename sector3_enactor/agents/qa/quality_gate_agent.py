"""Quality Gate agent (§5.7): independent blocker. Can advance assets to REVIEWED
and can block releases; cannot fix outputs itself."""
from __future__ import annotations

from typing import Any

from ..base import BaseEnactorAgent
from ...models.asset import AssetStage
from ...models.shared import AgentStatus


class QualityGateAgent(BaseEnactorAgent):
    def run(self, task, state: dict[str, Any]):
        business_id = state["business_id"]; plan_hash = state["plan_hash"]
        asset_ids = tuple(state["context"].get("assetIds", ()))
        evaluation = self.quality_gate.evaluate(
            execution_id=task.execution_id,
            artifact_contents={aid: self.artifacts.get(f"assets/{aid}/v1.txt") for aid in asset_ids
                               if f"assets/{aid}/v1.txt" in self.artifacts.keys()},
            approved_claims=tuple(state["request"].approved_claims),
            evidence_index=state["context"].get("evidenceIndex", {}),
            product_facts=state["context"].get("productFacts", {}),
            inventory_consistent=bool(state["context"].get("inventoryConsistent", True)),
            code_review_blocking=bool(state["context"].get("codeReviewBlocking", False)))
        report = self.store_artifact(f"qa/{task.execution_id}-report.json", repr([f.detail for f in evaluation.findings]))
        if not evaluation.passed:
            block = self.call(task, business_id, plan_hash, "qa.block_release",
                              {"executionId": task.execution_id, "findings": len(evaluation.findings)})
            if block.status != "success": return AgentStatus.FAILED, "Block action itself denied.", {}
            return AgentStatus.BLOCKED, f"Release blocked: {[f.detail for f in evaluation.findings if f.blocking]}", {
                "passed": False}
        for asset_id in asset_ids:
            asset = state["store"].assets.maybe(asset_id)
            if asset is not None and asset.stage is AssetStage.DRAFT:
                advance = self.call(task, business_id, plan_hash, "assets.advance_stage",
                                    {"assetId": asset_id, "to": AssetStage.REVIEWED.value})
                if advance.status != "success":
                    return AgentStatus.BLOCKED, f"Could not mark {asset_id} reviewed: {advance.error}", {}
                asset.advance_to(AssetStage.REVIEWED, actor_id=self.agent_id, reason="QA checklist passed")
        return AgentStatus.SUCCESS, "Quality gate passed.", {"passed": True, "report": report.artifact_key}
