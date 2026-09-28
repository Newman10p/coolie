"""Outbound handoff (§10 step 11): completion → Orchestrator; outcome → Research Room."""
from __future__ import annotations

from typing import Any

from ..models.execution import ExecutionResult
from ..models.outcome import OutcomeReport


def completion_payload(result: ExecutionResult) -> dict[str, Any]:
    return {
        "type": "enactor.execution.completed",
        "executionId": result.execution_id,
        "status": result.status.value,
        "summary": result.summary,
        "artifacts": [{"key": a.artifact_key, "hash": a.content_hash} for a in result.artifacts],
        "escalations": [{"id": e.escalation_id, "routedTo": e.routed_to, "severity": e.severity.value,
                         "reason": e.reason} for e in result.escalations],
        "completedAt": result.completed_at.isoformat() if result.completed_at else None,
    }


def outcome_payload(report: OutcomeReport) -> dict[str, Any]:
    return {
        "type": "enactor.outcome.reported",
        "reportId": report.report_id,
        "executionId": report.execution_id,
        "opportunityId": report.opportunity_id,
        "verdict": report.verdict.value,
        "assumptionsWrong": list(report.assumptions_wrong),
        "lessons": list(report.lessons),
        "invalidationObserved": list(report.invalidation_conditions_observed),
    }
