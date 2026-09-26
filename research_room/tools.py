"""Controlled read-only connector gateway used by research agents."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .models import ResearchMission
from .policy import ToolPolicy


@dataclass(frozen=True)
class Connector:
    name: str
    permission: str
    source_type: str
    execute: Callable[[dict[str, Any]], dict[str, Any]]


class ConnectorRegistry:
    def __init__(self) -> None: self._connectors: dict[str, Connector] = {}
    def register(self, connector: Connector) -> None:
        if connector.name in self._connectors: raise ValueError(f"Connector already registered: {connector.name}")
        self._connectors[connector.name] = connector
    def get(self, name: str) -> Connector: return self._connectors[name]


class ToolGateway:
    """Controller-owned gateway; agents cannot bypass permission/source-policy checks."""
    def __init__(self, policy: ToolPolicy, registry: ConnectorRegistry) -> None:
        self._policy = policy; self._registry = registry

    def call(self, mission: ResearchMission, *, task_id: str, agent_id: str, tool_name: str, allowed_tools: list[str], arguments: dict[str, Any]) -> dict[str, Any]:
        connector = self._registry.get(tool_name)
        if connector.source_type not in mission.allowed_sources.allowed_source_types: raise PermissionError("Mission source policy disallows this connector.")
        if not self._policy.authorize(connector.permission, allowed_tools): raise PermissionError("Task is not authorized to use this connector.")
        return connector.execute(dict(arguments))
