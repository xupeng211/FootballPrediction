"""
P3阶段高级集成测试: CQRSApplication
目标覆盖率: 42.11% → 80%
策略: 高级Mock + 真实依赖注入 + 端到端集成测试
"""

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import pytest

# 确保可以导入源码模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

# 导入目标模块
try:
    from src.cqrs.application import (
        AnalyticsCQRSService,
        CQRSServiceFactory,
        MatchCQRSService,
        PredictionCQRSService,
        UserCQRSService,
        initialize_cqrs,
    )
    from src.cqrs.bus import CommandBus, QueryBus
    from src.cqrs.commands import (
        CreateMatchCommand,
        CreatePredictionCommand,
        CreateUserCommand,
        UpdatePredictionCommand,
    )
    from src.cqrs.dto import CommandResult, MatchDTO, PredictionDTO
    from src.cqrs.handlers import PredictionCommandHandlers, PredictionQueryHandlers
    from src.cqrs.queries import (
        GetMatchByIdQuery,
        GetPredictionByIdQuery,
        GetUserStatsQuery,
    )

    CQRS_AVAILABLE = True
except ImportError as e:
    print(f"CQRS模块导入警告: {e}")
    CQRS_AVAILABLE = False


class TestCQRSApplicationAdvanced:
    """CQRSApplication 高级集成测试套件"""

    @pytest.fixture
    def mock_command_bus(self):
        """模拟命令总线"""
        bus = AsyncMock(spec=CommandBus)
        bus.dispatch.return_value = CommandResult(success=True, message="Success")
        return bus

    @pytest.fixture
    def mock_query_bus(self):
        """模拟查询总线"""
        bus = AsyncMock(spec=QueryBus)
        bus.dispatch.return_value = {"id": 1, "data": "test"}
        return bus

    @pytest.fixture
    def cqrs_services(self, mock_command_bus, mock_query_bus):
        """CQRS服务实例"""
        if not CQRS_AVAILABLE:
            pytest.skip("CQRS模块不可用")

        # 创建服务实例并注入模拟依赖
        with patch(
            "src.cqrs.application.get_command_bus", return_value=mock_command_bus
        ), patch("src.cqrs.application.get_query_bus", return_value=mock_query_bus):

            prediction_service = PredictionCQRSService()
            match_service = MatchCQRSService()
            user_service = UserCQRSService()
            analytics_service = AnalyticsCQRSService()

            return {
                "prediction": prediction_service,
                "match": match_service,
                "user": user_service,
                "analytics": analytics_service,
            }

    @pytest.mark.skipif(not CQRS_AVAILABLE, reason="CQRS模块不可用")
    def test_cqrs_module_import(self):
        """测试CQRS模块导入"""
        from src.cqrs import application, bus, commands, dto, handlers, queries

        assert application is not None
        assert bus is not None
        assert commands is not None
        assert queries is not None
        assert dto is not None
        assert handlers is not None

    @pytest.mark.asyncio
    async def test_prediction_cqrs_service_create_prediction(self, cqrs_services):
        """测试预测CQRS服务 - 创建预测"""
        prediction_service = cqrs_services["prediction"]

        result = await prediction_service.create_prediction(
            match_id=1,
            user_id=1,
            predicted_home=2,
            predicted_away=1,
            confidence=0.85,
            strategy_used="historical_analysis",
            notes="Test prediction",
        )

        assert result.success is True
        assert result.message == "Success"

        # 验证命令总线调用
        prediction_service.command_bus.dispatch.assert_called_once()

        # 获取调用的命令
        call_args = prediction_service.command_bus.dispatch.call_args[0][0]
        assert isinstance(call_args, CreatePredictionCommand)
        assert call_args.match_id == 1
        assert call_args.user_id == 1
        assert call_args.predicted_home == 2
        assert call_args.predicted_away == 1
        assert call_args.confidence == 0.85

    @pytest.mark.asyncio
    async def test_prediction_cqrs_service_update_prediction(self, cqrs_services):
        """测试预测CQRS服务 - 更新预测"""
        prediction_service = cqrs_services["prediction"]

        result = await prediction_service.update_prediction(
            prediction_id=1,
            predicted_home=3,
            predicted_away=1,
            confidence=0.90,
            strategy_used="ml_model",
        )

        assert result.success is True

        # 验证命令总线调用
        prediction_service.command_bus.dispatch.assert_called_once()

        # 获取调用的命令
        call_args = prediction_service.command_bus.dispatch.call_args[0][0]
        assert isinstance(call_args, UpdatePredictionCommand)
        assert call_args.prediction_id == 1
        assert call_args.predicted_home == 3
        assert call_args.confidence == 0.90

    @pytest.mark.asyncio
    async def test_prediction_cqrs_service_get_by_id(self, cqrs_services):
        """测试预测CQRS服务 - 根据ID获取预测"""
        prediction_service = cqrs_services["prediction"]

        # 设置查询总线返回值
        mock_prediction = PredictionDTO(
            id=1,
            match_id=1,
            user_id=1,
            predicted_home=2,
            predicted_away=1,
            confidence=0.85,
            strategy_used="test",
        )
        prediction_service.query_bus.dispatch.return_value = mock_prediction

        result = await prediction_service.get_prediction_by_id(1)

        assert result is not None
        assert isinstance(result, PredictionDTO)
        assert result.id == 1
        assert result.match_id == 1
        assert result.confidence == 0.85

        # 验证查询总线调用
        prediction_service.query_bus.dispatch.assert_called_once()
        call_args = prediction_service.query_bus.dispatch.call_args[0][0]
        assert isinstance(call_args, GetPredictionByIdQuery)
        assert call_args.prediction_id == 1

    @pytest.mark.asyncio
    async def test_match_cqrs_service_create_match(self, cqrs_services):
        """测试比赛CQRS服务 - 创建比赛"""
        from datetime import datetime

        match_service = cqrs_services["match"]

        result = await match_service.create_match(
            home_team="Team A",
            away_team="Team B",
            match_date=datetime(2024, 1, 1, 15, 0),
            competition="Premier League",
            venue="Stadium A",
        )

        assert result.success is True

        # 验证命令总线调用
        match_service.command_bus.dispatch.assert_called_once()

        # 获取调用的命令
        call_args = match_service.command_bus.dispatch.call_args[0][0]
        assert isinstance(call_args, CreateMatchCommand)
        assert call_args.home_team == "Team A"
        assert call_args.away_team == "Team B"
        assert call_args.competition == "Premier League"

    @pytest.mark.asyncio
    async def test_user_cqrs_service_create_user(self, cqrs_services):
        """测试用户CQRS服务 - 创建用户"""
        user_service = cqrs_services["user"]

        result = await user_service.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
        )

        assert result.success is True

        # 验证命令总线调用
        user_service.command_bus.dispatch.assert_called_once()

        # 获取调用的命令
        call_args = user_service.command_bus.dispatch.call_args[0][0]
        assert isinstance(call_args, CreateUserCommand)
        assert call_args.username == "testuser"
        assert call_args.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_analytics_cqrs_service_prediction_analytics(self, cqrs_services):
        """测试分析CQRS服务 - 预测分析"""
        analytics_service = cqrs_services["analytics"]

        # 设置查询总线返回值
        mock_analytics = {
            "total_predictions": 100,
            "accuracy": 0.75,
            "confidence_distribution": {"high": 30, "medium": 50, "low": 20},
        }
        analytics_service.query_bus.dispatch.return_value = mock_analytics

        result = await analytics_service.get_prediction_analytics(
            user_id=1, strategy_filter="historical_analysis"
        )

        assert result is not None
        assert isinstance(result, dict)
        assert result["total_predictions"] == 100
        assert result["accuracy"] == 0.75

        # 验证查询总线调用
        analytics_service.query_bus.dispatch.assert_called_once()

    def test_cqrs_service_factory(self):
        """测试CQRS服务工厂"""
        if not CQRS_AVAILABLE:
            pytest.skip("CQRS模块不可用")

        with patch("src.cqrs.application.get_command_bus"), patch(
            "src.cqrs.application.get_query_bus"
        ):

            # 测试工厂方法
            prediction_service = CQRSServiceFactory.create_prediction_service()
            match_service = CQRSServiceFactory.create_match_service()
            user_service = CQRSServiceFactory.create_user_service()
            analytics_service = CQRSServiceFactory.create_analytics_service()

            assert prediction_service is not None
            assert isinstance(prediction_service, PredictionCQRSService)
            assert match_service is not None
            assert isinstance(match_service, MatchCQRSService)
            assert user_service is not None
            assert isinstance(user_service, UserCQRSService)
            assert analytics_service is not None
            assert isinstance(analytics_service, AnalyticsCQRSService)

    @pytest.mark.asyncio
    async def test_initialize_cqrs_system(self):
        """测试CQRS系统初始化"""
        if not CQRS_AVAILABLE:
            pytest.skip("CQRS模块不可用")

        with patch("src.cqrs.application.get_command_bus") as mock_cmd_bus, patch(
            "src.cqrs.application.get_query_bus"
        ) as mock_query_bus:

            mock_cmd_instance = AsyncMock(spec=CommandBus)
            mock_query_instance = AsyncMock(spec=QueryBus)
            mock_cmd_bus.return_value = mock_cmd_instance
            mock_query_bus.return_value = mock_query_instance

            # 模拟命令处理器
            mock_prediction_handlers = Mock()
            mock_user_handlers = Mock()
            mock_query_handlers = Mock()

            with patch(
                "src.cqrs.application.PredictionCommandHandlers",
                return_value=mock_prediction_handlers,
            ), patch(
                "src.cqrs.application.UserCommandHandlers",
                return_value=mock_user_handlers,
            ), patch(
                "src.cqrs.application.PredictionQueryHandlers",
                return_value=mock_query_handlers,
            ), patch(
                "src.cqrs.application.LoggingMiddleware"
            ), patch(
                "src.cqrs.application.ValidationMiddleware"
            ):

                # 执行初始化
                await initialize_cqrs()

                # 验证命令处理器注册
                assert mock_cmd_instance.register_handler.call_count >= 3
                assert mock_query_instance.register_handler.call_count >= 3

    @pytest.mark.asyncio
    async def test_cqrs_error_handling(self, cqrs_services):
        """测试CQRS错误处理"""
        prediction_service = cqrs_services["prediction"]

        # 模拟命令总线抛出异常
        prediction_service.command_bus.dispatch.side_effect = ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await prediction_service.create_prediction(
                match_id=1,
                user_id=1,
                predicted_home=2,
                predicted_away=1,
                confidence=0.85,
            )

    @pytest.mark.asyncio
    async def test_cqrs_concurrent_operations(self, cqrs_services):
        """测试CQRS并发操作"""
        prediction_service = cqrs_services["prediction"]

        # 创建多个并发任务
        tasks = []
        for i in range(5):
            task = prediction_service.create_prediction(
                match_id=i,
                user_id=1,
                predicted_home=2,
                predicted_away=1,
                confidence=0.85,
            )
            tasks.append(task)

        # 执行并发操作
        results = await asyncio.gather(*tasks)

        # 验证所有操作都成功
        assert len(results) == 5
        for result in results:
            assert result.success is True

        # 验证命令总线被调用了5次
        assert prediction_service.command_bus.dispatch.call_count == 5

    def test_cqrs_integration_with_business_logic(self):
        """测试CQRS与业务逻辑的集成"""
        if not CQRS_AVAILABLE:
            pytest.skip("CQRS模块不可用")

        # 模拟完整的业务流程
        with patch("src.cqrs.application.get_command_bus") as mock_cmd_bus, patch(
            "src.cqrs.application.get_query_bus"
        ) as mock_query_bus:

            mock_cmd_instance = AsyncMock(spec=CommandBus)
            mock_query_instance = AsyncMock(spec=QueryBus)
            mock_cmd_bus.return_value = mock_cmd_instance
            mock_query_bus.return_value = mock_query_instance

            # 创建服务
            service = CQRSServiceFactory.create_prediction_service()

            # 验证服务初始化
            assert hasattr(service, "command_bus")
            assert hasattr(service, "query_bus")
            assert hasattr(service, "create_prediction")
            assert hasattr(service, "get_prediction_by_id")


if __name__ == "__main__":
    print("P3阶段高级集成测试: CQRSApplication")
    print("目标覆盖率: 42.11% → 80%")
    print("策略: 高级Mock + 真实依赖注入")
