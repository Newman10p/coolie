"""Application service that composes planning, agents, persistence, reporting, and handoffs."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .agents import AgentRegistry
from .controller import ResearchRoomController
from .models import MissionStatus, ResearchMission, ResearchTask, TaskStatus
from .planner import MissionPlanner
from .reporting import ReportGenerator
from .repositories import MissionRepository, OpportunityRepository, TaskRepository


class ResearchRoomService:
    def __init__(self, missions: MissionRepository, tasks: TaskRepository, opportunities: OpportunityRepository, controller: ResearchRoomController, planner: MissionPlanner, agents: AgentRegistry, reports: ReportGenerator) -> None:
        self.missions = missions; self.tasks = tasks; self.opportunities = opportunities
        self.controller = controller; self.planner = planner; self.agents = agents; self.reports = reports

    def create_mission(self, mission: ResearchMission, actor_id: str) -> ResearchMission:
        self.missions.create(mission)
        self.controller.transition(mission, MissionStatus.VALIDATING, actor_id=actor_id, reason="Mission intake validation")
        self.controller.transition(mission, MissionStatus.PLANNING, actor_id=actor_id, reason="Mission scope validated")
        return mission

    def plan_mission(self, mission_id: str, actor_id: str) -> tuple[ResearchTask, ...]:
        mission = self.missions.get(mission_id)
        planned = self.planner.plan(mission)
        for task in planned: self.tasks.create(task)
        self.controller.validate_task_graph(mission, planned)
        self.controller.transition(mission, MissionStatus.RESEARCHING, actor_id=actor_id, reason="Research tasks planned")
        return tuple(planned)

    def pause_mission(self, mission_id: str, actor_id: str, reason: str) -> ResearchMission:
        mission = self.missions.get(mission_id)
        self.controller.transition(mission, MissionStatus.PAUSED, actor_id=actor_id, reason=reason)
        return mission

    def resume_mission(self, mission_id: str, actor_id: str, reason: str) -> ResearchMission:
        mission = self.missions.get(mission_id)
        if mission.status is not MissionStatus.PAUSED: raise ValueError("Only paused missions can be resumed.")
        history = self.controller.history(mission_id)
        if not history: raise ValueError("Paused mission has no transition history.")
        self.controller.transition(mission, history[-1].from_status, actor_id=actor_id, reason=reason)
        return mission

    def cancel_mission(self, mission_id: str, actor_id: str, reason: str) -> ResearchMission:
        mission = self.missions.get(mission_id)
        self.controller.transition(mission, MissionStatus.CANCELLED, actor_id=actor_id, reason=reason)
        for task in self.tasks.for_mission(mission_id):
            if task.status not in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.BLOCKED, TaskStatus.CANCELLED}:
                task.status = TaskStatus.CANCELLED
        return mission

    def progress(self, mission_id: str) -> object:
        return self.controller.progress(self.missions.get(mission_id), list(self.tasks.for_mission(mission_id)))

    def run_ready_tasks(self, mission_id: str) -> tuple[ResearchTask, ...]:
        mission = self.missions.get(mission_id); all_tasks = list(self.tasks.for_mission(mission_id))
        ready = self.controller.ready_tasks(mission, all_tasks)
        for task in ready:
            task.status = TaskStatus.RUNNING
            try:
                result = self.agents.get(task.agent_type).run(mission, task)
                self.controller.complete_task(task, schema_valid=result.data is not None, evidence_confidence=result.confidence)
            except (KeyError, PermissionError, ValueError) as error:
                self.controller.record_failure(task, str(error))
        return tuple(ready)

    def report(self, mission_id: str, report_id: str) -> object:
        mission = self.missions.get(mission_id)
        payload: dict[str, Any] = {"mission": asdict(mission), "tasks": [asdict(task) for task in self.tasks.for_mission(mission_id)], "opportunities": [asdict(item) for item in self.opportunities.for_mission(mission_id)], "transitions": [asdict(item) for item in self.controller.history(mission_id)]}
        return self.reports.create(report_id, mission_id, payload)
