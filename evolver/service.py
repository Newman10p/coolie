from __future__ import annotations

from reliability import ReliabilityRuntime, default_reliability_runtime

from .controller import EvolverController, EvolverReview
from .models import CapabilityExtensionPlan, ExpansionRequest


class EvolverService:
    def __init__(
        self,
        controller: EvolverController | None = None,
        *,
        reliability: ReliabilityRuntime | None = None,
    ) -> None:
        self.controller = controller or EvolverController()
        self.reliability = reliability or default_reliability_runtime()

    def assess(self, request: ExpansionRequest, *, existing_capabilities: tuple[str, ...] = ()) -> CapabilityExtensionPlan:
        self.reliability.ensure_work_allowed("capability expansion assessment")
        return self.controller.assess(request, existing_capabilities=existing_capabilities).plan

    def history(self, request_id: str) -> CapabilityExtensionPlan | None:
        return self.controller.history(request_id)

    def health(self) -> dict[str, object]:
        paused = self.reliability.failsafe.paused
        return {
            "service": "evolver",
            "status": "paused" if paused else "ok",
            "ready": not paused,
            "reason": self.reliability.failsafe.reason,
        }


__all__ = ["EvolverController", "EvolverReview", "EvolverService"]
