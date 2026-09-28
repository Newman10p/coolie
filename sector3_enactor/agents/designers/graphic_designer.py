"""Graphic Designer (§5.2): concepts and asset drafts; never publishes (§8.1 rule 8)."""
from __future__ import annotations

from typing import Any

from ..base import BaseEnactorAgent
from ...models.asset import AssetStage, AssetType, AssetVersion
from ...models.shared import AgentStatus, now_utc


class GraphicDesignerAgent(BaseEnactorAgent):
    def run(self, task, state: dict[str, Any]):
        business_id = state["business_id"]; plan_hash = state["plan_hash"]
        brief = str(state["context"].get("brief", "campaign visual"))
        concept = self.brain(task, business_id, plan_hash, f"concept:{brief}", estimated_tokens=4000) or f"concept for {brief}"
        asset_id = f"ASSET-{task.task_id}"
        store = self.call(task, business_id, plan_hash, "assets.store_version",
                          {"assetId": asset_id, "content": concept, "version": "v1"})
        if store.status != "success": return AgentStatus.FAILED, f"Store denied: {store.error}", {}
        ref = self.store_artifact(f"assets/{asset_id}/v1.txt", concept)
        from ...models.asset import ManagedAsset
        asset = ManagedAsset(asset_id=asset_id, business_id=business_id, execution_id=task.execution_id,
                             asset_type=AssetType.IMAGE, name=brief, stage=AssetStage.DRAFT)
        asset.add_version(AssetVersion(version_id="v1", content_hash=ref.content_hash, artifact_key=ref.artifact_key,
                                       created_by=self.agent_id, created_at=now_utc(), notes="initial draft"))
        state["store"].assets.put(asset)
        return AgentStatus.SUCCESS, f"Draft asset {asset_id} stored (stage=draft).", {"asset_id": asset_id}
