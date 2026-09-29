"""Sector 3 — The Enactor. Deterministic multi-agent execution system."""
from .config.loader import SectorConfig, load_sector_config
from .controller.execution_controller import ExecutionController, RunOutcome
from .controller.enactor_controller import EnactorController
from .connectors.fake import build_fake_connectors, wire_gateway
from .tools.definitions import build_default_registry
from .policy.hashing import digest, canonical_json

__all__ = [
    "SectorConfig",
    "load_sector_config",
    "ExecutionController",
    "RunOutcome",
    "EnactorController",
    "build_fake_connectors",
    "wire_gateway",
    "build_default_registry",
    "digest",
    "canonical_json",
]
