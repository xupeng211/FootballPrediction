"""CQRS处理器架构测试
CQRS Handlers Architecture Tests.

全面测试src/cqrs/handlers.py模块中的所有命令和查询处理器.
Comprehensive testing of all command and query handlers in src/cqrs/handlers.py module.

Architecture Validation Strategy:
- 验证所有Handler的command_type/query_type属性
- 测试异步执行和异常处理
- 模拟数据库操作和依赖注入
- 验证Handler集合类的初始化和配置
- 测试边界条件和错误处理
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import time

import pytest

from src.cqrs.commands import (
    CreateMatchCommand,
    CreatePredictionCommand,
    CreateUserCommand,
    DeletePredictionCommand,
    UpdateMatchCommand,
    UpdatePredictionCommand,
)
from src.cqrs.dto import (
    MatchDTO,
    PredictionDTO,
    PredictionStatsDTO,
    UserDTO,
)
from src.cqrs.handlers import (
    CreateMatchHandler,
    CreatePredictionHandler,
    CreateUserHandler,
    DeletePredictionHandler,
    GetMatchByIdHandler,
    GetMatchPredictionsHandler,
    GetPredictionByIdHandler,
    GetPredictionsByUserHandler,
    GetUpcomingMatchesHandler,
    GetUserByIdHandler,
    GetUserStatsHandler,
    UpdateMatchHandler,
    UpdatePredictionHandler,
    MatchCommandHandlers,
    MatchQueryHandlers,
    PredictionCommandHandlers,
    PredictionQueryHandlers,
    UserCommandHandlers,
    UserQueryHandlers,
)
from src.cqrs.queries import (
    GetMatchByIdQuery,
    GetMatchPredictionsQuery,
    GetPredictionByIdQuery,
    GetPredictionsByUserQuery,
    GetUpcomingMatchesQuery,
    GetUserByIdQuery,
    GetUserStatsQuery,
)


class TestCreatePredictionHandler:
    """创建预测处理器测试."""

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.scalar = AsyncMock(return_value=None)  # 不存在重复预测
        session.get = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def handler(self):
        """创建预测处理器实例."""
        return CreatePredictionHandler()

    @pytest.fixture
    def sample_command(self):
        """示例创建预测命令."""
        return CreatePredictionCommand(
            match_id=1,
            user_id=1,
            predicted_home=2,
            predicted_away=1,
            confidence=0.85,
            strategy_used="lstm",
            notes="Test prediction",
        )

    @pytest.mark.asyncio
    async def test_command_type_property(self, handler):
        """测试命令类型属性."""
        assert handler.command_type == CreatePredictionCommand

    @pytest.mark.asyncio
    async def test_handle_success(self, handler, sample_command, mock_session):
        """测试成功处理创建预测命令."""
        # 模拟预测对象
        mock_prediction = MagicMock()
        mock_prediction.id = 1
        mock_prediction.match_id = sample_command.match_id
        mock_prediction.user_id = sample_command.user_id
        mock_prediction.predicted_home = sample_command.predicted_home
        mock_prediction.predicted_away = sample_command.predicted_away
        mock_prediction.confidence = Decimal(str(sample_command.confidence))
        mock_prediction.strategy_used = sample_command.strategy_used
        mock_prediction.notes = sample_command.notes
        mock_prediction.created_at = datetime.utcnow()

        def set_prediction_id(obj):
            obj.id = 1
            obj.match_id = sample_command.match_id
            obj.user_id = sample_command.user_id
            obj.predicted_home = sample_command.predicted_home
            obj.predicted_away = sample_command.predicted_away
            obj.confidence = Decimal(str(sample_command.confidence))
            obj.strategy_used = sample_command.strategy_used
            obj.notes = sample_command.notes
            obj.created_at = datetime.utcnow()

        mock_session.refresh.side_effect = set_prediction_id

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_command)

            # 验证结果
            assert result.success is True
            assert result.message == "预测创建成功"
            assert isinstance(result.data, PredictionDTO)
            assert result.data.match_id == sample_command.match_id
            assert result.data.user_id == sample_command.user_id

    @pytest.mark.asyncio
    async def test_handle_duplicate_prediction(
        self, handler, sample_command, mock_session
    ):
        """测试处理重复预测的情况."""
        # 模拟已存在预测
        mock_session.scalar.return_value = 1

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_command)

            # 验证失败结果
            assert result.success is False
            assert result.message == "预测已存在"
            assert "用户已经对该比赛进行了预测" in result.errors

    @pytest.mark.asyncio
    async def test_handle_database_error(self, handler, sample_command, mock_session):
        """测试数据库错误处理."""
        mock_session.execute.side_effect = Exception("Database error")

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_command)

            # 验证错误处理
            assert result.success is False
            assert result.message == "创建预测失败"
            assert "Database error" in result.errors[0]


class TestUpdatePredictionHandler:
    """更新预测处理器测试."""

    @pytest.fixture
    def handler(self):
        """创建更新预测处理器实例."""
        return UpdatePredictionHandler()

    @pytest.fixture
    def sample_command(self):
        """示例更新预测命令."""
        return UpdatePredictionCommand(
            prediction_id=1,
            predicted_home=3,
            predicted_away=1,
            confidence=0.90,
            strategy_used="updated_strategy",
            notes="Updated prediction",
        )

    @pytest.mark.asyncio
    async def test_command_type_property(self, handler):
        """测试命令类型属性."""
        assert handler.command_type == UpdatePredictionCommand

    @pytest.mark.asyncio
    async def test_handle_success(self, handler, sample_command):
        """测试成功更新预测."""
        # 模拟现有预测
        mock_prediction = MagicMock()
        mock_prediction.predicted_home = 1
        mock_prediction.predicted_away = 1
        mock_prediction.confidence = Decimal("0.75")
        mock_prediction.strategy_used = "old_strategy"
        mock_prediction.notes = "Old notes"
        mock_prediction.created_at = datetime.utcnow()

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_prediction
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_command)

            # 验证结果
            assert result.success is True
            assert result.message == "预测更新成功"
            assert isinstance(result.data, PredictionDTO)

    @pytest.mark.asyncio
    async def test_handle_prediction_not_found(self, handler, sample_command):
        """测试预测不存在的情况."""
        mock_session = AsyncMock()
        mock_session.get.return_value = None

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_command)

            # 验证失败结果
            assert result.success is False
            assert result.message == "预测未找到"
            assert "预测不存在" in result.errors


class TestDeletePredictionHandler:
    """删除预测处理器测试."""

    @pytest.fixture
    def handler(self):
        """创建删除预测处理器实例."""
        return DeletePredictionHandler()

    @pytest.fixture
    def sample_command(self):
        """示例删除预测命令."""
        return DeletePredictionCommand(prediction_id=1)

    @pytest.mark.asyncio
    async def test_command_type_property(self, handler):
        """测试命令类型属性."""
        assert handler.command_type == DeletePredictionCommand

    @pytest.mark.asyncio
    async def test_handle_success(self, handler, sample_command):
        """测试成功删除预测."""
        mock_prediction = MagicMock()
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_prediction
        mock_session.delete = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_command)

            # 验证结果
            assert result.success is True
            assert result.message == "预测删除成功"
            assert result.data["deleted_id"] == sample_command.prediction_id

    @pytest.mark.asyncio
    async def test_handle_prediction_not_found(self, handler, sample_command):
        """测试预测不存在的情况."""
        mock_session = AsyncMock()
        mock_session.get.return_value = None

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_command)

            # 验证失败结果
            assert result.success is False
            assert result.message == "预测未找到"


class TestCreateUserHandler:
    """创建用户处理器测试."""

    @pytest.fixture
    def handler(self):
        """创建用户处理器实例."""
        return CreateUserHandler()

    @pytest.fixture
    def sample_command(self):
        """示例创建用户命令."""
        return CreateUserCommand(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
        )

    @pytest.mark.asyncio
    async def test_command_type_property(self, handler):
        """测试命令类型属性."""
        assert handler.command_type == CreateUserCommand

    @pytest.mark.asyncio
    async def test_handle_success(self, handler, sample_command):
        """测试成功创建用户."""
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = sample_command.username
        mock_user.email = sample_command.email
        mock_user.is_active = True
        mock_user.created_at = datetime.utcnow()
        mock_user.last_login = datetime.utcnow()

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_command)

            # 验证结果
            assert result.success is True
            assert result.message == "用户创建成功"
            assert isinstance(result.data, UserDTO)
            assert result.data.username == sample_command.username
            assert result.data.email == sample_command.email


class TestGetPredictionByIdHandler:
    """根据ID获取预测处理器测试."""

    @pytest.fixture
    def handler(self):
        """创建查询处理器实例."""
        return GetPredictionByIdHandler()

    @pytest.fixture
    def sample_query(self):
        """示例查询."""
        return GetPredictionByIdQuery(prediction_id=1)

    @pytest.mark.asyncio
    async def test_query_type_property(self, handler):
        """测试查询类型属性."""
        assert handler.query_type == GetPredictionByIdQuery

    @pytest.mark.asyncio
    async def test_handle_success(self, handler, sample_query):
        """测试成功获取预测."""
        mock_prediction = MagicMock()
        mock_prediction.id = sample_query.prediction_id
        mock_prediction.match_id = 1
        mock_prediction.user_id = 1
        mock_prediction.predicted_home = 2
        mock_prediction.predicted_away = 1
        mock_prediction.confidence = Decimal("0.85")
        mock_prediction.strategy_used = "lstm"
        mock_prediction.points_earned = 10
        mock_prediction.accuracy_score = 0.95
        mock_prediction.notes = "Test prediction"
        mock_prediction.created_at = datetime.utcnow()
        mock_prediction.updated_at = datetime.utcnow()

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_prediction

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_query)

            # 验证结果
            assert result is not None
            assert isinstance(result, PredictionDTO)
            assert result.id == sample_query.prediction_id
            assert result.match_id == 1
            assert result.predicted_home == 2

    @pytest.mark.asyncio
    async def test_handle_not_found(self, handler, sample_query):
        """测试预测不存在的情况."""
        mock_session = AsyncMock()
        mock_session.get.return_value = None

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_query)

            # 验证结果为None
            assert result is None


class TestGetPredictionsByUserHandler:
    """获取用户预测列表处理器测试."""

    @pytest.fixture
    def handler(self):
        """创建查询处理器实例."""
        return GetPredictionsByUserHandler()

    @pytest.fixture
    def sample_query(self):
        """示例查询."""
        return GetPredictionsByUserQuery(
            user_id=1, start_date=datetime(2024, 1, 1), limit=10
        )

    @pytest.mark.asyncio
    async def test_query_type_property(self, handler):
        """测试查询类型属性."""
        assert handler.query_type == GetPredictionsByUserQuery

    @pytest.mark.asyncio
    async def test_handle_success(self, handler, sample_query):
        """测试成功获取用户预测列表."""
        # 模拟查询结果
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.match_id = 1
        mock_row.user_id = sample_query.user_id
        mock_row.predicted_home = 2
        mock_row.predicted_away = 1
        mock_row.confidence = Decimal("0.85")
        mock_row.strategy_used = "lstm"
        mock_row.points_earned = 10
        mock_row.accuracy_score = 0.95
        mock_row.notes = "Test prediction"
        mock_row.created_at = datetime.utcnow()
        mock_row.updated_at = datetime.utcnow()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        mock_session.execute.return_value = mock_result

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_query)

            # 验证结果
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], PredictionDTO)
            assert result[0].user_id == sample_query.user_id

    @pytest.mark.asyncio
    async def test_handle_empty_result(self, handler, sample_query):
        """测试空结果的情况."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_query)

            # 验证空结果
            assert isinstance(result, list)
            assert len(result) == 0


