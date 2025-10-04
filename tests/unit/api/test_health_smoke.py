"""Smoke tests for the /health endpoint."""

import pytest


@pytest.mark.unit
def test_health_endpoint_returns_200(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload.get("status") == "healthy"
    assert "checks" in payload
    assert "database" in payload["checks"]
    assert payload["checks"]["database"]["status"] in {"healthy", "skipped"}
