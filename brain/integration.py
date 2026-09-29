"""Drop-in research-room agent adapter backed by a scoped Brain session."""

from __future__ import annotations

from collections.abc import Callable

from research_room.models import AgentResult, ResearchMission, ResearchTask

from .models import BrainOperation, InferenceRequest, SessionGrant
from .runtime import BrainService


class BrainResearchAgent:
    def __init__(
        self,
        brain: BrainService,
        *,
        agent_id: str,
        role: str,
        session_issuer: Callable[[str, str], SessionGrant],
        session_revoker: Callable[[str], object],
    ) -> None:
        self._brain = brain
        self.agent_id = agent_id
        self.role = role
        self._session_issuer = session_issuer
        self._session_revoker = session_revoker
        self.allowed_tools: tuple[str, ...] = ()

    def run(self, mission: ResearchMission, task: ResearchTask) -> AgentResult:
        grant = self._session_issuer(self.agent_id, task.task_id)
        try:
            definition = self._brain.agent_definition(self.agent_id)
            response = self._brain.complete(
                InferenceRequest(
                    request_id=f"{task.task_id}-{task.attempts + 1}",
                    agent_id=self.agent_id,
                    sector=definition.sector,
                    task_id=task.task_id,
                    operation=BrainOperation.COMPLETE,
                    input={
                        "objective": task.objective,
                        "markets": mission.markets,
                        "business_models": mission.business_models,
                    },
                    max_tokens=max(1, definition.max_tokens_per_task // 2),
                    max_cost=definition.max_cost_per_task,
                    schema_name="agent_result",
                ),
                session_id=grant.session.session_id,
                session_token=grant.token,
            )
            return AgentResult("success", response.output, (), response.warnings, (), .5)
        finally:
            self._session_revoker(grant.session.session_id)
