"""Supply Communications (§5.1C): draft supplier messages; send only to known,
allowlisted suppliers with A2 approval; first-contact escalates."""
from __future__ import annotations

from typing import Any

from ..base import BaseEnactorAgent
from ...models.shared import AgentStatus, ToolMode


class SupplyCommunicationsAgent(BaseEnactorAgent):
    def run(self, task, state: dict[str, Any]):
        business_id = state["business_id"]; plan_hash = state["plan_hash"]
        supplier = state["context"].get("supplier")
        if not supplier: return AgentStatus.FAILED, "No supplier in context.", {}
        allowlisted = bool(supplier.get("allowlisted", False))
        first_contact = bool(supplier.get("firstContact", False))
        flags = tuple(["first_contact_with_new_supplier"] if first_contact else [])
        body = f"Checking delivery status for PO {supplier.get('po','n/a')}; expected {supplier.get('eta','unknown')}."
        draft = self.call(task, business_id, plan_hash, "supplier.draft_message",
                          {"supplier": supplier["id"], "body": body, "target": supplier["id"]})
        if draft.status != "success": return AgentStatus.FAILED, f"Drafting denied: {draft.error}", {}
        self.store_artifact(f"drafts/supplier-{supplier['id']}.txt", body)
        if not allowlisted:
            notify = self.call(task, business_id, plan_hash, "internal.notify",
                               {"channel": "human", "message": f"Unknown supplier {supplier['id']} — cannot contact autonomously.",
                                "target": "human"})
            return (AgentStatus.SUCCESS if notify.status == "success" else AgentStatus.FAILED), \
                   f"Escalated unknown supplier {supplier['id']} to human.", {"escalated": True}
        exact = {"recipient": supplier["contact"], "supplierId": supplier["id"]}
        approval = self.request_approval(task, business_id, "supplier.send_approved", supplier["contact"], exact,
                                         self._level_for(flags), reason=f"Follow up on PO {supplier.get('po')}")
        if not self.approval_ready(approval.approval_id):
            return AgentStatus.AWAITING_APPROVAL, f"Awaiting approval {approval.approval_id}.", {"approval_id": approval.approval_id}
        sent = self.call(task, business_id, plan_hash, "supplier.send_approved", exact, approval_id=approval.approval_id,
                         idempotency_key=f"{task.task_id}:{supplier['id']}", flags=flags)
        if sent.status != "success":
            return AgentStatus.BLOCKED, f"Send denied: {sent.error}", {}
        return AgentStatus.SUCCESS, f"Supplier {supplier['id']} contacted.", {"external_operation_id": sent.external_operation_id}

    def _level_for(self, flags):
        from ...models.approval import ApprovalLevel
        return ApprovalLevel.A3_STANDARD if "first_contact_with_new_supplier" in flags else ApprovalLevel.A2_LIGHTWEIGHT
