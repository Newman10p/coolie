"""Supabase Auth token verification and workspace permission resolution."""

from __future__ import annotations

import json
from collections.abc import Mapping
from contextlib import AbstractContextManager
from typing import Protocol
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
from uuid import UUID

from ui.owner_api import OwnerPrincipal
from sector3_enactor.models.approval import ApprovalLevel


class _MembershipResult(Protocol):
    def fetchone(self) -> tuple[str] | None: ...


class _DatabaseConnection(Protocol):
    def execute(
        self, query: str, parameters: tuple[UUID, str]
    ) -> _MembershipResult: ...


class _Database(Protocol):
    def connection(self) -> AbstractContextManager[_DatabaseConnection]: ...


class SupabaseOwnerAuthenticator:
    """Authenticate Supabase access tokens and resolve active workspace roles.

    Supabase Auth validates the token. The trusted backend database connection
    then resolves the caller's active role in the one configured workspace.
    """

    _ROLE_PERMISSIONS = {
        "owner": frozenset({
            "workspace:read",
            "workspace:write",
            "system:control",
            "enactor:execute",
            "treasury:manage",
        }),
        "admin": frozenset({
            "workspace:read",
            "workspace:write",
            "system:control",
            "enactor:execute",
            "treasury:manage",
        }),
        "operator": frozenset({
            "workspace:read",
            "workspace:write",
            "enactor:execute",
        }),
        "viewer": frozenset({"workspace:read"}),
    }
    _MAX_TOKEN_LENGTH = 16_384

    def __init__(
        self,
        database: _Database,
        *,
        supabase_url: str,
        anon_key: str,
        workspace_id: UUID,
        approval_levels: Mapping[str, ApprovalLevel] | None = None,
    ) -> None:
        base_url = supabase_url.rstrip("/")
        parsed_url = urlsplit(base_url)
        if parsed_url.scheme != "https" or not parsed_url.hostname or parsed_url.path:
            raise ValueError("A valid HTTPS Supabase project URL is required.")
        if not anon_key.strip():
            raise ValueError("The Supabase anon key is required for Auth token validation.")
        self._database = database
        self._auth_user_url = f"{base_url}/auth/v1/user"
        self._anon_key = anon_key
        self._workspace_id = UUID(str(workspace_id))
        self._approval_levels = dict(approval_levels or {})

    def __call__(self, environ: dict[str, object]) -> OwnerPrincipal | None:
        token = self._bearer_token(environ)
        if token is None:
            return None
        user_id = self._get_authenticated_user_id(token)
        if user_id is None:
            return None

        with self._database.connection() as connection:
            membership = connection.execute(
                """
                SELECT role
                FROM public.workspace_members
                WHERE workspace_id = %s AND user_id = %s AND status = 'active'
                """,
                (self._workspace_id, user_id),
            ).fetchone()
        if membership is None:
            return None

        role = membership[0]
        permissions = self._ROLE_PERMISSIONS.get(role)
        if permissions is None:
            raise ValueError(f"Unsupported active workspace role: {role!r}.")
        return OwnerPrincipal(
            subject=user_id,
            permissions=permissions,
            approver_level=self._approval_levels.get(user_id),
        )

    @classmethod
    def _bearer_token(cls, environ: dict[str, object]) -> str | None:
        authorization = environ.get("HTTP_AUTHORIZATION")
        if not isinstance(authorization, str):
            return None
        scheme, separator, token = authorization.partition(" ")
        token = token.strip()
        if (
            not separator
            or scheme.lower() != "bearer"
            or not token
            or len(token) > cls._MAX_TOKEN_LENGTH
            or any(character.isspace() for character in token)
        ):
            return None
        return token

    def _get_authenticated_user_id(self, token: str) -> str | None:
        request = Request(
            self._auth_user_url,
            headers={
                "apikey": self._anon_key,
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=5) as response:
                payload = json.loads(response.read())
        except HTTPError as error:
            if error.code in {401, 403}:
                return None
            raise
        if not isinstance(payload, dict) or not isinstance(payload.get("id"), str):
            raise ValueError("Supabase Auth returned an invalid user response.")
        try:
            return str(UUID(payload["id"]))
        except ValueError as error:
            raise ValueError("Supabase Auth returned an invalid user ID.") from error
