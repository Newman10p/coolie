"""Marketing models — document §5.4."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .shared import Money, now_utc, _non_empty


class CampaignStatus(str, Enum):
    DRAFT = "draft"; VALIDATED = "validated"; PUBLISHED = "published"; PAUSED = "paused"; COMPLETED = "completed"


@dataclass
class CampaignRecord:
    campaign_id: str
    business_id: str
    execution_id: str
    name: str
    channel: str  # email | instagram | ads | seo
    budget: Money
    status: CampaignStatus = CampaignStatus.DRAFT
    audience: str = ""
    creative_asset_ids: tuple[str, ...] = ()
    claims: tuple["MarketingClaim", ...] = ()
    stop_condition_ids: tuple[str, ...] = ()
    published_at: datetime | None = None

    def __post_init__(self) -> None:
        for name in ("campaign_id", "business_id", "execution_id", "name", "channel", "audience"):
            _non_empty(getattr(self, name), name)
        if not isinstance(self.budget, Money): raise ValueError("Campaign budget must be Money.")
        if self.channel not in {"email", "instagram", "ads", "seo"}: raise ValueError("Campaign channel is invalid.")


@dataclass(frozen=True)
class MarketingClaim:
    """Every public marketing claim must reference approved product info or research evidence."""
    claim_id: str
    text: str
    evidence_reference: str | None

    def __post_init__(self) -> None:
        _non_empty(self.claim_id, "claim_id"); _non_empty(self.text, "text")


@dataclass(frozen=True)
class ScheduledPost:
    post_id: str
    campaign_id: str
    business_id: str
    platform: str
    content: str
    scheduled_for: datetime
    asset_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("post_id", "campaign_id", "business_id", "platform", "content"): _non_empty(getattr(self, name), name)
        if self.scheduled_for.tzinfo is None: raise ValueError("scheduled_for must be timezone-aware.")
