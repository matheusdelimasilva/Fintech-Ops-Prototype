"""Service-level tests for feature-flag updates: ordering, atomicity, no-op, stale guard.

Persistence is always checked through a *fresh* session so a dirty in-memory object cannot
mask a rollback.
"""

from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app import audit, db, feature_flag_service
from app.errors import AppError, StaleUpdateError
from app.feature_flag_service import FlagChanges
from app.identity import CurrentUser
from app.models import AuditEvent, EntityType, FeatureFlag, Role

SAM = CurrentUser(id="user_sam_support", display_name="Sam Support", role=Role.SUPPORT_AGENT)
OLIVIA = CurrentUser(id="user_olivia_ops", display_name="Olivia Ops", role=Role.OPERATIONS_MANAGER)
AVERY = CurrentUser(id="user_avery_admin", display_name="Avery Admin", role=Role.ADMIN)

STAGING_FLAG = "flag_bulk_export_staging"  # enabled=True, rollout=50
PRODUCTION_FLAG = "flag_new_risk_scoring_production"  # enabled=True, rollout=10


@pytest.fixture
def factory(seeded_engine: Engine) -> sessionmaker[Session]:
    return db.make_session_factory(seeded_engine)


def _audit_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(AuditEvent)) or 0


def _flag_state(session: Session, flag_id: str) -> tuple[bool, int, object]:
    flag = session.get(FeatureFlag, flag_id)
    assert flag is not None
    return (flag.enabled, flag.rollout_percent, flag.updated_at)


def test_success_commits_flag_and_one_audit_event_together(factory: sessionmaker[Session]) -> None:
    with factory() as session:
        before_count = _audit_count(session)
        previous_updated_at = _flag_state(session, STAGING_FLAG)[2]
        flag = feature_flag_service.update_feature_flag(
            session,
            OLIVIA,
            STAGING_FLAG,
            FlagChanges(rollout_percent=75),
            "widen staging rollout",
            confirm_production=False,
        )
        assert flag.rollout_percent == 75
        assert flag.enabled is True

    with factory() as fresh:
        stored = fresh.get(FeatureFlag, STAGING_FLAG)
        assert stored is not None
        assert stored.rollout_percent == 75
        assert stored.updated_at != previous_updated_at

        events = fresh.scalars(select(AuditEvent).where(AuditEvent.entity_id == STAGING_FLAG)).all()
        assert _audit_count(fresh) == before_count + 1
        assert len(events) == 1
        event = events[0]
        assert event.entity_type is EntityType.FEATURE_FLAG
        assert event.action.value == "feature_flag.updated"
        assert event.actor_user_id == "user_olivia_ops"
        assert event.actor_role is Role.OPERATIONS_MANAGER
        assert event.reason == "widen staging rollout"
        assert event.occurred_at == stored.updated_at
        assert event.before_state["rollout_percent"] == 50
        assert event.after_state == audit.feature_flag_snapshot(stored)
        assert set(event.before_state) == set(event.after_state)


def test_admin_updates_production_with_confirmation(factory: sessionmaker[Session]) -> None:
    with factory() as session:
        feature_flag_service.update_feature_flag(
            session,
            AVERY,
            PRODUCTION_FLAG,
            FlagChanges(enabled=False, rollout_percent=0),
            "kill switch",
            confirm_production=True,
        )
    with factory() as fresh:
        enabled, rollout, _ = _flag_state(fresh, PRODUCTION_FLAG)
        assert (enabled, rollout) == (False, 0)


