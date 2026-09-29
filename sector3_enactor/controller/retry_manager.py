"""Bounded retry policy for connector calls."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetryManager:
    max_attempts: int = 3
    backoff_seconds: float = 1.0

    def should_retry(self, attempt: int, *, is_external_action: bool = False, has_idempotency_key: bool = False) -> bool:
        if is_external_action and not has_idempotency_key:
            return False
        return attempt < self.max_attempts

    def delay_for(self, attempt: int) -> float:
        return self.backoff_seconds * max(1, attempt)


__all__ = ["RetryManager"]
