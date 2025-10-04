"""API测试配置"""

from contextlib import ExitStack

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


def _install_health_stubs(stack: ExitStack) -> None:
    """将健康检查依赖替换为轻量桩对象"""

    mock_db_manager = MagicMock()
    session_cm = MagicMock()
    session_cm.__enter__.return_value = MagicMock()
    session_cm.__exit__.return_value = False
    mock_db_manager.get_session.return_value = session_cm

    stack.enter_context(
        patch("src.api.health.get_database_manager", return_value=mock_db_manager)
    )

    # 创建符合schema的完整响应
    health_check_response = {
        "healthy": True,
        "status": "healthy",
        "response_time_ms": 0.1,
        "details": {"message": "Service is healthy"},
    }
    async_success = AsyncMock(return_value=health_check_response)
    stack.enter_context(
        patch("src.api.health._collect_database_health", new=async_success)
    )
    stack.enter_context(patch("src.api.health._check_mlflow", new=async_success))
    stack.enter_context(patch("src.api.health._check_redis", new=async_success))
    stack.enter_context(patch("src.api.health._check_kafka", new=async_success))
    stack.enter_context(patch("src.api.health._check_filesystem", new=async_success))


@pytest.fixture
def api_client(monkeypatch):
    """API测试客户端，默认启用最小化健康检查模式"""
    from src.main import app

    monkeypatch.setenv("MINIMAL_HEALTH_MODE", "true")
    monkeypatch.setenv("FAST_FAIL", "false")
    monkeypatch.setenv("ENABLE_METRICS", "false")

    with ExitStack() as stack:
        _install_health_stubs(stack)
        app.dependency_overrides = {}
        with TestClient(app) as client:
            yield client


@pytest.fixture
def mock_auth_service():
    """模拟认证服务"""
    with patch("src.api.auth.AuthService") as mock:
        mock.verify_token.return_value = {"user_id": 1, "email": "test@example.com"}
        yield mock


@pytest.fixture
def mock_prediction_service():
    """模拟预测服务"""
    with patch("src.api.predictions.PredictionService") as mock:
        mock.create_prediction.return_value = {"id": 1, "status": "success"}
        mock.get_prediction.return_value = {"id": 1, "result": "2-1"}
        yield mock
