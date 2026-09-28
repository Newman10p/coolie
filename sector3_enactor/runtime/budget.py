"""Budget tracking — document §5.9, §7 (budget_type), §8.4.

Four budget types: model_tokens, api_calls, ad_spend, purchases. The gateway asks
the tracker to reserve BEFORE the connector runs and commits/rolls back after.
Overspend attempts are denied and flagged so the controller can pause the run.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..models.shared import Money


@dataclass
class BudgetLedger:
    """Per-execution spend ledger with reserve → commit semantics."""
    limits: dict[str, float]                 # budget_type -> limit
    currencies: dict[str, str] = field(default_factory=dict)
    spent: dict[str, float] = field(default_factory=lambda: {"model_tokens": 0.0, "api_calls": 0.0,
                                                             "ad_spend": 0.0, "purchases": 0.0})
    reserved: dict[str, float] = field(default_factory=lambda: {"model_tokens": 0.0, "api_calls": 0.0,
                                                                "ad_spend": 0.0, "purchases": 0.0})
    warning_emitted: bool = False
    exhausted: bool = False

    @classmethod
    def from_config(cls, budgets: dict) -> "BudgetLedger":
        limits = {"model_tokens": float(budgets.get("model_tokens", 0)), "api_calls": float(budgets.get("api_calls", 0))}
        currencies: dict[str, str] = {}
        for key in ("ad_spend", "purchases"):
            value = budgets.get(key)
            if isinstance(value, Money):
                limits[key] = value.amount; currencies[key] = value.currency
            else:
                limits[key] = 0.0
        return cls(limits=limits, currencies=currencies)

    def utilization(self) -> float:
        worst = 0.0
        for kind, limit in self.limits.items():
            if limit > 0:
                worst = max(worst, (self.spent[kind] + self.reserved[kind]) / limit)
        return worst

    def check(self, budget_type: str, cost: float, *, currency: str | None = None) -> tuple[bool, str]:
        if budget_type == "none": return True, ""
        if budget_type not in self.limits: return False, f"Unknown budget type {budget_type}; failing closed."
        limit = self.limits[budget_type]
        if cost < 0: return False, "Negative cost reservations are rejected."
        projected = self.spent[budget_type] + self.reserved[budget_type] + cost
        if projected > limit:
            return False, f"Budget {budget_type} would be exceeded ({projected:g} > {limit:g}); attempt denied."
        declared = self.currencies.get(budget_type)
        if declared and currency and currency != declared:
            return False, f"Currency {currency} does not match budget currency {declared}."
        return True, ""

    def reserve(self, budget_type: str, cost: float) -> None:
        if budget_type != "none": self.reserved[budget_type] += cost

    def commit(self, budget_type: str, cost: float) -> None:
        if budget_type == "none": return
        self.reserved[budget_type] = max(0.0, self.reserved[budget_type] - cost)
        self.spent[budget_type] += cost

    def rollback(self, budget_type: str, cost: float) -> None:
        if budget_type != "none":
            self.reserved[budget_type] = max(0.0, self.reserved[budget_type] - cost)


class BudgetTracker:
    def __init__(self, warning_threshold_percent: float = 80.0) -> None:
        self._ledgers: dict[str, BudgetLedger] = {}
        self._warning_at = warning_threshold_percent / 100.0

    def open_ledger(self, execution_id: str, budgets: dict) -> BudgetLedger:
        if execution_id in self._ledgers: raise ValueError(f"Ledger already open for {execution_id}.")
        ledger = BudgetLedger.from_config(budgets)
        self._ledgers[execution_id] = ledger
        return ledger

    def ledger(self, execution_id: str) -> BudgetLedger:
        if execution_id not in self._ledgers: raise KeyError(execution_id)
        return self._ledgers[execution_id]

    def record(self, execution_id: str, budget_type: str, cost: float) -> None:
        """Direct accounting for non-gateway consumption; overspend raises."""
        ledger = self.ledger(execution_id)
        allowed, reason = ledger.check(budget_type, cost)
        if not allowed:
            ledger.exhausted = True
            raise PermissionError(reason)
        ledger.commit(budget_type, cost)

    def near_limit(self, execution_id: str) -> bool:
        return self.ledger(execution_id).utilization() >= self._warning_at

    def exhausted(self, execution_id: str) -> bool:
        ledger = self.ledger(execution_id)
        return ledger.exhausted or any(
            ledger.limits[k] > 0 and ledger.spent[k] >= ledger.limits[k] for k in ledger.limits)
