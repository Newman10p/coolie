"""Catalog Manager (§5.5A): draft listings with evidence-backed claims; publish needs A3."""
from __future__ import annotations

from typing import Any

from ..base import BaseEnactorAgent
from ...models.approval import ApprovalLevel
from ...models.commerce import ProductRecord, ProductStatus
from ...models.shared import AgentStatus, Money


class CatalogManagerAgent(BaseEnactorAgent):
    def run(self, task, state: dict[str, Any]):
        business_id = state["business_id"]; plan_hash = state["plan_hash"]
        spec = state["context"].get("product", {})
        product_id = str(spec.get("productId", f"PROD-{task.task_id}"))
        record = ProductRecord(product_id=product_id, business_id=business_id, title=str(spec.get("title", "Product")),
                               description=str(spec.get("description", "Description")),
                               price=Money(float(spec.get("price", 10.0)), str(spec.get("currency", "USD"))),
                               sku=spec.get("sku", ""), evidence_references=tuple(spec.get("evidence", ())))
        draft = self.call(task, business_id, plan_hash, "catalog.create_draft",
                          {"productId": product_id, "title": record.title, "body": record.description})
        if draft.status != "success": return AgentStatus.FAILED, f"Draft denied: {draft.error}", {}
        validate = self.call(task, business_id, plan_hash, "catalog.validate_listing", {"productId": product_id})
        if validate.status != "success": return AgentStatus.FAILED, f"Validation denied: {validate.error}", {}
        if not validate.output.get("valid", True) or not record.evidence_references:
            state["store"].products.put(record)
            return AgentStatus.BLOCKED, "Listing lacks evidence references; publication blocked pre-approval.", {}
        exact = {"productId": product_id}
        approval = self.request_approval(task, business_id, "catalog.publish_approved", product_id, exact,
                                         ApprovalLevel.A3_STANDARD, reason="Publish validated listing")
        if not self.approval_ready(approval.approval_id):
            record.status = ProductStatus.IN_REVIEW; state["store"].products.put(record)
            return AgentStatus.AWAITING_APPROVAL, f"Listing in review; awaiting A3 approval {approval.approval_id}.", {
                "approval_id": approval.approval_id}
        published = self.call(task, business_id, plan_hash, "catalog.publish_approved", exact,
                              approval_id=approval.approval_id, idempotency_key=f"{task.task_id}:{product_id}")
        if published.status != "success": return AgentStatus.BLOCKED, f"Publish denied: {published.error}", {}
        record.status = ProductStatus.PUBLISHED; record.sku = record.sku or f"SKU-{product_id}"
        state["store"].products.put(record)
        return AgentStatus.SUCCESS, f"Product {product_id} published.", {"product_id": product_id}
