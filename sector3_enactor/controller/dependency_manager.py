"""Dependency manager for execution graphs."""
from __future__ import annotations


class DependencyManager:
    def __init__(self) -> None:
        self._graph = {}

    def add(self, task_id: str, dependencies: tuple[str, ...] = ()) -> None:
        self._graph[task_id] = tuple(dependencies)

    def ready(self, task_id: str, completed: set[str]) -> bool:
        return all(dep in completed for dep in self._graph.get(task_id, ()))


__all__ = ["DependencyManager"]