class TestGetUserStatsHandler:
    """获取用户统计处理器测试."""

    @pytest.fixture
    def handler(self):
        """创建查询处理器实例."""
        return GetUserStatsHandler()

    @pytest.fixture
    def sample_query(self):
        """示例查询."""
        return GetUserStatsQuery(user_id=1)

    @pytest.mark.asyncio
    async def test_query_type_property(self, handler):
        """测试查询类型属性."""
        assert handler.query_type == GetUserStatsQuery

    @pytest.mark.asyncio
    async def test_handle_success_with_predictions(self, handler, sample_query):
        """测试有预测记录的用户统计."""
        # 模拟基本统计结果
        mock_stats = MagicMock()
        mock_stats.total_predictions = 10
        mock_stats.successful_predictions = 7
        mock_stats.total_points = 85
        mock_stats.average_confidence = Decimal("0.82")

        # 模拟策略分布结果
        mock_strategy_row = MagicMock()
        mock_strategy_row.strategy_used = "lstm"
        mock_strategy_row.count = 6
        mock_strategy_row.avg_confidence = Decimal("0.85")
        mock_strategy_row.total_points = 60

        # 模拟最近表现结果
        mock_recent_row = MagicMock()
        mock_recent_row.match_date = datetime.utcnow()
        mock_recent_row.predicted_home = 2
        mock_recent_row.predicted_away = 1
        mock_recent_row.home_score = 2
        mock_recent_row.away_score = 1
        mock_recent_row.points_earned = 10
        mock_recent_row.accuracy_score = Decimal("1.0")

        mock_session = AsyncMock()

        # 设置不同的查询结果
        mock_session.execute.side_effect = [
            MagicMock(fetchone=MagicMock(return_value=mock_stats)),  # 基本统计
            MagicMock(fetchall=MagicMock(return_value=[mock_strategy_row])),  # 策略分布
            MagicMock(fetchall=MagicMock(return_value=[mock_recent_row])),  # 最近表现
        ]

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_query)

            # 验证结果
            assert result is not None
            assert isinstance(result, PredictionStatsDTO)
            assert result.user_id == sample_query.user_id
            assert result.total_predictions == 10
            assert result.successful_predictions == 7
            assert result.success_rate == 0.7
            assert result.total_points == 85
            assert "lstm" in result.strategy_breakdown
            assert len(result.recent_performance) == 1

    @pytest.mark.asyncio
    async def test_handle_no_predictions(self, handler, sample_query):
        """测试没有预测记录的用户统计."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None  # 没有统计数据
        mock_session.execute.return_value = mock_result

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_query)

            # 验证默认统计结果
            assert result is not None
            assert isinstance(result, PredictionStatsDTO)
            assert result.user_id == sample_query.user_id
            assert result.total_predictions == 0
            assert result.successful_predictions == 0
            assert result.success_rate == 0.0
            assert result.total_points == 0
            assert result.strategy_breakdown == {}
            assert result.recent_performance == []


class TestGetUpcomingMatchesHandler:
    """获取即将到来的比赛处理器测试."""

    @pytest.fixture
    def handler(self):
        """创建查询处理器实例."""
        return GetUpcomingMatchesHandler()

    @pytest.fixture
    def sample_query(self):
        """示例查询."""
        return GetUpcomingMatchesQuery(
            days_ahead=7, competition="Premier League", limit=5
        )

    @pytest.mark.asyncio
    async def test_query_type_property(self, handler):
        """测试查询类型属性."""
        assert handler.query_type == GetUpcomingMatchesQuery

    @pytest.mark.asyncio
    async def test_handle_success(self, handler, sample_query):
        """测试成功获取即将到来的比赛."""
        # 模拟比赛结果
        mock_match = MagicMock()
        mock_match.id = 1
        mock_match.home_team = "Arsenal"
        mock_match.away_team = "Chelsea"
        mock_match.home_score = None
        mock_match.away_score = None
        mock_match.match_date = datetime.utcnow()
        mock_match.status = "upcoming"
        mock_match.competition = "Premier League"
        mock_match.venue = "Emirates Stadium"
        mock_match.created_at = datetime.utcnow()
        mock_match.updated_at = datetime.utcnow()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_match]
        mock_session.execute.return_value = mock_result

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_query)

            # 验证结果
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], MatchDTO)
            assert result[0].competition == "Premier League"
            assert result[0].status == "upcoming"

    @pytest.mark.asyncio
    async def test_handle_empty_result(self, handler, sample_query):
        """测试没有即将到来的比赛."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_query)

            # 验证空结果
            assert isinstance(result, list)
            assert len(result) == 0


