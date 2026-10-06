"""Single-process desktop launcher and first-run setup for Coolie."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from threading import Lock, Timer
from typing import Callable
from urllib.parse import urlsplit
from uuid import UUID
from wsgiref.simple_server import WSGIServer, make_server
import webbrowser

from supabase_storage import PostgresWalletRegistry, create_database_from_env
from ui.demo_server import PreviewApp
from ui.supabase_auth import SupabaseOwnerAuthenticator
from ui.wallet_api import WalletOnlyApplication, WalletWorkspaceApi


MAX_SETUP_BODY = 16_384
_ENV_KEYS = (
    "SUPABASE_URL",
    "SUPABASE_REGION",
    "SUPABASE_ANON_KEY",
    "SUPABASE_DB_PASSWORD",
    "COOLIE_WORKSPACE_ID",
    "FIRECRAWL_API_KEY",
    "OPENSEARCH_URL",
    "OPENSEARCH_INDEX",
    "OPENSEARCH_USERNAME",
    "OPENSEARCH_PASSWORD",
    "COOLIE_RESEARCH_BROWSER_ALLOWED_HOSTS",
)


def user_config_path() -> Path:
    if configured_path := os.environ.get("COOLIE_CONFIG_PATH"):
        return Path(configured_path).expanduser()
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        return root / "Coolie" / "settings.env"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Coolie" / "settings.env"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "coolie" / "settings.env"


def _read_settings(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key in _ENV_KEYS:
            values[key] = value
    return values


def _validate_setup(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("Setup must be a JSON object.")
    values: dict[str, str] = {}
    for key in _ENV_KEYS:
        value = payload.get(key, "")
        if not isinstance(value, str) or any(character in value for character in "\r\n\x00"):
            raise ValueError(f"{key} must be a single-line string.")
        values[key] = value.strip()

    required = ("SUPABASE_URL", "SUPABASE_REGION", "SUPABASE_ANON_KEY", "SUPABASE_DB_PASSWORD", "COOLIE_WORKSPACE_ID")
    missing = [key for key in required if not values[key]]
    if missing:
        raise ValueError(f"Complete the required fields: {', '.join(missing)}.")
    parsed_url = urlsplit(values["SUPABASE_URL"])
    if parsed_url.scheme != "https" or not parsed_url.hostname or not parsed_url.hostname.endswith(".supabase.co"):
        raise ValueError("SUPABASE_URL must be an HTTPS Supabase project URL.")
    if parsed_url.path or parsed_url.query or parsed_url.fragment or parsed_url.username or parsed_url.password:
        raise ValueError("SUPABASE_URL must contain only the project origin.")
    if not re.fullmatch(r"[a-z0-9-]+", values["SUPABASE_REGION"], re.IGNORECASE):
        raise ValueError("SUPABASE_REGION is invalid.")
    if len(values["SUPABASE_ANON_KEY"]) > 8192 or len(values["SUPABASE_DB_PASSWORD"]) > 2048:
        raise ValueError("A Supabase setting exceeds the allowed length.")
    try:
        UUID(values["COOLIE_WORKSPACE_ID"])
    except ValueError as error:
        raise ValueError("COOLIE_WORKSPACE_ID must be a workspace UUID.") from error

    opensearch_fields = ("OPENSEARCH_URL", "OPENSEARCH_INDEX")
    if any(values[key] for key in opensearch_fields) and not all(values[key] for key in opensearch_fields):
        raise ValueError("Provide both OPENSEARCH_URL and OPENSEARCH_INDEX to configure OpenSearch.")
    if values["OPENSEARCH_URL"]:
        opensearch_url = urlsplit(values["OPENSEARCH_URL"])
        if opensearch_url.scheme != "https" or not opensearch_url.hostname:
            raise ValueError("OPENSEARCH_URL must be an HTTPS endpoint.")
    if values["OPENSEARCH_PASSWORD"] and not values["OPENSEARCH_USERNAME"]:
        raise ValueError("OPENSEARCH_USERNAME is required when an OpenSearch password is set.")
    if values["OPENSEARCH_USERNAME"] and not values["OPENSEARCH_PASSWORD"]:
        raise ValueError("OPENSEARCH_PASSWORD is required when an OpenSearch username is set.")

    if values["FIRECRAWL_API_KEY"] and (not values["OPENSEARCH_URL"] or not values["OPENSEARCH_INDEX"]):
        raise ValueError("Configure an OpenSearch endpoint and index before enabling Firecrawl research resources.")
    if values["FIRECRAWL_API_KEY"] and not values["COOLIE_RESEARCH_BROWSER_ALLOWED_HOSTS"]:
        raise ValueError("A browser host allowlist is required when configuring Firecrawl research resources.")
    return values


def _validate_auth_setup(payload: object) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("Connection setup must be a JSON object.")
    url = payload.get("SUPABASE_URL", "")
    anon_key = payload.get("SUPABASE_ANON_KEY", "")
    if not isinstance(url, str) or not isinstance(anon_key, str):
        raise ValueError("Supabase project URL and public anon key must be strings.")
    url = url.strip()
    anon_key = anon_key.strip()
    if len(url) > 2048 or any(character in url for character in "\r\n\x00"):
        raise ValueError("SUPABASE_URL must be a valid single-line project URL.")
    parsed_url = urlsplit(url)
    if parsed_url.scheme != "https" or not parsed_url.hostname or not parsed_url.hostname.endswith(".supabase.co"):
        raise ValueError("SUPABASE_URL must be an HTTPS Supabase project URL.")
    if parsed_url.path or parsed_url.query or parsed_url.fragment or parsed_url.username or parsed_url.password:
        raise ValueError("SUPABASE_URL must contain only the project origin.")
    if not anon_key or len(anon_key) > 8192 or any(character in anon_key for character in "\r\n\x00"):
        raise ValueError("SUPABASE_ANON_KEY must be a valid single-line public key.")
    return {"SUPABASE_URL": url, "SUPABASE_ANON_KEY": anon_key}


class DesktopApplication:
    """Serve the local setup flow, static UI, and supported wallet API."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or user_config_path()
        self._preview = PreviewApp()
        self._wallet_application: WalletOnlyApplication | None = None
        self._database = None
        self._lock = Lock()

    def __call__(self, environ: dict[str, object], start_response: Callable) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", "")).upper()
        path = str(environ.get("PATH_INFO", ""))
        if path.startswith("/api/setup"):
            return self._setup_route(environ, start_response, method, path)
        if path.startswith("/api/"):
            if not self._is_local_request(environ):
                return self._json(start_response, "403 Forbidden", {"error": "Coolie desktop APIs are available only from this local computer."})
            try:
                application = self._get_wallet_application()
            except (ValueError, ConnectionError, OSError) as error:
                return self._json(start_response, "503 Service Unavailable", {"error": str(error)})
            if application is None:
                return self._json(start_response, "503 Service Unavailable", {"error": "Complete first-run Supabase setup to enable the authenticated wallet API."})
            return application(environ, start_response)
        return self._preview(environ, start_response)

    def close(self) -> None:
        if self._database is not None:
            self._database.close()
            self._database = None
            self._wallet_application = None

    def _setup_route(self, environ: dict[str, object], start_response: Callable, method: str, path: str) -> list[bytes]:
        if not self._is_local_request(environ):
            return self._json(start_response, "403 Forbidden", {"error": "Coolie desktop setup is available only from this local computer."})
        if path not in {"/api/setup/config", "/api/setup/auth"}:
            return self._json(start_response, "404 Not Found", {"error": "Unknown setup route."})
        if method == "GET":
            settings = _read_settings(self.config_path)
            complete = all(settings.get(key) for key in (
                "SUPABASE_URL",
                "SUPABASE_REGION",
                "SUPABASE_ANON_KEY",
                "SUPABASE_DB_PASSWORD",
                "COOLIE_WORKSPACE_ID",
            ))
            public_config = {
                "authConfigured": bool(settings.get("SUPABASE_URL") and settings.get("SUPABASE_ANON_KEY")),
                "configured": complete,
                "supabaseUrl": settings.get("SUPABASE_URL", ""),
                "supabaseAnonKey": settings.get("SUPABASE_ANON_KEY", ""),
            }
            return self._json(start_response, "200 OK", public_config)
        if method != "POST":
            return self._json(start_response, "405 Method Not Allowed", {"error": "Setup accepts GET or POST."})
        if not self._valid_origin(environ):
            return self._json(start_response, "403 Forbidden", {"error": "Setup requests must originate from the local Coolie page."})
        raw_length = environ.get("CONTENT_LENGTH", "0")
        try:
            length = int(raw_length) if isinstance(raw_length, str) else 0
        except ValueError:
            length = -1
        if length <= 0 or length > MAX_SETUP_BODY:
            return self._json(start_response, "413 Content Too Large", {"error": "Setup payload is empty or exceeds the allowed size."})
        try:
            stream = environ.get("wsgi.input")
            if stream is None:
                raise ValueError("Setup request body is missing.")
            payload = json.loads(stream.read(length))
            if path == "/api/setup/auth":
                auth_settings = _validate_auth_setup(payload)
                settings = _read_settings(self.config_path)
                settings.update(auth_settings)
            else:
                settings = _read_settings(self.config_path)
                if isinstance(payload, dict):
                    for key, value in payload.items():
                        if key not in _ENV_KEYS:
                            continue
                        if isinstance(value, str) and not value.strip():
                            continue
                        settings[key] = value
                settings = _validate_setup(settings)
            self._save_settings(settings)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, OSError) as error:
            return self._json(start_response, "400 Bad Request", {"error": str(error)})
        self.close()
        return self._json(start_response, "200 OK", {"saved": True})

    def _save_settings(self, settings: dict[str, str]) -> None:
        path = self.config_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            path.parent.chmod(0o700)
        content = "".join(f"{key}={settings.get(key, '')}\n" for key in _ENV_KEYS)
        temporary = path.with_suffix(path.suffix + ".tmp")
        try:
            temporary.write_text(content, encoding="utf-8")
            if os.name != "nt":
                temporary.chmod(0o600)
            temporary.replace(path)
            if os.name != "nt":
                path.chmod(0o600)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _get_wallet_application(self) -> WalletOnlyApplication | None:
        if self._wallet_application is not None:
            return self._wallet_application
        with self._lock:
            if self._wallet_application is not None:
                return self._wallet_application
            settings = _read_settings(self.config_path)
            if not settings.get("COOLIE_WORKSPACE_ID"):
                return None
            database, workspace_id = create_database_from_env(
                env_file=self.config_path,
                environ=settings,
            )
            try:
                if not database.check():
                    raise ConnectionError("Supabase Postgres health check failed.")
                authenticator = SupabaseOwnerAuthenticator(
                    database,
                    supabase_url=settings.get("SUPABASE_URL", ""),
                    anon_key=settings.get("SUPABASE_ANON_KEY", ""),
                    workspace_id=workspace_id,
                )
                wallet_api = WalletWorkspaceApi(
                    PostgresWalletRegistry(database, workspace_id),
                    authenticator,
                )
                self._database = database
                self._wallet_application = WalletOnlyApplication(wallet_api, self._preview)
                return self._wallet_application
            except Exception:
                database.close()
                raise

    @staticmethod
    def _is_local_request(environ: dict[str, object]) -> bool:
        address = environ.get("REMOTE_ADDR")
        return address in {"127.0.0.1", "::1"}

    @classmethod
    def _valid_origin(cls, environ: dict[str, object]) -> bool:
        origin = environ.get("HTTP_ORIGIN")
        if not isinstance(origin, str):
            return False
        parsed = urlsplit(origin)
        host = parsed.hostname
        request_host = environ.get("HTTP_HOST")
        return (
            parsed.scheme == "http"
            and host in {"127.0.0.1", "localhost", "::1"}
            and isinstance(request_host, str)
            and request_host.casefold() == (parsed.netloc or "").casefold()
            and cls._is_local_request(environ)
        )

    @staticmethod
    def _json(start_response: Callable, status: str, payload: dict[str, object]) -> list[bytes]:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        start_response(status, [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
        ])
        return [body]


