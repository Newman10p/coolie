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
ui/                     Owner workroom interface and local sample preview server
tests/                  Standard-library unittest suite
migrations/             Sector-specific schema artifacts where present
```

Each domain has its own models, controller/service logic, and in several cases a small HTTP-style or WSGI API. These APIs are sector boundaries and testable integration points; they do not collectively form a deployed web application or a complete owner-facing backend-for-frontend (BFF).

## Local development

The Python packages use the standard library and require Python 3.11 or newer. From the repository root:

```bash
python -m unittest discover -s tests -v
```

To start the owner-workroom preview:

```bash
python -m ui.demo_server
```

Open [http://localhost:4173](http://localhost:4173). The preview server binds to `127.0.0.1` by default. It serves the static UI and fabricated sample read models at `/api/ui/briefing`, `/api/ui/office-table`, and `/api/ui/reports`. These records are visibly labeled as samples and are not connected to business, wallet, approval, or sector state. The preview server reports readiness as unavailable and does not implement Orchestrator messaging, speech transcription, or emergency controls.

The interface includes push-to-talk capture, a visible transcript, text input, and opt-in speech output. Voice is an input modality only: recognition cannot authorize or execute consequential actions. Audio capture requires browser microphone support and a secure context. In local sample mode, audio is discarded without upload. A real BFF must implement and secure the configured voice/message endpoints before those capabilities can work against Coolie.

## Composition and reliability

`CoolieSystem` in [coolie_runtime.py](./coolie_runtime.py) binds the seven domain services and the Enactor tool gateway to one shared `ReliabilityRuntime`. Composition requires explicit startup-check results for every domain; constructing service objects alone does not mark the system ready. Applications supply the services, dependency results, instance identity, and (if operator controls are enabled) an authentication callback.

The reliability API exposes liveness, startup, readiness, and dependency probes, along with authenticated pause/resume routes. The Report Collector can build a snapshot from registered sector health. To construct the root, instantiate each service and pass the complete service mapping plus explicit startup checks to `CoolieSystem`; see [the composition root](./coolie_runtime.py) and [its integration tests](./tests/test_reliability.py).

This reliability implementation is in-process and intended for local development and tests. Heartbeats, incidents, structured logs, domain workflow state, and Enactor idempotency records are not durable or coordinated across multiple processes. Production use requires appropriate persistent queues/stores, durable financial ledger and reconciliation, distributed coordination, worker supervision, telemetry/export, graceful shutdown, and tested recovery procedures.

## Current integration limits

- There is no production deployment entry point or unified web server for the sector APIs.
- There is no production owner BFF aggregating briefing, portfolio, financial, decisions, reports, or Orchestrator interactions. The UI currently uses its local sample service or a same-origin BFF supplied by an integrating application.
- No live model provider, managed secret store, production PostgreSQL/S3 adapter, or customer-facing Enactor connector is configured by default.
- Sector persistence varies; some repositories and artifact interfaces are in-memory or development-oriented. Schema files and interfaces do not by themselves provide a durable production database.
- The local emergency pause is not distributed, durable, or a substitute for infrastructure-level kill switches and incident response.

Treat these limits as deployment requirements, not as features implied by the preview. Before enabling consequential external actions, configure authenticated owner access, durable state and audit, verified integrations, financial reconciliation, monitoring, and end-to-end recovery tests.

## Contribution and verification

Keep sector responsibilities narrow, preserve explicit approval and policy boundaries, and do not present sample, stale, estimated, or forecast data as confirmed actual state. Add or update focused tests with behavioral changes, then run the full suite with:

```bash
python -m unittest discover -s tests -v
```
