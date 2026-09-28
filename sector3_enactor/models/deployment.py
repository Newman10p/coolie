"""Deployment & code-review models — document §5.3, §8.3."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .shared import now_utc, _non_empty


class Environment(str, Enum):
    SANDBOX = "sandbox"; STAGING = "staging"; PRODUCTION = "production"


class DeploymentStatus(str, Enum):
    PENDING = "pending"; SUCCEEDED = "succeeded"; FAILED = "failed"; ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class DeploymentRecord:
    deployment_id: str
    business_id: str
    execution_id: str
    environment: Environment
    artifact_key: str
    content_hash: str
    status: DeploymentStatus
    predecessor_deployment_id: str | None = None
    approval_id: str | None = None
    created_at: datetime = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        for name in ("deployment_id", "business_id", "execution_id", "artifact_key", "content_hash"):
            _non_empty(getattr(self, name), name)
        if not isinstance(self.environment, Environment): raise ValueError("environment must be an Environment.")
        if self.environment is Environment.PRODUCTION and not self.approval_id:
            raise ValueError("Production deployments require a bound approval_id.")
        if self.created_at.tzinfo is None: raise ValueError("created_at must be timezone-aware.")


@dataclass(frozen=True)
class CodeReviewReport:
    report_id: str
    task_id: str
    findings: tuple[dict[str, str], ...]     # {category, severity, detail}
    blocking: bool
    summary: str

    def __post_init__(self) -> None:
        _non_empty(self.report_id, "report_id"); _non_empty(self.summary, "summary")
        for finding in self.findings:
            if not {"category", "severity", "detail"} <= set(finding): raise ValueError("Findings need category/severity/detail.")
            if finding["severity"] not in {"low", "medium", "high", "critical"}: raise ValueError("Finding severity is invalid.")


class SandboxCommandResult(str, Enum):
    ALLOWED = "allowed"; DENIED = "denied"


@dataclass(frozen=True)
class SandboxPolicy:
    """Programmatic enforcement per §8.3: allowlists, not advisory prose."""
    allowed_commands: frozenset[str]
    allowed_network_hosts: frozenset[str]
    forbidden_paths: frozenset[str]
    ephemeral: bool = True

    def __post_init__(self) -> None:
        if not self.allowed_commands: raise ValueError("Sandbox policy requires a command allowlist.")
        if not self.ephemeral: raise ValueError("Enactor sandboxes must be ephemeral.")
        for path in self.forbidden_paths:
            if not path.startswith("/"): raise ValueError("Forbidden paths must be absolute.")