class TestCreateMatchHandler:
    """创建比赛处理器测试."""

    @pytest.fixture
    def handler(self):
        """创建比赛处理器实例."""
        return CreateMatchHandler()

    @pytest.fixture
    def sample_command(self):
        """示例创建比赛命令."""
        return CreateMatchCommand(
            home_team_id=1,
            away_team_id=2,
            match_date=datetime(2024, 12, 25, 15, 0),
            competition="Premier League",
            venue="Emirates Stadium",
        )

    @pytest.mark.asyncio
    async def test_handle_success(self, handler, sample_command):
        """测试成功创建比赛."""
        mock_match = MagicMock()
        mock_match.id = 1
        mock_match.home_team = "Arsenal"
        mock_match.away_team = "Chelsea"
        mock_match.home_score = None
        mock_match.away_score = None
        mock_match.match_date = sample_command.match_date
        mock_match.status = "upcoming"
        mock_match.competition = sample_command.competition
        mock_match.venue = sample_command.venue
        mock_match.created_at = datetime.utcnow()
        mock_match.updated_at = datetime.utcnow()

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_command)

            # 验证结果
            assert result.success is True
            assert result.message == "比赛创建成功"
            assert isinstance(result.data, MatchDTO)
            assert result.data.competition == sample_command.competition
            assert result.data.venue == sample_command.venue


