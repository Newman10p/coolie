"""Content-safety guardrails for reviewable content."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContentSafetyPolicy:
    disallowed_terms: frozenset[str] = frozenset({"ignore policy", "ignore approval", "send refund now", "bypass"})
    required_review_terms: frozenset[str] = frozenset({"legal", "medical", "safety", "financial"})

    def validate(self, text: str) -> None:
        lowered = text.lower()
        if any(term in lowered for term in self.disallowed_terms):
            raise PermissionError("Content contains direct instruction to bypass policy.")
        if any(term in lowered for term in self.required_review_terms):
            raise ValueError("Content requires human review before external publication.")


__all__ = ["ContentSafetyPolicy"]
