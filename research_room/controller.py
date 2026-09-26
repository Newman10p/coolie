from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .models import MissionStatus, ResearchMission, ResearchTask, TaskStatus

_TRANSITIONS = {
    MissionStatus.RECEIVED: {MissionStatus.VALIDATING, MissionStatus.CANCELLED},
    MissionStatus.VALIDATING: {MissionStatus.PLANNING, MissionStatus.FAILED, MissionStatus.PAUSED},
    MissionStatus.PLANNING: {MissionStatus.RESEARCHING, MissionStatus.FAILED, MissionStatus.PAUSED},
    MissionStatus.RESEARCHING: {MissionStatus.VERIFYING, MissionStatus.FAILED, MissionStatus.PAUSED},
    MissionStatus.VERIFYING: {MissionStatus.MODELING, MissionStatus.FAILED, MissionStatus.PAUSED},
    MissionStatus.MODELING: {MissionStatus.STRATEGIZING, MissionStatus.FAILED, MissionStatus.PAUSED},
    MissionStatus.STRATEGIZING: {MissionStatus.WAITING_FOR_APPROVAL, MissionStatus.SUBMITTED, MissionStatus.FAILED, MissionStatus.PAUSED},
    MissionStatus.WAITING_FOR_APPROVAL: {MissionStatus.SUBMITTED, MissionStatus.PAUSED, MissionStatus.CANCELLED},
    MissionStatus.SUBMITTED: {MissionStatus.COMPLETED, MissionStatus.ARCHIVED},
    MissionStatus.PAUSED: {MissionStatus.VALIDATING, MissionStatus.PLANNING, MissionStatus.RESEARCHING, MissionStatus.VERIFYING, MissionStatus.MODELING, MissionStatus.STRATEGIZING, MissionStatus.CANCELLED},
}
_TERMINAL_TASK_STATES = {TaskStatus.BLOCKED, TaskStatus.FAILED, TaskStatus.CANCELLED}
_GATED_STATES = {MissionStatus.VERIFYING, MissionStatus.MODELING, MissionStatus.STRATEGIZING, MissionStatus.SUBMITTED}


class TaskGraphError(ValueError):
    """Raised when a mission task graph cannot be scheduled safely."""


class QualityGateError(ValueError):
    """Raised when a mission is moved forward without required verified artifacts."""


@dataclass(frozen=True)
class MissionProgress:
    status: MissionStatus
    completed_tasks: int
    total_tasks: int
    blocked_tasks: int


@dataclass(frozen=True)
class MissionTransition:
    mission_id: str
    from_status: MissionStatus
    to_status: MissionStatus
    actor_id: str
    reason: str
    approval_context: str | None
    timestamp: datetime


@dataclass(frozen=True)
class SubmissionContext:
    financial_evaluation_attached: bool
    strategy_review_attached: bool
    explicit_recommendation: bool
    maximum_test_budget_defined: bool
    stop_conditions_defined: bool
    high_severity_risks_resolved_or_escalated: bool

    def missing_gates(self) -> list[str]:
        names = {
            "financial_evaluation_attached": self.financial_evaluation_attached,
            "strategy_review_attached": self.strategy_review_attached,
            "explicit_recommendation": self.explicit_recommendation,
            "maximum_test_budget_defined": self.maximum_test_budget_defined,
            "stop_conditions_defined": self.stop_conditions_defined,
            "high_severity_risks_resolved_or_escalated": self.high_severity_risks_resolved_or_escalated,
        }
        return [name for name, satisfied in names.items() if not satisfied]


