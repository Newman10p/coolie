"""Explicit binding of the Coolie service graph to Supabase repositories."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from brain.runtime import BrainService
from evolver.service import EvolverService
from money_calculator.controller import MoneyCalculatorController
from money_calculator.service import MoneyCalculatorService
from orchestrator.controller import OrchestratorController
from orchestrator.service import OrchestratorService
from report_collector.controller import ReportCollectorController
from report_collector.service import ReportCollectorService
from reliability.runtime import ReliabilityRuntime
from research_room.reporting import ReportGenerator
from research_room.service import ResearchRoomService
from sector3_enactor.controller.execution_controller import ExecutionController

from .brain import PostgresBudgetManager
from .database import SupabasePostgres
from .domain import PostgresDomainPersistence, PostgresObjectStorage
from .enactor import (
    PostgresArtifactStore,
    PostgresAuditRepository,
    PostgresBudgetTracker,
    PostgresEnactorIdempotency,
    PostgresStorefront,
)
from .reliability import PostgresReliabilityRuntime
from .research import PostgresResearchRepositories
from .wallets import PostgresWalletRegistry


class SupabaseServiceComposition:
    """Bind already-configured services before calling ``CoolieSystem``.

    Provider, tool, connector, and model configuration remain explicit inputs to
    the caller. Secrets and external integrations are never created implicitly.
    """

    def __init__(
        self,
        services: Mapping[str, object],
        database: SupabasePostgres,
        workspace_id: UUID,
    ) -> None:
        from coolie_runtime import CoolieSystem

        if set(services) != set(CoolieSystem.SECTORS):
            raise ValueError(
                "Supabase composition requires exactly the seven Coolie services."
            )
        if not database.check():
            raise ConnectionError("Supabase Postgres health check failed.")

        self.workspace_id = UUID(str(workspace_id))
        self.database = database
        self.domain = PostgresDomainPersistence(database, self.workspace_id)
        self.wallets = PostgresWalletRegistry(database, self.workspace_id)
        self.reliability: ReliabilityRuntime = PostgresReliabilityRuntime(self.domain)
        self.services = dict(services)

        research = self._require("research_room", ResearchRoomService)
        research_repositories = PostgresResearchRepositories.connect(
            database, self.workspace_id
        )
        research.missions = research_repositories.missions
        research.tasks = research_repositories.tasks
        research.opportunities = research_repositories.opportunities
        research.controller = research_repositories.controller
        research.reports = ReportGenerator(
            PostgresObjectStorage(database, self.workspace_id),
            research_repositories.reports,
        )

        orchestrator = self._require("orchestrator", OrchestratorService)
        orchestrator.controller = OrchestratorController(self.domain)

        finance = self._require("money_calculator", MoneyCalculatorService)
        finance.controller = MoneyCalculatorController(self.domain)

        evolver = self._require("evolver", EvolverService)
        from evolver.controller import EvolverController

        evolver.controller = EvolverController(self.domain)

        reports = self._require("report_collector", ReportCollectorService)
        reports.controller = ReportCollectorController(self.domain)

        brain = self._require("brain", BrainService)
        brain.bind_persistence(
            self.domain,
            budgets=PostgresBudgetManager(database, self.workspace_id),
        )

        enactor = self._require("sector3_enactor", ExecutionController)
        enactor.bind_storage(
            store=PostgresStorefront(database, self.workspace_id),
            artifacts=PostgresArtifactStore(database, self.workspace_id),
            audit=PostgresAuditRepository(database, self.workspace_id),
            budgets=PostgresBudgetTracker(database, self.workspace_id),
            idempotency_store=PostgresEnactorIdempotency(
                database, self.workspace_id
            ),
        )

        for service in self.services.values():
            if not hasattr(service, "reliability"):
                raise TypeError("Every composed Coolie service must expose reliability.")
            service.reliability = self.reliability
        enactor.gateway.reliability = self.reliability

    def _require(self, name: str, expected_type):
        service = self.services[name]
        if not isinstance(service, expected_type):
            raise TypeError(
                f"Service {name!r} must be an instance of {expected_type.__name__}."
            )
        return service
