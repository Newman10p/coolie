"""Repository contracts and deterministic in-memory implementations for application services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Generic, Protocol, TypeVar

from .config import SectorConfiguration
from .models import Evidence, OpportunityRecord, ResearchMission, ResearchTask
from .policy import ToolCallAudit


T = TypeVar("T")


class NotFoundError(KeyError): pass
class ConflictError(ValueError): pass


class Repository(Protocol[T]):
    def create(self, value: T) -> T: ...
    def get(self, identifier: str) -> T: ...


class InMemoryRepository(Generic[T]):
    def __init__(self, id_attribute: str) -> None:
        self._id_attribute = id_attribute; self._values: dict[str, T] = {}

    def create(self, value: T) -> T:
        identifier = getattr(value, self._id_attribute)
        if identifier in self._values: raise ConflictError(f"{self._id_attribute} already exists: {identifier}")
        self._values[identifier] = value
        return value

    def get(self, identifier: str) -> T:
        try: return self._values[identifier]
        except KeyError as error: raise NotFoundError(identifier) from error

    def replace(self, value: T) -> T:
        identifier = getattr(value, self._id_attribute)
        if identifier not in self._values: raise NotFoundError(identifier)
        self._values[identifier] = value
        return value

    def all(self) -> tuple[T, ...]: return tuple(self._values.values())


class MissionRepository(InMemoryRepository[ResearchMission]):
    def __init__(self) -> None: super().__init__("mission_id")


class OpportunityRepository(InMemoryRepository[OpportunityRecord]):
    def __init__(self) -> None: super().__init__("opportunity_id")
    def for_mission(self, mission_id: str) -> tuple[OpportunityRecord, ...]: return tuple(value for value in self.all() if value.mission_id == mission_id)


class TaskRepository(InMemoryRepository[ResearchTask]):
    def __init__(self) -> None: super().__init__("task_id")
    def for_mission(self, mission_id: str) -> tuple[ResearchTask, ...]: return tuple(value for value in self.all() if value.mission_id == mission_id)


@dataclass(frozen=True)
class SourceSnapshot:
    snapshot_id: str
    mission_id: str
    task_id: str
    source_reference: str
    retrieved_at: datetime
    content_hash: str
    artifact_key: str
    source_quality: float

    def __post_init__(self) -> None:
        if any(not value.strip() for value in (self.snapshot_id, self.mission_id, self.task_id, self.source_reference, self.content_hash, self.artifact_key)):
            raise ValueError("Source snapshot identity fields must be non-empty.")
        if self.retrieved_at.tzinfo is None: raise ValueError("Source snapshots require timezone-aware retrieval times.")
        if isinstance(self.source_quality, bool) or not isinstance(self.source_quality, (int, float)) or not isfinite(self.source_quality) or not 0 <= self.source_quality <= 1:
            raise ValueError("source_quality must be between 0 and 1.")


@dataclass(frozen=True)
class ResearchReport:
    report_id: str
    mission_id: str
    created_at: datetime
    artifact_key: str
    content_hash: str

    def __post_init__(self) -> None:
        if any(not value.strip() for value in (self.report_id, self.mission_id, self.artifact_key, self.content_hash)):
            raise ValueError("Report identity fields must be non-empty.")
        if self.created_at.tzinfo is None: raise ValueError("Reports require timezone-aware creation times.")


class AppendOnlyRepository(InMemoryRepository[T]):
    def replace(self, value: T) -> T:
        raise ConflictError("This repository is append-only.")


class EvidenceRepository(AppendOnlyRepository[Evidence]):
    def __init__(self) -> None:
        super().__init__("evidence_id"); self._mission_by_evidence: dict[str, str] = {}
    def create_for_mission(self, mission_id: str, value: Evidence) -> Evidence:
        if not mission_id.strip(): raise ValueError("mission_id is required.")
        created = super().create(value)
        self._mission_by_evidence[value.evidence_id] = mission_id
        return created
    def create(self, value: Evidence) -> Evidence:
        raise ValueError("Evidence must be created with a mission association.")
    def for_mission(self, mission_id: str) -> tuple[Evidence, ...]:
        return tuple(value for value in self.all() if self._mission_by_evidence[value.evidence_id] == mission_id)


class SourceSnapshotRepository(AppendOnlyRepository[SourceSnapshot]):
    def __init__(self) -> None: super().__init__("snapshot_id")
    def for_mission(self, mission_id: str) -> tuple[SourceSnapshot, ...]: return tuple(value for value in self.all() if value.mission_id == mission_id)


class ReportRepository(AppendOnlyRepository[ResearchReport]):
    def __init__(self) -> None: super().__init__("report_id")
    def for_mission(self, mission_id: str) -> tuple[ResearchReport, ...]: return tuple(value for value in self.all() if value.mission_id == mission_id)


class AuditRepository:
    def __init__(self) -> None: self._events: list[ToolCallAudit] = []
    def append(self, event: ToolCallAudit) -> ToolCallAudit:
        self._events.append(event); return event
    def for_mission(self, mission_id: str) -> tuple[ToolCallAudit, ...]: return tuple(event for event in self._events if event.mission_id == mission_id)


class ConfigurationRepository:
    def __init__(self) -> None: self._values: dict[str, SectorConfiguration] = {}
    def create(self, configuration: SectorConfiguration) -> SectorConfiguration:
        if configuration.version in self._values: raise ConflictError(f"Configuration version already exists: {configuration.version}")
        self._values[configuration.version] = configuration; return configuration
    def get(self, version: str) -> SectorConfiguration:
        try: return self._values[version]
        except KeyError as error: raise NotFoundError(version) from error
