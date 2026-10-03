from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
from math import isfinite
import re
import secrets
from threading import RLock
from typing import Any

from .models import (
    HealthStatus,
    Heartbeat,
    Incident,
    ReadinessStatus,
    ServiceHealth,
    StructuredLogRecord,
    now_utc,
)


class SystemPausedError(PermissionError):
    """Raised when a system-wide pause blocks new work."""


class SystemFailsafe:
    """Shared emergency pause gate. The same instance must be injected into sectors."""

    def __init__(self) -> None:
        self._reason: str | None = None
        self._paused_at: datetime | None = None
        self._lock = RLock()

    @property
    def paused(self) -> bool:
        with self._lock:
            return self._reason is not None

    @property
    def reason(self) -> str | None:
        with self._lock:
            return self._reason

    def pause(self, reason: str, *, authority: str) -> None:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Emergency-pause reason is required.")
        if not isinstance(authority, str) or not authority.strip():
            raise PermissionError("Emergency-pause authority is required.")
        with self._lock:
            self._reason = _sanitize_text(reason.strip())
            self._paused_at = now_utc()

    def resume(self, *, authority: str) -> None:
        if not isinstance(authority, str) or not authority.strip():
            raise PermissionError("Explicit restart authority is required.")
        with self._lock:
            if self._reason is None:
                raise ValueError("System is not paused.")
            self._reason = None
            self._paused_at = None

    def check(self, operation: str = "new work") -> None:
        with self._lock:
            if self._reason is not None:
                raise SystemPausedError(f"System is emergency-paused; {operation} is blocked.")

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "paused": self._reason is not None,
                "reason": self._reason,
                "paused_at": self._paused_at.isoformat() if self._paused_at else None,
            }