class TestUpdateMatchHandler:
    """更新比赛处理器测试."""

    @pytest.fixture
    def handler(self):
        """创建比赛处理器实例."""
        return UpdateMatchHandler()

    @pytest.fixture
    def sample_command(self):
        """示例更新比赛命令."""
        return UpdateMatchCommand(
            match_id=1, home_score=2, away_score=1, status="completed"
        )

    @pytest.mark.asyncio
    async def test_handle_success(self, handler, sample_command):
        """测试成功更新比赛."""
        mock_match = MagicMock()
        mock_match.home_score = None
        mock_match.away_score = None
        mock_match.status = "upcoming"
        mock_match.match_date = datetime.utcnow()
        mock_match.competition = "Premier League"
        mock_match.venue = "Emirates Stadium"
        mock_match.created_at = datetime.utcnow()
        mock_match.updated_at = None

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_match
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_command)

            # 验证结果
            assert result.success is True
            assert result.message == "比赛更新成功"
            assert isinstance(result.data, MatchDTO)
            assert result.data.home_score == sample_command.home_score
            assert result.data.away_score == sample_command.away_score
            assert result.data.status == sample_command.status

    @pytest.mark.asyncio
    async def test_handle_match_not_found(self, handler, sample_command):
        """测试比赛不存在的情况."""
        mock_session = AsyncMock()
        mock_session.get.return_value = None

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_command)

            # 验证失败结果
            assert result.success is False
            assert result.message == "更新比赛失败"


class TestGetMatchByIdHandler:
    """获取比赛处理器测试."""

    @pytest.fixture
    def handler(self):
        """创建查询处理器实例."""
        return GetMatchByIdHandler()

    @pytest.fixture
    def sample_query(self):
        """示例查询."""
        return GetMatchByIdQuery(match_id=1)

    @pytest.mark.asyncio
    async def test_handle_success(self, handler, sample_query):
        """测试成功获取比赛."""
        mock_match = MagicMock()
        mock_match.id = sample_query.match_id
        mock_match.home_team = "Arsenal"
        mock_match.away_team = "Chelsea"
        mock_match.home_score = 2
        mock_match.away_score = 1
        mock_match.match_date = datetime.utcnow()
        mock_match.status = "completed"
        mock_match.competition = "Premier League"
        mock_match.venue = "Emirates Stadium"
        mock_match.created_at = datetime.utcnow()
        mock_match.updated_at = datetime.utcnow()

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_match

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_query)

            # 验证结果
            assert result is not None
            assert isinstance(result, MatchDTO)
            assert result.id == sample_query.match_id
            assert result.home_team == "Arsenal"
            assert result.away_team == "Chelsea"

    @pytest.mark.asyncio
    async def test_handle_not_found(self, handler, sample_query):
        """测试比赛不存在的情况."""
        mock_session = AsyncMock()
        mock_session.get.return_value = None

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_query)

            # 验证结果为None
            assert result is None


