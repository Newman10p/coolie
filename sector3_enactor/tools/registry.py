"""Tool Registry — document §7. Every gateway-callable capability is declared here
with its mode, risk, allowed agents, approval level, reversibility, dry-run support,
budget type and data scope. The gateway refuses calls to unregistered tools."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..models.shared import ToolMode, _non_empty
from ..models.approval import ApprovalLevel

VALID_BUDGET_TYPES = frozenset({"none", "model_tokens", "api_calls", "ad_spend", "purchases"})
VALID_DATA_SCOPES = frozenset({
    "public_read", "internal_read", "customer_read", "customer_write", "product_write",
    "code_read", "code_write", "comms_send", "ads_write", "inventory_write", "seo_write", "payments_none",
})


@dataclass(frozen=True)
class EnactorToolDefinition:
    name: str
    description: str
    mode: ToolMode
    risk_level: str                      # low | medium | high | critical
    allowed_agents: frozenset[str]       # agent role names permitted to call this tool
    approval_level: ApprovalLevel        # minimum approval required
    reversible: bool
    supports_dry_run: bool
    budget_type: str
    data_scope: str
    target_argument: str = "target"      # argument key naming the action's target (for approval binding)
    cost_estimate: Callable[[dict[str, Any]], float] = field(default=lambda arguments: 0.0)

    def __post_init__(self) -> None:
        _non_empty(self.name, "name"); _non_empty(self.description, "description")
        if not isinstance(self.mode, ToolMode): raise ValueError("mode must be a ToolMode.")
        if self.risk_level not in {"low", "medium", "high", "critical"}: raise ValueError("Tool risk_level is invalid.")
        if not isinstance(self.approval_level, ApprovalLevel): raise ValueError("approval_level must be an ApprovalLevel.")
        if not self.allowed_agents: raise ValueError("Tool must declare at least one allowed agent (least privilege requires explicit grants).")
        if any(not agent.strip() for agent in self.allowed_agents): raise ValueError("Allowed agent names must be non-empty.")
        if self.budget_type not in VALID_BUDGET_TYPES: raise ValueError(f"budget_type must be one of {sorted(VALID_BUDGET_TYPES)}.")
        if self.data_scope not in VALID_DATA_SCOPES: raise ValueError(f"data_scope must be one of {sorted(VALID_DATA_SCOPES)}.")
        if self.mode is ToolMode.READ and self.approval_level is not ApprovalLevel.A0_NONE:
            raise ValueError("Read-only tools cannot require approvals.")
        if self.mode is ToolMode.EXTERNAL_ACTION and self.approval_level is ApprovalLevel.A0_NONE:
            raise ValueError("External actions must require at least A1 approval.")
        if self.mode is ToolMode.EXTERNAL_ACTION and not self.reversible and not self.supports_dry_run:
            raise ValueError("Irreversible external actions must support dry-run previews before execution.")


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, EnactorToolDefinition] = {}

    def register(self, definition: EnactorToolDefinition) -> None:
        if definition.name in self._tools: raise ValueError(f"Duplicate tool registration: {definition.name}")
        self._tools[definition.name] = definition

    def get(self, name: str) -> EnactorToolDefinition | None:
        return self._tools.get(name)

    def require(self, name: str) -> EnactorToolDefinition:
        tool = self._tools.get(name)
        if tool is None: raise KeyError(f"Unregistered tool cannot be called: {name}")
        return tool

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def tools_for_agent(self, agent_role: str) -> tuple[str, ...]:
        return tuple(name for name, tool in sorted(self._tools.items()) if agent_role in tool.allowed_agents)
