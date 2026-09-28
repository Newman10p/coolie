"""Metric Collector & Outcome Reporter (§5.8, §5.9): collects metrics, detects
anomalies, evaluates stop conditions, reports outcomes back into the Research Room."""
from __future__ import annotations

from typing import Any

from ..base import BaseEnactorAgent
from ...models.approval import ApprovalLevel
from ...models.outcome import AnomalyDetection, BusinessMetricSnapshot, OutcomeReport, OutcomeVerdict
from ...models.shared import AgentStatus, RiskSeverity, now_utc
from uuid import uuid4


class MetricCollectorAgent(BaseEnactorAgent):
    def run(self, task, state: dict[str, Any]):
        business_id = state["business_id"]; plan_hash = state["plan_hash"]
        request = state["request"]
        readings: dict[str, float] = dict(state["context"].get("metricReadings", {}))
        anomalies: list[AnomalyDetection] = []
        triggered: list[str] = []
        for condition in request.stop_conditions:
            observed = readings.get(condition.metric)
            if observed is None: continue
            snapshot = BusinessMetricSnapshot(metric_id=f"MTR-{uuid4().hex[:8]}", business_id=business_id,
                                              execution_id=task.execution_id, name=condition.metric,
                                              value=float(observed), unit="count", captured_at=now_utc())
            collect = self.call(task, business_id, plan_hash, "analytics.collect_business_metrics",
                                {"metricId": snapshot.metric_id, "name": snapshot.name, "value": snapshot.value})
            if collect.status == "success": state["store"].metrics.add(snapshot)
            if condition.evaluate(float(observed)):
                triggered.append(condition.condition_id)
                anomalies.append(AnomalyDetection(anomaly_id=f"ANM-{len(anomalies)+1}", execution_id=task.execution_id,
                                                  metric=condition.metric, observed=float(observed),
                                                  expected=float(condition.threshold), severity=RiskSeverity.HIGH,
                                                  suggested_action="Stop condition matched; controller must pause.",
                                                  stop_condition_id=condition.condition_id))
        detect = self.call(task, business_id, plan_hash, "analytics.detect_anomalies",
                           {"executionId": task.execution_id, "anomalies": len(anomalies)})
        verdict = OutcomeVerdict.PARTIAL if triggered else OutcomeVerdict.SUCCESS
        report = OutcomeReport(report_id=f"OUT-{uuid4().hex[:8]}", execution_id=task.execution_id,
                               business_id=business_id, opportunity_id=request.opportunity_id, verdict=verdict,
                               metrics_achieved=[{m: v} for m, v in readings.items()],
                               assumptions_wrong=tuple(triggered), lessons=("stop condition hit",) if triggered else ())
        file_result = self.call(task, business_id, plan_hash, "analytics.report_outcome",
                                {"reportId": report.report_id, "verdict": verdict.value})
        if file_result.status == "success": state["store"].outcomes.add(report)
        # Feeding the Research Room is an external action → A2 approval binding.
        exact = {"reportId": report.report_id}
        approval = self.request_approval(task, business_id, "research.submit_outcome", report.report_id, exact,
                                         ApprovalLevel.A2_LIGHTWEIGHT, reason="Feed outcome into research loop")
        if self.approval_ready(approval.approval_id):
            self.call(task, business_id, plan_hash, "research.submit_outcome", exact,
                      approval_id=approval.approval_id, idempotency_key=f"{task.task_id}:{report.report_id}")
        status = AgentStatus.SUCCESS if not triggered else AgentStatus.PARTIAL
        return status, f"Metrics collected; {len(triggered)} stop conditions triggered.", {
            "triggered_stop_conditions": triggered, "outcome_report_id": report.report_id}
