"""Narrow, predictable specialist agents that only operate through ToolGateway."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .models import AgentResult, ResearchMission, ResearchTask
from .tools import ToolGateway


class ResearchAgent(Protocol):
    agent_id: str
    role: str
    allowed_tools: tuple[str, ...]
    def run(self, mission: ResearchMission, task: ResearchTask) -> AgentResult: ...


@dataclass
class ConnectorResearchAgent:
    agent_id: str
    role: str
    allowed_tools: tuple[str, ...]
    gateway: ToolGateway

    def run(self, mission: ResearchMission, task: ResearchTask) -> AgentResult:
        if not self.allowed_tools: return AgentResult("partial", {}, (), ("No connector configured for this agent.",), ("External research data",), 0)
        tool = self.allowed_tools[0]
        result = self.gateway.call(mission, task_id=task.task_id, agent_id=self.agent_id, tool_name=tool, allowed_tools=task.allowed_tools, arguments={"objective": task.objective, "markets": mission.markets})
        return AgentResult("success", result, (), (), (), .5, ({"tool": tool},))


SPECIALIST_ROLES = ("market_discovery", "demand_validation", "competitor_intelligence", "supplier_fulfillment", "audience_customer", "marketing_intelligence", "product_offer", "risk_policy", "evidence_verification", "synthesis")


class AgentRegistry:
    def __init__(self) -> None: self._agents: dict[str, ResearchAgent] = {}
    def register(self, agent: ResearchAgent) -> None:
        if agent.role not in SPECIALIST_ROLES: raise ValueError("Agent role is not a registered specialist role.")
        if agent.role in self._agents: raise ValueError(f"Agent role already registered: {agent.role}")
        self._agents[agent.role] = agent
    def get(self, role: str) -> ResearchAgent: return self._agents[role]
