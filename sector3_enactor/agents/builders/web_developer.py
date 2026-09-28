"""Web Developer (§5.3, §8.3): branch → sandboxed build → PR → staging deploy with
approval → production ONLY via a request that a human fulfils."""
from __future__ import annotations

from typing import Any

from ..base import BaseEnactorAgent
from ...models.approval import ApprovalLevel
from ...models.deployment import DeploymentRecord, DeploymentStatus, Environment
from ...models.shared import AgentStatus


class WebDeveloperAgent(BaseEnactorAgent):
    def run(self, task, state: dict[str, Any]):
        business_id = state["business_id"]; plan_hash = state["plan_hash"]
        branch = f"enactor/{task.execution_id}"
        steps = [
            ("repo.create_branch", {"branch": branch, "base": "main"}),
            ("sandbox.run_command", {"command": "npm run build", "branch": branch}),
            ("repo.commit_patch", {"branch": branch, "files": ["landing.html"]}),
        ]
        for tool, arguments in steps:
            result = self.call(task, business_id, plan_hash, tool, arguments)
            if result.status != "success":
                return AgentStatus.BLOCKED if result.status == "denied" else AgentStatus.FAILED, \
                       f"{tool} refused: {result.error}", {}
        pr = self.call(task, business_id, plan_hash, "repo.open_pull_request", {"branch": branch, "title": task.objective})
        if pr.status != "success": return AgentStatus.BLOCKED, f"PR denied: {pr.error}", {}
        artifact = self.store_artifact(f"builds/{branch}/landing.html", "<html>landing</html>")
        # Staging deploy requires an A3 approval bound to the exact artifact.
        exact = {"environment": "staging", "artifactKey": artifact.artifact_key, "contentHash": artifact.content_hash}
        approval = self.request_approval(task, business_id, "hosting.deploy_staging", "staging", exact,
                                         ApprovalLevel.A3_STANDARD, reason="Deploy built landing page to staging")
        if not self.approval_ready(approval.approval_id):
            return AgentStatus.AWAITING_APPROVAL, f"PR open; awaiting staging approval {approval.approval_id}.", {
                "approval_id": approval.approval_id, "pull_request": pr.output.get("externalOperationId")}
        deploy = self.call(task, business_id, plan_hash, "hosting.deploy_staging",
                           dict(exact), approval_id=approval.approval_id, idempotency_key=f"{task.task_id}:staging")
        if deploy.status != "success": return AgentStatus.BLOCKED, f"Staging deploy denied: {deploy.error}", {}
        state["store"].deployments.add(DeploymentRecord(deployment_id=deploy.external_operation_id or f"DEP-{task.task_id}",
                                                        business_id=business_id, execution_id=task.execution_id,
                                                        environment=Environment.STAGING, artifact_key=artifact.artifact_key,
                                                        content_hash=artifact.content_hash, status=DeploymentStatus.SUCCEEDED,
                                                        approval_id=approval.approval_id))
        # Production is a REQUEST only — the agent can never execute it (§5.3B).
        prod = self.call(task, business_id, plan_hash, "hosting.request_production_deploy",
                         {"artifactKey": artifact.artifact_key, "reason": "staging verified"},
                         idempotency_key=f"{task.task_id}:prodreq")
        return AgentStatus.PARTIAL, "Staging deployed; production deployment requested (human required).", {
            "production_requested": prod.status == "success", "artifact_key": artifact.artifact_key}
