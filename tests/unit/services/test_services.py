# TODO: Consider creating a fixture for 20 repeated Mock creations

# TODO: Consider creating a fixture for 20 repeated Mock creations

from unittest.mock import patch, AsyncMock, MagicMock
"""
服务层单元测试
"""

# 可选依赖导入
try:
    from src.dependencies.optional import *
except ImportError:
    pass

import pytest
from datetime import datetime, timedelta
from src.services.enhanced_core import EnhancedBaseService, ServiceConfig
# from src.services.match_service import MatchService
# from src.services.prediction_service import PredictionService


@pytest.mark.unit

class TestServiceConfig:
    """服务配置测试"""

    def test_service_config_creation(self):
        """测试服务配置创建"""
        _config = ServiceConfig("test_service")

        assert _config.service_name == "test_service"
        assert _config.enabled is True
        assert _config.retry_attempts == 3
        assert _config.timeout == 30.0
        assert _config.health_check_interval == 60.0

    def test_service_config_custom(self):
        """测试自定义服务配置"""
        _config = ServiceConfig(
            "custom_service",
            enabled=False,
            retry_attempts=5,
            timeout=60.0,
            health_check_interval=120.0,
        )

        assert _config.service_name == "custom_service"
        assert _config.enabled is False
        assert _config.retry_attempts == 5
        assert _config.timeout == 60.0
        assert _config.health_check_interval == 120.0


class TestEnhancedBaseService:
    """增强基础服务测试"""

    @pytest.fixture
    def service_config(self):
        """服务配置"""
        return ServiceConfig("test_service")

    @pytest.fixture
    def enhanced_service(self, service_config):
        """增强基础服务实例"""
        return TestEnhancedService(service_config)

    def test_enhanced_service_init(self, enhanced_service, service_config):
        """测试增强服务初始化"""
        assert enhanced_service._config == service_config
        assert enhanced_service.service_name == "test_service"
        assert enhanced_service.metrics is not None
        assert enhanced_service.is_running is False

    @pytest.mark.asyncio
    async def test_service_lifecycle(self, enhanced_service):
        """测试服务生命周期"""
        # 启动服务
        await enhanced_service.start()
        assert enhanced_service.is_running is True
        assert enhanced_service.start_time is not None

        # 停止服务
        await enhanced_service.stop()
        assert enhanced_service.is_running is False

    @pytest.mark.asyncio
    async def test_health_check(self, enhanced_service):
        """测试健康检查"""
        health = await enhanced_service.health_check()
        assert health["status"] == "healthy"
        assert "uptime" in health
        assert "metrics" in health

    def test_record_metrics(self, enhanced_service):
        """测试记录指标"""
        # 记录成功指标
        enhanced_service.record_success("test_operation")
        metrics = enhanced_service.get_metrics()
        assert metrics["total_operations"] == 1
        assert metrics["successful_operations"] == 1

        # 记录失败指标
        enhanced_service.record_failure("test_operation")
        metrics = enhanced_service.get_metrics()
        assert metrics["total_operations"] == 2
        assert metrics["failed_operations"] == 1

    def test_get_uptime(self, enhanced_service):
        """测试获取运行时间"""
        # 未启动时返回0
        uptime = enhanced_service.get_uptime()
        assert uptime == 0

    def test_reset_metrics(self, enhanced_service):
        """测试重置指标"""
        # 记录一些指标
        enhanced_service.record_success("test_op")
        enhanced_service.record_failure("test_op")

        # 重置指标
        enhanced_service.reset_metrics()
        metrics = enhanced_service.get_metrics()
        assert metrics["total_operations"] == 0


