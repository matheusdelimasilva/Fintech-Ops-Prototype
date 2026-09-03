from fastapi.testclient import TestClient

from tests.conftest import OLIVIA, SAM


def test_list_refunds_returns_seed_in_deterministic_order(client: TestClient) -> None:
    response = client.get("/api/refunds", headers=SAM)

    assert response.status_code == 200
    refunds = response.json()
    assert len(refunds) == 12
    created = [r["created_at"] for r in refunds]
    assert created == sorted(created, reverse=True)
    assert refunds[0]["id"] == "rfnd_012"
    assert refunds[-1]["id"] == "rfnd_009"


def test_list_refunds_filters(client: TestClient) -> None:
    by_status = client.get("/api/refunds", headers=SAM, params={"status": "escalated"}).json()
    assert [r["id"] for r in by_status] == ["rfnd_010"]

    by_risk = client.get("/api/refunds", headers=SAM, params={"risk_level": "high"}).json()
    assert {r["risk_level"] for r in by_risk} == {"high"}
    assert len(by_risk) == 4

    by_search = client.get("/api/refunds", headers=SAM, params={"search": "NORTHWIND"}).json()
    assert [r["id"] for r in by_search] == ["rfnd_007"]

    by_txn = client.get("/api/refunds", headers=SAM, params={"search": "txn-2026-0003"}).json()
    assert [r["id"] for r in by_txn] == ["rfnd_003"]

    combined = client.get(
        "/api/refunds", headers=SAM, params={"status": "pending", "risk_level": "low"}
    ).json()
    assert {r["id"] for r in combined} == {"rfnd_001", "rfnd_002", "rfnd_011"}


def test_list_refunds_rejects_invalid_enum_with_error_envelope(client: TestClient) -> None:
    response = client.get("/api/refunds", headers=SAM, params={"status": "bogus"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]["errors"][0]["loc"] == ["query", "status"]


def test_read_refund_detail(client: TestClient) -> None:
    response = client.get("/api/refunds/rfnd_008", headers=SAM)

    assert response.status_code == 200
    body = response.json()
    assert body["refund_status"] == "approved"
    assert body["amount_cents"] == 12_999
    assert body["currency"] == "USD"
    assert body["last_action"] == "refund.approved"
    assert body["last_action_by"] == "Sam Support"
    assert body["last_action_at"] == "2026-01-04T15:02:00Z"


def test_read_unknown_refund_is_404(client: TestClient) -> None:
    response = client.get("/api/refunds/rfnd_999", headers=SAM)

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "NOT_FOUND",
        "message": "Refund not found.",
        "details": {"refund_id": "rfnd_999"},
    }


def test_money_is_always_an_integer_on_the_wire(client: TestClient) -> None:
    refunds = client.get("/api/refunds", headers=SAM).json()
    events = client.get("/api/audit-events", headers=SAM).json()

    assert refunds
    for refund in refunds:
        assert type(refund["amount_cents"]) is int
    for event in events:
        for state in (event["before_state"], event["after_state"]):
            assert type(state["amount_cents"]) is int

    assert not any(isinstance(value, float) for refund in refunds for value in refund.values())


def test_list_feature_flags(client: TestClient) -> None:
    response = client.get("/api/feature-flags", headers=SAM)

    assert response.status_code == 200
    flags = response.json()
    assert [(f["key"], f["environment"]) for f in flags] == [
        ("bulk_export", "staging"),
        ("instant_refunds", "production"),
        ("instant_refunds", "staging"),
        ("new_risk_scoring", "production"),
    ]
    assert all(0 <= f["rollout_percent"] <= 100 for f in flags)

    production = client.get(
        "/api/feature-flags", headers=SAM, params={"environment": "production"}
    ).json()
    assert {f["environment"] for f in production} == {"production"}
    assert len(production) == 2

    invalid = client.get("/api/feature-flags", headers=SAM, params={"environment": "qa"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"


def test_read_feature_flag_detail_and_404(client: TestClient) -> None:
    found = client.get("/api/feature-flags/flag_bulk_export_staging", headers=OLIVIA)
    assert found.status_code == 200
    assert found.json()["rollout_percent"] == 50

    missing = client.get("/api/feature-flags/flag_nope", headers=OLIVIA)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"


def test_list_audit_events_newest_first_with_parsed_states(client: TestClient) -> None:
    response = client.get("/api/audit-events", headers=SAM)

    assert response.status_code == 200
    events = response.json()
    assert [e["id"] for e in events] == ["evt_seed_003", "evt_seed_002", "evt_seed_001"]
    occurred = [e["occurred_at"] for e in events]
    assert occurred == sorted(occurred, reverse=True)

    approved = events[-1]
    assert approved["actor_user_id"] == "user_sam_support"
    assert approved["actor_role"] == "support_agent"
    assert approved["action"] == "refund.approved"
    assert approved["before_state"]["refund_status"] == "pending"
    assert approved["after_state"]["refund_status"] == "approved"
    assert approved["reason"]


def test_list_audit_events_filters(client: TestClient) -> None:
    by_entity = client.get(
        "/api/audit-events",
        headers=SAM,
        params={"entity_type": "refund", "entity_id": "rfnd_009"},
    ).json()
    assert [e["id"] for e in by_entity] == ["evt_seed_002"]

    by_actor = client.get(
        "/api/audit-events", headers=SAM, params={"actor": "user_sam_support"}
    ).json()
    assert [e["id"] for e in by_actor] == ["evt_seed_003", "evt_seed_001"]

    by_action = client.get(
        "/api/audit-events", headers=SAM, params={"action": "refund.rejected"}
    ).json()
    assert [e["id"] for e in by_action] == ["evt_seed_002"]

    none = client.get(
        "/api/audit-events", headers=SAM, params={"entity_type": "feature_flag"}
    ).json()
    assert none == []

    detail = client.get("/api/audit-events/evt_seed_001", headers=SAM)
    assert detail.status_code == 200
    assert detail.json()["entity_id"] == "rfnd_008"


def test_audit_events_are_read_only_through_the_api(client: TestClient) -> None:
    openapi = client.get("/openapi.json").json()

    audit_paths = {path: ops for path, ops in openapi["paths"].items() if "audit-events" in path}
    assert audit_paths
    for ops in audit_paths.values():
        assert set(ops) == {"get"}

    for method in ("post", "put", "patch", "delete"):
        response = client.request(method, "/api/audit-events/evt_seed_001", headers=SAM)
        assert response.status_code == 405
