"""Watch-only crypto wallet registry for owner-managed treasury addresses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from typing import Literal, Protocol
from uuid import UUID, uuid4

from psycopg.errors import UniqueViolation
from psycopg.types.json import Jsonb

from .database import SupabasePostgres


WalletPurpose = Literal["profits", "spending"]


@dataclass(frozen=True)
class WalletAccount:
    wallet_id: str
    purpose: WalletPurpose
    label: str
    network: str
    asset: str
    address: str
    created_by: str
    created_at: datetime
    status: Literal["active", "inactive"] = "active"
    custody: Literal["watch_only"] = "watch_only"
    updated_by: str | None = None


@dataclass(frozen=True)
class WalletWithdrawalRequest:
    request_id: str
    wallet_id: str
    destination_address: str
    network: str
    asset: str
    amount: str
    memo: str | None
    requested_by: str
    requested_at: datetime
    status: Literal["pending_review"] = "pending_review"


class WalletRegistry(Protocol):
    def list_accounts(self) -> tuple[WalletAccount, ...]: ...

    def register(
        self,
        *,
        purpose: WalletPurpose,
        label: str,
        network: str,
        asset: str,
        address: str,
        created_by: str,
    ) -> WalletAccount: ...

    def update(
        self, wallet_id: str, *, updated_by: str, changes: dict[str, object]
    ) -> WalletAccount: ...

    def deactivate(self, wallet_id: str, *, updated_by: str) -> WalletAccount: ...

    def list_withdrawals(self) -> tuple[WalletWithdrawalRequest, ...]: ...

    def request_withdrawal(
        self,
        *,
        wallet_id: str,
        destination_address: str,
        amount: str,
        memo: str | None,
        requested_by: str,
    ) -> WalletWithdrawalRequest: ...


class PostgresWalletRegistry:
    """Manage wallet-address metadata, never private keys or transactions."""

    _PURPOSES = {"profits", "spending"}
    _NETWORK_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
    _ASSET_PATTERN = re.compile(r"^[A-Z0-9]{2,16}$")
    _ADDRESS_PATTERN = re.compile(r"^[A-Za-z0-9]{20,160}$")
    _AMOUNT_PATTERN = re.compile(r"^(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,18})?$")

    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self.database = database
        self.workspace_id = UUID(str(workspace_id))

    def list_accounts(self) -> tuple[WalletAccount, ...]:
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT wallet_id, purpose, label, network, asset, address,
                       created_by, created_at, status, updated_by
                FROM public.wallet_accounts
                WHERE workspace_id = %s
                ORDER BY created_at, wallet_id
                """,
                (self.workspace_id,),
            ).fetchall()
        return tuple(
            WalletAccount(
                wallet_id=str(row[0]),
                purpose=row[1],
                label=row[2],
                network=row[3],
                asset=row[4],
                address=row[5],
                created_by=str(row[6]),
                created_at=row[7],
                status=row[8],
                updated_by=str(row[9]) if row[9] is not None else None,
            )
            for row in rows
        )

    def register(
        self,
        *,
        purpose: WalletPurpose,
        label: str,
        network: str,
        asset: str,
        address: str,
        created_by: str,
    ) -> WalletAccount:
        normalized = self._validate_wallet_fields({
            "purpose": purpose,
            "label": label,
            "network": network,
            "asset": asset,
            "address": address,
        })
        try:
            creator_id = str(UUID(created_by))
        except (ValueError, TypeError) as error:
            raise ValueError("created_by must be an authenticated user UUID.") from error

        account = WalletAccount(
            wallet_id=str(uuid4()),
            purpose=normalized["purpose"],
            label=normalized["label"],
            network=normalized["network"],
            asset=normalized["asset"],
            address=normalized["address"],
            created_by=creator_id,
            created_at=datetime.now(timezone.utc),
        )
        try:
            with self.database.connection() as connection:
                connection.execute(
                    """
                    INSERT INTO public.wallet_accounts
                        (workspace_id, wallet_id, purpose, label, network, asset,
                         address, created_by, created_at, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
                    """,
                    (
                        self.workspace_id,
                        account.wallet_id,
                        account.purpose,
                        account.label,
                        account.network,
                        account.asset,
                        account.address,
                        creator_id,
                        account.created_at,
                    ),
                )
                self._record_event(
                    connection,
                    wallet_id=account.wallet_id,
                    actor_id=creator_id,
                    action="registered",
                    details={
                        "purpose": account.purpose,
                        "label": account.label,
                        "network": account.network,
                        "asset": account.asset,
                        "address": account.address,
                    },
                )
        except UniqueViolation as error:
            raise ValueError(
                "An active wallet already exists for this purpose, network, and asset."
            ) from error
        return account

    def update(
        self, wallet_id: str, *, updated_by: str, changes: dict[str, object]
    ) -> WalletAccount:
        allowed = {"purpose", "label", "network", "asset", "address"}
        if not changes or set(changes) - allowed:
            raise ValueError("Wallet update contains unsupported or missing fields.")
        try:
            wallet_uuid = UUID(wallet_id)
            actor_id = str(UUID(updated_by))
        except (ValueError, TypeError) as error:
            raise ValueError("wallet_id and updated_by must be valid UUIDs.") from error
        try:
            with self.database.connection() as connection:
                current = connection.execute(
                    """
                    SELECT purpose, label, network, asset, address
                    FROM public.wallet_accounts
                    WHERE workspace_id = %s AND wallet_id = %s AND status = 'active'
                    """,
                    (self.workspace_id, wallet_uuid),
                ).fetchone()
                if current is None:
                    raise KeyError(wallet_id)
                values = dict(zip(("purpose", "label", "network", "asset", "address"), current))
                values.update(changes)
                normalized = self._validate_wallet_fields(values)
                row = connection.execute(
                    """
                    UPDATE public.wallet_accounts
                    SET purpose = %s, label = %s, network = %s, asset = %s,
                        address = %s, updated_by = %s, updated_at = now()
                    WHERE workspace_id = %s AND wallet_id = %s AND status = 'active'
                    RETURNING wallet_id, purpose, label, network, asset, address,
                              created_by, created_at, status, updated_by
                    """,
                    (
                        normalized["purpose"],
                        normalized["label"],
                        normalized["network"],
                        normalized["asset"],
                        normalized["address"],
                        actor_id,
                        self.workspace_id,
                        wallet_uuid,
                    ),
                ).fetchone()
                if row is None:
                    raise KeyError(wallet_id)
                self._record_event(
                    connection,
                    wallet_id=str(wallet_uuid),
                    actor_id=actor_id,
                    action="updated",
                    details={
                        "before": dict(zip(("purpose", "label", "network", "asset", "address"), current)),
                        "after": normalized,
                    },
                )
        except UniqueViolation as error:
            raise ValueError(
                "An active wallet already exists for this purpose, network, and asset."
            ) from error
        if row is None:
            raise KeyError(wallet_id)
        return self._account_from_row(row)

    def deactivate(self, wallet_id: str, *, updated_by: str) -> WalletAccount:
        try:
            wallet_uuid = UUID(wallet_id)
        except (ValueError, TypeError) as error:
            raise ValueError("wallet_id must be a UUID.") from error
        try:
            actor_id = str(UUID(updated_by))
        except (ValueError, TypeError) as error:
            raise ValueError("updated_by must be an authenticated user UUID.") from error
        with self.database.connection() as connection:
            row = connection.execute(
                """
                UPDATE public.wallet_accounts
                SET status = 'inactive', updated_at = now(), updated_by = %s
                WHERE workspace_id = %s AND wallet_id = %s AND status = 'active'
                RETURNING wallet_id, purpose, label, network, asset, address,
                          created_by, created_at, status, updated_by
                """,
                (actor_id, self.workspace_id, wallet_uuid),
            ).fetchone()
            if row is not None:
                self._record_event(
                    connection,
                    wallet_id=str(wallet_uuid),
                    actor_id=actor_id,
                    action="deactivated",
                    details={"status": "inactive"},
                )
        if row is None:
            raise KeyError(wallet_id)
        return self._account_from_row(row)

    def list_withdrawals(self) -> tuple[WalletWithdrawalRequest, ...]:
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT request_id, wallet_id, destination_address, network,
                       asset, amount::text, memo, requested_by, requested_at, status
                FROM public.wallet_withdrawal_requests
                WHERE workspace_id = %s
                ORDER BY requested_at DESC, request_id
                """,
                (self.workspace_id,),
            ).fetchall()
        return tuple(
            WalletWithdrawalRequest(
                request_id=str(row[0]),
                wallet_id=str(row[1]),
                destination_address=row[2],
                network=row[3],
                asset=row[4],
                amount=row[5],
                memo=row[6],
                requested_by=str(row[7]),
                requested_at=row[8],
                status=row[9],
            )
            for row in rows
        )

    def request_withdrawal(
        self,
        *,
        wallet_id: str,
        destination_address: str,
        amount: str,
        memo: str | None,
        requested_by: str,
    ) -> WalletWithdrawalRequest:
        try:
            wallet_uuid = UUID(wallet_id)
            actor_id = str(UUID(requested_by))
        except (ValueError, TypeError) as error:
            raise ValueError("wallet_id and requested_by must be valid UUIDs.") from error
        self._validate_address(destination_address, "destination_address")
        if not isinstance(amount, str) or not self._AMOUNT_PATTERN.fullmatch(amount):
            raise ValueError("amount must be a positive decimal with up to 18 fractional digits.")
        try:
            decimal_amount = Decimal(amount)
        except InvalidOperation as error:
            raise ValueError("amount must be a valid decimal string.") from error
        if decimal_amount <= 0:
            raise ValueError("amount must be greater than zero.")
        if memo is not None:
            memo = self._text(memo, "memo", max_length=280)
        request_id = str(uuid4())
        with self.database.connection() as connection:
            row = connection.execute(
                """
                INSERT INTO public.wallet_withdrawal_requests
                    (workspace_id, request_id, wallet_id, destination_address,
                     network, asset, amount, memo, requested_by, status)
                SELECT %s, %s, wa.wallet_id, %s, wa.network, wa.asset, %s, %s, %s,
                       'pending_review'
                FROM public.wallet_accounts AS wa
                WHERE wa.workspace_id = %s AND wa.wallet_id = %s
                  AND wa.purpose = 'spending' AND wa.status = 'active'
                RETURNING request_id, wallet_id, destination_address, network,
                          asset, amount::text, memo, requested_by, requested_at, status
                """,
                (
                    self.workspace_id,
                    request_id,
                    destination_address,
                    amount,
                    memo,
                    actor_id,
                    self.workspace_id,
                    wallet_uuid,
                ),
            ).fetchone()
        if row is None:
            raise KeyError(wallet_id)
        return WalletWithdrawalRequest(
            request_id=str(row[0]),
            wallet_id=str(row[1]),
            destination_address=row[2],
            network=row[3],
            asset=row[4],
            amount=row[5],
            memo=row[6],
            requested_by=str(row[7]),
            requested_at=row[8],
            status=row[9],
        )

    @staticmethod
    def _text(value: str, field: str, *, max_length: int) -> str:
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value.strip()) > max_length
            or any(ord(character) < 32 for character in value)
        ):
            raise ValueError(f"{field} must contain 1 to {max_length} printable characters.")
        return value.strip()

    @classmethod
    def _validate_wallet_fields(cls, fields: dict[str, object]) -> dict[str, str]:
        purpose = fields["purpose"]
        label = cls._text(fields["label"], "label", max_length=80)
        network = fields["network"]
        asset = fields["asset"]
        address = fields["address"]
        if not isinstance(purpose, str) or purpose not in cls._PURPOSES:
            raise ValueError("purpose must be 'profits' or 'spending'.")
        if not isinstance(network, str) or not cls._NETWORK_PATTERN.fullmatch(network):
            raise ValueError("network must be a lowercase network identifier.")
        if not isinstance(asset, str) or not cls._ASSET_PATTERN.fullmatch(asset):
            raise ValueError("asset must be an uppercase ticker.")
        cls._validate_address(address, "address")
        return {
            "purpose": purpose,
            "label": label,
            "network": network,
            "asset": asset,
            "address": address,
        }

    @classmethod
    def _validate_address(cls, value: object, field: str) -> None:
        if not isinstance(value, str) or not cls._ADDRESS_PATTERN.fullmatch(value):
            raise ValueError(f"{field} must be a 20–160 character alphanumeric public address.")

    @staticmethod
    def _account_from_row(row: tuple[object, ...]) -> WalletAccount:
        return WalletAccount(
            wallet_id=str(row[0]),
            purpose=row[1],
            label=row[2],
            network=row[3],
            asset=row[4],
            address=row[5],
            created_by=str(row[6]),
            created_at=row[7],
            status=row[8],
            updated_by=str(row[9]) if row[9] is not None else None,
        )

    def _record_event(
        self,
        connection,
        *,
        wallet_id: str,
        actor_id: str,
        action: str,
        details: dict[str, object],
    ) -> None:
        connection.execute(
            """
            INSERT INTO public.wallet_account_events
                (workspace_id, wallet_id, action, actor_id, details)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                self.workspace_id,
                wallet_id,
                action,
                actor_id,
                Jsonb(details),
            ),
        )
