-- Durable records used by server-side repository adapters.
alter table public.audit_events
    add column connector_account text,
    add column external_operation_id text;

create table public.enactor_records (
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    entity_type text not null,
    entity_id text not null,
    status text,
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (workspace_id, entity_type, entity_id)
);

create table public.enactor_artifacts (
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    artifact_key text not null,
    content_hash text not null,
    content_type text not null,
    content text not null,
    created_at timestamptz not null default now(),
    primary key (workspace_id, artifact_key)
);

create trigger enactor_artifacts_append_only
    before update on public.enactor_artifacts
    for each row execute function public.reject_immutable_record_change();

create index enactor_records_type_created_idx
    on public.enactor_records (workspace_id, entity_type, created_at);

create index enactor_artifacts_workspace_idx
    on public.enactor_artifacts (workspace_id, created_at);

create table public.research_mission_transitions (
    transition_id bigint generated always as identity primary key,
    workspace_id uuid not null,
    mission_id text not null,
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    recorded_at timestamptz not null default now(),
    foreign key (workspace_id, mission_id)
        references public.research_missions(workspace_id, mission_id) on delete cascade
);

create index research_mission_transitions_mission_idx
    on public.research_mission_transitions (workspace_id, mission_id, transition_id);

create trigger research_mission_transitions_append_only
    before update on public.research_mission_transitions
    for each row execute function public.reject_immutable_record_change();

alter table public.enactor_records enable row level security;
create policy enactor_records_select_member on public.enactor_records
    for select to authenticated
    using (public.is_workspace_member(workspace_id));
revoke all on public.enactor_records from anon, authenticated;
grant select on public.enactor_records to authenticated;
grant all on public.enactor_records to service_role;

alter table public.enactor_artifacts enable row level security;
create policy enactor_artifacts_select_member on public.enactor_artifacts
    for select to authenticated
    using (public.is_workspace_member(workspace_id));
revoke all on public.enactor_artifacts from anon, authenticated;
grant select on public.enactor_artifacts to authenticated;
grant all on public.enactor_artifacts to service_role;

alter table public.research_mission_transitions enable row level security;
create policy research_mission_transitions_select_member on public.research_mission_transitions
    for select to authenticated
    using (public.is_workspace_member(workspace_id));
revoke all on public.research_mission_transitions from anon, authenticated;
grant select on public.research_mission_transitions to authenticated;
grant all on public.research_mission_transitions to service_role;
grant usage, select on sequence public.research_mission_transitions_transition_id_seq
    to service_role;
