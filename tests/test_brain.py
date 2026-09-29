import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
import os
import unittest
from unittest.mock import patch

from research_room.models import Money
from research_room.models import ResearchMission, ResearchTask
from money_calculator import ActivationProposal, MoneyCalculatorService

from brain import (
    AgentDefinition,
    AgentRegistry,
    BrainApi,
    BrainOperation,
    BrainService,
    BrainResearchAgent,
    DataSensitivity,
    DelegationRequest,
    InferenceRequest,
    MemoryRecord,
    ModelProfile,
    ModelRegistry,
    ProviderError,
    ProviderOutputError,
    SecretInRequestError,
    SecretLeakError,
    ProviderResponse,
    ScopedCredential,
    SessionManager,
)
from brain.memory import MemoryStore
from brain.events import EventBus
from brain.policy import OutputValidationError, validate_output, validate_schema_definition
from brain.budget import BudgetExceeded
from brain.budget import BudgetManager


class TestSecretManager:
    def __init__(self):
        self.requesters = []

    def get_scoped_credential(self, *, requester_id, resource, purpose, duration_seconds):
        self.requesters.append((requester_id, resource, purpose, duration_seconds))
        if requester_id != "brain-provider-gateway" or purpose != "inference" or duration_seconds > 60:
            raise PermissionError("Not authorized.")
        return ScopedCredential(f"test-key-{resource}", resource)


class TestProvider:
    def __init__(self, provider_id, responses):
        self.provider_id = provider_id
        self.responses = list(responses)
        self.credentials = []
        self.used_credentials = []
        self.requests = []
        self.mutate_schema = False
        self.health_state = "healthy"

    def complete(self, request, credential):
        self.credentials.append(credential)
        self.used_credentials.append(credential.reveal_to_provider_adapter())
        self.requests.append(request)
        if self.mutate_schema and request.schema is not None:
            request.schema.clear()
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def health_check(self):
        return self.health_state


class BrainFixture(unittest.TestCase):
    def setUp(self):
        self.agents = AgentRegistry()
        self.agent = AgentDefinition(
            "research-agent-01", "research_room", "market_discovery",
            frozenset({
                BrainOperation.COMPLETE, BrainOperation.DELEGATE_TASK,
                BrainOperation.MEMORY_WRITE, BrainOperation.RETRIEVE, BrainOperation.MEMORY_FORGET,
            }),
            frozenset({"fast", "backup"}), frozenset({"research"}),
            1_000, Money(1, "USD"), max_delegation_depth=2,
            allowed_delegate_types=frozenset({"researcher"}),
        )
        self.agents.register(self.agent)
        self.models = ModelRegistry()
        self.models.register(ModelProfile(
            "fast", "primary", "model-fast", frozenset({BrainOperation.COMPLETE}),
            frozenset({"research_room"}), 2_000, .01, .02,
        ))
        self.models.register(ModelProfile(
            "backup", "secondary", "model-backup", frozenset({BrainOperation.COMPLETE}),
            frozenset({"research_room"}), 2_000, .02, .04,
        ))
        self.primary = TestProvider("primary", [ProviderResponse({"result": "research complete"}, 10, 20)])
        self.secondary = TestProvider("secondary", [ProviderResponse({"result": "fallback result"}, 10, 20)])
        self.secret_manager = TestSecretManager()
        self.service = BrainService(
            agents=self.agents,
            sessions=SessionManager(),
            models=self.models,
            providers={"primary": self.primary, "secondary": self.secondary},
            secrets=self.secret_manager,
            schemas={
                "agent_result": {
                    "type": "object",
                    "required": ["result"],
                    "properties": {"result": {"type": "string", "minLength": 1}},
                    "additionalProperties": False,
                }
            },
            failure_threshold=1,
        )

    def session(self, *, agent_id=None, task_id="task-1"):
        return self.service.create_session(agent_id or self.agent.agent_id, task_id=task_id)

    def request(self, *, task_id="task-1", max_cost=.5, **overrides):
        values = {
            "request_id": "request-1",
            "agent_id": self.agent.agent_id,
            "sector": self.agent.sector,
            "task_id": task_id,
            "operation": BrainOperation.COMPLETE,
            "input": {"prompt": "research market demand"},
            "max_tokens": 200,
            "max_cost": Money(max_cost, "USD"),
            "schema_name": "agent_result",
        }
        values.update(overrides)
        return InferenceRequest(**values)

    def test_emergency_stop_pauses_other_sectors_through_shared_reliability_runtime(self):
        runtime = self.service.reliability
        try:
            self.service.emergency_stop("operator safety stop", authority="owner-1")
            self.assertTrue(runtime.failsafe.paused)
            with self.assertRaises(PermissionError):
                MoneyCalculatorService().assess(
                    ActivationProposal(
                        "ACT-BRAIN-STOP", "test", "owner",
                        Money(100, "USD"), Money(150, "USD"), 10, 0.9,
                    )
                )
        finally:
            if runtime.failsafe.paused:
                self.service.restart(authority="owner-1")
        self.assertFalse(runtime.failsafe.paused)


