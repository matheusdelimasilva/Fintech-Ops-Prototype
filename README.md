# Fintech Ops Console

Evaluation prototype of a reusable foundation for fintech internal tools containing:

- Refund Operations: queue, detail, approval/rejection/escalation, server-side
  approval limits, and audit history.
- Feature Flags: staging and production controls that reuse the same RBAC,
  audit, API, and UI foundations.

All identities and business data are synthetic. 

## Intended stack

| Layer | Choice |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | FastAPI, Python |
| Persistence | SQLite |
| Backend tests | Pytest |

## Current state

Backend: SQLite persistence (SQLAlchemy), deterministic synthetic seed data,
server-side demo identity resolution, read-only JSON endpoints for the session,
refunds, feature flags, and audit events, the refund workflow —
approve / reject / escalate with server-enforced approval limits, required
reasons, state transitions, and an audit event written in the same transaction
as the refund — and feature-flag updates with server-enforced environment
permissions, mandatory production confirmation, and the same atomic audit
write.

Frontend: application shell with hash navigation (`#/refunds`,
`#/refunds/<id>`, `#/feature-flags`, `#/feature-flags/<id>`, `#/audit`), a
demo-user switcher backed by `GET /api/session`, the Refund Operations module
— server-filtered queue (search, status, risk), detail view, approve / reject /
escalate forms with required reasons, buttons driven by the server's
`allowed_actions`, and the refund's audit trail with changed-field diffs — and
the Feature Flags module — environment-filtered list, detail, an edit form
shown only when the server reports `can_edit`, a production confirmation step
when the server reports `requires_confirmation`, and the flag's audit trail.
The standalone Audit Trail page is a placeholder.

## Prerequisites

- Python 3.10 through 3.13 (the pinned Pydantic release does not support Python 3.14)
- Node.js 22 (`nvm use` reads `.nvmrc`; Node 20.18 is too old for Vite 8)

## Local commands

### Backend (`backend/`)

```bash
cd backend
python3.13 -m venv .venv   # or another installed Python from 3.10 through 3.13
./.venv/bin/pip install -r requirements-dev.txt   # runtime deps only: requirements.txt
./.venv/bin/uvicorn app.main:app --reload --port 8000   # run on http://localhost:8000
./.venv/bin/pytest                                 # tests
./.venv/bin/ruff check .                           # lint
./.venv/bin/ruff format .                          # format
```

Health check: `curl http://localhost:8000/health` returns
`{"status":"ok","service":"fintech-ops-console-api"}`.
Interactive API docs: http://localhost:8000/docs (use **Authorize** to set the
demo user header).

Every `/api/*` request must carry an `X-Demo-User-Id` header naming one of the
server-defined synthetic users: `user_sam_support`, `user_olivia_ops`, or
`user_avery_admin`. The backend resolves role and permissions from that ID;
nothing else sent by the client is trusted. Example:

```bash
curl -H 'X-Demo-User-Id: user_olivia_ops' http://localhost:8000/api/session
curl -H 'X-Demo-User-Id: user_olivia_ops' 'http://localhost:8000/api/refunds?status=pending'
```

Refund actions are `POST /api/refunds/{id}/approve|reject|escalate` with a JSON
body `{"reason": "..."}` (non-blank, at most 1000 characters after trimming).
The response is the updated refund; its `allowed_actions` field is a UI hint
computed for the calling user, and every action is re-authorized on the server
regardless of it. Example — Sam (`$500` limit) attempting a `$500.01` refund:

```bash
curl -X POST -H 'X-Demo-User-Id: user_sam_support' -H 'Content-Type: application/json' \
  -d '{"reason": "Duplicate charge confirmed"}' http://localhost:8000/api/refunds/rfnd_003/approve
# 403 {"error": {"code": "APPROVAL_LIMIT_EXCEEDED", ..., "details": {"amount_cents": 50001, "approval_limit_cents": 50000, ...}}}
```

