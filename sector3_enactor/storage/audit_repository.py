"""Append-only audit log with a hash chain covering the FULL traceability chain
(document §8.5): plan → execution → task → agent → tool call → connector account →
approval → external operation → result. Denials are audited too."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..policy.hashing import digest


@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    event_type: str            # gateway_call | denial | state_transition | approval_decision | deployment | budget | escalation | outcome
    business_id: str
    execution_id: str
    task_id: str | None
    agent_id: str | None
    tool: str | None
    connector_account: str | None
    approval_id: str | None
    external_operation_id: str | None
    payload_hash: str
    detail: dict[str, Any] = field(default_factory=dict)
    previous_hash: str = ""
    event_hash: str = ""
    recorded_at: datetime | None = None


class AuditRepository:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, *, event_type: str, business_id: str, execution_id: str, detail: dict[str, Any],
               task_id: str | None = None, agent_id: str | None = None, tool: str | None = None,
               connector_account: str | None = None, approval_id: str | None = None,
               external_operation_id: str | None = None, recorded_at: datetime | None = None) -> AuditEvent:
        if not event_type.strip() or not business_id.strip() or not execution_id.strip():
            raise ValueError("Audit events require event_type, business_id and execution_id.")
        previous_hash = self._events[-1].event_hash if self._events else "sha256:genesis"
        core = {
            "sequence": len(self._events), "event_type": event_type, "business_id": business_id,
            "execution_id": execution_id, "task_id": task_id, "agent_id": agent_id, "tool": tool,
            "connector_account": connector_account, "approval_id": approval_id,
            "external_operation_id": external_operation_id, "payload": detail,
            "previous_hash": previous_hash,
        }
        event = AuditEvent(sequence=core["sequence"], event_type=event_type, business_id=business_id,
                           execution_id=execution_id, task_id=task_id, agent_id=agent_id, tool=tool,
                           connector_account=connector_account, approval_id=approval_id,
                           external_operation_id=external_operation_id, payload_hash=digest(detail),
                           detail=dict(detail), previous_hash=previous_hash,
                           event_hash=digest(core), recorded_at=recorded_at)
        self._events.append(event)
        return event

    def events_for_execution(self, execution_id: str) -> tuple[AuditEvent, ...]:
        return tuple(event for event in self._events if event.execution_id == execution_id)

    def all_events(self) -> tuple[AuditEvent, ...]:
        return tuple(self._events)

    def verify_chain(self) -> bool:
        previous = "sha256:genesis"
        for index, event in enumerate(self._events):
            if event.sequence != index or event.previous_hash != previous: return False
            core = {"sequence": event.sequence, "event_type": event.event_type, "business_id": event.business_id,
                    "execution_id": event.execution_id, "task_id": event.task_id, "agent_id": event.agent_id,
                    "tool": event.tool, "connector_account": event.connector_account, "approval_id": event.approval_id,
                    "external_operation_id": event.external_operation_id, "payload": event.detail,
                    "previous_hash": event.previous_hash}
            if event.event_hash != digest(core): return False
            previous = event.event_hash
        return True
