"""Immutable source/report artifact storage abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class StoredArtifact:
    key: str
    content_hash: str
    content_type: str
    size_bytes: int


class ObjectStorage(Protocol):
    def put_immutable(self, key: str, content: bytes, content_type: str) -> StoredArtifact: ...
    def get(self, key: str) -> bytes: ...


def _artifact(key: str, content: bytes, content_type: str) -> StoredArtifact:
    if not key.strip() or key.startswith("/") or ".." in Path(key).parts: raise ValueError("Artifact key must be a safe relative key.")
    if not content_type.strip(): raise ValueError("content_type is required.")
    return StoredArtifact(key, "sha256:" + sha256(content).hexdigest(), content_type, len(content))


class InMemoryObjectStorage:
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put_immutable(self, key: str, content: bytes, content_type: str) -> StoredArtifact:
        record = _artifact(key, content, content_type)
        existing = self._objects.get(key)
        if existing is not None and existing != content: raise ValueError("Artifact keys are immutable.")
        self._objects[key] = bytes(content)
        return record

    def get(self, key: str) -> bytes:
        return self._objects[key]


class LocalObjectStorage:
    """Development implementation; production may supply an S3-compatible adapter."""
    def __init__(self, root: Path) -> None:
        self._root = root.resolve(); self._root.mkdir(parents=True, exist_ok=True)

    def put_immutable(self, key: str, content: bytes, content_type: str) -> StoredArtifact:
        record = _artifact(key, content, content_type)
        path = (self._root / key).resolve()
        if self._root not in path.parents: raise ValueError("Artifact key escapes storage root.")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != content: raise ValueError("Artifact keys are immutable.")
        path.write_bytes(content)
        return record

    def get(self, key: str) -> bytes:
        path = (self._root / key).resolve()
        if self._root not in path.parents: raise ValueError("Artifact key escapes storage root.")
        return path.read_bytes()