Feature-flag updates are `PATCH /api/feature-flags/{id}` with a JSON body
containing at least one of `enabled` (boolean) or `rollout_percent` (integer
0–100), a required non-blank `reason` (trimmed, at most 1000 characters), and
optionally `confirm_production` (boolean, default `false`). Types are strict:
`"true"`, `1`, and `"50"` are rejected, and an explicit `null` for a change
field is rejected rather than treated as omitted. Support agents cannot edit
any flag, operations managers may edit staging only, and admins may edit
staging and production; a production change is also refused unless
`confirm_production` is exactly `true`. Authorization is checked before the
confirmation, so an operations manager gets `403` on a production flag whether
or not they confirm. A request whose values equal the flag's current values is
`409 NO_CHANGE` and writes nothing. Each flag in the read responses carries
server-computed `can_edit` and `requires_confirmation` hints for the calling
user; PATCH re-checks both regardless. Example:

```bash
curl -X PATCH -H 'X-Demo-User-Id: user_avery_admin' -H 'Content-Type: application/json' \
  -d '{"enabled": false, "rollout_percent": 0, "reason": "Kill switch", "confirm_production": true}' \
  http://localhost:8000/api/feature-flags/flag_new_risk_scoring_production
# 200 {"id": "flag_new_risk_scoring_production", "enabled": false, "rollout_percent": 0, ..., "can_edit": true, "requires_confirmation": true}
```

Errors use a stable envelope: `{"error": {"code": "...", "message": "...", "details": {}}}`.
Codes in use: `MISSING_IDENTITY`, `UNKNOWN_IDENTITY` (401); `APPROVAL_LIMIT_EXCEEDED`,
`ACTION_NOT_PERMITTED_FOR_ROLE` (403); `NOT_FOUND` (404); `INVALID_STATE_TRANSITION`,
`NO_CHANGE`, `STALE_UPDATE` (409); `VALIDATION_ERROR`, `UNSUPPORTED_CURRENCY`,
`PRODUCTION_CONFIRMATION_REQUIRED` (422); `INTERNAL_ERROR` (500).

### Frontend (`frontend/`)

```bash
cd frontend
nvm use            # Node 22, from ../.nvmrc
npm install
npm run dev        # dev server on http://localhost:5173
npm run lint       # oxlint
npm test           # vitest (pure-function tests: API client, error presentation, formatters, router, audit diff, flag patch decision)
npm run build      # tsc -b && vite build (production build into dist/)
npm run preview    # serve the production build
```

The frontend calls the backend at `http://localhost:8000` by default; override
with the `VITE_API_BASE_URL` environment variable. Start the backend before the
frontend, otherwise the user switcher and queue report the API as unreachable.

The acting demo user is chosen in the header (default Sam Support) and stored in
`localStorage`; the browser sends only that user's ID in `X-Demo-User-Id`. Role,
approval limit, and per-refund `allowed_actions` shown in the UI all come from
the server. Actions the server does not allow are simply not offered; the
backend still re-authorizes every submitted action. Switching users keeps the
refund or flag selected in the URL hash (so the same record can be compared
across roles) and refetches everything for the new identity.

On the Feature Flags page the **Edit flag** button appears only when the
server's `can_edit` is true for the acting user, and the red production
confirmation block (with its checkbox gating the Confirm button) appears only
when the server's `requires_confirmation` is true; the browser does not derive
either rule from the flag's environment. The rollout input has no client-side
range check, so an out-of-range value reaches the server and its `422` is shown
through the shared error notice. Production flags are visually marked, and the
page states that they are synthetic and control no real system.

### Seed/reset

The backend uses a SQLite file at `backend/fintech_ops.db` (override with the
`DATABASE_URL` environment variable). On startup it creates the tables and
loads the deterministic synthetic dataset if the database is empty. To manage
it explicitly:

```bash
cd backend
./.venv/bin/python -m app.seed           # seed only if empty
./.venv/bin/python -m app.seed --reset   # drop everything and reseed to the known state
```

## Prototype limitations

This is deliberately not production-ready. It does not provide real SSO,
production secrets management, a production database, tamper-resistant audit
retention, DLP, vulnerability-management operations, backups, monitoring,
incident response, or real financial-system integrations.
