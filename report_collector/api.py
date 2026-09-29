from __future__ import annotations

from dataclasses import asdict
import json
from typing import Callable

from .service import ReportCollectorService


class ReportCollectorApi:
    def __init__(self, service: ReportCollectorService) -> None:
        self._service = service

    def __call__(self, environ: dict[str, object], start_response: Callable) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", ""))
        path = str(environ.get("PATH_INFO", ""))
        try:
            if method == "GET" and path == "/report-collector/health":
                return self._respond(start_response, "200 OK", self._service.health())
            if method == "POST" and path == "/report-collector/discover":
                length = int(environ.get("CONTENT_LENGTH") or 0)
                body = json.loads(environ["wsgi.input"].read(length) or b"{}")
                components = body.get("components", [])
                snapshot = self._service.discover(tuple({
                    (item["name"], item["category"], item["status"], item["owner"], item.get("details", ""))
                    for item in components
                }))
                # tuple of dicts is not directly convertible; rebuild using model shape
                records = []
                for item in components:
                    from .models import ComponentRecord
                    records.append(ComponentRecord(
                        name=item["name"],
                        category=item["category"],
                        status=item["status"],
                        owner=item["owner"],
                        details=item.get("details", ""),
                    ))
                snapshot = self._service.discover(tuple(records))
                return self._respond(start_response, "200 OK", asdict(snapshot))
            if method == "GET" and path == "/report-collector/discover":
                root = str(environ.get("QUERY_STRING", "")).replace("root=", "") or "."
                snapshot = self._service.discover_from_directory(root)
                return self._respond(start_response, "200 OK", asdict(snapshot))
            return self._respond(start_response, "404 Not Found", {"error": "not found"})
        except (KeyError, TypeError, ValueError) as error:
            return self._respond(start_response, "400 Bad Request", {"error": str(error)})

    @staticmethod
    def _respond(start_response: Callable, status: str, body: dict[str, object]) -> list[bytes]:
        content = json.dumps(body, default=str, ensure_ascii=False, allow_nan=False).encode("utf-8")
        start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(content)))])
        return [content]


__all__ = ["ReportCollectorApi"]
