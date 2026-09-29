import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace
import unittest

from coolie_runtime import CoolieSystem
from evolver import EvolverService, ExpansionRequest
from evolver.api import EvolverApi
from money_calculator import ActivationProposal, MoneyCalculatorService
from money_calculator.api import MoneyCalculatorApi
from orchestrator import OrchestratorService, OwnerObjective, ShariaStatus
from reliability import (
    HealthStatus,
    ReadinessStatus,
    ReliabilityApi,
    ReliabilityRuntime,
    SystemPausedError,
    default_reliability_runtime,
)
from report_collector import ComponentRecord, ReportCollectorService
from report_collector.api import ReportCollectorApi
from research_room.models import Money
from sector3_enactor.config.loader import load_sector_config
from sector3_enactor.controller.execution_controller import ExecutionController
from sector3_enactor.models.execution import ExecutionRequest
from sector3_enactor.models.shared import ToolMode
from sector3_enactor.models.task import EnactorTask
from sector3_enactor.tools.definitions import build_default_registry


def call_wsgi(app, method, path, body=None, *, environ_overrides=None):
    payload = json.dumps(body or {}).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(payload)),
        "wsgi.input": BytesIO(payload),
    }
    environ.update(environ_overrides or {})
    statuses = []
    response = app(environ, lambda status, _: statuses.append(status))
    return statuses[0], json.loads(b"".join(response))


