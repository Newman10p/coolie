-- Workspace-scoped persistence for non-Research/Enactor runtime state.
create table public.workspace_records (
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    record_type text not null,
    record_id text not null,
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (workspace_id, record_type, record_id)
);

create index workspace_records_type_created_idx
    on public.workspace_records (workspace_id, record_type, created_at);

create table public.workspace_events (
    event_sequence bigint generated always as identity primary key,
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    stream_name text not null,
    stream_key text not null,
    event_id text not null,
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    recorded_at timestamptz not null default now(),
    unique (workspace_id, stream_name, event_id)
);

create index workspace_events_stream_idx
    on public.workspace_events (workspace_id, stream_name, stream_key, event_sequence);

create table public.workspace_system_state (
    workspace_id uuid primary key references public.workspaces(id) on delete cascade,
    paused boolean not null default false,
    reason text,
    paused_at timestamptz,
    updated_at timestamptz not null default now(),
    check ((paused and reason is not null and paused_at is not null)
        or (not paused and reason is null and paused_at is null))
);

create table public.research_artifacts (
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    artifact_key text not null,
    content_hash text not null,
    content_type text not null,
    content bytea not null,
    created_at timestamptz not null default now(),
    primary key (workspace_id, artifact_key)
);

create table public.brain_budget_state (
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    agent_id text not null,
    task_id text not null,
    currency text not null check (currency ~ '^[A-Z]{3}$'),
    reserved numeric not null default 0 check (reserved >= 0),
    spent numeric not null default 0 check (spent >= 0),
    tokens_reserved bigint not null default 0 check (tokens_reserved >= 0),
    tokens_spent bigint not null default 0 check (tokens_spent >= 0),
    primary key (workspace_id, agent_id, task_id, currency)
);

create table public.brain_budget_reservations (
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    reservation_id text not null,
    agent_id text not null,
    task_id text not null,
    currency text not null check (currency ~ '^[A-Z]{3}$'),
    amount numeric not null check (amount > 0),
    tokens bigint not null check (tokens >= 0),
    created_at timestamptz not null default now(),
    primary key (workspace_id, reservation_id),
    foreign key (workspace_id, agent_id, task_id, currency)
        references public.brain_budget_state(workspace_id, agent_id, task_id, currency)
        on delete cascade
);

create table public.enactor_idempotency (
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    replay_key text not null,
    request_hash text not null,
    result jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (workspace_id, replay_key)
);

create table public.enactor_budget_ledgers (
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    execution_id text not null,
    limits jsonb not null check (jsonb_typeof(limits) = 'object'),
    currencies jsonb not null check (jsonb_typeof(currencies) = 'object'),
    spent jsonb not null check (jsonb_typeof(spent) = 'object'),
    reserved jsonb not null check (jsonb_typeof(reserved) = 'object'),
    warning_emitted boolean not null default false,
    exhausted boolean not null default false,
    updated_at timestamptz not null default now(),
    primary key (workspace_id, execution_id)
);

create trigger research_artifacts_append_only
    before update or delete on public.research_artifacts
    for each row execute function public.reject_immutable_record_change();

create trigger workspace_events_append_only
    before update or delete on public.workspace_events
    for each row execute function public.reject_immutable_record_change();

alter table public.workspace_records enable row level security;
create policy workspace_records_select_member on public.workspace_records
    for select to authenticated
    using (public.is_workspace_member(workspace_id));
revoke all on public.workspace_records from anon, authenticated;
grant select on public.workspace_records to authenticated;
grant all on public.workspace_records to service_role;

alter table public.workspace_events enable row level security;
create policy workspace_events_select_member on public.workspace_events
    for select to authenticated
    using (public.is_workspace_member(workspace_id));
revoke all on public.workspace_events from anon, authenticated;
grant select on public.workspace_events to authenticated;
grant all on public.workspace_events to service_role;
grant usage, select on sequence public.workspace_events_event_sequence_seq to service_role;

alter table public.workspace_system_state enable row level security;
create policy workspace_system_state_select_member on public.workspace_system_state
    for select to authenticated
    using (public.is_workspace_member(workspace_id));
revoke all on public.workspace_system_state from anon, authenticated;
grant select on public.workspace_system_state to authenticated;
grant all on public.workspace_system_state to service_role;

alter table public.research_artifacts enable row level security;
create policy research_artifacts_select_member on public.research_artifacts
    for select to authenticated
    using (public.is_workspace_member(workspace_id));
revoke all on public.research_artifacts from anon, authenticated;
grant select on public.research_artifacts to authenticated;
grant all on public.research_artifacts to service_role;

alter table public.brain_budget_state enable row level security;
create policy brain_budget_state_select_member on public.brain_budget_state
    for select to authenticated
    using (public.is_workspace_member(workspace_id));
revoke all on public.brain_budget_state from anon, authenticated;
grant select on public.brain_budget_state to authenticated;
grant all on public.brain_budget_state to service_role;

alter table public.brain_budget_reservations enable row level security;
create policy brain_budget_reservations_select_member on public.brain_budget_reservations
    for select to authenticated
    using (public.is_workspace_member(workspace_id));
revoke all on public.brain_budget_reservations from anon, authenticated;
grant select on public.brain_budget_reservations to authenticated;
grant all on public.brain_budget_reservations to service_role;

alter table public.enactor_idempotency enable row level security;
create policy enactor_idempotency_select_member on public.enactor_idempotency
    for select to authenticated
    using (public.is_workspace_member(workspace_id));
revoke all on public.enactor_idempotency from anon, authenticated;
grant select on public.enactor_idempotency to authenticated;
grant all on public.enactor_idempotency to service_role;

alter table public.enactor_budget_ledgers enable row level security;
create policy enactor_budget_ledgers_select_member on public.enactor_budget_ledgers
    for select to authenticated
    using (public.is_workspace_member(workspace_id));
revoke all on public.enactor_budget_ledgers from anon, authenticated;
grant select on public.enactor_budget_ledgers to authenticated;
grant all on public.enactor_budget_ledgers to service_role;
