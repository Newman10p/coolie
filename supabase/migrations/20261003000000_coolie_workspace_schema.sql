-- Initial durable schema for Coolie's Supabase project.
-- All business records are scoped to a workspace and protected by RLS.

create table public.workspaces (
    id uuid primary key default pg_catalog.gen_random_uuid(),
    name text not null check (length(trim(name)) between 1 and 120),
    owner_user_id uuid not null references auth.users(id) on delete restrict,
    created_at timestamptz not null default now(),
    unique (id, owner_user_id)
);

create table public.workspace_members (
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    role text not null check (role in ('owner', 'admin', 'operator', 'viewer')),
    status text not null default 'active' check (status in ('active', 'revoked')),
    created_at timestamptz not null default now(),
    primary key (workspace_id, user_id)
);

create index workspace_members_user_idx
    on public.workspace_members (user_id, workspace_id)
    where status = 'active';

create or replace function public.is_workspace_member(target_workspace uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select exists (
        select 1
        from public.workspace_members as member
        where member.workspace_id = target_workspace
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    );
$$;

create or replace function public.can_write_workspace(target_workspace uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select exists (
        select 1
        from public.workspace_members as member
        where member.workspace_id = target_workspace
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'operator')
    );
$$;

create or replace function public.can_manage_workspace(target_workspace uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select exists (
        select 1
        from public.workspace_members as member
        where member.workspace_id = target_workspace
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin')
    );
$$;

create or replace function public.is_workspace_member_path(target_workspace text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select exists (
        select 1
        from public.workspace_members as member
        where member.workspace_id::text = target_workspace
          and member.user_id = (select auth.uid())
          and member.status = 'active'
    );
$$;

create or replace function public.can_write_workspace_path(target_workspace text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select exists (
        select 1
        from public.workspace_members as member
        where member.workspace_id::text = target_workspace
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin', 'operator')
    );
$$;

create or replace function public.can_manage_workspace_path(target_workspace text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select exists (
        select 1
        from public.workspace_members as member
        where member.workspace_id::text = target_workspace
          and member.user_id = (select auth.uid())
          and member.status = 'active'
          and member.role in ('owner', 'admin')
    );
$$;

create or replace function public.create_owner_workspace(workspace_name text)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
    new_workspace_id uuid;
    current_user_id uuid := auth.uid();
begin
    if current_user_id is null then
        raise exception 'Authentication is required to create a workspace.';
    end if;
    if workspace_name is null or length(trim(workspace_name)) not between 1 and 120 then
        raise exception 'Workspace name must contain 1 to 120 characters.';
    end if;

    insert into public.workspaces (name, owner_user_id)
    values (trim(workspace_name), current_user_id)
    returning id into new_workspace_id;

    insert into public.workspace_members (workspace_id, user_id, role)
    values (new_workspace_id, current_user_id, 'owner');

    return new_workspace_id;
end;
$$;

revoke all on function public.is_workspace_member(uuid) from public, anon;
revoke all on function public.can_write_workspace(uuid) from public, anon;
revoke all on function public.can_manage_workspace(uuid) from public, anon;
revoke all on function public.is_workspace_member_path(text) from public, anon;
revoke all on function public.can_write_workspace_path(text) from public, anon;
revoke all on function public.can_manage_workspace_path(text) from public, anon;
revoke all on function public.create_owner_workspace(text) from public, anon;
grant execute on function public.is_workspace_member(uuid) to authenticated, service_role;
grant execute on function public.can_write_workspace(uuid) to authenticated, service_role;
grant execute on function public.can_manage_workspace(uuid) to authenticated, service_role;
grant execute on function public.is_workspace_member_path(text) to authenticated, service_role;
grant execute on function public.can_write_workspace_path(text) to authenticated, service_role;
grant execute on function public.can_manage_workspace_path(text) to authenticated, service_role;
grant execute on function public.create_owner_workspace(text) to authenticated;

create table public.research_missions (
    mission_id text not null,
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    status text not null,
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (workspace_id, mission_id)
);

create index research_missions_workspace_created_idx
    on public.research_missions (workspace_id, created_at desc);

create table public.research_tasks (
    task_id text not null,
    workspace_id uuid not null,
    mission_id text not null,
    status text not null,
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (workspace_id, task_id),
    unique (workspace_id, task_id, mission_id),
    foreign key (workspace_id, mission_id)
        references public.research_missions(workspace_id, mission_id) on delete cascade
);

create index research_tasks_mission_idx
    on public.research_tasks (workspace_id, mission_id, created_at);

create table public.source_snapshots (
    snapshot_id text not null,
    workspace_id uuid not null,
    mission_id text not null,
    task_id text not null,
    source_reference text not null,
    retrieved_at timestamptz not null,
    content_hash text not null,
    artifact_key text not null,
    source_quality double precision not null check (source_quality between 0 and 1),
    payload jsonb not null default '{}'::jsonb check (jsonb_typeof(payload) = 'object'),
    primary key (workspace_id, snapshot_id),
    unique (workspace_id, artifact_key),
    foreign key (workspace_id, mission_id)
        references public.research_missions(workspace_id, mission_id) on delete cascade,
    foreign key (workspace_id, task_id, mission_id)
        references public.research_tasks(workspace_id, task_id, mission_id) on delete cascade
);

create table public.evidence_records (
    evidence_id text not null,
    workspace_id uuid not null,
    mission_id text not null,
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    created_at timestamptz not null default now(),
    primary key (workspace_id, evidence_id),
    foreign key (workspace_id, mission_id)
        references public.research_missions(workspace_id, mission_id) on delete cascade
);

create index evidence_records_mission_idx
    on public.evidence_records (workspace_id, mission_id, created_at);

create table public.opportunities (
    opportunity_id text not null,
    workspace_id uuid not null,
    mission_id text not null,
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    created_at timestamptz not null default now(),
    primary key (workspace_id, opportunity_id),
    foreign key (workspace_id, mission_id)
        references public.research_missions(workspace_id, mission_id) on delete cascade
);

create table public.research_reports (
    report_id text not null,
    workspace_id uuid not null,
    mission_id text not null,
    created_at timestamptz not null default now(),
    artifact_key text not null,
    content_hash text not null,
    payload jsonb not null default '{}'::jsonb check (jsonb_typeof(payload) = 'object'),
    primary key (workspace_id, report_id),
    unique (workspace_id, artifact_key),
    foreign key (workspace_id, mission_id)
        references public.research_missions(workspace_id, mission_id) on delete cascade
);

create table public.finance_assessments (
    assessment_id text not null,
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    status text not null,
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    created_at timestamptz not null default now(),
    primary key (workspace_id, assessment_id)
);

create table public.evolver_assessments (
    request_id text not null,
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    created_at timestamptz not null default now(),
    primary key (workspace_id, request_id)
);

create table public.enactor_executions (
    execution_id text not null,
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    status text not null,
    plan_hash text,
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (workspace_id, execution_id)
);

create table public.enactor_approvals (
    approval_id text not null,
    workspace_id uuid not null,
    execution_id text not null,
    status text not null,
    decided_by uuid references auth.users(id) on delete restrict,
    decided_at timestamptz,
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    created_at timestamptz not null default now(),
    primary key (workspace_id, approval_id),
    foreign key (workspace_id, execution_id)
        references public.enactor_executions(workspace_id, execution_id) on delete cascade
);

create table public.audit_events (
    event_id bigint generated always as identity primary key,
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    sequence bigint not null check (sequence >= 0),
    event_type text not null,
    business_id text not null,
    execution_id text,
    mission_id text,
    task_id text,
    agent_id text,
    tool text,
    approval_id text,
    payload_hash text not null,
    previous_hash text not null,
    event_hash text not null,
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    recorded_at timestamptz not null default now(),
    unique (workspace_id, sequence),
    unique (workspace_id, event_hash)
);

create index audit_events_workspace_time_idx
    on public.audit_events (workspace_id, recorded_at desc);
create index audit_events_execution_idx
    on public.audit_events (workspace_id, execution_id, sequence)
    where execution_id is not null;

create table public.operational_snapshots (
    snapshot_id text not null,
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    generated_at timestamptz not null default now(),
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    primary key (workspace_id, snapshot_id)
);

create table public.reliability_incidents (
    incident_id text not null,
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    severity text not null,
    source text not null,
    summary text not null,
    payload jsonb not null default '{}'::jsonb check (jsonb_typeof(payload) = 'object'),
    created_at timestamptz not null default now(),
    primary key (workspace_id, incident_id)
);

create table public.sector_configurations (
    version text not null,
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    payload jsonb not null check (jsonb_typeof(payload) = 'object'),
    created_at timestamptz not null default now(),
    primary key (workspace_id, version)
);

create or replace function public.reject_immutable_record_change()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    raise exception '% records are append-only.', tg_table_name;
end;
$$;

create trigger audit_events_append_only
    before update on public.audit_events
    for each row execute function public.reject_immutable_record_change();
create trigger evidence_records_append_only
    before update on public.evidence_records
    for each row execute function public.reject_immutable_record_change();
create trigger research_reports_append_only
    before update on public.research_reports
    for each row execute function public.reject_immutable_record_change();

alter table public.workspaces enable row level security;
alter table public.workspace_members enable row level security;

create policy workspaces_select_member on public.workspaces
    for select to authenticated
    using (public.is_workspace_member(id));

create policy workspace_members_select_member on public.workspace_members
    for select to authenticated
    using (public.is_workspace_member(workspace_id));

create or replace function public.apply_workspace_rls(target_table regclass, append_only boolean default false)
returns void
language plpgsql
set search_path = ''
as $$
declare
    table_name text := target_table::text;
begin
    execute format('alter table %s enable row level security', target_table);
    execute format(
        'create policy %I on %s for select to authenticated using (public.is_workspace_member(workspace_id))',
        table_name || '_select_member',
        target_table
    );
    execute format(
        'create policy %I on %s for insert to authenticated with check (public.can_write_workspace(workspace_id))',
        table_name || '_insert_writer',
        target_table
    );
    if not append_only then
        execute format(
            'create policy %I on %s for update to authenticated using (public.can_write_workspace(workspace_id)) with check (public.can_write_workspace(workspace_id))',
            table_name || '_update_writer',
            target_table
        );
        execute format(
            'create policy %I on %s for delete to authenticated using (public.can_write_workspace(workspace_id))',
            table_name || '_delete_writer',
            target_table
        );
    end if;
end;
$$;

revoke all on function public.apply_workspace_rls(regclass, boolean)
    from public, anon, authenticated, service_role;

select public.apply_workspace_rls('public.research_missions'::regclass);
select public.apply_workspace_rls('public.research_tasks'::regclass);
select public.apply_workspace_rls('public.source_snapshots'::regclass, true);
select public.apply_workspace_rls('public.evidence_records'::regclass, true);
select public.apply_workspace_rls('public.opportunities'::regclass);
select public.apply_workspace_rls('public.research_reports'::regclass, true);
select public.apply_workspace_rls('public.finance_assessments'::regclass);
select public.apply_workspace_rls('public.evolver_assessments'::regclass);
select public.apply_workspace_rls('public.enactor_executions'::regclass);
select public.apply_workspace_rls('public.enactor_approvals'::regclass);
select public.apply_workspace_rls('public.audit_events'::regclass, true);
select public.apply_workspace_rls('public.operational_snapshots'::regclass, true);
select public.apply_workspace_rls('public.reliability_incidents'::regclass);
select public.apply_workspace_rls('public.sector_configurations'::regclass, true);

revoke all on public.workspaces, public.workspace_members from anon;
revoke all on public.research_missions, public.research_tasks, public.source_snapshots,
    public.evidence_records, public.opportunities, public.research_reports,
    public.finance_assessments, public.evolver_assessments, public.enactor_executions,
    public.enactor_approvals, public.audit_events, public.operational_snapshots,
    public.reliability_incidents, public.sector_configurations from anon;
revoke all on public.source_snapshots, public.evidence_records, public.research_reports,
    public.audit_events, public.operational_snapshots, public.sector_configurations
    from authenticated;

grant select on public.workspaces, public.workspace_members to authenticated;
grant select on public.research_missions, public.research_tasks, public.source_snapshots,
    public.evidence_records, public.opportunities, public.research_reports,
    public.finance_assessments, public.evolver_assessments, public.enactor_executions,
    public.enactor_approvals, public.audit_events, public.operational_snapshots,
    public.reliability_incidents, public.sector_configurations to authenticated;

grant all on public.research_missions, public.research_tasks, public.source_snapshots,
    public.evidence_records, public.opportunities, public.research_reports,
    public.finance_assessments, public.evolver_assessments, public.enactor_executions,
    public.enactor_approvals, public.audit_events, public.operational_snapshots,
    public.reliability_incidents, public.sector_configurations to service_role;
grant usage, select on sequence public.audit_events_event_id_seq to service_role;
grant execute on function public.create_owner_workspace(text) to authenticated;
grant execute on function public.reject_immutable_record_change() to authenticated, service_role;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'coolie-artifacts',
    'coolie-artifacts',
    false,
    52428800,
    array['application/json', 'text/plain', 'application/pdf', 'image/png', 'image/jpeg']
)
on conflict (id) do nothing;

create policy coolie_artifacts_read_member on storage.objects
    for select to authenticated
    using (
        bucket_id = 'coolie-artifacts'
        and public.is_workspace_member_path((storage.foldername(name))[1])
    );

create policy coolie_artifacts_insert_writer on storage.objects
    for insert to authenticated
    with check (
        bucket_id = 'coolie-artifacts'
        and public.can_write_workspace_path((storage.foldername(name))[1])
    );

create policy coolie_artifacts_update_writer on storage.objects
    for update to authenticated
    using (
        bucket_id = 'coolie-artifacts'
        and public.can_write_workspace_path((storage.foldername(name))[1])
    )
    with check (
        bucket_id = 'coolie-artifacts'
        and public.can_write_workspace_path((storage.foldername(name))[1])
    );

create policy coolie_artifacts_delete_admin on storage.objects
    for delete to authenticated
    using (
        bucket_id = 'coolie-artifacts'
        and public.can_manage_workspace_path((storage.foldername(name))[1])
    );