class ReliabilityRuntimeTests(unittest.TestCase):
    def test_coolie_system_composition_shares_gate_and_requires_startup_checks(self):
        runtime = ReliabilityRuntime()
        services = {
            sector: SimpleNamespace(reliability=ReliabilityRuntime())
            for sector in CoolieSystem.SECTORS
        }
        services["sector3_enactor"].gateway = SimpleNamespace(reliability=ReliabilityRuntime())
        system = CoolieSystem(
            services,
            startup_checks={sector: {"configuration": True} for sector in CoolieSystem.SECTORS},
            dependency_checks={"brain": {"model_provider": False}},
            instance_id="local-test",
            reliability=runtime,
        )
        self.assertTrue(all(service.reliability is runtime for service in services.values()))
        self.assertIs(services["sector3_enactor"].gateway.reliability, runtime)
        self.assertEqual(set(runtime.heartbeats.registered()), set(CoolieSystem.SECTORS))
        self.assertEqual(system.health("brain").readiness, ReadinessStatus.NOT_READY)
        for sector in CoolieSystem.SECTORS:
            system.heartbeat(sector, progress=True)
        self.assertEqual(system.health("report_collector").readiness, ReadinessStatus.READY)

    def test_global_pause_blocks_sector_work_but_reports_stay_available(self):
        runtime = ReliabilityRuntime()
        finance = MoneyCalculatorService(reliability=runtime)
        evolver = EvolverService(reliability=runtime)
        orchestrator = OrchestratorService(reliability=runtime)
        report_collector = ReportCollectorService(reliability=runtime)
        proposal = ActivationProposal(
            "ACT-1", "Run a controlled test", "owner",
            Money(100, "USD"), Money(150, "USD"), 30, 0.9,
        )
        expansion = ExpansionRequest(
            "EXP-1", "tutoring", "Add tutoring operations", ("scheduling",),
            expected_monthly_revenue=Money(10_000, "USD"),
        )
        objective = OwnerObjective("OBJ-1", "owner", "Launch", "Pilot")

        runtime.emergency_pause("operator stop", authority="owner-1")
        with self.assertRaises(SystemPausedError):
            finance.assess(proposal)
        with self.assertRaises(SystemPausedError):
            evolver.assess(expansion)
        with self.assertRaises(SystemPausedError):
            orchestrator.decide(
                objective,
                sharia_status=ShariaStatus.COMPLIANT,
                evidence_confidence=0.9,
                budget_approved=True,
                operational_risk="low",
            )
        self.assertEqual(
            report_collector.discover(
                (ComponentRecord("finance", "sector", "warning", "finance"),)
            ).alert_count,
            1,
        )
        runtime.resume(authority="owner-1")
        self.assertEqual(finance.assess(proposal).code.value, "approve")

    def test_shared_default_failsafe_is_wired_across_sector_services(self):
        self.assertIs(
            MoneyCalculatorService().reliability,
            EvolverService().reliability,
        )
        self.assertIs(
            MoneyCalculatorService().reliability,
            OrchestratorService().reliability,
        )
        self.assertIsNotNone(default_reliability_runtime())

    def test_health_readiness_fails_closed_on_dependency_and_stale_heartbeat(self):
        runtime = ReliabilityRuntime()
        now = datetime(2026, 9, 29, tzinfo=timezone.utc)
        runtime.heartbeats.register(
            "finance",
            sector_id="finance",
            instance_id="finance-1",
            interval_seconds=10,
            dependencies=("ledger",),
            startup_checks={"configuration": True},
            now=now,
        )
        healthy = runtime.health("finance", now=now + timedelta(seconds=5))
        self.assertEqual(healthy.readiness, ReadinessStatus.READY)

        runtime.heartbeats.set_dependency("finance", "ledger", HealthStatus.DEGRADED)
        dependency_down = runtime.health("finance", now=now + timedelta(seconds=5))
        self.assertEqual(dependency_down.readiness, ReadinessStatus.NOT_READY)
        self.assertEqual(dependency_down.status, HealthStatus.DEGRADED)

        runtime.heartbeats.set_dependency("finance", "ledger", HealthStatus.HEALTHY)
        stale = runtime.health("finance", now=now + timedelta(seconds=90))
        self.assertEqual(stale.status, HealthStatus.DEAD)
        self.assertEqual(stale.readiness, ReadinessStatus.NOT_READY)

    def test_health_api_separates_liveness_and_readiness_and_controls_pause(self):
        runtime = ReliabilityRuntime()
        api = ReliabilityApi(runtime, authorize_operator=lambda environ: "verified-owner")
        status, body = call_wsgi(api, "GET", "/health/live")
        self.assertEqual(status, "200 OK")
        self.assertTrue(body["live"])

        status, body = call_wsgi(api, "GET", "/health/ready")
        self.assertEqual(status, "503 Service Unavailable")
        self.assertFalse(body["ready"])

        runtime.heartbeats.register(
            "report-collector",
            sector_id="report_collector",
            instance_id="collector-1",
        )
        status, body = call_wsgi(api, "GET", "/health/ready")
        self.assertEqual(status, "200 OK")
        self.assertTrue(body["ready"])

        status, body = call_wsgi(
            api,
            "POST",
            "/system/emergency-pause",
            {"reason": "database integrity alert"},
        )
        self.assertEqual(status, "200 OK")
        self.assertTrue(body["paused"])
        status, body = call_wsgi(api, "GET", "/health/ready")
        self.assertEqual(status, "503 Service Unavailable")
        self.assertFalse(body["ready"])

        status, body = call_wsgi(api, "POST", "/system/resume", {})
        self.assertEqual(status, "200 OK")
        self.assertFalse(body["paused"])
        self.assertEqual(len(runtime.incidents()), 1)

    def test_report_collector_aggregates_registered_sector_health(self):
        runtime = ReliabilityRuntime()
        runtime.heartbeats.register(
            "brain",
            sector_id="brain",
            instance_id="brain-1",
            dependencies=("provider",),
        )
        runtime.heartbeats.register(
            "enactor",
            sector_id="sector3_enactor",
            instance_id="enactor-1",
        )
        runtime.heartbeats.set_dependency("brain", "provider", HealthStatus.DEGRADED)
        snapshot = ReportCollectorService(reliability=runtime).collect_system_health()
        components = {component.name: component for component in snapshot.components}
        self.assertEqual(components["brain"].status, "warning")
        self.assertEqual(components["enactor"].status, "healthy")
        self.assertEqual(snapshot.alert_count, 1)

    def test_unconfigured_operator_control_fails_closed_and_logs_redact_secrets(self):
        runtime = ReliabilityRuntime()
        api = ReliabilityApi(runtime)
        status, body = call_wsgi(
            api,
            "POST",
            "/system/emergency-pause",
            {"reason": "stop"},
        )
        self.assertEqual(status, "503 Service Unavailable")
        self.assertIn("not configured", body["error"])
        self.assertFalse(runtime.failsafe.paused)

        record = runtime.record(
            event_name="auth.failure",
            service="brain",
            sector="brain",
            severity="warning",
            message="Authentication failed.",
            data={"session_token": "secret-value", "attempt": 2},
        )
        self.assertEqual(record.data["session_token"], "******")
        self.assertEqual(record.data["attempt"], 2)

    def test_enactor_refuses_new_execution_while_shared_pause_is_active(self):
        runtime = ReliabilityRuntime()
        controller = ExecutionController(
            config=load_sector_config(),
            registry=build_default_registry(),
            reliability=runtime,
        )
        request = ExecutionRequest(
            execution_id="E-FAILSAFE",
            business_id="B-FAILSAFE",
            plan_id="P-FAILSAFE",
            objective="Build a local draft",
        )
        task = EnactorTask(
            task_id="T-FAILSAFE",
            execution_id=request.execution_id,
            agent_role="builders.web_developer",
            objective="Create a draft locally",
            tool="builder.create_asset",
            allowed_tools=("builder.create_asset",),
            mode=ToolMode.DRAFT,
        )
        plan = controller.compile_plan(request, (task,))
        runtime.emergency_pause("operator stop", authority="owner-1")
        with self.assertRaises(SystemPausedError):
            controller.submit(request, plan, {})
        self.assertIsNone(controller.store.executions.maybe(request.execution_id))

    def test_sector_http_boundaries_accept_their_cross_sector_data_shapes(self):
        finance = MoneyCalculatorApi(MoneyCalculatorService(reliability=ReliabilityRuntime()))
        status, body = call_wsgi(
            finance,
            "POST",
            "/money-calculator/assess",
            {
                "proposal_id": "ACT-API",
                "objective": "Run activation",
                "owner": "owner",
                "planned_spend": {"amount": 200, "currency": "USD"},
                "expected_revenue": {"amount": 300, "currency": "USD"},
                "time_horizon_days": 30,
                "confidence": 0.9,
                "budget_limit": {"amount": 150, "currency": "USD"},
            },
        )
        self.assertEqual(status, "200 OK")
        self.assertEqual(body["code"], "request_owner_approval")

        evolver = EvolverApi(EvolverService(reliability=ReliabilityRuntime()))
        status, body = call_wsgi(
            evolver,
            "POST",
            "/evolver/assess",
            {
                "request_id": "EXP-API",
                "business_domain": "tutoring",
                "idea": "Add online tutoring",
                "required_capabilities": ["scheduling", "payments"],
                "existing_capabilities": ["payments"],
                "expected_monthly_revenue": {"amount": 10000, "currency": "USD"},
            },
        )
        self.assertEqual(status, "200 OK")
        self.assertEqual(body["missing_capabilities"], ["scheduling"])
        self.assertTrue(body["financially_viable"])

        reports = ReportCollectorApi(ReportCollectorService(reliability=ReliabilityRuntime()))
        status, body = call_wsgi(
            reports,
            "POST",
            "/report-collector/discover",
            {"components": [
                {"name": "finance", "category": "sector", "status": "healthy", "owner": "finance"}
            ]},
        )
        self.assertEqual(status, "200 OK")
        self.assertEqual(body["components"][0]["name"], "finance")

    def test_finance_and_evolver_fail_closed_without_comparable_financial_inputs(self):
        with self.assertRaisesRegex(ValueError, "same currency"):
            ActivationProposal(
                "ACT-CURRENCY",
                "Run activation",
                "owner",
                Money(100, "USD"),
                Money(150, "CAD"),
                30,
                0.9,
            )
        plan = EvolverService(reliability=ReliabilityRuntime()).assess(
            ExpansionRequest(
                "EXP-NO-FORECAST",
                "tutoring",
                "Add tutoring operations",
                ("scheduling",),
            )
        )
        self.assertIsNone(plan.expected_revenue)
        self.assertFalse(plan.financially_viable)


if __name__ == "__main__":
    unittest.main()
