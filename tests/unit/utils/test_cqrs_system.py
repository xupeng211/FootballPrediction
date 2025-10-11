"""
CQRS系统单元测试
CQRS System Unit Tests

测试CQRS模式的核心功能。
Tests core functionality of CQRS pattern.
"""

import pytest
import asyncio
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.cqrs.base import Command, Query, ValidationResult
from src.cqrs.commands import (
    CreatePredictionCommand,
    UpdatePredictionCommand,
    DeletePredictionCommand,
)
from src.cqrs.queries import (
    GetPredictionByIdQuery,
    GetPredictionsByUserQuery,
    GetUserStatsQuery,
)
from src.cqrs.dto import PredictionDTO, CommandResult
from src.cqrs.bus import CommandBus, QueryBus
from src.cqrs.handlers import (
    CreatePredictionHandler,
    UpdatePredictionHandler,
    DeletePredictionHandler,
    GetPredictionByIdHandler,
    GetPredictionsByUserHandler,
    GetUserStatsHandler,
)
from src.cqrs.application import (
    PredictionCQRSService,
    CQRSServiceFactory,
    initialize_cqrs,
)


class TestCommand(Command):
    """测试命令"""

    def __init__(self):
        super().__init__()


class TestQuery(Query):
    """测试查询"""

    def __init__(self):
        super().__init__()


class TestCommandCreation:
    """测试命令创建"""

    def test_command_creation(self):
        """测试命令创建"""
        command = TestCommand()
        assert command.message_id is not None
        assert command.timestamp is not None


class TestQueryCreation:
    """测试查询创建"""

    def test_query_creation(self):
        """测试查询创建"""
        query = TestQuery()
        assert query.message_id is not None
        assert query.timestamp is not None


class TestCreatePredictionCommand:
    """测试创建预测命令"""

    @pytest.mark.asyncio
    async def test_valid_command(self):
        """测试有效命令"""
        command = CreatePredictionCommand(
            match_id=1, user_id=1, predicted_home=2, predicted_away=1, confidence=0.85
        )

        # 模拟数据库验证
        with patch("src.cqrs.commands.get_session") as mock_session:
            mock_session.return_value.__aenter__.return_value.get.return_value = (
                MagicMock()
            )
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar.return_value = None

            result = await command.validate()
            assert result.is_valid

    @pytest.mark.asyncio
    async def test_invalid_confidence(self):
        """测试无效置信度"""
        command = CreatePredictionCommand(
            match_id=1,
            user_id=1,
            predicted_home=2,
            predicted_away=1,
            confidence=1.5,  # 无效
        )

        result = await command.validate()
        assert not result.is_valid
        assert "置信度必须在0到1之间" in result.errors[0]


class TestGetPredictionByIdQuery:
    """测试获取预测查询"""

    @pytest.mark.asyncio
    async def test_valid_query(self):
        """测试有效查询"""
        query = GetPredictionByIdQuery(prediction_id=1)
        result = await query.validate()
        assert result.is_valid

    @pytest.mark.asyncio
    async def test_invalid_id(self):
        """测试无效ID"""
        query = GetPredictionByIdQuery(prediction_id=-1)
        result = await query.validate()
        assert not result.is_valid


@pytest.mark.asyncio
class TestCommandBus:
    """测试命令总线"""

    async def test_register_and_dispatch(self):
        """测试注册和分发"""
        bus = CommandBus()
        handler = AsyncMock()
        handler.handle.return_value = CommandResult.success_result()

        # 注册处理器
        bus.register_handler(TestCommand, handler)

        # 分发命令
        command = TestCommand()
        result = await bus.dispatch(command)

        assert result.success
        handler.handle.assert_called_once_with(command)

    async def test_no_handler_error(self):
        """测试没有处理器的错误"""
        bus = CommandBus()
        command = TestCommand()

        with pytest.raises(ValueError, match="没有找到命令"):
            await bus.dispatch(command)


@pytest.mark.asyncio
class TestQueryBus:
    """测试查询总线"""

    async def test_register_and_dispatch(self):
        """测试注册和分发"""
        bus = QueryBus()
        handler = AsyncMock()
        handler.handle.return_value = {"test": "data"}

        # 注册处理器
        bus.register_handler(TestQuery, handler)

        # 分发查询
        query = TestQuery()
        result = await bus.dispatch(query)

        assert result == {"test": "data"}
        handler.handle.assert_called_once_with(query)


@pytest.mark.asyncio
class TestCreatePredictionHandler:
    """测试创建预测处理器"""

    async def test_handle_success(self):
        """测试成功处理"""
        handler = CreatePredictionHandler()
        command = CreatePredictionCommand(
            match_id=1, user_id=1, predicted_home=2, predicted_away=1, confidence=0.85
        )

        # 模拟数据库操作
        mock_prediction = MagicMock()
        mock_prediction.id = 1
        mock_prediction.match_id = 1
        mock_prediction.user_id = 1
        mock_prediction.predicted_home = 2
        mock_prediction.predicted_away = 1
        mock_prediction.confidence = 0.85
        mock_prediction.strategy_used = "test"
        mock_prediction.notes = None
        mock_prediction.created_at = datetime.utcnow()

        with patch("src.cqrs.handlers.get_session") as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar.return_value = None
            mock_session.return_value.__aenter__.return_value.add.return_value = None
            mock_session.return_value.__aenter__.return_value.commit.return_value = None
            mock_session.return_value.__aenter__.return_value.refresh.return_value = (
                None
            )

            result = await handler.handle(command)

            assert result.success
            assert result.message == "预测创建成功"
            assert result.data is not None

    async def test_handle_duplicate(self):
        """测试重复预测"""
        handler = CreatePredictionHandler()
        command = CreatePredictionCommand(
            match_id=1, user_id=1, predicted_home=2, predicted_away=1, confidence=0.85
        )

        # 模拟已存在预测
        with patch("src.cqrs.handlers.get_session") as mock_session:
            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar.return_value = 1

            result = await handler.handle(command)

            assert not result.success
            assert "预测已存在" in result.message