class TestMatchService:
    """比赛服务测试"""

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        return AsyncMock()

    @pytest.fixture
    def match_service(self, mock_db_manager):
        """比赛服务实例"""
        return MatchService(mock_db_manager)

    @pytest.mark.asyncio
    async def test_get_upcoming_matches(self, match_service):
        """测试获取即将到来的比赛"""
        mock_matches = [MagicMock(), MagicMock()]
        match_service.match_repo.get_upcoming_matches = AsyncMock(
            return_value=mock_matches
        )

        _result = await match_service.get_upcoming_matches(days=7)
        assert len(result) == 2
        match_service.match_repo.get_upcoming_matches.assert_called_once_with(days=7)

    @pytest.mark.asyncio
    async def test_get_live_matches(self, match_service):
        """测试获取正在进行的比赛"""
        mock_matches = [MagicMock()]
        match_service.match_repo.get_live_matches = AsyncMock(return_value=mock_matches)

        _result = await match_service.get_live_matches()
        assert len(result) == 1
        match_service.match_repo.get_live_matches.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_match(self, match_service):
        """测试创建比赛"""
        match_data = {
            "home_team_id": 1,
            "away_team_id": 2,
            "league_id": 10,
            "scheduled_time": datetime.now() + timedelta(days=1),
        }
        mock_match = MagicMock(id=123)
        match_service.match_repo.create = AsyncMock(return_value=mock_match)

        _result = await match_service.create_match(match_data)
        assert _result.id == 123
        match_service.match_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_match_score(self, match_service):
        """测试更新比赛比分"""
        mock_match = MagicMock(id=123)
        match_service.match_repo.get_by_id = AsyncMock(return_value=mock_match)
        match_service.match_repo.update = AsyncMock(return_value=mock_match)

        _result = await match_service.update_match_score(123, 2, 1)
        assert _result.id == 123
        match_service.match_repo.get_by_id.assert_called_once_with(123)
        match_service.match_repo.update.assert_called_once()


class TestPredictionService:
    """预测服务测试"""

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        return AsyncMock()

    @pytest.fixture
    def prediction_service(self, mock_db_manager):
        """预测服务实例"""
        return PredictionService(mock_db_manager)

    @pytest.mark.asyncio
    async def test_make_prediction(self, prediction_service):
        """测试创建预测"""
        prediction_data = {
            "match_id": 123,
            "user_id": 456,
            "prediction_type": "match_result",
            "predicted_outcome": "home_win",
            "confidence": 0.75,
        }
        mock_prediction = MagicMock(id=789)
        prediction_service.prediction_repo.create = AsyncMock(
            return_value=mock_prediction
        )

        _result = await prediction_service.make_prediction(prediction_data)
        assert _result.id == 789
        prediction_service.prediction_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_predictions(self, prediction_service):
        """测试获取用户预测"""
        mock_predictions = [MagicMock(), MagicMock()]
        prediction_service.prediction_repo.get_user_predictions = AsyncMock(
            return_value=mock_predictions
        )

        _result = await prediction_service.get_user_predictions(user_id=456, limit=10)
        assert len(result) == 2
        prediction_service.prediction_repo.get_user_predictions.assert_called_once_with(
            456, limit=10
        )

    @pytest.mark.asyncio
    async def test_settle_prediction(self, prediction_service):
        """测试结算预测"""
        mock_prediction = MagicMock(id=789, is_correct=None, settled_at=None)
        prediction_service.prediction_repo.get_by_id = AsyncMock(
            return_value=mock_prediction
        )
        prediction_service.prediction_repo.update = AsyncMock(
            return_value=mock_prediction
        )

        _result = await prediction_service.settle_prediction(789, "home_win", True)
        assert _result.is_correct is True
        assert _result.settled_at is not None

    @pytest.mark.asyncio
    async def test_get_prediction_statistics(self, prediction_service):
        """测试获取预测统计"""
        prediction_service.prediction_repo.count = AsyncMock(side_effect=[100, 65])
        prediction_service.prediction_repo.get_prediction_accuracy = AsyncMock(
            return_value=65.0
        )

        _result = await prediction_service.get_prediction_statistics(
            user_id=456, days=30
        )
        assert _result["total_predictions"] == 100
        assert _result["accuracy"] == 65.0


# 用于测试的增强服务实现
class TestEnhancedService(EnhancedBaseService):
    """测试用的增强服务"""

    def __init__(self, config: ServiceConfig):
        super().__init__(config)

    async def _perform_health_check(self) -> dict:
        """执行健康检查"""
        return {"status": "healthy", "checks": {"database": "ok", "cache": "ok"}}

    async def _do_start(self):
        """启动服务"""
        pass

    async def _do_stop(self):
        """停止服务"""
        pass