class TestGetUserByIdHandler:
    """获取用户处理器测试."""

    @pytest.fixture
    def handler(self):
        """创建查询处理器实例."""
        return GetUserByIdHandler()

    @pytest.fixture
    def sample_query(self):
        """示例查询."""
        return GetUserByIdQuery(user_id=1)

    @pytest.mark.asyncio
    async def test_handle_success(self, handler, sample_query):
        """测试成功获取用户."""
        mock_user = MagicMock()
        mock_user.id = sample_query.user_id
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.full_name = "Test User"
        mock_user.is_active = True
        mock_user.created_at = datetime.utcnow()
        mock_user.updated_at = datetime.utcnow()

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_user

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_query)

            # 验证结果
            assert result is not None
            assert isinstance(result, UserDTO)
            assert result.id == sample_query.user_id
            assert result.username == "testuser"
            assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_handle_not_found(self, handler, sample_query):
        """测试用户不存在的情况."""
        mock_session = AsyncMock()
        mock_session.get.return_value = None

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_query)

            # 验证结果为None
            assert result is None


class TestGetMatchPredictionsHandler:
    """获取比赛预测处理器测试."""

    @pytest.fixture
    def handler(self):
        """创建查询处理器实例."""
        return GetMatchPredictionsHandler()

    @pytest.fixture
    def sample_query(self):
        """示例查询."""
        return GetMatchPredictionsQuery(match_id=1, limit=10)

    @pytest.mark.asyncio
    async def test_handle_success(self, handler, sample_query):
        """测试成功获取比赛预测."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.match_id = sample_query.match_id
        mock_row.user_id = 1
        mock_row.predicted_home = 2
        mock_row.predicted_away = 1
        mock_row.confidence = Decimal("0.85")
        mock_row.strategy_used = "lstm"
        mock_row.points_earned = 10
        mock_row.accuracy_score = Decimal("1.0")
        mock_row.notes = "Test prediction"
        mock_row.created_at = datetime.utcnow()
        mock_row.updated_at = datetime.utcnow()

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        mock_session.execute.return_value = mock_result

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_query)

            # 验证结果
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], PredictionDTO)
            assert result[0].match_id == sample_query.match_id

    @pytest.mark.asyncio
    async def test_handle_empty_result(self, handler, sample_query):
        """测试没有预测记录的比赛."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(sample_query)

            # 验证空结果
            assert isinstance(result, list)
            assert len(result) == 0


class TestHandlerCollections:
    """Handler集合类测试."""

    def test_prediction_command_handlers_initialization(self):
        """测试预测命令处理器集合初始化."""
        handlers = PredictionCommandHandlers()

        assert hasattr(handlers, "create")
        assert hasattr(handlers, "update")
        assert hasattr(handlers, "delete")
        assert isinstance(handlers.create, CreatePredictionHandler)
        assert isinstance(handlers.update, UpdatePredictionHandler)
        assert isinstance(handlers.delete, DeletePredictionHandler)

    def test_prediction_query_handlers_initialization(self):
        """测试预测查询处理器集合初始化."""
        handlers = PredictionQueryHandlers()

        assert hasattr(handlers, "get_by_id")
        assert hasattr(handlers, "get_by_user")
        assert hasattr(handlers, "get_stats")
        assert hasattr(handlers, "get_upcoming_matches")
        assert isinstance(handlers.get_by_id, GetPredictionByIdHandler)
        assert isinstance(handlers.get_by_user, GetPredictionsByUserHandler)
        assert isinstance(handlers.get_stats, GetUserStatsHandler)
        assert isinstance(handlers.get_upcoming_matches, GetUpcomingMatchesHandler)

    def test_user_command_handlers_initialization(self):
        """测试用户命令处理器集合初始化."""
        handlers = UserCommandHandlers()

        assert hasattr(handlers, "create")
        assert isinstance(handlers.create, CreateUserHandler)

    def test_user_query_handlers_initialization(self):
        """测试用户查询处理器集合初始化."""
        handlers = UserQueryHandlers()

        assert hasattr(handlers, "get_by_id")
        assert hasattr(handlers, "get_stats")
        assert isinstance(handlers.get_by_id, GetUserByIdHandler)
        assert isinstance(handlers.get_stats, GetUserStatsHandler)

    def test_match_command_handlers_initialization(self):
        """测试比赛命令处理器集合初始化."""
        handlers = MatchCommandHandlers()

        assert hasattr(handlers, "create")
        assert hasattr(handlers, "update")
        assert isinstance(handlers.create, CreateMatchHandler)
        assert isinstance(handlers.update, UpdateMatchHandler)

    def test_match_query_handlers_initialization(self):
        """测试比赛查询处理器集合初始化."""
        handlers = MatchQueryHandlers()

        assert hasattr(handlers, "get_by_id")
        assert hasattr(handlers, "get_upcoming")
        assert hasattr(handlers, "get_predictions")
        assert isinstance(handlers.get_by_id, GetMatchByIdHandler)
        assert isinstance(handlers.get_upcoming, GetUpcomingMatchesHandler)
        assert isinstance(handlers.get_predictions, GetMatchPredictionsHandler)


