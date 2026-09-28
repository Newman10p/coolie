# Sector 3: ENACTOR — Fully Phased Implementation Plan

Source of truth: `COOLIE STRUCTURE.docx` (Sector 3: Enactor). This plan turns that
architecture into an ordered, verifiable build sequence for this repository.

---

## 0. Ground rules carried from the document

The entire sector exists to enforce one rule:

> **The Enactor may execute an approved plan, but it may not independently redefine the
> business objective, exceed its permissions, spend unapproved money, or perform
> irreversible actions without authorization.**

Non-negotiable design constraints extracted from the doc (these become acceptance
criteria for every phase):

1. **Authorization is enforced in the tool implementation, not in prompts.** Every
   gateway call is independently validated (approval valid, unexpired, arguments match,
   target matches, budget available, agent still permitted).
2. **Approval is bound to exactness** — recipient, platform, content, amount, action.
   An approval for one campaign can never authorize another.
3. **Agents cannot remove or downgrade approval gates** from a compiled plan.
4. **Least privilege per division** — Customer Service never sees Git; Builders never
   see customer conversations; Marketers never see payment credentials.
5. **External content is untrusted** (email, supplier pages, git issues, social
   comments) — prompt-injection defense at the Tool Gateway.
6. **No endless retries on external side effects** (payments, email, publishing) —
   bounded retries, idempotency keys, circuit breakers.
7. **Every action is traceable**: Orchestrator plan → execution ID → task ID → agent ID
   → tool call → connector account → approval ID → external operation ID → result.
8. **QA can block, but never silently rewrite** what it reviews.
9. **Financial actions are recommendations, not executions** (Returns agent recommends;
   Money Calculator / human approves).
10. **The loop must close**: Research → Strategy → Enactment → Measurement → Research
    improvement.

## 1. Current repository state (what already exists)

- `research_room/` — Sector 2 delivered as a **dependency-free Python 3.11 package**:
  typed models with validation, lifecycle controller with attributable transitions,
  dependency-aware planner/scheduler, evidence pipeline, read-only `ToolPolicy` with
  canonical-hash audit events, versioned config (already contains an
  `enactor_request_limit` budget field), repositories with deterministic in-memory
  implementations, immutable artifacts, and a small WSGI API.
- `migrations/001_research_room.sql` — Postgres schema pattern: typed header columns +
  JSONB payload + artifact keys + content hashes + append-style audit table.
- `tests/test_research_room.py` — unittest suite (`python -m unittest discover -s tests`).
- No Enactor code exists yet. The doc's project structure is TypeScript-flavored; the
  repo convention is Python. **Decision: implement the Enactor in Python mirroring the
  doc's module map 1:1**, keeping the same names so the doc remains navigable
  (`controller/`, `agents/<division>/`, `tools/`, `connectors/`, `policy/`, `runtime/`,
  `models/`, `storage/`, `evaluation/`, `config/`, `api/`). Contracts translate the
  doc's TS types into validated frozen dataclasses/Enums exactly as Sector 2 did.

Style conventions inherited from `research_room`:
- Frozen dataclasses with `__post_init__` validation; `str, Enum` status types.
- Deterministic in-memory repositories first; durable adapters behind contracts only.
- Canonical-JSON audit hashing; versioned sector configuration retained per run.
- No live external connectors until their phase; fakes/adapters conform to contracts.

## 2. Target layout (translated from doc §11)

