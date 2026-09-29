from __future__ import annotations

from .controller import ReportCollectorController, ReportCollectorReview
from .models import ComponentRecord, OperationalSnapshot


class ReportCollectorService:
    def __init__(self, controller: ReportCollectorController | None = None) -> None:
        self.controller = controller or ReportCollectorController()

    def discover(self, components: tuple[ComponentRecord, ...] | list[ComponentRecord]) -> OperationalSnapshot:
        return self.controller.discover(components).snapshot

    def discover_from_directory(self, root: str) -> OperationalSnapshot:
        return self.controller.discover_from_directory(root).snapshot

    def history(self, snapshot_id: str) -> OperationalSnapshot | None:
        return self.controller.history(snapshot_id)

    @staticmethod
    def health() -> dict[str, str]:
        return {"status": "ok"}


__all__ = ["ReportCollectorController", "ReportCollectorReview", "ReportCollectorService"]
