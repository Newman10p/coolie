from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
from math import isfinite
from typing import Any


PROHIBITED_PERMISSIONS = frozenset({"finance:transfer", "commerce:purchase", "ads:spend", "social:publish", "customer:message", "account:create"})


def canonical_json(value: Any) -> str:
    """Serialize supported audit values deterministically before hashing them."""
    def normalize(item: Any) -> Any:
        if is_dataclass(item): return normalize(asdict(item))
        if isinstance(item, Enum): return normalize(item.value)
        if isinstance(item, datetime):
            if item.tzinfo is None: raise TypeError("Audit datetimes must be timezone-aware.")
            return item.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        if item is None or isinstance(item, (str, bool, int)): return item
        if isinstance(item, float):
            if not isfinite(item): raise TypeError("Audit values cannot contain non-finite floats.")
            return item
        if isinstance(item, bytes): return {"__bytes__": item.hex()}
        if isinstance(item, (list, tuple)): return [normalize(entry) for entry in item]
        if isinstance(item, set): return sorted((normalize(entry) for entry in item), key=lambda entry: json.dumps(entry, sort_keys=True, separators=(",", ":")))
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item): raise TypeError("Audit dictionaries require string keys.")
            return {key: normalize(item[key]) for key in sorted(item)}
        raise TypeError(f"Unsupported audit value: {type(item).__name__}")
    return json.dumps(normalize(value), sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class ToolCallAudit:
    coolie_instance_id: str
    sector_id: str
    mission_id: str
    agent_id: str
    task_id: str
    tool: str
    permission: str
    arguments_hash: str
    result_hash: str
    risk_level: str
    approval_context: str | None
    timestamp: datetime


class ToolPolicy:
    """Authorizes research-only capabilities; callers never receive raw tool access."""
    def __init__(self, granted_permissions: set[str]) -> None:
        forbidden = granted_permissions & PROHIBITED_PERMISSIONS
        if forbidden: raise ValueError(f"Research Room cannot be granted prohibited permissions: {sorted(forbidden)}")
        if any(not permission.startswith("research:") for permission in granted_permissions): raise ValueError("Research Room permissions must use the research: namespace.")
        self._granted = frozenset(granted_permissions)

    def authorize(self, permission: str, task_allowed_tools: list[str]) -> bool:
        return permission in self._granted and permission in task_allowed_tools

    @staticmethod
    def audit(*, coolie_instance_id: str, sector_id: str, mission_id: str, agent_id: str, task_id: str, tool: str, permission: str, arguments: Any, result: Any, risk_level: str = "low", approval_context: str | None = None) -> ToolCallAudit:
        required = {"coolie_instance_id": coolie_instance_id, "sector_id": sector_id, "mission_id": mission_id, "agent_id": agent_id, "task_id": task_id, "tool": tool, "permission": permission}
        if any(not value.strip() for value in required.values()): raise ValueError("Audit identity fields must be non-empty.")
        digest = lambda value: "sha256:" + sha256(canonical_json(value).encode("utf-8")).hexdigest()
        return ToolCallAudit(coolie_instance_id, sector_id, mission_id, agent_id, task_id, tool, permission, digest(arguments), digest(result), risk_level, approval_context, datetime.now(timezone.utc))
