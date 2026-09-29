"""Compatibility wrapper exposing the architecture doc's controller names."""
from __future__ import annotations

from typing import Any

from .execution_controller import ExecutionController, RunOutcome
from ..models.execution import ExecutionRequest, ExecutionStatus
from ..models.task import EnactorTask, ExecutionPlan


class EnactorController(ExecutionController):
    """Doc-aligned facade around the concrete execution controller."""

    def createPlan(self, request: ExecutionRequest, tasks: tuple[EnactorTask, ...]) -> ExecutionPlan:
        return self.compile_plan(request, tasks)

    def validatePlan(self, plan: ExecutionPlan) -> bool:
        self._verify_plan_integrity(plan)
        return True

    def start(self, request: ExecutionRequest, plan: ExecutionPlan, context: dict[str, Any]) -> RunOutcome:
        return self.submit(request, plan, context)

    def pause(self, request: ExecutionRequest, reason: str = "operator pause") -> None:
        self.state_machine.transition(request, ExecutionStatus.PAUSED, event="pause_requested", reason=reason)

    def cancel(self, request: ExecutionRequest, reason: str = "cancelled") -> None:
        self.state_machine.transition(request, ExecutionStatus.CANCELLED, event="cancel_requested", reason=reason)

    def getStatus(self, request: ExecutionRequest) -> ExecutionStatus:
        return request.status


__all__ = ["EnactorController", "ExecutionController", "RunOutcome"]
