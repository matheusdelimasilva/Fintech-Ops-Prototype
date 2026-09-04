# Devin Implementation Plan: Fintech Ops Console

## 1. Goal

Build a local prototype named **Fintech Ops Console** with:

1. A refund-operations module with server-enforced authorization, controlled
   state transitions, and a complete audit trail.
2. A feature-flags module using the same authorization, audit, API, and shared
   UI foundations.

## 2. Operating constraints

- Target timebox: approximately two hours.
- Use only synthetic data. Do not use real customers, payments, credentials, or
  company systems.
- Do not implement real SSO, payment processing, feature-flag infrastructure,
  or third-party integrations.
- Enforce sensitive permissions in the backend. Hiding a button in the UI is
  not authorization.
- Prefer a small, coherent codebase over broad feature coverage.
- Keep the app runnable locally with clear setup instructions.

If the repository already contains an application, inspect and preserve it
before changing structure or dependencies. If it is empty, use the structure
defined below.

## 3. Fixed implementation choices

Unless the existing repository makes one of these choices impractical, use:

| Area | Choice |
|---|---|
| Frontend | React, TypeScript, and Vite |
| Backend | FastAPI and Python |
| Persistence | SQLite with a simple ORM or explicit repository layer |
| API style | JSON REST endpoints |
| Tests | Pytest for backend policy/workflow tests; focused frontend tests only if time permits |
| Authentication | Synthetic demo users selected in the UI and identified to the backend by a demo user ID |
| Styling | Lightweight, accessible internal-tool UI; no pixel-perfect design work |

The demo identity mechanism must never trust a role or approval limit supplied
by the browser. The browser sends a known demo user ID; the backend resolves
that user's role and permissions from server-side data.

## 4. Suggested repository structure

```text
fintech-ops-console/
├── README.md
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── modules/
│   │   │   ├── refunds/
│   │   │   └── featureFlags/
│   │   ├── auth/
│   │   └── App.tsx
│   └── package.json
└── backend/
    ├── app/
    │   ├── api/
    │   ├── auth/
    │   ├── audit/
    │   ├── models/
    │   ├── repositories/
    │   ├── services/
    │   ├── seed.py
    │   └── main.py
    ├── tests/
    └── requirements.txt
```

The exact filenames may change, but authorization policy, workflow services,
audit recording, and persistence must remain separate enough to review and
test independently.

## 5. Domain model

### 5.1 Demo user

Store a small set of server-defined demo users:

| User | Role | Refund approval limit |
|---|---|---:|
| Sam Support | `support_agent` | $500 |
| Olivia Ops | `operations_manager` | $5,000 |
| Avery Admin | `admin` | Unlimited |

Minimum fields:

- `id`
- `display_name`
- `role`
- `approval_limit_cents` or equivalent server-side policy mapping

### 5.2 Refund case

Minimum fields:

- `id`
- `customer_name`
- `customer_reference`
- `transaction_reference`
- `amount_cents`
- `currency`
- `payment_status`
- `refund_status`: `pending`, `approved`, `rejected`, or `escalated`
- `risk_level`: `low`, `medium`, or `high`
- `reason_code` or descriptive context
- `created_at`
- `updated_at`
- optional last-action metadata for display

Persist money as integer minor units, never floating-point values.

### 5.3 Feature flag

Minimum fields:

- `id`
- `key`
- `description`
- `environment`: at least `staging` and `production`
- `enabled`
- `rollout_percent`: integer from 0 through 100
- `updated_at`

### 5.4 Audit event

Every successful state-changing action must create an audit event in the same
transaction as the domain change.

Minimum fields:

- `id`
- `occurred_at`
- `actor_user_id`
- `actor_display_name`
- `actor_role`
- `action`
- `entity_type`
- `entity_id`
- `before_state` as serialized JSON
- `after_state` as serialized JSON
- `reason`

Audit events are append-only in the application. Do not expose update or delete
operations for them.

## 6. Authorization and workflow rules