# ==================== 架构验证测试 ====================


@pytest.mark.asyncio
class TestHandlerArchitectureValidation:
    """Handler架构验证测试."""

    async def test_all_handler_type_properties(self):
        """验证所有Handler的command_type/query_type属性."""
        # 命令Handler类型验证
        command_handlers = [
            (CreatePredictionHandler(), CreatePredictionCommand),
            (UpdatePredictionHandler(), UpdatePredictionCommand),
            (DeletePredictionHandler(), DeletePredictionCommand),
            (CreateUserHandler(), CreateUserCommand),
            (CreateMatchHandler(), CreateMatchCommand),
            (UpdateMatchHandler(), UpdateMatchCommand),
        ]

        for handler, expected_type in command_handlers:
            assert hasattr(
                handler, "command_type"
            ), f"{handler.__class__.__name__} 缺少 command_type 属性"
            assert (
                handler.command_type == expected_type
            ), f"{handler.__class__.__name__} command_type 不正确"

        # 查询Handler类型验证
        query_handlers = [
            (GetPredictionByIdHandler(), GetPredictionByIdQuery),
            (GetPredictionsByUserHandler(), GetPredictionsByUserQuery),
            (GetUserStatsHandler(), GetUserStatsQuery),
            (GetUpcomingMatchesHandler(), GetUpcomingMatchesQuery),
            (GetUserByIdHandler(), GetUserByIdQuery),
            (GetMatchByIdHandler(), GetMatchByIdQuery),
            (GetMatchPredictionsHandler(), GetMatchPredictionsQuery),
        ]

        for handler, expected_type in query_handlers:
            assert hasattr(
                handler, "query_type"
            ), f"{handler.__class__.__name__} 缺少 query_type 属性"
            assert (
                handler.query_type == expected_type
            ), f"{handler.__class__.__name__} query_type 不正确"

    async def test_handler_async_methods(self):
        """验证所有Handler都实现了正确的异步方法."""
        handlers_to_test = [
            CreatePredictionHandler(),
            UpdatePredictionHandler(),
            DeletePredictionHandler(),
            CreateUserHandler(),
            GetPredictionByIdHandler(),
            GetPredictionsByUserHandler(),
            GetUserStatsHandler(),
            GetUpcomingMatchesHandler(),
            GetMatchByIdHandler(),
            GetUserByIdHandler(),
            CreateMatchHandler(),
            UpdateMatchHandler(),
            GetMatchPredictionsHandler(),
        ]

        for handler in handlers_to_test:
            # 验证handle方法存在且是协程
            assert hasattr(
                handler, "handle"
            ), f"{handler.__class__.__name__} 缺少 handle 方法"
            assert asyncio.iscoroutinefunction(
                handler.handle
            ), f"{handler.__class__.__name__} handle 方法不是异步的"

    async def test_handler_inheritance_structure(self):
        """验证Handler继承结构."""
        from src.cqrs.base import CommandHandler, QueryHandler

        # 验证命令Handler继承
        command_handlers = [
            CreatePredictionHandler,
            UpdatePredictionHandler,
            DeletePredictionHandler,
            CreateUserHandler,
            CreateMatchHandler,
            UpdateMatchHandler,
        ]

        for handler_class in command_handlers:
            assert issubclass(
                handler_class, CommandHandler
            ), f"{handler_class} 未继承 CommandHandler"

        # 验证查询Handler继承
        query_handlers = [
            GetPredictionByIdHandler,
            GetPredictionsByUserHandler,
            GetUserStatsHandler,
            GetUpcomingMatchesHandler,
            GetUserByIdHandler,
            GetMatchByIdHandler,
            GetMatchPredictionsHandler,
        ]

        for handler_class in query_handlers:
            assert issubclass(
                handler_class, QueryHandler
            ), f"{handler_class} 未继承 QueryHandler"


