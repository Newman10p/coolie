from __future__ import annotations

from dataclasses import asdict
import json
from typing import Callable

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
                return self._respond(start_response, "200 OK", self._service.health())
            if method == "POST" and path == "/evolver/assess":
                length = int(environ.get("CONTENT_LENGTH") or 0)
                body = json.loads(environ["wsgi.input"].read(length) or b"{}")
                if body.get("expected_monthly_revenue") is not None:
                    body["expected_monthly_revenue"] = Money(**body["expected_monthly_revenue"])
                if body.get("max_budget") is not None:
                    body["max_budget"] = Money(**body["max_budget"])
                request = ExpansionRequest(**body)
                existing_capabilities = tuple(body.get("existing_capabilities", ()))
                plan = self._service.assess(request, existing_capabilities=existing_capabilities)
                return self._respond(start_response, "200 OK", asdict(plan))
            return self._respond(start_response, "404 Not Found", {"error": "not found"})
        except (TypeError, ValueError, KeyError) as error:
            return self._respond(start_response, "400 Bad Request", {"error": str(error)})

    @staticmethod
    def _respond(start_response: Callable, status: str, body: dict[str, object]) -> list[bytes]:
        content = json.dumps(body, default=str, ensure_ascii=False, allow_nan=False).encode("utf-8")
        start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(content)))])
        return [content]


__all__ = ["EvolverApi"]
