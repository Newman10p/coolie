# Coolie Research Room (Sector 2)

The Research Room is Coolie's read-only business-intelligence and opportunity-validation sector. It accepts typed research missions, produces a dependency-aware plan, records evidence, enforces least-privilege tool policy, and prepares only internal handoff packets. It **cannot** purchase, publish, contact customers, transfer money, or make final business decisions.

## First implementation

This initial, dependency-free Python package establishes the sector boundary:

- typed mission, task, evidence, opportunity, and recommendation contracts;
- mission validation and explicit lifecycle transitions;
- task planning, dependency scheduling, retry limits, and output quality checks;
- evidence confidence aggregation and traceable source records;
- configurable opportunity scoring plus non-negotiable risk/budget/margin overrides;
- scoped tool permissions and audit-event creation;
- typed recommendation packets ready for financial, strategy, and orchestrator handoffs.

## Current guarantees

- Invalid domain inputs, task graphs, incomplete scorecards, mismatched currencies, and premature lifecycle submissions are rejected or held for more research.
- Every forward lifecycle transition is attributable to an actor and reason; submission also requires documented financial, strategy, recommendation, budget, stop-condition, and high-severity-risk gates.
- Tasks cannot run until their dependencies complete; failed, blocked, and cancelled prerequisites block downstream work.
- The tool policy only permits `research:` capabilities and emits canonical, deterministic audit hashes. The Research Room still has no live connectors, API, or Enactor execution authority.

## Phase 1 persistence and configuration

- Repository contracts and deterministic in-memory implementations now cover missions, tasks, opportunities, immutable evidence/source snapshots/reports, audit events, and versioned sector configuration.
- Immutable source/report artifacts can be held in memory or local development storage; a PostgreSQL schema migration is provided for durable production adapters and an S3-compatible adapter can implement the same object-storage contract.
- Scoring, budgets, agent permissions, source quality, and retention settings are validated and versioned so a historical mission can retain the policy used to evaluate it.
- The package deliberately does not yet ship a database driver or live PostgreSQL/S3 connector. Infrastructure adapters belong to deployment configuration and must conform to these contracts.

Run the tests with:

```bash
python -m unittest discover -s tests -v
```

External connectors and real-world Enactor actions are deliberately not implemented in this sector.

## Delivered workflow capabilities

The Research Room now plans product/service research tasks, runs registered narrow agents through a controller-owned read-only connector gateway, captures immutable source artifacts, sanitizes untrusted source text, extracts basic public facts, registers and verifies evidence, generates immutable reports, retains outcome learning records, and exposes a small WSGI mission API (create, get, pause, resume, cancel, progress). External provider adapters remain deployment concerns: no connector in this package can spend, publish, purchase, message customers, or call the Enactor.

## Sector 0: The Brain

The Brain is the provider-neutral intelligence and governance plane described in the supplied Coolie architecture DOCX. Its six-stage minimum viable foundation is implemented in the standard-library `brain` package:

- Provider adapters receive expiring credentials only through the Brain gateway and must translate provider exceptions to sanitized `ProviderError`s. `EnvironmentSecretManager` is a development adapter; production should inject a managed secret-store implementation.
- Registered agents receive expiring, revocable, task-scoped session tokens with operation, memory, token, and cost limits. Model profiles are routed by capability, sector, and registered agent permissions.
- Inference applies per-request authorization, estimated cost preflight plus provider-reported usage accounting, context-reference and sensitivity filtering, a common JSON-Schema subset validator, secret-leak rejection, and content-hash audit records. If a provider reports usage above a request's reserved ceiling, the overrun is recorded and the output is blocked; charges already incurred at the provider cannot be undone.
- Memory namespaces, bounded approval-aware delegation, and an append-only in-process event bus with retryable subscriber delivery provide isolated coordination primitives.
- Provider health, fallback profiles, circuit breakers, and an explicit emergency pause support degraded operation.

There is no provider key, live provider adapter, persistent Brain database, or production secret-store integration in this repository. Those are deployment-provided interfaces, not silently configured defaults. `BrainResearchAgent` can be registered with the Research Room's existing agent registry to route a research task through an explicitly configured Brain; its session-issuer and revoker callbacks must be supplied by trusted orchestration code and issue only the scopes needed for that task. The WSGI boundary exposes authenticated `POST /brain/inference` and unauthenticated `GET /brain/health`; only the session token is accepted from callers, never a provider credential. Memory search is lexical and in-process, not embedding/vector search; delegation reserves its full declared cap against the parent task; persistence, full JSON Schema, provider-specific adapters, and managed event delivery remain deployment work.

