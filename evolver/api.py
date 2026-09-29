from __future__ import annotations

from dataclasses import asdict
import json
from typing import Callable

from reliability import SystemPausedError

from research_room.models import Money

from .models import ExpansionRequest
from .service import EvolverService


class EvolverApi:
    def __init__(self, service: EvolverService) -> None:
        self._service = service

    def __call__(self, environ: dict[str, object], start_response: Callable) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", ""))
        path = str(environ.get("PATH_INFO", ""))
        try:
            if method == "GET" and path == "/evolver/health":
                health = self._service.health()
                return self._respond(
                    start_response,
                    "200 OK" if health["ready"] else "503 Service Unavailable",
                    health,
                )
            if method == "POST" and path == "/evolver/assess":
                length = int(environ.get("CONTENT_LENGTH") or 0)
                body = json.loads(environ["wsgi.input"].read(length) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError("Request body must be a JSON object.")
                allowed = {
                    "request_id", "business_domain", "idea", "required_capabilities",
                    "expected_monthly_revenue", "max_budget", "risk_tolerance", "created_at",
                    "existing_capabilities",
                }
                if set(body) - allowed:
                    raise ValueError("Request contains unsupported Evolver fields.")
                existing_capabilities = body.pop("existing_capabilities", ())
                if not isinstance(existing_capabilities, (list, tuple)) or any(
                    not isinstance(item, str) or not item.strip() for item in existing_capabilities
                ):
                    raise ValueError("existing_capabilities must be a list of non-empty strings.")
                required_capabilities = body.get("required_capabilities")
                if not isinstance(required_capabilities, (list, tuple)) or any(
                    not isinstance(item, str) or not item.strip() for item in required_capabilities
                ):
                    raise ValueError("required_capabilities must be a list of non-empty strings.")
                body["required_capabilities"] = tuple(required_capabilities)
                if body.get("expected_monthly_revenue") is not None:
                    body["expected_monthly_revenue"] = Money(**body["expected_monthly_revenue"])
                if body.get("max_budget") is not None:
                    body["max_budget"] = Money(**body["max_budget"])
                request = ExpansionRequest(**body)
                plan = self._service.assess(request, existing_capabilities=tuple(existing_capabilities))
                return self._respond(start_response, "200 OK", asdict(plan))
            return self._respond(start_response, "404 Not Found", {"error": "not found"})
        except SystemPausedError as error:
            return self._respond(start_response, "503 Service Unavailable", {"error": str(error)})
        except (TypeError, ValueError, KeyError) as error:
            return self._respond(start_response, "400 Bad Request", {"error": str(error)})

    @staticmethod
    def _respond(start_response: Callable, status: str, body: dict[str, object]) -> list[bytes]:
        content = json.dumps(body, default=str, ensure_ascii=False, allow_nan=False).encode("utf-8")
        start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(content)))])
        return [content]


__all__ = ["EvolverApi"]
