"""Small WSGI boundary for authenticated Brain inference and provider health."""

from __future__ import annotations

from dataclasses import asdict
import json
from typing import Callable

from research_room.models import Money

from .models import BrainOperation, InferenceRequest
from .budget import BudgetExceeded
from .provider import ProviderError
from .runtime import BrainService, ProviderOutputError, SecretLeakError


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Non-standard JSON constant is not allowed: {value}.")


class BrainApi:
    MAX_REQUEST_BYTES = 1_048_576

    def __init__(self, service: BrainService) -> None:
        self._service = service

    def __call__(self, environ: dict[str, object], start_response: Callable) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", ""))
        path = str(environ.get("PATH_INFO", ""))
        try:
            if method == "GET" and path == "/brain/health":
                return self._respond(start_response, "200 OK", self._service.health())
            if method == "POST" and path == "/brain/inference":
                authorization = str(environ.get("HTTP_AUTHORIZATION", ""))
                if not authorization.startswith("Bearer ") or not authorization.removeprefix("Bearer ").strip():
                    return self._respond(start_response, "401 Unauthorized", {"error": "Bearer session token is required."})
                body = self._read_json(environ)
                request = self._inference_request(body)
                response = self._service.complete(
                    request, session_id=str(body["session_id"]), session_token=authorization.removeprefix("Bearer ").strip(),
                )
                return self._respond(start_response, "200 OK", asdict(response))
            return self._respond(start_response, "404 Not Found", {"error": "not found"})
        except BudgetExceeded as error:
            return self._respond(start_response, "429 Too Many Requests", {"error": str(error)})
        except (SecretLeakError, ProviderOutputError):
            return self._respond(start_response, "502 Bad Gateway", {"error": "Provider output failed Brain safety validation."})
        except PermissionError as error:
            return self._respond(start_response, "403 Forbidden", {"error": str(error)})
        except KeyError as error:
            return self._respond(start_response, "404 Not Found", {"error": str(error)})
        except ValueError as error:
            return self._respond(start_response, "400 Bad Request", {"error": str(error)})
        except ProviderError:
            return self._respond(start_response, "503 Service Unavailable", {"error": "Inference provider is unavailable."})

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
    def _inference_request(body: dict[str, object]) -> InferenceRequest:
        try:
            allowed_fields = {
                "session_id", "request_id", "agent_id", "sector", "task_id", "operation", "input",
                "max_tokens", "max_cost", "model_profile", "schema_name", "context_refs", "timeout_ms",
            }
            if set(body) - allowed_fields:
                raise ValueError("Request contains unsupported inference fields.")
            for name in ("session_id", "request_id", "agent_id", "sector", "task_id"):
                if not isinstance(body.get(name), str) or not body[name].strip():
                    raise ValueError(f"{name} must be a non-empty string.")
            cost_data = body["max_cost"]
            if not isinstance(cost_data, dict) or set(cost_data) != {"amount", "currency"}:
                raise ValueError("max_cost must contain amount and currency.")
            references = body.get("context_refs", ())
            if not isinstance(references, (list, tuple)) or any(not isinstance(reference, str) for reference in references):
                raise ValueError("context_refs must be a list of strings.")
            return InferenceRequest(
                request_id=body["request_id"],
                agent_id=body["agent_id"],
                sector=body["sector"],
                task_id=body["task_id"],
                operation=BrainOperation(str(body["operation"])),
                input=body["input"],
                max_tokens=body["max_tokens"],
                max_cost=Money(**cost_data),
                model_profile=body.get("model_profile"),
                schema_name=body.get("schema_name"),
                context_refs=tuple(references),
                timeout_ms=body.get("timeout_ms", 60_000),
            )
        except KeyError as error:
            raise ValueError(f"Missing inference field: {error.args[0]}") from error

    @staticmethod
    def _respond(start_response: Callable, status: str, body: dict[str, object]) -> list[bytes]:
        content = json.dumps(body, default=str, ensure_ascii=False, allow_nan=False).encode("utf-8")
        start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(content)))])
        return [content]
