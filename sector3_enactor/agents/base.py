"""BaseEnactorAgent — document §12. Agents are role-scoped workers that propose
actions to the gateway; they hold NO credentials and cannot bypass policy."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..evaluation.quality_gate import QualityGate
from ..models.approval import ApprovalLevel, ApprovalStatus
from ..models.execution import ActionRequest, ActionResult
from ..models.shared import AgentStatus, RiskSeverity, ToolMode
from ..models.task import EnactorTask
from ..policy.approval_policy import ApprovalPolicy
from ..runtime.artifact_store import ArtifactStore
from ..storage.audit_repository import AuditRepository
from ..tools.gateway import GatewayContext, ToolGateway
from ..tools.registry import ToolRegistry

RISK_BY_LEVEL = {ApprovalLevel.A1_INTERNAL: RiskSeverity.LOW, ApprovalLevel.A2_LIGHTWEIGHT: RiskSeverity.MEDIUM,
                 ApprovalLevel.A3_STANDARD: RiskSeverity.HIGH, ApprovalLevel.A4_STRICT: RiskSeverity.CRITICAL}


@dataclass
class BaseEnactorAgent:
    agent_id: str
    role: str                          # e.g. "messengers.support_triage"
    division: str
    gateway: ToolGateway
    registry: ToolRegistry
    approval_policy: ApprovalPolicy
    artifacts: ArtifactStore
    audit: AuditRepository
    quality_gate: QualityGate | None = None
    model_used: str = "fake-brain-v1"
    calls_made: int = field(default=0, init=False)
    tokens_used: int = field(default=0, init=False)

    # -- helpers shared by divisions -----------------------------------------
    def context(self, task: EnactorTask, business_id: str, plan_hash: str, *,
                approval_id: str | None = None, amount=None, flags: tuple[str, ...] = ()) -> GatewayContext:
        return GatewayContext(business_id=business_id, execution_id=task.execution_id, task_id=task.task_id,
                              agent_role=self.role, agent_id=self.agent_id, allowed_tools=task.allowed_tools,
                              plan_hash=plan_hash, requested_mode=task.mode, approval_id=approval_id,
                              amount=amount, context_flags=flags)

    def call(self, task: EnactorTask, business_id: str, plan_hash: str, tool: str, arguments: dict[str, Any],
             *, mode: ToolMode | None = None, approval_id: str | None = None, idempotency_key: str | None = None,
             amount=None, flags: tuple[str, ...] = ()) -> ActionResult:
        definition = self.registry.require(tool)
        ctx = self.context(task, business_id, plan_hash, approval_id=approval_id, amount=amount, flags=flags)
        if mode is not None:
            ctx.requested_mode = mode
        request = ActionRequest(action_id=f"ACT-{self.calls_made + 1:03d}", tool=tool, arguments=dict(arguments),
                                risk_level=RISK_BY_LEVEL.get(definition.approval_level, RiskSeverity.LOW),
                                required_approval_level=definition.approval_level.value,
                                reversible=definition.reversible, idempotency_key=idempotency_key)
        self.calls_made += 1
        if definition.budget_type == "model_tokens":
            self.tokens_used += int(definition.cost_estimate(arguments))
        return self.gateway.execute(ctx, request)

    def request_approval(self, task: EnactorTask, business_id: str, tool: str, target: str,
                         exact_arguments: dict[str, Any], level: ApprovalLevel, reason: str, amount=None):
        return self.approval_policy.request(execution_id=task.execution_id, business_id=business_id, task=task,
                                            agent_id=self.agent_id, tool=tool, target=target,
                                            exact_arguments=exact_arguments, level=level,
                                            risk=RISK_BY_LEVEL[level], reason=reason, amount=amount)

    def approval_ready(self, approval_id: str) -> bool:
        approval = self.approval_policy._approvals.maybe(approval_id)
        return approval is not None and approval.status is ApprovalStatus.APPROVED

    def store_artifact(self, key: str, content: str, content_type: str = "text/plain"):
        return self.artifacts.put(key, content, content_type=content_type)

    def brain(self, task: EnactorTask, business_id: str, plan_hash: str, prompt: str, estimated_tokens: int = 1000) -> str:
        result = self.call(task, business_id, plan_hash, "brain.complete",
                           {"prompt": prompt, "estimatedTokens": estimated_tokens, "target": "brain"},
                           mode=ToolMode.READ)
        if result.status != "success": raise RuntimeError(f"Brain call failed: {result.error}")
        return str(result.output.get("text", ""))

    def run(self, task: EnactorTask, state: dict[str, Any]) -> tuple[AgentStatus, str, dict[str, Any]]:
        raise NotImplementedError(f"{self.role} must implement run()")
