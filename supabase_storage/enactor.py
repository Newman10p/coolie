"""Workspace-scoped Postgres adapters for the Enactor storage contracts."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any, Generic, TypeVar
from uuid import UUID

from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb

from sector3_enactor.models.approval import ApprovalRequest, ApprovalStatus
from sector3_enactor.models.asset import ManagedAsset
from sector3_enactor.models.commerce import (
    InventoryLevel,
    OrderRecord,
    ProductRecord,
)
from sector3_enactor.models.deployment import DeploymentRecord, DeploymentStatus
from sector3_enactor.models.execution import ActionResult, ExecutionRequest
from sector3_enactor.models.marketing import CampaignRecord
from sector3_enactor.models.messaging import InboundMessage, OutboundDraft, SupportTicket
from sector3_enactor.models.outcome import BusinessMetricSnapshot, OutcomeReport
from sector3_enactor.policy.hashing import canonical_json, digest
from sector3_enactor.runtime.budget import BudgetLedger
from sector3_enactor.storage.audit_repository import AuditEvent
from sector3_enactor.storage.repositories import NotFound

from .codec import decode_model, to_json_value
from .database import SupabasePostgres


T = TypeVar("T")


class PostgresEntityRepository(Generic[T]):
    """A typed mutable entity store, always scoped to one configured workspace."""

    def __init__(
        self,
        database: SupabasePostgres,
        workspace_id: UUID,
        entity_type: str,
        model_type: type[T],
        id_attribute: str,
    ) -> None:
        if not entity_type.replace("_", "").isalnum():
            raise ValueError("Entity type must be a static identifier.")
        self.database = database
        self.workspace_id = UUID(str(workspace_id))
        self.entity_type = entity_type
        self.model_type = model_type
        self.id_attribute = id_attribute

    def put(self, item: T) -> None:
        identifier = self._identifier(item)
        status = getattr(item, "status", None)
        status_value = getattr(status, "value", status)
        query = """
            INSERT INTO public.enactor_records
                (workspace_id, entity_type, entity_id, status, payload)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (workspace_id, entity_type, entity_id)
            DO UPDATE SET status = excluded.status, payload = excluded.payload,
                updated_at = now()
        """
        with self.database.connection() as connection:
            connection.execute(
                query,
                (
                    self.workspace_id,
                    self.entity_type,
                    identifier,
                    status_value,
                    Jsonb(to_json_value(item)),
                ),
            )

    def get(self, key: str) -> T:
        query = """
            SELECT payload FROM public.enactor_records
            WHERE workspace_id = %s AND entity_type = %s AND entity_id = %s
        """
        with self.database.connection() as connection:
            row = connection.execute(
                query, (self.workspace_id, self.entity_type, key)
            ).fetchone()
        if row is None:
            raise NotFound(f"{self.entity_type}: missing {self.id_attribute}={key}")
        return decode_model(row[0], self.model_type)

    def maybe(self, key: str) -> T | None:
        query = """
            SELECT payload FROM public.enactor_records
            WHERE workspace_id = %s AND entity_type = %s AND entity_id = %s
        """
        with self.database.connection() as connection:
            row = connection.execute(
                query, (self.workspace_id, self.entity_type, key)
            ).fetchone()
        return None if row is None else decode_model(row[0], self.model_type)

    def all(self) -> tuple[T, ...]:
        query = """
            SELECT payload FROM public.enactor_records
            WHERE workspace_id = %s AND entity_type = %s
            ORDER BY created_at, entity_id
        """
        with self.database.connection() as connection:
            rows = connection.execute(
                query, (self.workspace_id, self.entity_type)
            ).fetchall()
        return tuple(decode_model(row[0], self.model_type) for row in rows)

    def _identifier(self, item: T) -> str:
        identifier = getattr(item, self.id_attribute, None)
        if not isinstance(identifier, str) or not identifier:
            raise ValueError(f"Persisted entity requires a {self.id_attribute}.")
        return identifier


class PostgresInventoryRepository:
    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self._store = PostgresEntityRepository(
            database, workspace_id, "inventory", InventoryLevel, "product_id"
        )

    def put(self, level: InventoryLevel) -> None:
        self._store.put(level)

    def get(self, product_id: str) -> InventoryLevel:
        return self._store.get(product_id)

    def all(self) -> tuple[InventoryLevel, ...]:
        return self._store.all()


class PostgresApprovalRepository(PostgresEntityRepository[ApprovalRequest]):
    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        super().__init__(database, workspace_id, "approvals", ApprovalRequest, "approval_id")

    def put(self, item: ApprovalRequest) -> None:
        identifier = self._identifier(item)
        with self.database.connection() as connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"{self.workspace_id}:{identifier}",),
            )
            row = connection.execute(
                """
                SELECT payload FROM public.enactor_records
                WHERE workspace_id = %s AND entity_type = %s AND entity_id = %s
                FOR UPDATE
                """,
                (self.workspace_id, self.entity_type, identifier),
            ).fetchone()
            if row is not None:
                existing = decode_model(row[0], ApprovalRequest)
                if existing.status is ApprovalStatus.APPROVED and item.status not in {
                    ApprovalStatus.APPROVED,
                    ApprovalStatus.CONSUMED,
                }:
                    raise ValueError(
                        "Approved decisions are immutable except for single-use consumption."
                    )
                if existing.status in {
                    ApprovalStatus.DENIED,
                    ApprovalStatus.CONSUMED,
                } and item.status is not existing.status:
                    raise ValueError("Denied and consumed approvals cannot be changed.")
            status_value = item.status.value
            query = """
                INSERT INTO public.enactor_records
                    (workspace_id, entity_type, entity_id, status, payload)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (workspace_id, entity_type, entity_id)
                DO UPDATE SET status = excluded.status, payload = excluded.payload,
                    updated_at = now()
            """
            connection.execute(
                query,
                (
                    self.workspace_id,
                    self.entity_type,
                    identifier,
                    status_value,
                    Jsonb(to_json_value(item)),
                ),
            )

    def for_execution(self, execution_id: str) -> tuple[ApprovalRequest, ...]:
        return tuple(item for item in self.all() if item.execution_id == execution_id)


class PostgresDeploymentRepository:
    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self._store = PostgresEntityRepository(
            database, workspace_id, "deployments", DeploymentRecord, "deployment_id"
        )

    def add(self, record: DeploymentRecord) -> None:
        try:
            with self._store.database.connection() as connection:
                connection.execute(
                    """
                    INSERT INTO public.enactor_records
                        (workspace_id, entity_type, entity_id, status, payload)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        self._store.workspace_id,
                        self._store.entity_type,
                        record.deployment_id,
                        record.status.value,
                        Jsonb(to_json_value(record)),
                    ),
                )
        except UniqueViolation as error:
            raise ValueError("Duplicate deployment id.") from error

    def get(self, deployment_id: str) -> DeploymentRecord:
        return self._store.get(deployment_id)

    def all(self) -> tuple[DeploymentRecord, ...]:
        return self._store.all()

    def latest(self, business_id: str, environment: str) -> DeploymentRecord | None:
        matches = [
            record
            for record in self.all()
            if record.business_id == business_id
            and record.environment.value == environment
            and record.status is DeploymentStatus.SUCCEEDED
        ]
        return matches[-1] if matches else None


