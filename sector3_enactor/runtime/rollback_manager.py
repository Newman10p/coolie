"""Rollback tracking for deployments and staged releases."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RollbackEntry:
    deployment_id: str
    predecessor: str | None
    reason: str = "operator_requested"


@dataclass
class RollbackManager:
    _history: dict[str, RollbackEntry] = field(default_factory=dict)

    def record(self, deployment_id: str, *, predecessor: str | None = None, reason: str = "operator_requested") -> None:
        self._history[deployment_id] = RollbackEntry(deployment_id=deployment_id, predecessor=predecessor, reason=reason)

    def rollback(self, deployment_id: str) -> RollbackEntry:
        entry = self._history.get(deployment_id)
        if entry is None:
            raise KeyError(f"No recorded deployment to rollback: {deployment_id}")
        return entry


__all__ = ["RollbackManager", "RollbackEntry"]
