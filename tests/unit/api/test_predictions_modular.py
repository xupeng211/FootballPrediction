"""
预测API模块化测试
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException


def test_module_imports():
    """测试模块导入"""
    # 测试导入新模块
    from src.api.predictions_mod import (
        router,
        get_rate_limiter,
        is_rate_limit_available,
        get_match_prediction_handler,
        predict_match_handler,
        batch_predict_matches_handler,
        get_match_prediction_history_handler,
        get_recent_predictions_handler,
        verify_prediction_handler,
    )

    assert router is not None
    assert get_rate_limiter is not None
    assert is_rate_limit_available is not None
    assert get_match_prediction_handler is not None
    assert predict_match_handler is not None
    assert batch_predict_matches_handler is not None
    assert get_match_prediction_history_handler is not None
    assert get_recent_predictions_handler is not None
    assert verify_prediction_handler is not None


def test_rate_limiter():
    """测试速率限制器"""
    from src.api.predictions_mod.rate_limiter import (
        get_rate_limiter,
        is_rate_limit_available,
    )

    limiter = get_rate_limiter()
    assert limiter is not None

    # 检查速率限制是否可用
    available = is_rate_limit_available()
    assert isinstance(available, bool)


def test_prediction_handlers_import():
    """测试预测处理器导入"""
    from src.api.predictions_mod.prediction_handlers import (
        _format_cached_prediction,
        _format_realtime_prediction,
    )

    # 测试格式化函数存在
    assert _format_cached_prediction is not None
    assert _format_realtime_prediction is not None


@pytest.mark.asyncio
async def test_get_match_prediction_handler():
    """测试获取比赛预测处理器"""
    from src.api.predictions_mod.prediction_handlers import get_match_prediction_handler
    from src.database.models import Match, MatchStatus, Predictions

    # Mock依赖
    mock_request = Mock()
    mock_session = AsyncMock()

    # Mock比赛数据
    mock_match = Mock(spec=Match)
    mock_match.id = 123
    mock_match.home_team_id = 1
    mock_match.away_team_id = 2
    mock_match.league_id = 10
    mock_match.match_time = datetime.now(timezone.utc)
    mock_match.match_status = MatchStatus.SCHEDULED
    mock_match.season = "2024-25"

    # Mock预测数据
    mock_prediction = Mock(spec=Predictions)
    mock_prediction.id = 456
    mock_prediction.model_version = "1.0"
    mock_prediction.model_name = "test_model"
    mock_prediction.home_win_probability = 0.5
    mock_prediction.draw_probability = 0.3
    mock_prediction.away_win_probability = 0.2
    mock_prediction.predicted_result = "home"
    mock_prediction.confidence_score = 0.5
    mock_prediction.created_at = datetime.now(timezone.utc)
    mock_prediction.is_correct = None
    mock_prediction.actual_result = None

    # Mock数据库查询
    with patch('src.api.predictions_mod.prediction_handlers.select') as mock_select:
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_result

        # Mock预测查询
        with patch('src.api.predictions_mod.prediction_handlers.Prediction') as mock_pred_class:
            mock_pred_result = AsyncMock()
            mock_pred_result.scalar_one_or_none.return_value = mock_prediction
            mock_session.execute.return_value = mock_pred_result

            # 执行处理器
            result = await get_match_prediction_handler(
                mock_request, 123, force_predict=False, session=mock_session
            )

            # 验证结果
            assert result is not None
            assert result["success"] is True
            assert "data" in result
            assert result["data"]["match_id"] == 123
            assert result["data"]["source"] == "cached"


@pytest.mark.asyncio
async def test_get_match_prediction_not_found():
    """测试比赛不存在的情况"""
    from src.api.predictions_mod.prediction_handlers import get_match_prediction_handler

    mock_request = Mock()
    mock_session = AsyncMock()

    # Mock数据库查询返回None
    with patch('src.api.predictions_mod.prediction_handlers.select') as mock_select:
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # 执行处理器并期望抛出HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_match_prediction_handler(
                mock_request, 999, session=mock_session
            )

        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_batch_predict_matches_handler():
    """测试批量预测处理器"""
    from src.api.predictions_mod.batch_handlers import batch_predict_matches_handler
    from src.database.models import Match

    mock_request = Mock()
    mock_session = AsyncMock()
    match_ids = [1, 2, 3]

    # Mock有效比赛查询
    with patch('src.api.predictions_mod.batch_handlers.select') as mock_select:
        # 创建mock比赛对象
        class MockMatchRow:
            def __init__(self, id):
                self.id = id

        mock_result = AsyncMock()
        mock_result.fetchall.return_value = [MockMatchRow(1), MockMatchRow(2), MockMatchRow(3)]
        mock_session.execute.return_value = mock_result

        # Mock预测服务
        with patch('src.api.predictions_mod.batch_handlers.prediction_service') as mock_service:
            mock_prediction = Mock()
            mock_prediction.to_dict.return_value = {"test": "prediction"}
            mock_service.batch_predict_matches.return_value = [mock_prediction, mock_prediction, mock_prediction]

            # 执行处理器
            result = await batch_predict_matches_handler(
                mock_request, match_ids, session=mock_session
            )

            # 验证结果
            assert result is not None
            assert result["success"] is True
            assert result["data"]["total_requested"] == 3
            assert result["data"]["valid_matches"] == 3
            assert result["data"]["successful_predictions"] == 3


@pytest.mark.asyncio
async def test_batch_predict_too_many_matches():
    """测试批量预测超过限制"""
    from src.api.predictions_mod.batch_handlers import batch_predict_matches_handler

    mock_request = Mock()
    mock_session = AsyncMock()

    # 创建超过限制的match_ids列表
    match_ids = list(range(1, 52))  # 51个比赛，超过50的限制

    # 执行处理器并期望抛出HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await batch_predict_matches_handler(
            mock_request, match_ids, session=mock_session
        )

    assert exc_info.value.status_code == 400
    assert "最多支持50场比赛" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_match_prediction_history_handler():
    """测试获取比赛历史预测处理器"""
    from src.api.predictions_mod.history_handlers import get_match_prediction_history_handler
    from src.database.models import Match, Predictions

    mock_session = AsyncMock()

    # Mock比赛数据
    mock_match = Mock(spec=Match)
    mock_match.id = 123

    # Mock预测数据
    mock_prediction = Mock(spec=Predictions)
    mock_prediction.id = 456
    mock_prediction.model_version = "1.0"
    mock_prediction.model_name = "test_model"
    mock_prediction.home_win_probability = 0.5
    mock_prediction.draw_probability = 0.3
    mock_prediction.away_win_probability = 0.2
    mock_prediction.predicted_result = "home"
    mock_prediction.confidence_score = 0.5
    mock_prediction.created_at = datetime.now(timezone.utc)
    mock_prediction.is_correct = True
    mock_prediction.actual_result = "home"
    mock_prediction.verified_at = datetime.now(timezone.utc)

    # Mock数据库查询
    with patch('src.api.predictions_mod.history_handlers.select') as mock_select:
        # Mock比赛查询
        mock_match_result = AsyncMock()
        mock_match_result.scalar_one_or_none.return_value = mock_match

        # Mock历史预测查询
        mock_history_result = AsyncMock()
        mock_history_result.scalars.return_value.all.return_value = [mock_prediction]

        # 配置mock_session.execute按顺序返回不同结果
        execute_results = [mock_match_result, mock_history_result]
        mock_session.execute.side_effect = execute_results

        # 执行处理器
        result = await get_match_prediction_history_handler(
            123, limit=10, session=mock_session
        )

        # 验证结果
        assert result is not None
        assert result["success"] is True
        assert result["data"]["match_id"] == 123
        assert result["data"]["total_predictions"] == 1
        assert len(result["data"]["predictions"]) == 1


@pytest.mark.asyncio
async def test_get_recent_predictions_handler():
    """测试获取最近预测处理器"""
    from src.api.predictions_mod.history_handlers import get_recent_predictions_handler

    mock_session = AsyncMock()

    # Mock预测结果
    class MockPredictionRow:
        def __init__(self):
            self.id = 456
            self.match_id = 123
            self.model_version = "1.0"
            self.model_name = "test_model"
            self.predicted_result = "home"
            self.confidence_score = 0.5
            self.created_at = datetime.now(timezone.utc)
            self.is_correct = True
            self.home_team_id = 1
            self.away_team_id = 2
            self.match_time = datetime.now(timezone.utc)
            self.match_status = "finished"

    # Mock数据库查询
    with patch('src.api.predictions_mod.history_handlers.select') as mock_select:
        mock_result = AsyncMock()
        mock_result.fetchall.return_value = [MockPredictionRow()]
        mock_session.execute.return_value = mock_result

        # 执行处理器
        result = await get_recent_predictions_handler(
            hours=24, limit=50, session=mock_session
        )

        # 验证结果
        assert result is not None
        assert result["success"] is True
        assert result["data"]["time_range_hours"] == 24
        assert result["data"]["total_predictions"] == 1
        assert len(result["data"]["predictions"]) == 1


def test_backward_compatibility():
    """测试向后兼容性"""
    # 测试原始导入方式仍然有效
    from src.api.predictions import router

    # 验证路由器可以导入
    assert router is not None
    assert hasattr(router, 'routes')
    assert len(router.routes) > 0


def test_router_endpoints():
    """测试路由器端点"""
    from src.api.predictions_mod import router

    # 验证所有端点都存在
    route_paths = [route.path for route in router.routes]

    expected_paths = [
        "/{match_id}",
        "/{match_id}/predict",
        "/batch",
        "/history/{match_id}",
        "/recent",
        "/{match_id}/verify",
    ]

    for path in expected_paths:
        assert any(path in route_path for route_path in route_paths)