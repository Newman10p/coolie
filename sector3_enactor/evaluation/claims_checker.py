"""Marketing-claims checker (§5.4): every public claim must reference approved
product info or research evidence before publication is allowed."""
from __future__ import annotations

import re

SUPERLATIVE = re.compile(r"\b(best|guaranteed|100%|number one|no.1)\b", re.IGNORECASE)


def check_claims(claims: tuple, approved_claims: tuple[str, ...]) -> tuple[list[str], int]:
    violations: list[str] = []
    supported = 0
    approved_texts = {text.lower() for text in approved_claims}
    for claim in claims:
        text = getattr(claim, "text", "")
        evidence = getattr(claim, "evidence_reference", None)
        if SUPERLATIVE.search(text) and not evidence:
            violations.append(f"Unsupported superlative: {text!r}")
        elif not evidence:
            violations.append(f"Claim without evidence reference: {text!r}")
        elif text.lower() not in approved_texts:
            violations.append(f"Claim not present in approved_claims: {text!r}")
        else:
            supported += 1
    return violations, supported