def _open_local_browser(url: str) -> None:
    webbrowser.open(url, new=2)


def _local_log(message: str) -> None:
    log_path = user_config_path().parent / "coolie.log"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as log:
            log.write(message.replace("\r", " ").replace("\n", " ") + "\n")
    except OSError:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Coolie desktop workroom.")
    parser.add_argument("--host", default="127.0.0.1", help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, default=4173, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("Coolie desktop can bind only to this computer.")
    application = DesktopApplication()
    server: WSGIServer | None = None
    try:
        server = make_server(args.host, args.port, application)
        _, port = server.server_address[:2]
        url = f"http://127.0.0.1:{port}/"
        _local_log("Coolie local server started.")
        Timer(0.75, _open_local_browser, args=(url,)).start()
        server.serve_forever()
    except Exception as error:
        _local_log(f"Coolie could not start: {type(error).__name__}: {error}")
        if getattr(sys, "frozen", False):
            try:
                import tkinter
                from tkinter import messagebox

                root = tkinter.Tk()
                root.withdraw()
                messagebox.showerror("Coolie could not start", f"See the local log for details:\n{user_config_path().parent / 'coolie.log'}")
                root.destroy()
            except Exception:
                pass
        else:
            raise
    finally:
        if server is not None:
            server.server_close()
        application.close()


if __name__ == "__main__":
    main()
