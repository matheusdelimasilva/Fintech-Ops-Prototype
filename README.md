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
refunds, feature flags, and audit events, and the refund workflow —
approve / reject / escalate with server-enforced approval limits, required
reasons, state transitions, and an audit event written in the same transaction
as the refund. Feature-flag mutations and the frontend modules are not
implemented yet; the frontend is still a placeholder page showing backend health.

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

Errors use a stable envelope: `{"error": {"code": "...", "message": "...", "details": {}}}`.
Codes in use: `MISSING_IDENTITY`, `UNKNOWN_IDENTITY` (401); `APPROVAL_LIMIT_EXCEEDED`,
`ACTION_NOT_PERMITTED_FOR_ROLE` (403); `NOT_FOUND` (404); `INVALID_STATE_TRANSITION`
(409); `VALIDATION_ERROR`, `UNSUPPORTED_CURRENCY` (422); `INTERNAL_ERROR` (500).

### Frontend (`frontend/`)

```bash
cd frontend
nvm use            # Node 22, from ../.nvmrc
npm install
npm run dev        # dev server on http://localhost:5173
npm run lint       # oxlint
npm run build      # tsc -b && vite build (production build into dist/)
npm run preview    # serve the production build
```

The frontend calls the backend at `http://localhost:8000` by default; override
with the `VITE_API_BASE_URL` environment variable. Start the backend before the
frontend, otherwise the placeholder page reports the API as unreachable.

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