@pytest.mark.parametrize(
    ("actor", "flag_id", "changes", "confirm", "expected_code"),
    [
        # authorization comes first, even with confirmation and a real change
        (SAM, STAGING_FLAG, FlagChanges(enabled=False), True, "ACTION_NOT_PERMITTED_FOR_ROLE"),
        (SAM, PRODUCTION_FLAG, FlagChanges(enabled=False), True, "ACTION_NOT_PERMITTED_FOR_ROLE"),
        (
            OLIVIA,
            PRODUCTION_FLAG,
            FlagChanges(enabled=False),
            True,
            "ACTION_NOT_PERMITTED_FOR_ROLE",
        ),
        # then production confirmation, even for a no-op request
        (
            AVERY,
            PRODUCTION_FLAG,
            FlagChanges(enabled=True),
            False,
            "PRODUCTION_CONFIRMATION_REQUIRED",
        ),
        (
            AVERY,
            PRODUCTION_FLAG,
            FlagChanges(enabled=False),
            False,
            "PRODUCTION_CONFIRMATION_REQUIRED",
        ),
        # then the no-op check
        (OLIVIA, STAGING_FLAG, FlagChanges(enabled=True), False, "NO_CHANGE"),
        (OLIVIA, STAGING_FLAG, FlagChanges(rollout_percent=50), False, "NO_CHANGE"),
        (AVERY, PRODUCTION_FLAG, FlagChanges(enabled=True, rollout_percent=10), True, "NO_CHANGE"),
        (AVERY, "flag_missing", FlagChanges(enabled=True), True, "NOT_FOUND"),
    ],
)
def test_failures_leave_flag_and_audit_untouched(
    factory: sessionmaker[Session],
    actor: CurrentUser,
    flag_id: str,
    changes: FlagChanges,
    confirm: bool,
    expected_code: str,
) -> None:
    with factory() as snapshot_session:
        before_count = _audit_count(snapshot_session)
        exists = snapshot_session.get(FeatureFlag, flag_id) is not None
        before_state = _flag_state(snapshot_session, flag_id) if exists else None

    with factory() as session:
        with pytest.raises(AppError) as excinfo:
            feature_flag_service.update_feature_flag(
                session, actor, flag_id, changes, "reason", confirm_production=confirm
            )
        assert excinfo.value.code == expected_code

    with factory() as fresh:
        after_state = _flag_state(fresh, flag_id) if exists else None
        assert after_state == before_state
        assert _audit_count(fresh) == before_count


def test_no_change_details_report_current_values(factory: sessionmaker[Session]) -> None:
    with factory() as session:
        with pytest.raises(AppError) as excinfo:
            feature_flag_service.update_feature_flag(
                session,
                OLIVIA,
                STAGING_FLAG,
                FlagChanges(enabled=True, rollout_percent=50),
                "same values",
                confirm_production=False,
            )
    assert excinfo.value.code == "NO_CHANGE"
    assert excinfo.value.details == {
        "flag_id": STAGING_FLAG,
        "current": {"enabled": True, "rollout_percent": 50},
    }


def test_audit_failure_rolls_back_the_flag_update(
    factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*_: Any, **__: Any) -> AuditEvent:
        raise RuntimeError("audit store unavailable")

    monkeypatch.setattr(feature_flag_service, "record_event", explode)

    with factory() as session:
        before_count = _audit_count(session)
        before_state = _flag_state(session, STAGING_FLAG)
        with pytest.raises(RuntimeError):
            feature_flag_service.update_feature_flag(
                session,
                OLIVIA,
                STAGING_FLAG,
                FlagChanges(enabled=False),
                "should not persist",
                confirm_production=False,
            )

    with factory() as fresh:
        assert _flag_state(fresh, STAGING_FLAG) == before_state
        assert _audit_count(fresh) == before_count


