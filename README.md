# Coolie

Coolie is an AI-operated business workroom built around a simple boundary: the owner interface presents information and captures intent, while backend services retain responsibility for policy, financial calculations, authorization, compliance, approval validation, execution, and audit records.

The repository contains early, standard-library Python implementations of Coolie's core domains, a shared in-process reliability layer, and a responsive owner-workroom UI. It is a development foundation, not a production-ready operating system: external provider integrations, durable infrastructure, a production owner API, and deployment controls still need to be supplied and validated.

## Product model

The owner works through the **Orchestrator**, which coordinates decisions and bounded mandates across specialist domains:

| Domain | Responsibility |
| --- | --- |
| **Brain** | Provider-neutral model routing, scoped agent sessions, context and memory, delegation, usage limits, and inference audit records. |
| **Research Room** | Read-only missions, dependency-aware research work, evidence and source records, opportunity evaluation, and internal recommendations. |
| **Finance & Activation** | Assessment of proposed spend, expected revenue, margin, confidence, risk, budget limits, and activation recommendations. It does not control a live wallet or independently authorize spending. |
| **Enactor** | Compiles and runs approval-bound plans through a constrained tool gateway, with budgets, policy checks, state tracking, and execution audit records. |
| **Evolver** | Assesses capability gaps for proposed business domains and produces extension plans, required assets, and validation steps. It does not itself make an extension production-live. |
| **Report Collector** | Collects component and sector health into operational snapshots and reports without changing the state it observes. |
| **Reliability layer** | Shared readiness, heartbeat, incident/log records, dependency health, and emergency pause/resume controls for composed services. |

Architecture documents use different sector numbers in places. This README uses domain names to avoid confusing role labels with ordinal numbering. The Orchestrator is the owner-facing executive control plane, not an additional specialist department.

## Safety and authority boundaries

- A recommendation, forecast, or proposed plan is not an approval or proof of available funds.
- The UI can display and submit owner intent, but it is not an authentication or authorization boundary.
- The Research Room is read-only and cannot purchase, publish, message customers, transfer money, or invoke external Enactor actions.
- Optional Research Room MCP resources use explicit read-only Firecrawl, OpenSearch, and Playwright tools; the browser requires an operator-supplied host allowlist.
- The Finance & Activation service returns an assessment; it does not connect to a wallet, reconcile a ledger, or execute an investment.
- Enactor actions are mediated by its policy, approval, budget, and tool-gateway layers. Real external connectors and operational credentials must be configured separately.
- Emergency pause blocks new work only where services share the configured reliability runtime. It does not undo an action already in flight.
- Provider credentials and production secrets are deployment responsibilities. Do not put provider keys, payment credentials, or other secrets in the browser or repository.

## Repository map

```text
brain/                 Intelligence, provider boundary, sessions, memory, and inference
research_room/         Research missions, evidence, planning, and recommendations
orchestrator/           Owner objectives, decisions, policy gates, and mandates
money_calculator/       Finance and activation assessment
sector3_enactor/        Approval-bound plan execution and tool gateway
evolver/                Capability-expansion assessment
report_collector/       Operational snapshots and component reports
reliability/            Shared health, heartbeat, incident, and failsafe primitives
coolie_runtime.py       Composition root for the seven domains and shared failsafe
src/                    React owner workroom and screen components
ui/                     Static preview server and authenticated owner API adapter
tests/                  Python unittest suite
migrations/             Sector-specific schema artifacts where present
```

Each domain has its own models, controller/service logic, and in several cases a small HTTP-style or WSGI API. The React workroom is the primary UI; it is separate from the Python domain services and must use an authenticated same-origin API adapter for live data or actions.

## Local development

