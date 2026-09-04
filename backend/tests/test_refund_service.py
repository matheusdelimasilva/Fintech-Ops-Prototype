"""Service-level tests: transaction ownership, atomicity, and the stale-write guard.

Persistence is always checked through a *fresh* session so a dirty in-memory object cannot
mask a rollback.
"""

from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app import audit, db, refund_service
from app.errors import AppError, InvalidStateTransitionError
from app.identity import CurrentUser
from app.models import AuditEvent, RefundCase, RefundStatus, Role
from app.policy import RefundAction

SAM = CurrentUser(id="user_sam_support", display_name="Sam Support", role=Role.SUPPORT_AGENT)
OLIVIA = CurrentUser(id="user_olivia_ops", display_name="Olivia Ops", role=Role.OPERATIONS_MANAGER)


@pytest.fixture
def factory(seeded_engine: Engine) -> sessionmaker[Session]:
    return db.make_session_factory(seeded_engine)


def _audit_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(AuditEvent)) or 0


def _transitions(session: Session, refund_id: str) -> list[tuple[object, object]]:
    events = session.scalars(
        select(AuditEvent).where(AuditEvent.entity_id == refund_id).order_by(AuditEvent.occurred_at)
    ).all()
    return [(e.before_state["refund_status"], e.after_state["refund_status"]) for e in events]


def test_success_commits_refund_and_one_audit_event_together(
    factory: sessionmaker[Session],
) -> None:
    with factory() as session:
        before_count = _audit_count(session)
        refund = refund_service.perform_refund_action(
            session, SAM, "rfnd_001", RefundAction.APPROVE, "duplicate charge confirmed"
        )
        assert refund.refund_status is RefundStatus.APPROVED

    with factory() as fresh:
        stored = fresh.get(RefundCase, "rfnd_001")
        assert stored is not None
        assert stored.refund_status is RefundStatus.APPROVED
        assert stored.last_action_by == "Sam Support"
        assert stored.last_action_reason == "duplicate charge confirmed"
        assert stored.last_action_at == stored.updated_at

        events = fresh.scalars(select(AuditEvent).where(AuditEvent.entity_id == "rfnd_001")).all()
        assert _audit_count(fresh) == before_count + 1
        assert len(events) == 1
        event = events[0]
        assert event.id.startswith("evt_")
        assert event.occurred_at == stored.last_action_at
        assert event.before_state["refund_status"] == "pending"
        assert event.before_state["last_action"] is None
        assert event.after_state == audit.refund_snapshot(stored)
        assert set(event.before_state) == set(event.after_state)


def test_audit_failure_rolls_back_the_refund_update(
    factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*_: Any, **__: Any) -> AuditEvent:
        raise RuntimeError("audit store unavailable")

    monkeypatch.setattr(refund_service, "record_event", explode)

    with factory() as session:
        before_count = _audit_count(session)
        with pytest.raises(RuntimeError):
            refund_service.perform_refund_action(
                session, SAM, "rfnd_001", RefundAction.APPROVE, "should not persist"
            )

    with factory() as fresh:
        stored = fresh.get(RefundCase, "rfnd_001")
        assert stored is not None
        assert stored.refund_status is RefundStatus.PENDING
        assert stored.last_action is None
        assert stored.last_action_reason is None
        assert _audit_count(fresh) == before_count


@pytest.mark.parametrize(
    ("actor", "refund_id", "action", "expected_code"),
    [
        (SAM, "rfnd_003", RefundAction.APPROVE, "APPROVAL_LIMIT_EXCEEDED"),
        (SAM, "rfnd_008", RefundAction.APPROVE, "INVALID_STATE_TRANSITION"),
        (SAM, "rfnd_404", RefundAction.APPROVE, "NOT_FOUND"),
    ],
)
def test_denied_actions_leave_no_trace(
    factory: sessionmaker[Session],
    actor: CurrentUser,
    refund_id: str,
    action: RefundAction,
    expected_code: str,
) -> None:
    with factory() as snapshot_session:
        before_count = _audit_count(snapshot_session)
        before_row = snapshot_session.get(RefundCase, refund_id)
        before_status = before_row.refund_status if before_row else None

    with factory() as session:
        with pytest.raises(AppError) as excinfo:
            refund_service.perform_refund_action(session, actor, refund_id, action, "reason")
        assert excinfo.value.code == expected_code

    with factory() as fresh:
        after_row = fresh.get(RefundCase, refund_id)
        assert (after_row.refund_status if after_row else None) == before_status
        assert _audit_count(fresh) == before_count