### 6.1 General rules

- All known demo users may view refund cases, feature flags, and audit events.
- Unknown or missing demo user IDs receive an authentication error.
- Authorization decisions are made by backend policy functions or services.
- Rejected requests must not change domain data or create a success audit event.
- API errors should distinguish authentication, authorization, validation, and
  invalid-state-transition failures.

### 6.2 Refund rules

- Approval is allowed only when a refund is `pending` or `escalated`.
- Rejection is allowed only when a refund is `pending` or `escalated`.
- Escalation is allowed only when a refund is `pending`.
- Every approve, reject, or escalate action requires a non-blank reason.
- `support_agent` may approve or reject refunds of $500 or less.
- `operations_manager` may approve or reject refunds of $5,000 or less.
- `admin` may approve or reject any refund amount.
- Support agents and operations managers may escalate a pending refund.
- Repeating a completed action must return a conflict or validation error rather
  than silently succeeding.
- A direct API request above the user's limit must fail even if the UI is
  bypassed.

### 6.3 Feature-flag rules

- `support_agent` is read-only.
- `operations_manager` may change staging flags.
- `admin` may change staging or production flags.
- Rollout percentage must be an integer from 0 through 100.
- Every change requires a non-blank reason.
- Every production change also requires an explicit confirmation value in the
  request; the backend must verify it.
- A successful change records before/after values in the shared audit trail.

## 7. API contract

Use routes equivalent to the following. Exact naming may vary if the generated
OpenAPI contract remains clear and consistent.

### 7.1 Session and health

- `GET /health`
- `GET /api/session` — returns the server-resolved demo user based on the demo
  user ID supplied with the request

### 7.2 Refunds

- `GET /api/refunds`
  - filters: search text, status, risk level
  - include deterministic sorting; pagination is optional for the prototype
- `GET /api/refunds/{refund_id}`
- `POST /api/refunds/{refund_id}/approve`
- `POST /api/refunds/{refund_id}/reject`
- `POST /api/refunds/{refund_id}/escalate`

Mutation body:

```json
{
  "reason": "Customer requested a duplicate-charge refund"
}
```

### 7.3 Feature flags

- `GET /api/feature-flags`
- `PATCH /api/feature-flags/{flag_id}`

Mutation body:

```json
{
  "enabled": true,
  "rollout_percent": 25,
  "reason": "Controlled rollout for support verification",
  "confirm_production": true
}
```

### 7.4 Audit

- `GET /api/audit-events`
  - filters: entity type, entity ID, actor, action
- `GET /api/audit-events/{event_id}` if useful for the UI

Return stable error payloads that the frontend can display to the user.

## 8. Seed data

Seed deterministic data on first run or through an explicit reset command.

Refund seed cases must include:

- at least 10 rows with varied customers, statuses, amounts, and risk levels;
- pending refunds below, exactly at, and above the $500 threshold;
- pending refunds below, exactly at, and above the $5,000 threshold;
- at least one already approved, rejected, and escalated case;
- recognizable examples suitable for the demo walkthrough.

Feature-flag seed data must include:

- at least two staging flags;
- at least two production flags;
- a mix of enabled/disabled states and rollout percentages.

Provide an idempotent reset mechanism so the demo can be restored to a known
state.

## 9. Frontend experience

### 9.1 Application shell

- Product title: **Fintech Ops Console**.
- Navigation: Refund Operations, Feature Flags, and Audit Trail.
- Persistent demo-user switcher displaying the selected user's name, role, and
  refund approval limit.
- Clear prototype banner stating that all data and identities are synthetic.
- Loading, empty, success, and error states for core screens.

### 9.2 Refund Operations

- Queue/table with transaction reference, customer, amount, risk, status, and
  created date.
- Search and filters for status and risk level.
- Detail view or panel with full refund context.
- Approve, reject, and escalate actions where applicable.
- Required reason input for every mutation.
- Explain disabled UI actions, but still rely on backend enforcement.
- Refresh the refund and audit views after a successful action.
- Display backend authorization and transition errors clearly.

