"""API测试配置"""

from contextlib import ExitStack, asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Match, MatchStatus, PredictedResult, Predictions


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
    # 设置环境变量在导入前
    monkeypatch.setenv("MINIMAL_HEALTH_MODE", "true")
    monkeypatch.setenv("FAST_FAIL", "false")
    monkeypatch.setenv("ENABLE_METRICS", "false")
    monkeypatch.setenv("MINIMAL_API_MODE", "true")  # 只加载健康检查路由

    stack = ExitStack()
    try:
        _install_health_stubs(stack)

        # 延迟导入，在设置好环境变量和 mock 后
        from src.main import app

        app.dependency_overrides = {}
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client
    finally:
        stack.close()


@pytest.fixture
def api_client_full(monkeypatch):
    """API测试客户端，加载所有路由（用于测试非健康检查端点）"""
    # 设置环境变量在导入前
    monkeypatch.setenv("MINIMAL_HEALTH_MODE", "true")
    monkeypatch.setenv("FAST_FAIL", "false")
    monkeypatch.setenv("ENABLE_METRICS", "false")
    monkeypatch.setenv("MINIMAL_API_MODE", "false")  # 加载所有路由

    stack = ExitStack()
    try:
        _install_health_stubs(stack)

        # 额外的mock以避免导入重量级依赖
        mock_prediction_service = MagicMock()
        mock_prediction_service.predict_match = AsyncMock()
        mock_prediction_service.batch_predict_matches = AsyncMock()
        mock_prediction_service.verify_prediction = AsyncMock()

        stack.enter_context(
            patch("src.api.predictions.prediction_service", mock_prediction_service)
        )

        # Mock get_async_session dependency
        @asynccontextmanager
        async def mock_get_async_session():
            mock_session = MagicMock(spec=AsyncSession)
            mock_session.execute = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_session.close = AsyncMock()
            yield mock_session

        stack.enter_context(
            patch("src.api.predictions.get_async_session", mock_get_async_session)
        )

        # 延迟导入，在设置好环境变量和 mock 后
        from src.main import app

        app.dependency_overrides = {}
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client
    finally:
        stack.close()


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


@pytest.fixture
def sample_match():
    """创建一个示例比赛"""
    match = MagicMock(spec=Match)
    match.id = 12345
    match.home_team_id = 10
    match.away_team_id = 20
    match.league_id = 1
    match.match_time = datetime(2025, 9, 15, 15, 0, 0)
    match.match_status = MatchStatus.SCHEDULED
    match.season = "2024-25"
    return match


@pytest.fixture
def sample_match_finished():
    """创建一个已结束的示例比赛"""
    match = MagicMock(spec=Match)
    match.id = 12346
    match.home_team_id = 11
    match.away_team_id = 21
    match.league_id = 2
    match.match_time = datetime(2025, 9, 10, 15, 0, 0)
    match.match_status = MatchStatus.FINISHED
    match.season = "2024-25"
    return match


@pytest.fixture
def sample_prediction():
    """创建一个示例预测"""
    from decimal import Decimal

    prediction = MagicMock(spec=Predictions)
    prediction.id = 1
    prediction.match_id = 12345
    prediction.model_version = "1.0"
    prediction.model_name = "linear_regression"
    prediction.predicted_result = PredictedResult.HOME_WIN
    prediction.home_win_probability = Decimal("0.45")
    prediction.draw_probability = Decimal("0.30")
    prediction.away_win_probability = Decimal("0.25")
    prediction.confidence_score = Decimal("0.45")
    prediction.created_at = datetime.now()
    prediction.is_correct = None
    prediction.actual_result = None
    prediction.verified_at = None
    return prediction


@pytest.fixture
def sample_prediction_data():
    """示例预测数据字典"""
    return {
        "match_id": 12345,
        "model_version": "1.0",
        "model_name": "test_model",
        "predicted_result": "home_win",
        "home_win_probability": 0.45,
        "draw_probability": 0.30,
        "away_win_probability": 0.25,
        "confidence_score": 0.75,
    }
