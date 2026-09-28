"""Permission engine — document §8.1 rules 4–6 and §7.

An agent's effective permissions are the intersection of:
  config division grant ∩ tool registry allowed_agents ∩ plan task allowed_tools,
and every call must additionally satisfy mode/approval/budget/scope checks in the
gateway. Missing context ⇒ deny (fail closed).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config.loader import SectorConfig
from ..tools.registry import EnactorToolDefinition, ToolRegistry


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str


class AuthorizationEngine:
    def __init__(self, config: SectorConfig, registry: ToolRegistry) -> None:
        self._config = config
        self._registry = registry

    def division_grant(self, agent_role: str) -> frozenset[str]:
        # Agent roles look like "messengers.support_triage" → division "messengers".
        division = agent_role.split(".", 1)[0]
        return frozenset(self._config.tools_for_division(division))

    def effective_tools(self, agent_role: str, task_allowed_tools: tuple[str, ...]) -> frozenset[str]:
        registered = set(self._registry.names())
        return self.division_grant(agent_role) & set(task_allowed_tools) & registered

    def authorize(self, *, agent_role: str, task_allowed_tools: tuple[str, ...], tool: EnactorToolDefinition) -> PermissionDecision:
        if tool.name not in self._registry.names():
            return PermissionDecision(False, "Tool is not registered in the Tool Registry.")
        if agent_role not in tool.allowed_agents:
            return PermissionDecision(False, f"Agent role {agent_role} is not in the tool's allowedAgents list.")
        if tool.name not in self.division_grant(agent_role):
            return PermissionDecision(False, f"Division grant for {agent_role.split('.')[0]} does not include {tool.name}.")
        if tool.name not in set(task_allowed_tools):
            return PermissionDecision(False, f"Plan task does not list {tool.name} in allowed_tools.")
        return PermissionDecision(True, "permission")
