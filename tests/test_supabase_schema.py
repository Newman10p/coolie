from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20261003000000_coolie_workspace_schema.sql"
HARDENING_MIGRATION = ROOT / "supabase/migrations/20261003000001_restrict_direct_authenticated_writes.sql"
PERSISTENCE_MIGRATION = ROOT / "supabase/migrations/20261003000002_persistence_adapter_support.sql"
RUNTIME_MIGRATION = ROOT / "supabase/migrations/20261003000003_full_runtime_persistence.sql"
APPEND_ONLY_MIGRATION = ROOT / "supabase/migrations/20261003000004_complete_append_only_guards.sql"
WALLET_MIGRATION = ROOT / "supabase/migrations/20261003000005_watch_only_wallet_registry.sql"


class SupabaseSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION.read_text(encoding="utf-8")

    def test_project_reference_and_region_are_configured(self):
        config = (ROOT / "supabase/config.toml").read_text(encoding="utf-8")
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn('project_id = "dgyhahgtocogfwljwioc"', config)
        self.assertIn("SUPABASE_REGION=us-east-1", env_example)
        self.assertIn("SUPABASE_URL=https://dgyhahgtocogfwljwioc.supabase.co", env_example)

    def test_business_tables_are_workspace_scoped_and_rls_protected(self):
        table_names = re.findall(
            r"create table public\.([a-z_]+)\s*\(", self.sql, flags=re.IGNORECASE
        )
        self.assertIn("workspaces", table_names)
        self.assertIn("workspace_members", table_names)
        self.assertGreaterEqual(len(table_names), 15)
        self.assertIn("alter table public.workspaces enable row level security", self.sql)
        self.assertIn("alter table public.workspace_members enable row level security", self.sql)

        for table in table_names:
            if table in {"workspaces", "workspace_members"}:
                continue
            with self.subTest(table=table):
                self.assertRegex(
                    self.sql,
                    rf"select public\.apply_workspace_rls\('public\.{table}'::regclass",
                )
                if table not in {"workspaces", "workspace_members"}:
                    definition = re.search(
                        rf"create table public\.{table}\s*\((.*?)\n\);",
                        self.sql,
                        flags=re.IGNORECASE | re.DOTALL,
                    )
                    self.assertIsNotNone(definition)
                    self.assertIn("workspace_id", definition.group(1))

    def test_audit_and_immutable_records_are_protected(self):
        self.assertIn("create trigger audit_events_append_only", self.sql)
        self.assertIn("create trigger evidence_records_append_only", self.sql)
        self.assertIn("create trigger research_reports_append_only", self.sql)
        self.assertIn("revoke all on public.workspaces, public.workspace_members from anon", self.sql)
        self.assertIn("values (\n    'coolie-artifacts',\n    'coolie-artifacts',\n    false", self.sql)
        self.assertNotRegex(self.sql, r"(?i)grant\s+all\s+.*\bto\s+anon\b")

    def test_followup_migration_revokes_direct_authenticated_domain_writes(self):
        hardening = HARDENING_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("from anon, authenticated", hardening)
        self.assertRegex(
            hardening,
            r"grant select on public\.research_missions[\s\S]*?to authenticated",
        )
        self.assertNotRegex(
            hardening,
            r"(?i)grant\s+(?:all|insert|update|delete).*to\s+authenticated",
        )

    def test_persistence_adapter_migration_preserves_workspace_and_append_only_boundaries(self):
        migration = PERSISTENCE_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("primary key (workspace_id, entity_type, entity_id)", migration)
        self.assertIn("primary key (workspace_id, artifact_key)", migration)
        self.assertIn("alter table public.enactor_records enable row level security", migration)
        self.assertIn("alter table public.enactor_artifacts enable row level security", migration)
        self.assertIn("revoke all on public.enactor_records from anon, authenticated", migration)
        self.assertIn("revoke all on public.enactor_artifacts from anon, authenticated", migration)
        self.assertIn("create trigger enactor_artifacts_append_only", migration)
        self.assertIn("create trigger research_mission_transitions_append_only", migration)

    def test_full_runtime_tables_are_workspace_scoped_and_read_only_to_authenticated(self):
        migration = RUNTIME_MIGRATION.read_text(encoding="utf-8")
        for table in (
            "workspace_records",
            "workspace_events",
            "workspace_system_state",
            "research_artifacts",
            "brain_budget_state",
            "brain_budget_reservations",
            "enactor_idempotency",
            "enactor_budget_ledgers",
        ):
            with self.subTest(table=table):
                self.assertIn(f"alter table public.{table} enable row level security", migration)
                self.assertIn(
                    f"revoke all on public.{table} from anon, authenticated",
                    migration,
                )
                self.assertRegex(
                    migration,
                    rf"grant all on public\.{table} to service_role",
                )
        self.assertIn("create trigger workspace_events_append_only", migration)
        self.assertIn("create trigger research_artifacts_append_only", migration)

    def test_append_only_records_cannot_be_deleted(self):
        migration = APPEND_ONLY_MIGRATION.read_text(encoding="utf-8")
        self.assertRegex(
            migration,
            r"before update or delete on public\.audit_events",
        )
        self.assertRegex(
            migration,
            r"before update or delete on public\.enactor_artifacts",
        )

    def test_wallet_registry_is_watch_only_and_withdrawals_are_non_executable(self):
        migration = WALLET_MIGRATION.read_text(encoding="utf-8")
        self.assertIn("check (purpose in ('profits', 'spending'))", migration)
        self.assertIn("check (custody = 'watch_only')", migration)
        self.assertIn("revoke all on public.wallet_accounts from anon, authenticated", migration)
        self.assertIn("grant all on public.wallet_accounts to service_role", migration)
        self.assertIn(
            "revoke all on public.wallet_account_events from anon, authenticated",
            migration,
        )
        self.assertIn(
            "before update or delete on public.wallet_account_events",
            migration,
        )
        self.assertIn("check (status = 'pending_review')", migration)
        self.assertIn(
            "before update or delete on public.wallet_withdrawal_requests",
            migration,
        )
        self.assertIn(
            "they are not signed, broadcast, approved, or executed by Coolie",
            migration,
        )


if __name__ == "__main__":
    unittest.main()
