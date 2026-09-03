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
| 3 | Refund mutations, RBAC enforcement, atomic audit writes | [#4](https://github.com/matheusdelimasilva/Fintech-Ops-Prototype/pull/4) | In review |
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

## Checkpoint 3 — Refund mutations, RBAC enforcement, atomic audit writes (PR #4)

### Planning

Three-round design interview (29 decisions) before code. Decisions that bind
later checkpoints:

- Failure precedence: authentication → body validation → lookup →
  authorization → state transition. An unauthorized caller never learns the
  refund's state from the error; a missing identity wins over a bad body.
- Authorization is a pure function, `policy.refund_action_denial(role, action,
  amount_cents, currency) -> Denial | None`, with no database or HTTP
  dependency. The workflow service maps a `Denial` to the matching `403`/`422`.
- USD only. Any other currency fails closed (`422 UNSUPPORTED_CURRENCY`)
  rather than being compared against a USD limit.
- Admin may **not** escalate (escalation is a request for higher authority);
  support and operations may escalate any pending refund regardless of amount.
  A refund's `escalated` status never widens anyone's approval limit.
- Structured `403`s: `APPROVAL_LIMIT_EXCEEDED` carries `role, action,
  amount_cents, approval_limit_cents`; `ACTION_NOT_PERMITTED_FOR_ROLE` carries
  `role, action`. `409 INVALID_STATE_TRANSITION` carries `action,
  current_status, allowed_from`.
- Reason: Pydantic strips whitespace, then requires 1–1000 characters.
- The service owns the unit of work: one `commit()` after the refund update and
  the audit insert; any exception rolls back. Routes never commit.
- Stale-write guard: the transition is applied as `UPDATE ... WHERE id = ? AND
  refund_status IN (<allowed_from>)`; zero rows affected → `409`.
- One shared `audit.refund_snapshot(refund)` produces before/after state for
  seeded **and** live events; the seed builds historical "before" states by
  copying the snapshot and explicitly nulling the action fields.
- `RefundOut.allowed_actions` is a server-computed hint for the calling user
  from the same policy + transition tables; every mutation re-authorizes.
- Response is the updated `RefundOut` (same shape as GET); the audit event is
  read from `GET /api/audit-events?entity_id=...`.
- Skipped for now: exhaustive OpenAPI error declarations, a clock seam, and a
  request-body `expected_status`.

### Delivered

- `POST /api/refunds/{id}/approve`, `/reject`, `/escalate` with body
  `{"reason"}`; all three delegate to
  `refund_service.perform_refund_action(session, actor, refund_id, action, reason)`.
- `policy.py`: `RefundAction`, `Denial`, `refund_action_denial`, and
  `can_escalate_refunds` on the role policy (also exposed in `GET /api/session`).
- `refund_service.py`: declarative `ALLOWED_FROM` / `TARGET_STATUS` /
  `AUDIT_ACTION` maps, guarded conditional update, single commit,
  `allowed_actions(actor, refund)`.
- `audit.py`: `refund_snapshot` and `record_refund_event` (`evt_<uuid4 hex>` IDs;
  `occurred_at == refund.last_action_at == refund.updated_at`). Only GET
  routes exist for audit events.
- `errors.py`: `ApprovalLimitExceededError`, `ActionNotPermittedForRoleError`,
  `UnsupportedCurrencyError`, and a catch-all handler so unexpected failures
  return `500 INTERNAL_ERROR` in the standard envelope with no details leaked.
- Seed audit events reshaped to the shared 8-key snapshot (adds `last_action*`).
- README: current state, mutation usage, and the full error-code list.

### Commands run and results

```bash
cd backend
./.venv/bin/pytest                      # 131 passed
./.venv/bin/ruff check .                # All checks passed
./.venv/bin/ruff format --check .       # 26 files already formatted

cd frontend && nvm use 22
npm run lint                            # clean (frontend untouched)
npm run build                           # built (frontend untouched)
```

Live `uvicorn` smoke run against a fresh SQLite file (`curl`):

| Request | Result |
|---|---|
| Sam `POST /api/refunds/rfnd_003/approve` (50001 cents) | `403 APPROVAL_LIMIT_EXCEEDED`, `details.approval_limit_cents = 50000` |
| Sam `POST .../rfnd_003/escalate` with reason `"  above my limit  "` | `200`, status `escalated`, stored reason `"above my limit"`, `allowed_actions: []` |
| Olivia `POST .../rfnd_003/approve` (escalated, within her limit) | `200`, status `approved` |
| Olivia repeats the approve | `409 INVALID_STATE_TRANSITION`, `allowed_from: ["escalated","pending"]` |
| Sam `POST .../rfnd_001/approve` with reason `"   "` | `422 VALIDATION_ERROR` (`string_too_short`) |
| `GET /api/audit-events?entity_id=rfnd_003` | two events, `pending→escalated` then `escalated→approved`, newest first |

### Automated test coverage (131 tests, up from 30; most new cases are parametrized)

`test_refund_policy.py` (pure, no DB): inclusive limits for approve and reject
at 49999 / 50000 / 50001 / 500000 / 500001 per role; support/ops may escalate
any amount; admin may not escalate; every role × action fails closed on `EUR`.

`test_refund_service.py` (service, fresh session for every assertion): success
commits the refund and exactly one audit event with matching timestamps and a
before/after pair of identical shape; a failing audit recorder rolls back the
refund update; `403` / `409` / `404` leave the row and audit count unchanged;
the stale-write guard (below); `allowed_actions` combines policy and
transition legality.

`test_refund_mutations.py` (HTTP): limit boundaries via the API for both
approve and reject; escalate allowed / forbidden by role; escalated refunds
still respect limits; all illegal transitions from `approved`, `rejected`, and
`escalated`; repeating a completed action; eight invalid-reason bodies
(including 1001 chars and 1001 chars padded with whitespace); 1- and
1000-character reasons stored stripped in both the refund and the audit event;
ordering (`401` beats bad body, `403` beats bad state, `404` for unknown id);
browser-supplied role/limit headers and body fields ignored; the complete
before/after audit event compared field-by-field and key-set-compared against a
seeded event; `500 INTERNAL_ERROR` envelope with nothing persisted when the
audit write fails (`raise_server_exceptions=False`); `allowed_actions` per user
on pending / escalated / approved refunds in list and detail, shrinking after
each mutation.

`test_identity.py`: the identity guard is now derived from the OpenAPI schema —
every `/api/*` operation (10, including the three POSTs) returns `401` without
the header, so a new route without the dependency fails the suite.

`test_seed.py`: seeded audit `after_state` equals `refund_snapshot(row)` and
`before_state` has the same keys; reset determinism still holds.

### Stale-write guard — what the test does and does not show

`test_stale_write_is_rejected_by_the_guarded_update` runs two real sessions
through the real service: session A loads and authorizes `rfnd_001`; before A's
guarded `UPDATE` executes, session B approves the same refund and commits; A's
`UPDATE` matches zero rows and the service raises `409` with
`current_status: approved`. Afterwards the refund carries B's action and exactly
one new audit event exists. The interleaving point is injected by monkeypatching
the snapshot call the service makes between load and update.

This proves the conditional update detects a state change made by another
session before the write. It is **not** a concurrency or load test: it does not
exercise SQLite's locking, threads, or overlapping write transactions. The
race between two truly simultaneous writers is bounded by SQLite's single-writer
lock plus this guard, but that path has not been exercised.

### Human interventions

- Design interview: 29 decisions answered by the project owner; the owner
  changed four recommendations (failure precedence puts authentication first;
  the policy function takes `role` and `currency`; no `**overrides` on the
  snapshot helper; tests ship with the behavior they cover rather than in a
  trailing commit) and added five test cases (reason-length boundaries,
  stripped-reason equality across refund and audit, complete snapshot-shape
  comparison, `raise_server_exceptions=False`, and honest scoping of the
  guard test).
- The evidence ledger (PR #3) had not been merged when this checkpoint began,
  so its branch was merged into this one to append here; if #3 merges first the
  diff of #4 shrinks to this checkpoint alone.

### Limitations at this checkpoint

- No UI exists yet; every check above is API-level. Browser verification of
  the refund workflow is deferred to checkpoint 4.
- Feature-flag mutations, environment-specific authorization, and production
  confirmation are not implemented; the flag policy fields exist only as data.
- Concurrency: see the guard section above.
- The audit trail is append-only through the application only; SQLite offers no
  tamper evidence. There is no audit event for denied attempts (by design in the
  plan: failed requests must not create a success event; a separate
  security-event log is out of scope).
- Timestamps are naive UTC in SQLite and serialized with a `Z` suffix.
- Identity remains a plain header with no authentication, session, or CSRF story.
