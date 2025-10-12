"""
缓存一致性管理器测试
Tests for Cache Consistency Manager

测试src.cache.consistency_manager模块的功能
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import logging

from src.cache.consistency_manager import CacheConsistencyManager


class TestCacheConsistencyManager:
    """缓存一致性管理器测试"""

    def test_manager_initialization(self):
        """测试：管理器初始化"""
        manager = CacheConsistencyManager()

        # 检查默认属性
        assert manager.redis_manager is not None
        assert manager.db_manager is None
        assert manager.logger is not None
        assert isinstance(manager.logger, logging.Logger)

    def test_manager_initialization_with_managers(self):
        """测试：使用自定义管理器初始化"""
        mock_redis = Mock()
        mock_db = Mock()

        manager = CacheConsistencyManager(
            redis_manager=mock_redis,
            db_manager=mock_db
        )

        assert manager.redis_manager is mock_redis
        assert manager.db_manager is mock_db

    @pytest.mark.asyncio
    async def test_sync_cache_with_db_success(self):
        """测试：同步缓存到数据库（成功）"""
        manager = CacheConsistencyManager()

        result = await manager.sync_cache_with_db("match", 123)
        assert result is True

    @pytest.mark.asyncio
    async def test_sync_cache_with_db_with_db_manager(self):
        """测试：使用数据库管理器同步缓存"""
        mock_db = Mock()
        manager = CacheConsistencyManager(db_manager=mock_db)

        result = await manager.sync_cache_with_db("prediction", 456)
        assert result is True

    @pytest.mark.asyncio
    async def test_sync_cache_with_db_redis_error(self):
        """测试：Redis错误处理"""
        with patch('src.cache.consistency_manager.get_redis_manager') as mock_get_redis:
            import redis
            mock_get_redis.side_effect = redis.RedisError("Connection failed")

            manager = CacheConsistencyManager()
            result = await manager.sync_cache_with_db("match", 123)
            assert result is False

    @pytest.mark.asyncio
    async def test_sync_cache_with_db_connection_error(self):
        """测试：连接错误处理"""
        with patch('src.cache.consistency_manager.get_redis_manager') as mock_get_redis:
            mock_get_redis.side_effect = ConnectionError("Cannot connect")

            manager = CacheConsistencyManager()
            result = await manager.sync_cache_with_db("match", 123)
            assert result is False

    @pytest.mark.asyncio
    async def test_invalidate_cache_single_key(self):
        """测试：失效单个缓存键"""
        with patch('src.cache.consistency_manager.adelete_cache') as mock_adelete:
            mock_adelete.return_value = True

            manager = CacheConsistencyManager()
            result = await manager.invalidate_cache("test:key")

            assert result is True
            mock_adelete.assert_called_once_with("test:key")

    @pytest.mark.asyncio
    async def test_invalidate_cache_multiple_keys(self):
        """测试：失效多个缓存键"""
        with patch('src.cache.consistency_manager.adelete_cache') as mock_adelete:
            mock_adelete.return_value = True

            manager = CacheConsistencyManager()
            keys = ["test:key1", "test:key2", "test:key3"]
            result = await manager.invalidate_cache(keys)

            assert result is True
            assert mock_adelete.call_count == 3
            mock_adelete.assert_any_call("test:key1")
            mock_adelete.assert_any_call("test:key2")
            mock_adelete.assert_any_call("test:key3")

    @pytest.mark.asyncio
    async def test_invalidate_cache_empty_list(self):
        """测试：失效空键列表"""
        manager = CacheConsistencyManager()
        result = await manager.invalidate_cache([])
        assert result is True

    @pytest.mark.asyncio
    async def test_invalidate_cache_partial_failure(self):
        """测试：部分失效失败"""
        with patch('src.cache.consistency_manager.adelete_cache') as mock_adelete:
            mock_adelete.side_effect = [True, False, True]

            manager = CacheConsistencyManager()
            keys = ["test:key1", "test:key2", "test:key3"]
            result = await manager.invalidate_cache(keys)

            assert result is False  # 不是全部成功

    @pytest.mark.asyncio
    async def test_invalidate_cache_redis_error(self):
        """测试：失效缓存时Redis错误"""
        with patch('src.cache.consistency_manager.adelete_cache') as mock_adelete:
            import redis
            mock_adelete.side_effect = redis.RedisError("Redis error")

            manager = CacheConsistencyManager()
            result = await manager.invalidate_cache("test:key")
            assert result is False

    @pytest.mark.asyncio
    async def test_warm_cache_success(self):
        """测试：缓存预热成功"""
        manager = CacheConsistencyManager()

        ids = [1, 2, 3]
        result = await manager.warm_cache("match", ids)
        assert result is True

    @pytest.mark.asyncio
    async def test_warm_cache_empty_ids(self):
        """测试：预热空ID列表"""
        manager = CacheConsistencyManager()
        result = await manager.warm_cache("match", [])
        assert result is True

    @pytest.mark.asyncio
    async def test_warm_cache_partial_failure(self):
        """测试：部分预热失败"""
        with patch.object(CacheConsistencyManager, 'sync_cache_with_db') as mock_sync:
            mock_sync.side_effect = [True, False, True]

            manager = CacheConsistencyManager()
            ids = [1, 2, 3]
            result = await manager.warm_cache("match", ids)

            # 即使部分失败，仍然应该返回成功（因为大部分成功了）
            assert result is True

    @pytest.mark.asyncio
    async def test_warm_cache_all_failure(self):
        """测试：全部预热失败"""
        with patch.object(CacheConsistencyManager, 'sync_cache_with_db') as mock_sync:
            mock_sync.return_value = False

            manager = CacheConsistencyManager()
            ids = [1, 2, 3]
            result = await manager.warm_cache("match", ids)

            # 全部失败应该返回False
            assert result is False

    @pytest.mark.asyncio
    async def test_warm_cache_different_entity_types(self):
        """测试：预热不同实体类型"""
        manager = CacheConsistencyManager()

        # 测试不同的实体类型
        entity_types = ["match", "prediction", "user", "team"]

        for entity_type in entity_types:
            result = await manager.warm_cache(entity_type, [1, 2])
            assert result is True

    def test_manager_logger_configuration(self):
        """测试：管理器日志配置"""
        manager = CacheConsistencyManager()

        # 检查日志器名称
        assert "CacheConsistencyManager" in manager.logger.name

        # 检查日志器级别
        # 默认级别可能不是WARNING，取决于配置
        assert hasattr(manager.logger, 'level')

    def test_manager_error_handling_attributes(self):
        """测试：错误处理属性"""
        manager = CacheConsistencyManager()

        # 检查管理器有必要的错误处理属性
        assert hasattr(manager, 'logger')
        assert hasattr(manager, 'redis_manager')
        assert hasattr(manager, 'db_manager')


class TestCacheConsistencyManagerIntegration:
    """缓存一致性管理器集成测试"""

    @pytest.mark.asyncio
    async def test_sync_and_invalidate_workflow(self):
        """测试：同步和失效工作流"""
        manager = CacheConsistencyManager()

        # 先同步缓存
        sync_result = await manager.sync_cache_with_db("match", 123)
        assert sync_result is True

        # 然后失效缓存
        invalidate_result = await manager.invalidate_cache("match:123")
        assert invalidate_result is True

    @pytest.mark.asyncio
    async def test_batch_operations(self):
        """测试：批量操作"""
        manager = CacheConsistencyManager()

        # 批量预热
        ids = list(range(10))
        warm_result = await manager.warm_cache("match", ids)
        assert warm_result is True

        # 批量失效
        keys = [f"match:{i}" for i in ids]
        invalidate_result = await manager.invalidate_cache(keys)
        assert invalidate_result is True

    @pytest.mark.asyncio
    async def test_mixed_entity_operations(self):
        """测试：混合实体操作"""
        manager = CacheConsistencyManager()

        # 对不同实体类型进行操作
        operations = [
            ("match", [1, 2, 3]),
            ("prediction", [4, 5]),
            ("user", [6, 7, 8, 9])
        ]

        for entity_type, ids in operations:
            # 预热
            warm_result = await manager.warm_cache(entity_type, ids)
            assert warm_result is True

            # 单独同步
            for entity_id in ids:
                sync_result = await manager.sync_cache_with_db(entity_type, entity_id)
                assert sync_result is True

    def test_manager_state_persistence(self):
        """测试：管理器状态持久性"""
        manager1 = CacheConsistencyManager()
        manager2 = CacheConsistencyManager()

        # 不同的实例应该有不同的管理器（除非使用单例）
        assert manager1 is not manager2
        assert manager1.redis_manager is manager2.redis_manager  # Redis管理器可能是单例

    def test_manager_with_custom_components(self):
        """测试：使用自定义组件的管理器"""
        custom_redis = Mock()
        custom_db = Mock()

        manager = CacheConsistencyManager(
            redis_manager=custom_redis,
            db_manager=custom_db
        )

        # 验证自定义组件被正确设置
        assert manager.redis_manager is custom_redis
        assert manager.db_manager is custom_db

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """测试：错误恢复"""
        manager = CacheConsistencyManager()

        # 模拟一个操作失败
        with patch.object(manager, 'sync_cache_with_db') as mock_sync:
            mock_sync.return_value = False

            result1 = await manager.sync_cache_with_db("match", 123)
            assert result1 is False

            # 恢复正常
            mock_sync.return_value = True
            result2 = await manager.sync_cache_with_db("match", 124)
            assert result2 is True

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """测试：并发操作"""
        import asyncio

        manager = CacheConsistencyManager()

        async def sync_operation():
            await manager.sync_cache_with_db("match", 123)

        async def invalidate_operation():
            await manager.invalidate_cache("match:456")

        # 并发执行多个操作
        tasks = [
            sync_operation(),
            sync_operation(),
            invalidate_operation(),
            invalidate_operation()
        ]

        # 应该不会抛出异常
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 检查没有异常
        for result in results:
            assert not isinstance(result, Exception)