### 9.3 Feature Flags

- List flag key, description, environment, enabled state, rollout percentage,
  and last update time.
- Edit enabled state and rollout percentage.
- Require a change reason.
- Require a conspicuous confirmation step for production changes.
- Reuse the same identity, authorization feedback, audit components, form
  patterns, API conventions, and loading/error handling used by refunds.

### 9.4 Audit Trail

- Show newest events first.
- Display actor, role, action, entity, timestamp, and reason.
- Allow filtering by entity type and entity ID.
- Provide a readable before/after comparison, even if implemented as formatted
  JSON for the prototype.

## 10. Required tests

Prioritize the required backend authorization and workflow tests.

### 10.1 Authorization boundary tests

- Support agent can approve $500 and cannot approve $500.01.
- Operations manager can approve $5,000 and cannot approve $5,000.01.
- Admin can approve a value above $5,000.
- A direct API call cannot bypass an approval limit.
- Unknown or missing demo identity is rejected.
- Support agent cannot modify a feature flag.
- Operations manager can modify staging but not production.
- Admin can modify production after explicit confirmation.
- Production flag change without confirmation is rejected.

### 10.2 Workflow and validation tests

- Approve, reject, and escalate require a reason.
- Pending refund can move to each allowed next state.
- Completed refund cannot be approved, rejected, or escalated again.
- Feature-flag rollout below 0 or above 100 is rejected.
- Successful mutations create exactly one audit event with actor, reason, and
  before/after data.
- Failed mutations do not alter domain state and do not create a success audit
  event.

If time remains, add focused frontend tests for the role switcher, required
reason validation, and production confirmation dialog.

## 11. Implementation sequence and time budget

### Status

Detailed per-checkpoint evidence lives in `PROTOTYPE_EVIDENCE.md`.

