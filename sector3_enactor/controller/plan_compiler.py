"""Plan compilation helpers that match the Enactor architecture doc."""
from __future__ import annotations

from ..controller.execution_controller import ExecutionController
from ..models.execution import ExecutionRequest
from ..models.task import EnactorTask, ExecutionPlan


class PlanCompiler:
    def __init__(self, controller: ExecutionController | None = None) -> None:
        self.controller = controller

    def compile(self, request: ExecutionRequest, tasks: tuple[EnactorTask, ...]) -> ExecutionPlan:
        if self.controller is None:
            raise ValueError("PlanCompiler requires a controller instance.")
        return self.controller.compile_plan(request, tasks)

    def validate(self, plan: ExecutionPlan) -> bool:
        if self.controller is None:
            raise ValueError("PlanCompiler requires a controller instance.")
        self.controller._verify_plan_integrity(plan)
        return True


__all__ = ["PlanCompiler"]
