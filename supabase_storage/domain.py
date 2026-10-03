"""General workspace-scoped record and append-only event persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb

from .codec import decode_model, to_json_value
from .database import SupabasePostgres
from research_room.artifacts import StoredArtifact


T = TypeVar("T")


class PostgresDomainPersistence:
    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self.database = database
        self.workspace_id = UUID(str(workspace_id))

    def put_record(self, record_type: str, record_id: str, value: object) -> None:
        self._validate_key(record_type, record_id)
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO public.workspace_records
                    (workspace_id, record_type, record_id, payload)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (workspace_id, record_type, record_id)
                DO UPDATE SET payload = excluded.payload, updated_at = now()
                """,
                (
                    self.workspace_id,
                    record_type,
                    record_id,
                    Jsonb(to_json_value(value)),
                ),
            )

    def insert_record(self, record_type: str, record_id: str, value: object) -> None:
        self._validate_key(record_type, record_id)
        try:
            with self.database.connection() as connection:
                connection.execute(
                    """
                    INSERT INTO public.workspace_records
                        (workspace_id, record_type, record_id, payload)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        self.workspace_id,
                        record_type,
                        record_id,
                        Jsonb(to_json_value(value)),
                    ),
                )
        except UniqueViolation as error:
            raise ValueError(f"{record_type} already exists: {record_id}") from error

    def get_record(self, record_type: str, record_id: str, model_type: type[T]) -> T:
        return decode_model(self.get_payload(record_type, record_id), model_type)

    def get_payload(self, record_type: str, record_id: str) -> dict[str, Any]:
        self._validate_key(record_type, record_id)
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT payload FROM public.workspace_records
                WHERE workspace_id = %s AND record_type = %s AND record_id = %s
                """,
                (self.workspace_id, record_type, record_id),
            ).fetchone()
        if row is None:
            raise KeyError(record_id)
        if not isinstance(row[0], dict):
            raise TypeError("Persisted domain payload must be a JSON object.")
        return row[0]

    def maybe_record(self, record_type: str, record_id: str, model_type: type[T]) -> T | None:
        self._validate_key(record_type, record_id)
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT payload FROM public.workspace_records
                WHERE workspace_id = %s AND record_type = %s AND record_id = %s
                """,
                (self.workspace_id, record_type, record_id),
            ).fetchone()
        return None if row is None else decode_model(row[0], model_type)

    def all_records(self, record_type: str, model_type: type[T]) -> tuple[T, ...]:
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT payload FROM public.workspace_records
                WHERE workspace_id = %s AND record_type = %s
                ORDER BY created_at, record_id
                """,
                (self.workspace_id, record_type),
            ).fetchall()
        return tuple(decode_model(row[0], model_type) for row in rows)

    def record_ids(self, record_type: str) -> tuple[str, ...]:
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT record_id FROM public.workspace_records
                WHERE workspace_id = %s AND record_type = %s
                ORDER BY created_at, record_id
                """,
                (self.workspace_id, record_type),
            ).fetchall()
        return tuple(row[0] for row in rows)

    def delete_record(self, record_type: str, record_id: str) -> None:
        self._validate_key(record_type, record_id)
        with self.database.connection() as connection:
            row = connection.execute(
                """
                DELETE FROM public.workspace_records
                WHERE workspace_id = %s AND record_type = %s AND record_id = %s
                RETURNING record_id
                """,
                (self.workspace_id, record_type, record_id),
            ).fetchone()
        if row is None:
            raise KeyError(record_id)

    def append_event(
        self,
        stream_name: str,
        stream_key: str,
        event_id: str,
        value: object,
    ) -> None:
        self._validate_key(stream_name, stream_key)
        self._validate_key(stream_name, event_id)
        try:
            with self.database.connection() as connection:
                connection.execute(
                    """
                    INSERT INTO public.workspace_events
                        (workspace_id, stream_name, stream_key, event_id, payload)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        self.workspace_id,
                        stream_name,
                        stream_key,
                        event_id,
                        Jsonb(to_json_value(value)),
                    ),
                )
        except UniqueViolation as error:
            raise ValueError(f"Duplicate {stream_name} event: {event_id}") from error

    def events(
        self,
        stream_name: str,
        model_type: type[T],
        *,
        stream_key: str | None = None,
    ) -> tuple[T, ...]:
        if stream_key is None:
            query = """
                SELECT payload FROM public.workspace_events
                WHERE workspace_id = %s AND stream_name = %s
                ORDER BY event_sequence
            """
            parameters: tuple[Any, ...] = (self.workspace_id, stream_name)
        else:
            query = """
                SELECT payload FROM public.workspace_events
                WHERE workspace_id = %s AND stream_name = %s AND stream_key = %s
                ORDER BY event_sequence
            """
            parameters = (self.workspace_id, stream_name, stream_key)
        with self.database.connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return tuple(decode_model(row[0], model_type) for row in rows)

    def system_state(self) -> tuple[bool, str | None, datetime | None]:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT paused, reason, paused_at FROM public.workspace_system_state
                WHERE workspace_id = %s
                """,
                (self.workspace_id,),
            ).fetchone()
        return (False, None, None) if row is None else (row[0], row[1], row[2])

    def set_system_state(self, *, paused: bool, reason: str | None) -> None:
        paused_at = datetime.now(timezone.utc) if paused else None
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO public.workspace_system_state
                    (workspace_id, paused, reason, paused_at, updated_at)
                VALUES (%s, %s, %s, %s, now())
                ON CONFLICT (workspace_id)
                DO UPDATE SET paused = excluded.paused, reason = excluded.reason,
                    paused_at = excluded.paused_at, updated_at = now()
                """,
                (self.workspace_id, paused, reason, paused_at),
            )

    @staticmethod
    def _validate_key(*values: str) -> None:
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError("Persistence keys must be non-empty strings.")


class PostgresObjectStorage:
    """Immutable byte-oriented artifact storage scoped to the selected workspace."""

    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self.database = database
        self.workspace_id = UUID(str(workspace_id))

    def put_immutable(
        self, key: str, content: bytes, content_type: str
    ) -> StoredArtifact:
        if not key.strip() or key.startswith("/") or ".." in Path(key).parts:
            raise ValueError("Artifact key must be a safe relative key.")
        if not content_type.strip():
            raise ValueError("content_type is required.")
        content_hash = "sha256:" + sha256(content).hexdigest()
        with self.database.connection() as connection:
            row = connection.execute(
                """
                INSERT INTO public.research_artifacts
                    (workspace_id, artifact_key, content_hash, content_type, content)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (workspace_id, artifact_key) DO NOTHING
                RETURNING content_hash, content_type, content
                """,
                (self.workspace_id, key, content_hash, content_type, content),
            ).fetchone()
            if row is None:
                row = connection.execute(
                    """
                    SELECT content_hash, content_type, content
                    FROM public.research_artifacts
                    WHERE workspace_id = %s AND artifact_key = %s
                    """,
                    (self.workspace_id, key),
                ).fetchone()
                if row is None or row[0] != content_hash or bytes(row[2]) != content:
                    raise ValueError("Artifact keys are immutable.")
        return StoredArtifact(key, content_hash, content_type, len(content))

    def get(self, key: str) -> bytes:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT content FROM public.research_artifacts
                WHERE workspace_id = %s AND artifact_key = %s
                """,
                (self.workspace_id, key),
            ).fetchone()
        if row is None:
            raise KeyError(key)
        return bytes(row[0])
