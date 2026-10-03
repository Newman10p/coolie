"""Workspace-scoped Postgres persistence for Supabase deployments."""

from .database import SupabasePostgres, create_database_from_env
from .enactor import (
    PostgresArtifactStore,
    PostgresAuditRepository,
    PostgresBudgetTracker,
    PostgresEnactorIdempotency,
    PostgresStorefront,
)
from .brain import PostgresBudgetManager
from .composition import SupabaseServiceComposition
from .domain import PostgresDomainPersistence, PostgresObjectStorage
from .reliability import PostgresReliabilityRuntime
from .research import PostgresResearchRepositories
from .wallets import PostgresWalletRegistry, WalletAccount, WalletRegistry

__all__ = [
    "PostgresArtifactStore",
    "PostgresAuditRepository",
    "PostgresBudgetManager",
    "PostgresBudgetTracker",
    "PostgresDomainPersistence",
    "PostgresEnactorIdempotency",
    "PostgresObjectStorage",
    "PostgresResearchRepositories",
    "PostgresReliabilityRuntime",
    "PostgresStorefront",
    "PostgresWalletRegistry",
    "SupabaseServiceComposition",
    "SupabasePostgres",
    "WalletAccount",
    "WalletRegistry",
    "create_database_from_env",
]
