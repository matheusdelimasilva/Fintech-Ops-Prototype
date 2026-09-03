from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, inspect, select

from app import db, seed
from app.audit import refund_snapshot
from app.main import app
from app.models import AuditEvent, DemoUser, FeatureFlag, RefundCase, RefundStatus


def _snapshot(engine: Engine) -> list[tuple[object, ...]]:
    rows: list[tuple[object, ...]] = []
    with db.make_session_factory(engine)() as session:
        for model in (DemoUser, RefundCase, FeatureFlag, AuditEvent):
            columns = [c.name for c in inspect(model).columns]
            for obj in session.scalars(select(model).order_by(model.id)).all():
                rows.append(tuple(str(getattr(obj, col)) for col in columns))
    return rows


def test_reset_is_deterministic(engine: Engine) -> None:
    seed.reset(engine)
    first = _snapshot(engine)
    seed.reset(engine)
    second = _snapshot(engine)

    assert first == second
    assert len(first) == 3 + 12 + 4 + 3


def test_seed_if_empty_is_idempotent(engine: Engine) -> None:
    assert seed.seed_if_empty(engine) is True
    before = _snapshot(engine)
    assert seed.seed_if_empty(engine) is False
    assert _snapshot(engine) == before


def test_seed_contains_approval_threshold_fixtures(seeded_engine: Engine) -> None:
    with db.make_session_factory(seeded_engine)() as session:
        pending = session.scalars(
            select(RefundCase).where(RefundCase.refund_status == RefundStatus.PENDING)
        ).all()
        pending_amounts = {r.amount_cents for r in pending}
        statuses = {r.refund_status for r in session.scalars(select(RefundCase)).all()}

    assert {50_000, 50_001, 500_000, 500_001} <= pending_amounts
    assert min(pending_amounts) < 50_000
    assert max(pending_amounts) > 500_001
    assert statuses == set(RefundStatus)


def test_seeded_audit_snapshots_match_the_live_snapshot_shape(seeded_engine: Engine) -> None:
    with db.make_session_factory(seeded_engine)() as session:
        events = session.scalars(select(AuditEvent).order_by(AuditEvent.id)).all()
        refunds = {r.id: r for r in session.scalars(select(RefundCase)).all()}

        assert len(events) == 3
        for event in events:
            refund = refunds[event.entity_id]
            live = refund_snapshot(refund)
            assert event.after_state == live
            assert set(event.before_state) == set(live)
            assert event.before_state["refund_status"] == "pending"
            assert event.before_state["last_action"] is None
            assert event.before_state["last_action_at"] is None
            assert event.after_state["last_action_reason"] == event.reason


def test_app_startup_seeds_an_empty_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = f"sqlite:///{tmp_path / 'startup.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    db.get_engine.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.get("/api/refunds", headers={"X-Demo-User-Id": "user_avery_admin"})
        assert response.status_code == 200
        assert len(response.json()) == 12
    finally:
        db.get_engine().dispose()
        db.get_engine.cache_clear()
