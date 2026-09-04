"""API-level tests for PATCH /api/feature-flags/{id}.

State is verified through GET calls (a fresh session per request), never through objects
the mutation itself returned.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import AVERY, OLIVIA, SAM

USERS = {"sam": SAM, "olivia": OLIVIA, "avery": AVERY}
STAGING = "flag_bulk_export_staging"  # enabled=True, rollout=50
PRODUCTION = "flag_new_risk_scoring_production"  # enabled=True, rollout=10
REASON = "Controlled rollout for verification."


def _patch(client: TestClient, user: str, flag_id: str, body: Any) -> Any:
    return client.patch(f"/api/feature-flags/{flag_id}", headers=USERS[user], json=body)


def _get_flag(client: TestClient, flag_id: str, user: str = "avery") -> dict[str, Any]:
    return client.get(f"/api/feature-flags/{flag_id}", headers=USERS[user]).json()


def _events_for(client: TestClient, flag_id: str) -> list[dict[str, Any]]:
    return client.get(
        "/api/audit-events",
        headers=AVERY,
        params={"entity_type": "feature_flag", "entity_id": flag_id},
    ).json()


def _audit_count(client: TestClient) -> int:
    return len(client.get("/api/audit-events", headers=AVERY).json())


def _error(response: Any) -> dict[str, Any]:
    return response.json()["error"]


def _assert_unchanged(
    client: TestClient, flag_id: str, before: dict[str, Any], before_count: int
) -> None:
    assert _get_flag(client, flag_id) == before
    assert _audit_count(client) == before_count


# --- permissions ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("user", "flag_id", "allowed"),
    [
        ("sam", STAGING, False),
        ("sam", PRODUCTION, False),
        ("olivia", STAGING, True),
        ("olivia", PRODUCTION, False),
        ("avery", STAGING, True),
        ("avery", PRODUCTION, True),
    ],
)
def test_environment_permissions_are_enforced_at_the_api(
    client: TestClient, user: str, flag_id: str, allowed: bool
) -> None:
    before = _get_flag(client, flag_id)
    before_count = _audit_count(client)
    body = {"enabled": not before["enabled"], "reason": REASON, "confirm_production": True}

    response = _patch(client, user, flag_id, body)

    if allowed:
        assert response.status_code == 200
        assert response.json()["enabled"] is (not before["enabled"])
        assert _get_flag(client, flag_id)["enabled"] is (not before["enabled"])
        assert _audit_count(client) == before_count + 1
    else:
        assert response.status_code == 403
        error = _error(response)
        assert error["code"] == "ACTION_NOT_PERMITTED_FOR_ROLE"
        assert error["details"]["environment"] == before["environment"]
        assert (
            error["details"]["role"]
            == {
                "sam": "support_agent",
                "olivia": "operations_manager",
            }[user]
        )
        _assert_unchanged(client, flag_id, before, before_count)


def test_browser_supplied_authorization_claims_are_ignored(client: TestClient) -> None:
    before = _get_flag(client, PRODUCTION)
    before_count = _audit_count(client)

    response = client.patch(
        f"/api/feature-flags/{PRODUCTION}",
        headers={**OLIVIA, "X-Role": "admin"},
        json={"enabled": False, "reason": REASON, "confirm_production": True, "role": "admin"},
    )

    assert response.status_code == 403
    _assert_unchanged(client, PRODUCTION, before, before_count)


def test_missing_identity_wins_over_invalid_body(client: TestClient) -> None:
    response = client.patch(f"/api/feature-flags/{STAGING}", json={"reason": ""})

    assert response.status_code == 401
    assert _error(response)["code"] == "MISSING_IDENTITY"


# --- production confirmation ---------------------------------------------------------------


@pytest.mark.parametrize("confirm", [None, False, "true", 1])
def test_production_change_without_true_confirmation_is_422(
    client: TestClient, confirm: Any
) -> None:
    before = _get_flag(client, PRODUCTION)
    before_count = _audit_count(client)
    body: dict[str, Any] = {"enabled": False, "reason": REASON}
    if confirm is not None:
        body["confirm_production"] = confirm

    response = _patch(client, "avery", PRODUCTION, body)

    assert response.status_code == 422
    error = _error(response)
    if confirm in (None, False):
        assert error["code"] == "PRODUCTION_CONFIRMATION_REQUIRED"
        assert error["details"] == {"flag_id": PRODUCTION, "environment": "production"}
    else:
        # Only a literal JSON `true` counts; look-alikes fail schema validation.
        assert error["code"] == "VALIDATION_ERROR"
    _assert_unchanged(client, PRODUCTION, before, before_count)


def test_unauthorized_user_gets_403_before_confirmation_is_considered(client: TestClient) -> None:
    response = _patch(client, "olivia", PRODUCTION, {"enabled": False, "reason": REASON})

    assert response.status_code == 403
    assert _error(response)["code"] == "ACTION_NOT_PERMITTED_FOR_ROLE"


def test_staging_change_ignores_confirmation_flag(client: TestClient) -> None:
    response = _patch(client, "olivia", STAGING, {"rollout_percent": 25, "reason": REASON})

    assert response.status_code == 200
    assert _get_flag(client, STAGING)["rollout_percent"] == 25


# --- rollout and body validation -----------------------------------------------------------


@pytest.mark.parametrize("rollout", [0, 100])
def test_rollout_boundaries_succeed(client: TestClient, rollout: int) -> None:
    response = _patch(client, "olivia", STAGING, {"rollout_percent": rollout, "reason": REASON})

    assert response.status_code == 200
    assert response.json()["rollout_percent"] == rollout
    assert _get_flag(client, STAGING)["rollout_percent"] == rollout


@pytest.mark.parametrize(
    "body",
    [
        {"rollout_percent": -1, "reason": REASON},
        {"rollout_percent": 101, "reason": REASON},
        {"rollout_percent": 12.5, "reason": REASON},
        {"rollout_percent": "50", "reason": REASON},
        {"rollout_percent": None, "reason": REASON},
        {"enabled": None, "reason": REASON},
        {"enabled": "yes", "reason": REASON},
        {"reason": REASON},
        {"enabled": False},
        {"enabled": False, "reason": ""},
        {"enabled": False, "reason": "   "},
        {"enabled": False, "reason": "\n\t "},
        {"enabled": False, "reason": None},
        {"enabled": False, "reason": "x" * 1001},
    ],
)
def test_invalid_bodies_are_422_and_change_nothing(client: TestClient, body: Any) -> None:
    before = _get_flag(client, STAGING)
    before_count = _audit_count(client)

    response = _patch(client, "olivia", STAGING, body)

    assert response.status_code == 422
    assert _error(response)["code"] == "VALIDATION_ERROR"
    _assert_unchanged(client, STAGING, before, before_count)


@pytest.mark.parametrize("length", [1, 1000])
def test_reason_length_boundaries_succeed_and_are_stripped(client: TestClient, length: int) -> None:
    raw = "  " + "r" * length + "\n"

    response = _patch(client, "olivia", STAGING, {"enabled": False, "reason": raw})

    assert response.status_code == 200
    assert _events_for(client, STAGING)[0]["reason"] == "r" * length


# --- no-op ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        {"enabled": True, "reason": REASON},
        {"rollout_percent": 50, "reason": REASON},
        {"enabled": True, "rollout_percent": 50, "reason": REASON},
    ],
)
def test_no_op_is_409_and_writes_nothing(client: TestClient, body: Any) -> None:
    before = _get_flag(client, STAGING)
    before_count = _audit_count(client)

    response = _patch(client, "olivia", STAGING, body)

    assert response.status_code == 409
    error = _error(response)
    assert error["code"] == "NO_CHANGE"
    assert error["details"]["current"] == {"enabled": True, "rollout_percent": 50}
    _assert_unchanged(client, STAGING, before, before_count)


def test_repeating_a_completed_update_is_409_no_change(client: TestClient) -> None:
    body = {"enabled": False, "reason": REASON}
    assert _patch(client, "olivia", STAGING, body).status_code == 200
    count_after_first = _audit_count(client)

    repeat = _patch(client, "olivia", STAGING, body)

    assert repeat.status_code == 409
    assert _error(repeat)["code"] == "NO_CHANGE"
    assert _audit_count(client) == count_after_first


def test_unknown_flag_is_404(client: TestClient) -> None:
    response = _patch(client, "avery", "flag_nope", {"enabled": True, "reason": REASON})

    assert response.status_code == 404
    assert _error(response)["details"] == {"flag_id": "flag_nope"}


# --- success and audit ---------------------------------------------------------------------


def test_successful_update_writes_exactly_one_complete_audit_event(client: TestClient) -> None:
    before = _get_flag(client, PRODUCTION)
    before_count = _audit_count(client)

    response = _patch(
        client,
        "avery",
        PRODUCTION,
        {
            "enabled": False,
            "rollout_percent": 0,
            "reason": " kill switch ",
            "confirm_production": True,
        },
    )

    assert response.status_code == 200
    flag = response.json()
    assert flag == _get_flag(client, PRODUCTION)
    assert set(flag) == set(before)
    assert flag["enabled"] is False
    assert flag["rollout_percent"] == 0
    assert flag["updated_at"] > before["updated_at"]
    assert flag["can_edit"] is True
    assert flag["requires_confirmation"] is True

    assert _audit_count(client) == before_count + 1
    events = _events_for(client, PRODUCTION)
    assert len(events) == 1
    event = events[0]
    assert event["id"].startswith("evt_")
    assert event["occurred_at"] == flag["updated_at"]
    assert event["actor_user_id"] == "user_avery_admin"
    assert event["actor_display_name"] == "Avery Admin"
    assert event["actor_role"] == "admin"
    assert event["action"] == "feature_flag.updated"
    assert event["entity_type"] == "feature_flag"
    assert event["entity_id"] == PRODUCTION
    assert event["reason"] == "kill switch"
    assert event["before_state"] == {
        "key": "new_risk_scoring",
        "environment": "production",
        "enabled": True,
        "rollout_percent": 10,
        "updated_at": before["updated_at"],
    }
    assert event["after_state"] == {
        "key": "new_risk_scoring",
        "environment": "production",
        "enabled": False,
        "rollout_percent": 0,
        "updated_at": flag["updated_at"],
    }


def test_partial_update_leaves_the_other_field_alone(client: TestClient) -> None:
    response = _patch(client, "olivia", STAGING, {"enabled": False, "reason": REASON})

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["rollout_percent"] == 50


# --- capability hints ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("user", "expected"),
    [
        ("sam", {STAGING: (False, False), PRODUCTION: (False, True)}),
        ("olivia", {STAGING: (True, False), PRODUCTION: (False, True)}),
        ("avery", {STAGING: (True, False), PRODUCTION: (True, True)}),
    ],
)
def test_reads_expose_server_computed_capabilities(
    client: TestClient, user: str, expected: dict[str, tuple[bool, bool]]
) -> None:
    flags = {f["id"]: f for f in client.get("/api/feature-flags", headers=USERS[user]).json()}

    for flag_id, (can_edit, requires_confirmation) in expected.items():
        assert flags[flag_id]["can_edit"] is can_edit
        assert flags[flag_id]["requires_confirmation"] is requires_confirmation
        detail = _get_flag(client, flag_id, user=user)
        assert detail["can_edit"] is can_edit
        assert detail["requires_confirmation"] is requires_confirmation