```
sector3_enactor/
├── __init__.py
├── config/                  # sector-policy, agent-registry, connector-registry,
│                            # approval-levels, budgets, stop-conditions (YAML-loaded, versioned)
├── models/                  # execution, task, approval, asset, message, product,
│                            # campaign, deployment, outcome (+ shared money/risk types)
├── controller/              # enactor_controller, plan_compiler, task_scheduler,
│                            # dependency_manager, approval_manager, retry_manager,
│                            # escalation_manager, circuit_breaker
├── agents/                  # base_enactor_agent + divisions:
│   ├── messengers/ designers/ builders/ marketers/ seo/
│   ├── commerce/ qa/ analytics/
├── tools/                   # tool registry + EnactorToolDefinition (mode/risk/A-level/
│                            # reversibility/dry-run/budget-type/data-scope)
├── connectors/              # brain, orchestrator, research_room, email, messaging,
│                            # store, inventory, supplier, repository, hosting, design,
│                            # social, advertising, analytics, seo
├── policy/                  # authorization_engine, approval_policy, budget_policy,
│                            # communication_policy, production_policy, marketing_policy,
│                            # customer_data_policy, content_safety_policy
├── runtime/                 # sandbox_manager, secret_broker, token_manager,
│                            # rate_limiter, artifact_manager, rollback_manager,
│                            # environment_manager
├── storage/                 # execution/task/asset/message/approval/deployment/audit repositories
├── evaluation/              # quality_gates, content_validator, claims_validator,
│                            # release_validator, metrics_evaluator, anomaly_detector
├── api/                     # WSGI: execution, tasks, approvals, assets, comms, status
└── handoffs/                # research-room ⇄ enactor ⇄ orchestrator packet contracts
tests/enactor/               # permissions, approval-binding, sandbox, connector-contracts,
                             # messaging-policy, code-execution, rollback, prompt-injection,
                             # end-to-end-execution (doc §11 test list)
migrations/002_enactor.sql
```

---

## PHASE 0 — Foundations & contracts (no behavior yet)

**Goal:** the type system and registries that everything else must speak.

Deliverables:
- Package skeleton above; `pyproject.toml` entry; README section stub.
- `models/execution.py`: `ExecutionRequest`, `ExecutionResult`, `ExecutionStatus`
  (all 15 states from doc §4.2: RECEIVED … ARCHIVED), `ActionRequest`, `ActionResult`,
  `ArtifactReference`, `ExecutionMetric`, `Escalation`, `StopCondition`, `SuccessMetric`.
- `models/approval.py`: `ApprovalRequest` with risk level, exact arguments, expiry;
  `ApprovalLevel` A0–A4 (doc §4.5 table).
- Shared `Money`/`RiskSeverity` types aligned with `research_room.models`.
- `tools/tool_registry.py`: `EnactorToolDefinition` (doc §7) with validation — mode ∈
  read/draft/write/external_action, risk, allowedAgents, approvalLevel, reversible,
  supportsDryRun, budgetType, dataScope. Registry refuses duplicate names and unknown
  agents.
- `config/` loader: six YAML files, versioned like research-room config; invalid
  policy/config combinations fail closed.
- `handoffs/`: contract for the incoming mandate shape produced by Research Room
  recommendation packets (opportunityId ↔ research handoff linkage).

Acceptance:
- Round-trip serialization validation tests for every model; malformed inputs rejected.
- Registry rejects a tool claiming A-level "A6" or an empty `allowedAgents` list.
- Config versioning test: two versions coexist; a run pins the version it started with.

Exit criteria: all Phase 0 tests green; zero imports from `research_room` internals
(only public model shapes mirrored).

---

## PHASE 1 — Core runtime (doc §13 Phase 1) ⭐ the mandatory foundation

**Goal:** a governable execution machine with no real-world reach at all.

Deliverables:
1. **Execution Controller** (`controller/enactor_controller.py`)
   - createPlan / validatePlan / start / pause / resume / cancel / getStatus.
   - State machine with explicit legal transitions; every transition attributed to
     actor + reason (mirror `ResearchRoomController.transition`).
   - Mandate validation (lifecycle §9 phases 1–2): plan approved? opportunity valid?
     assets available? budget/permissions clear? risk flags? within sector authority?
2. **Plan Compiler** (`controller/plan_compiler.py`)
   - Objective → task graph (doc §4.3 landing-page example becomes a fixture).
   - Preserves objective, budget, constraints, audience, approved claims, required
     assets, success metrics, stop conditions, approval requirements.
   - Structural guarantee: approval gates present in the request cannot be dropped by
     any downstream mutation (graph stores them as immutable nodes; tamper attempt
     raises).
