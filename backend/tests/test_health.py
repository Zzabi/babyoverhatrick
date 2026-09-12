"""Tests for GET /health endpoint."""


def test_health_ok(client):
    """Health endpoint returns 200 with postgres and redis status."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "services" in data
    assert "postgres" in data["services"]
    assert "redis" in data["services"]
    # In a properly configured test environment both should be 'ok'
    assert data["services"]["postgres"] == "ok"


def test_health_status_field(client):
    """Health status field is either 'ok' or 'degraded'."""
    resp = client.get("/health")
    data = resp.json()
    assert data["status"] in {"ok", "degraded"}
