"""Marketing policy checks for claims and campaign actions."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MarketingPolicy:
    require_evidence_for_claims: bool = True
    approved_claims: tuple[str, ...] = ()
    blocked_policies: tuple[str, ...] = ("misleading", "unsupported_price", "unsafe_health_claim")
    max_campaign_budget_change_percent: float = 25.0
    allow_policy_override: bool = False

    def validate_claim(self, claim: str, *, evidence: str | None = None) -> None:
        if self.require_evidence_for_claims and (not claim or not evidence):
            raise PermissionError("Marketing claims require evidence before publication.")
        lowered = claim.lower()
        if any(token in lowered for token in self.blocked_policies):
            raise PermissionError(f"Marketing claim '{claim}' violates approved policy.")

    def validate_budget_change(self, old_budget: float, new_budget: float) -> None:
        change = abs(new_budget - old_budget) / old_budget if old_budget else 0.0
        if change > self.max_campaign_budget_change_percent / 100.0 and not self.allow_policy_override:
            raise PermissionError("Campaign budget changes beyond the policy cap require stronger approval.")


__all__ = ["MarketingPolicy"]
