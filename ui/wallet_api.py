"""Owner-authenticated API for watch-only wallets and manual withdrawal requests."""

from __future__ import annotations

from collections.abc import Callable
from io import BytesIO
import json
from typing import Protocol
from uuid import UUID

from ui.owner_api import OwnerPrincipal
from supabase_storage.wallets import WalletAccount, WalletRegistry, WalletWithdrawalRequest


class _Authenticator(Protocol):
    def __call__(self, environ: dict[str, object]) -> OwnerPrincipal | None: ...


class WalletWorkspaceApi:
    MAX_REQUEST_BYTES = 65_536

    def __init__(
        self,
        registry: WalletRegistry,
        authenticate: _Authenticator,
    ) -> None:
        self._registry = registry
        self._authenticate = authenticate

    def __call__(self, environ: dict[str, object], start_response: Callable) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD", "")).upper()
        path = str(environ.get("PATH_INFO", ""))
        if path != "/api/wallets" and not path.startswith("/api/wallets/"):
            return self._respond(start_response, "404 Not Found", {"error": "not found"})
        if method not in {"GET", "HEAD", "POST", "PATCH", "DELETE"}:
            return self._respond(start_response, "405 Method Not Allowed", {"error": "method not allowed"})

        principal = self._authenticate(environ)
        if principal is None:
            return self._respond(start_response, "401 Unauthorized", {"error": "Owner authentication is required."})
        required = "treasury:manage" if method in {"POST", "PATCH", "DELETE"} else "workspace:read"
        if required not in principal.permissions:
            return self._respond(start_response, "403 Forbidden", {"error": f"Missing permission: {required}."})

        try:
            if method in {"GET", "HEAD"} and path == "/api/wallets":
                return self._respond(start_response, "200 OK", {
                    "dataMode": "live",
                    "custody": "watch_only",
                    "wallets": [self._wallet_json(wallet) for wallet in self._registry.list_accounts()],
                })
            if method in {"GET", "HEAD"} and path == "/api/wallets/withdrawals":
                return self._respond(start_response, "200 OK", {
                    "dataMode": "live",
                    "withdrawalRequests": [
                        self._withdrawal_json(item)
                        for item in self._registry.list_withdrawals()
                    ],
                })
            if method == "POST" and path == "/api/wallets":
                body = self._read_json(environ)
                if set(body) != {"purpose", "label", "network", "asset", "address"}:
                    raise ValueError(
                        "Wallet setup requires exactly purpose, label, network, asset, and public address."
                    )
                wallet = self._registry.register(
                    purpose=body["purpose"],
                    label=body["label"],
                    network=body["network"],
                    asset=body["asset"],
                    address=body["address"],
                    created_by=principal.subject,
                )
                return self._respond(start_response, "201 Created", self._wallet_json(wallet))
            if method == "POST" and path == "/api/wallets/withdrawals":
                body = self._read_json(environ)
                allowed = {"walletId", "destinationAddress", "amount", "memo"}
                required_fields = {"walletId", "destinationAddress", "amount"}
                if set(body) - allowed or not required_fields.issubset(body):
                    raise ValueError(
                        "Withdrawal request requires walletId, destinationAddress, and amount."
                    )
                if not isinstance(body["amount"], str):
                    raise ValueError("amount must be a decimal string.")
                if body.get("memo") is not None and not isinstance(body["memo"], str):
                    raise ValueError("memo must be a string.")
                request = self._registry.request_withdrawal(
                    wallet_id=body["walletId"],
                    destination_address=body["destinationAddress"],
                    amount=body["amount"],
                    memo=body.get("memo"),
                    requested_by=principal.subject,
                )
                return self._respond(
                    start_response,
                    "202 Accepted",
                    self._withdrawal_json(request),
                )

            wallet_id = path.removeprefix("/api/wallets/").strip("/")
            if wallet_id == "withdrawals":
                return self._respond(start_response, "405 Method Not Allowed", {"error": "method not allowed"})
            try:
                UUID(wallet_id)
            except (ValueError, AttributeError):
                return self._respond(start_response, "404 Not Found", {"error": "not found"})
            if method == "PATCH":
                changes = self._read_json(environ)
                if not changes or set(changes) - {"purpose", "label", "network", "asset", "address"}:
                    raise ValueError("Wallet update contains unsupported or missing fields.")
                wallet = self._registry.update(
                    wallet_id,
                    updated_by=principal.subject,
                    changes=changes,
                )
                return self._respond(start_response, "200 OK", self._wallet_json(wallet))
            if method == "DELETE":
                wallet = self._registry.deactivate(
                    wallet_id,
                    updated_by=principal.subject,
                )
                return self._respond(start_response, "200 OK", self._wallet_json(wallet))
            return self._respond(start_response, "404 Not Found", {"error": "not found"})
        except KeyError:
            return self._respond(start_response, "404 Not Found", {"error": "active wallet not found"})
        except ValueError as error:
            message = str(error)
            status = (
                "409 Conflict"
                if "already exists for this purpose" in message
                else "400 Bad Request"
            )
            return self._respond(start_response, status, {"error": message})

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
    def _wallet_json(wallet: WalletAccount) -> dict[str, object]:
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
    def _withdrawal_json(request: WalletWithdrawalRequest) -> dict[str, object]:
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

    @staticmethod
    def _respond(start_response: Callable, status: str, payload: object) -> list[bytes]:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode()
        start_response(status, [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
        ])
        return [body]


class WalletOnlyApplication:
    """Serve wallet APIs and the React UI without fabricating other live sectors."""

    def __init__(self, wallet_api: WalletWorkspaceApi, static_app: Callable) -> None:
        self._wallet_api = wallet_api
        self._static_app = static_app

    def __call__(self, environ: dict[str, object], start_response: Callable) -> list[bytes]:
        path = str(environ.get("PATH_INFO", ""))
        if path == "/api/wallets" or path.startswith("/api/wallets/"):
            return self._wallet_api(environ, start_response)
        if path.startswith("/api/"):
            return WalletWorkspaceApi._respond(
                start_response,
                "503 Service Unavailable",
                {"dataMode": "partial", "error": "Only the authenticated watch-only wallet API is mounted."},
            )
        return self._static_app(environ, start_response)
