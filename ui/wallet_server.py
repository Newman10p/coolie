"""Run the scoped wallet-management API with Supabase Auth and the React UI."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from wsgiref.simple_server import make_server

from supabase_storage import PostgresWalletRegistry, create_database_from_env
from supabase_storage.database import read_env_file
from ui.demo_server import PreviewApp
from ui.supabase_auth import SupabaseOwnerAuthenticator
from ui.wallet_api import WalletOnlyApplication, WalletWorkspaceApi


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Coolie's wallet-only local integration host."
    )
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()
    for key, value in read_env_file(Path(".env")).items():
        os.environ.setdefault(key, value)

    database, workspace_id = create_database_from_env()
    try:
        if not database.check():
            raise ConnectionError("Supabase Postgres health check failed.")
        anon_key = os.environ.get("SUPABASE_ANON_KEY", "").strip()
        if not anon_key:
            raise ValueError("SUPABASE_ANON_KEY is required for authenticated wallet access.")
        authenticator = SupabaseOwnerAuthenticator(
            database,
            supabase_url=os.environ.get("SUPABASE_URL", ""),
            anon_key=anon_key,
            workspace_id=workspace_id,
        )
        wallet_api = WalletWorkspaceApi(
            PostgresWalletRegistry(database, workspace_id),
            authenticator,
        )
        application = WalletOnlyApplication(wallet_api, PreviewApp())
        host = args.host or os.environ.get("COOLIE_BIND_HOST", "127.0.0.1")
        port = args.port or int(os.environ.get("COOLIE_PORT", "4173"))
        with make_server(host, port, application) as server:
            print(f"Coolie wallet workroom integration: http://{host}:{port}", flush=True)
            server.serve_forever()
    finally:
        database.close()


if __name__ == "__main__":
    main()
