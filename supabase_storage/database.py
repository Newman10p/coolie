"""Postgres connection pool and secret-safe Supabase environment loading."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import os
from urllib.parse import urlparse
from uuid import UUID

from psycopg.conninfo import make_conninfo
from psycopg_pool import ConnectionPool


class SupabaseConfigurationError(ValueError):
    """Raised when required server-side database settings are missing or invalid."""


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not key.replace("_", "a").isalnum() or not key[0].isalpha():
            raise SupabaseConfigurationError(f"Invalid environment setting on line {line_number}.")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def _database_conninfo(values: Mapping[str, str]) -> str:
    explicit_url = values.get("DATABASE_URL", "").strip()
    if explicit_url and "<database-password>" not in explicit_url:
        parsed = urlparse(explicit_url)
        if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname:
            raise SupabaseConfigurationError("DATABASE_URL must be a PostgreSQL connection URL.")
        if parsed.scheme == "postgres" and parsed.query and "sslmode=" not in parsed.query:
            explicit_url += ("&" if "?" in explicit_url else "?") + "sslmode=require"
        elif parsed.scheme == "postgresql" and "sslmode=" not in parsed.query:
            explicit_url += ("&" if "?" in explicit_url else "?") + "sslmode=require"
        return explicit_url

    password = values.get("SUPABASE_DB_PASSWORD", "").strip()
    project_url = values.get("SUPABASE_URL", "").strip()
    region = values.get("SUPABASE_REGION", "").strip()
    if not password or not project_url or not region:
        raise SupabaseConfigurationError(
            "Set DATABASE_URL or SUPABASE_URL, SUPABASE_REGION, and SUPABASE_DB_PASSWORD."
        )
    project_host = urlparse(project_url).hostname
    if not project_host or not project_host.endswith(".supabase.co"):
        raise SupabaseConfigurationError("SUPABASE_URL must be a Supabase project URL.")
    project_ref = project_host.removesuffix(".supabase.co")
    pooler_host = values.get("SUPABASE_POOLER_HOST", f"aws-0-{region}.pooler.supabase.com")
    return make_conninfo(
        host=pooler_host,
        port=int(values.get("SUPABASE_POOLER_PORT", "5432")),
        dbname="postgres",
        user=f"postgres.{project_ref}",
        password=password,
        sslmode="require",
        connect_timeout=10,
        application_name="coolie-backend",
    )


class SupabasePostgres:
    """Small connection-pool wrapper. Workspace IDs are required by repositories."""

    def __init__(self, conninfo: str, *, min_size: int = 1, max_size: int = 8) -> None:
        if not conninfo.strip():
            raise SupabaseConfigurationError("Postgres connection information is required.")
        self._pool = ConnectionPool(conninfo, min_size=min_size, max_size=max_size, open=True, timeout=10)

    def connection(self):
        return self._pool.connection()

    def check(self) -> bool:
        with self._pool.connection() as connection:
            row = connection.execute("SELECT 1").fetchone()
        return row == (1,)

    def close(self) -> None:
        self._pool.close()


def create_database_from_env(
    *,
    env_file: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> tuple[SupabasePostgres, UUID]:
    """Create a pool only when an explicit Coolie workspace is configured."""
    local_values = read_env_file(env_file or Path(".env"))
    values = {**local_values, **dict(os.environ if environ is None else environ)}
    raw_workspace_id = values.get("COOLIE_WORKSPACE_ID", "").strip()
    if not raw_workspace_id:
        raise SupabaseConfigurationError(
            "COOLIE_WORKSPACE_ID is required; create or select an owned workspace before connecting."
        )
    try:
        workspace_id = UUID(raw_workspace_id)
    except ValueError as error:
        raise SupabaseConfigurationError("COOLIE_WORKSPACE_ID must be a UUID.") from error
    conninfo = _database_conninfo(values)
    return SupabasePostgres(conninfo), workspace_id
