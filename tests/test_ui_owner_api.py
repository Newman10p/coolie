import json
from io import BytesIO
from types import SimpleNamespace
import unittest

from sector3_enactor.api.routes import ApiResponse
from sector3_enactor.controller.execution_controller import ExecutionController
from sector3_enactor.models.approval import ApprovalLevel
from coolie_runtime import CoolieSystem
from reliability import ReliabilityRuntime
from ui.owner_api import OwnerPrincipal, OwnerWorkspaceApi
from supabase_storage.wallets import WalletAccount, WalletWithdrawalRequest
from datetime import datetime, timezone
from ui.wallet_api import WalletOnlyApplication, WalletWorkspaceApi


class FakeRepository:
    def __init__(self):
        self.items = []

    def all(self):
        return tuple(self.items)


class FakeResearchService:
    def __init__(self):
        self.missions = FakeRepository()
        self.created_by = None

    def create_mission(self, mission, actor_id):
        self.created_by = actor_id
        self.missions.items.append(mission)
        return mission


class FakeBrainService:
    def health(self):
        return {"service": "brain", "ready": True}


class FakeWalletRegistry:
    def __init__(self):
        self.wallets = {}
        self.requests = []

    def list_accounts(self):
        return tuple(self.wallets.values())

    def register(self, *, purpose, label, network, asset, address, created_by):
        wallet = WalletAccount(
            wallet_id="wallet-1",
            purpose=purpose,
            label=label,
            network=network,
            asset=asset,
            address=address,
            created_by=created_by,
            created_at=datetime.now(timezone.utc),
        )
        self.wallets[wallet.wallet_id] = wallet
        return wallet

    def update(self, wallet_id, *, updated_by, changes):
        previous = self.wallets[wallet_id]
        wallet = WalletAccount(
            **{
                **previous.__dict__,
                **changes,
                "updated_by": updated_by,
            }
        )
        self.wallets[wallet_id] = wallet
        return wallet

    def deactivate(self, wallet_id, *, updated_by):
        previous = self.wallets[wallet_id]
        wallet = WalletAccount(
            **{
                **previous.__dict__,
                "status": "inactive",
                "updated_by": updated_by,
            }
        )
        self.wallets[wallet_id] = wallet
        return wallet

    def list_withdrawals(self):
        return tuple(self.requests)

    def request_withdrawal(
        self,
        *,
        wallet_id,
        destination_address,
        amount,
        memo,
        requested_by,
    ):
        wallet = self.wallets[wallet_id]
        if wallet.purpose != "spending" or wallet.status != "active":
            raise KeyError(wallet_id)
        request = WalletWithdrawalRequest(
            request_id="withdrawal-1",
            wallet_id=wallet_id,
            destination_address=destination_address,
            network=wallet.network,
            asset=wallet.asset,
            amount=amount,
            memo=memo,
            requested_by=requested_by,
            requested_at=datetime.now(timezone.utc),
        )
        self.requests.append(request)
        return request


class FakeSystem:
    def __init__(self):
        self.research = FakeResearchService()
        services = {
            sector: SimpleNamespace(reliability=ReliabilityRuntime())
            for sector in CoolieSystem.SECTORS
        }
        services["brain"] = FakeBrainService()
        services["research_room"] = self.research
        enactor = object.__new__(ExecutionController)
        enactor.gateway = SimpleNamespace(reliability=ReliabilityRuntime())
        services["sector3_enactor"] = enactor
        self.system = CoolieSystem(
            services,
            startup_checks={
                sector: {"configuration": True}
                for sector in CoolieSystem.SECTORS
            },
            instance_id="owner-api-test",
            reliability=ReliabilityRuntime(),
        )
        for sector in CoolieSystem.SECTORS:
            self.system.heartbeat(sector, progress=True)

    @property
    def services(self):
        return self.system.services

    @property
    def SECTORS(self):
        return self.system.SECTORS

    def health(self, sector):
        return self.system.health(sector)


