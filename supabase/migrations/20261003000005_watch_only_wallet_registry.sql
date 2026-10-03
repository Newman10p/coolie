-- Store public wallet metadata only. Coolie never stores signing keys or submits transactions.
create table public.wallet_accounts (
    workspace_id uuid not null references public.workspaces(id) on delete cascade,
    wallet_id uuid not null default pg_catalog.gen_random_uuid(),
    purpose text not null check (purpose in ('profits', 'spending')),
    label text not null check (length(trim(label)) between 1 and 80),
    network text not null check (network ~ '^[a-z0-9][a-z0-9-]{1,63}$'),
    asset text not null check (asset ~ '^[A-Z0-9]{2,16}$'),
    address text not null check (address ~ '^[A-Za-z0-9]{20,160}$'),
    created_by uuid not null references auth.users(id) on delete restrict,
    updated_by uuid references auth.users(id) on delete restrict,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    status text not null default 'active' check (status in ('active', 'inactive')),
    custody text not null default 'watch_only' check (custody = 'watch_only'),
    primary key (workspace_id, wallet_id)
);

create unique index wallet_accounts_one_active_purpose_asset
    on public.wallet_accounts (workspace_id, purpose, network, asset)
    where status = 'active';
create unique index wallet_accounts_unique_active_address
    on public.wallet_accounts (workspace_id, network, asset, address)
    where status = 'active';

create table public.wallet_account_events (
    workspace_id uuid not null,
    event_id bigint generated always as identity,
    wallet_id uuid not null,
    action text not null check (action in ('registered', 'updated', 'deactivated')),
    actor_id uuid not null references auth.users(id) on delete restrict,
    details jsonb not null check (jsonb_typeof(details) = 'object'),
    recorded_at timestamptz not null default now(),
    primary key (workspace_id, event_id),
    foreign key (workspace_id, wallet_id)
        references public.wallet_accounts(workspace_id, wallet_id)
        on delete restrict
);

create index wallet_account_events_wallet_order
    on public.wallet_account_events (workspace_id, wallet_id, event_id);

create trigger wallet_account_events_append_only
    before update or delete on public.wallet_account_events
    for each row execute function public.reject_immutable_record_change();

create table public.wallet_withdrawal_requests (
    workspace_id uuid not null,
    request_id uuid not null default pg_catalog.gen_random_uuid(),
    wallet_id uuid not null,
    destination_address text not null check (destination_address ~ '^[A-Za-z0-9]{20,160}$'),
    network text not null check (network ~ '^[a-z0-9][a-z0-9-]{1,63}$'),
    asset text not null check (asset ~ '^[A-Z0-9]{2,16}$'),
    amount numeric(36, 18) not null check (amount > 0),
    memo text check (memo is null or length(trim(memo)) between 1 and 280),
    requested_by uuid not null references auth.users(id) on delete restrict,
    requested_at timestamptz not null default now(),
    status text not null default 'pending_review'
        check (status = 'pending_review'),
    primary key (workspace_id, request_id),
    foreign key (workspace_id, wallet_id)
        references public.wallet_accounts(workspace_id, wallet_id)
        on delete restrict
);

create index wallet_withdrawal_requests_workspace_requested
    on public.wallet_withdrawal_requests (workspace_id, requested_at desc);

create trigger wallet_withdrawal_requests_append_only
    before update or delete on public.wallet_withdrawal_requests
    for each row execute function public.reject_immutable_record_change();

alter table public.wallet_accounts enable row level security;
create policy wallet_accounts_select_member on public.wallet_accounts
    for select to authenticated
    using (public.is_workspace_member(workspace_id));
revoke all on public.wallet_accounts from anon, authenticated;
grant select on public.wallet_accounts to authenticated;
grant all on public.wallet_accounts to service_role;

alter table public.wallet_account_events enable row level security;
create policy wallet_account_events_select_member on public.wallet_account_events
    for select to authenticated
    using (public.is_workspace_member(workspace_id));
revoke all on public.wallet_account_events from anon, authenticated;
grant select on public.wallet_account_events to authenticated;
grant all on public.wallet_account_events to service_role;
grant usage, select on sequence public.wallet_account_events_event_id_seq to service_role;

alter table public.wallet_withdrawal_requests enable row level security;
create policy wallet_withdrawal_requests_select_member
    on public.wallet_withdrawal_requests
    for select to authenticated
    using (public.is_workspace_member(workspace_id));
revoke all on public.wallet_withdrawal_requests from anon, authenticated;
grant select on public.wallet_withdrawal_requests to authenticated;
grant all on public.wallet_withdrawal_requests to service_role;

comment on table public.wallet_accounts is
    'Watch-only public crypto wallet addresses; never stores private keys, balances, or transaction authority.';
comment on table public.wallet_withdrawal_requests is
    'Immutable requests for manual review; they are not signed, broadcast, approved, or executed by Coolie.';
