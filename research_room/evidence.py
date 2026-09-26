from __future__ import annotations

from .models import Evidence

_FRESHNESS = {"current": 1.0, "aging": 0.7, "stale": 0.3, "unknown": 0.5}
_DIRECTNESS = {"observed": 1.0, "calculated": 0.8, "inferred": 0.55}


def calculate_confidence(evidence: Evidence, source_quality: float, independence: float, *, weights: dict[str, float] | None = None) -> float:
    """Transparent weighted indicator, not a statistical certainty."""
    weights = weights or {"source": 0.30, "independence": 0.25, "freshness": 0.20, "directness": 0.25}
    if set(weights) != {"source", "independence", "freshness", "directness"} or round(sum(weights.values()), 8) != 1:
        raise ValueError("Confidence weights must contain four factors and sum to 1.")
    values = {"source": source_quality, "independence": independence, "freshness": _FRESHNESS[evidence.freshness], "directness": _DIRECTNESS[evidence.evidence_type]}
    if any(not 0 <= value <= 1 for value in values.values()):
        raise ValueError("Confidence factors must be between 0 and 1.")
    return round(sum(weights[key] * value for key, value in values.items()), 4)


def important_claims_have_sources(evidence: list[Evidence]) -> bool:
    return bool(evidence) and all(item.source_reference.strip() and item.claim.strip() for item in evidence)
