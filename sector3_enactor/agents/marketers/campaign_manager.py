"""Campaign Manager (§5.4): draft → claims validation → publish ONLY with valid A4
approval bound to exact campaign+budget; ad-budget increases escalate to A4/human."""
from __future__ import annotations

from typing import Any

from ..base import BaseEnactorAgent
from ...evaluation.claims_checker import check_claims
from ...models.approval import ApprovalLevel
from ...models.marketing import CampaignRecord, CampaignStatus, MarketingClaim
from ...models.shared import AgentStatus, Money


class CampaignManagerAgent(BaseEnactorAgent):
    def run(self, task, state: dict[str, Any]):
        business_id = state["business_id"]; plan_hash = state["plan_hash"]
        spec = state["context"].get("campaign", {})
        budget_amount = float(spec.get("budget", 100.0)); currency = str(spec.get("currency", "USD"))
        campaign_id = f"CAMP-{task.execution_id[-6:]}"
        claims = tuple(MarketingClaim(claim_id=f"CLM-{i}", text=text, evidence_reference=spec.get("evidence", {}).get(text))
                       for i, text in enumerate(spec.get("claims", [])))
        draft_body = {"campaignId": campaign_id, "channel": spec.get("channel", "email"),
                      "audience": spec.get("audience", "all"), "budgetAmount": budget_amount}
        draft = self.call(task, business_id, plan_hash, "campaigns.draft", {**draft_body, "estimatedTokens": 3000})
        if draft.status != "success": return AgentStatus.FAILED, f"Drafting denied: {draft.error}", {}
        violations, supported = check_claims(claims, tuple(state["request"].approved_claims))
        self.call(task, business_id, plan_hash, "claims.check_marketing_claims",
                  {"campaignId": campaign_id, "violations": violations, "supported": supported,
                   "target": campaign_id})
        campaign = CampaignRecord(campaign_id=campaign_id, business_id=business_id, execution_id=task.execution_id,
                                  name=spec.get("name", "launch campaign"), channel=spec.get("channel", "email"),
                                  budget=Money(budget_amount, currency), status=CampaignStatus.DRAFT,
                                  audience=spec.get("audience", "all"), claims=claims,
                                  stop_condition_ids=tuple(c.condition_id for c in state["request"].stop_conditions))
        state["store"].campaigns.put(campaign)
        if violations:
            return AgentStatus.BLOCKED, f"Unsupported claims block publication: {violations}", {"violations": violations}
        exact = dict(draft_body)
        approval = self.request_approval(task, business_id, "campaigns.publish_approved", campaign_id, exact,
                                         ApprovalLevel.A4_STRICT, reason=f"Publish campaign with {currency} {budget_amount} budget",
                                         amount=Money(budget_amount, currency))
        if not self.approval_ready(approval.approval_id):
            return AgentStatus.AWAITING_APPROVAL, f"Campaign drafted & validated; awaiting A4 approval {approval.approval_id}.", {
                "approval_id": approval.approval_id, "campaign_id": campaign_id}
        published = self.call(task, business_id, plan_hash, "campaigns.publish_approved",
                              {**exact, "approvalEvidence": approval.decided_by}, approval_id=approval.approval_id,
                              amount=Money(budget_amount, currency), idempotency_key=f"{task.task_id}:{campaign_id}")
        if published.status != "success":
            return AgentStatus.BLOCKED, f"Publish denied: {published.error}", {}
        campaign.status = CampaignStatus.PUBLISHED
        return AgentStatus.SUCCESS, f"Campaign {campaign_id} published.", {
            "campaign_id": campaign_id, "external_operation_id": published.external_operation_id}
