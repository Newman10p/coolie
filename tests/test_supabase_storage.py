from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import UUID

from research_room.models import MissionStatus, ResearchMission, SourcePolicy
from brain.events import EventBus
from brain.memory import MemoryStore
from brain.models import (
    AgentDefinition,
    BrainOperation,
    DataSensitivity,
    MemoryRecord,
)
from evolver.controller import EvolverController
from evolver.models import ExpansionRequest
from money_calculator.controller import MoneyCalculatorController
from money_calculator.models import ActivationProposal
from orchestrator.controller import OrchestratorController
from orchestrator.models import (
    OwnerObjective,
    ShariaStatus,
)
from report_collector.controller import ReportCollectorController
from report_collector.models import ComponentRecord
from supabase_storage.codec import decode_model, to_json_value
from supabase_storage.database import (
    SupabaseConfigurationError,
    create_database_from_env,
)
from supabase_storage.enactor import PostgresAuditRepository
from supabase_storage.repositories import (
    MissionScopedPostgresRepository,
    PostgresJsonRepository,
)
from supabase_storage.research import PostgresResearchRoomController
from research_room.models import Money


WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000001")


class FakeConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.next_row: tuple[object, ...] | None = None
        self.next_rows: list[tuple[object, ...]] = []

    def execute(self, query: str, parameters=()):
        values = tuple(parameters)
        self.calls.append((query, values))
        if "INSERT INTO public.research_mission_transitions" in query:
            self.next_rows = [(values[2].obj,)]
        return self

    def fetchone(self):
        return self.next_row

    def fetchall(self):
        return self.next_rows


class FakeDatabase:
    def __init__(self) -> None:
        self.connection_value = FakeConnection()

    @contextmanager
    def connection(self):
        yield self.connection_value


class FakeAuditConnection:
    def __init__(self) -> None:
        self.events: list[tuple[object, ...]] = []
        self.result: tuple[object, ...] | None = None
        self.rows: list[tuple[object, ...]] = []

    def execute(self, query: str, parameters=()):
        values = tuple(parameters)
        if "ORDER BY sequence DESC LIMIT 1" in query:
            self.result = (
                (self.events[-1][0], self.events[-1][1])
                if self.events
                else None
            )
        elif "INSERT INTO public.audit_events" in query:
            self.events.append((values[1], values[13]))
            self.rows.append(
                (
                    values[1], values[2], values[3], values[4], values[5],
                    values[6], values[7], values[8], values[9], values[10],
                    values[11], values[14].obj, values[12], values[13], values[15],
                )
            )
            self.result = None
        elif "FROM public.audit_events WHERE workspace_id = %s ORDER BY sequence" in query:
            self.rows.sort(key=lambda row: row[0])
        return self

    def fetchone(self):
        return self.result

    def fetchall(self):
        return list(self.rows)


class FakeAuditDatabase:
    def __init__(self) -> None:
        self.connection_value = FakeAuditConnection()

    @contextmanager
    def connection(self):
        yield self.connection_value


class FakeDomainPersistence:
    def __init__(self) -> None:
        self.records: dict[tuple[str, str], object] = {}
        self.streams: list[tuple[str, str, str, object]] = []

    def put_record(self, record_type: str, record_id: str, value: object) -> None:
        self.records[(record_type, record_id)] = value

    def insert_record(self, record_type: str, record_id: str, value: object) -> None:
        key = (record_type, record_id)
        if key in self.records:
            raise ValueError(f"{record_type} already exists: {record_id}")
        self.records[key] = value

    def get_record(self, record_type: str, record_id: str, model_type):
        return self.records[(record_type, record_id)]

    def maybe_record(self, record_type: str, record_id: str, model_type):
        return self.records.get((record_type, record_id))

    def all_records(self, record_type: str, model_type):
        return tuple(
            value for (kind, _), value in self.records.items() if kind == record_type
        )

    def record_ids(self, record_type: str):
        return tuple(
            record_id
            for (kind, record_id) in self.records
            if kind == record_type
        )

    def get_payload(self, record_type: str, record_id: str):
        return self.records[(record_type, record_id)]

    def delete_record(self, record_type: str, record_id: str) -> None:
        del self.records[(record_type, record_id)]

    def append_event(
        self, stream_name: str, stream_key: str, event_id: str, value: object
    ) -> None:
        if any(
            kind == stream_name and identifier == event_id
            for kind, _, identifier, _ in self.streams
        ):
            raise ValueError(f"Duplicate {stream_name} event: {event_id}")
        self.streams.append((stream_name, stream_key, event_id, value))

    def events(self, stream_name: str, model_type, *, stream_key: str | None = None):
        return tuple(
            value
            for kind, key, _, value in self.streams
            if kind == stream_name and (stream_key is None or key == stream_key)
        )