3. **Task Scheduler + Dependency Manager** (`task_scheduler.py`, `dependency_manager.py`)
   - Sequential/parallel execution, conditional branching, priority queues, timeouts,
     human-wait states, failure propagation (blocked prerequisites block dependents —
     reuse research-room semantics).
4. **Retry Manager + Circuit Breaker** (`retry_manager.py`, `circuit_breaker.py`)
   - Bounded retries with backoff; **hard rule: no automatic retry for
     `external_action` tools without an idempotency key**; breaker opens per tool/target
     after N failures; opening pauses the run rather than hammering providers.
5. **Approval Manager** (`approval_manager.py`)
   - Create/list/resolve approvals; expiry handling; **exact-binding check**: recorded
     hash of (tool, target, exactArguments, budget) compared at execution time —
     mismatch = denial, new approval required.
   - Policy engine hook to *raise* (never lower) approval level based on context.
6. **Tool Gateway** (`tools/gateway.py`) — the single choke point:
   verify agent identity → permission (least privilege) → approval level satisfied →
   approval valid/unexpired/exact-match → budget remaining → rate limit → data scope →
   then invoke connector. Emits canonical audit record for **every** call including
   denials.
7. **Budget Manager** (`policy/budget_policy.py` + runtime accounting)
   - Per-execution budget ledger (model tokens, API calls, ad spend, purchases);
     overspend attempts blocked at gateway; budget warnings via internal-comms slot.
8. **Audit Log** (`storage/audit_repository.py`)
   - Full traceability chain (§8.5): plan→execution→task→agent→tool call→connector
     account→approval→external op→result. Append-only; deterministic hashes.
9. **Base agent interface** (`agents/base_enactor_agent.py`)
   - `EnactorAgent[I,O]` + `EnactorResult[T]` exactly per doc §12 (status ∈ success /
     partial / blocked / failed / awaiting_approval; artifacts; toolCalls; warnings;
     escalations; rollbackAvailable).
10. **Connectors (contract + fake only):** `brain.connector` (complete/extract/classify/
    embed/retrieveContext/validateStructuredOutput — holds central key conceptually;
    agents get scoped requests, never credentials), `orchestrator.connector`
    (getExecutionPlan/reportProgress/requestDecision/requestApproval/reportFailure/
    reportOutcome), `research_room.connector` (getOpportunity/getEvidence/…/submitOutcome).
    All three ship as protocol + deterministic in-memory fakes.
11. **API slice** (`api/execution.routes`, `status.routes`): WSGI create/start/pause/
    resume/cancel/get-status/get-results — mirrors research-room's small-API approach.

Acceptance tests (subset of doc §11):
- `end_to_end_execution.test`: full lifecycle §9 phases 1–11 with fakes, including a
  WAITING_FOR_APPROVAL stall and resume-after-approval.
- `approval_binding.test`: approval for campaign X cannot execute campaign Y (argument
  drift, recipient drift, amount drift each denied).
- `permissions.test`: agent outside `allowedAgents` denied even if approval exists.
- Budget exhaustion mid-run → PAUSED + escalation, never silent overrun.
- Retry cap on external_action proven by call-count assertions on the fake connector.

Exit criteria: a mandate can flow end-to-end against fakes with a complete audit trail
and zero ability to touch anything real.

---

## PHASE 2 — Production capabilities (doc §13 Phase 2)

**Goal:** make real *internal* things safely: assets, code, staging deploys, rollback.

Deliverables:
- **Asset storage & versioning** (`runtime/artifact_manager.py`): lifecycle folders
  `concept → draft → reviewed → approved → published → archived` (doc §5.2D); immutable
  versions with content hashes (reuse research-room artifact pattern).
- **Builder division (core)**: `product_builder.agent` (create_project,
  implement_feature), `code_review.agent` (authn/authz, injection, secret leakage,
  dependency vulns, coverage checks as structured reports).
