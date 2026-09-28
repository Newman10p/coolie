"""Commerce models — document §5.5 (Catalog, Inventory, Fulfillment, Returns)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .shared import Money, now_utc, _non_empty


class ProductStatus(str, Enum):
    DRAFT = "draft"; IN_REVIEW = "in_review"; PUBLISHED = "published"; ARCHIVED = "archived"


@dataclass
class ProductRecord:
    product_id: str
    business_id: str
    title: str
    description: str
    price: Money
    cost: Money | None = None
    sku: str = ""
    status: ProductStatus = ProductStatus.DRAFT
    evidence_references: tuple[str, ...] = ()   # claims must link to research evidence (§5.4)
    updated_at: datetime = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        for name in ("product_id", "business_id", "title", "description"): _non_empty(getattr(self, name), name)
        if not isinstance(self.price, Money): raise ValueError("price must be Money.")
        if self.cost is not None and not isinstance(self.cost, Money): raise ValueError("cost must be Money.")
        if self.status is ProductStatus.PUBLISHED and not self.sku:
            raise ValueError("Published products require a SKU.")


@dataclass(frozen=True)
class InventoryLevel:
    product_id: str
    business_id: str
    quantity: int
    reorder_point: int
    supplier_reference: str | None = None

    def __post_init__(self) -> None:
        _non_empty(self.product_id, "product_id")
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int) or self.quantity < 0:
            raise ValueError("Inventory quantity must be a non-negative integer.")
        if isinstance(self.reorder_point, bool) or not isinstance(self.reorder_point, int) or self.reorder_point < 0:
            raise ValueError("reorder_point must be a non-negative integer.")

    @property
    def low_stock(self) -> bool:
        return self.quantity <= self.reorder_point


@dataclass(frozen=True)
class InventorySyncPreview:
    execution_id: str
    changes: tuple[dict[str, object], ...]
    oversell_risk: bool
    summary: str

    def __post_init__(self) -> None:
        _non_empty(self.execution_id, "execution_id")
        if not isinstance(self.changes, tuple): raise ValueError("changes must be a tuple of dicts.")


class OrderStatus(str, Enum):
    OPEN = "open"; ROUTED = "routed"; SHIPPED = "shipped"; DELIVERED = "delivered"; PROBLEM = "problem"


@dataclass
class OrderRecord:
    order_id: str
    business_id: str
    product_ids: tuple[str, ...]
    customer_reference: str
    total: Money
    status: OrderStatus = OrderStatus.OPEN
    tracking_number: str | None = None
    fulfillment_route: str | None = None

    def __post_init__(self) -> None:
        for name in ("order_id", "business_id", "customer_reference"): _non_empty(getattr(self, name), name)
        if not self.product_ids: raise ValueError("Orders require at least one product.")
        if not isinstance(self.total, Money): raise ValueError("Order total must be Money.")


class ReturnDisposition(str, Enum):
    RECOMMEND_REFUND = "recommend_refund"; RECOMMEND_REPLACEMENT = "recommend_replacement"
    RECOMMEND_STORE_CREDIT = "recommend_store_credit"; REJECT_WITH_EXPLANATION = "reject_with_explanation"
    ESCALATE_HUMAN = "escalate_human"


@dataclass(frozen=True)
class ReturnRecommendation:
    """The Returns agent ONLY recommends; money moves via Money Calculator / humans (§5.5D)."""
    recommendation_id: str
    business_id: str
    order_id: str
    disposition: ReturnDisposition
    proposed_amount: Money | None
    justification: str
    routed_to: str  # finance | human | money_calculator

    def __post_init__(self) -> None:
        for name in ("recommendation_id", "business_id", "order_id", "justification", "routed_to"):
            _non_empty(getattr(self, name), name)
        if self.routed_to not in {"finance", "human", "money_calculator"}:
            raise ValueError("Return recommendations must route to finance, human or money_calculator.")
        if self.proposed_amount is not None and not isinstance(self.proposed_amount, Money):
            raise ValueError("proposed_amount must be Money.")
