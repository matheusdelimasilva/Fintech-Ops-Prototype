# Fintech Ops Console

A time-boxed evaluation prototype for testing whether Devin-assisted custom
development can provide a reusable foundation for fintech internal tools.

The prototype will contain:

- Refund Operations: queue, detail, approval/rejection/escalation, server-side
  approval limits, and audit history.
- Feature Flags: staging and production controls that reuse the same RBAC,
  audit, API, and UI foundations.

All identities and business data are synthetic. This repository must never be
connected to real customers, payments, KYC systems, corporate SSO, production
feature flags, or production infrastructure.

## Status

Repository prepared for the initial Devin planning and implementation session.
Application scaffolding has not yet been generated.

## Start here

1. Read `AGENTS.md` for mandatory operating and security rules.
2. Read `DEVIN_IMPLEMENTATION_PLAN.md` for the complete domain model, API
   contract, implementation sequence, and acceptance matrix.
3. Begin in Devin Q&A mode and request a plan only.
4. Review the plan, then authorize Agent mode to implement one checkpoint at a
   time.
5. Record results in `PROTOTYPE_EVIDENCE.md`.

## Intended stack

| Layer | Choice |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | FastAPI, Python |
| Persistence | SQLite |
| Backend tests | Pytest |

## Local commands

Devin must replace this section with exact, verified install, run, lint, test,
build, and seed-reset commands when it creates the application scaffold.

## Prototype limitations

This is deliberately not production-ready. It does not provide real SSO,
production secrets management, a production database, tamper-resistant audit
retention, DLP, vulnerability-management operations, backups, monitoring,
incident response, or real financial-system integrations.