class BrainInferenceTests(BrainFixture):
    def test_service_does_not_publish_secret_or_registry_backends(self):
        for attribute in ("secrets", "sessions", "agents", "providers", "memory", "events"):
            self.assertFalse(hasattr(self.service, attribute))

    def test_scoped_inference_audits_usage_without_exposing_provider_secret(self):
        grant = self.session()
        result = self.service.complete(
            self.request(model_profile="fast"), session_id=grant.session.session_id, session_token=grant.token,
        )

        self.assertEqual(result.output, {"result": "research complete"})
        self.assertEqual(result.status, "success")
        self.assertEqual(result.usage.cost.currency, "USD")
        self.assertEqual(len(self.service.audit_log()), 1)
        self.assertEqual(self.service.audit_log()[0].status, "success")
        self.assertEqual(self.service.audit_log()[0].context_refs, ())
        grant_repr = repr(grant)
        self.assertNotIn(grant.token, grant_repr)
        self.assertEqual(self.secret_manager.requesters, [("brain-provider-gateway", "primary", "inference", 60)])
        self.assertNotIn("test-key", repr(self.primary.credentials[0]))
        self.assertEqual(self.primary.used_credentials, ["test-key-primary"])
        with self.assertRaises(PermissionError):
            self.primary.credentials[0].reveal_to_provider_adapter()
        self.assertIn("brain.inference.completed", [event.event_type for event in self.service.event_log()])

    def test_session_is_bound_to_agent_task_and_revocation(self):
        grant = self.session()
        with self.assertRaises(PermissionError):
            self.service.complete(self.request(task_id="another-task"), session_id=grant.session.session_id, session_token=grant.token)
        self.service.revoke_session(grant.session.session_id, authority="operator-1")
        with self.assertRaises(PermissionError):
            self.service.complete(self.request(), session_id=grant.session.session_id, session_token=grant.token)

    def test_request_id_is_idempotent_and_cannot_spend_twice(self):
        grant = self.session()
        request = self.request()
        self.service.complete(request, session_id=grant.session.session_id, session_token=grant.token)
        with self.assertRaisesRegex(ValueError, "already been used"):
            self.service.complete(request, session_id=grant.session.session_id, session_token=grant.token)
        self.assertEqual(len(self.service.usage_log()), 1)
        self.assertEqual(self.service.audit_log()[-1].reason, "duplicate_request_id")

    def test_agent_pause_revokes_sessions_and_prevents_reuse_after_resume(self):
        grant = self.session()
        self.service.set_agent_status(self.agent.agent_id, "paused", authority="operator-1")
        with self.assertRaises(PermissionError):
            self.service.complete(self.request(), session_id=grant.session.session_id, session_token=grant.token)
        self.service.set_agent_status(self.agent.agent_id, "active", authority="operator-1")
        with self.assertRaises(PermissionError):
            self.service.complete(self.request(), session_id=grant.session.session_id, session_token=grant.token)

    def test_invalid_structured_output_is_rejected_and_audited(self):
        self.primary.responses = [ProviderResponse({"unexpected": "output"}, 10, 20)]
        self.primary.mutate_schema = True
        grant = self.session()
        with self.assertRaisesRegex(ProviderOutputError, "registered schema"):
            self.service.complete(self.request(), session_id=grant.session.session_id, session_token=grant.token)
        audit = self.service.audit_log()[-1]
        self.assertEqual((audit.status, audit.reason), ("blocked", "output_schema_invalid"))
        self.assertIsNone(audit.output_hash)

    def test_provider_secret_in_output_is_rejected(self):
        self.primary.responses = [ProviderResponse({"result": "test-key-primary"}, 10, 20)]
        grant = self.session()
        with self.assertRaisesRegex(SecretLeakError, "secret-leak"):
            self.service.complete(self.request(), session_id=grant.session.session_id, session_token=grant.token)
        self.assertEqual(self.service.audit_log()[-1].reason, "secret_leak")

    def test_secret_in_input_is_blocked_before_provider_call(self):
        grant = self.session()
        with self.assertRaises(SecretInRequestError):
            self.service.complete(
                self.request(input={"prompt": "test-key-primary"}),
                session_id=grant.session.session_id, session_token=grant.token,
            )
        self.assertEqual(self.primary.requests, [])
        self.assertEqual(self.service.audit_log()[-1].reason, "secret_in_request")

    def test_provider_failure_falls_back_and_opens_provider_circuit(self):
        self.primary.responses = [ProviderError("provider failed")]
        grant = self.session()
        result = self.service.complete(
            self.request(model_profile="fast"), session_id=grant.session.session_id, session_token=grant.token,
        )
        self.assertEqual(result.model_profile, "backup")
        self.assertTrue(any("fallback" in warning for warning in result.warnings))
        self.assertEqual(self.service.health()["providers"]["primary"]["state"], "open")
        self.assertEqual(self.secondary.requests[0].model, "model-backup")

    def test_per_request_cost_ceiling_is_enforced_and_actual_usage_is_retained(self):
        self.primary.responses = [ProviderResponse({"result": "research complete"}, 100, 20)]
        grant = self.session()
        with self.assertRaisesRegex(PermissionError, "exceeded the task cost or token budget"):
            self.service.complete(
                self.request(max_tokens=1, max_cost=.0005),
                session_id=grant.session.session_id, session_token=grant.token,
            )
        self.assertEqual(len(self.service.usage_log()), 1)
        self.assertEqual(self.service.audit_log()[-1].reason, "budget_exceeded")

    def test_emergency_pause_requires_explicit_restart(self):
        grant = self.session()
        revoked = self.service.emergency_stop("provider incident", authority="operator-1")
        self.assertEqual(revoked[0].status, "revoked")
        with self.assertRaisesRegex(PermissionError, "emergency-paused"):
            self.service.complete(self.request(), session_id=grant.session.session_id, session_token=grant.token)
        with self.assertRaisesRegex(PermissionError, "emergency-paused"):
            self.session(task_id="paused-task")
        with self.assertRaises(PermissionError):
            self.service.restart(authority="")
        self.service.restart(authority="operator-1")
        grant = self.session()
        result = self.service.complete(self.request(), session_id=grant.session.session_id, session_token=grant.token)
        self.assertEqual(result.status, "success")

    def test_secret_manager_only_reads_configured_environment_secret(self):
        from brain.provider import EnvironmentSecretManager, SecretAccessError

        manager = EnvironmentSecretManager({"primary": "BRAIN_TEST_PROVIDER_KEY"})
        with patch.dict(os.environ, {"BRAIN_TEST_PROVIDER_KEY": "local-test-secret"}):
            credential = manager.get_scoped_credential(
                requester_id="brain-provider-gateway", resource="primary", purpose="inference", duration_seconds=60,
            )
        self.assertEqual(credential.reveal_to_provider_adapter(), "local-test-secret")
        with self.assertRaises(SecretAccessError):
            manager.get_scoped_credential(requester_id="research-agent-01", resource="primary", purpose="inference", duration_seconds=60)

    def test_health_does_not_echo_untrusted_provider_status(self):
        self.primary.health_state = "test-key-primary"
        self.assertEqual(self.service.health()["providers"]["primary"]["health"], "unknown")


