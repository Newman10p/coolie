"""Safe capture, extraction, normalization, verification, and contradiction handling."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re

from .artifacts import ObjectStorage
from .evidence import calculate_confidence
from .models import Evidence
from .repositories import EvidenceRepository, SourceSnapshot, SourceSnapshotRepository


@dataclass(frozen=True)
class ExtractedFact:
    field: str
    value: str
    evidence_type: str


@dataclass(frozen=True)
class VerificationResult:
    evidence_id: str
    verified: bool
    confidence: float
    reasons: tuple[str, ...]


def sanitize_untrusted_content(content: str) -> tuple[str, tuple[str, ...]]:
    """Marks page text as data and removes common instruction-injection patterns."""
    patterns = (r"(?im)^\s*(ignore|disregard|override)\b.*$", r"(?im)^\s*(system|developer)\s*:\s*.*$", r"(?im)^\s*(call|use)\s+(a )?tool\b.*$")
    warnings: list[str] = []
    for pattern in patterns:
        content, count = re.subn(pattern, "[untrusted instruction removed]", content)
        if count: warnings.append("Potential prompt-injection text removed from source content.")
    return content, tuple(warnings)


class EvidencePipeline:
    def __init__(self, storage: ObjectStorage, snapshots: SourceSnapshotRepository, evidence: EvidenceRepository) -> None:
        self._storage = storage; self._snapshots = snapshots; self._evidence = evidence

    def capture(self, *, snapshot_id: str, mission_id: str, task_id: str, source_type: str, source_reference: str, content: str, source_quality: float) -> tuple[SourceSnapshot, tuple[str, ...]]:
        safe_content, warnings = sanitize_untrusted_content(content)
        key = f"sources/{mission_id}/{snapshot_id}.txt"
        artifact = self._storage.put_immutable(key, safe_content.encode("utf-8"), "text/plain")
        snapshot = SourceSnapshot(snapshot_id, mission_id, task_id, source_reference, datetime.now(timezone.utc), artifact.content_hash, artifact.key, source_quality)
        self._snapshots.create(snapshot)
        return snapshot, warnings

    def extract(self, content: str) -> tuple[ExtractedFact, ...]:
        safe_content, _ = sanitize_untrusted_content(content)
        facts: list[ExtractedFact] = []
        for amount, currency in re.findall(r"\b([\d][\d,]*(?:\.\d+)?)\s*(USD|UGX|EUR|GBP)\b", safe_content, re.I):
            facts.append(ExtractedFact("price", f"{amount.replace(',', '')} {currency.upper()}", "observed"))
        for days in re.findall(r"\b(\d+\s*[–-]\s*\d+\s+(?:business\s+)?days?)\b", safe_content, re.I): facts.append(ExtractedFact("delivery", days, "observed"))
        for count in re.findall(r"\b([\d,]+)\s+reviews?\b", safe_content, re.I): facts.append(ExtractedFact("review_count", count.replace(",", ""), "observed"))
        return tuple(facts)

    def register_claim(self, *, evidence_id: str, mission_id: str, source_type: str, source_reference: str, claim: str, evidence_type: str, source_quality: float, freshness: str = "current", limitations: tuple[str, ...] = ()) -> Evidence:
        seed = Evidence(evidence_id, source_type, source_reference, datetime.now(timezone.utc), claim, evidence_type, 0.0, freshness, limitations)
        confidence = calculate_confidence(seed, source_quality, 1.0)
        value = Evidence(evidence_id, source_type, source_reference, seed.retrieved_at, claim, evidence_type, confidence, freshness, limitations)
        return self._evidence.create_for_mission(mission_id, value)

    def verify(self, evidence: Evidence, *, source_quality: float, independent_sources: int) -> VerificationResult:
        independence = min(1.0, independent_sources / 2)
        confidence = calculate_confidence(evidence, source_quality, independence)
        reasons = [] if independent_sources else ["No independent corroborating source."]
        return VerificationResult(evidence.evidence_id, confidence >= .6 and not reasons, confidence, tuple(reasons))

    @staticmethod
    def contradictions(evidence: tuple[Evidence, ...]) -> tuple[tuple[str, str], ...]:
        """Find conflicting `field: value` claims without penalizing corroboration."""
        by_field: dict[str, dict[str, set[str]]] = {}
        for item in evidence:
            field, separator, value = item.claim.partition(":")
            if separator: by_field.setdefault(field.strip().casefold(), {}).setdefault(value.strip().casefold(), set()).add(item.source_reference)
        return tuple((field, "; ".join(f"{value} ({', '.join(sorted(sources))})" for value, sources in sorted(values.items()))) for field, values in by_field.items() if len(values) > 1)
