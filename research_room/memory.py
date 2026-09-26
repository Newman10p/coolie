"""Append-only learning records; historical research artifacts are never rewritten."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class OutcomeRecord:
    mission_id: str
    opportunity_id: str
    outcome: str
    assumptions_wrong: tuple[str, ...]
    recorded_at: datetime


class ResearchMemory:
    def __init__(self) -> None: self._outcomes: list[OutcomeRecord] = []
    def record_outcome(self, mission_id: str, opportunity_id: str, outcome: str, assumptions_wrong: tuple[str, ...] = ()) -> OutcomeRecord:
        if not mission_id.strip() or not opportunity_id.strip() or not outcome.strip(): raise ValueError("Outcome identity and outcome are required.")
        record = OutcomeRecord(mission_id, opportunity_id, outcome, assumptions_wrong, datetime.now(timezone.utc))
        self._outcomes.append(record); return record
    def for_mission(self, mission_id: str) -> tuple[OutcomeRecord, ...]: return tuple(record for record in self._outcomes if record.mission_id == mission_id)
