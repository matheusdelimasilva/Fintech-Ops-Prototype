# Prototype evidence ledger

Running record of what has been built, how it was verified, where a human
intervened, and what is still missing. Append a section per checkpoint; do not
rewrite earlier sections.

All data and identities in this prototype are synthetic. Identity is a demo
user ID header resolved server-side; there is no real authentication.

## Checkpoint index

| # | Checkpoint | PR | Status |
|---|---|---|---|
| 1 | Runnable skeleton (scaffold + `/health`) | [#1](https://github.com/matheusdelimasilva/Fintech-Ops-Prototype/pull/1) | Merged |
| 2 | Backend foundation: persistence, seed, demo identity, read-only API | [#2](https://github.com/matheusdelimasilva/Fintech-Ops-Prototype/pull/2) | Merged |
| 3 | Refund mutations, RBAC enforcement, atomic audit writes | — | Not started |
| 4 | Frontend shell + Refund Operations UI | — | Not started |
| 5 | Feature Flags reuse proof | — | Not started |
| 6 | Final verification and handoff | — | Not started |

## Checkpoint 1 — Runnable skeleton (PR #1)

**Delivered:** FastAPI app exposing `GET /health`; React 19 / Vite 8 / TypeScript
placeholder page that displays backend health; `ruff` and `oxlint` configured;
`.nvmrc` pinning Node 22.

**Verification:** `pytest` (1 test), `ruff check`, `npm run lint`, `npm run build`.

**Human interventions:** None recorded beyond PR review and merge.

## Checkpoint 2 — Backend foundation (PR #2)

### Planning

Planned through a structured design interview (four rounds, 30 decisions)
before any code was written. Decisions that shape later checkpoints:

- SQLAlchemy 2.0 declarative ORM over SQLite; `DATABASE_URL` env override,
  default `backend/fintech_ops.db` (gitignored).
- Tables are created and the seed inserted on app startup **only when the
  database is empty**; `python -m app.seed --reset` is the explicit,
  idempotent reset. No reset endpoint (it would be an unauthenticated
  destructive mutation).
- Identity: `X-Demo-User-Id` header on every `/api/*` route, including reads.
  Missing → `401 MISSING_IDENTITY`; unknown → `401 UNKNOWN_IDENTITY` (both are
  authentication failures, not `403`).
- Role → approval limit / editable flag environments lives only in
  `backend/app/policy.py`; the user row stores `role` alone. No authorization
  claim is ever read from the request.
- Uniform error envelope `{"error": {"code", "message", "details"}}` for all
  non-2xx responses, including Pydantic validation failures.
- Readable deterministic IDs (`rfnd_001`, `flag_bulk_export_staging`,
  `evt_seed_001`), fixed absolute UTC timestamps, integer minor units only.
- Read endpoints return bare arrays with deterministic sorts; no pagination.
- Module layout: flat single-file modules (`db.py`, `models.py`, `errors.py`,
  `identity.py`, `policy.py`, `repositories.py`, `schemas.py`, `seed.py`) plus
  one `api/` package with a router per domain. `services/` and `audit.py`
  are intentionally absent until checkpoint 3.

### Delivered

- Models: `DemoUser`, `RefundCase` (with denormalized `last_action*` columns),
  `FeatureFlag`, `AuditEvent` (`JSON` before/after state). Enums stored as
  checked `VARCHAR`.
- Seed: 3 demo users; 12 refunds including pending rows at exactly
  50000 / 50001 / 500000 / 500001 cents and one approved, rejected, and
  escalated case; 4 feature flags (2 staging, 2 production); 3 historical
  audit events with real before/after JSON.
- Read-only API: `GET /api/session` (user + server-resolved policy + demo
  roster + identity note), `GET /api/refunds[?search&status&risk_level]`,
  `GET /api/refunds/{id}`, `GET /api/feature-flags[?environment]`,
  `GET /api/feature-flags/{id}`,
  `GET /api/audit-events[?entity_type&entity_id&actor&action]`,
  `GET /api/audit-events/{id}`. `/health` remains open.
- Swagger UI `Authorize` box wired to the demo header (`APIKeyHeader`).
- README: current state, identity header usage, seed/reset commands.
- Devin environment blueprint added (backend venv, Node 22 via nvm, frontend
  `npm install`, lint/test/build/run commands).

### Commands run and results

```bash
cd backend
./.venv/bin/pytest                      # 30 passed
./.venv/bin/ruff check .                # All checks passed
./.venv/bin/ruff format --check .       # 21 files already formatted
./.venv/bin/python -m app.seed          # "Seeded empty database ..."
./.venv/bin/python -m app.seed          # "... already seeded; use --reset to start over."
./.venv/bin/python -m app.seed --reset  # "Reset and reseeded ..."

cd frontend && nvm use 22
npm run lint                            # clean (frontend untouched)
npm run build                           # built (frontend untouched)
```

Direct API checks (TestClient / curl against a fresh seed):

| Request | Result |
|---|---|
| `GET /api/refunds` with no header | `401` `MISSING_IDENTITY` |
| `GET /api/session` with `X-Demo-User-Id: bogus` | `401` `UNKNOWN_IDENTITY` |
| `GET /api/session` as Sam / Olivia / Avery | limits `50000` / `500000` / `null`; flag permissions none / staging / staging+production |
| `GET /api/session` as Sam with extra `X-Role: admin` header and `?role=admin` | role stays `support_agent` |
| `GET /api/refunds` as any user | 12 rows, newest first (`rfnd_012` first) |
| `GET /api/refunds?status=bogus` | `422` `VALIDATION_ERROR` in the shared envelope |
| `GET /api/refunds/rfnd_999` | `404` `NOT_FOUND` |
| `POST/PUT/PATCH/DELETE /api/audit-events/{id}` | `405`; OpenAPI lists only `get` under `/api/audit-events*` |

### Automated test coverage (30 tests)

Identity: 401 codes for missing/unknown identity; every `/api` read route
requires identity (parametrized); per-user role and policy resolution;
browser-supplied role claims ignored; `/health` unauthenticated.

Read API: refund list order and filters; invalid enum → 422 envelope; detail
and 404; integer-only money on the wire; flag list/filter/detail; audit list
order, filters, parsed before/after objects; audit routes are GET-only.

Seed: two resets produce identical rows; `seed_if_empty` is idempotent;
threshold fixtures (50000 / 50001 / 500000 / 500001) exist as pending; app
startup seeds an empty DB.

### Human interventions

- Design interview: 30 decisions answered by the project owner before
  implementation (see "Planning").
- Owner deferred README/evidence updates during planning, then reversed on the
  README (updated in PR #2) and requested this ledger after the merge.
- A browser-driven run through Swagger UI was started after the PR opened but
  was interrupted by a session restart before producing a report; the API
  checks above were re-executed from the shell instead. Browser verification
  is deferred to the checkpoint that adds a UI.

### Limitations at this checkpoint

- No mutations exist yet, so approval limits, required reasons, state
  transitions, and atomic audit writes are **not yet enforced anywhere** — only
  the policy values and seed fixtures for them are in place.
- `RefundCase.last_action*` columns are seeded but not maintained by any write
  path.
- Identity is a plain header with no authentication, session, or CSRF story.
- The audit trail is append-only through the application only; SQLite offers no
  tamper evidence.
- Engine is a module-level `lru_cache` singleton keyed off `DATABASE_URL` at
  first use; tests clear the cache when they override the URL.

### Remaining production work (unchanged from README)

Real SSO, secrets management, production database, tamper-resistant audit
retention, DLP, vulnerability management, backups, monitoring, incident
response, and real financial-system integrations are all out of scope.
