# Prototype evidence ledger

Running record of what has been built, how it was verified, where a human
intervened, and what is still missing. Append a section per checkpoint; do not
rewrite earlier sections.

All data and identities in this prototype are synthetic. Identity is a demo
user ID header resolved server-side; there is no real authentication.

**Elapsed milestones.** Wall-clock effort per checkpoint was not captured for
checkpoints 1–3; the agent sessions that produced them were interrupted and
resumed, so no reliable start/stop times exist. The only timing evidence is the
commit history (`git log --format='%h %ci %s'`), which records when each layer
was committed, not how long it took. Later checkpoints should record start and
end times explicitly.

## Checkpoint index

| # | Checkpoint | PR | Status |
|---|---|---|---|
| 1 | Runnable skeleton (scaffold + `/health`) | [#1](https://github.com/matheusdelimasilva/Fintech-Ops-Prototype/pull/1) | Merged |
| 2 | Backend foundation: persistence, seed, demo identity, read-only API | [#2](https://github.com/matheusdelimasilva/Fintech-Ops-Prototype/pull/2) | Merged |
| 3 | Refund mutations, RBAC enforcement, atomic audit writes | [#4](https://github.com/matheusdelimasilva/Fintech-Ops-Prototype/pull/4) | Merged |
| 4 | Frontend shell + Refund Operations UI | [#5](https://github.com/matheusdelimasilva/Fintech-Ops-Prototype/pull/5) | Merged |
| 5 | Feature Flags end-to-end (reuse proof) | [#6](https://github.com/matheusdelimasilva/Fintech-Ops-Prototype/pull/6) | In review |
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
  refund_status = <status the service observed and snapshotted>`; zero rows
  affected → `409`. Review of the first version (which matched any allowed
  source status) found that an interleaved `pending → escalated` would let a
  later reject succeed while its audit event claimed `pending → rejected`; the
  guard now requires the exact observed status so `before_state` is always the
  true immediate predecessor.
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
- `refund_service.py`: one immutable `Transition(allowed_from, target,
  audit_action)` per action in `TRANSITIONS`, exact-status guarded update,
  single commit, `allowed_actions(actor, refund)`. Denial codes map to error
  classes and user-facing messages here, so `Denial` itself is just
  `(code, details)`.
- `audit.py`: `refund_snapshot` and `record_refund_event` (`evt_<uuid4 hex>` IDs;
  `occurred_at == refund.last_action_at == refund.updated_at`). Only GET
  routes exist for audit events. Timestamp formatting lives in a neutral
  `timeutil.py` shared by audit, service, and API schemas, so audit does not
  import from the presentation layer.
- `errors.py`: `ApprovalLimitExceededError`, `ActionNotPermittedForRoleError`,
  `UnsupportedCurrencyError`, and a catch-all handler so unexpected failures
  return `500 INTERNAL_ERROR` in the standard envelope with no details leaked;
  the underlying exception is logged server-side with `logger.exception`.
- Seed audit events reshaped to the shared 8-key snapshot (adds `last_action*`).
- README: current state, mutation usage, and the full error-code list.

### Commands run and results

```bash
cd backend
./.venv/bin/pytest                      # 153 passed
./.venv/bin/ruff check .                # All checks passed
./.venv/bin/ruff format --check .       # 27 files already formatted

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

### Automated test coverage (153 tests, up from 30; most new cases are parametrized)

`test_refund_policy.py` (pure, no DB): the full role × {approve, reject} ×
{49999, 50000, 50001, 500000, 500001} matrix (30 cases) with the complete
`details` payload asserted on every denial; role × escalate × the same five
amounts (admin denied, others allowed regardless of amount); admin has no upper
bound; every role × action fails closed on `EUR`.

`test_refund_service.py` (service, fresh session for every assertion): success
commits the refund and exactly one audit event with matching timestamps and a
before/after pair of identical shape; a failing audit recorder rolls back the
refund update; `403` / `409` / `404` leave the row and audit count unchanged;
the two stale-write guard tests (below); `allowed_actions` combines policy and
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
audit write fails (`raise_server_exceptions=False`), while `caplog` shows the
real exception logged at ERROR with method and path and absent from the
response body; `allowed_actions` per user
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

`test_guard_rejects_a_stale_snapshot_even_when_the_new_status_also_allows_the_action`
is the review-found case: A snapshots `pending`; B escalates and commits; A
rejects. Because `escalated` is itself a legal source for reject, a guard on
"any allowed status" let A through and recorded `pending → rejected` for what
was really `escalated → rejected`. With the exact-status guard A gets `409`
with `current_status: escalated`, the only event is `pending → escalated`, and
A's retry against the current row records `escalated → rejected`. The test was
run against the old guard to confirm it fails there.

Both tests prove the conditional update detects a state change made by another
session before the write. They are **not** concurrency or load tests: they do
not exercise SQLite's locking, threads, or overlapping write transactions. The
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
- PR #4 review by the project owner found nine issues, fixed before merge:
  the guard matched any allowed source status instead of the observed one
  (P1, reproduced by the owner with an escalate-then-reject interleave); the
  catch-all handler discarded the exception instead of logging it; `audit.py`
  imported `to_utc_iso` from the API schema module; the three transition maps
  were consolidated into one `Transition` record per action; `Denial` dropped
  the `message` field to match the agreed `(code, details)` shape; the policy
  matrix was widened to the full role × action × five-amount table; the
  Python 3.10–3.13 README/`.python-version` change from `main` was merged in;
  and this ledger gained the elapsed-milestones statement above.
- The owner declined a Swagger `/docs` browser run for this backend-only
  checkpoint; verification is `pytest` plus the `curl` smoke run above.

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

## Checkpoint 4 — Frontend shell + Refund Operations UI (PR #5)

### Planning

Two-round design interview (15 decisions; the owner ended it early because the
third round had no open questions). Decisions that bind later checkpoints:

- No new runtime dependencies. Navigation is a ~40-line hash router
  (`#/refunds`, `#/refunds/<id>`, `#/feature-flags`, `#/audit`); data loading
  is a narrow `useQuery(fetcher, key, {isEmpty})` hook with abort on
  key change, `reload()`, and `setData()`. "Empty" is a caller-supplied
  predicate, not an array assumption.
- Identity is a React context (`IdentityProvider`) persisted to `localStorage`
  (default `user_sam_support`). A low-level `createApiClient(userId)` is the
  only place that sets headers; the context-bound `useApiClient()` sits above
  it, so the provider never consumes its own context. If the stored id is
  unknown to the server the switcher shows the `401` and offers "Reset to Sam
  Support"; the roster itself always comes from `/api/session`.
- Error contract: `ApiError {status, code, message, details}`. Backend
  envelopes keep their code/details; a non-JSON or un-enveloped HTTP response
  is `INVALID_RESPONSE` **with its HTTP status preserved**; `NETWORK_ERROR`
  (status 0) is reserved for a rejected `fetch`; anything else thrown on a
  request path (a programming error) is normalized once, by `toApiError`, to
  `UNEXPECTED_ERROR` so bugs are never reported as connectivity. A pure
  `describeApiError(error)` chooses the heading from status/code only — no
  message-string parsing — and formats `*_cents` details as money.
- Actions the server does not list in `allowed_actions` are **hidden**, with a
  generic "Available actions are determined by server policy" note. The owner
  rejected composing a limit-based explanation in the UI because
  `allowed_actions` alone cannot say *why* (limit, role, or state); a
  `denied_actions` API extension is noted as a possible follow-up.
- Reason form: Confirm is disabled while the trimmed reason is empty (UX only);
  no client `maxLength`, so a 1,001-character reason reaches the server and
  exercises the `422` rendering path.
- After `200`: detail replaced by the response, queue refetched with current
  filters, audit refetched, form closed, dismissible banner built from the
  returned `last_action` / `last_action_by` / `last_action_at` (never from the
  current identity). The banner lives in a shared `NoticesProvider` keyed by
  `refund:<id>`, so it survives switching refunds, pages, or users and
  disappears only on Dismiss or when a new action is submitted for that refund. After `409`: structured notice plus automatic refetch of
  refund and audit; a form whose action is no longer in the refreshed
  `allowed_actions` closes. Other errors keep the form and reason for retry.
- Filters (search debounced 300 ms; status/risk immediate) are query params on
  `GET /api/refunds`; nothing is filtered client-side. The selected refund
  lives in the hash; filters do not.
- Timestamps render in UTC inside `<time datetime>`; money via a shared
  `formatMoney(cents, currency)` that never converts cents to a float.
- Plain CSS, semantic tables, `aria-current` navigation, labelled controls,
  visible focus rings, `role="alert"` for errors and `role="status"` for
  non-urgent updates.
- Vitest (pinned `4.1.11`, no jsdom / Testing Library) was approved for pure
  units only; `npm test` joins the gate.

### Delivered

- `frontend/src/api/`: `types.ts` mirrors `schemas.py`; `client.ts` exposes
  `createApiClient(userId)` with `getSession`, `listRefunds(filters)`,
  `getRefund`, `performRefundAction`, `listRefundAuditEvents`, and feature-flag
  reads. Only `Accept`, `Content-Type` (JSON bodies), and `X-Demo-User-Id` are
  sent.
- `frontend/src/shared/`: `useQuery`, `describeApiError`, `format`
  (`formatMoney`, `formatApprovalLimit`, `formatTimestamp`, `formatDate`,
  labels), `ErrorNotice` (alert, structured details, code + HTTP status,
  retry/refresh, dismiss), `StatusBanner` (status), `LoadingState`,
  `EmptyState`.
- `frontend/src/identity/`: `IdentityProvider`, `context.ts` (`useIdentity`,
  `useApiClient`), `UserSwitcher` showing server-provided display name, role,
  approval limit, and "may escalate refunds".
- `frontend/src/router.ts`, `App.tsx` (title, primary nav, synthetic-data
  banner, switcher; `<main>` keyed by user id so switching users remounts
  the page — open forms, filters, and cached results are dropped and refetched
  for the new identity. The **hash-selected refund is deliberately kept**, so
  the same refund can be compared across roles; only its `allowed_actions`
  change).
- `frontend/src/refunds/`: `RefundsPage`, `RefundFilters`, `RefundQueue`
  (transaction, customer, amount, risk, status, created), `RefundDetailPanel`
  (keyed per refund id; detail + audit queries, action state, 200/409
  handling), `RefundDetail`, `RefundActionForm`.
- `frontend/src/audit/`: `changedFields` (pure diff) and `AuditEventList`
  (newest first; actor, role, user id, action, UTC time, reason, changed-field
  table, raw before/after JSON behind `<details>`). Domain-neutral so Feature
  Flags and the Audit Trail page can reuse it.
- Feature Flags and Audit Trail routes render "Not implemented in this
  checkpoint".
- README: current state, `npm test`, identity/`allowed_actions` behaviour.

### Commands run and results

```bash
cd frontend && nvm use 22
npm run lint                            # oxlint: clean
npm test                                # vitest: 5 files, 48 tests passed
npm run build                           # tsc -b && vite build: built

cd backend
./.venv/bin/pytest                      # 153 passed (unchanged)
./.venv/bin/ruff check .                # All checks passed
./.venv/bin/ruff format --check .       # already formatted
```

`npm install --save-dev --save-exact vitest@4.1.11` failed inside npm's
Arborist (`Cannot read properties of null (reading 'edgesOut')`) while resolving
Vitest's optional browser peer dependencies; `--legacy-peer-deps` for that one
install succeeded, after which a clean `npm ci` reproduces `node_modules`
from the committed lockfile without flags.

### Automated frontend tests (48, all pure functions, Node environment)

- `api/client.test.ts`: successful JSON; backend envelope → `ApiError` with
  code/message/details preserved; non-JSON error body and non-JSON 200 body →
  `INVALID_RESPONSE` with the HTTP status kept; JSON error without the envelope
  → `INVALID_RESPONSE`; only `X-Demo-User-Id` is added as a caller header;
  action bodies are `{reason}`; a rejected `fetch` → `NETWORK_ERROR` status 0;
  `toApiError` passes `ApiError` through and labels other throwables
  `UNEXPECTED_ERROR`; `AbortError` propagates untouched.
- `shared/describeApiError.test.ts`: 401/403/404/409/422/500/`NETWORK_ERROR`/
  `INVALID_RESPONSE`/`UNEXPECTED_ERROR` headings (409 is the domain-neutral
  "Record has changed") chosen from status/code even when the message
  text is misleading; `403` details render `approval_limit_cents` as `$500.00`;
  `409` suggests refresh; `422` validation errors flattened.
- `shared/format.test.ts`: `$0.00`, `$0.01`, `$500.00`, `$500.01`,
  `$5,000.00`, `$5,000.01`, large and negative values without float drift;
  `Unlimited`; UTC timestamp/date; invalid input passthrough.
- `audit/changedFields.test.ts`: only differing keys, keys present on one side
  only, identical snapshots, display formatting.
- `router.test.ts`: every hash form, unknown-route fallback, id round trip.

### Direct HTTP evidence (fresh seed, `curl` against `uvicorn`)

These pair with the UI: Sam's detail view for `rfnd_003` ($500.01) offers only
**Escalate**, so the `403` below is unreachable from the UI by design and is
shown here as the server still enforcing it when asked directly.

| Request | Result |
|---|---|
| Sam `POST /api/refunds/rfnd_003/approve` | `403 APPROVAL_LIMIT_EXCEEDED`, `details: {role: support_agent, action: approve, amount_cents: 50001, approval_limit_cents: 50000}` |
| Sam `POST .../rfnd_001/approve` with a 1,001-character reason | `422 VALIDATION_ERROR`, `details.errors[0].type = string_too_long` |
| Sam `POST .../rfnd_003/escalate` twice | `200` then `409 INVALID_STATE_TRANSITION`, `current_status: escalated`, `allowed_from: ["pending"]` |
| `GET /api/refunds` with no header | `401 MISSING_IDENTITY` |

### Browser observations (agent smoke check during implementation)

A short manual pass in Chrome against the dev servers, before the owner asked
the agent to stop taking screenshots: as Sam, `#/refunds/rfnd_003` rendered the
switcher (Support Agent, `$500.00`, may escalate: Yes), the 12-row queue, and a
detail panel offering only **Escalate**. Confirming an escalation with a reason
replaced the detail (status Escalated, last action by Sam Support), updated the
queue row without a reload, showed the success banner, changed the actions
area to "No actions are available to you for this refund", and listed one audit
event with a five-row changed-fields table (`pending → escalated` plus the four
`last_action*` fields). The browser console showed only Vite/React dev-mode
info messages. The database was reset to the seed afterwards.

**Not verified in the browser by the agent** (the owner chose to run these
themselves): Olivia and Avery identities, Olivia approving the escalated refund,
the two-tab `409`, the 1,001-character `422` rendering, and the empty-search
state. The corresponding rendering paths are covered by the unit tests above
and the backend responses by the `curl` table.

### Elapsed milestones

The checkpoint spanned one agent session with a context reset between the design
interview and implementation, so wall-clock effort was again not captured
reliably. Branch commit timestamps (`git log --format='%h %ci %s' main..`)
place the four implementation commits within roughly 10 minutes of each other on
2026-09-03 (UTC); the shared foundations had been written before the first of
them was committed, so that span understates the work.

### Human interventions

- Design interview: 15 decisions answered by the project owner; the owner
  amended five recommendations (non-JSON responses are `INVALID_RESPONSE`, not
  `NETWORK_ERROR`; hide denied actions instead of composing a limit-based
  explanation; build success text from returned metadata; the provider must
  not consume its own context; `curl` rather than DevTools for the direct-403
  evidence, plus a pure presentation function for unit tests).
- The owner asked the agent to stop computer-use screenshots and to leave
  browser verification to them; the testing-agent run planned for this
  checkpoint was therefore not performed.

### Limitations at this checkpoint

- The UI cannot explain *why* an action is unavailable; it only knows the
  server's `allowed_actions`. A `denied_actions: [{action, code, details}]`
  field on `RefundOut` would let it, and is the one API awkwardness surfaced
  by this slice.
- Feature Flags and the standalone Audit Trail pages are placeholders.
- Frontend tests cover pure functions only; component behaviour (form gating,
  409 refetch, form auto-close) is exercised manually, not by automated tests.
- Filters are not persisted in the URL; reloading returns to unfiltered.
- Refund ids appear in the hash; deep links to a refund another user may not
  act on simply show no actions. The selection survives a user switch (the
  round-1 design note said it would clear; keeping it was judged more useful
  for comparing roles and the code/docs now agree).
- The post-mutation banner reads "refreshing queue and audit trail…" until
  both refetches settle, then "refreshed"; a failed refetch is reported by the
  queue/audit error notices, not by the banner.
- No optimistic UI, pagination, or polling; the queue refetches only after the
  current user's own mutation or a filter change, so another tab's change
  surfaces as a `409` on submit rather than proactively.

### Review follow-up (same PR)

Owner review after the PR opened found: the ledger claimed switching users
clears the hash-selected refund (it does not); refund-specific wording in the
shared `409` heading; unexpected-error normalization duplicated in `useQuery`
and `RefundDetailPanel`, both mislabelling programming failures as network
failures; unused `useQuery.enabled`; the success banner claiming refreshes had
completed while they were in flight. Resolution: keep the selection (better for
comparing roles) and fix the docs; "Record has changed"; single `toApiError` →
`UNEXPECTED_ERROR`; `enabled` removed; banner reads "refreshing…" until the
queue and audit queries settle. Gates re-run: oxlint clean, vitest 48, build
ok, pytest 153.

Owner browser feedback (same PR): Approve is now green, Escalate grey (Reject
stays red) via a shared `REFUND_ACTION_TONE` map used by both the action buttons
and the confirm button; the refund detail renders as two label/value tables
(`<th scope="row">`) instead of a flat `<dl>`; the success banner persists
until Dismiss (see above) instead of being lost when the detail panel remounts.
Gates re-run: oxlint clean, vitest 48, build ok.

## Checkpoint 5 — Feature Flags end-to-end (PR #6)

### Planning

One-round design interview (8 decisions, all accepted, four with amendments)
after PR #5 merged; the branch was cut from the merged `main`, not from the
review branch. Decisions that shaped the implementation:

- `PATCH /api/feature-flags/{id}` body: optional `enabled` / `rollout_percent`
  (at least one required), required trimmed `reason` (the same `ActionReason`
  type as refunds), `confirm_production` defaulting to `false`. Owner
  amendment: explicit `null` for a change field must be rejected or
  consistently treated as omitted — it is **rejected** (`422`).
- No-op requests are `409 NO_CHANGE` with `details.current`, so "every
  successful mutation writes exactly one audit event" holds without lying about
  an update. Owner amendment: the UI maps this code to "No changes to apply",
  not the shared 409 heading — `describeApiError` became code-aware.
- Authorization is checked **before** production confirmation; a missing
  confirmation for an authorized admin is `422 PRODUCTION_CONFIRMATION_REQUIRED`
  (a `ValidationError` subclass), never `403`. Staging ignores the flag.
- Pure `feature_flag_edit_denial(role, environment)` in `policy.py` reusing
  `ACTION_NOT_PERMITTED_FOR_ROLE`; service mirrors the refund shape (load →
  authorize → confirm → no-op check → guarded `UPDATE` → audit → one commit).
- `FeatureFlagOut` carries server-computed `can_edit` and
  `requires_confirmation`. They are hints; PATCH re-checks both.
- `record_refund_event` generalized into one domain-neutral `record_event`
  used by both services; `feature_flag_snapshot` added. Owner amendment: the
  concurrency guard must not rely on clock uniqueness alone — the conditional
  `UPDATE` matches the observed `enabled`, `rollout_percent`, **and**
  `updated_at`, and a test drives a `50 → 60 → 50` interleaving to show that
  restoring the observed values does not slip past the timestamp check.
- UI: same split layout as refunds; Confirm disabled until the production box
  is ticked; consequence accepted that "production without confirmation → 422"
  is unreachable from the UI (like the refund 403) and is proven by tests and
  `curl`. Owner amendment on notices: reuse the existing pattern rather than
  adding a second one — the `NoticesProvider` introduced for the "banner must
  survive until Dismiss" request already existed, so flags use it keyed by
  `feature_flag:<id>`.
- Success banner is timestamp-only ("Feature flag updated at …"); the actor is
  read from the refreshed audit event, never inferred from the current identity.

### Delivered

Backend (three commits, each green on its own):

- `policy.py`: `feature_flag_edit_denial`, `ROLLOUT_MIN` / `ROLLOUT_MAX`
  (moved here so the schema does not import the service).
- `audit.py`: `record_event(session, *, actor, action, entity_type, entity_id,
  before_state, after_state, reason, occurred_at)`; `refund_service.py` now
  calls it, and `feature_flag_snapshot` sits beside `refund_snapshot`.
- `feature_flag_service.py`: `FlagChanges`, `update_feature_flag`, `can_edit`,
  `requires_confirmation`; guarded `UPDATE ... WHERE id = ? AND enabled = ? AND
  rollout_percent = ? AND updated_at = ?`; `NoChangeError` (409) and
  `StaleUpdateError` (409) added to `errors.py` beside
  `ProductionConfirmationRequiredError` (422).
- `schemas.py`: `FeatureFlagPatch` with `StrictBool` / `StrictInt` (so
  `"true"`, `1`, `"50"` are rejected — `confirm_production` must be a literal
  JSON `true`), explicit-`null` rejection, at-least-one-change validator;
  `FeatureFlagOut` gains `can_edit`, `requires_confirmation`.
- `routes_feature_flags.py`: `PATCH /{flag_id}`; list and detail responses
  computed per calling user.

Frontend (one commit):

- `api/client.ts`: `listFeatureFlags(filters)`, `getFeatureFlag`,
  `updateFeatureFlag(id, patch)` (`PATCH`), and a generic
  `listAuditEvents(entityType, entityId)` that the refund panel now uses too.
- `router.ts`: `#/feature-flags/<id>` selection, `featureFlagHash`.
- `shared/describeApiError.ts`: code-aware headings (`NO_CHANGE` → "No changes
  to apply", `STALE_UPDATE` / `INVALID_STATE_TRANSITION` → "Record has
  changed", `PRODUCTION_CONFIRMATION_REQUIRED`); still status/code only.
- `shared/format.ts`: `ENVIRONMENT_LABELS`, `formatEnabled`, `formatRollout`.
- `shared/ReasonField.tsx` and `shared/DetailsTable.tsx` extracted from the
  refund components and used by both modules.
- `featureFlags/`: `FeatureFlagsPage` (environment filter as a query param),
  `FeatureFlagTable`, `FeatureFlagDetail`, `FeatureFlagDetailPanel` (detail +
  audit queries via `useQuery`, 200/409 handling identical in shape to refunds,
  notice via `NoticesProvider`, `AuditEventList`), `FeatureFlagEditForm`, and
  the pure `buildFlagPatch.ts` (`decidePatch`) that decides what to send.
- Production distinction: red `Production` tag, red left border on production
  rows, red confirmation block reading "This changes a **production** flag.
  Prototype only: no real system is affected." Detail rows and the page
  header repeat that the flags are synthetic.

Reuse check (AGENTS.md asks for remaining duplication to be reported): the
flags panel reuses `useApiClient`, `useQuery`, `toApiError`, `ErrorNotice`,
`StatusBanner`, `NoticesProvider`, `LoadingState` / `EmptyState`,
`AuditEventList`, `ReasonField`, `DetailsTable`, and the formatters. What is
still duplicated between `RefundDetailPanel` and `FeatureFlagDetailPanel` is
the ~30-line mutation sequence (pending flag, clear error, call, `setData`,
record notice, reload audit, 409 → refetch). Both are small enough that a
shared `useMutation` hook was not judged worth its abstraction yet; noted as a
follow-up rather than done speculatively.

### Commands run and results

```bash
cd backend
./.venv/bin/ruff check .                # All checks passed
./.venv/bin/ruff format --check .       # already formatted
./.venv/bin/pytest                      # 227 passed (153 before; +74)

cd frontend && nvm use 22
npm run lint                            # oxlint: clean
npm test                                # vitest: 6 files, 64 tests passed (48 before; +16)
npm run build                           # tsc -b && vite build: built

git diff --check                        # clean
```

The refund service and API suites (63 tests) were re-run on their own after the
`record_event` generalization, before the feature-flag service was added, and
passed unchanged.

### Automated backend tests (74 new)

- `test_feature_flag_policy.py`: role × environment matrix for
  `feature_flag_edit_denial` (support denied everywhere, ops staging only,
  admin both) and agreement with the `can_edit_*_flags` booleans already served
  by `/api/session`.
- `test_feature_flag_service.py`: success commits the flag and exactly one
  audit event with full before/after snapshots; admin production update with
  confirmation; parametrized failure paths (support/ops role denials, missing
  confirmation, no-op, unknown flag) each leave the flag row **and** the audit
  count untouched; `NO_CHANGE` details report current values; a monkeypatched
  `record_event` raising after the flag `UPDATE` rolls the flag back; stale
  write rejected by the guarded update; the `50 → 60 → 50` interleaving is
  still rejected because `updated_at` moved; capability hints follow policy;
  `FlagChanges` validation.
- `test_feature_flag_mutations.py` (API): environment permissions for all
  three users on staging and production; browser-supplied role/limit headers
  ignored; missing identity wins over an invalid body; production change with
  `false`, omitted, `"true"`, and `1` all `422 PRODUCTION_CONFIRMATION_REQUIRED`;
  ops gets `403` on production even with confirmation; staging ignores the
  flag; rollouts `0` and `100` succeed; `-1`, `101`, `"50"`, `12.5`, explicit
  `null`, empty body, missing / blank / whitespace-only / 1,001-character
  reasons all `422` and change nothing; 1- and 1,000-character reasons succeed
  and are stored trimmed; no-op is `409 NO_CHANGE` with no write; repeating a
  completed update is `409`; unknown flag `404`; a successful update writes
  exactly one event with the expected `before_state` / `after_state`,
  `reason`, actor, and entity fields; partial updates leave the other field
  alone; reads expose `can_edit` / `requires_confirmation` per user.
- `test_identity.py`: OpenAPI operation count updated to 11 (the new PATCH).

### Automated frontend tests (16 new, pure functions)

- `featureFlags/buildFlagPatch.test.ts`: draft starts from the loaded flag;
  no change → `no_change`; changed field without a reason → `reason_required`
  (blank / whitespace); only differing fields are sent, reason trimmed; `-1`,
  `101`, `12.5`, `100`, `0` are all **sent** (range and integer-ness are the
  server's call); only a non-numeric rollout is gated client-side; production
  gating follows `requires_confirmation` from the server, and
  `confirm_production: true` is sent only after the box is ticked and never for
  a flag that did not require it.
- `shared/describeApiError.test.ts`: `NO_CHANGE`, `STALE_UPDATE`,
  `PRODUCTION_CONFIRMATION_REQUIRED` headings; generic `VALIDATION_ERROR`
  unchanged.
- `shared/format.test.ts`: `formatEnabled`, `formatRollout`.
- `router.test.ts`: `#/feature-flags`, `#/feature-flags/<id>`, round trip.

### Direct HTTP evidence (fresh seed, `curl` against `uvicorn` on a scratch DB)

| Request | Result |
|---|---|
| Olivia `PATCH .../flag_new_risk_scoring_production` with `confirm_production: true` | `403 ACTION_NOT_PERMITTED_FOR_ROLE`, `details.editable_environments: ["staging"]` |
| Avery `PATCH .../flag_new_risk_scoring_production` without confirmation | `422 PRODUCTION_CONFIRMATION_REQUIRED`, `details.environment: production` |
| Olivia `PATCH .../flag_bulk_export_staging` `rollout_percent: 101` | `422 VALIDATION_ERROR`, `less_than_equal` on `body.rollout_percent` |
| Olivia `PATCH .../flag_bulk_export_staging` `rollout_percent: 50` (current) | `409 NO_CHANGE`, `details.current: {enabled: true, rollout_percent: 50}` |
| Olivia `PATCH .../flag_bulk_export_staging` `rollout_percent: 75`, reason `"  widen  "` | `200`, `rollout_percent: 75`, new `updated_at`, `can_edit: true` |
| `GET /api/audit-events?entity_type=feature_flag&entity_id=flag_bulk_export_staging` | one `feature_flag.updated` event by Olivia Ops, reason `widen`, `before_state.rollout_percent: 50` → `after_state.rollout_percent: 75` |
| Sam `GET /api/feature-flags` | every flag `can_edit: false`; `requires_confirmation` true only for the two production flags |

The scratch database was deleted afterwards; the committed seed is unchanged.

### Browser verification

**Not performed by the agent.** The owner stated they will verify in the
browser themselves, so no screenshots, recordings, or console checks are
claimed here. Rendering decisions that would otherwise be shown in the browser
(`NO_CHANGE` heading, form gating, what the client sends) are covered by the
pure tests above; server behaviour by the API tests and the `curl` table.
Suggested owner pass: Sam sees no **Edit flag** button on any flag; Olivia sees
it on staging only; Avery sees it on both, with the red confirmation block and
a disabled Confirm on production until the box is ticked; `101` in the rollout
field shows the shared `422` notice; resubmitting current values shows "No
changes to apply"; a successful save updates the list row, the detail, the
banner, and the audit list without a reload.

### Elapsed milestones

PR #5 merged at 2026-09-04 00:25 UTC. The four implementation commits on this
branch are timestamped 00:50, 00:52, 00:54, and 01:01 UTC (`git log
--format='%h %ci %s' main..`); the design interview and the backend/service
work preceded the first commit, so the ~36 minutes from merge to the frontend
commit is the closest honest wall-clock figure for this checkpoint. Docs and
gates followed immediately after.

### Human interventions

- Design interview: 8 decisions, all accepted; owner amendments on explicit
  `null` handling, code-aware 409 wording, the concurrency guard (observed
  values, not the clock alone), and not adding a second notice mechanism.
- Owner asked that the PR #5 review corrections land before this work built
  on them (they had already merged) and that refund tests be re-run explicitly
  after generalizing the audit recorder (done).
- Browser verification is owned by the project owner for this checkpoint.

### Limitations at this checkpoint

- `FeatureFlag` has no `last_updated_by` / reason columns; the list and detail
  show only `updated_at`, and the actor is visible only in the audit list.
- "Production without confirmation → 422" and "role not permitted → 403" are
  unreachable from the UI by design (Confirm is disabled; the button is not
  rendered). They are proven by tests and `curl`, not by clicking.
- The UI gates a non-numeric rollout (`""`, `abc`) client-side because a
  `type="number"` input cannot submit those; everything numeric, including
  `12.5`, is sent so the server's `422` is the visible outcome.
- The mutation sequence in the two detail panels is still duplicated (see the
  reuse check above).
- Component behaviour (button visibility per role, confirmation gating,
  post-save refresh) is not covered by automated UI tests; it is left to the
  owner's browser pass.
- The standalone Audit Trail page remains a placeholder.
- The audit trail is append-only through the application only: nothing
  prevents direct SQLite edits, and there is no hash chain, WORM storage, or
  external log shipping.

### Remaining production work

Unchanged from the README: real SSO and identity, secrets management, a
production database with migrations, tamper-resistant audit retention, DLP,
monitoring/alerting, backups, incident response, and real integrations. For
flags specifically: a real flag-evaluation service, per-segment targeting,
scheduled rollouts, and approval workflows (two-person rule) for production
changes — none of which this prototype claims to provide.
