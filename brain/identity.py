"""Agent registration and short-lived, task-scoped session credentials."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from hashlib import sha256
import hmac
import secrets
from threading import RLock

from research_room.models import Money

from .models import AgentDefinition, AgentSession, BrainOperation, SessionGrant, utc_now


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}

    def register(self, agent: AgentDefinition) -> None:
        if agent.agent_id in self._agents:
            raise ValueError(f"Agent already registered: {agent.agent_id}")
        self._agents[agent.agent_id] = agent

    def get(self, agent_id: str) -> AgentDefinition:
        try:
            agent = self._agents[agent_id]
        except KeyError as error:
            raise KeyError(f"Unknown agent: {agent_id}") from error
        if agent.status != "active":
            raise PermissionError(f"Agent is {agent.status}: {agent_id}")
        return agent

    def definitions(self) -> tuple[AgentDefinition, ...]:
        return tuple(self._agents.values())

    def set_status(self, agent_id: str, status: str) -> AgentDefinition:
        if status not in {"active", "paused", "revoked"}:
            raise ValueError("Agent status must be active, paused, or revoked.")
        try:
            agent = self._agents[agent_id]
        except KeyError as error:
            raise KeyError(f"Unknown agent: {agent_id}") from error
        updated = replace(agent, status=status)
        self._agents[agent_id] = updated
        return updated


class SessionManager:
    def __init__(self, *, maximum_lifetime_seconds: int = 3600) -> None:
        if isinstance(maximum_lifetime_seconds, bool) or not isinstance(maximum_lifetime_seconds, int) or maximum_lifetime_seconds <= 0:
            raise ValueError("maximum_lifetime_seconds must be a positive integer.")
        self._maximum_lifetime = maximum_lifetime_seconds
        self._sessions: dict[str, AgentSession] = {}
        self._token_hashes: dict[str, str] = {}
        self._lock = RLock()

    def create(
        self,
        agent: AgentDefinition,
        *,
        task_id: str,
        duration_seconds: int = 300,
        operations: frozenset[BrainOperation] | None = None,
        memory_namespaces: frozenset[str] | None = None,
        token_limit: int | None = None,
        cost_limit: Money | None = None,
    ) -> SessionGrant:
        if not task_id.strip():
            raise ValueError("task_id is required.")
        if isinstance(duration_seconds, bool) or not isinstance(duration_seconds, int) or not 0 < duration_seconds <= self._maximum_lifetime:
            raise ValueError("Session duration exceeds the configured lifetime.")
        selected_operations = agent.allowed_operations if operations is None else operations
        selected_namespaces = agent.allowed_memory_namespaces if memory_namespaces is None else memory_namespaces
        if not selected_operations or not selected_operations <= agent.allowed_operations:
            raise PermissionError("Session operations exceed agent permissions.")
        if not selected_namespaces <= agent.allowed_memory_namespaces:
            raise PermissionError("Session memory namespaces exceed agent permissions.")
        effective_tokens = agent.max_tokens_per_task if token_limit is None else token_limit
        if isinstance(effective_tokens, bool) or not isinstance(effective_tokens, int) or not 0 < effective_tokens <= agent.max_tokens_per_task:
            raise PermissionError("Session token limit exceeds agent permissions.")
        effective_cost = agent.max_cost_per_task if cost_limit is None else cost_limit
        if effective_cost.currency != agent.max_cost_per_task.currency or effective_cost.amount > agent.max_cost_per_task.amount:
            raise PermissionError("Session cost limit exceeds agent permissions.")
        token = secrets.token_urlsafe(32)
        session = AgentSession(
            secrets.token_urlsafe(24),
            agent.agent_id,
            agent.sector,
            task_id,
            selected_operations,
            selected_namespaces,
            effective_tokens,
            effective_cost,
            utc_now() + timedelta(seconds=duration_seconds),
        )
        with self._lock:
            self._sessions[session.session_id] = session
            self._token_hashes[session.session_id] = self._hash(token)
        return SessionGrant(session, token)

    def validate(self, session_id: str, token: str) -> AgentSession:
        if not isinstance(session_id, str) or not isinstance(token, str) or not 32 <= len(token) <= 256:
            raise PermissionError("Invalid agent session.")
        with self._lock:
            session = self._sessions.get(session_id)
            token_hash = self._token_hashes.get(session_id)
            if session is None or token_hash is None or not hmac.compare_digest(token_hash, self._hash(token)):
                raise PermissionError("Invalid agent session.")
            if session.status != "active":
                raise PermissionError(f"Agent session is {session.status}.")
            if session.expires_at <= utc_now():
                self._sessions[session_id] = AgentSession(
                    session.session_id, session.agent_id, session.sector, session.task_id,
                    session.allowed_operations, session.allowed_memory_namespaces,
                    session.token_limit, session.cost_limit, session.expires_at, "expired",
                )
                raise PermissionError("Agent session has expired.")
            return session

    def revoke_all(self) -> tuple[AgentSession, ...]:
        with self._lock:
            revoked = []
            for session_id, session in self._sessions.items():
                self._token_hashes.pop(session_id, None)
                if session.status != "active":
                    continue
                item = AgentSession(
                    session.session_id, session.agent_id, session.sector, session.task_id,
                    session.allowed_operations, session.allowed_memory_namespaces,
                    session.token_limit, session.cost_limit, session.expires_at, "revoked",
                )
                self._sessions[session_id] = item
                revoked.append(item)
            return tuple(revoked)

    def revoke_agent(self, agent_id: str) -> tuple[AgentSession, ...]:
        with self._lock:
            revoked = []
            for session_id, session in self._sessions.items():
                if session.agent_id != agent_id:
                    continue
                self._token_hashes.pop(session_id, None)
                if session.status != "active":
                    continue
                item = AgentSession(
                    session.session_id, session.agent_id, session.sector, session.task_id,
                    session.allowed_operations, session.allowed_memory_namespaces,
                    session.token_limit, session.cost_limit, session.expires_at, "revoked",
                )
                self._sessions[session_id] = item
                revoked.append(item)
            return tuple(revoked)

    def revoke(self, session_id: str) -> AgentSession:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"Unknown session: {session_id}")
            revoked = AgentSession(
                session.session_id, session.agent_id, session.sector, session.task_id,
                session.allowed_operations, session.allowed_memory_namespaces,
                session.token_limit, session.cost_limit, session.expires_at, "revoked",
            )
            self._sessions[session_id] = revoked
            self._token_hashes.pop(session_id, None)
            return revoked

    @staticmethod
    def _hash(token: str) -> str:
        return sha256(token.encode("utf-8")).hexdigest()
