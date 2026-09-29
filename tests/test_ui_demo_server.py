import json
from io import BytesIO
import unittest

from ui.demo_server import application


def call_wsgi(method: str, path: str):
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": "0",
        "wsgi.input": BytesIO(b""),
    }
    captured = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)

    body = b"".join(application(environ, start_response))
    return captured, body


class DemoWorkroomServerTests(unittest.TestCase):
    def test_owner_read_models_are_marked_as_sample(self):
        for path in ("/api/ui/briefing", "/api/ui/office-table", "/api/ui/reports"):
            with self.subTest(path=path):
                response, body = call_wsgi("GET", path)
                self.assertEqual(response["status"], "200 OK")
                self.assertEqual(response["headers"]["Content-Type"], "application/json; charset=utf-8")
                self.assertEqual(json.loads(body)["dataMode"], "sample")

    def test_health_endpoint_does_not_claim_real_readiness(self):
        response, body = call_wsgi("GET", "/api/health/ready")
        health = json.loads(body)
        self.assertEqual(response["status"], "503 Service Unavailable")
        self.assertEqual(health["dataMode"], "sample")
        self.assertFalse(health["ready"])
        self.assertIn("does not connect", health["reason"])

    def test_sample_server_rejects_owner_controls(self):
        for path in ("/api/system/emergency-pause", "/api/system/resume"):
            with self.subTest(path=path):
                response, body = call_wsgi("POST", path)
                self.assertEqual(response["status"], "405 Method Not Allowed")
                self.assertEqual(json.loads(body)["error"], "method not allowed")

        response, body = call_wsgi("GET", "/api/system/resume")
        self.assertEqual(response["status"], "503 Service Unavailable")
        self.assertEqual(json.loads(body)["dataMode"], "sample")

    def test_sample_server_does_not_fake_voice_or_orchestrator_responses(self):
        for path in ("/api/orchestrator/transcribe", "/api/orchestrator/messages"):
            with self.subTest(path=path):
                response, body = call_wsgi("POST", path)
                self.assertEqual(response["status"], "503 Service Unavailable")
                payload = json.loads(body)
                self.assertEqual(payload["dataMode"], "sample")
                self.assertIn("not connected", payload["error"])

    def test_static_ui_is_served_and_unknown_paths_are_not_exposed(self):
        response, body = call_wsgi("GET", "/")
        self.assertEqual(response["status"], "200 OK")
        self.assertIn(b"Coolie", body)
        self.assertIn(b"voice-toggle", body)
        self.assertIn(b"orchestrator-prompt", body)

        response, body = call_wsgi("GET", "/../README.md")
        self.assertEqual(response["status"], "404 Not Found")
        self.assertNotIn(b"Research Room", body)


if __name__ == "__main__":
    unittest.main()
