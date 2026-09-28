"""Plan and task-graph models — document §4.3, §4.4."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .approval import ApprovalLevel
from .shared import ToolMode, now_utc, _non_empty
from .execution import TaskLifecycleStatus


@dataclass(frozen=True)
class ApprovalGate:
    """Immutable node marking that a task may only proceed with a valid approval.

    Compiled plans store gates as separate immutable objects; removing one from a
    plan's gate tuple is detected by the plan hash (§8.1 rule 3).
    """
    gate_id: str
    required_level: ApprovalLevel
    description: str

    def __post_init__(self) -> None:
        _non_empty(self.gate_id, "gate_id"); _non_empty(self.description, "description")
        if not isinstance(self.required_level, ApprovalLevel): raise ValueError("required_level must be an ApprovalLevel.")
        if self.required_level is ApprovalLevel.A0_NONE: raise ValueError("A0 is not a gate.")


@dataclass
class EnactorTask:
    task_id: str
    execution_id: str
    agent_role: str
    objective: str
    tool: str | None = None                       # primary gateway tool for this task
    arguments: dict[str, Any] = field(default_factory=dict)
    dependencies: tuple[str, ...] = ()
    allowed_tools: tuple[str, ...] = ()
    mode: ToolMode = ToolMode.READ
    approval_gate: ApprovalGate | None = None
    timeout_seconds: int = 300
    maximum_retries: int = 1
    priority: int = 0
    conditional_on: str | None = None             # run only when a named metric/flag is true
    status: TaskLifecycleStatus = TaskLifecycleStatus.PENDING
    attempts: int = 0
    blocked_reason: str | None = None
    failure_reason: str | None = None
    approval_id: str | None = None                # filled once an approval is bound

    def __post_init__(self) -> None:
        for name in ("task_id", "execution_id", "agent_role", "objective"):
            _non_empty(getattr(self, name), name)
        if self.task_id in self.dependencies: raise ValueError("A task cannot depend on itself.")
        if len(set(self.dependencies)) != len(self.dependencies): raise ValueError("Task dependencies must be unique.")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, int) or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive integer.")
        if isinstance(self.maximum_retries, bool) or not isinstance(self.maximum_retries, int) or self.maximum_retries < 0:
            raise ValueError("maximum_retries must be a non-negative integer.")
        if not isinstance(self.mode, ToolMode): raise ValueError("mode must be a ToolMode.")
        if self.approval_gate is not None and self.mode is ToolMode.READ:
            raise ValueError("Read-only tasks cannot carry approval gates.")


@dataclass(frozen=True)
class ExecutionPlan:
    execution_id: str
    plan_id: str
    objective: str
    tasks: tuple[EnactorTask, ...]
    constraints: tuple[str, ...] = ()
    audience: str | None = None
    approved_claims: tuple[str, ...] = ()
    required_assets: tuple[str, ...] = ()
    success_metric_ids: tuple[str, ...] = ()
    stop_condition_ids: tuple[str, ...] = ()
    budget_summary: dict[str, Any] = field(default_factory=dict)
    compiled_at: datetime = field(default_factory=now_utc)
    plan_hash: str = ""

    def __post_init__(self) -> None:
        for name in ("execution_id", "plan_id", "objective"): _non_empty(getattr(self, name), name)
        if not self.tasks: raise ValueError("A plan requires at least one task.")
        ids = [task.task_id for task in self.tasks]
        if len(set(ids)) != len(ids): raise ValueError("Plan task IDs must be unique.")
        if self.compiled_at.tzinfo is None: raise ValueError("compiled_at must be timezone-aware.")

    def gates(self) -> tuple[ApprovalGate, ...]:
        return tuple(task.approval_gate for task in self.tasks if task.approval_gate is not None)
