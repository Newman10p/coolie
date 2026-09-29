"""Minimal standard-library WSGI boundary; internal tools are intentionally not exposed."""
from __future__ import annotations

from dataclasses import asdict
import json
from typing import Callable

from reliability import SystemPausedError

from .models import Money, ResearchMission
from .service import ResearchRoomService


class ResearchRoomApi:
    def __init__(self, service: ResearchRoomService) -> None: self._service = service
    def __call__(self, environ: dict[str, object], start_response: Callable) -> list[bytes]:
        method, path = environ["REQUEST_METHOD"], environ["PATH_INFO"]
        try:
            if method == "GET" and path == "/research/health":
                health = self._service.health()
                return self._respond(
                    start_response,
                    "503 Service Unavailable" if not health["ready"] else "200 OK",
                    health,
                )
            if method == "POST" and path == "/research-missions":
                length = int(environ.get("CONTENT_LENGTH") or 0); body = json.loads(environ["wsgi.input"].read(length) or b"{}")
                capital = body.get("capital_limit")
                if capital: body["capital_limit"] = Money(**capital)
                mission = self._service.create_mission(ResearchMission(**body), str(environ.get("HTTP_X_ACTOR_ID", "api")))
                return self._respond(start_response, "201 Created", asdict(mission))
            if method == "POST" and path.startswith("/research-missions/"):
                mission_id, action = path.removeprefix("/research-missions/").rsplit("/", 1)
                actor = str(environ.get("HTTP_X_ACTOR_ID", "api")); reason = str(environ.get("HTTP_X_REASON", action))
                if action == "pause": return self._respond(start_response, "200 OK", asdict(self._service.pause_mission(mission_id, actor, reason)))
                if action == "resume": return self._respond(start_response, "200 OK", asdict(self._service.resume_mission(mission_id, actor, reason)))
                if action == "cancel": return self._respond(start_response, "200 OK", asdict(self._service.cancel_mission(mission_id, actor, reason)))
            if method == "GET" and path.startswith("/research-missions/"):
                mission_id = path.rsplit("/", 1)[-1]
                if mission_id.endswith("progress"):
                    mission_id = path.removesuffix("/progress").rsplit("/", 1)[-1]
                    return self._respond(start_response, "200 OK", asdict(self._service.progress(mission_id)))
                return self._respond(start_response, "200 OK", asdict(self._service.missions.get(mission_id)))
            return self._respond(start_response, "404 Not Found", {"error": "not found"})
        except SystemPausedError as error:
            return self._respond(start_response, "503 Service Unavailable", {"error": str(error)})
        except (KeyError, ValueError) as error:
            return self._respond(start_response, "400 Bad Request", {"error": str(error)})
    @staticmethod
    def _respond(start_response: Callable, status: str, body: dict[str, object]) -> list[bytes]:
        content = json.dumps(body, default=str).encode("utf-8")
        start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(content)))])
        return [content]
