"""Customer-data-policy guardrails for message and order data."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CustomerDataPolicy:
    allowed_scopes: frozenset[str] = frozenset({"customer_read", "customer_write", "internal_read"})
    require_masking: bool = True
    sensitive_fields: frozenset[str] = frozenset({"ssn", "payment_card", "bank_account", "password", "token"})
    blocked_prefixes: tuple[str, ...] = ("debug-", "internal-", "secret-")
    allowlist: tuple[str, ...] = field(default_factory=tuple)

    def validate_scope(self, scope: str) -> None:
        if scope not in self.allowed_scopes:
            raise PermissionError(f"Unknown data scope {scope!r}; fail closed.")

    def scrub(self, payload: dict) -> dict:
        cleaned = {}
        for key, value in payload.items():
            clean_key = str(key).lower()
            if any(field in clean_key for field in self.sensitive_fields):
                cleaned[key] = "[REDACTED]"
            elif any(prefix in clean_key for prefix in self.blocked_prefixes):
                cleaned[key] = "[REDACTED]"
            else:
                cleaned[key] = value
        return cleaned


__all__ = ["CustomerDataPolicy"]
