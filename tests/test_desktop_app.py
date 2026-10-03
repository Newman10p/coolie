from __future__ import annotations

import json
from io import BytesIO
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from ui.desktop_app import DesktopApplication


def request(application, method: str, path: str, *, payload=None, origin="http://127.0.0.1:4173"):
    body = json.dumps(payload).encode() if payload is not None else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "HTTP_HOST": "127.0.0.1:4173",
        "HTTP_ORIGIN": origin,
        "REMOTE_ADDR": "127.0.0.1",
        "wsgi.input": BytesIO(body),
    }
    response = {}

    def start_response(status, headers):
        response["status"] = status
        response["headers"] = dict(headers)

    response["body"] = b"".join(application(environ, start_response))
    return response


def complete_setup():
    return {
        "SUPABASE_URL": "https://coolie-test.supabase.co",
        "SUPABASE_REGION": "us-east-1",
        "SUPABASE_ANON_KEY": "public-test-anon",
        "SUPABASE_DB_PASSWORD": "local test secret",
        "COOLIE_WORKSPACE_ID": str(uuid4()),
    }


class DesktopSetupTests(unittest.TestCase):
    def test_desktop_host_serves_the_built_workroom_ui(self):
        with TemporaryDirectory() as directory:
            application = DesktopApplication(Path(directory) / "settings.env")
            response = request(application, "GET", "/")
            if response["status"] == "200 OK":
                self.assertIn(b"Coolie", response["body"])
            else:
                self.assertEqual(response["status"], "503 Service Unavailable")
                self.assertIn(b"npm run build", response["body"])

    def test_first_run_config_is_incomplete_then_saves_private_settings(self):
        with TemporaryDirectory() as directory:
            config_path = Path(directory) / "coolie" / "settings.env"
            application = DesktopApplication(config_path)

            before = request(application, "GET", "/api/setup/config")
            self.assertEqual(before["status"], "200 OK")
            self.assertEqual(json.loads(before["body"]), {
                "configured": False,
                "supabaseUrl": "",
                "supabaseAnonKey": "",
            })

            settings = complete_setup()
            saved = request(application, "POST", "/api/setup/config", payload=settings)
            self.assertEqual(saved["status"], "200 OK")
            self.assertEqual(json.loads(saved["body"]), {"saved": True})
            self.assertTrue(config_path.is_file())
            persisted = config_path.read_text(encoding="utf-8")
            self.assertIn("SUPABASE_DB_PASSWORD=local test secret", persisted)

            after = request(application, "GET", "/api/setup/config")
            payload = json.loads(after["body"])
            self.assertTrue(payload["configured"])
            self.assertEqual(payload["supabaseAnonKey"], settings["SUPABASE_ANON_KEY"])
            self.assertNotIn(settings["SUPABASE_DB_PASSWORD"], after["body"].decode())
            if os.name != "nt":
                self.assertEqual(config_path.stat().st_mode & 0o777, 0o600)
            application.close()

    def test_setup_requires_workspace_and_rejects_remote_origin(self):
        with TemporaryDirectory() as directory:
            application = DesktopApplication(Path(directory) / "settings.env")
            incomplete = request(
                application,
                "POST",
                "/api/setup/config",
                payload={"SUPABASE_URL": "https://coolie-test.supabase.co"},
            )
            self.assertEqual(incomplete["status"], "400 Bad Request")
            self.assertIn(b"COOLIE_WORKSPACE_ID", incomplete["body"])

            remote = request(
                application,
                "POST",
                "/api/setup/config",
                payload=complete_setup(),
                origin="https://attacker.example",
            )
            self.assertEqual(remote["status"], "403 Forbidden")

    def test_provider_configuration_must_be_complete(self):
        with TemporaryDirectory() as directory:
            application = DesktopApplication(Path(directory) / "settings.env")
            settings = complete_setup()
            settings["OPENSEARCH_URL"] = "https://search.example.com"
            response = request(application, "POST", "/api/setup/config", payload=settings)
            self.assertEqual(response["status"], "400 Bad Request")
            self.assertIn(b"OPENSEARCH_INDEX", response["body"])

    def test_api_remains_explicitly_disabled_until_supabase_setup(self):
        with TemporaryDirectory() as directory:
            application = DesktopApplication(Path(directory) / "settings.env")
            response = request(application, "GET", "/api/wallets")
            self.assertEqual(response["status"], "503 Service Unavailable")
            self.assertIn(b"Complete first-run Supabase setup", response["body"])


if __name__ == "__main__":
    unittest.main()