class ResearchRoomController:
    def __init__(self) -> None:
        self._history: dict[str, list[MissionTransition]] = {}

    def validate(self, mission: ResearchMission) -> list[str]:
        # Dataclasses reject invalid instances at construction. This method remains the API intake seam.
        errors: list[str] = []
        if not mission.mission_id.strip(): errors.append("mission_id is required")
        if not mission.objective.strip(): errors.append("objective is required")
        return errors

    def validate_task_graph(self, mission: ResearchMission, tasks: list[ResearchTask]) -> None:
        ids = [task.task_id for task in tasks]
        duplicates = sorted({task_id for task_id in ids if ids.count(task_id) > 1})
        if duplicates: raise TaskGraphError(f"Duplicate task IDs: {', '.join(duplicates)}")
        by_id = {task.task_id: task for task in tasks}
        for task in tasks:
            if task.mission_id != mission.mission_id: raise TaskGraphError(f"Task {task.task_id} belongs to another mission.")
            missing = [dependency for dependency in task.dependencies if dependency not in by_id]
            if missing: raise TaskGraphError(f"Task {task.task_id} has missing dependencies: {', '.join(missing)}")
        visited: set[str] = set(); active: set[str] = set()
        def visit(task_id: str) -> None:
            if task_id in active: raise TaskGraphError(f"Circular task dependency detected at {task_id}.")
            if task_id not in visited:
                active.add(task_id)
                for dependency in by_id[task_id].dependencies: visit(dependency)
                active.remove(task_id); visited.add(task_id)
        for task_id in by_id: visit(task_id)

    def transition(self, mission: ResearchMission, target: MissionStatus, *, actor_id: str, reason: str, tasks: list[ResearchTask] | None = None, submission_context: SubmissionContext | None = None, approval_context: str | None = None) -> None:
        if target not in _TRANSITIONS.get(mission.status, set()):
            raise ValueError(f"Invalid mission transition: {mission.status.value} -> {target.value}")
        if not actor_id.strip() or not reason.strip(): raise ValueError("Transitions require actor_id and reason.")
        if target in _GATED_STATES:
            if tasks is None: raise QualityGateError("Forward lifecycle transitions require the mission task list.")
            self.validate_task_graph(mission, tasks)
            incomplete = [task.task_id for task in tasks if task.required and task.status is not TaskStatus.COMPLETED]
            if incomplete: raise QualityGateError(f"Required tasks are incomplete: {', '.join(incomplete)}")
        if target is MissionStatus.SUBMITTED:
            if submission_context is None: raise QualityGateError("Submission requires a submission context.")
            missing = submission_context.missing_gates()
            if missing: raise QualityGateError(f"Submission quality gates are unmet: {', '.join(missing)}")
        previous = mission.status
        mission.status = target
        self._history.setdefault(mission.mission_id, []).append(MissionTransition(mission.mission_id, previous, target, actor_id, reason, approval_context, datetime.now(timezone.utc)))

    def history(self, mission_id: str) -> tuple[MissionTransition, ...]:
        return tuple(self._history.get(mission_id, []))

    def ready_tasks(self, mission: ResearchMission, tasks: list[ResearchTask]) -> list[ResearchTask]:
        self.validate_task_graph(mission, tasks)
        by_id = {task.task_id: task for task in tasks}; ready: list[ResearchTask] = []
        for task in tasks:
            if task.status is not TaskStatus.PENDING: continue
            failed_dependencies = [dependency for dependency in task.dependencies if by_id[dependency].status in _TERMINAL_TASK_STATES]
            if failed_dependencies:
                task.status = TaskStatus.BLOCKED
                task.blocked_reason = f"Blocked by terminal dependencies: {', '.join(failed_dependencies)}"
            elif all(by_id[dependency].status is TaskStatus.COMPLETED for dependency in task.dependencies):
                task.status = TaskStatus.READY
                ready.append(task)
        return sorted(ready, key=lambda item: item.priority, reverse=True)

    def complete_task(self, task: ResearchTask, *, schema_valid: bool, evidence_confidence: float) -> None:
        if task.status not in {TaskStatus.READY, TaskStatus.RUNNING}: raise ValueError("Only ready or running tasks can be completed.")
        if not 0 <= evidence_confidence <= 1: raise ValueError("evidence_confidence must be between 0 and 1.")
        if not schema_valid or evidence_confidence < task.required_evidence_threshold:
            task.status = TaskStatus.BLOCKED
            task.blocked_reason = "Output schema or evidence-confidence quality gate failed."
            return
        task.status = TaskStatus.COMPLETED
        task.blocked_reason = None

    def record_failure(self, task: ResearchTask, reason: str) -> None:
        if not reason.strip(): raise ValueError("Failure reason is required.")
        task.attempts += 1; task.failure_reason = reason
        task.status = TaskStatus.PENDING if task.attempts <= task.maximum_retries else TaskStatus.FAILED

    def progress(self, mission: ResearchMission, tasks: list[ResearchTask]) -> MissionProgress:
        return MissionProgress(mission.status, sum(t.status is TaskStatus.COMPLETED for t in tasks), len(tasks), sum(t.status is TaskStatus.BLOCKED for t in tasks))
