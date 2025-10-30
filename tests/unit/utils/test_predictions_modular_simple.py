from unittest.mock import AsyncMock, Mock

"""
预测API模块化简化测试
"""

import pytest


def test_module_imports():
    """测试模块导入"""
    # 测试导入新模块
    from src.api.predictions_mod import (
        get_rate_limiter,
        is_rate_limit_available,
        router,
    )

    assert router is not None
    assert get_rate_limiter is not None
    assert is_rate_limit_available is not None


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
        get_prediction_service,
    )

    # 测试格式化函数存在
    assert _format_cached_prediction is not None
    assert _format_realtime_prediction is not None
    assert get_prediction_service is not None


def test_batch_handlers_import():
    """测试批量处理器导入"""
    from src.api.predictions_mod.batch_handlers import batch_predict_matches_handler
    from src.api.predictions_mod.batch_handlers import (
        get_prediction_service as get_batch_prediction_service,
    )

    assert batch_predict_matches_handler is not None
    assert get_batch_prediction_service is not None


def test_history_handlers_import():
    """测试历史处理器导入"""
    from src.api.predictions_mod.history_handlers import (
        get_match_prediction_history_handler,
        get_recent_predictions_handler,
    )

    assert get_match_prediction_history_handler is not None
    assert get_recent_predictions_handler is not None


def test_schemas_import():
    """测试模式导入"""
    from src.api.predictions_mod.schemas import (
        BatchPredictionRequest,
        MatchInfo,
        PredictionData,
        PredictionResponse,
        VerificationResponse,
    )

    assert MatchInfo is not None
    assert PredictionData is not None
    assert PredictionResponse is not None
    assert BatchPredictionRequest is not None
    assert VerificationResponse is not None


def test_backward_compatibility():
    """测试向后兼容性"""
    # 测试原始导入方式仍然有效
    from src.api.predictions import router

    # 验证路由器可以导入
    assert router is not None
    assert hasattr(router, "routes")
    assert len(router.routes) > 0


def test_router_endpoints():
    """测试路由器端点"""
    from src.api.predictions_mod import router

    # 验证路由器有路由
    assert hasattr(router, "routes")
    assert len(router.routes) > 0

    # 验证路由器有正确的prefix
    assert router.prefix == "/predictions"

    # 验证路由器有正确的tags
    assert "predictions" in router.tags


@pytest.mark.asyncio
async def test_batch_predict_too_many_matches():
    """测试批量预测超过限制"""
    from fastapi import HTTPException

    from src.api.predictions_mod.batch_handlers import batch_predict_matches_handler

    mock_request = Mock()
    mock_session = AsyncMock()

    # 创建超过限制的match_ids列表
    match_ids = list(range(1, 52))  # 51个比赛,超过50的限制

    # 执行处理器并期望抛出HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await batch_predict_matches_handler(mock_request, match_ids, session=mock_session)

    assert exc_info.value.status_code == 400
    assert "最多支持50场比赛" in exc_info.value.detail


def test_prediction_response_schema():
    """测试预测响应模式"""
    from src.api.predictions_mod.schemas import (
        MatchInfo,
        PredictionData,
        PredictionResponse,
    )

    # 创建测试数据
    match_info = MatchInfo(
        match_id=123,
        home_team_id=1,
        away_team_id=2,
        league_id=10,
        match_time="2024-01-01T15:00:00",
        match_status="scheduled",
        season="2024-25",
    )

    prediction_data = PredictionData(
        id=456,
        model_version="1.0",
        model_name="test_model",
        home_win_probability=0.5,
        draw_probability=0.3,
        away_win_probability=0.2,
        predicted_result="home",
        confidence_score=0.5,
        created_at="2024-01-01T10:00:00",
    )

    # 创建预测响应
    response = PredictionResponse(
        match_id=123,
        match_info=match_info,
        _prediction=prediction_data,
        source="cached",
    )

    # 验证数据
    assert response.match_id == 123
    assert response.source == "cached"
    assert response.match_info.home_team_id == 1
    assert response.prediction.predicted_result == "home"


def test_batch_prediction_request_schema():
    """测试批量预测请求模式"""
    from src.api.predictions_mod.schemas import BatchPredictionRequest

    # 创建批量预测请求
    request = BatchPredictionRequest(match_ids=[1, 2, 3])

    # 验证数据
    assert len(request.match_ids) == 3
    assert request.match_ids[0] == 1

    # 测试超过限制的情况
    with pytest.raises(ValueError):
        BatchPredictionRequest(match_ids=list(range(1, 52)))  # 51个比赛
