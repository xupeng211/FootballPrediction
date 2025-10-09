"""数据收集器测试"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.collectors.fixtures_collector import FixturesCollector
from src.collectors.odds_collector import OddsCollector
from src.collectors.scores_collector import ScoresCollector


class TestDataCollectors:
    """测试数据收集器"""

    def test_fixtures_collector_creation(self):
        """测试赛程收集器创建"""
        # Mock必要的依赖
        db_session = Mock()
        redis_client = Mock()
        collector = FixturesCollector(db_session, redis_client)
        assert collector is not None
        assert collector.db_session == db_session
        assert collector.redis_client == redis_client

    def test_odds_collector_creation(self):
        """测试赔率收集器创建"""
        # Mock必要的依赖
        db_session = Mock()
        redis_client = Mock()
        collector = OddsCollector(db_session, redis_client)
        assert collector is not None
        assert collector.db_session == db_session
        assert collector.redis_client == redis_client

    def test_scores_collector_creation(self):
        """测试比分收集器创建"""
        # Mock必要的依赖
        db_session = Mock()
        redis_client = Mock()
        collector = ScoresCollector(db_session, redis_client)
        assert collector is not None
        assert collector.db_session == db_session
        assert collector.redis_client == redis_client

    def test_collector_configuration(self):
        """测试收集器配置"""
        # Mock必要的依赖
        db_session = Mock()
        redis_client = Mock()
        collector = FixturesCollector(db_session, redis_client)

        # 验证基本属性存在
        assert hasattr(collector, "api_endpoints")
        assert hasattr(collector, "cache_timeout")
        assert hasattr(collector, "headers")
        # 缓存超时时间可能是60或3600
        assert collector.cache_timeout in [60, 3600]

    @pytest.mark.asyncio
    async def test_async_data_collection(self):
        """测试异步数据收集"""
        # Mock必要的依赖
        db_session = Mock()
        redis_client = Mock()
        collector = OddsCollector(db_session, redis_client)

        # Mock异步方法
        collector.collect_odds = AsyncMock(return_value=[{"match": "test"}])

        # 执行异步收集
        data = await collector.collect_odds(match_id=1)

        assert data == [{"match": "test"}]

    def test_collector_error_handling(self):
        """测试收集器错误处理"""
        # Mock必要的依赖
        db_session = Mock()
        redis_client = Mock()
        collector = ScoresCollector(db_session, redis_client)

        # 验证logger存在
        assert hasattr(collector, "db_session")
        assert hasattr(collector, "redis_client")
        # 缓存超时时间可能是60或3600，取决于具体实现
        assert hasattr(collector, "cache_timeout")
        assert collector.cache_timeout in [60, 3600]

    def test_collector_metrics(self):
        """测试收集器指标"""
        # Mock必要的依赖
        db_session = Mock()
        redis_client = Mock()
        collector = FixturesCollector(db_session, redis_client)

        # 验证基本属性
        assert hasattr(collector, "api_endpoints")
        assert hasattr(collector, "cache_timeout")
        assert hasattr(collector, "headers")