def test_stale_write_is_rejected_by_the_guarded_update(
    factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deterministic two-session interleave, same scope caveat as the refund test: it exercises
    the conditional-update guard with two real sessions, not SQLite locking under load."""
    real_snapshot: Callable[[FeatureFlag], dict[str, object]] = (
        feature_flag_service.feature_flag_snapshot
    )
    interleaved = {"done": False}

    def snapshot_then_let_b_win(flag: FeatureFlag) -> dict[str, object]:
        result = real_snapshot(flag)
        if not interleaved["done"]:
            interleaved["done"] = True
            with factory() as session_b:
                feature_flag_service.update_feature_flag(
                    session_b,
                    AVERY,
                    flag.id,
                    FlagChanges(rollout_percent=60),
                    "B changed first",
                    confirm_production=False,
                )
        return result

    monkeypatch.setattr(feature_flag_service, "feature_flag_snapshot", snapshot_then_let_b_win)

    with factory() as session_a:
        before_count = _audit_count(session_a)
        with pytest.raises(StaleUpdateError) as excinfo:
            feature_flag_service.update_feature_flag(
                session_a,
                OLIVIA,
                STAGING_FLAG,
                FlagChanges(enabled=False),
                "A is too late",
                confirm_production=False,
            )
        assert excinfo.value.details["current"] == {"enabled": True, "rollout_percent": 60}

    with factory() as fresh:
        enabled, rollout, _ = _flag_state(fresh, STAGING_FLAG)
        assert (enabled, rollout) == (True, 60)
        events = fresh.scalars(select(AuditEvent).where(AuditEvent.entity_id == STAGING_FLAG)).all()
        assert [e.reason for e in events] == ["B changed first"]
        assert _audit_count(fresh) == before_count + 1


def test_guard_catches_a_concurrent_change_that_restores_the_observed_values(
    factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """B flips rollout 50 -> 60 -> 50 between A's read and A's UPDATE. A's observed values are
    back in place, so only `updated_at` distinguishes the row; the guard must still reject A so
    the audit trail's before-state is the row A actually read."""
    real_snapshot: Callable[[FeatureFlag], dict[str, object]] = (
        feature_flag_service.feature_flag_snapshot
    )
    interleaved = {"done": False}

    def snapshot_then_b_round_trips(flag: FeatureFlag) -> dict[str, object]:
        result = real_snapshot(flag)
        if not interleaved["done"]:
            interleaved["done"] = True
            for rollout, reason in ((60, "B up"), (50, "B back")):
                with factory() as session_b:
                    feature_flag_service.update_feature_flag(
                        session_b,
                        AVERY,
                        flag.id,
                        FlagChanges(rollout_percent=rollout),
                        reason,
                        confirm_production=False,
                    )
        return result

    monkeypatch.setattr(feature_flag_service, "feature_flag_snapshot", snapshot_then_b_round_trips)

    with factory() as session_a:
        with pytest.raises(StaleUpdateError):
            feature_flag_service.update_feature_flag(
                session_a,
                OLIVIA,
                STAGING_FLAG,
                FlagChanges(enabled=False),
                "A is too late",
                confirm_production=False,
            )

    with factory() as fresh:
        enabled, rollout, _ = _flag_state(fresh, STAGING_FLAG)
        assert (enabled, rollout) == (True, 50)
        events = fresh.scalars(
            select(AuditEvent)
            .where(AuditEvent.entity_id == STAGING_FLAG)
            .order_by(AuditEvent.occurred_at)
        ).all()
        assert [e.reason for e in events] == ["B up", "B back"]


@pytest.mark.parametrize(
    ("actor", "flag_id", "expected_can_edit", "expected_requires_confirmation"),
    [
        (SAM, STAGING_FLAG, False, False),
        (SAM, PRODUCTION_FLAG, False, True),
        (OLIVIA, STAGING_FLAG, True, False),
        (OLIVIA, PRODUCTION_FLAG, False, True),
        (AVERY, STAGING_FLAG, True, False),
        (AVERY, PRODUCTION_FLAG, True, True),
    ],
)
def test_capability_hints_follow_policy_and_environment(
    factory: sessionmaker[Session],
    actor: CurrentUser,
    flag_id: str,
    expected_can_edit: bool,
    expected_requires_confirmation: bool,
) -> None:
    with factory() as session:
        flag = session.get(FeatureFlag, flag_id)
        assert flag is not None
        assert feature_flag_service.can_edit(actor, flag) is expected_can_edit
        assert feature_flag_service.requires_confirmation(flag) is expected_requires_confirmation


def test_flag_changes_requires_at_least_one_field_and_a_valid_rollout() -> None:
    with pytest.raises(ValueError):
        FlagChanges()
    with pytest.raises(ValueError):
        FlagChanges(rollout_percent=101)
    with pytest.raises(ValueError):
        FlagChanges(rollout_percent=-1)
    assert FlagChanges(rollout_percent=0).rollout_percent == 0
    assert FlagChanges(rollout_percent=100).rollout_percent == 100
