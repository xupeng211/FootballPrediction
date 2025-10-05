"""API测试配置"""

from contextlib import ExitStack
from datetime import datetime
from typing import AsyncGenerator
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

    stack.enter_context(patch("src.api.health.get_database_manager", return_value=mock_db_manager))

    # 创建符合schema的完整响应
    health_check_response = {
        "healthy": True,
        "status": "healthy",
        "response_time_ms": 0.1,
        "details": {"message": "Service is healthy"},
    }
    async_success = AsyncMock(return_value=health_check_response)
    stack.enter_context(patch("src.api.health._collect_database_health", new=async_success))
    stack.enter_context(patch("src.api.health._check_mlflow", new=async_success))
    stack.enter_context(patch("src.api.health._check_redis", new=async_success))
    stack.enter_context(patch("src.api.health._check_kafka", new=async_success))
    stack.enter_context(patch("src.api.health._check_filesystem", new=async_success))

    # Mock数据质量监控器 - 模块不存在时跳过
    # 注意：这个模块可能不存在，所以暂时注释掉
    # mock_dqm = MagicMock()
    # mock_dqm.generate_quality_report = AsyncMock(return_value={
    #     "overall_status": "healthy",
    #     "quality_score": 95.0,
    #     "anomalies": {"count": 0, "items": []},
    #     "report_time": datetime.now().isoformat(),
    # })
    # stack.enter_context(
    #     patch("src.data.quality.data_quality_monitor.DataQualityMonitor",
    #           return_value=mock_dqm)
    # )


@pytest.fixture
def api_client(monkeypatch):
    """API测试客户端，默认启用最小化健康检查模式"""
    # 设置环境变量在导入前
    monkeypatch.setenv("MINIMAL_HEALTH_MODE", "true")
    monkeypatch.setenv("FAST_FAIL", "false")
    monkeypatch.setenv("ENABLE_METRICS", "false")
    monkeypatch.setenv("ENABLE_FEAST", "false")
    monkeypatch.setenv("MINIMAL_API_MODE", "true")  # 只加载健康检查路由

    stack = ExitStack()
    try:
        _install_health_stubs(stack)

        # 延迟导入，在设置好环境变量和 mock 后
        import importlib
        from src import main as main_module

        main = importlib.reload(main_module)
        app = main.app

        app.dependency_overrides = {}
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client
    finally:
        stack.close()


@pytest.fixture
def mock_async_session():
    """创建一个可配置的mock数据库会话"""
    mock_session = MagicMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()
    return mock_session


@pytest.fixture
def api_client_full(monkeypatch):
    """API测试客户端，加载所有路由（用于测试非健康检查端点）

    使用dependency_overrides来注入mock dependencies，这是FastAPI推荐的测试方式。
    返回一个包含client和mock_session的命名空间对象，以便测试可以配置mock行为。
    """
    # 设置环境变量在导入前
    monkeypatch.setenv("MINIMAL_HEALTH_MODE", "true")
    monkeypatch.setenv("FAST_FAIL", "false")
    monkeypatch.setenv("ENABLE_METRICS", "false")
    monkeypatch.setenv("ENABLE_FEAST", "false")
    monkeypatch.setenv("MINIMAL_API_MODE", "false")  # 加载所有路由

    # 创建mock session - 必须在这里创建，确保是同一个实例
    mock_session = MagicMock(spec=AsyncSession)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.close = AsyncMock()

    stack = ExitStack()
    try:
        _install_health_stubs(stack)

        # 延迟导入，在设置好环境变量和 mock 后
        import importlib
        from src import main as main_module
        from src.database.connection import get_async_session

        main = importlib.reload(main_module)
        app = main.app

        # 创建返回mock session的异步生成器
        async def override_get_async_session() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        # 使用FastAPI的dependency_overrides机制
        app.dependency_overrides[get_async_session] = override_get_async_session

        with TestClient(app, raise_server_exceptions=False) as client:
            # 为了向后兼容，返回client本身，但添加mock_session属性
            client.mock_session = mock_session
            yield client
    finally:
        # 清理dependency overrides - 在测试结束后清理
        try:
            from src.main import app

            app.dependency_overrides.clear()
        except Exception:
            pass
        stack.close()


@pytest.fixture
def mock_prediction_service_instance():
    """创建一个可配置的mock预测服务实例"""
    mock_service = MagicMock()
    mock_service.predict_match = AsyncMock()
    mock_service.batch_predict_matches = AsyncMock()
    mock_service.verify_prediction = AsyncMock()
    return mock_service


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
