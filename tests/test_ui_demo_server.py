import json
from io import BytesIO
import unittest

from ui.demo_server import application
from ui.live_app import LiveCoolieApplication


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


class PreviewServerTests(unittest.TestCase):
    def test_api_routes_explicitly_report_preview_is_not_connected(self):
        response, body = call_wsgi("GET", "/api/ui/bootstrap")
        self.assertEqual(response["status"], "503 Service Unavailable")
        payload = json.loads(body)
        self.assertEqual(payload["dataMode"], "preview")
        self.assertIn("does not connect", payload["error"])

    def test_preview_serves_built_react_app_when_present(self):
        response, body = call_wsgi("GET", "/")
        if response["status"] == "503 Service Unavailable":
            self.assertIn(b"npm run build", body)
        else:
            self.assertEqual(response["status"], "200 OK")
            self.assertIn(b"Coolie", body)

    def test_unknown_paths_and_traversal_are_not_exposed(self):
        for path in ("/missing", "/../../README.md"):
            with self.subTest(path=path):
                response, body = call_wsgi("GET", path)
                self.assertEqual(response["status"], "404 Not Found")
                self.assertNotIn(b"Research Room", body)

    def test_live_host_routes_api_and_static_requests_to_the_correct_app(self):
        calls = []

        def api(environ, start_response):
            calls.append(("api", environ["PATH_INFO"]))
            start_response("200 OK", [("Content-Type", "text/plain")])
            return [b"authenticated-api"]

        def static(environ, start_response):
            calls.append(("static", environ["PATH_INFO"]))
            start_response("200 OK", [("Content-Type", "text/plain")])
            return [b"workroom"]

        live = LiveCoolieApplication(api, static)
        for path, expected in (
            ("/api/ui/bootstrap", b"authenticated-api"),
            ("/", b"workroom"),
        ):
            environ = {
                "REQUEST_METHOD": "GET",
                "PATH_INFO": path,
                "CONTENT_LENGTH": "0",
                "wsgi.input": BytesIO(b""),
            }
            result = {}

            def start_response(status, _headers):
                result["status"] = status

            self.assertEqual(b"".join(live(environ, start_response)), expected)
            self.assertEqual(result["status"], "200 OK")
        self.assertEqual(calls, [
            ("api", "/api/ui/bootstrap"),
            ("static", "/"),
        ])


if __name__ == "__main__":
    unittest.main()
