from __future__ import annotations

import json
from typing import Callable

from research_room.models import Money

from .models import DecisionCode, OwnerObjective, ShariaStatus
from .service import OrchestratorService


class OrchestratorApi:
    def __init__(self, service: OrchestratorService | None = None) -> None:
        self._service = service or OrchestratorService()

    def __call__(self, environ: dict[str, object], start_response: Callable) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", "")).upper()
        path = str(environ.get("PATH_INFO", ""))

        if method == "GET" and path == "/orchestrator/health":
            return self._respond(start_response, "200 OK", {"status": "ok", "sector": "orchestrator"})

        if method == "POST" and path == "/orchestrator/decision":
            payload = self._read_json(environ)
            objective = self._objective_from_payload(payload)
            decision = self._service.decide(
                objective,
                sharia_status=ShariaStatus(str(payload["sharia_status"])),
                evidence_confidence=float(payload["evidence_confidence"]),
                budget_approved=bool(payload.get("budget_approved", False)),
                operational_risk=str(payload.get("operational_risk", "low")),
                approved_actions=tuple(str(item) for item in payload.get("approved_actions", ("monitor",)))
            )
            return self._respond(start_response, "200 OK", {"decision": decision.code.value, "summary": decision.summary})

        return self._respond(start_response, "404 Not Found", {"error": "not found"})

    @staticmethod
    def _read_json(environ: dict[str, object]) -> dict[str, object]:
        body = environ.get("wsgi.input")
        if body is None:
            raise ValueError("Request body is missing.")
        length = int(environ.get("CONTENT_LENGTH") or 0)
        if length <= 0:
            raise ValueError("Request body must not be empty.")
        content = body.read(length)
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("Request body must be valid JSON.") from exc
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    @staticmethod
    def _objective_from_payload(payload: dict[str, object]) -> OwnerObjective:
        title = str(payload.get("objective_id") or payload.get("id") or "")
        owner = str(payload.get("owner") or "system")
        summary = str(payload.get("summary") or payload.get("objective") or "Objective")
        desired = str(payload.get("desired_outcome") or "achieve the objective")
        max_budget = payload.get("max_budget")
        money = None
        if max_budget is not None:
            if not isinstance(max_budget, dict):
                raise ValueError("max_budget must be a JSON object with amount and currency.")
            money = Money(float(max_budget["amount"]), str(max_budget["currency"]))
        approval_required = bool(payload.get("approval_required", False))
        return OwnerObjective(
            objective_id=title,
            owner=owner,
            summary=summary,
            desired_outcome=desired,
            max_budget=money,
            approval_required=approval_required,
        )

    @staticmethod
    def _respond(start_response: Callable, status: str, body: dict[str, object]) -> list[bytes]:
        content = json.dumps(body, default=str, ensure_ascii=False, allow_nan=False).encode("utf-8")
        start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(content)))])
        return [content]
