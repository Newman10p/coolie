"""Durable workspace-scoped failsafe, incident, and structured log adapters."""

from __future__ import annotations

import secrets
from threading import RLock
from typing import Any

from reliability.models import Incident, StructuredLogRecord
from reliability.runtime import (
    ReliabilityRuntime,
    SystemFailsafe,
    _redact,
    _sanitize_text,
)

from .domain import PostgresDomainPersistence


class PostgresSystemFailsafe(SystemFailsafe):
    """Reads pause state from Postgres on each gate check for cross-process safety."""

    def __init__(self, persistence: PostgresDomainPersistence) -> None:
        super().__init__()
        self._persistence = persistence

    @property
    def paused(self) -> bool:
        return self._persistence.system_state()[0]

    @property
    def reason(self) -> str | None:
        return self._persistence.system_state()[1]

    def pause(self, reason: str, *, authority: str) -> None:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Emergency-pause reason is required.")
        if not isinstance(authority, str) or not authority.strip():
            raise PermissionError("Emergency-pause authority is required.")
        sanitized = _sanitize_text(reason.strip())
        self._persistence.set_system_state(paused=True, reason=sanitized)

    def resume(self, *, authority: str) -> None:
        if not isinstance(authority, str) or not authority.strip():
            raise PermissionError("Explicit restart authority is required.")
        if not self.paused:
            raise ValueError("System is not paused.")
        self._persistence.set_system_state(paused=False, reason=None)

    def check(self, operation: str = "new work") -> None:
        if self.paused:
            from reliability.runtime import SystemPausedError

            raise SystemPausedError(
                f"System is emergency-paused; {operation} is blocked."
            )

    def snapshot(self) -> dict[str, object]:
        paused, reason, paused_at = self._persistence.system_state()
        return {
            "paused": paused,
            "reason": reason,
            "paused_at": paused_at.isoformat() if paused_at else None,
        }


class PostgresReliabilityRuntime(ReliabilityRuntime):
    def __init__(self, persistence: PostgresDomainPersistence) -> None:
        self._persistence = persistence
        self._log_lock = RLock()
        super().__init__(failsafe=PostgresSystemFailsafe(persistence))

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
        self._persistence.append_event(
            "reliability_logs",
            service,
            secrets.token_urlsafe(18),
            record,
        )
        return record

    def incident(
        self,
        *,
        source: str,
        severity: str,
        summary: str,
        trace_id: str | None = None,
    ) -> Incident:
        incident = Incident(
            incident_id=f"incident-{secrets.token_hex(8)}",
            source=source,
            severity=severity,
            summary=_sanitize_text(summary),
            trace_id=trace_id,
        )
        self._persistence.append_event(
            "reliability_incidents", source, incident.incident_id, incident
        )
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
        return self._persistence.events("reliability_logs", StructuredLogRecord)

    def incidents(self) -> tuple[Incident, ...]:
        return self._persistence.events("reliability_incidents", Incident)