class HeartbeatRegistry:
    def __init__(self) -> None:
        self._heartbeats: dict[str, Heartbeat] = {}
        self._startup: dict[str, tuple[bool, str]] = {}
        self._dependencies: dict[str, dict[str, HealthStatus]] = {}
        self._lock = RLock()

    def register(
        self,
        component_id: str,
        *,
        sector_id: str,
        instance_id: str,
        interval_seconds: float = 15,
        dependencies: tuple[str, ...] = (),
        startup_checks: dict[str, bool] | None = None,
        now: datetime | None = None,
    ) -> Heartbeat:
        if not component_id.strip() or not sector_id.strip() or not instance_id.strip():
            raise ValueError("component_id, sector_id, and instance_id are required.")
        if (
            isinstance(interval_seconds, bool)
            or not isinstance(interval_seconds, (int, float))
            or not isfinite(interval_seconds)
            or interval_seconds <= 0
        ):
            raise ValueError("interval_seconds must be positive.")
        checks = startup_checks or {}
        if any(not isinstance(passed, bool) for passed in checks.values()):
            raise ValueError("startup check results must be booleans.")
        failed = tuple(name for name, passed in checks.items() if not passed)
        startup_ok = not failed
        reason = "startup checks passed" if startup_ok else f"startup checks failed: {', '.join(failed)}"
        at = now or now_utc()
        heartbeat = Heartbeat(
            component_id=component_id,
            sector_id=sector_id,
            instance_id=instance_id,
            status=HealthStatus.HEALTHY if startup_ok else HealthStatus.DEGRADED,
            sequence=1,
            interval_seconds=float(interval_seconds),
            last_seen_at=at,
            last_progress_at=at,
        )
        with self._lock:
            current = self._heartbeats.get(component_id)
            if current is not None:
                age = max(0.0, (at - current.last_seen_at).total_seconds())
                if current.instance_id == instance_id or (
                    current.status is not HealthStatus.DEAD
                    and age <= current.interval_seconds * 8
                ):
                    raise ValueError(f"Component already has a live registered instance: {component_id}")
            self._heartbeats[component_id] = heartbeat
            self._startup[component_id] = startup_ok, reason
            self._dependencies[component_id] = {
                dependency: HealthStatus.HEALTHY for dependency in dependencies
            }
        return heartbeat

    def heartbeat(
        self,
        component_id: str,
        *,
        instance_id: str,
        status: HealthStatus = HealthStatus.HEALTHY,
        current_task_id: str | None = None,
        progress: bool = False,
        queue_depth: int | None = None,
        active_tasks: int | None = None,
        now: datetime | None = None,
    ) -> Heartbeat:
        at = now or now_utc()
        with self._lock:
            current = self._heartbeats.get(component_id)
            if current is None:
                raise KeyError(f"Component is not registered: {component_id}")
            if current.instance_id != instance_id:
                raise PermissionError("Heartbeat instance does not match the registered instance.")
            update = replace(
                current,
                status=status,
                sequence=current.sequence + 1,
                last_seen_at=at,
                last_progress_at=at if progress else current.last_progress_at,
                current_task_id=current_task_id,
                queue_depth=queue_depth,
                active_tasks=active_tasks,
            )
            self._heartbeats[component_id] = update
            return update

    def set_dependency(self, component_id: str, dependency: str, status: HealthStatus) -> None:
        if not dependency.strip():
            raise ValueError("dependency must be a non-empty string.")
        with self._lock:
            if component_id not in self._heartbeats:
                raise KeyError(f"Component is not registered: {component_id}")
            self._dependencies[component_id][dependency] = status

    def health(
        self,
        component_id: str,
        *,
        paused: bool = False,
        now: datetime | None = None,
        progress_timeout_intervals: float = 8,
    ) -> ServiceHealth:
        at = now or now_utc()
        with self._lock:
            heartbeat = self._heartbeats.get(component_id)
            startup = self._startup.get(component_id)
            dependencies = dict(self._dependencies.get(component_id, {}))
        if heartbeat is None or startup is None:
            raise KeyError(f"Component is not registered: {component_id}")
        startup_complete, startup_reason = startup
        age = max(0.0, (at - heartbeat.last_seen_at).total_seconds())
        clock_skew = at < heartbeat.last_seen_at
        if heartbeat.status is HealthStatus.DEAD or age > heartbeat.interval_seconds * 8:
            status = HealthStatus.DEAD
            reason = "heartbeat expired"
            liveness = False
        elif heartbeat.status is HealthStatus.STALLED or (
            heartbeat.current_task_id is not None
            and heartbeat.last_progress_at is not None
            and (at - heartbeat.last_progress_at).total_seconds()
            > heartbeat.interval_seconds * progress_timeout_intervals
        ):
            status = HealthStatus.STALLED
            reason = "component has not reported meaningful progress"
            liveness = True
        elif age > heartbeat.interval_seconds * 4:
            status = HealthStatus.STALLED
            reason = "heartbeat is stale"
            liveness = True
        elif age > heartbeat.interval_seconds * 2 or heartbeat.status is HealthStatus.DEGRADED:
            status = HealthStatus.DEGRADED
            reason = "heartbeat is delayed or component reports degraded"
            liveness = True
        elif clock_skew:
            status = HealthStatus.DEGRADED
            reason = "heartbeat timestamp is ahead of the health-check clock"
            liveness = True
        else:
            status = heartbeat.status
            reason = startup_reason
            liveness = heartbeat.status is not HealthStatus.DEAD
        failed_dependencies = {
            name: value for name, value in dependencies.items()
            if value is not HealthStatus.HEALTHY
        }
        if paused:
            status = HealthStatus.PAUSED
            reason = "system emergency pause is active"
        elif not startup_complete:
            status = HealthStatus.DEGRADED
            reason = startup_reason
        elif failed_dependencies and status is not HealthStatus.DEAD:
            status = HealthStatus.DEGRADED
            reason = "one or more dependencies are degraded"
        ready = (
            startup_complete
            and not paused
            and not failed_dependencies
            and status is HealthStatus.HEALTHY
            and liveness
        )
        return ServiceHealth(
            service=component_id,
            liveness=liveness,
            startup_complete=startup_complete,
            readiness=ReadinessStatus.READY if ready else ReadinessStatus.NOT_READY,
            status=status,
            reason=reason,
            dependencies=dependencies,
            heartbeat=heartbeat,
            checked_at=at,
        )

    def registered(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._heartbeats))


