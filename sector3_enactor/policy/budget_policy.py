"""Budget policy wrapper built on the runtime budget ledger."""
from __future__ import annotations

from dataclasses import dataclass

from ..runtime.budget import BudgetLedger, BudgetTracker


@dataclass
class BudgetPolicy:
    tracker: BudgetTracker

    def __init__(self, *, warning_threshold_percent: float = 80.0, tracker: BudgetTracker | None = None) -> None:
        self.tracker = tracker or BudgetTracker(warning_threshold_percent)

    def open_ledger(self, execution_id: str, budgets: dict) -> BudgetLedger:
        return self.tracker.open_ledger(execution_id, budgets)

    def ledger(self, execution_id: str) -> BudgetLedger:
        return self.tracker.ledger(execution_id)

    def check(self, execution_id: str, budget_type: str, cost: float, *, currency: str | None = None) -> tuple[bool, str]:
        return self.tracker.ledger(execution_id).check(budget_type, cost, currency=currency)

    def reserve(self, execution_id: str, budget_type: str, cost: float) -> None:
        self.tracker.ledger(execution_id).reserve(budget_type, cost)

    def commit(self, execution_id: str, budget_type: str, cost: float) -> None:
        self.tracker.ledger(execution_id).commit(budget_type, cost)

    def rollback(self, execution_id: str, budget_type: str, cost: float) -> None:
        self.tracker.ledger(execution_id).rollback(budget_type, cost)

    def over_budget(self, execution_id: str) -> bool:
        return self.tracker.exhausted(execution_id)


__all__ = ["BudgetPolicy", "BudgetLedger", "BudgetTracker"]