class PostgresMetricRepository:
    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self._store = PostgresEntityRepository(
            database, workspace_id, "metrics", BusinessMetricSnapshot, "metric_id"
        )

    def add(self, snapshot: BusinessMetricSnapshot) -> None:
        self._store.put(snapshot)

    def for_execution(self, execution_id: str) -> tuple[BusinessMetricSnapshot, ...]:
        return tuple(item for item in self._store.all() if item.execution_id == execution_id)

    def for_business(self, business_id: str) -> tuple[BusinessMetricSnapshot, ...]:
        return tuple(item for item in self._store.all() if item.business_id == business_id)


class PostgresOutcomeRepository:
    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self._store = PostgresEntityRepository(
            database, workspace_id, "outcomes", OutcomeReport, "report_id"
        )

    def add(self, report: OutcomeReport) -> None:
        try:
            identifier = getattr(report, "report_id")
            with self._store.database.connection() as connection:
                connection.execute(
                    """
                    INSERT INTO public.enactor_records
                        (workspace_id, entity_type, entity_id, payload)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        self._store.workspace_id,
                        self._store.entity_type,
                        identifier,
                        Jsonb(to_json_value(report)),
                    ),
                )
        except UniqueViolation as error:
            raise ValueError("Duplicate outcome report id.") from error

    def all(self) -> tuple[OutcomeReport, ...]:
        return self._store.all()


class PostgresStorefront:
    """Drop-in repository aggregate accepted by Enactor's execution controller."""

    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self.executions = PostgresEntityRepository(
            database, workspace_id, "executions", ExecutionRequest, "execution_id"
        )
        self.approvals = PostgresApprovalRepository(database, workspace_id)
        self.assets = PostgresEntityRepository(
            database, workspace_id, "assets", ManagedAsset, "asset_id"
        )
        self.messages = PostgresEntityRepository(
            database, workspace_id, "messages", InboundMessage, "message_id"
        )
        self.drafts = PostgresEntityRepository(
            database, workspace_id, "drafts", OutboundDraft, "draft_id"
        )
        self.tickets = PostgresEntityRepository(
            database, workspace_id, "tickets", SupportTicket, "ticket_id"
        )
        self.products = PostgresEntityRepository(
            database, workspace_id, "products", ProductRecord, "product_id"
        )
        self.inventory = PostgresInventoryRepository(database, workspace_id)
        self.orders = PostgresEntityRepository(
            database, workspace_id, "orders", OrderRecord, "order_id"
        )
        self.campaigns = PostgresEntityRepository(
            database, workspace_id, "campaigns", CampaignRecord, "campaign_id"
        )
        self.deployments = PostgresDeploymentRepository(database, workspace_id)
        self.metrics = PostgresMetricRepository(database, workspace_id)
        self.outcomes = PostgresOutcomeRepository(database, workspace_id)


class PostgresAuditRepository:
    """Append-only, workspace-serialized hash chain with the existing Enactor API."""

    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self.database = database
        self.workspace_id = UUID(str(workspace_id))

    def append(
        self,
        *,
        event_type: str,
        business_id: str,
        execution_id: str,
        detail: dict[str, Any],
        task_id: str | None = None,
        agent_id: str | None = None,
        tool: str | None = None,
        connector_account: str | None = None,
        approval_id: str | None = None,
        external_operation_id: str | None = None,
        recorded_at: datetime | None = None,
    ) -> AuditEvent:
        if not event_type.strip() or not business_id.strip() or not execution_id.strip():
            raise ValueError("Audit events require event_type, business_id and execution_id.")
        timestamp = recorded_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            raise ValueError("Audit event timestamps must be timezone-aware.")
        normalized_detail = json.loads(canonical_json(detail))

        with self.database.connection() as connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (str(self.workspace_id),),
            )
            previous = connection.execute(
                """
                SELECT sequence, event_hash FROM public.audit_events
                WHERE workspace_id = %s ORDER BY sequence DESC LIMIT 1
                """,
                (self.workspace_id,),
            ).fetchone()
            sequence = 0 if previous is None else int(previous[0]) + 1
            previous_hash = "sha256:genesis" if previous is None else previous[1]
            core = {
                "sequence": sequence,
                "event_type": event_type,
                "business_id": business_id,
                "execution_id": execution_id,
                "task_id": task_id,
                "agent_id": agent_id,
                "tool": tool,
                "connector_account": connector_account,
                "approval_id": approval_id,
                "external_operation_id": external_operation_id,
                "payload": normalized_detail,
                "previous_hash": previous_hash,
            }
            event_hash = digest(core)
            payload_hash = digest(normalized_detail)
            connection.execute(
                """
                INSERT INTO public.audit_events
                    (workspace_id, sequence, event_type, business_id, execution_id,
                     task_id, agent_id, tool, connector_account, approval_id,
                     external_operation_id, payload_hash, previous_hash, event_hash,
                     payload, recorded_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    self.workspace_id, sequence, event_type, business_id, execution_id,
                    task_id, agent_id, tool, connector_account, approval_id,
                    external_operation_id, payload_hash, previous_hash, event_hash,
                    Jsonb(normalized_detail), timestamp,
                ),
            )
        return AuditEvent(
            sequence=sequence,
            event_type=event_type,
            business_id=business_id,
            execution_id=execution_id,
            task_id=task_id,
            agent_id=agent_id,
            tool=tool,
            connector_account=connector_account,
            approval_id=approval_id,
            external_operation_id=external_operation_id,
            payload_hash=payload_hash,
            detail=normalized_detail,
            previous_hash=previous_hash,
            event_hash=event_hash,
            recorded_at=timestamp,
        )

    def all_events(self) -> tuple[AuditEvent, ...]:
        query = """
            SELECT sequence, event_type, business_id, execution_id, task_id, agent_id,
                   tool, connector_account, approval_id, external_operation_id,
                   payload_hash, payload, previous_hash, event_hash, recorded_at
            FROM public.audit_events WHERE workspace_id = %s ORDER BY sequence
        """
        with self.database.connection() as connection:
            rows = connection.execute(query, (self.workspace_id,)).fetchall()
        return tuple(
            AuditEvent(
                sequence=int(row[0]),
                event_type=row[1],
                business_id=row[2],
                execution_id=row[3] or "",
                task_id=row[4],
                agent_id=row[5],
                tool=row[6],
                connector_account=row[7],
                approval_id=row[8],
                external_operation_id=row[9],
                payload_hash=row[10],
                detail=row[11],
                previous_hash=row[12],
                event_hash=row[13],
                recorded_at=row[14],
            )
            for row in rows
        )

    def events_for_execution(self, execution_id: str) -> tuple[AuditEvent, ...]:
        return tuple(
            event for event in self.all_events() if event.execution_id == execution_id
        )

    def verify_chain(self) -> bool:
        events = self.all_events()
        previous_hash = "sha256:genesis"
        for expected_sequence, event in enumerate(events):
            if (
                event.sequence != expected_sequence
                or event.previous_hash != previous_hash
                or event.payload_hash != digest(event.detail)
            ):
                return False
            core = {
                "sequence": event.sequence,
                "event_type": event.event_type,
                "business_id": event.business_id,
                "execution_id": event.execution_id,
                "task_id": event.task_id,
                "agent_id": event.agent_id,
                "tool": event.tool,
                "connector_account": event.connector_account,
                "approval_id": event.approval_id,
                "external_operation_id": event.external_operation_id,
                "payload": event.detail,
                "previous_hash": event.previous_hash,
            }
            if event.event_hash != digest(core):
                return False
            previous_hash = event.event_hash
        return True


class PostgresEnactorIdempotency:
    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self.database = database
        self.workspace_id = UUID(str(workspace_id))

    def get(self, replay_key: str) -> tuple[str, ActionResult | None] | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT request_hash, result FROM public.enactor_idempotency
                WHERE workspace_id = %s AND replay_key = %s
                """,
                (self.workspace_id, replay_key),
            ).fetchone()
        if row is None:
            return None
        return (
            row[0],
            None if row[1] is None else decode_model(row[1], ActionResult),
        )

    def claim(
        self, replay_key: str, request_hash: str
    ) -> tuple[str, ActionResult | None] | None:
        with self.database.connection() as connection:
            inserted = connection.execute(
                """
                INSERT INTO public.enactor_idempotency
                    (workspace_id, replay_key, request_hash)
                VALUES (%s, %s, %s)
                ON CONFLICT (workspace_id, replay_key) DO NOTHING
                RETURNING replay_key
                """,
                (self.workspace_id, replay_key, request_hash),
            ).fetchone()
        return None if inserted is not None else self.get(replay_key)

    def complete(
        self, replay_key: str, request_hash: str, result: ActionResult
    ) -> None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                UPDATE public.enactor_idempotency
                SET result = %s, updated_at = now()
                WHERE workspace_id = %s AND replay_key = %s
                  AND request_hash = %s AND result IS NULL
                RETURNING replay_key
                """,
                (
                    Jsonb(to_json_value(result)),
                    self.workspace_id,
                    replay_key,
                    request_hash,
                ),
            ).fetchone()
        if row is None:
            raise RuntimeError("Idempotency record could not be completed.")


class PostgresBudgetLedger:
    def __init__(self, database: SupabasePostgres, workspace_id: UUID, execution_id: str) -> None:
        self.database = database
        self.workspace_id = UUID(str(workspace_id))
        self.execution_id = execution_id
        state = self._read()
        self.limits = state["limits"]
        self.currencies = state["currencies"]

    def _read(self) -> dict[str, Any]:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT limits, currencies, spent, reserved, warning_emitted, exhausted
                FROM public.enactor_budget_ledgers
                WHERE workspace_id = %s AND execution_id = %s
                """,
                (self.workspace_id, self.execution_id),
            ).fetchone()
        if row is None:
            raise KeyError(self.execution_id)
        return {
            "limits": row[0],
            "currencies": row[1],
            "spent": row[2],
            "reserved": row[3],
            "warning_emitted": row[4],
            "exhausted": row[5],
        }

    def _change(self, operation):
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT limits, currencies, spent, reserved, warning_emitted, exhausted
                FROM public.enactor_budget_ledgers
                WHERE workspace_id = %s AND execution_id = %s
                FOR UPDATE
                """,
                (self.workspace_id, self.execution_id),
            ).fetchone()
            if row is None:
                raise KeyError(self.execution_id)
            state = {
                "limits": row[0],
                "currencies": row[1],
                "spent": row[2],
                "reserved": row[3],
                "warning_emitted": row[4],
                "exhausted": row[5],
            }
            result = operation(state)
            connection.execute(
                """
                UPDATE public.enactor_budget_ledgers
                SET spent = %s, reserved = %s, warning_emitted = %s,
                    exhausted = %s, updated_at = now()
                WHERE workspace_id = %s AND execution_id = %s
                """,
                (
                    Jsonb(state["spent"]),
                    Jsonb(state["reserved"]),
                    state["warning_emitted"],
                    state["exhausted"],
                    self.workspace_id,
                    self.execution_id,
                ),
            )
        return result

    def utilization(self) -> float:
        state = self._read()
        return max(
            (
                (state["spent"][kind] + state["reserved"][kind]) / limit
                for kind, limit in self.limits.items()
                if limit > 0
            ),
            default=0.0,
        )

    def check(self, budget_type: str, cost: float, *, currency: str | None = None) -> tuple[bool, str]:
        if budget_type == "none":
            return True, ""
        if budget_type not in self.limits:
            return False, f"Unknown budget type {budget_type}; failing closed."
        if cost < 0:
            return False, "Negative cost reservations are rejected."
        state = self._read()
        projected = (
            state["spent"][budget_type]
            + state["reserved"][budget_type]
            + cost
        )
        if projected > self.limits[budget_type]:
            return False, (
                f"Budget {budget_type} would be exceeded "
                f"({projected:g} > {self.limits[budget_type]:g}); attempt denied."
            )
        declared = self.currencies.get(budget_type)
        if declared and currency and currency != declared:
            return False, f"Currency {currency} does not match budget currency {declared}."
        return True, ""

    def reserve(self, budget_type: str, cost: float) -> None:
        if budget_type == "none":
            return

        def reserve_value(state: dict[str, Any]) -> str | None:
            if budget_type not in self.limits:
                return f"Unknown budget type {budget_type}; failing closed."
            projected = (
                state["spent"][budget_type]
                + state["reserved"][budget_type]
                + cost
            )
            if cost < 0 or projected > self.limits[budget_type]:
                state["exhausted"] = True
                return f"Budget {budget_type} would be exceeded; attempt denied."
            state["reserved"][budget_type] += cost
            return None

        error = self._change(reserve_value)
        if error is not None:
            raise PermissionError(error)

    def commit(self, budget_type: str, cost: float) -> None:
        if budget_type == "none":
            return

        def commit_value(state: dict[str, Any]) -> None:
            state["reserved"][budget_type] = max(
                0.0, state["reserved"][budget_type] - cost
            )
            state["spent"][budget_type] += cost

        self._change(commit_value)

    def rollback(self, budget_type: str, cost: float) -> None:
        if budget_type == "none":
            return

        def rollback_value(state: dict[str, Any]) -> None:
            state["reserved"][budget_type] = max(
                0.0, state["reserved"][budget_type] - cost
            )

        self._change(rollback_value)

    @property
    def exhausted(self) -> bool:
        return self._read()["exhausted"]

    @exhausted.setter
    def exhausted(self, value: bool) -> None:
        self._change(lambda state: state.__setitem__("exhausted", value))

    @property
    def warning_emitted(self) -> bool:
        return self._read()["warning_emitted"]

    @warning_emitted.setter
    def warning_emitted(self, value: bool) -> None:
        self._change(lambda state: state.__setitem__("warning_emitted", value))


class PostgresBudgetTracker:
    def __init__(
        self,
        database: SupabasePostgres,
        workspace_id: UUID,
        warning_threshold_percent: float = 80.0,
    ) -> None:
        self.database = database
        self.workspace_id = UUID(str(workspace_id))
        self._warning_at = warning_threshold_percent / 100.0

    def open_ledger(self, execution_id: str, budgets: dict) -> PostgresBudgetLedger:
        template = BudgetLedger.from_config(budgets)
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO public.enactor_budget_ledgers
                    (workspace_id, execution_id, limits, currencies, spent, reserved)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (workspace_id, execution_id) DO NOTHING
                """,
                (
                    self.workspace_id,
                    execution_id,
                    Jsonb(template.limits),
                    Jsonb(template.currencies),
                    Jsonb(template.spent),
                    Jsonb(template.reserved),
                ),
            )
        ledger = PostgresBudgetLedger(self.database, self.workspace_id, execution_id)
        if ledger.limits != template.limits or ledger.currencies != template.currencies:
            raise ValueError("Persisted execution budget does not match its configured limits.")
        return ledger

    def ledger(self, execution_id: str) -> PostgresBudgetLedger:
        return PostgresBudgetLedger(self.database, self.workspace_id, execution_id)

    def record(self, execution_id: str, budget_type: str, cost: float) -> None:
        ledger = self.ledger(execution_id)

        def record_value(state: dict[str, Any]) -> str | None:
            if budget_type == "none":
                return None
            if budget_type not in ledger.limits:
                return f"Unknown budget type {budget_type}; failing closed."
            projected = (
                state["spent"][budget_type]
                + state["reserved"][budget_type]
                + cost
            )
            if cost < 0 or projected > ledger.limits[budget_type]:
                state["exhausted"] = True
                return (
                    f"Budget {budget_type} would be exceeded "
                    f"({projected:g} > {ledger.limits[budget_type]:g}); attempt denied."
                )
            state["spent"][budget_type] = projected
            return None

        error = ledger._change(record_value)
        if error is not None:
            raise PermissionError(error)

    def near_limit(self, execution_id: str) -> bool:
        return self.ledger(execution_id).utilization() >= self._warning_at

    def exhausted(self, execution_id: str) -> bool:
        ledger = self.ledger(execution_id)
        return ledger.exhausted or any(
            ledger.limits[kind] > 0
            and ledger._read()["spent"][kind] >= ledger.limits[kind]
            for kind in ledger.limits
        )