class ReliabilityRuntime:
    def __init__(self, *, failsafe: SystemFailsafe | None = None) -> None:
        self.failsafe = failsafe or SystemFailsafe()
        self.heartbeats = HeartbeatRegistry()
        self._logs: list[StructuredLogRecord] = []
        self._incidents: list[Incident] = []
        self._lock = RLock()

    def ensure_work_allowed(self, operation: str = "new work") -> None:
        self.failsafe.check(operation)

    def emergency_pause(self, reason: str, *, authority: str) -> None:
        self.failsafe.pause(reason, authority=authority)
        self.incident(
            source="system",
            severity="critical",
            summary=f"Emergency pause enabled: {reason.strip()}",
        )

    def resume(self, *, authority: str) -> None:
        self.failsafe.resume(authority=authority)
        self.record(
            event_name="system.emergency_restarted",
            service="reliability",
            sector="system",
            severity="warning",
            message="System emergency pause was cleared by an authorized operator.",
            data={"authority": authority},
        )

    def health(self, component_id: str, *, now: datetime | None = None) -> ServiceHealth:
        return self.heartbeats.health(component_id, paused=self.failsafe.paused, now=now)

    def health_snapshot(self, *, now: datetime | None = None) -> tuple[ServiceHealth, ...]:
        return tuple(self.health(component_id, now=now) for component_id in self.heartbeats.registered())

    def record(
        self,
        *,
        event_name: str,
        service: str,
        sector: str,
        severity: str,
        message: str,
        trace_id: str | None = None,
        request_id: str | None = None,
        task_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> StructuredLogRecord:
        record = StructuredLogRecord(
            event_name=event_name,
            service=service,
            sector=sector,
            severity=severity,
            message=_sanitize_text(message),
            trace_id=trace_id,
            request_id=request_id,
            task_id=task_id,
            data=_redact(data or {}),
        )
        with self._lock:
            self._logs.append(record)
        return record

    def incident(self, *, source: str, severity: str, summary: str, trace_id: str | None = None) -> Incident:
        incident = Incident(
            incident_id=f"incident-{secrets.token_hex(8)}",
            source=source,
            severity=severity,
            summary=_sanitize_text(summary),
            trace_id=trace_id,
        )
        with self._lock:
            self._incidents.append(incident)
        self.record(
            event_name="incident.detected",
            service=source,
            sector=source,
            severity=severity,
            message=summary,
            trace_id=trace_id,
            data={"incident_id": incident.incident_id},
        )
        return incident

    def logs(self) -> tuple[StructuredLogRecord, ...]:
        with self._lock:
            return tuple(self._logs)

    def incidents(self) -> tuple[Incident, ...]:
        with self._lock:
            return tuple(self._incidents)


_DEFAULT_RUNTIME = ReliabilityRuntime()


def default_reliability_runtime() -> ReliabilityRuntime:
    """Return the process-wide failsafe used by default sector compositions."""
    return _DEFAULT_RUNTIME


_SENSITIVE_KEYS = ("password", "secret", "token", "credential", "api_key", "apikey")


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "******" if any(token in str(key).lower() for token in _SENSITIVE_KEYS) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    try:
        json.dumps(value, allow_nan=False)
        return _sanitize_text(value) if isinstance(value, str) else deepcopy(value)
    except (TypeError, ValueError):
        return f"<{type(value).__name__}>"


_SECRET_TEXT = re.compile(
    r"(?i)\b(password|secret|token|credential|api[_-]?key)\b(\s*[:=]\s*|\s+)([^\s,;]+)"
)


def _sanitize_text(value: str) -> str:
    return _SECRET_TEXT.sub(r"\1\2******", value)
