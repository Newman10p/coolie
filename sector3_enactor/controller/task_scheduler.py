"""Task scheduler wrappers against the execution graph utilities."""
from __future__ import annotations

from ..runtime.task_graph import topological_order


class TaskScheduler:
    def __init__(self, plan=None) -> None:
        self.plan = plan

    def schedule(self, plan) -> list:
        self.plan = plan
        return topological_order(plan)


__all__ = ["TaskScheduler"]
