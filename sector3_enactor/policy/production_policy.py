"""Production safety policy used by staging and production release flows."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductionPolicy:
    require_approval_for_production: bool = True
    require_smoke_tests: bool = True
    require_release_lock: bool = True
    staging_only: bool = True

    def validate_release(self, *, environment: str, approval_id: str | None = None, smoke_tests_passed: bool = False) -> None:
        if environment.lower() == "production":
            if self.require_approval_for_production and not approval_id:
                raise PermissionError("Production release requires a bound approval ID.")
            if self.require_smoke_tests and not smoke_tests_passed:
                raise PermissionError("Production release requires passing smoke tests.")
            if self.require_release_lock:
                raise PermissionError("Production release requires a release lock; staged deploy is the safe default.")


__all__ = ["ProductionPolicy"]
