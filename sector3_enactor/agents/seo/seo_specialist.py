"""SEO Specialist (§5.6): audits, briefs and changesets; live application needs A3."""
from __future__ import annotations

from typing import Any

from ..base import BaseEnactorAgent
from ...models.approval import ApprovalLevel
from ...models.shared import AgentStatus


class SeoSpecialistAgent(BaseEnactorAgent):
    def run(self, task, state: dict[str, Any]):
        business_id = state["business_id"]; plan_hash = state["plan_hash"]
        audit = self.call(task, business_id, plan_hash, "seo.run_technical_audit", {"target": state.get("site", "shop.example")})
        if audit.status != "success": return AgentStatus.FAILED, f"Audit denied: {audit.error}", {}
        changeset_id = f"SEOC-{task.task_id}"
        submit = self.call(task, business_id, plan_hash, "seo.submit_changeset",
                           {"changesetId": changeset_id, "items": ["meta-descriptions", "alt-text"]})
        if submit.status != "success": return AgentStatus.BLOCKED, f"Changeset submission denied: {submit.error}", {}
        exact = {"changesetId": changeset_id}
        approval = self.request_approval(task, business_id, "seo.apply_approved_changes", changeset_id, exact,
                                         ApprovalLevel.A3_STANDARD, reason="Apply SEO changeset to live site")
        if not self.approval_ready(approval.approval_id):
            return AgentStatus.AWAITING_APPROVAL, f"Changeset submitted; awaiting A3 approval {approval.approval_id}.", {
                "approval_id": approval.approval_id}
        applied = self.call(task, business_id, plan_hash, "seo.apply_approved_changes", exact,
                            approval_id=approval.approval_id, idempotency_key=f"{task.task_id}:{changeset_id}")
        if applied.status != "success": return AgentStatus.BLOCKED, f"Apply denied: {applied.error}", {}
        return AgentStatus.SUCCESS, f"SEO changeset {changeset_id} applied.", {"changeset_id": changeset_id}
