from __future__ import annotations

from dataclasses import asdict
import json
from typing import Callable

from research_room.models import Money

from .models import ActivationProposal
from .service import MoneyCalculatorService


class MoneyCalculatorApi:
    def __init__(self, service: MoneyCalculatorService) -> None:
        self._service = service

    def __call__(self, environ: dict[str, object], start_response: Callable) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", ""))
        path = str(environ.get("PATH_INFO", ""))
        try:
            if method == "GET" and path == "/money-calculator/health":
                return self._respond(start_response, "200 OK", self._service.health())
            if method == "POST" and path == "/money-calculator/assess":
                length = int(environ.get("CONTENT_LENGTH") or 0)
                body = json.loads(environ["wsgi.input"].read(length) or b"{}")
                if body.get("planned_spend"):
                    body["planned_spend"] = Money(**body["planned_spend"])
                if body.get("expected_revenue"):
                    body["expected_revenue"] = Money(**body["expected_revenue"])
                proposal = ActivationProposal(**body)
                budget_limit = body.get("budget_limit")
                if budget_limit is not None:
                    budget_limit = Money(**budget_limit)
                recommendation = self._service.assess(proposal, budget_limit=budget_limit)
                return self._respond(start_response, "200 OK", asdict(recommendation))
            return self._respond(start_response, "404 Not Found", {"error": "not found"})
        except (KeyError, TypeError, ValueError) as error:
            return self._respond(start_response, "400 Bad Request", {"error": str(error)})

    @staticmethod
    def _respond(start_response: Callable, status: str, body: dict[str, object]) -> list[bytes]:
        content = json.dumps(body, default=str, ensure_ascii=False, allow_nan=False).encode("utf-8")
        start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(content)))])
        return [content]


__all__ = ["MoneyCalculatorApi"]
