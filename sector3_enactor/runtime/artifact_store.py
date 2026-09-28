"""Content-addressed artifact storage (§6.1 Artifacts, §8.5 content hashes)."""
from __future__ import annotations

from dataclasses import dataclass

from ..models.execution import ArtifactReference
from ..policy.hashing import digest


@dataclass
class ArtifactStore:
    _blobs: dict[str, str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self._blobs is None: self._blobs = {}

    def put(self, key: str, content: str, *, content_type: str = "text/plain") -> ArtifactReference:
        if not key.strip(): raise ValueError("Artifact key must be non-empty.")
        content_hash = digest({"content": content})
        if key in self._blobs and self._blobs[key] != content:
            raise ValueError(f"Artifact {key} is immutable; write a new versioned key instead.")
        self._blobs[key] = content
        return ArtifactReference(artifact_key=key, content_hash=content_hash, content_type=content_type)

    def get(self, key: str) -> str:
        if key not in self._blobs: raise KeyError(f"Unknown artifact {key}")
        return self._blobs[key]

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._blobs))
