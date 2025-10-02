import os
import warnings
from typing import Any, Dict

import pytest
from fastapi import HTTPException, status
from unittest.mock import AsyncMock

os.environ.setdefault("MINIMAL_API_MODE", "true")
warnings.filterwarnings("ignore", category=UserWarning)

import src.api.health as health_module  # noqa: E402  pylint: disable=wrong-import-position

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


@pytest.fixture(autouse=True)
def minimal_health_mode(monkeypatch):
    monkeypatch.setenv("FAST_FAIL", "false")
    monkeypatch.setenv("MINIMAL_HEALTH_MODE", "true")
    monkeypatch.setattr(health_module, "FAST_FAIL", False, raising=False)
    monkeypatch.setattr(health_module, "MINIMAL_HEALTH_MODE", True, raising=False)
    monkeypatch.setattr(health_module, "_optional_checks_enabled", lambda: False)


def _healthy_payload(name: str) -> Dict[str, Any]:
    return {
        "healthy": True,
        "status": "healthy",
        "response_time_ms": 1.2,
        "details": {"message": f"{name} ok"},
    }


def test_router_exposes_expected_paths():
    routes = {route.path for route in health_module.router.routes}

    assert "/health" in routes
    assert "/health/liveness" in routes
    assert "/health/readiness" in routes


@pytest.mark.asyncio
async def test_health_check_full_mode(monkeypatch):
    monkeypatch.setattr(health_module, "MINIMAL_HEALTH_MODE", False, raising=False)
    monkeypatch.setattr(health_module, "FAST_FAIL", True, raising=False)
    monkeypatch.setattr(health_module, "_optional_checks_enabled", lambda: True)
    monkeypatch.setattr(
        health_module,
        "_collect_database_health",
        AsyncMock(return_value=_healthy_payload("database")),
    )
    monkeypatch.setattr(
        health_module,
        "_check_redis",
        AsyncMock(return_value=_healthy_payload("redis")),
    )
    monkeypatch.setattr(
        health_module,
        "_check_kafka",
        AsyncMock(return_value=_healthy_payload("kafka")),
    )
    monkeypatch.setattr(
        health_module,
        "_check_mlflow",
        AsyncMock(return_value=_healthy_payload("mlflow")),
    )
    monkeypatch.setattr(
        health_module,
        "_check_filesystem",
        AsyncMock(return_value=_healthy_payload("filesystem")),
    )

    result = await health_module.health_check()

    assert result["status"] == "healthy"
    assert result["mode"] == "full"
    assert set(result["checks"].keys()) == {
        "database",
        "redis",
        "kafka",
        "mlflow",
        "filesystem",
    }


@pytest.mark.asyncio
async def test_health_check_minimal_mode_skips_optional(monkeypatch):
    monkeypatch.setattr(health_module, "MINIMAL_HEALTH_MODE", True, raising=False)
    monkeypatch.setattr(health_module, "FAST_FAIL", False, raising=False)

    result = await health_module.health_check()

    assert result["mode"] == "minimal"
    assert result["checks"]["database"]["status"] == "skipped"
    assert result["checks"]["redis"]["status"] == "skipped"


@pytest.mark.asyncio
async def test_health_check_raises_when_dependency_unhealthy(monkeypatch):
    monkeypatch.setattr(health_module, "MINIMAL_HEALTH_MODE", False, raising=False)
    monkeypatch.setattr(health_module, "FAST_FAIL", True, raising=False)
    monkeypatch.setattr(health_module, "_optional_checks_enabled", lambda: True)
    unhealthy = {"healthy": False, "status": "unhealthy"}
    monkeypatch.setattr(
        health_module,
        "_collect_database_health",
        AsyncMock(return_value=unhealthy),
    )
    monkeypatch.setattr(
        health_module,
        "_check_redis",
        AsyncMock(return_value=_healthy_payload("redis")),
    )
    monkeypatch.setattr(
        health_module,
        "_check_kafka",
        AsyncMock(return_value=_healthy_payload("kafka")),
    )
    monkeypatch.setattr(
        health_module,
        "_check_mlflow",
        AsyncMock(return_value=_healthy_payload("mlflow")),
    )
    monkeypatch.setattr(
        health_module,
        "_check_filesystem",
        AsyncMock(return_value=_healthy_payload("filesystem")),
    )

    with pytest.raises(HTTPException) as exc:
        await health_module.health_check()

    assert exc.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert exc.value.detail["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_readiness_check_reports_dependencies(monkeypatch):
    monkeypatch.setattr(health_module, "MINIMAL_HEALTH_MODE", False, raising=False)
    monkeypatch.setattr(health_module, "_optional_checks_enabled", lambda: True)
    monkeypatch.setattr(
        health_module,
        "_collect_database_health",
        AsyncMock(return_value=_healthy_payload("database")),
    )
    monkeypatch.setattr(
        health_module,
        "_check_redis",
        AsyncMock(return_value=_healthy_payload("redis")),
    )
    monkeypatch.setattr(
        health_module,
        "_check_kafka",
        AsyncMock(return_value=_healthy_payload("kafka")),
    )
    monkeypatch.setattr(
        health_module,
        "_check_mlflow",
        AsyncMock(return_value=_healthy_payload("mlflow")),
    )

    result = await health_module.readiness_check()

    assert result["ready"] is True
    assert all(check["healthy"] for check in result["checks"].values())


@pytest.mark.asyncio
async def test_readiness_check_raises_when_any_dependency_fails(monkeypatch):
    monkeypatch.setattr(health_module, "MINIMAL_HEALTH_MODE", False, raising=False)
    monkeypatch.setattr(health_module, "_optional_checks_enabled", lambda: False)
    unhealthy = {"healthy": False, "status": "unhealthy"}
    monkeypatch.setattr(
        health_module,
        "_collect_database_health",
        AsyncMock(return_value=unhealthy),
    )
    monkeypatch.setattr(
        health_module,
        "_check_redis",
        AsyncMock(return_value=_healthy_payload("redis")),
    )
    monkeypatch.setattr(
        health_module,
        "_check_kafka",
        AsyncMock(return_value=_healthy_payload("kafka")),
    )
    monkeypatch.setattr(
        health_module,
        "_check_mlflow",
        AsyncMock(return_value=_healthy_payload("mlflow")),
    )

    with pytest.raises(HTTPException) as exc:
        await health_module.readiness_check()

    assert exc.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert exc.value.detail["ready"] is False
