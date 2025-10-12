"""
比分收集器测试
Tests for Scores Collector

测试src.collectors.scores_collector模块的比分收集功能
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import asyncio

# 测试导入
try:
    from src.collectors.scores_collector import ScoresCollector, ScoresCollectorFactory

    SCORES_COLLECTOR_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    SCORES_COLLECTOR_AVAILABLE = False
    ScoresCollector = None
    ScoresCollectorFactory = None


@pytest.mark.skipif(
    not SCORES_COLLECTOR_AVAILABLE, reason="Scores collector module not available"
)
class TestScoresCollector:
    """比分收集器测试"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def mock_redis_client(self):
        """模拟Redis客户端"""
        redis = AsyncMock()
        redis.get_cache_value = AsyncMock(return_value=None)
        redis.set_cache_value = AsyncMock()
        redis.delete_cache = AsyncMock()
        return redis

    @pytest.fixture
    def collector(self, mock_db_session, mock_redis_client):
        """创建比分收集器实例"""
        with patch.dict("os.environ", {"FOOTBALL_API_TOKEN": "test_token"}):
            return ScoresCollector(mock_db_session, mock_redis_client)

    def test_collector_creation(self, collector):
        """测试：收集器创建"""
        assert collector is not None
        assert collector.db_session is not None
        assert collector.redis_client is not None
        assert collector.cache_timeout == 60
        assert collector.headers["X-Auth-Token"] == "test_token"

    def test_collector_creation_without_token(self, mock_db_session, mock_redis_client):
        """测试：没有API Token的收集器创建"""
        with patch.dict("os.environ", {}, clear=True):
            collector = ScoresCollector(mock_db_session, mock_redis_client)
            assert collector.headers == {}
            assert "X-Auth-Token" not in collector.headers

    @pytest.mark.asyncio
    async def test_collect_live_scores_with_cache(self, collector):
        """测试：从缓存收集实时比分"""
        cached_data = {"live_matches_count": 2, "scores": {"match1": {}}}
        collector.redis_client.get_cache_value.return_value = cached_data

        result = await collector.collect_live_scores()

        assert result == cached_data
        collector.redis_client.get_cache_value.assert_called_once_with("scores:live")

    @pytest.mark.asyncio
    async def test_collect_live_scores_force_refresh(self, collector):
        """测试：强制刷新实时比分"""
        # 模拟数据库查询
        mock_match = Mock()
        mock_match.id = 1
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.minute = 45
        mock_match.match_status = "live"
        mock_match.home_score = 2
        mock_match.away_score = 1

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_match]
        collector.db_session.execute.return_value = mock_result

        result = await collector.collect_live_scores(force_refresh=True)

        assert "live_matches_count" in result
        assert result["live_matches_count"] == 1
        assert "scores" in result
        collector.redis_client.set_cache_value.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_live_scores_no_cache(self, collector):
        """测试：没有缓存时收集实时比分"""
        collector.redis_client.get_cache_value.return_value = None

        # 模拟空查询结果
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        collector.db_session.execute.return_value = mock_result

        result = await collector.collect_live_scores()

        assert result["live_matches_count"] == 0
        assert result["scores"] == {}
        collector.redis_client.set_cache_value.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_live_scores_with_error(self, collector):
        """测试：收集实时比分时的错误处理"""
        collector.db_session.execute.side_effect = Exception("Database error")

        result = await collector.collect_live_scores()

        assert "error" in result
        assert "Database error" in result["error"]

    @pytest.mark.asyncio
    async def test_get_live_matches_from_db(self, collector):
        """测试：从数据库获取实时比赛"""
        mock_match = Mock()
        mock_match.match_status = "live"

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_match]
        collector.db_session.execute.return_value = mock_result

        matches = await collector._get_live_matches_from_db()

        assert len(matches) == 1
        assert matches[0] == mock_match

    @pytest.mark.asyncio
    async def test_get_match_score_with_scores(self, collector):
        """测试：获取有比分的比赛"""
        mock_match = Mock()
        mock_match.home_score = 2
        mock_match.away_score = 1

        score = await collector._get_match_score(mock_match)

        assert score == {"home": 2, "away": 1}

    @pytest.mark.asyncio
    async def test_get_match_score_without_scores(self, collector):
        """测试：获取没有比分的比赛"""
        mock_match = Mock()
        mock_match.home_score = None
        mock_match.away_score = None

        score = await collector._get_match_score(mock_match)

        assert score == {"home": 0, "away": 0}

    @pytest.mark.asyncio
    async def test_clear_match_cache(self, collector):
        """测试：清除比赛缓存"""
        match_id = 123

        await collector._clear_match_cache(match_id)

        expected_calls = [("scores:live",), ("events:match:123",)]
        actual_calls = [
            call[0] for call in collector.redis_client.delete_cache.call_args_list
        ]

        assert len(actual_calls) == 2
        assert actual_calls[0] in expected_calls
        assert actual_calls[1] in expected_calls


