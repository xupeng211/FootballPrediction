"""
consistency_manager.py 测试文件
测试缓存一致性管理器功能
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from src.cache.consistency_manager import CacheConsistencyManager

pytestmark = pytest.mark.unit


class DummyRedis:
    def __init__(self):
        self.deleted = []

    async def adelete(self, *keys):
        self.deleted.extend(keys)


class TestCacheConsistencyManager:
    """测试缓存一致性管理器"""

    def test_init(self):
        """测试初始化"""
        mock_redis = Mock()
        mock_db = Mock()

        manager = CacheConsistencyManager(mock_redis, mock_db)

        assert manager.redis_manager == mock_redis
        assert manager.db_manager == mock_db

    @pytest.mark.asyncio
    async def test_sync_cache_with_db(self):
        """测试数据库同步到缓存"""
        mock_redis = Mock()
        mock_db = Mock()

        manager = CacheConsistencyManager(mock_redis, mock_db)

        # 这个方法目前是placeholder实现，只测试不会抛出异常
        await manager.sync_cache_with_db("match", 123)

        # 如果未来有实现，这里可以添加更多的断言
        assert True

    @pytest.mark.asyncio
    async def test_invalidate_cache(self):
        """测试缓存失效"""
        mock_redis = Mock()
        mock_redis.adelete = AsyncMock()
        mock_db = Mock()

        manager = CacheConsistencyManager(mock_redis, mock_db)

        keys = ["key1", "key2", "key3"]
        await manager.invalidate_cache(keys)

        # 验证Redis的adelete方法被调用
        mock_redis.adelete.assert_called_once_with(*keys)

    @pytest.mark.asyncio
    async def test_invalidate_cache_empty_keys(self):
        """测试空键列表的缓存失效"""
        mock_redis = Mock()
        mock_redis.adelete = AsyncMock()
        mock_db = Mock()

        manager = CacheConsistencyManager(mock_redis, mock_db)

        # 测试空键列表
        await manager.invalidate_cache([])

        # 验证Redis的adelete方法没有被调用
        mock_redis.adelete.assert_not_called()

    @pytest.mark.asyncio
    async def test_warm_cache(self):
        """测试缓存预热"""
        mock_redis = Mock()
        mock_db = Mock()

        manager = CacheConsistencyManager(mock_redis, mock_db)

        # 这个方法目前是placeholder实现，只测试不会抛出异常
        await manager.warm_cache("prediction", [1, 2, 3])

        # 如果未来有实现，这里可以添加更多的断言
        assert True

    def test_class_structure(self):
        """测试类结构"""
        # 检查类是否存在且可以实例化
        assert hasattr(CacheConsistencyManager, '__init__')
        assert hasattr(CacheConsistencyManager, 'sync_cache_with_db')
        assert hasattr(CacheConsistencyManager, 'invalidate_cache')
        assert hasattr(CacheConsistencyManager, 'warm_cache')


async def run_invalidate():
    manager = CacheConsistencyManager(DummyRedis(), None)
    await manager.invalidate_cache(["key1", "key2"])
    return manager


def test_invalidate_cache_event_loop():
    manager = asyncio.run(run_invalidate())
    assert manager.redis_manager.deleted == ["key1", "key2"]
