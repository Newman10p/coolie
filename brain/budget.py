"""Per-agent, per-task cost and token reservations and usage accounting."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import secrets
from threading import RLock

from research_room.models import Money


class BudgetExceeded(PermissionError):
    pass


@dataclass(frozen=True)
class BudgetReservation:
    reservation_id: str
    agent_id: str
    task_id: str
    amount: Money
    tokens: int


class BudgetManager:
    def __init__(self) -> None:
        self._reservations: dict[str, BudgetReservation] = {}
        self._reserved: dict[tuple[str, str, str], Decimal] = {}
        self._spent: dict[tuple[str, str, str], Decimal] = {}
        self._token_reserved: dict[tuple[str, str], int] = {}
        self._token_spent: dict[tuple[str, str], int] = {}
        self._lock = RLock()

    def reserve(
        self,
        *,
        agent_id: str,
        task_id: str,
        amount: Money,
        limit: Money,
        tokens: int = 0,
        token_limit: int | None = None,
    ) -> BudgetReservation:
        if amount.currency != limit.currency:
            raise BudgetExceeded("Budget currency mismatch.")
        if amount.amount <= 0:
            raise BudgetExceeded("A positive cost reservation is required.")
        if isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0:
            raise ValueError("Token reservation must be a non-negative integer.")
        if token_limit is not None and (isinstance(token_limit, bool) or not isinstance(token_limit, int) or token_limit < 0):
            raise ValueError("token_limit must be a non-negative integer.")
        with self._lock:
            key = self._key(agent_id, task_id, amount.currency)
            reserve = Decimal(str(amount.amount))
            spent = self._spent.get(key, Decimal(0))
            pending = self._reserved.get(key, Decimal(0))
            if spent + pending + reserve > Decimal(str(limit.amount)):
                raise BudgetExceeded("Task budget is exhausted.")
            token_key = self._token_key(agent_id, task_id)
            token_pending = self._token_reserved.get(token_key, 0)
            token_spent = self._token_spent.get(token_key, 0)
            if token_limit is not None and token_spent + token_pending + tokens > token_limit:
                raise BudgetExceeded("Task token budget is exhausted.")
            reservation = BudgetReservation(secrets.token_urlsafe(18), agent_id, task_id, amount, tokens)
            self._reservations[reservation.reservation_id] = reservation
            self._reserved[key] = pending + reserve
            self._token_reserved[token_key] = token_pending + tokens
            return reservation

    def commit(
        self,
        reservation_id: str,
        actual_cost: Money,
        *,
        limit: Money,
        actual_tokens: int = 0,
        token_limit: int | None = None,
    ) -> None:
        if isinstance(actual_tokens, bool) or not isinstance(actual_tokens, int) or actual_tokens < 0:
            raise ValueError("Actual token usage must be a non-negative integer.")
        if token_limit is not None and (isinstance(token_limit, bool) or not isinstance(token_limit, int) or token_limit < 0):
            raise ValueError("token_limit must be a non-negative integer.")
        with self._lock:
            reservation = self._pop(reservation_id)
            key = self._key(reservation.agent_id, reservation.task_id, reservation.amount.currency)
            pending = self._reserved.get(key, Decimal(0)) - Decimal(str(reservation.amount.amount))
            self._reserved[key] = max(Decimal(0), pending)
            token_key = self._token_key(reservation.agent_id, reservation.task_id)
            token_pending = self._token_reserved.get(token_key, 0) - reservation.tokens
            self._token_reserved[token_key] = max(0, token_pending)
            if actual_cost.currency != reservation.amount.currency:
                raise BudgetExceeded("Provider usage currency does not match its reservation.")
            spent = self._spent.get(key, Decimal(0)) + Decimal(str(actual_cost.amount))
            self._spent[key] = spent
            tokens_spent = self._token_spent.get(token_key, 0) + actual_tokens
            self._token_spent[token_key] = tokens_spent
            if (
                actual_cost.amount > reservation.amount.amount
                or spent > Decimal(str(limit.amount))
                or actual_tokens > reservation.tokens
                or (token_limit is not None and tokens_spent > token_limit)
            ):
                raise BudgetExceeded("Provider usage exceeded the task cost or token budget.")

    def release(self, reservation_id: str) -> None:
        with self._lock:
            reservation = self._pop(reservation_id)
            self._release(reservation)

    def release_if_active(self, reservation_id: str) -> None:
        with self._lock:
            reservation = self._reservations.pop(reservation_id, None)
            if reservation is not None:
                self._release(reservation)

    def _release(self, reservation: BudgetReservation) -> None:
        key = self._key(reservation.agent_id, reservation.task_id, reservation.amount.currency)
        pending = self._reserved.get(key, Decimal(0)) - Decimal(str(reservation.amount.amount))
        self._reserved[key] = max(Decimal(0), pending)
        token_key = self._token_key(reservation.agent_id, reservation.task_id)
        self._token_reserved[token_key] = max(0, self._token_reserved.get(token_key, 0) - reservation.tokens)

    def _pop(self, reservation_id: str) -> BudgetReservation:
        try:
            return self._reservations.pop(reservation_id)
        except KeyError as error:
            raise KeyError(f"Unknown budget reservation: {reservation_id}") from error

    @staticmethod
    def _key(agent_id: str, task_id: str, currency: str) -> tuple[str, str, str]:
        return agent_id, task_id, currency

    @staticmethod
    def _token_key(agent_id: str, task_id: str) -> tuple[str, str]:
        return agent_id, task_id