- **Sandbox manager** (`runtime/sandbox_manager.py`): ephemeral workspaces, restricted
  shell, command allowlist, network allowlist, dependency scanning hooks, no SSH keys /
  cloud creds / personal dirs, staging≠production separation (§8.3). Enforcement is
  programmatic (allowlist checks in gateway/runtime), not advisory.
- **Repository + Hosting connectors (contract + fake)**: branch/patch/checks/PR/merge;
  createPreview/deployStaging/readLogs/healthCheck/requestProductionDeploy/rollback.
- **Release/DevOps agent**: run_ci_pipeline → deploy_to_staging → run_smoke_tests →
  request_production_release(requires approvalId). Production deploy is A4-gated.
- **Rollback manager** (`runtime/rollback_manager.py`): every deployment records its
  predecessor; `rollbackApprovedRelease` path tested; ROLLED_BACK state wired into the
  state machine.
- **Designer division (drafts only)**: product_design, brand_ui, creative_assets agents
  producing assets through the versioned pipeline; **Design QA agent** with
  `run_design_qa` report (resolution, legibility, brand, mobile, duplicates, suspected
  copyrighted/trademarked elements flagged for humans).
- **Catalog Agent (drafts)**: create/update/validate product drafts via Store connector
  fake; publish stays A3-gated and out of scope here.
- **QA core**: `evaluation/quality_gates.py`, `content_validator.py`,
  `release_validator.py`; storefront/accessibility test runners as report producers.
  QA blocks; it never edits.
- **Secret broker** (`runtime/secret_broker.py`): connectors resolve credentials at
  call time from an injected provider; agents and sandboxes never see values; audit
  records which secret alias was used, never the secret.

Acceptance tests:
- `sandbox.test`: disallowed command/network target refused by runtime regardless of
  agent intent.
- `code_execution.test`: builder patch → review report → CI → staging → smoke →
  release request requires a matching approvalId; production deploy without it fails.
- Rollback restores previous artifact pointer and is itself audited.
- Asset lifecycle test: an asset cannot jump from `draft` to `published` (missing
  reviewed/approved steps rejected).

Exit criteria: a landing page / storefront artifact can be built, reviewed, staged,
released (with approval) and rolled back — entirely against fakes, fully audited.

---

## PHASE 3 — Communication & marketing (doc §13 Phase 3)

**Goal:** controlled contact with the outside world, starting low-risk.

Deliverables:
- **Messenger division**:
  - `request_triage.agent`: classify_request over the 11 documented intents;
    route_request to customer_service | commerce | finance | human.
  - `customer_service.agent`: read message/order context, draft replies, send only
    low-risk approved replies (A2 policy), create tickets, escalate. Hard-coded
    restricted-action list (refunds, compensation, legal, payment disputes, medical/
    safety claims, account changes, policy exceptions) → always escalation.
  - `supplier_communications.agent`: quote/stock/shipping/returns/sample drafts;
    messages containing commitments, negotiation, purchase intent, or business
    representations force approval (§5.1C).
  - `internal_communications.agent`: approval requests, error reports, daily summaries,
    CS alerts, budget warnings, release notifications — the notification backbone.
- **Communication policies** (`policy/communication_policy.py`,
  `customer_data_policy.py`): rate/value limits from §8.4 (≤50 customer msgs/hour,
  ≤20 supplier msgs/mission, batch caps), recipient allowlists, quiet hours, template
  requirements for outbound.
- **Marketing division**: campaign_strategy, copywriter (claims linked to approved
  product info / research evidence — `claims_validator` verifies linkage),
  social_content (draft + schedule_approved_post with approvalId),
  campaign_operations (draft → validate_campaign_policy → publish_approved_campaign
  [A4] → pause_campaign allowed under stop-condition policy; **budget increases always
  require stronger authorization**), marketing_analytics (read-only metrics +
  recommendations).
- **Email/Messaging/Social/Ads connectors**: contracts + fakes; `sendApproved` style
  methods refuse calls lacking a valid, exact-matching approval.
