"""Deterministic in-memory repositories for every Sector 3 entity.
Durable Postgres adapters implement the same interfaces (Phase 6)."""
from __future__ import annotations

from typing import Callable

from ..models.approval import ApprovalRequest, ApprovalStatus
from ..models.asset import ManagedAsset
from ..models.commerce import InventoryLevel, OrderRecord, ProductRecord
from ..models.deployment import DeploymentRecord
from ..models.execution import ExecutionRequest
from ..models.marketing import CampaignRecord
from ..models.messaging import InboundMessage, OutboundDraft, SupportTicket
from ..models.outcome import BusinessMetricSnapshot, OutcomeReport


class NotFound(KeyError):
    pass


class _EntityStore:
    """Minimal typed map keyed by an attribute name."""
    def __init__(self, key_attr: str) -> None:
        self._key_attr = key_attr
        self._items: dict[str, object] = {}

    def put(self, item: object) -> None:
        key = str(getattr(item, self._key_attr))
        self._items[key] = item

    def get(self, key: str) -> object:
        if key not in self._items: raise NotFound(f"{type(self).__name__}: missing {self._key_attr}={key}")
        return self._items[key]

    def maybe(self, key: str):
        return self._items.get(key)

    def all(self) -> tuple[object, ...]:
        return tuple(self._items.values())


class ExecutionRepository(_EntityStore):
    def __init__(self) -> None: super().__init__("execution_id")


class ApprovalRepository(_EntityStore):
    def __init__(self) -> None: super().__init__("approval_id")

    def get(self, key: str) -> ApprovalRequest: return super().get(key)

    def put(self, item: ApprovalRequest) -> None:
        existing = self.maybe(item.approval_id)
        if isinstance(existing, ApprovalRequest):
            if existing.status is ApprovalStatus.APPROVED and item.status not in {
                ApprovalStatus.APPROVED,
                ApprovalStatus.CONSUMED,
            }:
                raise ValueError("Approved decisions are immutable except for single-use consumption.")
            if existing.status in {ApprovalStatus.DENIED, ApprovalStatus.CONSUMED} and item.status is not existing.status:
                raise ValueError("Denied and consumed approvals cannot be changed.")
        super().put(item)

    def for_execution(self, execution_id: str) -> tuple[ApprovalRequest, ...]:
        return tuple(item for item in self.all() if isinstance(item, ApprovalRequest) and item.execution_id == execution_id)


class AssetRepository(_EntityStore):
    def __init__(self) -> None: super().__init__("asset_id")
    def get(self, key: str) -> ManagedAsset: return super().get(key)


class MessageRepository(_EntityStore):
    def __init__(self) -> None: super().__init__("message_id")
    def get(self, key: str) -> InboundMessage: return super().get(key)


class DraftRepository(_EntityStore):
    def __init__(self) -> None: super().__init__("draft_id")
    def get(self, key: str) -> OutboundDraft: return super().get(key)


class TicketRepository(_EntityStore):
    def __init__(self) -> None: super().__init__("ticket_id")
    def get(self, key: str) -> SupportTicket: return super().get(key)


class ProductRepository(_EntityStore):
    def __init__(self) -> None: super().__init__("product_id")
    def get(self, key: str) -> ProductRecord: return super().get(key)


class InventoryRepository:
    def __init__(self) -> None: self._levels: dict[str, InventoryLevel] = {}
    def put(self, level: InventoryLevel) -> None: self._levels[level.product_id] = level
    def get(self, product_id: str) -> InventoryLevel:
        if product_id not in self._levels: raise NotFound(f"Inventory missing for {product_id}")
        return self._levels[product_id]
    def all(self) -> tuple[InventoryLevel, ...]: return tuple(self._levels.values())


class OrderRepository(_EntityStore):
    def __init__(self) -> None: super().__init__("order_id")
    def get(self, key: str) -> OrderRecord: return super().get(key)


class CampaignRepository(_EntityStore):
    def __init__(self) -> None: super().__init__("campaign_id")
    def get(self, key: str) -> CampaignRecord: return super().get(key)


class DeploymentRepository:
    def __init__(self) -> None: self._records: list[DeploymentRecord] = []
    def add(self, record: DeploymentRecord) -> None:
        if any(existing.deployment_id == record.deployment_id for existing in self._records):
            raise ValueError("Duplicate deployment id.")
        self._records.append(record)
    def latest(self, business_id: str, environment: str) -> DeploymentRecord | None:
        matches = [r for r in self._records if r.business_id == business_id and r.environment.value == environment and r.status.value == "succeeded"]
        return matches[-1] if matches else None
    def get(self, deployment_id: str) -> DeploymentRecord:
        for record in reversed(self._records):
            if record.deployment_id == deployment_id: return record
        raise NotFound(deployment_id)
    def all(self) -> tuple[DeploymentRecord, ...]: return tuple(self._records)


class MetricRepository:
    def __init__(self) -> None: self._snapshots: list[BusinessMetricSnapshot] = []
    def add(self, snapshot: BusinessMetricSnapshot) -> None: self._snapshots.append(snapshot)
    def for_execution(self, execution_id: str) -> tuple[BusinessMetricSnapshot, ...]:
        return tuple(s for s in self._snapshots if s.execution_id == execution_id)
    def for_business(self, business_id: str) -> tuple[BusinessMetricSnapshot, ...]:
        return tuple(s for s in self._snapshots if s.business_id == business_id)


class OutcomeRepository:
    def __init__(self) -> None: self._reports: list[OutcomeReport] = []
    def add(self, report: OutcomeReport) -> None:
        if any(existing.report_id == report.report_id for existing in self._reports): raise ValueError("Duplicate outcome report id.")
        self._reports.append(report)
    def all(self) -> tuple[OutcomeReport, ...]: return tuple(self._reports)


class Storefront:
    """Aggregate of mutable domain stores shared by fakes and agents."""
    def __init__(self) -> None:
        self.executions = ExecutionRepository()
        self.approvals = ApprovalRepository()
        self.assets = AssetRepository()
        self.messages = MessageRepository()
        self.drafts = DraftRepository()
        self.tickets = TicketRepository()
        self.products = ProductRepository()
        self.inventory = InventoryRepository()
        self.orders = OrderRepository()
        self.campaigns = CampaignRepository()
        self.deployments = DeploymentRepository()
        self.metrics = MetricRepository()
        self.outcomes = OutcomeRepository()
