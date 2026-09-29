"""Capability-based model profile registry and cost-aware fallback ordering."""

from __future__ import annotations

from .models import AgentDefinition, InferenceRequest, ModelProfile


class ModelRegistry:
    def __init__(self) -> None:
        self._profiles: dict[str, ModelProfile] = {}

    def register(self, profile: ModelProfile) -> None:
        if profile.profile_id in self._profiles:
            raise ValueError(f"Model profile already registered: {profile.profile_id}")
        self._profiles[profile.profile_id] = profile

    def get(self, profile_id: str) -> ModelProfile:
        try:
            return self._profiles[profile_id]
        except KeyError as error:
            raise KeyError(f"Unknown model profile: {profile_id}") from error

    def route(self, agent: AgentDefinition, request: InferenceRequest) -> tuple[ModelProfile, ...]:
        profiles = [
            profile for profile in self._profiles.values()
            if profile.profile_id in agent.allowed_models
            and request.operation in profile.capabilities
            and request.sector in profile.allowed_sectors
            and profile.context_window >= request.max_tokens
            and profile.currency == request.max_cost.currency
        ]
        if request.model_profile is not None:
            preferred = [profile for profile in profiles if profile.profile_id == request.model_profile]
            if not preferred:
                raise PermissionError("Requested model profile is not permitted for this inference.")
            profiles = preferred + [profile for profile in profiles if profile.profile_id != request.model_profile]
        profiles.sort(key=lambda profile: (
            profile.profile_id != request.model_profile if request.model_profile is not None else False,
            profile.cost_per_1k_input_tokens + profile.cost_per_1k_output_tokens,
            -profile.reliability_score,
            profile.profile_id,
        ))
        if not profiles:
            raise PermissionError("No model profile satisfies agent, sector, operation, and request policy.")
        return tuple(profiles)
