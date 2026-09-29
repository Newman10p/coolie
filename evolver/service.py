from __future__ import annotations

from .controller import EvolverController, EvolverReview
from .models import CapabilityExtensionPlan, ExpansionRequest


class EvolverService:
    def __init__(self, controller: EvolverController | None = None) -> None:
        self.controller = controller or EvolverController()

    def assess(self, request: ExpansionRequest, *, existing_capabilities: tuple[str, ...] = ()) -> CapabilityExtensionPlan:
        return self.controller.assess(request, existing_capabilities=existing_capabilities).plan

    def history(self, request_id: str) -> CapabilityExtensionPlan | None:
        return self.controller.history(request_id)

    @staticmethod
    def health() -> dict[str, str]:
        return {"status": "ok"}


__all__ = ["EvolverController", "EvolverReview", "EvolverService"]
