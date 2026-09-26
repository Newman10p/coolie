"""Immutable JSON research reports generated from persisted mission artifacts."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json

from .artifacts import ObjectStorage
from .repositories import ReportRepository, ResearchReport


class ReportGenerator:
    def __init__(self, storage: ObjectStorage, reports: ReportRepository) -> None:
        self._storage = storage; self._reports = reports
    def create(self, report_id: str, mission_id: str, payload: dict[str, object]) -> ResearchReport:
        content = json.dumps(payload, default=str, sort_keys=True, separators=(",", ":")).encode("utf-8")
        artifact = self._storage.put_immutable(f"reports/{mission_id}/{report_id}.json", content, "application/json")
        report = ResearchReport(report_id, mission_id, datetime.now(timezone.utc), artifact.key, artifact.content_hash)
        return self._reports.create(report)
