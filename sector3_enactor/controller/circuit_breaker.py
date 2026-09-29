"""Circuit breaker pattern for external tool failures."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    open_for_seconds: float = 30.0
    _failures: dict[str, int] = field(default_factory=dict)
    _open: dict[str, float] = field(default_factory=dict)

    def allow(self, key: str, *, now: float | None = None) -> bool:
        now = now if now is not None else 0.0
        if key in self._open and self._open[key] > now:
            return False
        self._open.pop(key, None)
        return True

    def record_failure(self, key: str, *, now: float | None = None) -> None:
        now = now if now is not None else 0.0
        count = self._failures.get(key, 0) + 1
        self._failures[key] = count
        if count >= self.failure_threshold:
            self._open[key] = now + self.open_for_seconds

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)
        self._open.pop(key, None)


__all__ = ["CircuitBreaker"]
