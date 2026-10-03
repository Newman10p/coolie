"""Start Coolie's authenticated same-origin API/UI host.

The host requires a deployment-provided service factory because model providers,
connector credentials, and operational policies are deployment-specific.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
import importlib
import os
from pathlib import Path
from typing import Callable
from wsgiref.simple_server import make_server

from coolie_runtime import CoolieSystem
from sector3_enactor.models.approval import ApprovalLevel
from supabase_storage import (
    SupabaseServiceComposition,
    create_database_from_env,
)
from supabase_storage.database import read_env_file
from ui.live_app import LiveCoolieApplication
from ui.owner_api import OwnerWorkspaceApi
from ui.supabase_auth import SupabaseOwnerAuthenticator


@dataclass(frozen=True)
class CoolieServiceBundle:
    services: Mapping[str, object]
    startup_checks: Mapping[str, Mapping[str, bool]]
    instance_id: str
    dependency_checks: Mapping[str, Mapping[str, bool]] | None = None
    approval_levels: Mapping[str, ApprovalLevel] | None = None


def _load_environment() -> None:
    for key, value in read_env_file(Path(".env")).items():
        os.environ.setdefault(key, value)


def _load_factory(specification: str) -> Callable[[], CoolieServiceBundle]:
    module_name, separator, callable_name = specification.partition(":")
    if not separator or not module_name or not callable_name:
        raise ValueError("COOLIE_SERVICES_FACTORY must be in module:function form.")
    factory = getattr(importlib.import_module(module_name), callable_name, None)
    if not callable(factory):
        raise TypeError("COOLIE_SERVICES_FACTORY must name an importable callable.")
    return factory


def create_live_application(bundle: CoolieServiceBundle):
    """Build the Supabase-backed service graph and authenticated owner app."""
    database, workspace_id = create_database_from_env()
    try:
        composition = SupabaseServiceComposition(
            bundle.services,
            database,
            workspace_id,
        )
        system = CoolieSystem(
            composition.services,
            startup_checks=bundle.startup_checks,
            instance_id=bundle.instance_id,
            reliability=composition.reliability,
            dependency_checks=bundle.dependency_checks,
        )
        env = {**read_env_file(Path(".env")), **os.environ}
        anon_key = env.get("SUPABASE_ANON_KEY", "").strip()
        if not anon_key:
            raise ValueError("SUPABASE_ANON_KEY is required for authenticated owner access.")
        authenticator = SupabaseOwnerAuthenticator(
            database,
            supabase_url=env.get("SUPABASE_URL", ""),
            anon_key=anon_key,
            workspace_id=workspace_id,
            approval_levels=bundle.approval_levels,
        )
        owner_api = OwnerWorkspaceApi(
            system,
            authenticate=authenticator,
            wallet_registry=composition.wallets,
        )
        return LiveCoolieApplication(owner_api), database
    except Exception:
        database.close()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the live Coolie owner API and UI.")
    parser.add_argument("--host", default=None, help="Bind host; defaults to COOLIE_BIND_HOST or 127.0.0.1")
    parser.add_argument("--port", type=int, default=None, help="Bind port; defaults to COOLIE_PORT or 4173")
    args = parser.parse_args()
    _load_environment()
    factory_spec = os.environ.get("COOLIE_SERVICES_FACTORY", "").strip()
    if not factory_spec:
        raise SystemExit(
            "Set COOLIE_SERVICES_FACTORY=module:function to provide configured Coolie services."
        )
    bundle = _load_factory(factory_spec)()
    if not isinstance(bundle, CoolieServiceBundle):
        raise TypeError("The service factory must return CoolieServiceBundle.")
    application, database = create_live_application(bundle)
    host = args.host or os.environ.get("COOLIE_BIND_HOST", "127.0.0.1")
    port = args.port or int(os.environ.get("COOLIE_PORT", "4173"))
    try:
        with make_server(host, port, application) as server:
            print(f"Coolie authenticated workroom: http://{host}:{port}", flush=True)
            server.serve_forever()
    finally:
        database.close()


if __name__ == "__main__":
    main()
