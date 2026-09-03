"""API-level tests for POST /api/refunds/{id}/approve|reject|escalate.

State is verified through GET calls (a fresh session per request), never through objects
the mutation itself returned.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app import db, refund_service
from app.main import app
from tests.conftest import AVERY, OLIVIA, SAM

USERS = {"sam": SAM, "olivia": OLIVIA, "avery": AVERY}
REASON = {"reason": "Verified with the customer."}


def _post(client: TestClient, user: str, action: str, refund_id: str, body: Any = REASON) -> Any:
    return client.post(f"/api/refunds/{refund_id}/{action}", headers=USERS[user], json=body)


def _get_refund(client: TestClient, refund_id: str) -> dict[str, Any]:
    return client.get(f"/api/refunds/{refund_id}", headers=AVERY).json()


def _events_for(client: TestClient, refund_id: str) -> list[dict[str, Any]]:
    return client.get("/api/audit-events", headers=AVERY, params={"entity_id": refund_id}).json()


def _audit_count(client: TestClient) -> int:
    return len(client.get("/api/audit-events", headers=AVERY).json())


def _error(response: Any) -> dict[str, Any]:
    return response.json()["error"]


# Seed amounts: rfnd_002=50000, rfnd_003=50001, rfnd_005=500000, rfnd_006=500001,
# rfnd_010 is escalated at 76500.


@pytest.mark.parametrize("action", ["approve", "reject"])
@pytest.mark.parametrize(
    ("user", "refund_id", "allowed"),
    [
        ("sam", "rfnd_002", True),
        ("sam", "rfnd_003", False),
        ("olivia", "rfnd_003", True),
        ("olivia", "rfnd_005", True),
        ("olivia", "rfnd_006", False),
        ("avery", "rfnd_006", True),
    ],
)
def test_approval_limits_are_enforced_at_the_api(
    client: TestClient, user: str, action: str, refund_id: str, allowed: bool
) -> None:
    response = _post(client, user, action, refund_id)

    target = {"approve": "approved", "reject": "rejected"}[action]
    if allowed:
        assert response.status_code == 200
        assert response.json()["refund_status"] == target
        assert _get_refund(client, refund_id)["refund_status"] == target
    else:
        assert response.status_code == 403
        error = _error(response)
        assert error["code"] == "APPROVAL_LIMIT_EXCEEDED"
        assert error["details"]["approval_limit_cents"] == {"sam": 50_000, "olivia": 500_000}[user]
        assert error["details"]["amount_cents"] == _get_refund(client, refund_id)["amount_cents"]
        assert _get_refund(client, refund_id)["refund_status"] == "pending"


def test_support_can_escalate_a_within_limit_pending_refund(client: TestClient) -> None:
    response = _post(client, "sam", "escalate", "rfnd_001")

    assert response.status_code == 200
    assert response.json()["refund_status"] == "escalated"
    assert response.json()["last_action"] == "refund.escalated"


def test_admin_cannot_escalate(client: TestClient) -> None:
    response = _post(client, "avery", "escalate", "rfnd_001")

    assert response.status_code == 403
    assert _error(response)["code"] == "ACTION_NOT_PERMITTED_FOR_ROLE"
    assert _error(response)["details"] == {"role": "admin", "action": "escalate"}


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_escalated_refund_still_respects_the_limit(client: TestClient, action: str) -> None:
    denied = _post(client, "sam", action, "rfnd_010")
    assert denied.status_code == 403
    assert _error(denied)["code"] == "APPROVAL_LIMIT_EXCEEDED"

    allowed = _post(client, "olivia", action, "rfnd_010")
    assert allowed.status_code == 200
    assert allowed.json()["refund_status"] == {"approve": "approved", "reject": "rejected"}[action]


@pytest.mark.parametrize(
    ("refund_id", "action"),
    [
        ("rfnd_008", "approve"),
        ("rfnd_008", "reject"),
        ("rfnd_008", "escalate"),
        ("rfnd_009", "approve"),
        ("rfnd_009", "reject"),
        ("rfnd_009", "escalate"),
        ("rfnd_010", "escalate"),
    ],
)
def test_illegal_transitions_are_409(client: TestClient, refund_id: str, action: str) -> None:
    before = _get_refund(client, refund_id)

    response = _post(client, "olivia", action, refund_id)

    assert response.status_code == 409
    error = _error(response)
    assert error["code"] == "INVALID_STATE_TRANSITION"
    assert error["details"]["action"] == action
    assert error["details"]["current_status"] == before["refund_status"]
    assert error["details"]["allowed_from"] == (
        ["pending"] if action == "escalate" else ["escalated", "pending"]
    )
    assert _get_refund(client, refund_id) == before


@pytest.mark.parametrize("action", ["approve", "reject", "escalate"])
def test_repeating_a_completed_action_is_409(client: TestClient, action: str) -> None:
    assert _post(client, "olivia", action, "rfnd_001").status_code == 200
    events_after_first = _audit_count(client)

    repeat = _post(client, "olivia", action, "rfnd_001")

    assert repeat.status_code == 409
    assert _error(repeat)["code"] == "INVALID_STATE_TRANSITION"
    assert _audit_count(client) == events_after_first


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"reason": ""},
        {"reason": "   "},
        {"reason": "\n\t "},
        {"reason": None},
        {"reason": 42},
        {"reason": "x" * 1001},
        {"reason": "  " + "x" * 1001 + "  "},
    ],
)
def test_invalid_reasons_are_422_and_change_nothing(client: TestClient, body: Any) -> None:
    before = _get_refund(client, "rfnd_001")
    before_count = _audit_count(client)

    response = _post(client, "sam", "approve", "rfnd_001", body=body)

    assert response.status_code == 422
    assert _error(response)["code"] == "VALIDATION_ERROR"
    assert _get_refund(client, "rfnd_001") == before
    assert _audit_count(client) == before_count


@pytest.mark.parametrize("length", [1, 1000])
def test_reason_length_boundaries_succeed_and_are_stripped(client: TestClient, length: int) -> None:
    raw = "  " + "r" * length + "\n"

    response = _post(client, "sam", "approve", "rfnd_001", body={"reason": raw})

    assert response.status_code == 200
    stored = _get_refund(client, "rfnd_001")
    event = _events_for(client, "rfnd_001")[0]
    assert stored["last_action_reason"] == "r" * length
    assert event["reason"] == "r" * length
    assert event["after_state"]["last_action_reason"] == "r" * length


def test_missing_identity_wins_over_invalid_body(client: TestClient) -> None:
    response = client.post("/api/refunds/rfnd_001/approve", json={"reason": ""})

    assert response.status_code == 401
    assert _error(response)["code"] == "MISSING_IDENTITY"


def test_authorization_wins_over_state_transition(client: TestClient) -> None:
    # rfnd_010 is escalated (so escalate is an illegal transition) *and* Avery may not escalate.
    response = _post(client, "avery", "escalate", "rfnd_010")

    assert response.status_code == 403
    assert _error(response)["code"] == "ACTION_NOT_PERMITTED_FOR_ROLE"


def test_unknown_refund_is_404_for_an_authenticated_actor(client: TestClient) -> None:
    response = _post(client, "avery", "approve", "rfnd_999")

    assert response.status_code == 404
    assert _error(response)["code"] == "NOT_FOUND"
    assert _error(response)["details"] == {"refund_id": "rfnd_999"}


def test_browser_supplied_authorization_claims_are_ignored(client: TestClient) -> None:
    response = client.post(
        "/api/refunds/rfnd_006/approve",
        headers={**SAM, "X-Role": "admin", "X-Approval-Limit": "999999999"},
        json={"reason": "trying to bypass", "role": "admin", "approval_limit_cents": None},
    )

    assert response.status_code == 403
    assert _error(response)["code"] == "APPROVAL_LIMIT_EXCEEDED"


def test_successful_action_writes_exactly_one_complete_audit_event(client: TestClient) -> None:
    before = _get_refund(client, "rfnd_004")
    before_count = _audit_count(client)

    response = _post(client, "olivia", "approve", "rfnd_004", body={"reason": " ok to refund "})

    assert response.status_code == 200
    refund = response.json()
    assert refund == _get_refund(client, "rfnd_004")
    assert refund["refund_status"] == "approved"
    assert refund["last_action"] == "refund.approved"
    assert refund["last_action_by"] == "Olivia Ops"
    assert refund["last_action_reason"] == "ok to refund"
    assert refund["last_action_at"] == refund["updated_at"]
    assert refund["updated_at"] > before["updated_at"]

    assert _audit_count(client) == before_count + 1
    events = _events_for(client, "rfnd_004")
    assert len(events) == 1
    event = events[0]
    assert event["id"].startswith("evt_")
    assert event["occurred_at"] == refund["last_action_at"]
    assert event["actor_user_id"] == "user_olivia_ops"
    assert event["actor_display_name"] == "Olivia Ops"
    assert event["actor_role"] == "operations_manager"
    assert event["action"] == "refund.approved"
    assert event["entity_type"] == "refund"
    assert event["entity_id"] == "rfnd_004"
    assert event["reason"] == "ok to refund"
    assert event["before_state"] == {
        "refund_status": "pending",
        "amount_cents": before["amount_cents"],
        "currency": "USD",
        "risk_level": before["risk_level"],
        "last_action": None,
        "last_action_by": None,
        "last_action_reason": None,
        "last_action_at": None,
    }
    assert event["after_state"] == {
        "refund_status": "approved",
        "amount_cents": before["amount_cents"],
        "currency": "USD",
        "risk_level": before["risk_level"],
        "last_action": "refund.approved",
        "last_action_by": "Olivia Ops",
        "last_action_reason": "ok to refund",
        "last_action_at": refund["last_action_at"],
    }
    seeded = client.get("/api/audit-events/evt_seed_001", headers=AVERY).json()
    assert set(seeded["before_state"]) == set(event["before_state"])
    assert set(seeded["after_state"]) == set(event["after_state"])


def test_unexpected_failure_returns_the_error_envelope_and_persists_nothing(
    seeded_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*_: Any, **__: Any) -> None:
        raise RuntimeError("audit store unavailable")

    monkeypatch.setattr(refund_service, "record_refund_event", explode)
    factory = db.make_session_factory(seeded_engine)

    def override_get_session() -> Any:
        with factory() as session:
            yield session

    app.dependency_overrides[db.get_session] = override_get_session
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            before_count = _audit_count(client)
            response = _post(client, "sam", "approve", "rfnd_001")

            assert response.status_code == 500
            assert _error(response) == {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
                "details": {},
            }
            assert _get_refund(client, "rfnd_001")["refund_status"] == "pending"
            assert _audit_count(client) == before_count
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("user", "refund_id", "expected"),
    [
        ("sam", "rfnd_001", ["approve", "reject", "escalate"]),
        ("sam", "rfnd_003", ["escalate"]),
        ("olivia", "rfnd_003", ["approve", "reject", "escalate"]),
        ("avery", "rfnd_007", ["approve", "reject"]),
        ("sam", "rfnd_010", []),
        ("olivia", "rfnd_010", ["approve", "reject"]),
        ("avery", "rfnd_008", []),
    ],
)
def test_allowed_actions_are_computed_for_the_requesting_user(
    client: TestClient, user: str, refund_id: str, expected: list[str]
) -> None:
    detail = client.get(f"/api/refunds/{refund_id}", headers=USERS[user]).json()
    listed = next(
        r for r in client.get("/api/refunds", headers=USERS[user]).json() if r["id"] == refund_id
    )

    assert detail["allowed_actions"] == expected
    assert listed["allowed_actions"] == expected


def test_allowed_actions_shrink_after_a_mutation(client: TestClient) -> None:
    assert _post(client, "sam", "escalate", "rfnd_001").json()["allowed_actions"] == [
        "approve",
        "reject",
    ]
    assert _post(client, "sam", "approve", "rfnd_001").json()["allowed_actions"] == []
