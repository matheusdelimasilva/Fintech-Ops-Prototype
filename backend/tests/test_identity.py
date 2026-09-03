import pytest
from fastapi.testclient import TestClient

from tests.conftest import AVERY, OLIVIA, SAM

PROTECTED_READ_ROUTES = [
    "/api/session",
    "/api/refunds",
    "/api/refunds/rfnd_001",
    "/api/feature-flags",
    "/api/feature-flags/flag_bulk_export_staging",
    "/api/audit-events",
    "/api/audit-events/evt_seed_001",
]


def test_health_is_unauthenticated(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_session_without_header_is_401_missing_identity(client: TestClient) -> None:
    response = client.get("/api/session")

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "MISSING_IDENTITY"
    assert set(body["error"]) == {"code", "message", "details"}


def test_session_with_unknown_user_is_401_unknown_identity(client: TestClient) -> None:
    response = client.get("/api/session", headers={"X-Demo-User-Id": "user_mallory"})

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNKNOWN_IDENTITY"
    assert body["error"]["details"] == {"demo_user_id": "user_mallory"}


@pytest.mark.parametrize("path", PROTECTED_READ_ROUTES)
def test_every_api_read_route_requires_identity(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "MISSING_IDENTITY"


@pytest.mark.parametrize(
    ("headers", "expected_role", "expected_policy"),
    [
        (
            SAM,
            "support_agent",
            {
                "approval_limit_cents": 50_000,
                "can_edit_staging_flags": False,
                "can_edit_production_flags": False,
            },
        ),
        (
            OLIVIA,
            "operations_manager",
            {
                "approval_limit_cents": 500_000,
                "can_edit_staging_flags": True,
                "can_edit_production_flags": False,
            },
        ),
        (
            AVERY,
            "admin",
            {
                "approval_limit_cents": None,
                "can_edit_staging_flags": True,
                "can_edit_production_flags": True,
            },
        ),
    ],
)
def test_session_resolves_role_and_policy_server_side(
    client: TestClient,
    headers: dict[str, str],
    expected_role: str,
    expected_policy: dict[str, object],
) -> None:
    response = client.get("/api/session", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["id"] == headers["X-Demo-User-Id"]
    assert body["user"]["role"] == expected_role
    assert body["policy"] == expected_policy
    assert [user["id"] for user in body["available_users"]] == [
        "user_avery_admin",
        "user_olivia_ops",
        "user_sam_support",
    ]
    assert "synthetic" in body["identity_note"].lower()


def test_browser_supplied_role_claims_are_ignored(client: TestClient) -> None:
    response = client.get(
        "/api/session",
        headers={**SAM, "X-Role": "admin", "X-Approval-Limit-Cents": "0"},
        params={"role": "admin"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "support_agent"
    assert response.json()["policy"]["approval_limit_cents"] == 50_000
