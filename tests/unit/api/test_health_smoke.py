"""Smoke tests for the /health endpoint."""

import os

import pytest
from fastapi.testclient import TestClient

# Ensure minimal mode for the app under test
os.environ.setdefault("MINIMAL_HEALTH_MODE", "true")
os.environ.setdefault("FAST_FAIL", "false")
os.environ.setdefault("ENABLE_METRICS", "false")

from src.main import app  # noqa: E402  (import after environment setup)

client = TestClient(app)


@pytest.mark.unit
def test_health_endpoint_returns_200():
    response = client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload.get("status") == "healthy"
    assert "checks" in payload
    assert "database" in payload["checks"]
    assert payload["checks"]["database"]["status"] in {"healthy", "skipped"}
