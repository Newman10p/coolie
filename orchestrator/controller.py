from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .models import DecisionAudit, DecisionCode, EnactorMandate, OrchestratorDecision, OwnerObjective, ShariaStatus


@dataclass(frozen=True)
class ObjectiveReview:
    objective_id: str
    sharia_status: ShariaStatus
    evidence_confidence: float
    budget_approved: bool
    operational_risk: str
    decision: OrchestratorDecision
    mandate: EnactorMandate | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class OrchestratorController:
    def __init__(self) -> None:
        self._history: dict[str, list[OrchestratorDecision]] = {}

    def record(self, objective: OwnerObjective, decision: OrchestratorDecision) -> OrchestratorDecision:
        self._history.setdefault(objective.objective_id, []).append(decision)
        return decision

    def history(self, objective_id: str) -> tuple[OrchestratorDecision, ...]:
        return tuple(self._history.get(objective_id, []))

    def review_objective(
        self,
        objective: OwnerObjective,
        *,
        sharia_status: ShariaStatus,
        evidence_confidence: float,
        budget_approved: bool,
        operational_risk: str,
        approved_actions: tuple[str, ...] | None = None,
    ) -> ObjectiveReview:
        if sharia_status == ShariaStatus.NON_COMPLIANT:
            code = DecisionCode.REJECT
            summary = "Reject the objective because Sharia compliance failed."
            reason = "A non-compliant Sharia assessment blocks execution."
            decision = OrchestratorDecision(
                decision_id=f"decision-{objective.objective_id}-reject",
                objective_id=objective.objective_id,
                code=code,
                summary=summary,
                reason=reason,
            )
            return ObjectiveReview(objective.objective_id, sharia_status, evidence_confidence, budget_approved, operational_risk, self.record(objective, decision))

        if sharia_status == ShariaStatus.UNCERTAIN:
            code = DecisionCode.PAUSE
            summary = "Pause the objective pending clarifying review."
            reason = "The Sharia gate is uncertain; execution must stop until it is resolved."
            decision = OrchestratorDecision(
                decision_id=f"decision-{objective.objective_id}-pause",
                objective_id=objective.objective_id,
                code=code,
                summary=summary,
                reason=reason,
            )
            return ObjectiveReview(objective.objective_id, sharia_status, evidence_confidence, budget_approved, operational_risk, self.record(objective, decision))

        if not 0 <= float(evidence_confidence) <= 1:
            raise ValueError("evidence_confidence must be a number between 0 and 1.")
        if evidence_confidence < 0.7:
            code = DecisionCode.RESEARCH_MORE
            summary = "Request more research before proceeding."
            reason = "Evidence confidence is below the minimum threshold."
            decision = OrchestratorDecision(
                decision_id=f"decision-{objective.objective_id}-research",
                objective_id=objective.objective_id,
                code=code,
                summary=summary,
                reason=reason,
            )
            return ObjectiveReview(objective.objective_id, sharia_status, evidence_confidence, budget_approved, operational_risk, self.record(objective, decision))

        if objective.max_budget is not None and not budget_approved:
            code = DecisionCode.REQUEST_OWNER_APPROVAL
            summary = "Request owner approval for the budget."
            reason = "The objective exceeds the current approved budget authority."
            decision = OrchestratorDecision(
                decision_id=f"decision-{objective.objective_id}-approval",
                objective_id=objective.objective_id,
                code=code,
                summary=summary,
                reason=reason,
                requires_owner_approval=True,
            )
            return ObjectiveReview(objective.objective_id, sharia_status, evidence_confidence, budget_approved, operational_risk, self.record(objective, decision))

        if operational_risk.strip().lower() == "critical":
            code = DecisionCode.STOP
            summary = "Stop the objective because the operational risk is critical."
            reason = "Critical operational risk blocks launch."
            decision = OrchestratorDecision(
                decision_id=f"decision-{objective.objective_id}-stop",
                objective_id=objective.objective_id,
                code=code,
                summary=summary,
                reason=reason,
            )
            return ObjectiveReview(objective.objective_id, sharia_status, evidence_confidence, budget_approved, operational_risk, self.record(objective, decision))

        if operational_risk.strip().lower() in {"high", "medium"}:
            code = DecisionCode.RUN_CONTROLLED_TEST
            summary = "Run a controlled test before broad activation."
            reason = "A limited launch is safer than immediate execution."
            decision = OrchestratorDecision(
                decision_id=f"decision-{objective.objective_id}-test",
                objective_id=objective.objective_id,
                code=code,
                summary=summary,
                reason=reason,
            )
            return ObjectiveReview(objective.objective_id, sharia_status, evidence_confidence, budget_approved, operational_risk, self.record(objective, decision))

        code = DecisionCode.APPROVE_LIMITED_LAUNCH if objective.approval_required else DecisionCode.CONTINUE
        summary = "Proceed with the objective." if code == DecisionCode.CONTINUE else "Approve a limited launch."
        reason = "All required gates are satisfied and the objective is within policy bounds."
        decision = OrchestratorDecision(
            decision_id=f"decision-{objective.objective_id}-approve",
            objective_id=objective.objective_id,
            code=code,
            summary=summary,
            reason=reason,
            requires_owner_approval=objective.approval_required,
            budget_approved=budget_approved,
        )
        review = ObjectiveReview(objective.objective_id, sharia_status, evidence_confidence, budget_approved, operational_risk, self.record(objective, decision))

        mandate = None
        if code in {DecisionCode.APPROVE_LIMITED_LAUNCH, DecisionCode.CONTINUE, DecisionCode.RUN_CONTROLLED_TEST}:
            allowed = tuple(approved_actions or ("research", "monitor", "pause"))
            mandate = EnactorMandate(
                mandate_id=f"mandate-{objective.objective_id}",
                objective_id=objective.objective_id,
                action="execute" if code is not DecisionCode.RUN_CONTROLLED_TEST else "run_controlled_test",
                allowed_actions=allowed,
                constraints=(
                    "stay within approved budget",
                    "respect Sharia and policy gates",
                    "pause on unexpected risk",
                ),
                budget_cap=objective.max_budget,
                approval_reference="owner-approval" if objective.approval_required else None,
            )
        return ObjectiveReview(
            objective.objective_id,
            sharia_status,
            evidence_confidence,
            budget_approved,
            operational_risk,
            decision,
            mandate=mandate,
            timestamp=review.timestamp,
        )

    def audit(self, objective: OwnerObjective, decision: OrchestratorDecision, *, sharia_status: ShariaStatus, evidence_confidence: float, budget_approved: bool, operational_risk: str) -> DecisionAudit:
        return DecisionAudit(
            objective_id=objective.objective_id,
            decision_id=decision.decision_id,
            code=decision.code,
            sharia_status=sharia_status,
            evidence_confidence=evidence_confidence,
            budget_approved=budget_approved,
            operational_risk=operational_risk,
        )
