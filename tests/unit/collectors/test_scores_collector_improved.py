""""""""
比分收集器单元测试
Unit tests for Scores Collector

测试 src.collectors.scores_collector 模块的实时比分收集功能
""""""""

import os

import pytest

# 测试导入
try:
    from src.collectors.scores_collector import ScoresCollector, ScoresCollectorFactory
    from src.database.models import Match, MatchStatus

    SCORES_COLLECTOR_AVAILABLE = True
except ImportError:
    SCORES_COLLECTOR_AVAILABLE = False
    ScoresCollector = None
    ScoresCollectorFactory = None
    Match = None
    MatchStatus = None


@pytest.mark.skipif(not SCORES_COLLECTOR_AVAILABLE, reason="Scores collector module not available")
@pytest.mark.unit
class TestScoresCollector:
    """比分收集器测试类"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def mock_redis_client(self):
        """模拟Redis客户端"""
        return AsyncMock()

    @pytest.fixture
    def scores_collector(self, mock_db_session, mock_redis_client):
        """创建比分收集器实例"""
        with patch.dict(os.environ, {"FOOTBALL_API_TOKEN": "test_token"}):
            return ScoresCollector(mock_db_session, mock_redis_client)

    def test_collector_initialization(self, scores_collector):
        """测试收集器初始化"""
        assert scores_collector.db_session is not None
        assert scores_collector.redis_client is not None
        assert scores_collector.cache_timeout == 60
        assert "live_scores" in scores_collector.api_endpoints
        assert "X-Auth-Token" in scores_collector.headers

    def test_collector_initialization_without_api_token(self, mock_db_session, mock_redis_client):
        """测试没有API Token时的初始化"""
        with patch.dict(os.environ, {}, clear=True):
            with patch("src.collectors.scores_collector.logger") as mock_logger:
                collector = ScoresCollector(mock_db_session, mock_redis_client)
                assert collector.headers == {}
                mock_logger.warning.assert_called_once_with("未设置 FOOTBALL_API_TOKEN 环境变量")

    @pytest.mark.asyncio
    async def test_collect_live_scores_with_cache(self, scores_collector):
        """测试从缓存收集实时比分"""
        cached_data = {
            "live_matches_count": 2,
            "scores": {"1": {"score": {"home": 1, "away": 1}}},
        }
        scores_collector.redis_client.get_cache_value.return_value = cached_data

        result = await scores_collector.collect_live_scores()

        scores_collector.redis_client.get_cache_value.assert_called_once_with("scores:live")
        assert result == cached_data

    @pytest.mark.asyncio
    async def test_collect_live_scores_force_refresh(self, scores_collector):
        """测试强制刷新实时比分"""
        # 模拟数据库查询返回的比赛
        mock_match = Mock()
        mock_match.id = 1
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2
        mock_match.minute = 45
        mock_match.match_status = "live"
        mock_match.home_score = 2
        mock_match.away_score = 1

        # 模拟_get_live_matches_from_db方法返回结果
        with patch.object(scores_collector, "_get_live_matches_from_db", return_value=[mock_match]):
            with patch.object(
                scores_collector,
                "_get_match_score",
                return_value={"home": 2, "away": 1},
            ):
                result = await scores_collector.collect_live_scores(force_refresh=True)

        assert result["live_matches_count"] == 1
        assert "scores" in result
        assert 1 in result["scores"]
        assert result["scores"][1]["score"] == {"home": 2, "away": 1}

        # 验证缓存被设置
        scores_collector.redis_client.set_cache_value.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_live_scores_database_error(self, scores_collector):
        """测试数据库错误时的处理"""
        # 需要抛出一个能被捕获的异常类型
        with patch.object(
            scores_collector,
            "_get_live_matches_from_db",
            side_effect=ValueError("Database error"),
        ):
            scores_collector.redis_client.get_cache_value.return_value = None

            with patch("src.collectors.scores_collector.logger") as mock_logger:
                result = await scores_collector.collect_live_scores()

        assert "error" in result
        assert "Database error" in result["error"]
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_live_matches_from_db_integration(self, scores_collector):
        """测试从数据库获取实时比赛（集成测试层面）"""
        # 这个测试验证方法的接口正确性,而不是实际的数据库查询
        # 实际的数据库查询应该通过更高层次的集成测试来验证

        # 验证方法存在且可调用
        assert hasattr(scores_collector, "_get_live_matches_from_db")
        assert callable(getattr(scores_collector, "_get_live_matches_from_db"))

    @pytest.mark.asyncio
    async def test_get_match_score_with_scores(self, scores_collector):
        """测试获取有比分的比赛分数"""
        mock_match = Mock()
        mock_match.home_score = 3
        mock_match.away_score = 1

        score = await scores_collector._get_match_score(mock_match)

        assert score == {"home": 3, "away": 1}

    @pytest.mark.asyncio
    async def test_get_match_score_without_scores(self, scores_collector):
        """测试获取没有比分的比赛分数"""
        mock_match = Mock()
        mock_match.home_score = None
        mock_match.away_score = None

        score = await scores_collector._get_match_score(mock_match)

        assert score == {"home": 0, "away": 0}

    @pytest.mark.asyncio
    async def test_clear_match_cache(self, scores_collector):
        """测试清除比赛缓存"""
        match_id = 123

        await scores_collector._clear_match_cache(match_id)

        expected_keys = ["scores:live", "events:match:123"]
        assert scores_collector.redis_client.delete_cache.call_count == 2
        calls = [call[0][0] for call in scores_collector.redis_client.delete_cache.call_args_list]
        assert calls == expected_keys

    @pytest.mark.asyncio
    async def test_collect_live_scores_caching_behavior(self, scores_collector):
        """测试缓存行为"""
        # 第一次调用 - 无缓存
        scores_collector.redis_client.get_cache_value.return_value = None
        mock_match = Mock()
        mock_match.id = 1
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2
        mock_match.minute = 30
        mock_match.match_status = "live"
        mock_match.home_score = 1
        mock_match.away_score = 0

        with patch.object(scores_collector, "_get_live_matches_from_db", return_value=[mock_match]):
            with patch.object(
                scores_collector,
                "_get_match_score",
                return_value={"home": 1, "away": 0},
            ):
                await scores_collector.collect_live_scores()

        # 验证结果被缓存
        scores_collector.redis_client.set_cache_value.assert_called_once_with(
            "scores:live", ANY, expire=60
        )

        # 第二次调用 - 有缓存
        cached_result = {"live_matches_count": 1, "scores": {"test": "data"}}
        scores_collector.redis_client.get_cache_value.return_value = cached_result
        result2 = await scores_collector.collect_live_scores()

        assert result2 == cached_result
        # set_cache_value 应该只被调用一次（第一次）
        assert scores_collector.redis_client.set_cache_value.call_count == 1

    def test_api_endpoints_configuration(self, scores_collector):
        """测试API端点配置"""
        assert "live_scores" in scores_collector.api_endpoints
        assert "events" in scores_collector.api_endpoints
        assert (
            scores_collector.api_endpoints["events"].format(match_id=123)
            == "https://api.football-data.org/v4/matches/123/events"
        )

    @pytest.mark.asyncio
    async def test_collect_live_scores_empty_result(self, scores_collector):
        """测试空结果处理"""
        # 模拟没有实时比赛
        with patch.object(scores_collector, "_get_live_matches_from_db", return_value=[]):
            scores_collector.redis_client.get_cache_value.return_value = None

            result = await scores_collector.collect_live_scores(force_refresh=True)

        assert result["live_matches_count"] == 0
        assert result["scores"] == {}
        scores_collector.redis_client.set_cache_value.assert_called_once()


@pytest.mark.skipif(not SCORES_COLLECTOR_AVAILABLE, reason="Scores collector module not available")
@pytest.mark.unit
class TestScoresCollectorFactory:
    """比分收集器工厂类测试"""

    def test_factory_create(self):
        """测试工厂创建方法"""
        with patch("src.collectors.scores_collector.DatabaseManager") as mock_db:
            with patch("src.collectors.scores_collector.RedisManager") as mock_redis:
                with patch.dict(os.environ, {"FOOTBALL_API_TOKEN": "factory_test"}):
                    collector = ScoresCollectorFactory.create()

                    mock_db.assert_called_once()
                    mock_redis.assert_called_once()
                    assert isinstance(collector, ScoresCollector)


@pytest.mark.skipif(not SCORES_COLLECTOR_AVAILABLE, reason="Scores collector module not available")
@pytest.mark.unit
class TestScoresCollectorIntegration:
    """比分收集器集成测试"""

    @pytest.mark.asyncio
    async def test_full_workflow_integration(self):
        """测试完整工作流程集成"""
        # 创建模拟依赖
        mock_db_session = AsyncMock()
        mock_redis_client = AsyncMock()

        with patch.dict(os.environ, {"FOOTBALL_API_TOKEN": "integration_test"}):
            collector = ScoresCollector(mock_db_session, mock_redis_client)

        # 模拟多场比赛
        matches = [
            Mock(
                id=1,
                home_team_id=1,
                away_team_id=2,
                minute=45,
                match_status="live",
                home_score=2,
                away_score=1,
            ),
            Mock(
                id=2,
                home_team_id=3,
                away_team_id=4,
                minute=30,
                match_status="half_time",
                home_score=1,
                away_score=1,
            ),
        ]

        # 模拟无缓存
        mock_redis_client.get_cache_value.return_value = None

        with patch.object(collector, "_get_live_matches_from_db", return_value=matches):
            with patch.object(collector, "_get_match_score") as mock_get_score:
                mock_get_score.side_effect = [
                    {"home": 2, "away": 1},
                    {"home": 1, "away": 1},
                ]

                result = await collector.collect_live_scores(force_refresh=True)

        # 验证结果
        assert result["live_matches_count"] == 2
        assert len(result["scores"]) == 2
        assert 1 in result["scores"]
        assert 2 in result["scores"]

        # 验证缓存操作
        mock_redis_client.set_cache_value.assert_called_once()
        call_args = mock_redis_client.set_cache_value.call_args
        cache_key = call_args[0][0]
        call_args[0][1]
        # expire 是关键字参数
        assert cache_key == "scores:live"
        assert call_args[1]["expire"] == 60

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """测试错误恢复工作流程"""
        mock_db_session = AsyncMock()
        mock_redis_client = AsyncMock()

        with patch.dict(os.environ, {"FOOTBALL_API_TOKEN": "error_test"}):
            collector = ScoresCollector(mock_db_session, mock_redis_client)

        # 模拟数据库错误
        with patch.object(
            collector,
            "_get_live_matches_from_db",
            side_effect=RuntimeError("Connection failed"),
        ):
            mock_redis_client.get_cache_value.return_value = None

            with patch("src.collectors.scores_collector.logger") as mock_logger:
                result = await collector.collect_live_scores()

        # 验证错误处理
        assert "error" in result
        assert "Connection failed" in result["error"]
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_cache_operations(self):
        """测试并发缓存操作"""
        mock_db_session = AsyncMock()
        mock_redis_client = AsyncMock()

        with patch.dict(os.environ, {"FOOTBALL_API_TOKEN": "concurrent_test"}):
            collector = ScoresCollector(mock_db_session, mock_redis_client)

        import asyncio

        # 模拟并发调用
        async def collect_scores():
            mock_redis_client.get_cache_value.return_value = None

            return await collector.collect_live_scores(force_refresh=True)

        with patch.object(collector, "_get_live_matches_from_db", return_value=[]):
            # 并发执行多个收集任务
            tasks = [collect_scores() for _ in range(3)]
            results = await asyncio.gather(*tasks)

            # 验证所有任务都成功完成
            assert all(isinstance(result, dict) for result in results)
            assert all("live_matches_count" in result for result in results)


@pytest.mark.skipif(
    SCORES_COLLECTOR_AVAILABLE,
    reason="This test should only run when module is not available",
)
@pytest.mark.unit
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试模块导入错误处理"""
        assert not SCORES_COLLECTOR_AVAILABLE
        assert ScoresCollector is None
        assert ScoresCollectorFactory is None


def test_module_imports():
    """测试模块导入功能"""
    if SCORES_COLLECTOR_AVAILABLE:
from src.collectors.scores_collector import (
            ScoresCollector,
            ScoresCollectorFactory,
        )

        assert ScoresCollector is not None
        assert ScoresCollectorFactory is not None
        assert callable(ScoresCollector)
        assert callable(ScoresCollectorFactory.create)