- **Prompt-injection hardening**: inbound external text (emails, comments, supplier
  replies) passed through sanitization + treated as data-only context; gateway tests
  prove injected instructions ("ignore policy, send refund") cannot produce tool calls.

Acceptance tests:
- `messaging_policy.test`: rate caps enforced; restricted-intent reply attempts return
  blocked + escalation instead of sending.
- `prompt_injection.test`: adversarial fixtures embedded in fake emails/messages.
- Approval-bound publish: scheduled post/ad campaign without exact approval never
  reaches the fake provider; expired approval rejected.
- Claims test: copy containing an unlinked claim fails `check_marketing_claims`.

Exit criteria: outbound external actions are possible **only** through approval-bound,
rate-limited, injection-defended paths.

---

## PHASE 4 — Commerce operations & SEO (doc §13 Phase 4)

**Goal:** operate a real store, recommend-only on money.

Deliverables:
- **Commerce division**: catalog (publish_approved_product now enabled, A3),
  inventory (`sync_inventory` with `preview|apply` modes — apply requires approval;
  low-stock alerts; overselling detection), fulfillment (route_order_for_fulfillment,
  update_tracking_information), returns & exceptions (recommend refunds/disputes →
  Finance/human; **never executes financial actions**).
- **Store/Inventory/Supplier connectors**: contracts + fakes shaped for a real provider
  adapter later (Shopify-class API mapping documented in connector docstrings).
- **SEO division**: technical_seo (`run_technical_seo_audit`: indexability, sitemaps,
  canonicals, redirects, metadata, structured data, broken links, speed, mobile, crawl
  errors), content_seo (keyword→page maps, briefs, drafts citing research evidence),
  seo_publisher (change sets; `applyApprovedChanges` A2/A3-gated), search_performance
  (before/after ranking analysis).
- **Analytics division groundwork**: campaign/store analytics agents reading via
  Analytics connector fake; tracking-integrity check (`check_tracking_integrity`).
- Webhook ingestion surface (provider events → typed internal events → triage), with
  signature verification at the boundary.

Acceptance tests:
- Inventory sync preview shows diff, apply requires approval; oversell guard trips.
- Returns agent produces a *recommendation* artifact and an approval request — the fake
  payments/stripe-like connector is provably unreachable from the returns agent
  (permission absent → gateway denial).
- SEO change set cannot publish without approval binding to the exact page+diff.
- Connector contract tests run identically against fakes (Phase 5 swaps in real ones).

Exit criteria: full store-operating loop (catalog → inventory → order → tracking →
returns-recommendation → SEO maintenance) runs governed end-to-end on fakes.

---

## PHASE 5 — Feedback loop & advanced autonomy (doc §13 Phase 5)

**Goal:** measurable outcomes flowing back to Brain/Strategy/Research, plus limited
self-action within pre-approved envelopes.

Deliverables:
- **Analytics & feedback division**: `collect_business_metrics` (views, ATC, checkout,
  purchases, inquiries, returns, refunds, campaigns, search, incidents, supplier
  delays, support volume, delivery), `compare_against_targets`,
  `detect_execution_anomalies`, `report_outcome_to_orchestrator`,
  `send_feedback_to_research_room` — closing Research → Strategy → Enactment →
  Measurement → Research (§5.8).
- **Anomaly-driven responses (bounded)**: auto-pause campaign under explicit stop
  condition (pre-approved policy exception), auto-escalate supplier delay, auto-open
  support ticket surge — each enumerated in `stop_conditions.yaml`; anything not
  enumerated escalates instead of acting.
- Controlled campaign optimization loop (recommend → approve → apply; budget raise
  always A4).
- Supplier follow-up workflows (bounded cadence, mission-scoped limits).
- Automated content testing (A/B harness feeding metrics evaluator).
- Cross-business portfolio execution readiness: multi-`businessId` scoping in
  storage/audit, per-business budgets and credentials isolation.
- Learned-outcome feedback records compatible with research-room retention format.

Acceptance tests:
- Outcome report round-trips into the research-room fake and appears as a retention
  record.
