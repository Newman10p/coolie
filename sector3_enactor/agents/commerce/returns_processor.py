"""Returns Processor (§5.5D): RECOMMENDS dispositions only — money never moves here."""
from __future__ import annotations

from typing import Any

from ..base import BaseEnactorAgent
from ...models.commerce import ReturnDisposition, ReturnRecommendation
from ...models.shared import AgentStatus, Money


class ReturnsProcessorAgent(BaseEnactorAgent):
    def run(self, task, state: dict[str, Any]):
        business_id = state["business_id"]; plan_hash = state["plan_hash"]
        order_id = str(state["context"].get("orderId", ""))
        if not order_id: return AgentStatus.FAILED, "No order in context.", {}
        orders = self.call(task, business_id, plan_hash, "store.read_orders", {"orderId": order_id, "target": order_id})
        amount = float(state["context"].get("amount", 0.0))
        recommendation = ReturnRecommendation(
            recommendation_id=f"RET-{order_id}", business_id=business_id, order_id=order_id,
            disposition=ReturnDisposition.RECOMMEND_REFUND if amount <= 50 else ReturnDisposition.ESCALATE_HUMAN,
            proposed_amount=Money(amount, "USD") if amount else None,
            justification="Within standard refund window per policy.", routed_to="finance")
        recorded = self.call(task, business_id, plan_hash, "returns.recommend",
                             {"orderId": order_id, "disposition": recommendation.disposition.value,
                              "amount": amount})
        if recorded.status != "success": return AgentStatus.BLOCKED, f"Recommendation denied: {recorded.error}", {}
        notify = self.call(task, business_id, plan_hash, "internal.notify",
                           {"channel": "finance", "message": f"Return recommendation for {order_id}: {recommendation.disposition.value}",
                            "target": "finance"})
        if notify.status != "success": return AgentStatus.FAILED, "Finance notification denied.", {}
        return AgentStatus.SUCCESS, f"Recommendation filed for {order_id}; finance decides.", {
            "recommendation_id": recommendation.recommendation_id}
