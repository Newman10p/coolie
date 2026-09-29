from __future__ import annotations

import json
from typing import Callable

from .runtime import ReliabilityRuntime


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Non-standard JSON constant is not allowed: {value}.")


class ReliabilityApi:
    MAX_REQUEST_BYTES = 4_096

    def __init__(
        self,
        runtime: ReliabilityRuntime,
        *,
        authorize_operator: Callable[[dict[str, object]], str] | None = None,
    ) -> None:
        self._runtime = runtime
        self._authorize_operator = authorize_operator

    def __call__(self, environ: dict[str, object], start_response: Callable) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", "")).upper()
        path = str(environ.get("PATH_INFO", ""))
        if method == "GET" and path == "/health/live":
            return self._respond(start_response, "200 OK", {"live": True, "status": "alive"})
        if method == "GET" and path == "/health/startup":
            health = self._runtime.health_snapshot()
            ready = bool(health) and all(item.startup_complete for item in health)
            return self._respond(start_response, "200 OK" if ready else "503 Service Unavailable", {
                "startup_complete": ready,
                "services": [item.service for item in health],
            })
        if method == "GET" and path == "/health/ready":
            health = self._runtime.health_snapshot()
            ready = bool(health) and not self._runtime.failsafe.paused and all(
                item.readiness.value == "ready" for item in health
            )
            return self._respond(start_response, "200 OK" if ready else "503 Service Unavailable", {
                "ready": ready,
                "status": "ready" if ready else "not_ready",
                "paused": self._runtime.failsafe.paused,
                "reason": self._runtime.failsafe.reason,
                "services": [self._health_data(item) for item in health],
            })
        if method == "GET" and path == "/health/dependencies":
            return self._respond(start_response, "200 OK", {
                "services": [self._health_data(item) for item in self._runtime.health_snapshot()]
            })
        if method == "POST" and path in {"/system/emergency-pause", "/system/resume"}:
            if self._authorize_operator is None:
                return self._respond(start_response, "503 Service Unavailable", {
                    "error": "Authenticated operator control is not configured."
                })
            try:
                authority = self._authorize_operator(environ)
                if not isinstance(authority, str) or not authority.strip():
                    return self._respond(start_response, "403 Forbidden", {"error": "Operator authorization failed."})
                payload = self._read_json(environ)
                if path == "/system/emergency-pause":
                    reason = payload.get("reason")
                    if not isinstance(reason, str) or not reason.strip():
                        raise ValueError("reason is required.")
                    self._runtime.emergency_pause(reason, authority=authority)
                    return self._respond(start_response, "200 OK", self._runtime.failsafe.snapshot())
                self._runtime.resume(authority=authority)
                return self._respond(start_response, "200 OK", self._runtime.failsafe.snapshot())
            except PermissionError as error:
                return self._respond(start_response, "403 Forbidden", {"error": str(error)})
            except (KeyError, TypeError, ValueError) as error:
                return self._respond(start_response, "400 Bad Request", {"error": str(error)})
        return self._respond(start_response, "404 Not Found", {"error": "not found"})

    @classmethod
    def _read_json(cls, environ: dict[str, object]) -> dict[str, object]:
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except (TypeError, ValueError) as error:
            raise ValueError("Content-Length must be a valid integer.") from error
        if length <= 0 or length > cls.MAX_REQUEST_BYTES:
            raise ValueError("Request body size is invalid.")
        stream = environ.get("wsgi.input")
        if stream is None:
            raise ValueError("Request body is missing.")
        try:
            body = json.loads(stream.read(length), parse_constant=_reject_json_constant)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Request body must be valid JSON.") from error
        if not isinstance(body, dict):
            raise ValueError("Request body must be a JSON object.")
        return body

    @staticmethod
    def _health_data(health) -> dict[str, object]:
        return {
            "service": health.service,
            "liveness": health.liveness,
            "startup_complete": health.startup_complete,
            "readiness": health.readiness.value,
            "status": health.status.value,
            "reason": health.reason,
            "dependencies": {name: status.value for name, status in health.dependencies.items()},
        }

    @staticmethod
    def _respond(start_response: Callable, status: str, body: dict[str, object]) -> list[bytes]:
        content = json.dumps(body, default=str, ensure_ascii=False, allow_nan=False).encode("utf-8")
        start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(content)))])
        return [content]
