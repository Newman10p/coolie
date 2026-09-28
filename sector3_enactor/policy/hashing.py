"""Canonical JSON + SHA-256 digest helpers shared by approvals and audit."""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import json
from math import isfinite
from typing import Any


def canonical_json(value: Any) -> str:
    """Deterministic serialization; refuses anything non-canonical (fail closed)."""
    def normalize(item: Any) -> Any:
        if is_dataclass(item): return normalize(asdict(item))
        if isinstance(item, Enum): return normalize(item.value)
        if isinstance(item, datetime):
            if item.tzinfo is None: raise TypeError("Hashed datetimes must be timezone-aware.")
            return item.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        if item is None or isinstance(item, (str, bool, int)): return item
        if isinstance(item, float):
            if not isfinite(item): raise TypeError("Cannot hash non-finite floats.")
            return item
        if isinstance(item, bytes): return {"__bytes__": item.hex()}
        if isinstance(item, (list, tuple)): return [normalize(entry) for entry in item]
        if isinstance(item, set): return sorted((normalize(entry) for entry in item), key=lambda e: json.dumps(e, sort_keys=True))
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item): raise TypeError("Hashed dictionaries require string keys.")
            return {key: normalize(item[key]) for key in sorted(item)}
        raise TypeError(f"Unsupported value for canonical hashing: {type(item).__name__}")
    return json.dumps(normalize(value), sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return "sha256:" + sha256(canonical_json(value).encode("utf-8")).hexdigest()
