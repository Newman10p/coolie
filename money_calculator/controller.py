from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from research_room.models import Money

from .models import ActivationDecisionCode, ActivationProposal, SpendRecommendation


@dataclass(frozen=True)
class FinanceReview:
    proposal_id: str
    decision: SpendRecommendation
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MoneyCalculatorController:
    def __init__(self) -> None:
        self._history: dict[str, list[SpendRecommendation]] = {}

    def record(self, proposal: ActivationProposal, recommendation: SpendRecommendation) -> SpendRecommendation:
        self._history.setdefault(proposal.proposal_id, []).append(recommendation)
        return recommendation

    def history(self, proposal_id: str) -> tuple[SpendRecommendation, ...]:
        return tuple(self._history.get(proposal_id, []))

    def assess(
        self,
        proposal: ActivationProposal,
        *,
        budget_limit: Money | None = None,
    ) -> FinanceReview:
        spend = float(proposal.planned_spend.amount)
        revenue = float(proposal.expected_revenue.amount)
        roi = proposal.projected_roi
        margin = proposal.projected_margin
        payback_days = max(0, int(proposal.time_horizon_days))

        if proposal.confidence < 0.6:
            reason = "Confidence is below the minimum threshold for a real activation spend."
            recommendation = SpendRecommendation(
                recommendation_id=f"finance-{proposal.proposal_id}-pause",
                proposal_id=proposal.proposal_id,
                code=ActivationDecisionCode.PAUSE,
                summary="Pause the activation until more evidence is collected.",
                reason=reason,
                recommended_spend=proposal.planned_spend,
                expected_roi=roi,
                payback_days=payback_days,
            )
            return FinanceReview(proposal.proposal_id, self.record(proposal, recommendation))

        if revenue < spend:
            recommendation = SpendRecommendation(
                recommendation_id=f"finance-{proposal.proposal_id}-reject",
                proposal_id=proposal.proposal_id,
                code=ActivationDecisionCode.REJECT,
                summary="Reject the activation because it is not cash-positive.",
                reason="Expected revenue is below the planned spend.",
                recommended_spend=Money(0.0, proposal.planned_spend.currency),
                expected_roi=roi,
                payback_days=payback_days,
            )
            return FinanceReview(proposal.proposal_id, self.record(proposal, recommendation))

        if margin < proposal.required_margin_percent:
            recommendation = SpendRecommendation(
                recommendation_id=f"finance-{proposal.proposal_id}-hold",
                proposal_id=proposal.proposal_id,
                code=ActivationDecisionCode.HOLD,
                summary="Hold the activation until the margin target is met.",
                reason=f"Projected margin {margin:.2f}% is below the required {proposal.required_margin_percent:.2f}%.",
                recommended_spend=proposal.planned_spend,
                expected_roi=roi,
                payback_days=payback_days,
            )
            return FinanceReview(proposal.proposal_id, self.record(proposal, recommendation))

        if budget_limit is not None and proposal.planned_spend.amount > budget_limit.amount:
            capped = Money(min(float(budget_limit.amount), spend), proposal.planned_spend.currency)
            recommendation = SpendRecommendation(
                recommendation_id=f"finance-{proposal.proposal_id}-approval",
                proposal_id=proposal.proposal_id,
                code=ActivationDecisionCode.REQUEST_OWNER_APPROVAL,
                summary="Request owner approval for the spend cap.",
                reason="The requested activation exceeds the approved budget limit.",
                recommended_spend=capped,
                expected_roi=roi,
                payback_days=payback_days,
                approval_required=True,
            )
            return FinanceReview(proposal.proposal_id, self.record(proposal, recommendation))

        if proposal.approval_required:
            recommendation = SpendRecommendation(
                recommendation_id=f"finance-{proposal.proposal_id}-approve",
                proposal_id=proposal.proposal_id,
                code=ActivationDecisionCode.APPROVE,
                summary="Approve the activation with an approval-bound execution gate.",
                reason="The activation meets evidence and margin thresholds and requires explicit approval before launch.",
                recommended_spend=proposal.planned_spend,
                expected_roi=roi,
                payback_days=payback_days,
                approval_required=True,
            )
            return FinanceReview(proposal.proposal_id, self.record(proposal, recommendation))

        code = ActivationDecisionCode.SCALE if roi >= 100.0 else ActivationDecisionCode.APPROVE
        summary = "Approve the activation." if code == ActivationDecisionCode.APPROVE else "Scale the activation."
        recommendation = SpendRecommendation(
            recommendation_id=f"finance-{proposal.proposal_id}-{code.value}",
            proposal_id=proposal.proposal_id,
            code=code,
            summary=summary,
            reason=f"The investment yields a projected ROI of {roi:.2f}% with acceptable risk and margin.",
            recommended_spend=proposal.planned_spend,
            expected_roi=roi,
            payback_days=payback_days,
        )
        return FinanceReview(proposal.proposal_id, self.record(proposal, recommendation))
