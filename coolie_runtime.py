from __future__ import annotations

from collections.abc import Mapping
from typing import Callable, Protocol

from reliability import (
    HealthStatus,
    ReliabilityApi,
    ReliabilityRuntime,
    ServiceHealth,
    default_reliability_runtime,
)


class ReliabilityAware(Protocol):
    reliability: ReliabilityRuntime


class CoolieSystem:
    """Composition root that binds all sectors to one fail-safe and health plane.

    Startup check results are required explicitly so object construction alone
    cannot make the system report ready.
    """

    SECTORS = (
        "brain",
        "research_room",
        "orchestrator",
        "money_calculator",
        "sector3_enactor",
        "evolver",
        "report_collector",
    )

    def __init__(
        self,
        services: Mapping[str, ReliabilityAware],
        *,
        startup_checks: Mapping[str, Mapping[str, bool]],
        instance_id: str,
        reliability: ReliabilityRuntime | None = None,
        dependency_checks: Mapping[str, Mapping[str, bool]] | None = None,
        authorize_operator: Callable[[dict[str, object]], str] | None = None,
    ) -> None:
        if not isinstance(instance_id, str) or not instance_id.strip():
            raise ValueError("instance_id must be a non-empty string.")
        missing = set(self.SECTORS) - set(services)
        extra = set(services) - set(self.SECTORS)
        if missing or extra:
            raise ValueError(
                f"Sector composition mismatch; missing={sorted(missing)}, unsupported={sorted(extra)}."
            )
        if set(startup_checks) != set(self.SECTORS):
            raise ValueError("Startup checks must be provided for every configured sector.")
        for sector in self.SECTORS:
            checks = startup_checks[sector]
            if (
                not isinstance(checks, Mapping)
                or not checks
                or any(not isinstance(name, str) or not name.strip() for name in checks)
                or any(not isinstance(result, bool) for result in checks.values())
            ):
                raise ValueError(f"Startup checks for {sector} must contain boolean results.")

        self.reliability = reliability or default_reliability_runtime()
        existing = set(self.reliability.heartbeats.registered())
        if existing.intersection(self.SECTORS):
            raise ValueError("Reliability runtime already has one or more Coolie sector instances registered.")
        self.services = dict(services)
        enactor_gateway = getattr(self.services["sector3_enactor"], "gateway", None)
        if enactor_gateway is None:
            raise ValueError("The Enactor service must expose its ToolGateway.")
        dependency_checks = dependency_checks or {}
        if set(dependency_checks) - set(self.SECTORS):
            raise ValueError("Dependency checks contain an unknown sector.")
        for sector, dependencies in dependency_checks.items():
            if not isinstance(dependencies, Mapping) or any(
                not isinstance(name, str) or not name.strip() or not isinstance(healthy, bool)
                for name, healthy in dependencies.items()
            ):
                raise ValueError(f"Dependency checks for {sector} must map names to booleans.")
        for sector, service in self.services.items():
            service.reliability = self.reliability
        enactor_gateway.reliability = self.reliability

        self._instance_id = instance_id
        intervals = {
            "brain": 10,
            "research_room": 15,
            "orchestrator": 10,
            "money_calculator": 15,
            "sector3_enactor": 15,
            "evolver": 15,
            "report_collector": 15,
        }
        for sector in self.SECTORS:
            self.reliability.heartbeats.register(
                sector,
                sector_id=sector,
                instance_id=f"{instance_id}:{sector}",
                interval_seconds=intervals[sector],
                startup_checks=dict(startup_checks[sector]),
                dependencies=tuple((dependency_checks.get(sector) or {}).keys()),
            )
            for dependency, healthy in (dependency_checks.get(sector) or {}).items():
                if not isinstance(healthy, bool):
                    raise ValueError(f"Dependency health for {sector}/{dependency} must be boolean.")
                self.reliability.heartbeats.set_dependency(
                    sector,
                    dependency,
                    HealthStatus.HEALTHY if healthy else HealthStatus.DEGRADED,
                )
        self.api = ReliabilityApi(self.reliability, authorize_operator=authorize_operator)

    def heartbeat(
        self,
        sector: str,
        *,
        status: HealthStatus = HealthStatus.HEALTHY,
        current_task_id: str | None = None,
        progress: bool = False,
        queue_depth: int | None = None,
        active_tasks: int | None = None,
    ):
        if sector not in self.services:
            raise KeyError(f"Unknown Coolie sector: {sector}")
        return self.reliability.heartbeats.heartbeat(
            sector,
            instance_id=f"{self._instance_id}:{sector}",
            status=status,
            current_task_id=current_task_id,
            progress=progress,
            queue_depth=queue_depth,
            active_tasks=active_tasks,
        )

    def health(self, sector: str) -> ServiceHealth:
        if sector not in self.services:
            raise KeyError(f"Unknown Coolie sector: {sector}")
        return self.reliability.health(sector)
