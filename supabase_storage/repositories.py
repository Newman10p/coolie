"""Workspace-scoped JSONB repository implementation for the Research Room."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb

from .codec import decode_model, to_json_value
from .database import SupabasePostgres
from research_room.repositories import ConflictError


T = TypeVar("T")


class PostgresJsonRepository(Generic[T]):
    """Typed record store; all SQL is workspace constrained and identifiers are static."""

    def __init__(
        self,
        database: SupabasePostgres,
        workspace_id: UUID,
        *,
        table: str,
        id_column: str,
        model_type: type[T],
        has_status: bool = False,
        has_mission: bool = False,
        append_only: bool = False,
        extra_columns: tuple[str, ...] = (),
        order_column: str = "created_at",
    ) -> None:
        for value in (table, id_column, *extra_columns, order_column):
            if not value.replace("_", "").isalnum():
                raise ValueError("SQL identifiers must be simple static names.")
        self.database = database
        self.workspace_id = UUID(str(workspace_id))
        self.table = table
        self.id_column = id_column
        self.model_type = model_type
        self.has_status = has_status
        self.has_mission = has_mission
        self.append_only = append_only
        self.extra_columns = extra_columns
        self.order_column = order_column

    def create(self, value: T, *, mission_id_override: str | None = None) -> T:
        identifier = self._attribute(value, self.id_column)
        columns = ["workspace_id", self.id_column]
        parameters: list[object] = [self.workspace_id, identifier]
        if self.has_mission:
            columns.append("mission_id")
            parameters.append(
                mission_id_override
                if mission_id_override is not None
                else self._attribute(value, "mission_id")
            )
        if self.has_status:
            columns.append("status")
            status = self._attribute(value, "status")
            parameters.append(getattr(status, "value", status))
        for column in self.extra_columns:
            parameters.append(self._attribute(value, column))
        columns.append("payload")
        parameters.append(Jsonb(to_json_value(value)))
        placeholders = ", ".join(["%s"] * len(columns))
        query = (
            f"INSERT INTO public.{self.table} ({', '.join(columns)}) "
            f"VALUES ({placeholders}) RETURNING {self.id_column}"
        )
        try:
            with self.database.connection() as connection:
                row = connection.execute(query, parameters).fetchone()
        except UniqueViolation as error:
            raise ConflictError(f"{self.id_column} already exists: {identifier}") from error
        if row is None:
            raise RuntimeError(f"Postgres insert did not return {self.id_column}.")
        return value

    def get(self, identifier: str) -> T:
        query = (
            f"SELECT payload FROM public.{self.table} "
            f"WHERE workspace_id = %s AND {self.id_column} = %s"
        )
        with self.database.connection() as connection:
            row = connection.execute(query, (self.workspace_id, identifier)).fetchone()
        if row is None:
            raise KeyError(identifier)
        return decode_model(row[0], self.model_type)

    def all(self) -> tuple[T, ...]:
        query = (
            f"SELECT payload FROM public.{self.table} "
            f"WHERE workspace_id = %s ORDER BY {self.order_column}, " + self.id_column
        )
        with self.database.connection() as connection:
            rows = connection.execute(query, (self.workspace_id,)).fetchall()
        return tuple(decode_model(row[0], self.model_type) for row in rows)

    def replace(self, value: T) -> T:
        if self.append_only:
            raise ValueError("This repository is append-only.")
        identifier = self._attribute(value, self.id_column)
        assignments = ["payload = %s"]
        parameters: list[object] = [Jsonb(to_json_value(value))]
        if self.has_status:
            assignments.append("status = %s")
            status = self._attribute(value, "status")
            parameters.append(getattr(status, "value", status))
        if self.has_mission:
            assignments.append("mission_id = %s")
            parameters.append(self._attribute(value, "mission_id"))
        if self.table in {"research_missions", "research_tasks"}:
            assignments.append("updated_at = now()")
        parameters.extend((self.workspace_id, identifier))
        query = (
            f"UPDATE public.{self.table} SET {', '.join(assignments)} "
            f"WHERE workspace_id = %s AND {self.id_column} = %s "
            f"RETURNING {self.id_column}"
        )
        with self.database.connection() as connection:
            row = connection.execute(query, parameters).fetchone()
        if row is None:
            raise KeyError(identifier)
        return value

    @staticmethod
    def _attribute(value: T, name: str):
        if not hasattr(value, name):
            raise TypeError(f"Expected persisted value with {name!r} attribute.")
        result = getattr(value, name)
        if isinstance(result, datetime) and result.tzinfo is None:
            raise ValueError(f"{name} must be timezone-aware.")
        return result


class MissionScopedPostgresRepository(PostgresJsonRepository[T]):
    def for_mission(self, mission_id: str) -> tuple[T, ...]:
        query = (
            f"SELECT payload FROM public.{self.table} "
            f"WHERE workspace_id = %s AND mission_id = %s ORDER BY {self.order_column}, "
            + self.id_column
        )
        with self.database.connection() as connection:
            rows = connection.execute(query, (self.workspace_id, mission_id)).fetchall()
        return tuple(decode_model(row[0], self.model_type) for row in rows)