def test_stale_write_is_rejected_by_the_guarded_update(
    factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deterministic two-session interleave.

    Session A loads and authorizes `rfnd_001` as pending. Before A's guarded UPDATE runs,
    session B approves the same refund through the real service and commits. A's UPDATE
    then matches zero rows and must fail with 409 while writing nothing.

    Scope: this exercises the conditional-update guard with two real sessions. It does not
    exercise SQLite locking or threaded interleaving under load.
    """
    real_snapshot: Callable[[RefundCase], dict[str, object]] = refund_service.refund_snapshot
    interleaved = {"done": False}

    def snapshot_then_let_b_win(refund: RefundCase) -> dict[str, object]:
        result = real_snapshot(refund)
        if not interleaved["done"]:
            interleaved["done"] = True
            with factory() as session_b:
                refund_service.perform_refund_action(
                    session_b, OLIVIA, refund.id, RefundAction.APPROVE, "B approved first"
                )
        return result

    monkeypatch.setattr(refund_service, "refund_snapshot", snapshot_then_let_b_win)

    with factory() as session_a:
        before_count = _audit_count(session_a)
        with pytest.raises(InvalidStateTransitionError) as excinfo:
            refund_service.perform_refund_action(
                session_a, SAM, "rfnd_001", RefundAction.REJECT, "A rejects too late"
            )
        assert excinfo.value.details["current_status"] == "approved"
        assert excinfo.value.details["action"] == "reject"

    with factory() as fresh:
        stored = fresh.get(RefundCase, "rfnd_001")
        assert stored is not None
        assert stored.refund_status is RefundStatus.APPROVED
        assert stored.last_action_by == "Olivia Ops"
        assert stored.last_action_reason == "B approved first"
        events = fresh.scalars(select(AuditEvent).where(AuditEvent.entity_id == "rfnd_001")).all()
        assert [e.reason for e in events] == ["B approved first"]
        assert _audit_count(fresh) == before_count + 1


def test_guard_rejects_a_stale_snapshot_even_when_the_new_status_also_allows_the_action(
    factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Session A snapshots `pending`; session B escalates and commits; A then rejects.

    `escalated` is itself a legal source for reject, so a guard on "any allowed status" would
    let A through and record `pending -> rejected` while the real transition was
    `escalated -> rejected`. The guard must match the exact observed status instead.
    Same scope caveat as above: two real sessions, no locking or threads under load.
    """
    real_snapshot: Callable[[RefundCase], dict[str, object]] = refund_service.refund_snapshot
    interleaved = {"done": False}

    def snapshot_then_let_b_escalate(refund: RefundCase) -> dict[str, object]:
        result = real_snapshot(refund)
        if not interleaved["done"]:
            interleaved["done"] = True
            with factory() as session_b:
                refund_service.perform_refund_action(
                    session_b, SAM, refund.id, RefundAction.ESCALATE, "B escalated first"
                )
        return result

    monkeypatch.setattr(refund_service, "refund_snapshot", snapshot_then_let_b_escalate)

    with factory() as session_a:
        before_count = _audit_count(session_a)
        with pytest.raises(InvalidStateTransitionError) as excinfo:
            refund_service.perform_refund_action(
                session_a, OLIVIA, "rfnd_001", RefundAction.REJECT, "A rejects a stale row"
            )
        assert excinfo.value.details["current_status"] == "escalated"
        assert excinfo.value.details["action"] == "reject"

    with factory() as fresh:
        stored = fresh.get(RefundCase, "rfnd_001")
        assert stored is not None
        assert stored.refund_status is RefundStatus.ESCALATED
        assert stored.last_action_reason == "B escalated first"
        assert _transitions(fresh, "rfnd_001") == [("pending", "escalated")]
        assert _audit_count(fresh) == before_count + 1

    # A retry against the current row now records the true transition.
    monkeypatch.setattr(refund_service, "refund_snapshot", real_snapshot)
    with factory() as session_a:
        refund_service.perform_refund_action(
            session_a, OLIVIA, "rfnd_001", RefundAction.REJECT, "A rejects the current row"
        )
    with factory() as fresh:
        assert _transitions(fresh, "rfnd_001") == [
            ("pending", "escalated"),
            ("escalated", "rejected"),
        ]


@pytest.mark.parametrize(
    ("actor", "refund_id", "expected"),
    [
        (SAM, "rfnd_001", ["approve", "reject", "escalate"]),
        (SAM, "rfnd_003", ["escalate"]),
        (OLIVIA, "rfnd_003", ["approve", "reject", "escalate"]),
        (SAM, "rfnd_010", []),
        (OLIVIA, "rfnd_010", ["approve", "reject"]),
        (OLIVIA, "rfnd_008", []),
    ],
)
def test_allowed_actions_combine_policy_and_transitions(
    factory: sessionmaker[Session], actor: CurrentUser, refund_id: str, expected: list[str]
) -> None:
    with factory() as session:
        refund = session.get(RefundCase, refund_id)
        assert refund is not None
        actions = refund_service.allowed_actions(actor, refund)
    assert [a.value for a in actions] == expected
