from contextlib import contextmanager
from io import BytesIO
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from uuid import UUID

from ui.supabase_auth import SupabaseOwnerAuthenticator


OWNER_ID = UUID("080c2dc0-7332-4689-ade9-8a2229b2f4e3")
WORKSPACE_ID = UUID("2558d070-be78-4888-85e0-fb02975984ec")


class FakeConnection:
    def __init__(self, role: str | None) -> None:
        self.role = role
        self.query: str | None = None
        self.parameters: tuple[object, ...] | None = None

    def execute(self, query: str, parameters: tuple[object, ...]):
        self.query = query
        self.parameters = parameters
        return self

    def fetchone(self):
        return (self.role,) if self.role is not None else None


class FakeDatabase:
    def __init__(self, role: str | None) -> None:
        self.connection_value = FakeConnection(role)

    @contextmanager
    def connection(self):
        yield self.connection_value


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self) -> bytes:
        return self.payload


class SupabaseOwnerAuthenticatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = FakeDatabase("owner")
        self.authenticator = SupabaseOwnerAuthenticator(
            self.database,
            supabase_url="https://example.supabase.co",
            anon_key="public-anon-key",
            workspace_id=WORKSPACE_ID,
        )
        self.environ = {"HTTP_AUTHORIZATION": "Bearer valid-token"}

    @patch("ui.supabase_auth.urlopen")
    def test_valid_token_resolves_active_workspace_owner(self, urlopen) -> None:
        urlopen.return_value = FakeResponse({"id": str(OWNER_ID)})

        principal = self.authenticator(self.environ)

        self.assertIsNotNone(principal)
        self.assertEqual(principal.subject, str(OWNER_ID))
        self.assertEqual(
            principal.permissions,
            frozenset({
                "workspace:read",
                "workspace:write",
                "system:control",
                "enactor:execute",
                "treasury:manage",
            }),
        )
        self.assertIsNone(principal.approver_level)
        self.assertIn("status = 'active'", self.database.connection_value.query)
        self.assertEqual(
            self.database.connection_value.parameters,
            (WORKSPACE_ID, str(OWNER_ID)),
        )
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.supabase.co/auth/v1/user")
        self.assertEqual(request.get_header("Authorization"), "Bearer valid-token")

    @patch("ui.supabase_auth.urlopen")
    def test_missing_bearer_token_does_not_contact_supabase(self, urlopen) -> None:
        self.assertIsNone(self.authenticator({}))
        self.assertIsNone(
            self.authenticator({"HTTP_AUTHORIZATION": "Basic invalid"})
        )
        urlopen.assert_not_called()

    @patch("ui.supabase_auth.urlopen")
    def test_invalid_supabase_token_is_unauthenticated(self, urlopen) -> None:
        urlopen.side_effect = HTTPError(
            "https://example.supabase.co/auth/v1/user",
            401,
            "unauthorized",
            {},
            BytesIO(b'{"message":"invalid token"}'),
        )

        self.assertIsNone(self.authenticator(self.environ))

    @patch("ui.supabase_auth.urlopen")
    def test_user_without_active_membership_is_denied(self, urlopen) -> None:
        self.database.connection_value.role = None
        urlopen.return_value = FakeResponse({"id": str(OWNER_ID)})

        self.assertIsNone(self.authenticator(self.environ))

    @patch("ui.supabase_auth.urlopen")
    def test_user_id_must_be_a_valid_uuid(self, urlopen) -> None:
        urlopen.return_value = FakeResponse({"id": "not-a-user-id"})

        with self.assertRaisesRegex(ValueError, "invalid user ID"):
            self.authenticator(self.environ)


if __name__ == "__main__":
    unittest.main()