The Python packages require Python 3.11 or newer and declare their runtime dependencies in `pyproject.toml`. The frontend uses Node.js and npm. From the repository root:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
npm ci
npm run build
```

### Windows desktop download

For a single-file Windows install, use the [latest Coolie.exe release](https://github.com/Newman10p/coolie/releases/latest/download/Coolie.exe). On first launch, the app opens its local setup page, saves Supabase/provider settings under the current Windows user profile, and uses the computer's existing default browser. The executable bundles the Python runtime and built UI: users do not need to install Python, Node.js, npm, or a local database. Internet access, an existing configured Supabase project, and an existing Supabase owner/workspace membership are still required.

The downloadable file is published by [`.github/workflows/build-desktop.yml`](./.github/workflows/build-desktop.yml) when a `v*` version tag is pushed. Until the first tagged release is published, the link points to the GitHub latest-release asset location and no executable has been published there. The workflow also makes the Windows executable available as a build artifact for manual runs.

On first run, enter the Supabase project URL, region, public anon/publishable key, database password, and workspace UUID in the setup page. These values are stored in a settings file in the user's application-data directory (on Windows, `%LOCALAPPDATA%\\Coolie\\settings.env`). The desktop server binds only to `127.0.0.1`; setup writes are restricted to local-origin requests and private configuration values are not returned to the browser. The file is protected by the current user's local profile permissions, not separately encrypted; use a trusted, password-protected computer account. Do not enter a service-role key. The anon key is public and is used by the Supabase Auth client; the database password stays server-side. Provider fields are optional and remain inactive unless a separately configured service factory enables their corresponding integration.

Supabase does not issue a temporary/dummy password through this client flow. After setup, use **Set first password / Forgot password** on the sign-in screen. Supabase emails an expiring, identity-verified recovery link; the owner then chooses their actual password in Coolie. In Supabase Auth URL Configuration, add `http://127.0.0.1:4173` to the allowed redirect URLs and ensure the project's email provider can deliver the recovery email. This avoids creating or transmitting a shared temporary password.

The desktop bundle runs the currently supported local integration: the built owner-workroom UI and the Supabase-authenticated, watch-only wallet API. It does **not** turn preview panels into live sector services, voice interaction, or autonomous control. The other APIs continue to return explicit unavailable responses until a deployment service factory configures the seven-sector graph, model/provider integrations, policies, and any MCP connectors. Keys collected for optional research integrations are stored for that future configuration but do not activate MCP servers by themselves. Coolie therefore does not request a model/voice-provider key in this setup flow: there is no live conversational provider wired to use one yet. Do not use the preview UI as an indication that unconfigured sectors are operational.

To run the React development UI and local static preview server in separate terminals:

```bash
python -m ui.demo_server
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Vite dev server proxies `/api` to the local server on port `4173`; that server serves the built app and returns an explicit `503` for API routes. The static preview does not create or fabricate backend data. To serve the production build locally, run `npm run build` and then `python -m ui.demo_server`; the preview is at [http://localhost:4173](http://localhost:4173).

The replacement interface keeps its supplied design-prototype content clearly marked as preview data. When a live authenticated backend is connected, the status strip reports actual sector readiness and Research Mission Control switches to real persisted Research Room missions. Mission creation is submitted to the backend and does not itself start research or execute tools. Other screens remain design-preview panels until their corresponding live read models and safe actions are implemented. The Orchestrator voice panel is still a local interface demonstration; no transcription or chat service is connected.

### Research Room MCP resources

[`research_room/mcp_resources.py`](./research_room/mcp_resources.py) provides a stdio MCP client and a `ResearchMCPBridge` which can be registered as the existing read-only `search` connector by the deployment-owned service factory. It invokes only `firecrawl_search`/`firecrawl_scrape`, OpenSearch `SearchIndexTool`, and Playwright `browser_navigate`/`browser_snapshot`; it does not expose Firecrawl feedback/other tools, OpenSearch mutations, or browser clicks, typing, form submission, or downloads. The combined connector requires missions to allow both `web` and `internal` source types, so the local OpenSearch index cannot be queried under a web-only source policy. Results are bounded, prompt-injection-like text is sanitized, and the browser only visits discovered URLs whose hosts match the configured allowlist.

The bridge expects these upstream open-source servers:

- [Firecrawl MCP server](https://github.com/firecrawl/firecrawl-mcp-server), launched with `npx -y firecrawl-mcp`; it requires a server-side Firecrawl API key.
- [OpenSearch MCP server for Python](https://github.com/opensearch-project/opensearch-mcp-server-py), launched with `uvx opensearch-mcp-server-py`; this connects to an existing OpenSearch cluster and searches the configured index. It is not a public web-search engine.
- [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp), launched headlessly with `npx -y @playwright/mcp@latest --headless`.

Set `FIRECRAWL_API_KEY`, `OPENSEARCH_URL`, `OPENSEARCH_INDEX`, and `COOLIE_RESEARCH_BROWSER_ALLOWED_HOSTS` in the server-side `.env`. OpenSearch basic authentication can use `OPENSEARCH_USERNAME`/`OPENSEARCH_PASSWORD`; managed deployments should prefer their supported AWS identity mechanism. The host allowlist is a comma-separated list of exact DNS names (for example `www.example.com`) or explicit subdomain patterns (for example `*.example.org`). Do not use a broad wildcard. The browser checks URL scheme, credentials, local hostnames, literal non-public IPs, and non-web ports in addition to this allowlist; deployment network egress rules should also block private/link-local ranges because DNS-based destinations cannot be safely pinned by this application-level check. These MCP programs run as child processes with the service account's filesystem permissions; run them under a restricted account/container and keep package versions reviewed and pinned in production.

The factory must opt in and compose the bridge before constructing the existing gateway:

```python
connectors = ConnectorRegistry()
register_research_mcp_connector(connectors, ResearchMCPBridge.from_environment())
gateway = ToolGateway(ToolPolicy({"research:web:search"}), connectors)
```

Use the resulting gateway for the Research Room agents already configured with the `search` connector and the `research:web:search` permission. The MCP executables are launched only when a research task runs; the host needs `npx`, `uvx`, network access to the configured providers, and Playwright's headless browser runtime. Review and pin the upstream executable versions for production rather than relying on floating package tags. The bridge uses a 30-second per-response timeout, limits browser reads to three pages, and rejects combined results over 500 KB. The OpenSearch server may expose additional operations, but this bridge never calls them.

## Composition and reliability

`CoolieSystem` in [coolie_runtime.py](./coolie_runtime.py) binds the seven domain services and the Enactor tool gateway to one shared `ReliabilityRuntime`. Composition requires explicit startup-check results for every domain; constructing service objects alone does not mark the system ready. Applications supply the services, dependency results, instance identity, and (if operator controls are enabled) an authentication callback.

[`ui/owner_api.py`](./ui/owner_api.py) provides an integration adapter around that composed system. An integrating application constructs `OwnerWorkspaceApi(system, authenticate=...)` with a trusted authenticator that returns an `OwnerPrincipal` containing server-verified permissions and, for Enactor decisions, a server-verified approval level. It mounts the adapter under `/api`; do not trust identity, permission, or approval-level fields supplied by the browser. The adapter aggregates real readiness and mission records, exposes the existing domain APIs behind explicit read/write/execute/approve permissions, and replaces caller-supplied Enactor approver identity with the authenticated principal. The adapter does not create credentials, configure service providers, or provide a default login.

[`ui/supabase_auth.py`](./ui/supabase_auth.py) supplies the Supabase authenticator for that boundary. It asks Supabase Auth to validate each bearer token, then checks that the returned user has an active membership in the configured workspace before deriving permissions from the database role. The server needs the project URL, the public anon key, and the existing server-only Postgres connection. The anon key is not a service credential; **the service-role key is not needed for owner login or token verification and must not be sent to the browser or chat**. The React workroom uses that same public anon key for email/password sign-in, holds the session in browser session storage, and sends its access token as a bearer token to `/api`. The Vite config explicitly exposes only the project URL and anon key from `.env`; database credentials and any service-role key are not embedded in the frontend. Enactor approval authority is not inferred from workspace role: only explicitly configured per-user approval levels permit approval actions.

The local integration host [`ui/live_server.py`](./ui/live_server.py) combines the persistent service composition, Supabase-backed owner authentication, watch-only wallet registry, `/api` routes, and built static UI. Since provider/model/tool and connector configuration is intentionally deployment-specific, set `COOLIE_SERVICES_FACTORY=module:function` to an application-owned function returning `CoolieServiceBundle` (configured services plus explicit startup checks), then run `python -m ui.live_server`. It binds to `127.0.0.1:4173` by default. It uses Python's single-process development WSGI server and is **not a production server**; deploy it behind a production-grade WSGI server and TLS reverse proxy before public exposure.

For wallet setup without a configured provider/service factory, run `python -m ui.wallet_server` after `npm run build`. This local integration host uses the existing Supabase connection and Auth key, serves the React app, and mounts only the authenticated wallet registry and manual withdrawal-request API. Other `/api` endpoints return `503` until the full service factory is configured. It also uses the single-process development server and must not be exposed publicly.

Example API wiring after creating the services and `CoolieSystem`:

```python
import os
from ui.owner_api import OwnerWorkspaceApi
from ui.supabase_auth import SupabaseOwnerAuthenticator

