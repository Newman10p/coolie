"""Provider and secret-manager boundaries. The raw credential never leaves this module."""

from __future__ import annotations

from datetime import datetime, timedelta
import os
from threading import RLock
from typing import Protocol

from .models import ProviderRequest, ProviderResponse, utc_now


class ProviderError(RuntimeError):
    """A provider request failed; its message must not contain credentials."""


class SecretAccessError(PermissionError):
    pass


class ScopedCredential:
    def __init__(self, value: str, resource: str, *, expires_at: datetime | None = None) -> None:
        if not value:
            raise ValueError("Provider credential is empty.")
        if not resource.strip():
            raise ValueError("Provider credential resource is required.")
        self._value = value
        self.resource = resource
        current_time = utc_now()
        self.expires_at = expires_at or current_time + timedelta(seconds=60)
        if self.expires_at.tzinfo is None:
            raise ValueError("Provider credential expiry must be timezone-aware.")
        if not current_time < self.expires_at <= current_time + timedelta(seconds=60):
            raise ValueError("Provider credentials cannot be scoped for more than 60 seconds.")
        self._active = True
        self._lock = RLock()

    def reveal_to_provider_adapter(self) -> str:
        with self._lock:
            self._check_active()
            return self._value

    def contains(self, value: str) -> bool:
        with self._lock:
            self._check_active()
            return bool(value) and self._value in value

    def revoke(self) -> None:
        with self._lock:
            self._value = ""
            self._active = False

    def _check_active(self) -> None:
        if not self._active or self.expires_at <= utc_now():
            self._value = ""
            self._active = False
            raise SecretAccessError("Provider credential has expired or been revoked.")

    def __repr__(self) -> str:
        with self._lock:
            return f"ScopedCredential(resource={self.resource!r}, active={self._active})"


class SecretManager(Protocol):
    def get_scoped_credential(self, *, requester_id: str, resource: str, purpose: str, duration_seconds: int) -> ScopedCredential: ...


class EnvironmentSecretManager:
    """Development adapter; production should inject a managed secret-store implementation."""

    def __init__(self, resources: dict[str, str]) -> None:
        if any(not resource.strip() or not variable.strip() for resource, variable in resources.items()):
            raise ValueError("Secret resource and environment-variable names are required.")
        self._resources = dict(resources)

    def get_scoped_credential(self, *, requester_id: str, resource: str, purpose: str, duration_seconds: int) -> ScopedCredential:
        if (
            requester_id != "brain-provider-gateway"
            or purpose != "inference"
            or isinstance(duration_seconds, bool)
            or not isinstance(duration_seconds, int)
            or not 0 < duration_seconds <= 60
        ):
            raise SecretAccessError("Provider credential request is not authorized.")
        variable = self._resources.get(resource)
        if variable is None:
            raise SecretAccessError("Provider credential resource is not configured.")
        value = os.environ.get(variable)
        if not value:
            raise SecretAccessError("Provider credential is unavailable.")
        return ScopedCredential(value, resource, expires_at=utc_now() + timedelta(seconds=duration_seconds))


class ProviderAdapter(Protocol):
    provider_id: str

    def complete(self, request: ProviderRequest, credential: ScopedCredential) -> ProviderResponse: ...

    def health_check(self) -> str: ...
