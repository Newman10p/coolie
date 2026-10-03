"""Supabase-backed repositories matching Research Room's existing contracts."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from research_room.config import SectorConfiguration
from research_room.controller import (
    MissionTransition,
    ResearchRoomController,
    SubmissionContext,
)
from research_room.models import (
    Evidence,
    MissionStatus,
    OpportunityRecord,
    ResearchMission,
    ResearchTask,
)
from research_room.repositories import (
    ConflictError,
    EvidenceRepository,
    MissionRepository,
    OpportunityRepository,
    ReportRepository,
    SourceSnapshot,
    SourceSnapshotRepository,
    TaskRepository,
    ResearchReport,
)

from .database import SupabasePostgres
from .repositories import MissionScopedPostgresRepository, PostgresJsonRepository
from .codec import decode_model, to_json_value
from psycopg.types.json import Jsonb


class PostgresMissionRepository(MissionRepository):
    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self._store = PostgresJsonRepository(
            database, workspace_id, table="research_missions", id_column="mission_id",
            model_type=ResearchMission, has_status=True,
        )

    def create(self, value: ResearchMission) -> ResearchMission:
        return self._store.create(value)

    def get(self, identifier: str) -> ResearchMission:
        return self._store.get(identifier)

    def replace(self, value: ResearchMission) -> ResearchMission:
        return self._store.replace(value)

    def all(self) -> tuple[ResearchMission, ...]:
        return self._store.all()


class PostgresTaskRepository(TaskRepository):
    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self._store = MissionScopedPostgresRepository(
            database, workspace_id, table="research_tasks", id_column="task_id",
            model_type=ResearchTask, has_status=True, has_mission=True,
        )

    def create(self, value: ResearchTask) -> ResearchTask:
        return self._store.create(value)

    def get(self, identifier: str) -> ResearchTask:
        return self._store.get(identifier)

    def replace(self, value: ResearchTask) -> ResearchTask:
        return self._store.replace(value)

    def all(self) -> tuple[ResearchTask, ...]:
        return self._store.all()

    def for_mission(self, mission_id: str) -> tuple[ResearchTask, ...]:
        return self._store.for_mission(mission_id)


class PostgresOpportunityRepository(OpportunityRepository):
    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self._store = MissionScopedPostgresRepository(
            database, workspace_id, table="opportunities", id_column="opportunity_id",
            model_type=OpportunityRecord, has_mission=True,
        )

    def create(self, value: OpportunityRecord) -> OpportunityRecord:
        return self._store.create(value)

    def get(self, identifier: str) -> OpportunityRecord:
        return self._store.get(identifier)

    def replace(self, value: OpportunityRecord) -> OpportunityRecord:
        return self._store.replace(value)

    def all(self) -> tuple[OpportunityRecord, ...]:
        return self._store.all()

    def for_mission(self, mission_id: str) -> tuple[OpportunityRecord, ...]:
        return self._store.for_mission(mission_id)


class PostgresEvidenceRepository(EvidenceRepository):
    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self._store = MissionScopedPostgresRepository(
            database, workspace_id, table="evidence_records", id_column="evidence_id",
            model_type=Evidence, has_mission=True, append_only=True,
        )

    def create_for_mission(self, mission_id: str, value: Evidence) -> Evidence:
        if not mission_id.strip():
            raise ValueError("mission_id is required.")
        return self._store.create(value, mission_id_override=mission_id)

    def create(self, value: Evidence) -> Evidence:
        raise ValueError(
            f"Evidence {value.evidence_id!r} must be created with a mission association."
        )

    def get(self, identifier: str) -> Evidence:
        return self._store.get(identifier)

    def all(self) -> tuple[Evidence, ...]:
        return self._store.all()

    def for_mission(self, mission_id: str) -> tuple[Evidence, ...]:
        return self._store.for_mission(mission_id)

class PostgresSourceSnapshotRepository(SourceSnapshotRepository):
    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self._store = MissionScopedPostgresRepository(
            database, workspace_id, table="source_snapshots", id_column="snapshot_id",
            model_type=SourceSnapshot, has_mission=True, append_only=True,
            order_column="retrieved_at",
            extra_columns=(
                "task_id", "source_reference", "retrieved_at", "content_hash",
                "artifact_key", "source_quality",
            ),
        )

    def create(self, value: SourceSnapshot) -> SourceSnapshot:
        return self._store.create(value)

    def get(self, identifier: str) -> SourceSnapshot:
        return self._store.get(identifier)

    def all(self) -> tuple[SourceSnapshot, ...]:
        return self._store.all()

    def for_mission(self, mission_id: str) -> tuple[SourceSnapshot, ...]:
        return self._store.for_mission(mission_id)

    def replace(self, value: SourceSnapshot) -> SourceSnapshot:
        raise ConflictError(f"Source snapshot {value.snapshot_id!r} is append-only.")


class PostgresReportRepository(ReportRepository):
    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self._store = MissionScopedPostgresRepository(
            database, workspace_id, table="research_reports", id_column="report_id",
            model_type=ResearchReport, has_mission=True, append_only=True,
            extra_columns=("created_at", "artifact_key", "content_hash"),
        )

    def create(self, value: ResearchReport) -> ResearchReport:
        return self._store.create(value)

    def get(self, identifier: str) -> ResearchReport:
        return self._store.get(identifier)

    def all(self) -> tuple[ResearchReport, ...]:
        return self._store.all()

    def for_mission(self, mission_id: str) -> tuple[ResearchReport, ...]:
        return self._store.for_mission(mission_id)

    def replace(self, value: ResearchReport) -> ResearchReport:
        raise ConflictError(f"Research report {value.report_id!r} is append-only.")


class PostgresConfigurationRepository:
    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self._store = PostgresJsonRepository(
            database, workspace_id, table="sector_configurations", id_column="version",
            model_type=SectorConfiguration, append_only=True,
        )

    def create(self, value: SectorConfiguration) -> SectorConfiguration:
        return self._store.create(value)

    def get(self, version: str) -> SectorConfiguration:
        return self._store.get(version)

    def all(self) -> tuple[SectorConfiguration, ...]:
        return self._store.all()

    def replace(self, value: SectorConfiguration) -> SectorConfiguration:
        raise ConflictError(f"Configuration {value.version!r} is append-only.")


class PostgresResearchRoomController(ResearchRoomController):
    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        super().__init__()
        self._database = database
        self._workspace_id = UUID(str(workspace_id))

    def transition(
        self,
        mission: ResearchMission,
        target: MissionStatus,
        *,
        actor_id: str,
        reason: str,
        tasks: list[ResearchTask] | None = None,
        submission_context: SubmissionContext | None = None,
        approval_context: str | None = None,
    ) -> None:
        previous_status = mission.status
        super().transition(
            mission,
            target,
            actor_id=actor_id,
            reason=reason,
            tasks=tasks,
            submission_context=submission_context,
            approval_context=approval_context,
        )
        transition = self._history[mission.mission_id][-1]
        try:
            with self._database.connection() as connection:
                connection.execute(
                    """
                    INSERT INTO public.research_mission_transitions
                        (workspace_id, mission_id, payload)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        self._workspace_id,
                        mission.mission_id,
                        Jsonb(to_json_value(transition)),
                    ),
                )
        except Exception:
            mission.status = previous_status
            self._history[mission.mission_id].pop()
            raise

    def history(self, mission_id: str) -> tuple[MissionTransition, ...]:
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT payload FROM public.research_mission_transitions
                WHERE workspace_id = %s AND mission_id = %s ORDER BY transition_id
                """,
                (self._workspace_id, mission_id),
            ).fetchall()
        return tuple(decode_model(row[0], MissionTransition) for row in rows)


@dataclass(frozen=True)
class PostgresResearchRepositories:
    missions: PostgresMissionRepository
    tasks: PostgresTaskRepository
    opportunities: PostgresOpportunityRepository
    evidence: PostgresEvidenceRepository
    source_snapshots: PostgresSourceSnapshotRepository
    reports: PostgresReportRepository
    configurations: PostgresConfigurationRepository
    controller: PostgresResearchRoomController

    @classmethod
    def connect(cls, database: SupabasePostgres, workspace_id: UUID) -> "PostgresResearchRepositories":
        return cls(
            PostgresMissionRepository(database, workspace_id),
            PostgresTaskRepository(database, workspace_id),
            PostgresOpportunityRepository(database, workspace_id),
            PostgresEvidenceRepository(database, workspace_id),
            PostgresSourceSnapshotRepository(database, workspace_id),
            PostgresReportRepository(database, workspace_id),
            PostgresConfigurationRepository(database, workspace_id),
            PostgresResearchRoomController(database, workspace_id),
        )
