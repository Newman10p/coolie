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
