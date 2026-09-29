from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .models import ComponentRecord, OperationalSnapshot


@dataclass(frozen=True)
class ReportCollectorReview:
    snapshot_id: str
    snapshot: OperationalSnapshot
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ReportCollectorController:
    def __init__(self) -> None:
        self._history: dict[str, OperationalSnapshot] = {}

    def discover(self, components: tuple[ComponentRecord, ...] | list[ComponentRecord]) -> ReportCollectorReview:
        records = tuple(components)
        if not records:
            raise ValueError("At least one component must be registered before generating a report.")
        healthy = sum(1 for component in records if component.status == "healthy")
        health_ratio = healthy / len(records)
        alert_count = sum(1 for component in records if component.status in {"warning", "critical", "offline"})
        summary = (
            "Operational snapshot is healthy." if health_ratio >= 0.8 else
            "Operational snapshot is degraded; action is recommended." if health_ratio >= 0.5 else
            "Operational snapshot is critical; immediate attention is required."
        )
        snapshot = OperationalSnapshot(
            snapshot_id=f"snapshot-{len(self._history) + 1}",
            components=records,
            summary=summary,
            health_ratio=health_ratio,
            alert_count=alert_count,
            orchestrator_ready=health_ratio >= 0.6,
        )
        self._history[snapshot.snapshot_id] = snapshot
        return ReportCollectorReview(snapshot.snapshot_id, snapshot)

    def discover_from_directory(self, root: str) -> ReportCollectorReview:
        path = Path(root)
        if not path.exists():
            raise ValueError(f"Directory does not exist: {root}")
        components = []
        for candidate in sorted(path.rglob("*.py")):
            if any(part in {".git", "__pycache__"} for part in candidate.parts):
                continue
            name = candidate.stem
            category = "python-module"
            status = "healthy"
            owner = candidate.parent.name or "unknown"
            details = f"Discovered {candidate.relative_to(path)}"
            components.append(ComponentRecord(name=name, category=category, status=status, owner=owner, details=details))
        if not components:
            raise ValueError(f"No Python modules were discovered under {root}.")
        return self.discover(tuple(components))

    def history(self, snapshot_id: str) -> OperationalSnapshot | None:
        return self._history.get(snapshot_id)
