"""Quality Gate — document §5.7. A mandatory independent checkpoint between
production and release. The gate BLOCKS releases; it does not fix outputs."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GateFinding:
    category: str          # code | design | copy | claims | product_info | inventory | conversion_risk
    severity: str          # low | medium | high | critical
    detail: str
    blocking: bool


@dataclass
class GateEvaluation:
    execution_id: str
    findings: list[GateFinding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.blocking or f.severity in {"high", "critical"} for f in self.findings)

    def add(self, finding: GateFinding) -> None:
        self.findings.append(finding)


class QualityGate:
    CHECKLIST = ("code_quality", "design_quality", "copy_accuracy", "claims_evidence",
                 "product_information", "inventory_consistency", "conversion_risk")

    def evaluate(self, *, execution_id: str, artifact_contents: dict[str, str],
                 approved_claims: tuple[str, ...], evidence_index: dict[str, str],
                 product_facts: dict[str, str], inventory_consistent: bool,
                 code_review_blocking: bool = False, design_notes_missing: bool = False) -> GateEvaluation:
        evaluation = GateEvaluation(execution_id=execution_id)
        # Claims must be backed by evidence (§5.4/§5.7).
        for claim in approved_claims:
            reference = evidence_index.get(claim)
            if not reference:
                evaluation.add(GateFinding("claims", "critical", f"Claim has no evidence reference: {claim!r}", True))
        # Copy accuracy vs approved product facts.
        for key, body in artifact_contents.items():
            for fact_name, fact_value in product_facts.items():
                marker = "{{" + fact_name + "}}"
                if marker in body:
                    evaluation.add(GateFinding("copy", "high", f"{key}: unresolved placeholder {marker}", True))
            lowered = body.lower()
            for banned in ("guaranteed results", "cure", "risk-free money back"):
                if banned in lowered:
                    evaluation.add(GateFinding("copy", "critical", f"{key}: prohibited phrase '{banned}'", True))
        if code_review_blocking:
            evaluation.add(GateFinding("code", "high", "Code review reported blocking findings", True))
        if design_notes_missing:
            evaluation.add(GateFinding("design", "medium", "Design submission lacks rationale notes", False))
        if not inventory_consistent:
            evaluation.add(GateFinding("inventory", "critical", "Inventory levels inconsistent across channels", True))
        return evaluation
