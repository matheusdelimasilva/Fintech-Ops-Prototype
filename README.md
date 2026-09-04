# Fintech Ops Console

A local prototype of an internal operations console for a fintech team. It
shows how one set of backend-enforced controls — role-based authorization,
required reasons, controlled state transitions, and an append-only audit trail
— can be built once and reused across two workflows:

- **Refund Operations.** A queue of refund requests that support agents,
  operations managers, and admins can approve, reject, or escalate. The server
  enforces per-role approval limits ($500 / $5,000 / unlimited), allows only
  valid status transitions, and requires a reason for every action.
- **Feature Flags.** Staging and production flags with an enabled state and a
  rollout percentage. Support is read-only, operations managers may change
  staging, admins may change both; production changes require an explicit
  confirmation that the server checks.
- **Audit Trail.** Every successful change is written in the same database
  transaction as the record it changed, with actor, role, timestamp, reason,
  and before/after values. The trail can be filtered by entity type, entity
  ID, actor, and action, and each refund or flag links to its own history.

You pick a demo user in the header; the browser sends only that user's ID and
the backend resolves role and permissions. The UI hides what a user cannot do,
but every rule is enforced server-side regardless of what the client sends.

All identities and data are synthetic. Nothing connects to a payment processor,
identity provider, feature-flag service, or any production system. It is not
production-ready: there is no real authentication, no tamper-resistant audit
storage, and no pagination of the audit log. `PROTOTYPE_EVIDENCE.md` records
how each part was built and verified and what remains for a real deployment.

## Running it

Prerequisites: Python 3.10–3.13 and Node.js 22 (`nvm use` reads `.nvmrc`).

Backend (FastAPI + SQLite, on http://localhost:8000):

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements-dev.txt
./.venv/bin/uvicorn app.main:app --reload --port 8000
```

The database (`backend/fintech_ops.db`) is created and seeded with synthetic
data on first start. `./.venv/bin/python -m app.seed --reset` restores the seed.
Interactive API docs are at http://localhost:8000/docs; every `/api/*` request
needs an `X-Demo-User-Id` header of `user_sam_support`, `user_olivia_ops`, or
`user_avery_admin`.

Frontend (React + Vite, on http://localhost:5173), in a second terminal:

```bash
cd frontend
nvm use
npm install
npm run dev
```

Open http://localhost:5173, choose a demo user in the header, and switch between
Refund Operations, Feature Flags, and Audit Trail. The frontend talks to the
backend at http://localhost:8000 (override with `VITE_API_BASE_URL`), so start
the backend first.

Checks:

```bash
cd backend && ./.venv/bin/pytest && ./.venv/bin/ruff check .
cd frontend && npm run lint && npm test && npm run build
```
