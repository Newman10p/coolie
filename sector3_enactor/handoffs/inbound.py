"""Inbound handoff (§6.1 Execution Requests): accept Orchestrator requests AND
Research Room proposals routed via the Orchestrator, validating against §4.1 fields."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models.execution import ExecutionRequest
from ..models.shared import Money, RiskSeverity, StopCondition, SuccessMetric


@dataclass(frozen=True)
class ValidationReport:
    valid: bool
    errors: tuple[str, ...]
    risk_flags: tuple[str, ...]


HIGH_RISK_KEYWORDS = {"refund", "payment", "medical", "legal", "supplement ingest", "irreversible"}


def validate_request(request: ExecutionRequest) -> ValidationReport:
    errors: list[str] = []
    flags: list[str] = list(request.risk_flags)
    if not request.objective.strip(): errors.append("objective is required.")
    if not request.success_metrics: errors.append("At least one success metric is required (§4.1).")
    if not request.stop_conditions: errors.append("At least one stop condition is required (§4.1).")
    lowered = request.objective.lower()
    if any(word in lowered for word in HIGH_RISK_KEYWORDS):
        flags.append("high_risk_domain")
    if request.budget and request.budget.amount > 0 and request.maximum_automatic_spend is None:
        flags.append("missing_automatic_spend_cap")
    return ValidationReport(valid=not errors, errors=tuple(errors), risk_flags=tuple(dict.fromkeys(flags)))


def execution_from_proposal(proposal: dict[str, Any]) -> ExecutionRequest:
    """Map a Research-Room-style proposal payload into an ExecutionRequest."""
    metrics = tuple(SuccessMetric(metric_id=m["id"], name=m["name"], target=float(m["target"]), unit=m["unit"])
                    for m in proposal.get("successMetrics", ()))
    stops = tuple(StopCondition(condition_id=s["id"], description=s["description"], metric=s["metric"],
                                operator=s["operator"], threshold=float(s["threshold"]))
                  for s in proposal.get("stopConditions", ()))
    budget = None
    if proposal.get("budget"): budget = Money(float(proposal["budget"]["amount"]), str(proposal["budget"]["currency"]))
    cap = None
    if proposal.get("maxAutoSpend"): cap = Money(float(proposal["maxAutoSpend"]["amount"]), str(proposal["maxAutoSpend"]["currency"]))
    return ExecutionRequest(execution_id=proposal["executionId"], business_id=proposal["businessId"],
                            plan_id=proposal.get("planId", f"PLAN-{proposal['executionId']}"),
                            objective=proposal["objective"], opportunity_id=proposal.get("opportunityId"),
                            strategy_id=proposal.get("strategyId"), requested_by=proposal.get("requestedBy", "orchestrator"),
                            constraints=tuple(proposal.get("constraints", ())), audience=proposal.get("audience"),
                            approved_claims=tuple(proposal.get("approvedClaims", ())),
                            required_assets=tuple(proposal.get("requiredAssets", ())),
                            success_metrics=metrics, stop_conditions=stops, budget=budget,
                            maximum_automatic_spend=cap, approval_requirements=tuple(proposal.get("approvalRequirements", ())),
                            risk_flags=tuple(proposal.get("riskFlags", ())))
