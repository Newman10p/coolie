from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


def _nonempty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")


@dataclass(frozen=True)
class ComponentRecord:
    name: str
    category: str
    status: Literal["healthy", "warning", "critical", "offline"]
    owner: str
    details: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _nonempty(self.name, "name")
        _nonempty(self.category, "category")
        _nonempty(self.owner, "owner")
        if self.status not in {"healthy", "warning", "critical", "offline"}:
            raise ValueError("status must be healthy, warning, critical, or offline.")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware.")


@dataclass(frozen=True)
class OperationalSnapshot:
    snapshot_id: str
    components: tuple[ComponentRecord, ...]
    summary: str
    health_ratio: float
    alert_count: int
    orchestrator_ready: bool
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _nonempty(self.snapshot_id, "snapshot_id")
        _nonempty(self.summary, "summary")
        if not isinstance(self.components, tuple):
            raise ValueError("components must be a tuple.")
        if not 0 <= float(self.health_ratio) <= 1:
            raise ValueError("health_ratio must be between 0 and 1.")
        if isinstance(self.alert_count, bool) or not isinstance(self.alert_count, int) or self.alert_count < 0:
            raise ValueError("alert_count must be a non-negative integer.")
        if not isinstance(self.orchestrator_ready, bool):
            raise ValueError("orchestrator_ready must be a boolean.")
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware.")