- Stop-condition pause happens without a new approval but is audited with the policy
  citation; the *same* action without a matching stop condition is denied.
- Anomaly false-positive does not trigger any external write.

Exit criteria: the sector demonstrably improves future decisions using its own results,
while every autonomous act traces to a pre-approved policy line.

---

## PHASE 6 — Hardening & productionization

**Goal:** swap fakes for real infrastructure and prove the security posture.

Deliverables:
- `migrations/002_enactor.sql`: executions, tasks, approvals (with binding hash),
  assets/versions, messages, products, campaigns, deployments, outcomes, audit_events
  — same header+JSONB+hash pattern as `001_research_room.sql`; append-only audit grant.
- Durable repository adapters implementing Phase 0/1 contracts (Postgres driver kept
  out of the core package, mirroring research-room's stance).
- Real connector adapters (email, store, git/hosting, social/ads, analytics/SEO) as a
  separate extras install; secrets via runtime secret broker only.
- Token manager + provider rate-limit integration; environment manager (staging vs
  prod credential separation).
- Chaos/failure drills: connector timeout mid-publish, approval expiring between gate
  and execution, crash during deploy → recovery lands in a consistent state.
- Red-team suite: expanded prompt-injection corpus, confused-deputy tests (agent
  replaying another agent's approval), argument-drift fuzzing against the gateway.
- Load/perf pass on scheduler; observability (structured logs, sector metrics, health
  endpoints).
- Docs: operator runbook, approval-reviewer guide, threat model mapped to NIST AI RMF
  Govern/Map/Measure/Manage (per §8.5 citation).

Exit criteria: `python -m unittest discover` green across both sectors; red-team suite
finds no path from an agent-authored instruction to an unapproved external write.

---

## PHASE 7 — Integration with the rest of Coolie

**Goal:** Sector 3 as a plug-in peer of Sector 2.

Deliverables:
- Handoff wiring: Research Room recommendation packet → ExecutionRequest factory
  (opportunityId, strategyId, evidence refs carried through); outcome →
  `research.submitOutcome()` adapter.
- Orchestrator/Brain/Money Calculator/Strategy Manager integration contracts defined
  jointly (this phase assumes those sectors expose their own connectors).
- End-to-end scenario test: doc §10 workflow ("build and validate a product landing
  page under the approved test budget") executed across Sector 2 + Sector 3 fakes with
  a single traceable chain.
- Versioned inter-sector API contracts + compatibility tests.

Exit criteria: the §10 worked example passes as one automated test with a complete
audit trail spanning research → enactment → measurement → reported outcome.

---

## Sequencing summary

| Phase | Scope | Doc reference | Real-world reach |
|---|---|---|---|
| 0 | Models, tool registry, configs, handoff contracts | §4.1, §7, §11, §12 | none |
| 1 | Controller, compiler, scheduler, gateway, approvals, budget, audit, base agent, core connectors (fakes) | §13-P1, §4.2–4.5, §8.5, §9 | none |
| 2 | Assets, builders, sandbox, release, rollback, design, catalog drafts, QA gates, secret broker | §13-P2, §5.2, §5.3, §5.7, §8.3 | staging only (fakes) |
| 3 | Messengers, marketing, comms policies, injection defense | §13-P3, §5.1, §5.4, §8.2, §8.4 | external, approval-bound |
| 4 | Commerce ops, SEO, webhooks, analytics groundwork | §13-P4, §5.5, §5.6 | external, approval-bound |
| 5 | Outcome loop, anomaly response, bounded autonomy, portfolio | §13-P5, §5.8, §9 P9–11 | external, policy-pre-approved |
| 6 | Persistence, real adapters, chaos/red-team, docs | §8, §11 tests | production |
| 7 | Coolie-wide integration, §10 scenario E2E | §2, §6, §10 | cross-sector |

**Rule of thumb for every phase:** nothing moves forward until the previous phase's
acceptance tests pass, and no phase ever grants an agent a capability the Tool Gateway
cannot independently deny.
