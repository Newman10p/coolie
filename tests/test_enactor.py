import unittest
from datetime import datetime, timezone

from sector3_enactor.config.loader import load_sector_config
from sector3_enactor.connectors.fake import build_fake_connectors, wire_gateway
from sector3_enactor.controller.execution_controller import ExecutionController
from sector3_enactor.models.approval import ApprovalLevel
from sector3_enactor.models.execution import ActionRequest, ExecutionRequest
from sector3_enactor.models.messaging import (
    ConversationParty,
    InboundMessage,
    MessageChannel,
    MessageDirection,
)
from sector3_enactor.models.shared import Money, RiskSeverity, StopCondition, SuccessMetric, ToolMode
from sector3_enactor.models.task import EnactorTask
from sector3_enactor.tools.definitions import build_default_registry
from sector3_enactor.tools.gateway import GatewayContext


class EnactorCoreTests(unittest.TestCase):
    def test_config_and_registry_are_loaded(self):
        config = load_sector_config()
        registry = build_default_registry()
        self.assertEqual(config.version, "2026-09-01.1")
        self.assertIn("email.send_approved", registry.names())
        self.assertEqual(registry.get("email.send_approved").approval_level, ApprovalLevel.A3_STANDARD)

    def test_external_action_idempotency_is_bound_and_replayed_once(self):
        config = load_sector_config()
        registry = build_default_registry()
        controller = ExecutionController(config=config, registry=registry)
        connectors = build_fake_connectors()
        wire_gateway(controller.gateway, registry.names(), connectors)
        task = EnactorTask(
            task_id="T-IDEMPOTENT",
            execution_id="E-IDEMPOTENT",
            agent_role="messengers.support_triage",
            objective="Send approved customer response",
            tool="email.send_approved",
            arguments={"recipient": "customer@example.com"},
            allowed_tools=("email.send_approved",),
            mode=ToolMode.EXTERNAL_ACTION,
        )
        request = ExecutionRequest(
            execution_id="E-IDEMPOTENT",
            business_id="B-IDEMPOTENT",
            plan_id="P-IDEMPOTENT",
            objective="Send a customer response",
        )
        plan = controller.compile_plan(request, (task,))
        controller.budgets.open_ledger(request.execution_id, config.budgets)
        arguments = {
            "recipient": "customer@example.com",
            "subject": "Order update",
            "body": "Your order is on the way.",
        }
        context = GatewayContext(
            business_id=request.business_id,
            execution_id=request.execution_id,
            task_id=task.task_id,
            agent_role=task.agent_role,
            agent_id="messengers.support_triage@E-IDEMPOTENT",
            allowed_tools=task.allowed_tools,
            plan_hash=plan.plan_hash,
            requested_mode=ToolMode.EXTERNAL_ACTION,
        )
        preview = controller.gateway.execute(
            context,
            ActionRequest(
                action_id="A-PREVIEW",
                tool="email.send_approved",
                arguments={**arguments, "dryRun": True},
                risk_level=RiskSeverity.HIGH,
                required_approval_level=ApprovalLevel.A3_STANDARD.value,
                reversible=False,
                idempotency_key="send-001",
            ),
        )
        self.assertEqual(preview.status, "success")

        approval = controller.approval_policy.request(
            execution_id=request.execution_id,
            business_id=request.business_id,
            task=task,
            agent_id=context.agent_id,
            tool="email.send_approved",
            target=arguments["recipient"],
            exact_arguments=arguments,
            level=ApprovalLevel.A3_STANDARD,
            risk=RiskSeverity.HIGH,
            reason="Owner-approved response.",
        )
        controller.approve(approval.approval_id, decided_by="owner", level=ApprovalLevel.A3_STANDARD)
        bound_context = GatewayContext(
            business_id=context.business_id,
            execution_id=context.execution_id,
            task_id=context.task_id,
            agent_role=context.agent_role,
            agent_id=context.agent_id,
            allowed_tools=context.allowed_tools,
            plan_hash=context.plan_hash,
            requested_mode=context.requested_mode,
            approval_id=approval.approval_id,
        )
        action = ActionRequest(
            action_id="A-SEND",
            tool="email.send_approved",
            arguments=arguments,
            risk_level=RiskSeverity.HIGH,
            required_approval_level=ApprovalLevel.A3_STANDARD.value,
            reversible=False,
            idempotency_key="send-001",
        )
        sent = controller.gateway.execute(bound_context, action)
        replay = controller.gateway.execute(
            bound_context,
            ActionRequest(
                action_id="A-SEND-RETRY",
                tool=action.tool,
                arguments=arguments,
                risk_level=RiskSeverity.HIGH,
                required_approval_level=ApprovalLevel.A3_STANDARD.value,
                reversible=False,
                idempotency_key="send-001",
            ),
        )
        self.assertEqual(sent.status, "success", sent.error)
        self.assertTrue(replay.output["deduplicated"])
        self.assertEqual(len(connectors["email"].calls), 2)

        drifted = controller.gateway.execute(
            bound_context,
            ActionRequest(
                action_id="A-DRIFT",
                tool=action.tool,
                arguments={**arguments, "body": "different text"},
                risk_level=RiskSeverity.HIGH,
                required_approval_level=ApprovalLevel.A3_STANDARD.value,
                reversible=False,
                idempotency_key="send-001",
            ),
        )
        self.assertEqual(drifted.status, "denied")
        self.assertIn("idempotency_conflict", drifted.error)
        self.assertEqual(len(connectors["email"].calls), 2)

    def test_support_triage_handles_inbound_message_and_required_approval(self):
        config = load_sector_config()
        registry = build_default_registry()
        controller = ExecutionController(config=config, registry=registry)
        connectors = build_fake_connectors()
        wire_gateway(controller.gateway, registry.names(), connectors)

        request = ExecutionRequest(
            execution_id="E-100",
            business_id="B-100",
            plan_id="P-100",
            objective="Respond to customer order-status inquiry",
            success_metrics=(SuccessMetric("M-1", "cases_resolved", 1.0, "count"),),
            stop_conditions=(StopCondition("S-1", "No customer harm", "cases_resolved", ">=", 0.0),),
            budget=Money(100.0, "USD"),
            maximum_automatic_spend=Money(10.0, "USD"),
        )

        task = EnactorTask(
            task_id="T-1",
            execution_id=request.execution_id,
            agent_role="messengers.support_triage",
            objective="Triage the inbound order-status request",
            tool="email.send_approved",
            arguments={"recipient": "customer@example.com"},
            dependencies=(),
            allowed_tools=("triage.classify_request", "triage.route_request", "internal.notify", "email.send_approved"),
            mode=ToolMode.EXTERNAL_ACTION,
        )

        plan = controller.compile_plan(request, (task,))
        context = {
            "inbound_message": InboundMessage(
                message_id="MSG-1",
                business_id=request.business_id,
                channel=MessageChannel.EMAIL,
                direction=MessageDirection.INBOUND,
                party=ConversationParty.CUSTOMER,
                sender_reference="customer@example.com",
                subject="Order status",
                body="Where is my order?",
                received_at=datetime.now(timezone.utc),
            ),
            "restricted_intents": ("returns_request", "payment_dispute"),
            "orderId": "ORD-42",
        }

        outcome = controller.submit(request, plan, context)
        self.assertEqual(outcome.result.status.value, "awaiting_approval")
        self.assertIn("approval_id", str(outcome.result.escalations))

    def test_restricted_intent_is_escalated_instead_of_sending(self):
        config = load_sector_config()
        registry = build_default_registry()
        controller = ExecutionController(config=config, registry=registry)
        connectors = build_fake_connectors()
        wire_gateway(controller.gateway, registry.names(), connectors)

        request = ExecutionRequest(
            execution_id="E-200",
            business_id="B-200",
            plan_id="P-200",
            objective="Escalate a restricted complaint",
            success_metrics=(SuccessMetric("M-2", "cases_escalated", 1.0, "count"),),
            stop_conditions=(StopCondition("S-2", "No unhandled risk", "cases_escalated", ">=", 1.0),),
            budget=Money(50.0, "USD"),
            maximum_automatic_spend=Money(5.0, "USD"),
        )

        task = EnactorTask(
            task_id="T-2",
            execution_id=request.execution_id,
            agent_role="messengers.support_triage",
            objective="Classify restricted support request",
            tool="triage.classify_request",
            arguments={"messageId": "MSG-2", "body": "I need a refund now!"},
            dependencies=(),
            allowed_tools=("triage.classify_request", "triage.route_request", "internal.notify"),
            mode=ToolMode.READ,
        )

        plan = controller.compile_plan(request, (task,))
        context = {
            "inbound_message": InboundMessage(
                message_id="MSG-2",
                business_id=request.business_id,
                channel=MessageChannel.EMAIL,
                direction=MessageDirection.INBOUND,
                party=ConversationParty.CUSTOMER,
                sender_reference="customer@example.com",
                subject="Refund",
                body="I need a refund now!",
                received_at=datetime.now(timezone.utc),
            ),
            "restricted_intents": ("returns_request", "payment_dispute"),
        }

        outcome = controller.submit(request, plan, context)
        self.assertEqual(outcome.result.status.value, "awaiting_approval")
        self.assertTrue(any("restricted intent" in str(escalation.reason).lower() for escalation in outcome.result.escalations))


if __name__ == "__main__":
    unittest.main()