@pytest.mark.asyncio
class TestHandlerErrorHandlingValidation:
    """Handler错误处理验证."""

    @pytest.fixture
    def mock_session_with_errors(self):
        """模拟各种数据库错误的会话."""
        session = AsyncMock()

        # 模拟连接错误
        session.connection_error = Exception("Database connection failed")

        # 模拟约束违反错误
        session.constraint_error = Exception("Constraint violation")

        # 模拟超时错误
        session.timeout_error = TimeoutError("Query timeout")

        return session

    async def test_create_prediction_various_errors(self):
        """测试创建预测的各种错误情况."""
        handler = CreatePredictionHandler()

        # 测试数据库连接错误
        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_session.scalar.side_effect = Exception(
                "Connection failed"
            )  # 修复：scalar而不是execute
            mock_get_session.return_value.__aenter__.return_value = mock_session

            command = CreatePredictionCommand(
                match_id=1,
                user_id=1,
                predicted_home=2,
                predicted_away=1,
                confidence=0.8,
            )

            result = await handler.handle(command)
            assert result.success is False
            assert "Connection failed" in result.errors[0]

    async def test_update_prediction_concurrent_access(self):
        """测试更新预测的并发访问."""
        handler = UpdatePredictionHandler()

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_prediction = MagicMock()
            mock_prediction.updated_at = datetime.utcnow()
            mock_session.get.return_value = mock_prediction

            # 模拟并发冲突
            mock_session.commit.side_effect = [
                None,  # 第一次成功
                Exception("Concurrent modification conflict"),  # 第二次冲突
            ]

            mock_get_session.return_value.__aenter__.return_value = mock_session

            command = UpdatePredictionCommand(prediction_id=1, predicted_home=3)

            # 第一次更新应该成功
            result1 = await handler.handle(command)
            assert result1.success is True

            # 第二次更新应该失败（并发冲突）
            result2 = await handler.handle(command)
            assert result2.success is False

    async def test_query_handlers_consistency_validation(self):
        """验证查询Handler的一致性行为."""
        query_handlers = [
            (GetPredictionByIdHandler(), GetPredictionByIdQuery(prediction_id=1)),
            (GetUserByIdHandler(), GetUserByIdQuery(user_id=1)),
            (GetMatchByIdHandler(), GetMatchByIdQuery(match_id=1)),
        ]

        for handler, query in query_handlers:
            with patch("src.cqrs.handlers.get_session") as mock_get_session:
                mock_session = AsyncMock()
                mock_session.get.return_value = None  # 模拟未找到
                mock_get_session.return_value.__aenter__.return_value = mock_session

                # 所有未找到的查询都应该返回None
                result = await handler.handle(query)
                assert (
                    result is None
                ), f"{handler.__class__.__name__} 在未找到记录时应该返回None"


@pytest.mark.asyncio
class TestHandlerPerformanceValidation:
    """Handler性能验证测试."""

    async def test_handler_async_performance(self):
        """测试Handler异步执行性能."""
        handler = CreatePredictionHandler()

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_session.scalar.return_value = None  # 修复：确保没有重复预测
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()

            def mock_add(obj):
                obj.id = 1
                obj.created_at = datetime.utcnow()

            mock_session.add = MagicMock(side_effect=mock_add)
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # 使用不同的ID确保不重复
            command = CreatePredictionCommand(
                match_id=9999,
                user_id=9999,
                predicted_home=2,
                predicted_away=1,
                confidence=0.8,
            )

            # 测试执行时间
            start_time = time.time()
            result = await handler.handle(command)
            end_time = time.time()

            execution_time = end_time - start_time

            # 验证结果正确
            assert result.success is True

            # 验证执行时间合理（应该在毫秒级别）
            assert execution_time < 1.0, f"Handler执行时间过长: {execution_time}s"

    async def test_concurrent_handler_execution(self):
        """测试Handler并发执行."""
        handler = GetPredictionByIdHandler()

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_prediction = MagicMock(id=1)
            mock_session.get.return_value = mock_prediction
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # 创建多个并发查询
            queries = [GetPredictionByIdQuery(prediction_id=i) for i in range(1, 6)]

            # 并发执行
            start_time = time.time()
            results = await asyncio.gather(
                *[handler.handle(query) for query in queries]
            )
            end_time = time.time()

            # 验证所有结果都正确
            assert len(results) == 5
            assert all(result is not None for result in results)

            # 验证并发执行比串行执行快
            concurrent_time = end_time - start_time

            # 简单验证：并发执行时间应该合理
            assert concurrent_time < 2.0, f"并发执行时间过长: {concurrent_time}s"


@pytest.mark.asyncio
class TestHandlerEdgeCasesValidation:
    """Handler边界情况验证."""

    async def test_extreme_values_handling(self):
        """测试极端值处理."""
        handler = CreatePredictionHandler()

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_session.scalar.return_value = None  # 修复：确保没有重复预测
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()

            def mock_add(obj):
                # 模拟数据库设置极端值
                obj.id = 999999999
                obj.created_at = datetime.utcnow()

            mock_session.add = MagicMock(side_effect=mock_add)
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # 测试极端值 - 使用唯一ID避免重复
            command = CreatePredictionCommand(
                match_id=888888888,
                user_id=777777777,
                predicted_home=100,
                predicted_away=-100,
                confidence=0.999999,
                strategy_used="x" * 1000,  # 非常长的策略名
                notes="y" * 10000,  # 非常长的备注
            )

            result = await handler.handle(command)
            assert result.success is True

    async def test_null_and_empty_values_handling(self):
        """测试空值和空字符串处理."""
        handler = UpdatePredictionHandler()

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_prediction = MagicMock()
            mock_prediction.confidence = Decimal("0.5")
            mock_prediction.strategy_used = "old"
            mock_prediction.notes = "old_notes"
            mock_session.get.return_value = mock_prediction
            mock_session.commit = AsyncMock()
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # 测试空值更新
            command = UpdatePredictionCommand(
                prediction_id=1,
                predicted_home=None,  # 不更新
                predicted_away=None,  # 不更新
                confidence=None,  # 不更新
                strategy_used="",  # 空字符串
                notes=None,  # 设为None
            )

            result = await handler.handle(command)
            assert result.success is True

    async def test_unicode_handling(self):
        """测试Unicode字符处理."""
        handler = CreatePredictionHandler()

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_session.scalar.return_value = None  # 修复：确保没有重复预测
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()

            def mock_add(obj):
                obj.id = 1
                obj.created_at = datetime.utcnow()

            mock_session.add = MagicMock(side_effect=mock_add)
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # 测试Unicode字符 - 使用唯一ID避免重复
            command = CreatePredictionCommand(
                match_id=666666666,
                user_id=555555555,
                predicted_home=2,
                predicted_away=1,
                confidence=0.8,
                strategy_used="🏆_足球模型_中文_🚀",  # 包含Emoji和中文
                notes="测试预测 🎯 中文内容 📊",
            )

            result = await handler.handle(command)
            assert result.success is True