def make_mission() -> ResearchMission:
    return ResearchMission(
        mission_id="mission-1",
        objective="Assess a test market",
        requested_by="human",
        markets=["US"],
        business_models=["direct"],
        risk_tolerance="low",
        required_evidence_level="basic",
        allowed_sources=SourcePolicy(
            allowed_source_types=frozenset({"web", "api"}),
            allow_paid_sources=False,
        ),
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        status=MissionStatus.PLANNING,
    )


class SupabaseCodecTests(unittest.TestCase):
    def test_nested_research_models_round_trip(self) -> None:
        mission = make_mission()
        self.assertEqual(decode_model(to_json_value(mission), ResearchMission), mission)

    def test_json_rejects_non_finite_numbers(self) -> None:
        with self.assertRaises(ValueError):
            to_json_value(float("nan"))

    def test_missing_workspace_fails_before_database_connect(self) -> None:
        with TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "SUPABASE_URL=https://example.supabase.co\n"
                "SUPABASE_REGION=us-east-1\n"
                "SUPABASE_DB_PASSWORD=placeholder\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                SupabaseConfigurationError, "COOLIE_WORKSPACE_ID is required"
            ):
                create_database_from_env(env_file=env_file, environ={})

    def test_brain_memory_and_events_survive_adapter_recreation(self) -> None:
        persistence = FakeDomainPersistence()
        agent = AgentDefinition(
            "agent-1",
            "research_room",
            "researcher",
            frozenset({BrainOperation.RETRIEVE, BrainOperation.MEMORY_WRITE}),
            frozenset({"model-1"}),
            frozenset({"research"}),
            100,
            Money(1, "USD"),
        )
        memory = MemoryStore(persistence)
        record = MemoryRecord(
            "memory-1",
            "research",
            {"fact": "market"},
            DataSensitivity.INTERNAL,
            "source-1",
        )
        memory.write(agent, record)
        restored_memory = MemoryStore(persistence)
        self.assertEqual(restored_memory.get(agent, "memory-1"), record)

        events = EventBus(persistence)
        event = events.publish(
            "brain.test",
            source="brain",
            payload={"status": "ok"},
            correlation_id="request-1",
        )
        restored_events = EventBus(persistence)
        self.assertEqual(restored_events.events(), (event,))


class SupabaseDomainHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.persistence = FakeDomainPersistence()

    def test_finance_and_orchestrator_histories_are_durable(self) -> None:
        proposal = ActivationProposal(
            "proposal-1",
            "Controlled launch",
            "owner",
            Money(10, "USD"),
            Money(20, "USD"),
            30,
            0.9,
        )
        finance = MoneyCalculatorController(self.persistence)
        recommendation = finance.assess(proposal).decision
        self.assertEqual(
            MoneyCalculatorController(self.persistence).history("proposal-1"),
            (recommendation,),
        )

        objective = OwnerObjective("objective-1", "owner", "Launch", "Pilot")
        orchestrator = OrchestratorController(self.persistence)
        decision = orchestrator.review_objective(
            objective,
            sharia_status=ShariaStatus.COMPLIANT,
            evidence_confidence=0.9,
            budget_approved=True,
            operational_risk="low",
        ).decision
        self.assertEqual(
            OrchestratorController(self.persistence).history("objective-1"),
            (decision,),
        )

    def test_evolver_and_report_collector_histories_are_durable(self) -> None:
        request = ExpansionRequest(
            "request-1",
            "education",
            "Extend service",
            ("scheduling",),
            expected_monthly_revenue=Money(10_000, "USD"),
        )
        plan = EvolverController(self.persistence).assess(request).plan
        self.assertEqual(EvolverController(self.persistence).history("request-1"), plan)

        controller = ReportCollectorController(self.persistence)
        snapshot = controller.discover(
            (ComponentRecord("api", "service", "healthy", "platform"),)
        ).snapshot
        restored = ReportCollectorController(self.persistence)
        self.assertEqual(restored.history(snapshot.snapshot_id), snapshot)


class SupabaseRepositoryScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = FakeDatabase()

    def test_create_and_get_always_include_workspace_id(self) -> None:
        mission = make_mission()
        self.database.connection_value.next_row = (mission.mission_id,)
        repository = PostgresJsonRepository(
            self.database,
            WORKSPACE_ID,
            table="research_missions",
            id_column="mission_id",
            model_type=ResearchMission,
            has_status=True,
        )

        repository.create(mission)
        self.database.connection_value.next_row = (to_json_value(mission),)
        repository.get(mission.mission_id)

        insert_query, insert_parameters = self.database.connection_value.calls[0]
        select_query, select_parameters = self.database.connection_value.calls[1]
        self.assertIn("workspace_id", insert_query)
        self.assertEqual(insert_parameters[0], WORKSPACE_ID)
        self.assertIn("workspace_id = %s", select_query)
        self.assertEqual(select_parameters, (WORKSPACE_ID, mission.mission_id))

    def test_mission_listing_is_scoped_by_workspace_and_mission(self) -> None:
        repository = MissionScopedPostgresRepository(
            self.database,
            WORKSPACE_ID,
            table="research_tasks",
            id_column="task_id",
            model_type=ResearchMission,
            has_mission=True,
        )
        repository.for_mission("mission-1")

        query, parameters = self.database.connection_value.calls[0]
        self.assertIn("workspace_id = %s AND mission_id = %s", query)
        self.assertEqual(parameters, (WORKSPACE_ID, "mission-1"))

    def test_research_controller_persists_and_reads_transition_history(self) -> None:
        controller = PostgresResearchRoomController(self.database, WORKSPACE_ID)
        mission = make_mission()
        controller.transition(
            mission,
            MissionStatus.RESEARCHING,
            actor_id="owner",
            reason="Plan accepted",
        )

        history = controller.history(mission.mission_id)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].from_status, MissionStatus.PLANNING)
        self.assertEqual(history[0].to_status, MissionStatus.RESEARCHING)
        insert_query, insert_parameters = self.database.connection_value.calls[0]
        select_query, select_parameters = self.database.connection_value.calls[1]
        self.assertIn("workspace_id", insert_query)
        self.assertEqual(insert_parameters[0], WORKSPACE_ID)
        self.assertIn("workspace_id = %s AND mission_id = %s", select_query)
        self.assertEqual(select_parameters, (WORKSPACE_ID, mission.mission_id))

    def test_untrusted_sql_identifiers_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "SQL identifiers"):
            PostgresJsonRepository(
                self.database,
                WORKSPACE_ID,
                table="research_missions; DROP TABLE workspaces",
                id_column="mission_id",
                model_type=ResearchMission,
            )

    def test_persisted_audit_chain_verifies_after_json_normalization(self) -> None:
        database = FakeAuditDatabase()
        audit = PostgresAuditRepository(database, WORKSPACE_ID)
        audit.append(
            event_type="gateway_call",
            business_id="business-1",
            execution_id="execution-1",
            detail={
                "observed_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "labels": {"b", "a"},
            },
        )

        self.assertTrue(audit.verify_chain())
        events = audit.events_for_execution("execution-1")
        self.assertEqual(len(events), 1)
        self.assertEqual(
            events[0].detail,
            {
                "labels": ["a", "b"],
                "observed_at": "2026-01-01T00:00:00Z",
            },
        )


if __name__ == "__main__":
    unittest.main()
