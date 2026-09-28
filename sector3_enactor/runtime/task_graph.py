"""Task graph compilation + cycle detection — document §4.4, §6.1 Execution Plans."""
from __future__ import annotations

from ..models.task import EnactorTask, ExecutionPlan


class CycleError(ValueError):
    pass


def validate_graph(tasks: tuple[EnactorTask, ...]) -> None:
    ids = {task.task_id for task in tasks}
    for task in tasks:
        missing = set(task.dependencies) - ids
        if missing: raise ValueError(f"Task {task.task_id} depends on unknown tasks: {sorted(missing)}")
    # Kahn's algorithm
    indegree = {task.task_id: len(task.dependencies) for task in tasks}
    children: dict[str, list[str]] = {task.task_id: [] for task in tasks}
    for task in tasks:
        for dep in task.dependencies: children[dep].append(task.task_id)
    queue = [tid for tid, deg in indegree.items() if deg == 0]
    visited = 0
    while queue:
        node = queue.pop(); visited += 1
        for child in children[node]:
            indegree[child] -= 1
            if indegree[child] == 0: queue.append(child)
    if visited != len(tasks): raise CycleError("Task graph contains a cycle; plan cannot be compiled.")


def topological_order(plan: ExecutionPlan) -> tuple[EnactorTask, ...]:
    validate_graph(plan.tasks)
    ordered: list[EnactorTask] = []
    done: set[str] = set()
    remaining = list(plan.tasks)
    while remaining:
        ready = [t for t in remaining if set(t.dependencies) <= done]
        if not ready: raise CycleError("Task graph contains a cycle.")
        ready.sort(key=lambda t: (-t.priority, t.task_id))
        for task in ready:
            ordered.append(task); done.add(task.task_id); remaining.remove(task)
    return tuple(ordered)