@pytest.mark.asyncio
class TestPredictionCQRSService:
    """测试预测CQRS服务"""

    async def test_create_prediction(self):
        """测试创建预测"""
        service = PredictionCQRSService()

        # 模拟命令总线
        with patch.object(service.command_bus, "dispatch") as mock_dispatch:
            mock_dispatch.return_value = CommandResult.success_result(
                data=PredictionDTO(
                    id=1,
                    match_id=1,
                    user_id=1,
                    predicted_home=2,
                    predicted_away=1,
                    confidence=0.85,
                )
            )

            result = await service.create_prediction(
                match_id=1,
                user_id=1,
                predicted_home=2,
                predicted_away=1,
                confidence=0.85,
            )

            assert result.success
            mock_dispatch.assert_called_once()

    async def test_get_prediction_by_id(self):
        """测试获取预测"""
        service = PredictionCQRSService()
        expected_dto = PredictionDTO(
            id=1,
            match_id=1,
            user_id=1,
            predicted_home=2,
            predicted_away=1,
            confidence=0.85,
        )

        # 模拟查询总线
        with patch.object(service.query_bus, "dispatch") as mock_dispatch:
            mock_dispatch.return_value = expected_dto

            result = await service.get_prediction_by_id(1)

            assert result == expected_dto
            mock_dispatch.assert_called_once()


class TestCommandResult:
    """测试命令结果"""

    def test_success_result(self):
        """测试成功结果"""
        result = CommandResult.success_result(data={"id": 1})
        assert result.success
        assert result.message == "操作成功"
        assert result.data == {"id": 1}
        assert result.errors is None

    def test_failure_result(self):
        """测试失败结果"""
        errors = ["错误1", "错误2"]
        result = CommandResult.failure_result(errors)
        assert not result.success
        assert result.message == "操作失败"
        assert result.errors == errors


@pytest.mark.asyncio
class TestCQRSInitialization:
    """测试CQRS初始化"""

    async def test_initialize_cqrs(self):
        """测试初始化CQRS系统"""
        await initialize_cqrs()

        from src.cqrs.bus import get_command_bus, get_query_bus

        command_bus = get_command_bus()
        query_bus = get_query_bus()

        # 验证命令处理器已注册
        assert len(command_bus.get_registered_commands()) > 0
        assert "CreatePredictionCommand" in command_bus.get_registered_commands()

        # 验证查询处理器已注册
        assert len(query_bus.get_registered_queries()) > 0
        assert "GetPredictionByIdQuery" in query_bus.get_registered_queries()


class TestCQRSServiceFactory:
    """测试CQRS服务工厂"""

    def test_create_services(self):
        """测试创建服务"""
        prediction_service = CQRSServiceFactory.create_prediction_service()
        assert prediction_service is not None
        assert isinstance(prediction_service, PredictionCQRSService)

        # 测试其他服务创建
        match_service = CQRSServiceFactory.create_match_service()
        user_service = CQRSServiceFactory.create_user_service()
        analytics_service = CQRSServiceFactory.create_analytics_service()

        assert match_service is not None
        assert user_service is not None
        assert analytics_service is not None


@pytest.mark.asyncio
class TestCQRSIntegration:
    """测试CQRS集成"""

    async def test_full_prediction_workflow(self):
        """测试完整的预测工作流"""
        # 初始化系统
        await initialize_cqrs()

        # 创建服务
        service = CQRSServiceFactory.create_prediction_service()

        # 模拟数据库
        with patch("src.cqrs.handlers.get_session") as mock_session:
            # 创建预测
            mock_prediction = MagicMock()
            mock_prediction.id = 1
            mock_prediction.match_id = 1
            mock_prediction.user_id = 1
            mock_prediction.predicted_home = 2
            mock_prediction.predicted_away = 1
            mock_prediction.confidence = 0.85
            mock_prediction.strategy_used = "test"
            mock_prediction.notes = None
            mock_prediction.created_at = datetime.utcnow()

            mock_session.return_value.__aenter__.return_value.execute.return_value.scalar.return_value = None
            mock_session.return_value.__aenter__.return_value.add.return_value = None
            mock_session.return_value.__aenter__.return_value.commit.return_value = None
            mock_session.return_value.__aenter__.return_value.refresh.return_value = (
                mock_prediction
            )

            # 执行创建
            create_result = await service.create_prediction(
                match_id=1,
                user_id=1,
                predicted_home=2,
                predicted_away=1,
                confidence=0.85,
            )
            assert create_result.success

            # 模拟查询
            mock_session.return_value.__aenter__.return_value.get.return_value = (
                mock_prediction
            )

            # 执行查询
            prediction = await service.get_prediction_by_id(1)
            assert prediction is not None
            assert prediction.predicted_home == 2