@pytest.mark.asyncio
class TestHandlerIntegrationWithCQRS:
    """Handler与CQRS系统集成测试."""

    async def test_handler_command_bus_integration(self):
        """测试Handler与命令总线的集成."""
        from src.cqrs.bus import CommandBus

        # 创建命令总线并注册Handler
        command_bus = CommandBus()
        handler = CreatePredictionHandler()
        command_bus.register_handler(CreatePredictionCommand, handler)

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_session.scalar.return_value = None
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()

            def mock_add(obj):
                obj.id = 1
                obj.created_at = datetime.utcnow()

            mock_session.add = MagicMock(side_effect=mock_add)
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # 通过命令总线分发命令
            command = CreatePredictionCommand(
                match_id=1,
                user_id=1,
                predicted_home=2,
                predicted_away=1,
                confidence=0.8,
            )

            result = await command_bus.dispatch(command)

            # 验证结果
            assert result.success is True

    async def test_handler_query_bus_integration(self):
        """测试Handler与查询总线的集成."""
        from src.cqrs.bus import QueryBus

        # 创建查询总线并注册Handler
        query_bus = QueryBus()
        handler = GetPredictionByIdHandler()
        query_bus.register_handler(GetPredictionByIdQuery, handler)

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_prediction = MagicMock(id=1)
            mock_session.get.return_value = mock_prediction
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # 通过查询总线分发查询
            query = GetPredictionByIdQuery(prediction_id=1)

            result = await query_bus.dispatch(query)

            # 验证结果
            assert result is not None
            assert result.id == 1


@pytest.mark.asyncio
class TestHandlerValidationIntegration:
    """Handler验证集成测试."""

    async def test_handler_with_validatable_commands(self):
        """测试Handler与可验证命令的集成."""
        # 这个测试验证Handler能够处理带有验证逻辑的命令
        handler = CreatePredictionHandler()

        # 创建可能需要验证的命令
        command = CreatePredictionCommand(
            match_id=1,
            user_id=1,
            predicted_home=2,
            predicted_away=1,
            confidence=0.8,
            strategy_used=None,  # 可能为空
            notes=None,
        )

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_session.scalar.return_value = None
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()

            def mock_add(obj):
                obj.id = 1
                obj.created_at = datetime.utcnow()

            mock_session.add = MagicMock(side_effect=mock_add)
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await handler.handle(command)
            assert result.success is True


# ==================== 性能基准测试 ====================


@pytest.mark.asyncio
@pytest.mark.slow
class TestHandlerPerformanceBenchmarks:
    """Handler性能基准测试."""

    async def benchmark_create_prediction_performance(self):
        """创建预测性能基准测试."""
        handler = CreatePredictionHandler()

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_session.scalar.return_value = None
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()

            def mock_add(obj):
                obj.id = 1
                obj.created_at = datetime.utcnow()

            mock_session.add = MagicMock(side_effect=mock_add)
            mock_get_session.return_value.__aenter__.return_value = mock_session

            command = CreatePredictionCommand(
                match_id=1,
                user_id=1,
                predicted_home=2,
                predicted_away=1,
                confidence=0.8,
            )

            # 基准测试：执行100次
            start_time = time.time()
            for _ in range(100):
                await handler.handle(command)
            end_time = time.time()

            total_time = end_time - start_time
            avg_time = total_time / 100

            # 验证平均执行时间合理
            assert avg_time < 0.01, f"平均执行时间过长: {avg_time}s"

            print(f"CreatePredictionHandler 平均执行时间: {avg_time:.4f}s")

    async def benchmark_query_performance(self):
        """查询性能基准测试."""
        handler = GetPredictionByIdHandler()

        with patch("src.cqrs.handlers.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_prediction = MagicMock(id=1)
            mock_session.get.return_value = mock_prediction
            mock_get_session.return_value.__aenter__.return_value = mock_session

            query = GetPredictionByIdQuery(prediction_id=1)

            # 基准测试：执行1000次
            start_time = time.time()
            for _ in range(1000):
                await handler.handle(query)
            end_time = time.time()

            total_time = end_time - start_time
            avg_time = total_time / 1000

            # 验证平均执行时间合理
            assert avg_time < 0.001, f"查询平均执行时间过长: {avg_time}s"

            print(f"GetPredictionByIdHandler 平均执行时间: {avg_time:.4f}s")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