| Phase | Status | Notes |
|---|---|---|
| 1 — Foundation | **Done** (PR #1, PR #2, PR #5) | Backend: persistence, seed/reset, demo identity, error envelope, read-only endpoints for refunds, feature flags, audit, and session. Frontend (PR #5): shell, hash router, identity context, shared API client with `ApiError`, `useQuery`, formatters, error/status/loading/empty primitives. |
| 2 — Refund workflow | **Done** (backend PR #4, UI PR #5) | `POST /api/refunds/{id}/approve\|reject\|escalate` with required trimmed reasons, declarative state machine, guarded conditional update, and `allowed_actions` per caller. UI: server-filtered queue, hash-selected detail, inline action forms, post-mutation refresh. |
| 3 — RBAC and audit | **Done for refunds and feature flags** (backend PR #4, UI PR #5, flags PR #6) | Pure `refund_action_denial` / `feature_flag_edit_denial` policies with structured `403` codes, admin cannot escalate, USD-only fail-closed, one domain-neutral `record_event` recorder writing the audit event in the same transaction as the domain row, boundary/bypass/ordering/atomicity tests. UI renders only server-provided capabilities (`allowed_actions`, `can_edit`, `requires_confirmation`), shows structured `401/403/409/422` envelopes, and lists each record's audit events with changed-field diffs. Standalone Audit Trail page is still a placeholder. |
| 4 — Feature Flags reuse proof | **Done** (PR #6, review fixes PR #8) | `PATCH /api/feature-flags/{id}` with strict partial body, required trimmed reason, `confirm_production`, `409 NO_CHANGE` for no-ops, guarded conditional update on observed values + `updated_at`; `FlagChanges` enforces literal `bool` / `int` at the service boundary too. UI: environment-filtered list (key, description, environment, state, rollout, updated), hash-selected detail, edit form only when `can_edit`, red confirmation block gating Confirm only when `requires_confirmation`, shared error/notice/audit components; success banners report each follow-up refetch's real status and a stale `409` refetches detail, audit, and list. Browser verification is owner-owned and still outstanding. |
| 5 — Verification and handoff | Not started | |

Actual sequencing differs from the time budget below: the foundation checkpoint
absorbed the read-only API surface for all entities so later phases add only
mutations, enforcement, and UI.

### Phase 1 — Foundation (0–15 minutes)

1. Inspect the repository and note existing constraints.
2. Scaffold frontend and backend.
3. Add a health endpoint, database initialization, seed/reset mechanism, and
   basic run instructions.
4. Establish shared demo identity resolution and error response conventions.

**Checkpoint:** Both services run locally, seeded data is available, and the
frontend can call the backend.

### Phase 2 — Refund workflow (15–55 minutes)

1. Implement refund model, repository, list/detail endpoints, and seed cases.
2. Build queue, search/filter, and detail UI.
3. Implement state-transition service for approve, reject, and escalate.
4. Add reason capture and user feedback.

**Checkpoint:** A user can complete an end-to-end refund action and see the
persisted result.

### Phase 3 — RBAC and audit (55–80 minutes)

1. Centralize role and approval-limit policy.
2. Enforce all mutation rules on the backend.
3. Implement append-only audit storage in the same transaction as mutations.
4. Add the audit UI and before/after display.
5. Add authorization-boundary and workflow tests.

**Checkpoint:** A direct unauthorized API request fails; an authorized action
succeeds and creates one complete audit event.

### Phase 4 — Feature Flags reuse proof (80–100 minutes)

1. Implement feature-flag model, seed data, list endpoint, and update service.
2. Apply environment-specific authorization and production confirmation.
3. Build feature-flag list/edit UI using existing shared patterns.
4. Route successful changes through the existing audit system.

**Checkpoint:** The second module works without duplicating identity, audit,
API error handling, or shared UI foundations.

### Phase 5 — Verification and handoff (100–120 minutes)

1. Run automated tests and fix failures.
2. Run the full demo walkthrough below.
3. Inspect code for duplicated policy logic, missing server checks, and unclear
   boundaries.
4. Finalize `README.md` with setup, reset, test, and demo instructions.

If time runs short, preserve backend authorization, audit integrity, and tests.
Reduce UI polish or secondary filters first.

## 12. Demo walkthrough

1. Start from a freshly seeded database.
2. Select Sam Support and open a pending refund above $500.
3. Attempt approval and show the backend-generated authorization failure.
4. Select Olivia Ops and approve an eligible refund with a required reason.
5. Open the audit trail and show actor, role, timestamp, reason, and before/after
   state.
6. Attempt a refund above $5,000 as Olivia Ops and show the failure.
7. Select Avery Admin and complete the high-value action.
8. Open Feature Flags and attempt a production change without confirmation;
   show rejection.
9. Confirm the production change as Avery Admin and show the shared audit
   event.

## 13. Definition of done

The prototype is complete when all of the following are true:

- The app runs locally from documented commands.
- Seed/reset produces deterministic demo data.
- Refund queue, filters, detail, and state-changing actions work.
- Approval thresholds are enforced by the backend at $500 and $5,000.
- Required reasons and valid state transitions are enforced by the backend.
- Every successful mutation creates one complete audit event.
- Failed mutations do not change state.
- Feature Flags reuses the shared identity, authorization, audit, API, and UI
  patterns.
- Production flag changes require admin authorization and explicit confirmation.
- Required backend tests pass.
- The demo walkthrough can be completed from a fresh reset.
- `README.md` is complete.

## 14. Clarification and escalation protocol

Proceed with the defaults in this plan unless a discovery would materially
change the result. Ask the project owner before proceeding if:

- an existing repository conflicts with the proposed stack or structure;
- a real deployment target is required rather than local execution;
- real company identity, customer data, or external credentials would be
  needed;
- the role limits or workflow rules differ from the stated $500/$5,000 model;
- the prototype is expected to become production code;
- a requested change would displace the core RBAC, audit, or test work from the
  two-hour timebox.

For small implementation details, make a reasonable choice, record it, and keep
moving.
