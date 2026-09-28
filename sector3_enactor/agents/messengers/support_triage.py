"""Support Triage (§5.1A/B): classify → draft from template → send only with a
valid approval; restricted intents ALWAYS escalate and never receive autonomous replies."""
from __future__ import annotations

from typing import Any

from ..base import BaseEnactorAgent
from ...models.shared import AgentStatus, ToolMode
from ...models.approval import ApprovalLevel
from ...models.messaging import MessageIntent, RESTRICTED_INTENTS, SupportTicket

ORDER_STATUS_TEMPLATE = ("Hi {name}, your order {order_id} is {status}. "
                         "Estimated delivery: {eta}. Reply to this email any time.")


class SupportTriageAgent(BaseEnactorAgent):
    def run(self, task, state: dict[str, Any]):
        business_id = state["business_id"]; plan_hash = state["plan_hash"]
        message = state["context"].get("inbound_message")
        if message is None: return AgentStatus.FAILED, "No inbound message in context.", {}
        classification = self.call(task, business_id, plan_hash, "triage.classify_request",
                                   {"messageId": message.message_id, "body": message.body[:200],
                                    "target": message.message_id}, mode=ToolMode.READ)
        if classification.status != "success": return AgentStatus.FAILED, f"Triage failed: {classification.error}", {}
        intent_value = str(classification.output.get("intent", "customer_feedback"))
        try: intent = MessageIntent(intent_value)
        except ValueError: intent = MessageIntent.CUSTOMER_FEEDBACK

        restricted = set(RESTRICTED_INTENTS) | {MessageIntent(value) for value in state.get("restricted_intents", ())}
        if intent in restricted:
            ticket = SupportTicket(ticket_id=f"TKT-{message.message_id}", business_id=business_id,
                                  message_id=message.message_id, intent=intent, severity="high",
                                  escalation_reason=f"Restricted intent {intent.value}: human decision required.")
            state["store"].tickets.put(ticket)
            route = self.call(task, business_id, plan_hash, "triage.route_request",
                              {"messageId": message.message_id, "queue": "human_review", "target": message.message_id})
            notify = self.call(task, business_id, plan_hash, "internal.notify",
                               {"channel": "human", "message": f"Escalated {intent.value} for {message.sender_reference}",
                                "target": "human"})
            if route.status != "success" or notify.status != "success":
                return AgentStatus.FAILED, "Escalation routing denied by gateway.", {"intent": intent.value}
            return AgentStatus.SUCCESS, f"Escalated to human (restricted intent {intent.value}).", {
                "intent": intent.value, "escalated": True, "ticket_id": ticket.ticket_id}

        reply_type = str(classification.output.get("replyType", "informational"))
        body = ORDER_STATUS_TEMPLATE.format(name=message.sender_reference.split("@")[0],
                                            order_id=state["context"].get("orderId", "n/a"),
                                            status="on its way", eta="2 business days") \
            if intent is MessageIntent.ORDER_STATUS else f"Thanks for your note about {intent.value}; we're on it."
        draft_id = f"DRAFT-{message.message_id}"
        from ...models.messaging import OutboundDraft, MessageChannel, ConversationParty
        draft = OutboundDraft(draft_id=draft_id, business_id=business_id, execution_id=task.execution_id,
                              channel=MessageChannel.EMAIL, recipient=message.sender_reference,
                              party=ConversationParty.CUSTOMER, subject=None, body=body, intent=intent,
                              linked_inbound_message_id=message.message_id, created_by_agent=self.agent_id)
        state["store"].drafts.put(draft)
        self.store_artifact(f"drafts/{draft_id}.txt", body)

        exact = {"recipient": message.sender_reference, "draftId": draft_id}
        approval = self.request_approval(task, business_id, "email.send_approved", message.sender_reference,
                                         exact, ApprovalLevel.A3_STANDARD, reason=f"Reply to {intent.value} ({reply_type})")
        if not self.approval_ready(approval.approval_id):
            return AgentStatus.AWAITING_APPROVAL, f"Draft ready; awaiting A3 approval {approval.approval_id}.", {
                "intent": intent.value, "draft_id": draft_id, "approval_id": approval.approval_id}
        sent = self.call(task, business_id, plan_hash, "email.send_approved",
                         {**exact, "templateId": "order_status_v1"}, approval_id=approval.approval_id,
                         idempotency_key=f"{task.task_id}:{draft_id}")
        if sent.status != "success":
            return (AgentStatus.BLOCKED if sent.status == "denied" else AgentStatus.FAILED), \
                   f"Send refused: {sent.error}", {"draft_id": draft_id}
        return AgentStatus.SUCCESS, f"Replied to {message.sender_reference} ({intent.value}).", {
            "intent": intent.value, "draft_id": draft_id, "external_operation_id": sent.external_operation_id}
