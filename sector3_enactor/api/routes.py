"""Minimal HTTP-style surface over the controller (§14 Phase 6: FastAPI-compatible
shape without requiring a server process). Handlers are plain functions returning
JSON-serializable dicts; errors map to 4xx instead of stack traces."""
from __future__ import annotations

from typing import Any

from ..controller.execution_controller import ExecutionController
from ..handoffs.inbound import execution_from_proposal
from ..models.approval import ApprovalLevel
from ..policy.hashing import canonical_json


class ApiResponse:
    def __init__(self, status_code: int, body: dict[str, Any]) -> None:
        self.status_code = status_code
        self.body = body

    def json(self) -> str:
        return canonical_json(self.body)


class EnactorApi:
    def __init__(self, controller: ExecutionController) -> None:
        self.controller = controller

    def post_executions(self, payload: dict[str, Any]) -> ApiResponse:
        try:
            request = execution_from_proposal(payload)
        except (KeyError, ValueError, TypeError) as error:
            return ApiResponse(422, {"error": f"Invalid execution request: {error}"})
        tasks = payload.get("tasks")
        if not tasks:
            return ApiResponse(422, {"error": "Execution payload must include compiled tasks."})
        from ..models.task import ApprovalGate, EnactorTask
        from ..models.shared import ToolMode
        from ..models.approval import ApprovalLevel as _AL
        parsed = []
        for t in tasks:
            gate = None
            if t.get("approvalGate"):
                gate = ApprovalGate(gate_id=t["approvalGate"]["gateId"],
                                    required_level=_AL(t["approvalGate"]["level"]),
                                    description=t["approvalGate"].get("description", "plan gate"))
            parsed.append(EnactorTask(task_id=t["taskId"], execution_id=request.execution_id, agent_role=t["agentRole"],
                                      objective=t["objective"], tool=t.get("tool"), mode=ToolMode(t.get("mode", "read")),
                                      dependencies=tuple(t.get("dependencies", ())),
                                      allowed_tools=tuple(t.get("allowedTools", ())),
                                      arguments=dict(t.get("arguments", {})), approval_gate=gate))
        try:
            plan = self.controller.compile_plan(request, tuple(parsed))
        except ValueError as error:
            return ApiResponse(422, {"error": str(error)})
        outcome = self.controller.submit(request, plan, payload.get("context", {}))
        code = 202 if outcome.result.status.value in ("awaiting_approval",) else 200
        return ApiResponse(code, {"executionId": outcome.result.execution_id, "status": outcome.result.status.value,
                                  "planHash": plan.plan_hash,
                                  "summary": outcome.result.summary,
                                  "approvalsPending": [e.approval_request_id for e in outcome.result.escalations
                                                       if e.approval_request_id]})

    def post_executions_resume(self, execution_id: str, payload: dict[str, Any]) -> ApiResponse:
        """Resume an awaiting-approval execution after decisions land (§10 step 4)."""
        stored = self.controller.store.executions.maybe(execution_id)
        if stored is None:
            return ApiResponse(404, {"error": f"Unknown execution {execution_id}."})
        plan_hash = payload.get("planHash")
        plan = self.controller._plan_registry.get(plan_hash) if plan_hash else None
        if plan is None or plan.execution_id != execution_id:
            return ApiResponse(422, {"error": "planHash must reference the registered compiled plan."})
        self.controller.close_execution_circuit(execution_id)
        outcome = self.controller.resume(stored, plan, payload.get("context", {}))
        code = 202 if outcome.result.status.value in ("awaiting_approval",) else 200
        return ApiResponse(code, {"executionId": execution_id, "status": outcome.result.status.value,
                                  "summary": outcome.result.summary})

    def post_approvals_decision(self, approval_id: str, payload: dict[str, Any]) -> ApiResponse:
        approve = bool(payload.get("approve", False))
        decided_by = str(payload.get("decidedBy", ""))
        if not decided_by: return ApiResponse(422, {"error": "decidedBy is required."})
        try:
            level = ApprovalLevel(payload.get("approverLevel", "A4"))
        except ValueError:
            return ApiResponse(422, {"error": "Unknown approver level."})
        try:
            decision = self.controller.approve(approval_id, decided_by=decided_by, level=level) if approve \
                else self.controller.deny(approval_id, decided_by=decided_by, level=level)
        except KeyError:
            return ApiResponse(404, {"error": f"Unknown approval {approval_id}."})
        except (ValueError, PermissionError) as error:
            return ApiResponse(409, {"error": str(error)})
        return ApiResponse(200, {"approvalId": decision.approval_id, "status": decision.status.value})

    def get_trace(self, execution_id: str) -> ApiResponse:
        events = self.controller.audit.events_for_execution(execution_id)
        if not events: return ApiResponse(404, {"error": "No trace for execution."})
        return ApiResponse(200, {"executionId": execution_id, "chainValid": self.controller.audit.verify_chain(),
                                 "events": [{"sequence": e.sequence, "type": e.event_type, "tool": e.tool,
                                             "agent": e.agent_id, "approval": e.approval_id,
                                             "operation": e.external_operation_id, "hash": e.event_hash}
                                            for e in events]})
