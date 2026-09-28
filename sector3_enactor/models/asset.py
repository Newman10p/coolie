"""Asset lifecycle models — document §5.2D (concept → draft → reviewed → approved → published → archived)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .shared import now_utc, _non_empty


class AssetStage(str, Enum):
    CONCEPT = "concept"; DRAFT = "draft"; REVIEWED = "reviewed"; APPROVED = "approved"
    PUBLISHED = "published"; ARCHIVED = "archived"


STAGE_ORDER = {stage: index for index, stage in enumerate(
    [AssetStage.CONCEPT, AssetStage.DRAFT, AssetStage.REVIEWED, AssetStage.APPROVED, AssetStage.PUBLISHED, AssetStage.ARCHIVED])}


class AssetType(str, Enum):
    COPY = "copy"; IMAGE = "image"; PAGE = "page"; CODE = "code"; PRODUCT_LISTING = "product_listing"
    SEO_CHANGESET = "seo_changeset"; REPORT = "report"; CAMPAIGN = "campaign"


@dataclass(frozen=True)
class AssetVersion:
    version_id: str
    content_hash: str
    artifact_key: str
    created_by: str
    created_at: datetime
    notes: str = ""

    def __post_init__(self) -> None:
        for name in ("version_id", "content_hash", "artifact_key", "created_by"): _non_empty(getattr(self, name), name)
        if self.created_at.tzinfo is None: raise ValueError("created_at must be timezone-aware.")


@dataclass
class ManagedAsset:
    asset_id: str
    business_id: str
    execution_id: str | None
    asset_type: AssetType
    name: str
    stage: AssetStage = AssetStage.CONCEPT
    versions: tuple[AssetVersion, ...] = ()
    review_notes: tuple[str, ...] = ()
    updated_at: datetime = field(default_factory=now_utc)

    def __post_init__(self) -> None:
        for name in ("asset_id", "business_id", "name"): _non_empty(getattr(self, name), name)
        if not isinstance(self.asset_type, AssetType): raise ValueError("asset_type must be an AssetType.")
        if not isinstance(self.stage, AssetStage): raise ValueError("stage must be an AssetStage.")

    def advance_to(self, target: AssetStage, *, actor_id: str, reason: str) -> None:
        """One-step-forward movement only; QA/human review cannot be skipped (§8.1 rule 8)."""
        if not actor_id.strip() or not reason.strip(): raise ValueError("Stage transitions require actor_id and reason.")
        current, wanted = STAGE_ORDER[self.stage], STAGE_ORDER[target]
        allowed_next = {current + 1} if self.stage is not AssetStage.PUBLISHED else {STAGE_ORDER[AssetStage.ARCHIVED]}
        if wanted not in allowed_next:
            raise ValueError(f"Illegal asset transition {self.stage.value} -> {target.value}; stages advance one step at a time.")
        if target in {AssetStage.REVIEWED, AssetStage.APPROVED, AssetStage.PUBLISHED} and not self.versions:
            raise ValueError("Cannot review/approve/publish an asset with no stored versions.")
        self.stage = target
        self.updated_at = now_utc()

    def add_version(self, version: AssetVersion) -> None:
        if any(existing.version_id == version.version_id for existing in self.versions):
            raise ValueError("Asset version IDs must be unique.")
        self.versions = self.versions + (version,)
        self.updated_at = now_utc()
