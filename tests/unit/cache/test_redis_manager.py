"""
Redis管理器测试
测试Redis连接池、基础操作方法
"""

import json
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
        manager._sync_client = MagicMock()
        manager._async_client = MagicMock()
        return manager

    @pytest.fixture
    def mock_sync_client(self):
        """Mock同步Redis客户端"""
        client = MagicMock()
        client.ping.return_value = True
        client.get.return_value = None
        client.setex.return_value = True
        client.delete.return_value = 1
        client.exists.return_value = 1
        client.expire.return_value = True
        client.keys.return_value = ["key1", "key2"]
        client.info.return_value = {
            "connected_clients": 1,
            "used_memory": 1024,
            "keyspace_hits": 100,
            "keyspace_misses": 10,
        }
        return client

    @pytest.fixture
    def mock_async_client(self):
        """Mock异步Redis客户端"""
        client = AsyncMock()
        client.ping.return_value = True
        client.get.return_value = None
        client.setex.return_value = True
        client.delete.return_value = 1
        client.exists.return_value = 1
        client.expire.return_value = True
        client.keys.return_value = ["key1", "key2"]
        client.info.return_value = {
            "connected_clients": 1,
            "used_memory": 1024,
            "keyspace_hits": 100,
            "keyspace_misses": 10,
        }
        return client

    def test_initialization(self, redis_manager):
        """测试初始化"""
        assert redis_manager.logger is not None
        assert hasattr(redis_manager, "_sync_client")
        assert hasattr(redis_manager, "_async_client")

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

    def test_set_sync(self, redis_manager, mock_sync_client):
        """测试同步设置值"""
        redis_manager._sync_client = mock_sync_client

        # 设置字符串
        result = redis_manager.set("test_key", "test_value")
        assert result is True

        # 设置字典（JSON序列化）
        result = redis_manager.set("test_dict", {"key": "value"})
        assert result is True

    def test_get_sync(self, redis_manager, mock_sync_client):
        """测试同步获取值"""
        redis_manager._sync_client = mock_sync_client

        # 获取字符串
        mock_sync_client.get.return_value = "test_value"
        result = redis_manager.get("test_key")
        assert result == "test_value"

        # 获取JSON数据
        mock_sync_client.get.return_value = b'{"key": "value"}'
        result = redis_manager.get("test_json")
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_set_async(self, redis_manager, mock_async_client):
        """测试异步设置值"""
        redis_manager._async_client = mock_async_client

        result = await redis_manager.aset("test_key", "test_value")
        assert result is True
        mock_async_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_async(self, redis_manager, mock_async_client):
        """测试异步获取值"""
        redis_manager._async_client = mock_async_client

        mock_async_client.get.return_value = "test_value"
        result = await redis_manager.aget("test_key")
        assert result == "test_value"

    def test_set_with_ttl(self, redis_manager, mock_sync_client):
        """测试设置带TTL的值"""
        redis_manager._sync_client = mock_sync_client

        result = redis_manager.set("test_key", "test_value", ttl=60)
        assert result is True
        mock_sync_client.setex.assert_called_once_with("test_key", 60, "test_value")

    def test_delete_sync(self, redis_manager, mock_sync_client):
        """测试同步删除"""
        redis_manager._sync_client = mock_sync_client

        result = redis_manager.delete("test_key")
        assert result == 1

    @pytest.mark.asyncio
    async def test_delete_async(self, redis_manager, mock_async_client):
        """测试异步删除"""
        redis_manager._async_client = mock_async_client

        result = await redis_manager.adelete("test_key")
        assert result == 1

    def test_exists_sync(self, redis_manager, mock_sync_client):
        """测试同步检查键存在"""
        redis_manager._sync_client = mock_sync_client

        result = redis_manager.exists("test_key")
        assert result == 1

    @pytest.mark.asyncio
    async def test_exists_async(self, redis_manager, mock_async_client):
        """测试异步检查键存在"""
        redis_manager._async_client = mock_async_client

        mock_async_client.exists.return_value = 1
        result = await redis_manager.aexists("test_key")
        assert result is True

    def test_expire_sync(self, redis_manager, mock_sync_client):
        """测试同步设置过期时间"""
        redis_manager._sync_client = mock_sync_client

        result = redis_manager.expire("test_key", 60)
        assert result is True

    @pytest.mark.asyncio
    async def test_expire_async(self, redis_manager, mock_async_client):
        """测试异步设置过期时间"""
        redis_manager._async_client = mock_async_client

        result = await redis_manager.aexpire("test_key", 60)
        assert result is True

    def test_keys_sync(self, redis_manager, mock_sync_client):
        """测试同步获取键列表"""
        redis_manager._sync_client = mock_sync_client

        result = redis_manager.keys("pattern*")
        assert result == ["key1", "key2"]

    @pytest.mark.asyncio
    async def test_keys_async(self, redis_manager, mock_async_client):
        """测试异步获取键列表"""
        redis_manager._async_client = mock_async_client

        result = await redis_manager.akeys("pattern*")
        assert result == ["key1", "key2"]

    def test_health_check_healthy(self, redis_manager, mock_sync_client):
        """测试健康检查 - 健康"""
        redis_manager._sync_client = mock_sync_client

        health = redis_manager.health_check()
        assert health["status"] == "healthy"
        assert health["sync_client"] is True

    @pytest.mark.asyncio
    async def test_health_check_async_healthy(
        self, redis_manager, mock_sync_client, mock_async_client
    ):
        """测试健康检查 - 异步健康"""
        redis_manager._sync_client = mock_sync_client
        redis_manager._async_client = mock_async_client

        health = redis_manager.health_check()
        assert health["status"] == "healthy"
        assert health["sync_client"] is True
        assert health["async_client"] is True

    def test_health_check_unhealthy(self, redis_manager, mock_sync_client):
        """测试健康检查 - 不健康"""
        mock_sync_client.ping.side_effect = Exception("Connection failed")
        redis_manager._sync_client = mock_sync_client

        health = redis_manager.health_check()
        assert health["status"] == "unhealthy"
        assert health["sync_client"] is False

    def test_close_sync(self, redis_manager, mock_sync_client):
        """测试同步关闭"""
        redis_manager._sync_client = mock_sync_client
        redis_manager._sync_client.close = MagicMock()

        redis_manager.close()
        redis_manager._sync_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_async(self, redis_manager, mock_async_client):
        """测试异步关闭"""
        redis_manager._async_client = mock_async_client

        await redis_manager.aclose()
        mock_async_client.close.assert_called_once()

    def test_get_stats(self, redis_manager, mock_sync_client):
        """测试获取统计信息"""
        redis_manager._sync_client = mock_sync_client

        stats = redis_manager.get_stats()
        assert stats["connected_clients"] == 1
        assert stats["used_memory"] == 1024

    def test_json_serialization(self, redis_manager, mock_sync_client):
        """测试JSON序列化"""
        redis_manager._sync_client = mock_sync_client
        test_data = {
            "match_id": 12345,
            "teams": ["Team A", "Team B"],
            "score": {"home": 2, "away": 1},
        }

        result = redis_manager.set("test_json", test_data)
        assert result is True

        # 验证JSON被正确序列化
        call_args = mock_sync_client.setex.call_args[0]
        assert json.loads(call_args[2]) == test_data

    def test_json_deserialization(self, redis_manager, mock_sync_client):
        """测试JSON反序列化"""
        redis_manager._sync_client = mock_sync_client
        json_data = b'{"match_id": 12345, "teams": ["Team A", "Team B"]}'
        mock_sync_client.get.return_value = json_data

        result = redis_manager.get("test_json")
        assert isinstance(result, dict)
        assert result["match_id"] == 12345
        assert result["teams"] == ["Team A", "Team B"]

    def test_error_handling_get(self, redis_manager, mock_sync_client):
        """测试获取时的错误处理"""
        mock_sync_client.get.side_effect = Exception("Redis error")
        redis_manager._sync_client = mock_sync_client

        result = redis_manager.get("test_key")
        assert result is None
        redis_manager.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_error_handling_get_async(self, redis_manager, mock_async_client):
        """测试异步获取时的错误处理"""
        mock_async_client.get.side_effect = Exception("Redis error")
        redis_manager._async_client = mock_async_client

        result = await redis_manager.aget("test_key")
        assert result is None
        redis_manager.logger.error.assert_called()

    def test_mget_multiple_keys(self, redis_manager, mock_sync_client):
        """测试批量获取"""
        redis_manager._sync_client = mock_sync_client
        mock_sync_client.mget.return_value = [b'{"id": 1}', b'{"id": 2}', None]

        result = redis_manager.mget(["key1", "key2", "key3"])
        assert len(result) == 3
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
        assert result[2] is None

    def test_mset_multiple_values(self, redis_manager, mock_sync_client):
        """测试批量设置"""
        redis_manager._sync_client = mock_sync_client
        redis_manager._sync_client.mset.return_value = True

        data = {"key1": {"id": 1}, "key2": {"id": 2}, "key3": "string_value"}

        result = redis_manager.mset(data)
        assert result is True
        mock_sync_client.mset.assert_called_once()

    def test_increment(self, redis_manager, mock_sync_client):
        """测试增量操作"""
        redis_manager._sync_client = mock_sync_client
        mock_sync_client.incr.return_value = 5

        result = redis_manager.increment("counter")
        assert result == 5

    def test_decrement(self, redis_manager, mock_sync_client):
        """测试减量操作"""
        redis_manager._sync_client = mock_sync_client
        mock_sync_client.decr.return_value = 3

        result = redis_manager.decrement("counter")
        assert result == 3

    def test_hash_operations(self, redis_manager, mock_sync_client):
        """测试哈希操作"""
        redis_manager._sync_client = mock_sync_client
        mock_sync_client.hset.return_value = 1
        mock_sync_client.hget.return_value = b"value"
        mock_sync_client.hgetall.return_value = {
            b"field1": b"value1",
            b"field2": b"value2",
        }

        # 设置哈希字段
        result = redis_manager.hset("hash_key", "field", "value")
        assert result == 1

        # 获取哈希字段
        result = redis_manager.hget("hash_key", "field")
        assert result == "value"

        # 获取所有哈希字段
        result = redis_manager.hgetall("hash_key")
        assert "field1" in result

    def test_list_operations(self, redis_manager, mock_sync_client):
        """测试列表操作"""
        redis_manager._sync_client = mock_sync_client
        mock_sync_client.lpush.return_value = 1
        mock_sync_client.rpop.return_value = b"item"
        mock_sync_client.llen.return_value = 2

        # 左推入
        result = redis_manager.lpush("list_key", "item")
        assert result == 1

        # 右弹出
        result = redis_manager.rpop("list_key")
        assert result == "item"

        # 获取长度
        result = redis_manager.llen("list_key")
        assert result == 2

    def test_context_manager_sync(self, redis_manager, mock_sync_client):
        """测试同步上下文管理器"""
        redis_manager._sync_client = mock_sync_client
        redis_manager._sync_client.close = MagicMock()

        with patch.object(redis_manager, "close") as mock_close:
            with redis_manager:
                pass
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_async(self, redis_manager, mock_async_client):
        """测试异步上下文管理器"""
        redis_manager._async_client = mock_async_client

        with patch.object(redis_manager, "aclose") as mock_close:
            async with redis_manager:
                pass
            mock_close.assert_called_once()

    def test_cache_key_prefix_validation(self):
        """测试缓存键前缀验证"""
        # 有效前缀
        valid_prefixes = ["match", "team", "odds", "features", "predictions", "stats"]
        for prefix in valid_prefixes:
            key = CacheKeyManager.build_key(prefix, 123)
            assert prefix in key

        # 无效前缀（应该仍然工作但会记录警告）
        key = CacheKeyManager.build_key("invalid", 123)
        assert "invalid:123" in key

    def test_ttl_config_validation(self):
        """测试TTL配置验证"""
        # 所有配置的TTL应该是正整数
        for key, ttl in CacheKeyManager.TTL_CONFIG.items():
            assert isinstance(ttl, int)
            assert ttl > 0
            assert ttl <= 86400  # 不超过24小时

    def test_build_cache_key_with_special_chars(self):
        """测试构建包含特殊字符的缓存键"""
        key = CacheKeyManager.build_key("match", "team-123", "stats:latest")
        assert "match:team-123:stats:latest" in key

    def test_get_ttl_for_data_type(self):
        """测试为不同数据类型获取TTL"""
        test_cases = [
            ("match_info", 3600),
            ("match_features", 7200),
            ("team_stats", 14400),
            ("odds_data", 900),
            ("predictions", 7200),
            ("nonexistent", 3600),  # 默认值
        ]

        for data_type, expected_ttl in test_cases:
            ttl = CacheKeyManager.get_ttl(data_type)
            assert ttl == expected_ttl
