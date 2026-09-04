import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import AVERY, OLIVIA, SAM

PATH_PARAMS = {
    "{refund_id}": "rfnd_001",
    "{flag_id}": "flag_bulk_export_staging",
    "{event_id}": "evt_seed_001",
}


def _concrete(path: str) -> str:
    for placeholder, value in PATH_PARAMS.items():
        path = path.replace(placeholder, value)
    assert "{" not in path, f"unmapped path parameter in {path}"
    return path


# Derived from the OpenAPI schema so a route added without the identity dependency fails here.
EVERY_API_OPERATION = sorted(
    (method.upper(), _concrete(path))
    for path, operations in app.openapi()["paths"].items()
    if path.startswith("/api/")
    for method in operations
)


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


def test_schema_lists_the_expected_api_operations() -> None:
    assert len(EVERY_API_OPERATION) == 11
    assert ("POST", "/api/refunds/rfnd_001/approve") in EVERY_API_OPERATION
    assert ("PATCH", "/api/feature-flags/flag_bulk_export_staging") in EVERY_API_OPERATION


@pytest.mark.parametrize(("method", "path"), EVERY_API_OPERATION)
def test_every_api_operation_in_the_schema_requires_identity(
    client: TestClient, method: str, path: str
) -> None:
    response = client.request(method, path, json={"reason": "valid reason"})

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
                "can_escalate_refunds": True,
            },
        ),
        (
            OLIVIA,
            "operations_manager",
            {
                "approval_limit_cents": 500_000,
                "can_edit_staging_flags": True,
                "can_edit_production_flags": False,
                "can_escalate_refunds": True,
            },
        ),
        (
            AVERY,
            "admin",
            {
                "approval_limit_cents": None,
                "can_edit_staging_flags": True,
                "can_edit_production_flags": True,
                "can_escalate_refunds": False,
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