@pytest.mark.skipif(
    not SCORES_COLLECTOR_AVAILABLE, reason="Scores collector module not available"
)
class TestScoresCollectorFactory:
    """比分收集器工厂测试"""

    @patch("src.collectors.scores_collector.DatabaseManager")
    @patch("src.collectors.scores_collector.RedisManager")
    def test_create_collector(self, mock_redis, mock_db):
        """测试：创建收集器"""
        mock_db_instance = Mock()
        mock_redis_instance = Mock()
        mock_db.return_value = mock_db_instance
        mock_redis.return_value = mock_redis_instance

        collector = ScoresCollectorFactory.create()

        assert isinstance(collector, ScoresCollector)
        mock_db.assert_called_once()
        mock_redis.assert_called_once()


@pytest.mark.skipif(
    SCORES_COLLECTOR_AVAILABLE, reason="Scores collector module should be available"
)
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not SCORES_COLLECTOR_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if SCORES_COLLECTOR_AVAILABLE:
        from src.collectors.scores_collector import (
            ScoresCollector,
            ScoresCollectorFactory,
        )

        assert ScoresCollector is not None
        assert ScoresCollectorFactory is not None


@pytest.mark.skipif(
    not SCORES_COLLECTOR_AVAILABLE, reason="Scores collector module not available"
)
class TestScoresCollectorAdvanced:
    """比分收集器高级测试"""

    @pytest.mark.asyncio
    async def test_collect_multiple_matches(self):
        """测试：收集多场比赛"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get_cache_value.return_value = None

        # 创建多场比赛
        matches = []
        for i in range(5):
            match = Mock()
            match.id = i + 1
            match.home_team_id = (i + 1) * 10
            match.away_team_id = (i + 1) * 20
            match.minute = 45 + i * 10
            match.match_status = "live" if i % 2 == 0 else "half_time"
            match.home_score = i + 1
            match.away_score = i
            matches.append(match)

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = matches
        mock_db.execute.return_value = mock_result

        with patch.dict("os.environ", {"FOOTBALL_API_TOKEN": "test"}):
            collector = ScoresCollector(mock_db, mock_redis)
            result = await collector.collect_live_scores()

            assert result["live_matches_count"] == 5
            assert len(result["scores"]) == 5

    @pytest.mark.asyncio
    async def test_cache_timeout_configuration(self):
        """测试：缓存超时配置"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get_cache_value.return_value = None

        with patch.dict("os.environ", {"FOOTBALL_API_TOKEN": "test"}):
            collector = ScoresCollector(mock_db, mock_redis)
            collector.cache_timeout = 120  # 设置2分钟缓存

            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = []
            mock_db.execute.return_value = mock_result

            await collector.collect_live_scores()

            # 验证缓存使用了正确的超时时间
            mock_redis.set_cache_value.assert_called_once()
            call_args = mock_redis.set_cache_value.call_args
            assert call_args[0][2] == 120  # expire参数

    @pytest.mark.asyncio
    async def test_concurrent_collection(self):
        """测试：并发收集"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get_cache_value.return_value = None

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        with patch.dict("os.environ", {"FOOTBALL_API_TOKEN": "test"}):
            collector = ScoresCollector(mock_db, mock_redis)

            # 并发执行多次收集
            tasks = [collector.collect_live_scores() for _ in range(10)]
            results = await asyncio.gather(*tasks)

            # 所有结果应该相同
            assert all(result == results[0] for result in results)

    def test_api_endpoints_configuration(self):
        """测试：API端点配置"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()

        with patch.dict("os.environ", {"FOOTBALL_API_TOKEN": "test"}):
            collector = ScoresCollector(mock_db, mock_redis)

            assert "live_scores" in collector.api_endpoints
            assert "events" in collector.api_endpoints
            assert collector.api_endpoints["live_scores"].startswith("https://api")

    def test_different_match_statuses(self):
        """测试：不同的比赛状态"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()

        with patch.dict("os.environ", {"FOOTBALL_API_TOKEN": "test"}):
            collector = ScoresCollector(mock_db, mock_redis)

            # 测试不同状态的比赛
            statuses = ["live", "half_time", "finished", "postponed"]
            for status in statuses:
                match = Mock()
                match.match_status = status
                match.home_score = None
                match.away_score = None

                # 运行异步测试
                async def test_score():
                    score = await collector._get_match_score(match)
                    if status in ["live", "half_time"]:
                        # 正在进行的比赛应该有比分
                        assert score in [
                            {"home": 0, "away": 0},
                            {"home": None, "away": None},
                        ]

                asyncio.run(test_score())

    @pytest.mark.asyncio
    async def test_error_logging(self):
        """测试：错误日志记录"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get_cache_value.return_value = None

        with patch("src.collectors.scores_collector.logger") as mock_logger:
            with patch.dict("os.environ", {"FOOTBALL_API_TOKEN": "test"}):
                collector = ScoresCollector(mock_db, mock_redis)
                collector.db_session.execute.side_effect = ValueError("Test error")

                await collector.collect_live_scores()

                # 验证错误被记录
                mock_logger.error.assert_called_once()
                assert "收集实时比分失败" in str(mock_logger.error.call_args)

    @pytest.mark.asyncio
    async def test_partial_failure_handling(self):
        """测试：部分失败处理"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()
        mock_redis.get_cache_value.return_value = None

        # 一些比赛有数据，一些没有
        matches = [
            Mock(
                id=1,
                home_team_id=10,
                away_team_id=20,
                minute=45,
                match_status="live",
                home_score=2,
                away_score=1,
            ),
            Mock(
                id=2,
                home_team_id=30,
                away_team_id=40,
                minute=30,
                match_status="live",
                home_score=None,
                away_score=None,
            ),
        ]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = matches
        mock_db.execute.return_value = mock_result

        with patch.dict("os.environ", {"FOOTBALL_API_TOKEN": "test"}):
            collector = ScoresCollector(mock_db, mock_redis)
            result = await collector.collect_live_scores()

            # 应该处理所有比赛，即使有些数据不完整
            assert result["live_matches_count"] == 2
            assert len(result["scores"]) == 2

    def test_environment_variable_handling(self):
        """测试：环境变量处理"""
        mock_db = AsyncMock()
        mock_redis = AsyncMock()

        # 测试不同的环境变量设置
        test_cases = [
            ({"FOOTBALL_API_TOKEN": "valid_token"}, "valid_token"),
            ({}, None),
            ({"FOOTBALL_API_TOKEN": ""}, None),
        ]

        for env_vars, expected_token in test_cases:
            with patch.dict("os.environ", env_vars, clear=True):
                collector = ScoresCollector(mock_db, mock_redis)
                if expected_token:
                    assert collector.headers.get("X-Auth-Token") == expected_token
                else:
                    assert "X-Auth-Token" not in collector.headers
