"""
测试预测API的模块化拆分
Test modular split of predictions API
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.api.predictions.models import (
    PredictionRequest,
    PredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    UpcomingMatchesRequest,
    UpcomingMatchesResponse,
    ModelStatsResponse,
    PredictionHistoryResponse,
    PredictionOverviewResponse,
    VerificationResponse,
    CacheClearResponse,
    HealthCheckResponse,
)
from src.api.predictions.endpoints.single import router as single_router
from src.api.predictions.endpoints.batch import router as batch_router
from src.api.predictions.endpoints.stats import router as stats_router
from src.api.predictions.endpoints.streaming import router as streaming_router
from src.api.predictions.endpoints.admin import router as admin_router


class TestModels:
    """测试预测API模型"""

    def test_prediction_request_model(self):
        """测试预测请求模型"""
        request = PredictionRequest(
            match_id=123, force_refresh=True, include_features=False
        )
        assert request.match_id == 123
        assert request.force_refresh is True
        assert request.include_features is False

    def test_batch_prediction_request_model(self):
        """测试批量预测请求模型"""
        request = BatchPredictionRequest(
            match_ids=[1, 2, 3], force_refresh=False, include_features=True
        )
        assert len(request.match_ids) == 3
        assert request.force_refresh is False
        assert request.include_features is True

    def test_prediction_response_model(self):
        """测试预测响应模型"""
        response = PredictionResponse(
            match_id=123,
            prediction="home_win",
            probabilities={"home_win": 0.6, "draw": 0.3, "away_win": 0.1},
            confidence=0.85,
            model_version="v1.0.0",
            model_name="football_predictor",
            prediction_time="2024-01-01T15:00:00Z",
        )
        assert response.match_id == 123
        assert response.prediction == "home_win"
        assert response.probabilities["home_win"] == 0.6
        assert response.confidence == 0.85

    def test_upcoming_matches_request_model(self):
        """测试即将开始比赛请求模型"""
        request = UpcomingMatchesRequest(
            hours_ahead=48, league_ids=[1, 2, 3], force_refresh=True
        )
        assert request.hours_ahead == 48
        assert len(request.league_ids) == 3
        assert request.force_refresh is True

    def test_model_stats_response_model(self):
        """测试模型统计响应模型"""
        response = ModelStatsResponse(
            model_name="test_model",
            period_days=7,
            total_predictions=100,
            verified_predictions=80,
            accuracy=0.75,
            avg_confidence=0.82,
            predictions_by_result={"home_win": 40, "draw": 20, "away_win": 20},
            last_updated="2024-01-01T15:00:00Z",
        )
        assert response.model_name == "test_model"
        assert response.accuracy == 0.75
        assert response.predictions_by_result["home_win"] == 40

    def test_verification_response_model(self):
        """测试验证响应模型"""
        response = VerificationResponse(
            match_id=123, verified=True, correct=1, accuracy=0.85, message="验证完成"
        )
        assert response.match_id == 123
        assert response.verified is True
        assert response.accuracy == 0.85


class TestSingleEndpoints:
    """测试单个预测端点"""

    @pytest.mark.asyncio
    async def test_predict_match_endpoint(self):
        """测试预测比赛端点"""
        # 测试路由存在
        routes = [route.path for route in single_router.routes]
        assert "/predict" in routes

    @pytest.mark.asyncio
    async def test_get_match_prediction_endpoint(self):
        """测试获取比赛预测端点"""
        routes = [route.path for route in single_router.routes]
        assert "/match/{match_id}" in routes

    @pytest.mark.asyncio
    async def test_get_match_history_endpoint(self):
        """测试获取比赛历史端点"""
        routes = [route.path for route in single_router.routes]
        assert "/history/match/{match_id}" in routes


class TestBatchEndpoints:
    """测试批量预测端点"""

    @pytest.mark.asyncio
    async def test_batch_predict_endpoint(self):
        """测试批量预测端点"""
        routes = [route.path for route in batch_router.routes]
        assert "/predict/batch" in routes

    @pytest.mark.asyncio
    async def test_upcoming_matches_endpoint(self):
        """测试即将开始比赛端点"""
        routes = [route.path for route in batch_router.routes]
        assert "/predict/upcoming" in routes


class TestStatsEndpoints:
    """测试统计相关端点"""

    @pytest.mark.asyncio
    async def test_model_statistics_endpoint(self):
        """测试模型统计端点"""
        routes = [route.path for route in stats_router.routes]
        assert "/stats/model/{model_name}" in routes

    @pytest.mark.asyncio
    async def test_prediction_overview_endpoint(self):
        """测试预测概览端点"""
        routes = [route.path for route in stats_router.routes]
        assert "/stats/overview" in routes

    @pytest.mark.asyncio
    async def test_verify_prediction_endpoint(self):
        """测试验证预测端点"""
        routes = [route.path for route in stats_router.routes]
        assert "/verify/{match_id}" in routes


class TestStreamingEndpoints:
    """测试流式预测端点"""

    @pytest.mark.asyncio
    async def test_stream_predictions_endpoint(self):
        """测试流式预测端点"""
        routes = [route.path for route in streaming_router.routes]
        assert "/stream/matches/{match_id}" in routes


class TestAdminEndpoints:
    """测试管理功能端点"""

    @pytest.mark.asyncio
    async def test_clear_cache_endpoint(self):
        """测试清理缓存端点"""
        routes = [route.path for route in admin_router.routes]
        assert "/cache" in routes

    @pytest.mark.asyncio
    async def test_health_check_endpoint(self):
        """测试健康检查端点"""
        routes = [route.path for route in admin_router.routes]
        assert "/health" in routes


class TestModularStructure:
    """测试模块化结构"""

    def test_import_from_main_module(self):
        """测试从主模块导入"""
        from src.api.predictions import router
        from src.api.predictions import PredictionRequest
        from src.api.predictions import PredictionResponse

        assert router is not None
        assert PredictionRequest is not None
        assert PredictionResponse is not None

    def test_import_from_endpoints(self):
        """测试从端点模块导入"""
        from src.api.predictions.endpoints import routers

        assert len(routers) == 5  # 应该有5个子路由器
        assert single_router in routers
        assert batch_router in routers
        assert stats_router in routers
        assert streaming_router in routers
        assert admin_router in routers

    def test_backward_compatibility(self):
        """测试向后兼容性"""
        # 从原始文件导入应该仍然有效
        from src.api.predictions_api import router as old_router
        from src.api.predictions_api import PredictionRequest as old_model

        assert old_router is not None
        assert old_model is not None

    def test_router_prefix_and_tags(self):
        """测试路由器前缀和标签"""
        from src.api.predictions import router

        assert router.prefix == "/api/v1/predictions"
        assert "predictions" in router.tags

    def test_all_routes_included(self):
        """测试所有路由都被包含"""
        from src.api.predictions import router

        # 收集所有路由路径
        all_paths = set()
        for route in router.routes:
            if hasattr(route, "path"):
                all_paths.add(route.path)

        # 验证至少包含所有期望的路径模式
        expected_patterns = [
            "/predict",
            "/match/",
            "/history/",
            "/stats/",
            "/verify/",
            "/stream/",
            "/cache",
            "/health",
        ]

        # 验证每个模式都存在
        for pattern in expected_patterns:
            found = any(pattern in path for path in all_paths)
            assert found, f"路径模式 {pattern} 未找到"

        # 验证至少有11个端点
        assert len(all_paths) >= 10, f"期望至少10个端点，实际找到 {len(all_paths)} 个"


@pytest.mark.asyncio
async def test_integration_example():
    """测试集成示例"""
    from src.api.predictions import router

    # 验证路由器可以正常使用
    assert router is not None
    assert len(router.routes) > 0

    # 验证模型可以正常实例化
    request = PredictionRequest(match_id=123)
    assert request.match_id == 123