For local development, configure a provider adapter, model profiles, agent policies, and `EnvironmentSecretManager` explicitly in application composition. Run the standard-library test suite with:

```bash
python -m unittest discover -s tests -v
```

## Sector 4: Business Finance / Money Calculator / Activation Manager

The actual Sector 4 layer in the architecture is the business-finance and activation plane: it evaluates planned spend, expected revenue, margin, risk, and confidence before a real activation is approved. This package complements the earlier governance-oriented Orchestrator and keeps the business decision logic explicitly separate from the policy-enforcement layer.

The first implementation adds:

- typed activation proposals with predicted revenue, margin, and confidence gates;
- spend approval logic that rejects unprofitable or weak-evidence activations;
- budget-cap checks and owner-approval requests before exceeding a signed limit;
- a deterministic finance recommendation record with ROI and payback insights;
- a small WSGI boundary for assessment requests and decision records.

This sector remains bounded by design: it can recommend or gate spending, but it does not bypass policy, Sharia, operational risk, or owner approval gates. Those controls remain enforced by the governance stack around it.

## Sector 5: The Evolver

The Evolver is the controlled capability-expansion layer described in the updated Word architecture. It evaluates a proposed new business domain, identifies what Coolie already supports, highlights capability gaps, estimates the required agents, tools, connectors, policies, and data models, and produces a validated extension plan for approval.

The implementation adds:

- expansion requests and capability-gap models;
- a controller that maps missing capabilities to required build components;
- cost and revenue viability checks for the proposed extension;
- a plan object that captures required assets, testing steps, and reusability guidance.

## Sector 6: The Report Collector

The Report Collector gathers the current operational picture from the live system and produces an operational snapshot that can be handed to the Orchestrator for presentation through the UI. It is designed to auto-discover system components and present a coherent health summary without directly changing policy or state.

The implementation adds:

- system component records with status and ownership metadata;
- snapshot generation with health ratios and alert counts;
- directory-based discovery of Python modules and their current status;
- a small API surface for health and discovery operations.

## Shared reliability and failsafe

All sector services and the Enactor tool gateway use the same process-wide `ReliabilityRuntime` by default. Applications can inject a fresh runtime for isolation, or compose all seven sector services through [coolie_runtime.py](./coolie_runtime.py), which requires explicit startup checks, binds the shared emergency pause, and registers service heartbeats. When the pause is active, Brain inference, research execution, business decisions, finance assessments, capability planning, and Enactor execution fail closed. Report collection and read-only health inspection remain available.

The reliability package provides liveness/startup/readiness/dependency probes, heartbeat staleness and progress assessment, incident records, structured event records with sensitive-field redaction, and an authenticated WSGI pause/resume interface. Operator control is unavailable unless the application supplies an authentication callback. The Report Collector can build snapshots from registered sector health.

This is a local reliability foundation, not production durability: heartbeats, incidents, logs, workflow state, and Enactor idempotency records are currently in memory. The repository does not yet have a durable queue/event store, database-backed ledger or reconciliation worker, service supervisors, distributed leases, telemetry exporter, or deployment-level graceful-shutdown integration. Those adapters and staging failure/soak tests are required before enabling production external actions. Run local tests with:

```bash
python -m unittest discover -s tests -v
```

## Owner workroom UI

The dependency-free, responsive owner interface is in [`ui/`](./ui/). Its navy-and-blue workroom theme follows the UI brief's blue, gold, and metallic plate tokens. The global Orchestrator drawer includes push-to-talk audio capture, a visible transcript, always-available text input, and opt-in speech output. Audio is uploaded only after recording stops and only to a configured owner BFF; local preview recordings are discarded. A real integration must implement `POST /api/orchestrator/transcribe` and `POST /api/orchestrator/messages`; voice recognition never authorizes or executes actions. Run the local sample server from the repository root:

```bash
python -m ui.demo_server
```

Then open `http://localhost:4173`. This server supplies sample owner read models at `/api/ui/briefing`, `/api/ui/office-table`, and `/api/ui/reports` so the connected UI can be exercised. All responses are marked as sample data and the interface labels them as such; none are connected to business, wallet, approval, or sector state. The sample server does not provide real readiness checks, Orchestrator messaging, speech transcription, or emergency pause/resume. It is a UI development fixture, not a backend for operating Coolie.

To connect a real owner BFF, configure its same-origin API base path (for example, `/api`) in Settings. The BFF must expose those three owner read models plus authenticated reliability routes under that prefix. The repository does not yet implement production owner aggregation. Missing live data is shown as unavailable rather than replaced with preview values.