authenticate_owner = SupabaseOwnerAuthenticator(
    database,
    supabase_url=os.environ["SUPABASE_URL"],
    anon_key=os.environ["SUPABASE_ANON_KEY"],
    workspace_id=workspace_id,
)
owner_api = OwnerWorkspaceApi(
    system,
    authenticate=authenticate_owner,
    wallet_registry=composition.wallets,
)
```

Set `SUPABASE_ANON_KEY` in the local `.env`; it is a public project key and can be obtained from Supabase Project Settings → API Keys. The Vite dev server uses it for sign-in, while the server authenticator uses it to validate access tokens. The offline preview deliberately returns `503` for API routes and is not a live backend host.

## Supabase database setup

The repository is configured for Supabase project `dgyhahgtocogfwljwioc` in `us-east-1`. The migrations in [`supabase/migrations/`](./supabase/migrations/) create workspace-scoped tables for research, finance assessments, Enactor approvals/executions, audit records, Evolver assessments, reliability reports, wallet metadata and withdrawal requests, and a private artifact bucket. Row Level Security policies deny anonymous access and scope authenticated access to active workspace membership; authenticated table access is read-only, and domain writes must go through a trusted backend. A workspace owner can bootstrap a workspace with the `create_owner_workspace` database function. Migration `20261003000005_watch_only_wallet_registry.sql` has been applied to the linked project and verified in remote migration history.

To apply the migration from a trusted local terminal:

```bash
npx supabase login
npx supabase link --project-ref dgyhahgtocogfwljwioc
npx supabase db push
```

Supabase CLI may prompt for the project's database password when linking; enter it only in the local prompt. Review the pending migration output before confirming. For an existing project containing data or manually created tables, take a backup and inspect the schema before applying this initial migration. The project reference and region are identifiers, not database credentials.

Copy [`.env.example`](./.env.example) to an untracked `.env`. Set `SUPABASE_DB_PASSWORD`, `SUPABASE_ANON_KEY`, and `COOLIE_WORKSPACE_ID`; the backend builds a TLS connection to the regional session pooler unless a server-only `DATABASE_URL` override is supplied. The linked development workspace owner has accepted the invitation and has active membership. Do not send database passwords, access tokens, anon keys, or service-role keys in chat or commit them. Never put a service-role key or database URL in a `VITE_*` variable or browser bundle.

The workspace schema and browser-write restriction are applied to Supabase. Additive migrations provide durable repositories for Research Room, Enactor, Brain memory/delegations/events/audits/usage/budgets, Orchestrator decisions, Finance recommendations, Evolver assessments, Report Collector snapshots, operational logs/incidents, shared emergency-pause state, immutable report/artifact storage, and watch-only wallet metadata. Enactor approval state, execution records, budget ledgers, audit hash chain, and idempotency results are workspace-scoped.

### Wallet and withdrawal safety

The Crypto Wallet Setup UI registers separately categorized public addresses for **profits** and **spending**. Network and asset are explicitly entered rather than assumed. Metadata can be edited or deactivated; changes and deactivations are kept in an append-only audit table, and duplicate active purpose/network/asset combinations are rejected. A withdrawal form creates an immutable `pending_review` request associated with an active spending wallet. It does **not** inspect balances, prove address ownership, approve or execute a transfer, or sign/broadcast a blockchain transaction. Address syntax checks are generic only and do not validate the selected network, token contract, checksum, or destination. Verify those independently before using an address.

Coolie must never receive a seed phrase or private key in UI, API, environment, or chat. Actual custody or automated withdrawals require choosing a chain/asset and a dedicated qualified wallet/signing provider, verified balance and destination checks, risk limits, transaction simulation, independent approval controls, and provider-specific integration/security review. No service-role key is needed for watch-only registry or authenticated owner requests.

To select those adapters, first construct all seven services with their normal provider, model, tool, and connector configuration, then bind them before serving requests:

```python
from supabase_storage import SupabaseServiceComposition, create_database_from_env