class PostgresArtifactStore:
    """Immutable text artifacts stored privately in the workspace-scoped database."""

    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self.database = database
        self.workspace_id = UUID(str(workspace_id))

    def put(self, key: str, content: str, *, content_type: str = "text/plain"):
        from sector3_enactor.models.execution import ArtifactReference

        if not key.strip():
            raise ValueError("Artifact key must be non-empty.")
        content_hash = digest({"content": content})
        with self.database.connection() as connection:
            row = connection.execute(
                """
                INSERT INTO public.enactor_artifacts
                    (workspace_id, artifact_key, content_hash, content_type, content)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (workspace_id, artifact_key)
                RETURNING artifact_key
                """,
                (self.workspace_id, key, content_hash, content_type, content),
            ).fetchone()
            if row is None:
                existing = connection.execute(
                    """
                    SELECT content, content_hash FROM public.enactor_artifacts
                    WHERE workspace_id = %s AND artifact_key = %s
                    """,
                    (self.workspace_id, key),
                ).fetchone()
                if existing is None or existing[0] != content or existing[1] != content_hash:
                    raise ValueError(
                        f"Artifact {key} is immutable; write a new versioned key instead."
                    )
        return ArtifactReference(key, content_hash, content_type)

    def get(self, key: str) -> str:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT content FROM public.enactor_artifacts
                WHERE workspace_id = %s AND artifact_key = %s
                """,
                (self.workspace_id, key),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown artifact {key}")
        return row[0]

    def keys(self) -> tuple[str, ...]:
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT artifact_key FROM public.enactor_artifacts
                WHERE workspace_id = %s ORDER BY artifact_key
                """,
                (self.workspace_id,),
            ).fetchall()
        return tuple(row[0] for row in rows)
