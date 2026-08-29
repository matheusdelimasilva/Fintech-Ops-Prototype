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

Scaffold only: a FastAPI backend exposing `GET /health` and a React/Vite
placeholder page that displays backend health. Refund Operations, Feature
Flags, and the Audit Trail are not implemented yet, so there is no database or
seed data.

## Prerequisites

- Python 3.10 or newer
- Node.js 22 (`nvm use` reads `.nvmrc`; Node 20.18 is too old for Vite 8)

## Local commands

### Backend (`backend/`)

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements-dev.txt   # runtime deps only: requirements.txt
./.venv/bin/uvicorn app.main:app --reload --port 8000   # run on http://localhost:8000
./.venv/bin/pytest                                 # tests
./.venv/bin/ruff check .                           # lint
./.venv/bin/ruff format .                          # format
```

Health check: `curl http://localhost:8000/health` returns
`{"status":"ok","service":"fintech-ops-console-api"}`.
Interactive API docs: http://localhost:8000/docs

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

Not applicable yet — no database exists in the scaffold.

## Prototype limitations

This is deliberately not production-ready. It does not provide real SSO,
production secrets management, a production database, tamper-resistant audit
retention, DLP, vulnerability-management operations, backups, monitoring,
incident response, or real financial-system integrations.