database, workspace_id = create_database_from_env()
composition = SupabaseServiceComposition(services, database, workspace_id)
system = CoolieSystem(
    composition.services,
    startup_checks=startup_checks,
    instance_id="coolie-backend-1",
    reliability=composition.reliability,
)
```

The persistent binding intentionally refuses a Brain instance that has already accumulated in-memory state; bind it during startup, before processing work. Provider credentials and runtime definitions remain deployment configuration, and short-lived Brain session tokens are deliberately process-ephemeral so a restart invalidates them. Heartbeats are also ephemeral liveness signals. When this composition is used, pause state, logs, incidents, audit records, and supported domain histories use workspace-scoped Postgres adapters. The standard UI preview and local default service constructors still use in-memory repositories unless the host explicitly uses this composition.

Never create an `auth.users` row directly in SQL or invent an owner identity. Authenticated membership is configured, but a live end-to-end app still needs a deployment-provided `COOLIE_SERVICES_FACTORY` with actual provider/model/tool configuration. Database schema and unit tests passing alone do not certify production readiness; external connectors, authentication hosting, backups, and recovery procedures still require deployment-specific validation.

The reliability API exposes liveness, startup, readiness, and dependency probes, along with authenticated pause/resume routes. The Report Collector can build a snapshot from registered sector health. To construct the root, instantiate each service and pass the complete service mapping plus explicit startup checks to `CoolieSystem`; see [the composition root](./coolie_runtime.py) and [its integration tests](./tests/test_reliability.py).

The default reliability implementation is in-process and intended for local development and tests. Without the Supabase composition, state is not durable or coordinated across multiple processes. Even with the composition, heartbeats and short-lived Brain sessions remain ephemeral; durable financial ledger reconciliation, distributed work queues/coordination, worker supervision, telemetry/export, graceful shutdown, and tested recovery procedures remain deployment responsibilities.

## Current integration limits

- The WSGI live host and Supabase owner-auth adapter are provided, but the application still needs a deployment-supplied service factory, HTTPS/reverse-proxy configuration, and actual provider/model/tool setup.
- The live UI integration currently covers system/sector readiness, persisted research missions, and Research Room mission creation. Portfolio, ledger, financial history, opportunities, decisions, reports, and Orchestrator voice/messaging panels are still design-preview data or unsupported interactions; they must not be treated as live state or execution controls.
- No live model provider, managed secret store, or customer-facing Enactor connector is configured by default. Supabase Postgres and private artifact-storage adapters are available, but the host must configure and bind them before serving requests.
- Supabase persistence currently covers the documented domain histories and operational records, while other runtime concerns such as heartbeats and Brain session tokens intentionally remain process-local. Schema files and adapters do not by themselves certify a production deployment.
- Wallet support is watch-only metadata and a manual-review request queue; there is no blockchain RPC, live balance reconciliation, signer, custody integration, or withdrawal execution.
- The local emergency pause is not distributed, durable, or a substitute for infrastructure-level kill switches and incident response.

Treat these limits as deployment requirements, not as features implied by the preview. Before enabling consequential external actions, configure authenticated owner access, durable state and audit, verified integrations, financial reconciliation, monitoring, and end-to-end recovery tests.

## Contribution and verification

Keep sector responsibilities narrow, preserve explicit approval and policy boundaries, and do not present sample, stale, estimated, or forecast data as confirmed actual state. Add or update focused tests with behavioral changes, then run the full suite with:

```bash
python -m unittest discover -s tests -v
```
