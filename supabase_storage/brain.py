"""Durable Brain memory, event, audit, usage, and budget adapters."""

from __future__ import annotations

from decimal import Decimal
import secrets
from uuid import UUID

from brain.budget import BudgetExceeded, BudgetReservation
from research_room.models import Money

from .database import SupabasePostgres


class PostgresBudgetManager:
    """Transactional cost/token reservation manager shared across worker instances."""

    def __init__(self, database: SupabasePostgres, workspace_id: UUID) -> None:
        self.database = database
        self.workspace_id = UUID(str(workspace_id))

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
        if token_limit is not None and (
            isinstance(token_limit, bool)
            or not isinstance(token_limit, int)
            or token_limit < 0
        ):
            raise ValueError("token_limit must be a non-negative integer.")
        reservation = BudgetReservation(
            secrets.token_urlsafe(18), agent_id, task_id, amount, tokens
        )
        with self.database.connection() as connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (
                    f"{self.workspace_id}:{agent_id}:{task_id}:{amount.currency}",
                ),
            )
            connection.execute(
                """
                INSERT INTO public.brain_budget_state
                    (workspace_id, agent_id, task_id, currency)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (self.workspace_id, agent_id, task_id, amount.currency),
            )
            row = connection.execute(
                """
                SELECT reserved, spent, tokens_reserved, tokens_spent
                FROM public.brain_budget_state
                WHERE workspace_id = %s AND agent_id = %s
                  AND task_id = %s AND currency = %s
                FOR UPDATE
                """,
                (self.workspace_id, agent_id, task_id, amount.currency),
            ).fetchone()
            reserved, spent, token_reserved, token_spent = row
            if Decimal(spent) + Decimal(reserved) + Decimal(str(amount.amount)) > Decimal(str(limit.amount)):
                raise BudgetExceeded("Task budget is exhausted.")
            if (
                token_limit is not None
                and int(token_spent) + int(token_reserved) + tokens > token_limit
            ):
                raise BudgetExceeded("Task token budget is exhausted.")
            connection.execute(
                """
                INSERT INTO public.brain_budget_reservations
                    (workspace_id, reservation_id, agent_id, task_id,
                     currency, amount, tokens)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    self.workspace_id,
                    reservation.reservation_id,
                    agent_id,
                    task_id,
                    amount.currency,
                    amount.amount,
                    tokens,
                ),
            )
            connection.execute(
                """
                UPDATE public.brain_budget_state
                SET reserved = reserved + %s, tokens_reserved = tokens_reserved + %s
                WHERE workspace_id = %s AND agent_id = %s
                  AND task_id = %s AND currency = %s
                """,
                (
                    amount.amount,
                    tokens,
                    self.workspace_id,
                    agent_id,
                    task_id,
                    amount.currency,
                ),
            )
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
        if token_limit is not None and (
            isinstance(token_limit, bool)
            or not isinstance(token_limit, int)
            or token_limit < 0
        ):
            raise ValueError("token_limit must be a non-negative integer.")
        exceeded = False
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT agent_id, task_id, currency, amount, tokens
                FROM public.brain_budget_reservations
                WHERE workspace_id = %s AND reservation_id = %s
                FOR UPDATE
                """,
                (self.workspace_id, reservation_id),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown budget reservation: {reservation_id}")
            agent_id, task_id, currency, reserved_amount, reserved_tokens = row
            if actual_cost.currency != currency or actual_cost.currency != limit.currency:
                raise BudgetExceeded("Provider usage currency does not match its reservation.")
            state = connection.execute(
                """
                SELECT reserved, spent, tokens_reserved, tokens_spent
                FROM public.brain_budget_state
                WHERE workspace_id = %s AND agent_id = %s
                  AND task_id = %s AND currency = %s
                FOR UPDATE
                """,
                (self.workspace_id, agent_id, task_id, currency),
            ).fetchone()
            _, spent, _, token_spent = state
            new_spent = Decimal(spent) + Decimal(str(actual_cost.amount))
            new_tokens_spent = int(token_spent) + actual_tokens
            exceeded = (
                actual_cost.amount > float(reserved_amount)
                or new_spent > Decimal(str(limit.amount))
                or actual_tokens > int(reserved_tokens)
                or (
                    token_limit is not None
                    and new_tokens_spent > token_limit
                )
            )
            connection.execute(
                """
                UPDATE public.brain_budget_state
                SET reserved = GREATEST(0, reserved - %s),
                    spent = spent + %s,
                    tokens_reserved = GREATEST(0, tokens_reserved - %s),
                    tokens_spent = tokens_spent + %s
                WHERE workspace_id = %s AND agent_id = %s
                  AND task_id = %s AND currency = %s
                """,
                (
                    reserved_amount,
                    actual_cost.amount,
                    reserved_tokens,
                    actual_tokens,
                    self.workspace_id,
                    agent_id,
                    task_id,
                    currency,
                ),
            )
            connection.execute(
                """
                DELETE FROM public.brain_budget_reservations
                WHERE workspace_id = %s AND reservation_id = %s
                """,
                (self.workspace_id, reservation_id),
            )
        if exceeded:
            raise BudgetExceeded("Provider usage exceeded the task cost or token budget.")

    def release(self, reservation_id: str) -> None:
        self._release(reservation_id, required=True)

    def release_if_active(self, reservation_id: str) -> None:
        self._release(reservation_id, required=False)

    def _release(self, reservation_id: str, *, required: bool) -> None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT agent_id, task_id, currency, amount, tokens
                FROM public.brain_budget_reservations
                WHERE workspace_id = %s AND reservation_id = %s
                FOR UPDATE
                """,
                (self.workspace_id, reservation_id),
            ).fetchone()
            if row is None:
                if required:
                    raise KeyError(f"Unknown budget reservation: {reservation_id}")
                return
            agent_id, task_id, currency, amount, tokens = row
            connection.execute(
                """
                UPDATE public.brain_budget_state
                SET reserved = GREATEST(0, reserved - %s),
                    tokens_reserved = GREATEST(0, tokens_reserved - %s)
                WHERE workspace_id = %s AND agent_id = %s
                  AND task_id = %s AND currency = %s
                """,
                (
                    amount,
                    tokens,
                    self.workspace_id,
                    agent_id,
                    task_id,
                    currency,
                ),
            )
            connection.execute(
                """
                DELETE FROM public.brain_budget_reservations
                WHERE workspace_id = %s AND reservation_id = %s
                """,
                (self.workspace_id, reservation_id),
            )
