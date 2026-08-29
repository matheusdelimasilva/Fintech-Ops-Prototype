# Fintech Ops Console agent instructions

These instructions apply to the entire repository. Read
`DEVIN_IMPLEMENTATION_PLAN.md` before proposing or implementing changes.

## Objective and timebox

Build a local evaluation prototype named **Fintech Ops Console**. It must demonstrate:

1. A Refund Operations workflow with backend-enforced authorization, controlled
   state transitions, and an append-only audit trail.
2. A Feature Flags workflow that reuses the same authorization, audit, API, and
   shared UI foundations.

Optimize for verifiable evidence, clear code, and honest limitations rather
than feature count or visual polish.

## Planning and communication

- Inspect the repository and this file before editing.
- If the session asks for a plan, return the architecture, assumptions, risks,
  implementation order, and acceptance-test matrix without changing files.
- Once implementation is authorized, work in reviewable checkpoints: runnable
  skeleton, refund vertical slice, RBAC and audit, security tests, feature-flag
  reuse, then final verification.
- Do not replace the agreed stack or add a major dependency without explaining
  the reason and receiving approval.
- Do not expand scope. If blocked for more than ten minutes, report the cause,
  evidence, and two recovery options instead of repeatedly trying unrelated
  approaches.

## Fixed prototype stack

- Frontend: React, TypeScript, and Vite.
- Backend: FastAPI and Python.
- Persistence: SQLite behind an ORM or explicit repository layer.
- API: JSON REST endpoints.
- Tests: Pytest for backend policy and workflow tests. Add focused frontend
  tests only when they protect important behavior and fit the timebox.
- Authentication: synthetic demo users selected in the UI. The browser sends
  only a known demo-user ID; the backend resolves role and permissions.
- Styling: accessible, lightweight internal-tool UI.

Keep authorization policy, workflow services, audit recording, and persistence
separate enough to review and test independently. Use integer minor units for
money; never use floating-point values for refund amounts.

## Security and data-safety invariants

- Use synthetic data only.
- Do not connect payment processors, KYC systems, corporate SSO, production
  feature-flag services, or production infrastructure.
- UI visibility is not authorization. Enforce authentication, authorization,
  approval limits, required reasons, state transitions, and production
  confirmations in the backend.
- Never trust a role, approval limit, actor name, or other authorization claim
  supplied by the browser.
- Every successful mutation and its audit event must be persisted atomically.
- Failed or unauthorized requests must not change domain data and must not
  create a success audit event.
- Audit events are append-only through the application. Do not expose update or
  delete endpoints for them. Describe the prototype audit trail as
  “append-only through the application,” not tamper-proof or immutable.
- Clearly identify mocked identity and missing production controls.

## Required domain policy

Server-defined demo users:

| Role | Refund approval/rejection limit | Feature flags |
|---|---:|---|
| `support_agent` | $500 | Read-only |
| `operations_manager` | $5,000 | May change staging |
| `admin` | Unlimited | May change staging and production |

Refund rules:

- Approve or reject only a `pending` or `escalated` refund.
- Escalate only a `pending` refund.
- Every approve, reject, or escalate action requires a nonblank reason.
- Support agents and operations managers may escalate pending refunds.
- Repeating a completed action must return a validation or conflict error.

Feature-flag rules:

- Rollout percentage is an integer from 0 through 100.
- Every mutation requires a nonblank reason.
- Every production mutation requires an explicit confirmation value that is
  checked by the backend.
- Feature Flags must reuse the central authorization, audit, API-client,
  confirmation, and error-handling foundations.

## Minimum verification gates

Before declaring the work complete:

- Run the backend tests, frontend linting/tests, and production build.
- Exercise both modules in the browser and check for console errors.
- Test $500.00 versus $500.01 and $5,000.00 versus $5,000.01.
- Prove that direct unauthorized API calls return an appropriate `403`.
- Test missing identities, missing reasons, invalid state transitions, repeated
  actions, invalid rollout percentages, and missing production confirmation.
- Verify every successful mutation writes the expected before/after audit event.
- Confirm the second module actually reuses shared primitives; report any
  duplication that remains.
- Update `PROTOTYPE_EVIDENCE.md` with elapsed milestones, commands run, test
  results, human interventions, limitations, and remaining production work.
- Keep `README.md` commands accurate and sufficient for a new engineer to run
  the prototype locally.

## Git discipline

- Work on a branch; do not commit directly to protected `main` after initial
  repository setup.
- Keep commits small and aligned with the implementation checkpoints.
- Do not commit `.env` files, secrets, local databases, dependency directories,
  build output, caches, screenshots containing sensitive information, or synced
  `sources/` material.
- Do not rewrite history or force-push.
- Open a pull request only after the required checks pass, and leave merging to
  a human reviewer.
