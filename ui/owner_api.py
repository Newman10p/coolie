"""Authenticated same-origin adapter for the composed Coolie domain APIs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import Enum
import json
from io import BytesIO
from typing import Callable, Mapping
from uuid import uuid4

from brain.api import BrainApi
from evolver.api import EvolverApi
from money_calculator.api import MoneyCalculatorApi
from orchestrator.api import OrchestratorApi
from reliability import SystemPausedError
from research_room.api import ResearchRoomApi
from research_room.models import Money, ResearchMission
from report_collector.api import ReportCollectorApi
from sector3_enactor.api.routes import EnactorApi
from sector3_enactor.controller.execution_controller import ExecutionController
from sector3_enactor.models.approval import ApprovalLevel
from supabase_storage.wallets import (
    WalletAccount,
    WalletRegistry,
    WalletWithdrawalRequest,
)


@dataclass(frozen=True)
class OwnerPrincipal:
    subject: str
    permissions: frozenset[str]
    approver_level: ApprovalLevel | None = None

    def __post_init__(self) -> None:
        if not self.subject.strip():
            raise ValueError("Owner identity subject must not be empty.")
        if not isinstance(self.permissions, frozenset):
            raise ValueError("Owner identity permissions must be a frozenset.")


Authenticator = Callable[[dict[str, object]], OwnerPrincipal | None]


class OwnerWorkspaceApi:
    """Expose domain APIs only after an injected owner authenticator grants access.

    Authentication and permission assignment are deployment responsibilities;
    no local or default identity is trusted by this adapter.
    """

    MAX_REQUEST_BYTES = 1_048_576
    _DOMAIN_PREFIXES = (
        ("/api/brain/", "brain", "/brain/"),
        ("/api/research/", "research_room", "/research/"),
        ("/api/research-missions", "research_room", "/research-missions"),
        ("/api/orchestrator/", "orchestrator", "/orchestrator/"),
        ("/api/money-calculator/", "money_calculator", "/money-calculator/"),
        ("/api/evolver/", "evolver", "/evolver/"),
        ("/api/report-collector/", "report_collector", "/report-collector/"),
    )

    def __init__(
        self,
        system: object,
        authenticate: Authenticator,
        *,
        wallet_registry: WalletRegistry | None = None,
    ) -> None:
        if not callable(authenticate):
            raise TypeError("An owner authenticator callback is required.")
        self._system = system
        self._authenticate = authenticate
        self._wallet_registry = wallet_registry
        services = getattr(system, "services", None)
        if not isinstance(services, Mapping):
            raise TypeError("The API requires a composed CoolieSystem.")

        enactor_service = services["sector3_enactor"]
        controller = (
            enactor_service
            if isinstance(enactor_service, ExecutionController)
            else getattr(enactor_service, "controller", None)
        )
        if not isinstance(controller, ExecutionController):
            raise TypeError("The composed Enactor service must expose its ExecutionController.")

        self._apis: dict[str, Callable] = {
            "brain": BrainApi(services["brain"]),
            "research_room": ResearchRoomApi(services["research_room"]),
            "orchestrator": OrchestratorApi(services["orchestrator"]),
            "money_calculator": MoneyCalculatorApi(services["money_calculator"]),
            "sector3_enactor": EnactorApi(controller),
            "evolver": EvolverApi(services["evolver"]),
            "report_collector": ReportCollectorApi(services["report_collector"]),
        }

    def __call__(self, environ: dict[str, object], start_response: Callable) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", "")).upper()
        path = str(environ.get("PATH_INFO", ""))
        if not path.startswith("/api/"):
            return self._respond(start_response, "404 Not Found", {"error": "not found"})
        if method not in {"GET", "HEAD", "POST", "PATCH", "DELETE"}:
            return self._respond(start_response, "405 Method Not Allowed", {"error": "method not allowed"})

        principal = self._authenticate(environ)
        if principal is None:
            return self._respond(start_response, "401 Unauthorized", {"error": "Owner authentication is required."})
        permission = self._required_permission(method, path)
        if permission not in principal.permissions:
            return self._respond(start_response, "403 Forbidden", {"error": f"Missing permission: {permission}."})

        if path == "/api/ui/bootstrap":
            if method != "GET":
                return self._respond(start_response, "405 Method Not Allowed", {"error": "method not allowed"})
            return self._bootstrap(start_response)
        if path == "/api/ui/missions":
            return self._missions(environ, start_response, method, principal)
        if path == "/api/wallets" or path.startswith("/api/wallets/"):
            return self._wallets(environ, start_response, method, path, principal)
        if path.startswith("/api/enactor/"):
            return self._enactor(environ, start_response, method, path, principal)

        for prefix, service_name, domain_path in self._DOMAIN_PREFIXES:
            if path == prefix.rstrip("/") or path.startswith(prefix):
                child_path = domain_path + path[len(prefix):] if path.startswith(prefix) else domain_path
                return self._call_domain(
                    environ, start_response, service_name, child_path, principal
                )
        return self._respond(start_response, "404 Not Found", {"error": "not found"})

    @staticmethod
    def _required_permission(method: str, path: str) -> str:
        if path == "/api/wallets" or path.startswith("/api/wallets/"):
            return "treasury:manage" if method in {"POST", "PATCH", "DELETE"} else "workspace:read"
        if path.startswith("/api/enactor/approvals/") and path.endswith("/decision"):
            return "enactor:approve"
        if path == "/api/enactor/executions" or path.endswith("/resume"):
            return "enactor:execute"
        if path.startswith("/api/system/"):
            return "system:control"
        return "workspace:read" if method in {"GET", "HEAD"} else "workspace:write"

    def _wallets(
        self,
        environ: dict[str, object],
        start_response: Callable,
        method: str,
        path: str,
        principal: OwnerPrincipal,
    ) -> list[bytes]:
        if self._wallet_registry is None:
            return self._respond(
                start_response,
                "503 Service Unavailable",
                {"error": "Watch-only wallet registry is not configured."},
            )
        if method in {"GET", "HEAD"} and path == "/api/wallets":
            return self._respond(
                start_response,
                "200 OK",
                {
                    "dataMode": "live",
                    "custody": "watch_only",
                    "wallets": [
                        self._wallet_to_json(wallet)
                        for wallet in self._wallet_registry.list_accounts()
                    ],
                },
            )
        if method in {"GET", "HEAD"} and path == "/api/wallets/withdrawals":
            return self._respond(
                start_response,
                "200 OK",
                {
                    "dataMode": "live",
                    "withdrawalRequests": [
                        self._withdrawal_to_json(request)
                        for request in self._wallet_registry.list_withdrawals()
                    ],
                },
            )
        if method == "POST" and path == "/api/wallets/withdrawals":
            try:
                body = self._read_json(environ)
                allowed = {
                    "walletId",
                    "destinationAddress",
                    "amount",
                    "memo",
                }
                if set(body) - allowed or not {
                    "walletId",
                    "destinationAddress",
                    "amount",
                }.issubset(body):
                    raise ValueError(
                        "Withdrawal request requires walletId, destinationAddress, and amount."
                    )
                if not isinstance(body["amount"], str):
                    raise ValueError("amount must be a decimal string.")
                if body.get("memo") is not None and not isinstance(body["memo"], str):
                    raise ValueError("memo must be a string.")
                request = self._wallet_registry.request_withdrawal(
                    wallet_id=body["walletId"],
                    destination_address=body["destinationAddress"],
                    amount=body["amount"],
                    memo=body.get("memo"),
                    requested_by=principal.subject,
                )
            except KeyError:
                return self._respond(start_response, "404 Not Found", {"error": "active spending wallet not found"})
            except ValueError as error:
                return self._respond(start_response, "400 Bad Request", {"error": str(error)})
            return self._respond(
                start_response,
                "202 Accepted",
                self._withdrawal_to_json(request),
            )

        wallet_id = path.removeprefix("/api/wallets/").strip("/")
        if method == "DELETE" and wallet_id and "/" not in wallet_id:
            try:
                wallet = self._wallet_registry.deactivate(
                    wallet_id, updated_by=principal.subject
                )
            except KeyError:
                return self._respond(start_response, "404 Not Found", {"error": "wallet not found or inactive"})
            except ValueError as error:
                return self._respond(start_response, "400 Bad Request", {"error": str(error)})
            return self._respond(start_response, "200 OK", self._wallet_to_json(wallet))
        if method == "PATCH" and wallet_id and "/" not in wallet_id:
            try:
                body = self._read_json(environ)
                allowed = {"purpose", "label", "network", "asset", "address"}
                if not body or set(body) - allowed:
                    raise ValueError("Wallet update contains unsupported or missing fields.")
                wallet = self._wallet_registry.update(
                    wallet_id,
                    updated_by=principal.subject,
                    changes=body,
                )
            except KeyError:
                return self._respond(start_response, "404 Not Found", {"error": "wallet not found or inactive"})
            except ValueError as error:
                message = str(error)
                status = (
                    "409 Conflict"
                    if "already exists for this purpose" in message
                    else "400 Bad Request"
                )
                return self._respond(start_response, status, {"error": message})
            return self._respond(start_response, "200 OK", self._wallet_to_json(wallet))
        if method != "POST" or path != "/api/wallets":
            return self._respond(start_response, "404 Not Found", {"error": "not found"})
        try:
            body = self._read_json(environ)
            allowed = {"purpose", "label", "network", "asset", "address"}
            if set(body) != allowed:
                raise ValueError(
                    "Wallet setup requires exactly purpose, label, network, asset, and public address."
                )
            wallet = self._wallet_registry.register(
                purpose=body["purpose"],
                label=body["label"],
                network=body["network"],
                asset=body["asset"],
                address=body["address"],
                created_by=principal.subject,
            )
        except ValueError as error:
            message = str(error)
            status = (
                "409 Conflict"
                if "already exists for this purpose" in message
                else "400 Bad Request"
            )
            return self._respond(start_response, status, {"error": message})
        return self._respond(start_response, "201 Created", self._wallet_to_json(wallet))

    @staticmethod
    def _wallet_to_json(wallet: WalletAccount) -> dict[str, object]:
        return {
            "walletId": wallet.wallet_id,
            "purpose": wallet.purpose,
            "label": wallet.label,
            "network": wallet.network,
            "asset": wallet.asset,
            "address": wallet.address,
            "custody": "watch_only",
            "status": wallet.status,
            "createdBy": wallet.created_by,
            "createdAt": wallet.created_at.isoformat(),
            "updatedBy": wallet.updated_by,
        }

    @staticmethod
    def _withdrawal_to_json(
        request: WalletWithdrawalRequest,
    ) -> dict[str, object]:
        return {
            "requestId": request.request_id,
            "walletId": request.wallet_id,
            "destinationAddress": request.destination_address,
            "network": request.network,
            "asset": request.asset,
            "amount": request.amount,
            "memo": request.memo,
            "requestedBy": request.requested_by,
            "requestedAt": request.requested_at.isoformat(),
            "status": request.status,
            "execution": "not_executed",
        }

    def _bootstrap(self, start_response: Callable) -> list[bytes]:
        services = []
        for sector in self._system.SECTORS:
            health = self._system.health(sector)
            services.append({
                "service": health.service,
                "liveness": health.liveness,
                "startupComplete": health.startup_complete,
                "readiness": health.readiness.value,
                "status": health.status.value,
                "reason": health.reason,
            })
        research = self._system.services["research_room"]
        missions = tuple(research.missions.all())
        return self._respond(start_response, "200 OK", {
            "dataMode": "live",
            "services": services,
            "missions": [self._mission_to_json(mission) for mission in missions],
        })

    def _missions(
        self,
        environ: dict[str, object],
        start_response: Callable,
        method: str,
        principal: OwnerPrincipal,
    ) -> list[bytes]:
        service = self._system.services["research_room"]
        if method in {"GET", "HEAD"}:
            return self._respond(start_response, "200 OK", {
                "dataMode": "live",
                "missions": [self._mission_to_json(item) for item in service.missions.all()],
            })
        try:
            body = self._read_json(environ)
            allowed = {
                "objective", "markets", "businessModels", "riskTolerance",
                "requiredEvidenceLevel", "capitalLimit", "timeLimitDays",
            }
            if set(body) - allowed:
                raise ValueError("Request contains unsupported mission fields.")
            required = ("objective", "markets", "businessModels", "riskTolerance", "requiredEvidenceLevel")
            if any(field not in body for field in required):
                raise ValueError("Mission objective, markets, businessModels, riskTolerance, and requiredEvidenceLevel are required.")
            capital = body.get("capitalLimit")
            if capital is not None:
                if not isinstance(capital, dict) or set(capital) != {"amount", "currency"}:
                    raise ValueError("capitalLimit must include amount and currency.")
                capital = Money(**capital)
            mission = ResearchMission(
                mission_id=f"MSN-{uuid4().hex}",
                objective=body["objective"],
                requested_by="human",
                markets=body["markets"],
                business_models=body["businessModels"],
                risk_tolerance=body["riskTolerance"],
                required_evidence_level=body["requiredEvidenceLevel"],
                capital_limit=capital,
                time_limit_days=body.get("timeLimitDays"),
            )
            created = service.create_mission(mission, principal.subject)
        except SystemPausedError as error:
            return self._respond(start_response, "503 Service Unavailable", {"error": str(error)})
        except (KeyError, TypeError, ValueError) as error:
            return self._respond(start_response, "400 Bad Request", {"error": str(error)})
        return self._respond(start_response, "201 Created", self._mission_to_json(created))

    def _call_domain(
        self,
        environ: dict[str, object],
        start_response: Callable,
        service_name: str,
        child_path: str,
        principal: OwnerPrincipal,
    ) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", "")).upper()
        if service_name == "report_collector" and not (
            method == "GET"
            and child_path in {"/report-collector/health", "/report-collector/system-health"}
        ):
            return self._respond(start_response, "404 Not Found", {"error": "not found"})
        child_environ = dict(environ)
        child_environ["PATH_INFO"] = child_path
        if service_name == "research_room":
            child_environ["HTTP_X_ACTOR_ID"] = principal.subject
        elif (
            method == "POST"
            and (service_name, child_path) in {
                ("orchestrator", "/orchestrator/decision"),
                ("money_calculator", "/money-calculator/assess"),
            }
        ):
            try:
                body = self._read_json(environ)
            except ValueError as error:
                return self._respond(start_response, "400 Bad Request", {"error": str(error)})
            body["owner"] = principal.subject
            encoded = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
            child_environ["wsgi.input"] = BytesIO(encoded)
            child_environ["CONTENT_LENGTH"] = str(len(encoded))
        captured: dict[str, object] = {}

        def capture(status: str, headers: list[tuple[str, str]], _exc_info=None) -> None:
            captured["status"] = status
            captured["headers"] = headers
            if _exc_info is not None:
                captured["exc_info"] = _exc_info

        body = self._apis[service_name](child_environ, capture)
        if "exc_info" in captured:
            start_response(captured["status"], captured["headers"], captured["exc_info"])
        else:
            start_response(captured["status"], captured["headers"])
        return body

    def _enactor(
        self,
        environ: dict[str, object],
        start_response: Callable,
        method: str,
        path: str,
        principal: OwnerPrincipal,
    ) -> list[bytes]:
        api = self._apis["sector3_enactor"]
        suffix = path.removeprefix("/api/enactor/")
        try:
            if method == "GET" and suffix == "health":
                response = api.get_health()
            elif method == "GET" and suffix.endswith("/trace"):
                execution_id = suffix.removeprefix("executions/").removesuffix("/trace")
                response = api.get_trace(execution_id)
            elif method == "POST" and suffix == "executions":
                response = api.post_executions(self._read_json(environ))
            elif method == "POST" and suffix.startswith("executions/") and suffix.endswith("/resume"):
                execution_id = suffix.removeprefix("executions/").removesuffix("/resume")
                response = api.post_executions_resume(execution_id, self._read_json(environ))
            elif method == "POST" and suffix.startswith("approvals/") and suffix.endswith("/decision"):
                if principal.approver_level is None:
                    return self._respond(start_response, "403 Forbidden", {"error": "Authenticated approver level is required."})
                approval_id = suffix.removeprefix("approvals/").removesuffix("/decision")
                body = self._read_json(environ)
                if not isinstance(body.get("approve"), bool):
                    return self._respond(start_response, "400 Bad Request", {"error": "approve must be a boolean."})
                response = api.post_approvals_decision(approval_id, {
                    "approve": body["approve"],
                    "decidedBy": principal.subject,
                    "approverLevel": principal.approver_level.value,
                })
            else:
                return self._respond(start_response, "404 Not Found", {"error": "not found"})
        except (TypeError, ValueError) as error:
            return self._respond(start_response, "400 Bad Request", {"error": str(error)})
        return self._respond(start_response, f"{response.status_code} {self._reason(response.status_code)}", response.body)

    @classmethod
    def _read_json(cls, environ: dict[str, object]) -> dict[str, object]:
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
        except (TypeError, ValueError) as error:
            raise ValueError("Content-Length must be a valid integer.") from error
        stream = environ.get("wsgi.input")
        if stream is None or length <= 0 or length > cls.MAX_REQUEST_BYTES:
            raise ValueError("Request body size is invalid.")
        try:
            value = json.loads(stream.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Request body must be valid JSON.") from error
        if not isinstance(value, dict):
            raise ValueError("Request body must be a JSON object.")
        return value

    @staticmethod
    def _mission_to_json(mission: ResearchMission) -> dict[str, object]:
        return {
            "missionId": mission.mission_id,
            "objective": mission.objective,
            "requestedBy": mission.requested_by,
            "markets": mission.markets,
            "businessModels": mission.business_models,
            "riskTolerance": mission.risk_tolerance,
            "requiredEvidenceLevel": mission.required_evidence_level,
            "capitalLimit": asdict(mission.capital_limit) if mission.capital_limit else None,
            "timeLimitDays": mission.time_limit_days,
            "status": mission.status.value,
            "createdAt": mission.created_at.isoformat(),
        }

    @classmethod
    def _respond(cls, start_response: Callable, status: str, payload: object) -> list[bytes]:
        content = json.dumps(payload, ensure_ascii=False, allow_nan=False, default=cls._json_default).encode("utf-8")
        start_response(status, [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(content))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
        ])
        return [content]

    @staticmethod
    def _json_default(value: object) -> str:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Enum):
            return value.value
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable.")

    @staticmethod
    def _reason(code: int) -> str:
        return {
            200: "OK",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            202: "Accepted",
            405: "Method Not Allowed",
            404: "Not Found",
            201: "Created",
            409: "Conflict",
            422: "Unprocessable Entity",
            503: "Service Unavailable",
        }.get(code, "Error")