def request(app, method, path, *, body=None):
    encoded = json.dumps(body).encode() if body is not None else b""
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(encoded)),
        "wsgi.input": BytesIO(encoded),
    }
    captured = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)

    result = b"".join(app(environ, start_response))
    return captured, json.loads(result)


class OwnerWorkspaceApiTests(unittest.TestCase):
    def setUp(self):
        self.system = FakeSystem()
        self.principal = OwnerPrincipal("owner-17", frozenset({"workspace:read", "workspace:write"}))
        self.app = OwnerWorkspaceApi(self.system.system, lambda _: self.principal)

    def test_all_domain_routes_require_an_authenticated_principal(self):
        unauthenticated = OwnerWorkspaceApi(self.system.system, lambda _: None)
        response, body = request(unauthenticated, "GET", "/api/brain/health")
        self.assertEqual(response["status"], "401 Unauthorized")
        self.assertIn("authentication", body["error"])

    def test_domain_api_is_mounted_behind_workspace_read_permission(self):
        response, body = request(self.app, "GET", "/api/brain/health")
        self.assertEqual(response["status"], "200 OK")
        self.assertTrue(body["ready"])

        no_read_access = OwnerWorkspaceApi(
            self.system.system, lambda _: OwnerPrincipal("limited", frozenset())
        )
        denied, payload = request(no_read_access, "GET", "/api/brain/health")
        self.assertEqual(denied["status"], "403 Forbidden")
        self.assertEqual(payload["error"], "Missing permission: workspace:read.")

    def test_bootstrap_contains_live_composed_health_and_real_missions(self):
        response, body = request(self.app, "GET", "/api/ui/bootstrap")
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(body["dataMode"], "live")
        self.assertEqual(len(body["services"]), 7)
        self.assertEqual(body["missions"], [])

    def test_mission_creation_uses_authenticated_actor_and_returns_backend_record(self):
        response, body = request(
            self.app,
            "POST",
            "/api/ui/missions",
            body={
                "objective": "Validate demand in the UAE",
                "markets": ["UAE"],
                "businessModels": ["ecommerce"],
                "riskTolerance": "low",
                "requiredEvidenceLevel": "standard",
            },
        )
        self.assertEqual(response["status"], "201 Created")
        self.assertEqual(body["requestedBy"], "human")
        self.assertEqual(body["status"], "received")
        self.assertEqual(self.system.research.created_by, "owner-17")
        self.assertEqual(len(self.system.research.missions.all()), 1)

    def test_approval_identity_and_level_cannot_be_forged_in_request(self):
        approver = OwnerPrincipal(
            "trusted-approver",
            frozenset({"enactor:approve"}),
            ApprovalLevel.A3_STANDARD,
        )
        app = OwnerWorkspaceApi(self.system.system, lambda _: approver)
        received = {}

        class ApprovalApi:
            def post_approvals_decision(self, approval_id, payload):
                received["id"] = approval_id
                received.update(payload)
                return ApiResponse(200, {"approvalId": approval_id, "status": "approved"})

        app._apis["sector3_enactor"] = ApprovalApi()
        response, _ = request(
            app,
            "POST",
            "/api/enactor/approvals/ap-1/decision",
            body={"approve": True, "decidedBy": "attacker", "approverLevel": "A4"},
        )
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(received["decidedBy"], "trusted-approver")
        self.assertEqual(received["approverLevel"], "A3")

    def test_report_collector_discovery_cannot_read_arbitrary_server_paths(self):
        response, body = request(
            self.app,
            "GET",
            "/api/report-collector/discover?root=/",
        )
        self.assertEqual(response["status"], "404 Not Found")
        self.assertEqual(body["error"], "not found")

    def test_wallet_create_modify_and_remove_require_treasury_management(self):
        registry = FakeWalletRegistry()
        owner = OwnerPrincipal(
            "owner-17",
            frozenset({"workspace:read", "treasury:manage"}),
        )
        app = OwnerWorkspaceApi(
            self.system.system,
            lambda _: owner,
            wallet_registry=registry,
        )
        created, wallet = request(
            app,
            "POST",
            "/api/wallets",
            body={
                "purpose": "profits",
                "label": "Profit receive",
                "network": "chain-mainnet",
                "asset": "USDC",
                "address": "A" * 32,
            },
        )
        self.assertEqual(created["status"], "201 Created")
        self.assertEqual(wallet["custody"], "watch_only")
        changed, updated = request(
            app,
            "PATCH",
            "/api/wallets/wallet-1",
            body={"label": "Revenue wallet"},
        )
        self.assertEqual(changed["status"], "200 OK")
        self.assertEqual(updated["label"], "Revenue wallet")
        removed, inactive = request(app, "DELETE", "/api/wallets/wallet-1")
        self.assertEqual(removed["status"], "200 OK")
        self.assertEqual(inactive["status"], "inactive")

        denied_app = OwnerWorkspaceApi(
            self.system.system,
            lambda _: self.principal,
            wallet_registry=registry,
        )
        denied, _ = request(
            denied_app,
            "POST",
            "/api/wallets",
            body={
                "purpose": "profits",
                "label": "Test",
                "network": "chain-mainnet",
                "asset": "USDC",
                "address": "B" * 32,
            },
        )
        self.assertEqual(denied["status"], "403 Forbidden")

    def test_wallet_withdrawal_creates_pending_review_only(self):
        registry = FakeWalletRegistry()
        owner = OwnerPrincipal(
            "owner-17",
            frozenset({"workspace:read", "treasury:manage"}),
        )
        app = OwnerWorkspaceApi(
            self.system.system,
            lambda _: owner,
            wallet_registry=registry,
        )
        request(
            app,
            "POST",
            "/api/wallets",
            body={
                "purpose": "spending",
                "label": "Operating spend",
                "network": "chain-mainnet",
                "asset": "USDC",
                "address": "C" * 32,
            },
        )
        response, result = request(
            app,
            "POST",
            "/api/wallets/withdrawals",
            body={
                "walletId": "wallet-1",
                "destinationAddress": "D" * 32,
                "amount": "12.50",
            },
        )
        self.assertEqual(response["status"], "202 Accepted")
        self.assertEqual(result["status"], "pending_review")
        self.assertEqual(result["execution"], "not_executed")

        attempted_transfer, _ = request(
            app,
            "POST",
            "/api/wallets/withdrawals",
            body={
                "walletId": "wallet-1",
                "destinationAddress": "D" * 32,
                "amount": "12.50",
                "privateKey": "must-be-rejected",
            },
        )
        self.assertEqual(attempted_transfer["status"], "400 Bad Request")

    def test_wallet_only_api_authenticates_requests_and_exposes_no_other_live_api(self):
        registry = FakeWalletRegistry()
        owner = OwnerPrincipal(
            "owner-17",
            frozenset({"workspace:read", "treasury:manage"}),
        )
        wallet_api = WalletWorkspaceApi(registry, lambda _: owner)
        static_calls = []

        def static_app(environ, start_response):
            static_calls.append(environ["PATH_INFO"])
            start_response("200 OK", [])
            return [b"{}"]

        app = WalletOnlyApplication(wallet_api, static_app)
        response, body = request(app, "GET", "/api/wallets")
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(body["custody"], "watch_only")

        response, body = request(app, "GET", "/api/ui/bootstrap")
        self.assertEqual(response["status"], "503 Service Unavailable")
        self.assertEqual(body["dataMode"], "partial")

        response, body = request(app, "GET", "/")
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(body, {})
        self.assertEqual(static_calls, ["/"])

        unauthenticated = WalletWorkspaceApi(registry, lambda _: None)
        response, body = request(unauthenticated, "GET", "/api/wallets")
        self.assertEqual(response["status"], "401 Unauthorized")


if __name__ == "__main__":
    unittest.main()
