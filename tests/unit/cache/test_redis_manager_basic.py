"""
Redis管理器基础测试
测试RedisManager的核心功能
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cache.redis_manager import CacheKeyManager, RedisManager


@pytest.mark.unit
class TestRedisManager:
    """RedisManager测试"""

    @pytest.fixture
    def redis_manager(self):
        """创建Redis管理器实例"""
        manager = RedisManager()
        manager.logger = MagicMock()
        # 初始化客户端
        manager._init_sync_pool = MagicMock()
        manager._sync_client = MagicMock()
        manager._async_client = MagicMock()
        return manager

    # === 初始化测试 ===

    def test_redis_manager_initialization(self, redis_manager):
        """测试Redis管理器初始化"""
        assert redis_manager.logger is not None
        # RedisManager 在初始化时客户端为 None，需要在使用时初始化
        assert redis_manager._sync_client is not None  # fixture 中设置的 mock

    # === CacheKeyManager测试 ===

    def test_cache_key_manager_build_key(self):
        """测试构建缓存Key"""
        # 基础Key构建
        key = CacheKeyManager.build_key("match", 123, "features")
        assert "match:123:features" in key

        # 包含额外信息
        key = CacheKeyManager.build_key("team", 1, "stats", type="recent")
        assert "team:1:stats" in key
        assert "recent" in key

    def test_cache_key_manager_get_ttl(self):
        """测试获取TTL"""
        # 已知数据类型的TTL
        ttl = CacheKeyManager.get_ttl("match_info")
        assert ttl == 3600

        # 未知数据类型的默认TTL
        ttl = CacheKeyManager.get_ttl("unknown_type")
        assert ttl == 3600

    # === 连接管理测试 ===

    @pytest.mark.asyncio
    async def test_get_async_client(self, redis_manager):
        """测试获取异步客户端"""
        mock_client = AsyncMock()
        redis_manager._async_client = mock_client

        result = await redis_manager.get_async_client()
        assert result is mock_client

    # === 基础操作测试 ===

    def test_set_sync(self, redis_manager):
        """测试同步设置值"""
        redis_manager._sync_client.setex.return_value = True

        result = redis_manager.set("test_key", "test_value")

        assert result is True
        redis_manager._sync_client.setex.assert_called_once()

    def test_get_sync(self, redis_manager):
        """测试同步获取值"""
        redis_manager._sync_client.get.return_value = "test_value"

        result = redis_manager.get("test_key")

        assert result == "test_value"
        redis_manager._sync_client.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_set_async(self, redis_manager):
        """测试异步设置值"""
        mock_client = AsyncMock()
        mock_client.setex.return_value = True
        redis_manager._async_client = mock_client

        result = await redis_manager.aset("test_key", "test_value")

        assert result is True
        mock_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_async(self, redis_manager):
        """测试异步获取值"""
        mock_client = AsyncMock()
        mock_client.get.return_value = "test_value"
        redis_manager._async_client = mock_client

        result = await redis_manager.aget("test_key")

        assert result == "test_value"
        mock_client.get.assert_called_once_with("test_key")

    # === JSON操作测试 ===
    # 注意：RedisManager 的 set/get 方法会自动处理 JSON 序列化/反序列化

    def test_set_json_sync(self, redis_manager):
        """测试同步设置JSON值（通过set方法）"""
        redis_manager._sync_client.setex.return_value = True
        test_data = {"key": "value", "number": 123}

        result = redis_manager.set("test_key", test_data)

        assert result is True
        # 验证数据被序列化为JSON
        call_args = redis_manager._sync_client.setex.call_args[0]
        assert call_args[0] == "test_key"
        assert '"key": "value"' in call_args[2]
        assert '"number": 123' in call_args[2]

    def test_get_json_sync(self, redis_manager):
        """测试同步获取JSON值（通过get方法）"""
        redis_manager._sync_client.get.return_value = b'{"key": "value", "number": 123}'

        result = redis_manager.get("test_key")

        assert result == {"key": "value", "number": 123}
        redis_manager._sync_client.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_set_json_async(self, redis_manager):
        """测试异步设置JSON值（通过aset方法）"""
        mock_client = AsyncMock()
        mock_client.setex.return_value = True
        redis_manager._async_client = mock_client
        test_data = {"key": "value", "number": 123}

        result = await redis_manager.aset("test_key", test_data)

        assert result is True
        call_args = mock_client.setex.call_args[0]
        assert call_args[0] == "test_key"
        assert '"key": "value"' in call_args[2]

    @pytest.mark.asyncio
    async def test_get_json_async(self, redis_manager):
        """测试异步获取JSON值（通过aget方法）"""
        mock_client = AsyncMock()
        mock_client.get.return_value = b'{"key": "value", "number": 123}'
        redis_manager._async_client = mock_client

        result = await redis_manager.aget("test_key")

        assert result == {"key": "value", "number": 123}
        mock_client.get.assert_called_once_with("test_key")

    # === TTL操作测试 ===

    def test_set_with_ttl_sync(self, redis_manager):
        """测试同步设置带TTL的值"""
        redis_manager._sync_client.setex.return_value = True

        result = redis_manager.set("test_key", "test_value", ttl=60)

        assert result is True
        redis_manager._sync_client.setex.assert_called_once_with("test_key", 60, "test_value")

    @pytest.mark.asyncio
    async def test_set_with_ttl_async(self, redis_manager):
        """测试异步设置带TTL的值"""
        mock_client = AsyncMock()
        mock_client.setex.return_value = True
        redis_manager._async_client = mock_client

        result = await redis_manager.aset("test_key", "test_value", ttl=60)

        assert result is True
        mock_client.setex.assert_called_once_with("test_key", 60, "test_value")

    # === 删除操作测试 ===

    def test_delete_sync(self, redis_manager):
        """测试同步删除"""
        redis_manager._sync_client.delete.return_value = 1

        result = redis_manager.delete("test_key")

        assert result == 1
        redis_manager._sync_client.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_delete_async(self, redis_manager):
        """测试异步删除"""
        mock_client = AsyncMock()
        mock_client.delete.return_value = 1
        redis_manager._async_client = mock_client

        result = await redis_manager.adelete("test_key")

        assert result == 1
        mock_client.delete.assert_called_once_with("test_key")

    # === 键存在性测试 ===

    def test_exists_sync(self, redis_manager):
        """测试同步检查键存在"""
        redis_manager._sync_client.exists.return_value = 1

        result = redis_manager.exists("test_key")

        assert result == 1
        redis_manager._sync_client.exists.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_exists_async(self, redis_manager):
        """测试异步检查键存在"""
        redis_manager._async_client.exists.return_value = 1

        result = await redis_manager.aexists("test_key")

        assert result is True
        redis_manager._async_client.exists.assert_called_once_with("test_key")

    # === 过期时间测试 ===

    def test_expire_sync(self, redis_manager):
        """测试同步设置过期时间"""
        redis_manager._sync_client.expire.return_value = True

        result = redis_manager.expire("test_key", 60)

        assert result is True
        redis_manager._sync_client.expire.assert_called_once_with("test_key", 60)

    @pytest.mark.asyncio
    async def test_expire_async(self, redis_manager):
        """测试异步设置过期时间"""
        redis_manager._async_client.expire.return_value = True

        result = await redis_manager.aexpire("test_key", 60)

        assert result is True
        redis_manager._async_client.expire.assert_called_once_with("test_key", 60)

    # === 键模式操作测试 ===

    def test_keys_sync(self, redis_manager):
        """测试同步获取键列表"""
        redis_manager._sync_client.keys.return_value = ["key1", "key2", "key3"]

        result = redis_manager.keys("pattern*")

        assert result == ["key1", "key2", "key3"]
        redis_manager._sync_client.keys.assert_called_once_with("pattern*")

    @pytest.mark.asyncio
    async def test_keys_async(self, redis_manager):
        """测试异步获取键列表"""
        redis_manager._async_client.keys.return_value = ["key1", "key2", "key3"]

        result = await redis_manager.akeys("pattern*")

        assert result == ["key1", "key2", "key3"]
        redis_manager._async_client.keys.assert_called_once_with("pattern*")

    # === 错误处理测试 ===

    def test_handle_connection_error(self, redis_manager):
        """测试处理连接错误"""
        redis_manager._sync_client.get.side_effect = Exception("Connection lost")

        result = redis_manager.get("test_key")

        assert result is None
        redis_manager.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_handle_async_connection_error(self, redis_manager):
        """测试处理异步连接错误"""
        redis_manager._async_client.get.side_effect = Exception("Connection lost")

        result = await redis_manager.aget("test_key")

        assert result is None
        redis_manager.logger.error.assert_called()

    # === 健康检查测试 ===

    def test_health_check_healthy(self, redis_manager):
        """测试健康检查 - 健康"""
        redis_manager._sync_client.ping.return_value = True

        health = redis_manager.health_check()

        assert health["status"] == "healthy"
        assert health["sync_client"] is True

    @pytest.mark.asyncio
    async def test_health_check_async_healthy(self, redis_manager):
        """测试健康检查 - 异步健康"""
        redis_manager._sync_client.ping.return_value = True
        redis_manager._async_client.ping.return_value = True

        health = redis_manager.health_check()

        assert health["status"] == "healthy"
        assert health["sync_client"] is True
        assert health["async_client"] is True

    def test_health_check_unhealthy(self, redis_manager):
        """测试健康检查 - 不健康"""
        redis_manager._sync_client.ping.side_effect = Exception("Ping failed")

        health = redis_manager.health_check()

        assert health["status"] == "unhealthy"
        assert health["sync_client"] is False

    # === 关闭测试 ===

    def test_close_sync(self, redis_manager):
        """测试同步关闭"""
        redis_manager._sync_client.close = MagicMock()

        redis_manager.close()

        redis_manager._sync_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_async(self, redis_manager):
        """测试异步关闭"""
        redis_manager._async_client.close = AsyncMock()

        await redis_manager.aclose()

        redis_manager._async_client.close.assert_called_once()

    # === 统计信息测试 ===

    def test_get_stats(self, redis_manager):
        """测试获取统计信息"""
        mock_stats = {
            "connected_clients": 1,
            "used_memory": 1024,
            "keyspace_hits": 100,
            "keyspace_misses": 10,
        }
        redis_manager._sync_client.info.return_value = mock_stats

        stats = redis_manager.get_stats()

        assert stats["connected_clients"] == 1
        assert stats["used_memory"] == 1024
        redis_manager._sync_client.info.assert_called_once()

    # === 上下文管理器测试 ===

    def test_context_manager_sync(self, redis_manager):
        """测试同步上下文管理器"""
        with patch.object(redis_manager, "close") as mock_close:
            with redis_manager:
                pass
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_async(self, redis_manager):
        """测试异步上下文管理器"""
        with patch.object(redis_manager, "aclose") as mock_close:
            async with redis_manager:
                pass
            mock_close.assert_called_once()
