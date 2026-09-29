from __future__ import annotations

from reliability import ReliabilityRuntime, default_reliability_runtime

from .controller import ReportCollectorController, ReportCollectorReview
from .models import ComponentRecord, OperationalSnapshot


class ReportCollectorService:
    def __init__(
        self,
        controller: ReportCollectorController | None = None,
        *,
        reliability: ReliabilityRuntime | None = None,
    ) -> None:
        self.controller = controller or ReportCollectorController()
        self.reliability = reliability or default_reliability_runtime()

    def discover(self, components: tuple[ComponentRecord, ...] | list[ComponentRecord]) -> OperationalSnapshot:
        return self.controller.discover(components).snapshot

    def discover_from_directory(self, root: str) -> OperationalSnapshot:
        return self.controller.discover_from_directory(root).snapshot

    def collect_system_health(self) -> OperationalSnapshot:
        health = self.reliability.health_snapshot()
        if not health:
            raise ValueError("No sector heartbeats are registered; system health is unavailable.")
        records = []
        for item in health:
            if item.status.value == "healthy":
                status = "healthy"
            elif item.status.value in {"dead"}:
                status = "offline"
            elif item.status.value in {"stalled"}:
                status = "critical"
            else:
                status = "warning"
            records.append(ComponentRecord(
                name=item.service,
                category="sector-service",
                status=status,
                owner=item.service,
                details=item.reason,
            ))
        return self.controller.discover(tuple(records)).snapshot

    def history(self, snapshot_id: str) -> OperationalSnapshot | None:
        return self.controller.history(snapshot_id)

    def health(self) -> dict[str, object]:
        services = self.reliability.health_snapshot()
        ready = bool(services) and all(item.readiness.value == "ready" for item in services)
        return {
            "service": "report-collector",
            "status": "ok" if ready else "not_ready",
            "ready": ready,
            "system_paused": self.reliability.failsafe.paused,
            "registered_services": len(services),
        }


__all__ = ["ReportCollectorController", "ReportCollectorReview", "ReportCollectorService"]