class BrainPolicyAndMemoryTests(BrainFixture):
    def test_agent_task_token_budget_is_aggregated_across_requests(self):
        budgets = BudgetManager()
        first = budgets.reserve(
            agent_id="agent", task_id="task", amount=Money(.5, "USD"), limit=Money(1, "USD"),
            tokens=60, token_limit=100,
        )
        budgets.commit(first.reservation_id, Money(.1, "USD"), limit=Money(1, "USD"), actual_tokens=60, token_limit=100)
        with self.assertRaisesRegex(BudgetExceeded, "token budget"):
            budgets.reserve(
                agent_id="agent", task_id="task", amount=Money(.5, "USD"), limit=Money(1, "USD"),
                tokens=41, token_limit=100,
            )

    def test_model_policy_rejects_unpermitted_profile_and_token_limit(self):
        grant = self.session()
        with self.assertRaises(PermissionError):
            self.service.complete(
                self.request(model_profile="not-registered"),
                session_id=grant.session.session_id, session_token=grant.token,
            )
        with self.assertRaises(PermissionError):
            self.service.complete(
                self.request(max_tokens=1_001),
                session_id=grant.session.session_id, session_token=grant.token,
            )

    def test_memory_namespace_expiry_and_sensitivity_are_enforced(self):
        store = MemoryStore()
        content = {"finding": "demand rising"}
        record = MemoryRecord("memory-1", "research", content, DataSensitivity.INTERNAL, "source-1")
        store.write(self.agent, record)
        content["finding"] = "tampered"
        self.assertEqual(store.get(self.agent, "memory-1").content, {"finding": "demand rising"})
        from brain.memory import ContextBuilder
        context = ContextBuilder(store).build(
            self.agent, task_id="task-1", references=("memory-1",), max_tokens=100,
        )
        self.assertTrue(context.items[0].untrusted)
        self.assertEqual(context.source_refs, ("source-1",))
        with self.assertRaises(PermissionError):
            store.retrieve(self.agent, namespace="customer_data", query="", top_k=1)
        restricted = MemoryRecord("memory-2", "research", {}, DataSensitivity.RESTRICTED, "private")
        with self.assertRaises(PermissionError):
            store.write(self.agent, restricted)

    def test_event_records_and_subscribers_cannot_mutate_stored_payloads(self):
        bus = EventBus()
        payload = {"nested": {"value": "original"}}
        event = bus.publish("brain.test", source="test", payload=payload, correlation_id="test-1")
        event.payload["nested"]["value"] = "returned mutation"
        payload["nested"]["value"] = "input mutation"
        bus.subscribe("brain.test", lambda item: item.payload["nested"].update(value="subscriber mutation"))
        bus.dispatch(event.event_id)
        self.assertEqual(bus.events()[0].payload, {"nested": {"value": "original"}})

    def test_event_delivery_retries_only_failed_subscribers(self):
        bus = EventBus()
        event = bus.publish("brain.test", source="test", payload={}, correlation_id="test-2")
        delivered = []
        failures = [True]
        bus.subscribe("brain.test", lambda _: delivered.append("first"), subscriber_id="first")

        def intermittent_handler(_):
            if failures[0]:
                failures[0] = False
                raise RuntimeError("temporary handler failure")
            delivered.append("second")

        bus.subscribe("brain.test", intermittent_handler, subscriber_id="second")
        with self.assertRaises(RuntimeError):
            bus.dispatch(event.event_id)
        bus.dispatch(event.event_id)
        self.assertEqual(delivered, ["first", "second"])

    def test_session_memory_scope_is_narrower_than_agent_registry(self):
        record = MemoryRecord("memory-scoped", "research", {"finding": "demand rising"}, DataSensitivity.INTERNAL, "source-1")
        setup_grant = self.session()
        self.service.write_memory(record, session_id=setup_grant.session.session_id, session_token=setup_grant.token)
        grant = self.service.create_session(
            self.agent.agent_id, task_id="task-1",
            operations=frozenset({BrainOperation.RETRIEVE}),
            memory_namespaces=frozenset(),
        )
        with self.assertRaises(PermissionError):
            self.service.retrieve_memory(
                namespace="research", query="demand", session_id=grant.session.session_id, session_token=grant.token,
            )

    def test_inference_context_is_filtered_by_session_namespace(self):
        writer = self.session()
        record = MemoryRecord(
            "memory-context", "research", {"finding": "demand rising"}, DataSensitivity.INTERNAL, "source-context",
        )
        self.service.write_memory(record, session_id=writer.session.session_id, session_token=writer.token)
        grant = self.service.create_session(
            self.agent.agent_id, task_id="task-1", operations=frozenset({BrainOperation.COMPLETE}),
            memory_namespaces=frozenset({"research"}),
        )
        result = self.service.complete(
            self.request(context_refs=("memory-context",)),
            session_id=grant.session.session_id, session_token=grant.token,
        )
        self.assertEqual(result.status, "success")
        self.assertTrue(self.primary.requests[0].context[0]["untrusted"])
        self.assertEqual(self.service.audit_log()[-1].context_refs, ("memory-context",))

    def test_memory_write_retrieve_and_forget_are_session_authorized(self):
        grant = self.session()
        record = MemoryRecord("memory-service", "research", {"finding": "demand"}, DataSensitivity.INTERNAL, "source-2")
        self.service.write_memory(record, session_id=grant.session.session_id, session_token=grant.token)
        retrieved = self.service.retrieve_memory(
            namespace="research", query="demand", session_id=grant.session.session_id, session_token=grant.token,
        )
        self.assertEqual(retrieved, (record,))
        self.service.forget_memory("memory-service", session_id=grant.session.session_id, session_token=grant.token)
        self.assertEqual(
            self.service.retrieve_memory(
                namespace="research", query="demand", session_id=grant.session.session_id, session_token=grant.token,
            ),
            (),
        )

    def test_json_schema_validator_checks_nested_output(self):
        schema = {
            "type": "object",
            "required": ["items"],
            "properties": {"items": {"type": "array", "items": {"type": "integer"}, "minItems": 1}},
        }
        validate_output({"items": [1, 2]}, schema)
        with self.assertRaises(OutputValidationError):
            validate_output({"items": ["not-an-int"]}, schema)
        with self.assertRaisesRegex(ValueError, "Unsupported JSON Schema keyword"):
            validate_schema_definition({"type": "string", "pattern": "^safe"})

    def test_delegation_requires_approval_and_target_session(self):
        grant = self.session()
        self.service.write_memory(
            MemoryRecord("memory-1", "research", {"finding": "competitor price"}, DataSensitivity.INTERNAL, "source-1"),
            session_id=grant.session.session_id, session_token=grant.token,
        )
        target = AgentDefinition(
            "researcher-01", "research_room", "researcher", frozenset({BrainOperation.COMPLETE}),
            frozenset({"fast"}), frozenset({"research"}), 100, Money(.2, "USD"),
        )
        self.agents.register(target)
        delegation = self.service.request_delegation(
            DelegationRequest(
                "delegation-1", self.agent.agent_id, "researcher", "Check competitor pricing",
                ("memory-1",), Money(.2, "USD"), datetime.now(timezone.utc) + timedelta(minutes=5),
                1, "agent_result", True,
            ),
            session_id=grant.session.session_id, session_token=grant.token,
        )
        self.assertEqual(delegation.status, "awaiting_approval")
        target_grant = self.service.create_session("researcher-01", task_id="delegation-1")
        with self.assertRaises(PermissionError):
            self.service.complete_delegation(
                "delegation-1", target_agent_id="researcher-01",
                session_id=target_grant.session.session_id, session_token=target_grant.token,
                result={"result": "done"},
            )
        self.service.approve_delegation("delegation-1", authority="orchestrator-1")
        completed = self.service.complete_delegation(
            "delegation-1", target_agent_id="researcher-01",
            session_id=target_grant.session.session_id, session_token=target_grant.token,
            result={"result": "done"},
        )
        self.assertEqual(completed.status, "completed")
        with self.assertRaises(BudgetExceeded):
            self.service.request_delegation(
                DelegationRequest(
                    "delegation-2", self.agent.agent_id, "researcher", "Check another competitor",
                    (), Money(.9, "USD"), datetime.now(timezone.utc) + timedelta(minutes=5),
                    1, "agent_result", True,
                ),
                session_id=grant.session.session_id, session_token=grant.token,
            )


