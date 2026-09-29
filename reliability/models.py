from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Any


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STALLED = "stalled"
    DEAD = "dead"
    PAUSED = "paused"


class ReadinessStatus(str, Enum):
    READY = "ready"
    NOT_READY = "not_ready"


@dataclass(frozen=True)
class Heartbeat:
    component_id: str
    sector_id: str
    instance_id: str
    status: HealthStatus
    sequence: int
    interval_seconds: float
    last_seen_at: datetime = field(default_factory=now_utc)
    last_progress_at: datetime | None = None
    current_task_id: str | None = None
    queue_depth: int | None = None
    active_tasks: int | None = None

    def __post_init__(self) -> None:
        for name in ("component_id", "sector_id", "instance_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")
        if not isinstance(self.status, HealthStatus):
            raise ValueError("status must be a HealthStatus.")
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 1:
            raise ValueError("sequence must be a positive integer.")
        if (
            isinstance(self.interval_seconds, bool)
            or not isinstance(self.interval_seconds, (int, float))
            or not isfinite(self.interval_seconds)
            or self.interval_seconds <= 0
        ):
            raise ValueError("interval_seconds must be positive.")
        for name in ("last_seen_at", "last_progress_at"):
            value = getattr(self, name)
            if value is not None and value.tzinfo is None:
                raise ValueError(f"{name} must be timezone-aware.")
        if self.queue_depth is not None and (
            isinstance(self.queue_depth, bool) or not isinstance(self.queue_depth, int) or self.queue_depth < 0
        ):
            raise ValueError("queue_depth must be a non-negative integer.")
        if self.active_tasks is not None and (
            isinstance(self.active_tasks, bool) or not isinstance(self.active_tasks, int) or self.active_tasks < 0
        ):
            raise ValueError("active_tasks must be a non-negative integer.")


@dataclass(frozen=True)
class ServiceHealth:
    service: str
    liveness: bool
    startup_complete: bool
    readiness: ReadinessStatus
    status: HealthStatus
    reason: str
    dependencies: dict[str, HealthStatus]
    heartbeat: Heartbeat | None
    checked_at: datetime = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        if self.checked_at.tzinfo is None:
            raise ValueError("checked_at must be timezone-aware.")


@dataclass(frozen=True)
class Incident:
    incident_id: str
    source: str
    severity: str
    summary: str
    trace_id: str | None = None
    created_at: datetime = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        for name in ("incident_id", "source", "severity", "summary"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")


@dataclass(frozen=True)
class StructuredLogRecord:
    event_name: str
    service: str
    sector: str
    severity: str
    message: str
    trace_id: str | None = None
    request_id: str | None = None
    task_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        for name in ("event_name", "service", "sector", "severity", "message"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware.")