class BrainApiTests(BrainFixture):
    def test_wsgi_inference_requires_bearer_session_and_exposes_health(self):
        app = BrainApi(self.service)
        statuses = []
        body = {
            "session_id": "missing",
            "request_id": "request-1",
            "agent_id": self.agent.agent_id,
            "sector": self.agent.sector,
            "task_id": "task-1",
            "operation": "complete",
            "input": {"prompt": "research"},
            "max_tokens": 200,
            "max_cost": {"amount": .5, "currency": "USD"},
        }
        encoded = json.dumps(body).encode()
        response = app(
            {"REQUEST_METHOD": "POST", "PATH_INFO": "/brain/inference", "CONTENT_LENGTH": str(len(encoded)),
             "wsgi.input": BytesIO(encoded)},
            lambda status, _: statuses.append(status),
        )
        self.assertEqual(statuses, ["401 Unauthorized"])
        self.assertIn(b"Bearer session token", response[0])

        statuses.clear()
        app({"REQUEST_METHOD": "GET", "PATH_INFO": "/brain/health"}, lambda status, _: statuses.append(status))
        self.assertEqual(statuses, ["200 OK"])

    def test_json_body_rejects_nonstandard_numeric_constants(self):
        with self.assertRaisesRegex(ValueError, "Non-standard JSON constant"):
            BrainApi._read_json({
                "CONTENT_LENGTH": "11",
                "wsgi.input": BytesIO(b'{"n": NaN}'),
            })

    def test_wsgi_authenticated_inference_uses_scoped_token(self):
        app = BrainApi(self.service)
        grant = self.session()
        statuses = []
        body = {
            "session_id": grant.session.session_id,
            "request_id": "request-api",
            "agent_id": self.agent.agent_id,
            "sector": self.agent.sector,
            "task_id": "task-1",
            "operation": "complete",
            "input": {"prompt": "research"},
            "max_tokens": 200,
            "max_cost": {"amount": .5, "currency": "USD"},
            "schema_name": "agent_result",
        }
        encoded = json.dumps(body).encode()
        response = app(
            {"REQUEST_METHOD": "POST", "PATH_INFO": "/brain/inference", "CONTENT_LENGTH": str(len(encoded)),
             "HTTP_AUTHORIZATION": f"Bearer {grant.token}", "wsgi.input": BytesIO(encoded)},
            lambda status, _: statuses.append(status),
        )
        self.assertEqual(statuses, ["200 OK"])
        self.assertIn(b"research complete", response[0])
        self.assertNotIn(b"test-key", response[0])


class BrainResearchIntegrationTests(BrainFixture):
    def test_research_room_agent_adapter_uses_and_revokes_brain_session(self):
        agent = BrainResearchAgent(
            self.service, agent_id=self.agent.agent_id, role=self.agent.role,
            session_issuer=lambda agent_id, task_id: self.service.create_session(
                agent_id, task_id=task_id, operations=frozenset({BrainOperation.COMPLETE}),
                memory_namespaces=frozenset(),
            ),
            session_revoker=lambda session_id: self.service.revoke_session(session_id, authority="test-orchestrator"),
        )
        mission = ResearchMission(
            "RM-brain", "Assess demand", "orchestrator", ["Uganda"], ["resale"], "medium", "standard",
        )
        task = ResearchTask("RM-brain-01", "RM-brain", self.agent.role, "Assess demand", [], [], "agent_result", 30)
        result = agent.run(mission, task)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.data, {"result": "research complete"})
        self.assertIn("brain.session.revoked", [event.event_type for event in self.service.event_log()])


if __name__ == "__main__":
    unittest.main()
