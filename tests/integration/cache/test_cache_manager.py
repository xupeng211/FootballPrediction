"""
Redis缓存管理器测试模块

测试覆盖：
- Redis连接池管理
- 基础CRUD操作（get / set / delete）
- 批量操作（mget / mset）
- 缓存Key命名规范
- TTL过期策略
- 错误处理和降级
- 健康检查功能

覆盖率目标：>85%
"""

import json
import logging
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

pytestmark = pytest.mark.integration

from redis.exceptions import ConnectionError, RedisError, TimeoutError

from src.cache.redis_manager import (
    CacheKeyManager,
    RedisManager,
    adelete_cache,
    aget_cache,
    aset_cache,
    delete_cache,
    get_cache,
    get_redis_manager,
    set_cache,
)


class TestCacheKeyManager:
    """测试缓存Key管理器"""

    def test_build_key_basic(self):
        """测试基础Key构建"""
        # 基本Key构建
        key = CacheKeyManager.build_key("match", 123, "features")
        assert key == "match:123:features"

        # 带额外参数的Key构建
        key = CacheKeyManager.build_key("team", 1, "stats", type="recent")
        assert key == "team:1:stats:type:recent"

        # 多个额外参数
        key = CacheKeyManager.build_key("odds", 123, bookmaker="bet365", market="1x2")
        assert key == "odds:123:bookmaker:bet365:market:1x2"

    def test_build_key_unknown_prefix(self):
        """测试未知前缀的Key构建"""
        with patch("src.cache.redis_manager.logger") as mock_logger:
            key = CacheKeyManager.build_key("unknown_prefix", 123)
            assert key == "unknown_prefix:123"
            mock_logger.warning.assert_called_once()

    def test_get_ttl(self):
        """测试TTL获取"""
        # 已知缓存类型
        ttl = CacheKeyManager.get_ttl("match_info")
        assert ttl == 1800  # 30分钟

        ttl = CacheKeyManager.get_ttl("team_stats")
        assert ttl == 3600  # 1小时

        ttl = CacheKeyManager.get_ttl("odds_data")
        assert ttl == 300  # 5分钟

        # 未知缓存类型，返回默认TTL
        ttl = CacheKeyManager.get_ttl("unknown_type")
        assert ttl == 1800  # 默认30分钟

    def test_predefined_key_methods(self):
        """测试预定义的Key生成方法"""
        # 比赛特征Key
        key = CacheKeyManager.match_features_key(123)
        assert key == "match:123:features"

        # 球队统计Key
        key = CacheKeyManager.team_stats_key(1, "recent")
        assert key == "team:1:stats:type:recent"

        key = CacheKeyManager.team_stats_key(1)  # 默认类型
        assert key == "team:1:stats:type:recent"

        # 赔率Key
        key = CacheKeyManager.odds_key(123, "bet365")
        assert key == "odds:123:bet365"

        key = CacheKeyManager.odds_key(123)  # 默认博彩商
        assert key == "odds:123:all"

        # 预测结果Key
        key = CacheKeyManager.prediction_key(123, "v2.0")
        assert key == "predictions:123:v2.0"

        key = CacheKeyManager.prediction_key(123)  # 默认版本
        assert key == "predictions:123:latest"


class TestRedisManager:
    """测试Redis管理器"""

    def setup_method(self):
        """测试前设置"""
        # 创建Redis管理器实例
        self.redis_manager = RedisManager(
            redis_url="redis://localhost:6379 / 0",
            max_connections=10,
            socket_timeout=2.0,
        )

    def test_init(self):
        """测试Redis管理器初始化"""
        manager = RedisManager()
        # 使用实际配置的Redis URL，而不是硬编码localhost
        assert manager.redis_url in [
            "redis://localhost:6379/0",
            "redis://redis:6379/0",
            "redis://:redis_pass@localhost:6379/0",
        ]

        assert manager.max_connections == 20
        assert manager.socket_timeout == 5.0

        # 自定义配置
        custom_manager = RedisManager(
            redis_url="redis://custom:6380/1", max_connections=5, socket_timeout=10.0
        )
        assert custom_manager.redis_url == "redis://custom:6380/1"
        assert custom_manager.max_connections == 5
        assert custom_manager.socket_timeout == 10.0

    def test_mask_password(self):
        """测试密码掩码功能"""
        url_with_password = "redis://user:secret123@localhost:6379 / 0"
        masked = self.redis_manager._mask_password(url_with_password)
        assert masked == "redis://user:****@localhost:6379 / 0"

        url_without_password = "redis://localhost:6379 / 0"
        masked = self.redis_manager._mask_password(url_without_password)
        assert masked == "redis://localhost:6379 / 0"

    @patch("redis.ConnectionPool.from_url")
    @patch("redis.Redis")
    def test_init_sync_pool_success(self, mock_redis, mock_pool):
        """测试同步连接池初始化成功"""
        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance

        manager = RedisManager()
        manager._init_sync_pool()

        assert manager._sync_pool == mock_pool_instance
        assert manager._sync_client == mock_redis_instance

    @patch("redis.ConnectionPool.from_url")
    def test_init_sync_pool_failure(self, mock_pool):
        """测试同步连接池初始化失败"""
        mock_pool.side_effect = Exception("Connection failed")

        # 创建一个新的RedisManager实例，这会触发_init_sync_pool
        manager = RedisManager()

        # 验证连接池和客户端都为None
        assert manager._sync_pool is None
        assert manager._sync_client is None

    @pytest.mark.asyncio
    @patch("redis.asyncio.ConnectionPool.from_url")
    @patch("redis.asyncio.Redis")
    async def test_init_async_pool_success(self, mock_redis, mock_pool):
        """测试异步连接池初始化成功"""
        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance
        mock_redis_instance = Mock()
        mock_redis.return_value = mock_redis_instance

        await self.redis_manager._init_async_pool()

        assert self.redis_manager._async_pool == mock_pool_instance
        assert self.redis_manager._async_client == mock_redis_instance

    @pytest.mark.asyncio
    @patch("redis.asyncio.ConnectionPool.from_url")
    async def test_init_async_pool_failure(self, mock_pool):
        """测试异步连接池初始化失败"""
        mock_pool.side_effect = Exception("Async connection failed")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            await self.redis_manager._init_async_pool()

            assert self.redis_manager._async_pool is None
            assert self.redis_manager._async_client is None
            mock_logger.error.assert_called_once()

    def test_sync_client_property(self):
        """测试同步客户端属性"""
        # 模拟客户端存在
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        assert self.redis_manager.sync_client == mock_client

        # 模拟客户端不存在
        self.redis_manager._sync_client = None
        assert self.redis_manager.sync_client is None

    @pytest.mark.asyncio
    async def test_get_async_client(self):
        """测试获取异步客户端"""
        # 模拟客户端已存在
        mock_client = Mock()
        self.redis_manager._async_client = mock_client
        client = await self.redis_manager.get_async_client()
        assert client == mock_client

        # 模拟客户端不存在，需要初始化
        self.redis_manager._async_client = None
        with patch.object(self.redis_manager, "_init_async_pool") as mock_init:
            mock_client_new = Mock()

            async def mock_init_side_effect():
                self.redis_manager._async_client = mock_client_new

            mock_init.side_effect = mock_init_side_effect

            client = await self.redis_manager.get_async_client()
            assert client == mock_client_new
            mock_init.assert_called_once()

    def test_get_success(self):
        """测试同步GET操作成功"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client

        # 测试JSON数据
        test_data = {"key": "value", "number": 123}
        mock_client.get.return_value = json.dumps(test_data)

        result = self.redis_manager.get("test_key")
        assert result == test_data
        mock_client.get.assert_called_once_with("test_key")

    def test_get_string_data(self):
        """测试同步GET操作返回字符串数据"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client

        # 测试普通字符串
        mock_client.get.return_value = b"simple_string"
        result = self.redis_manager.get("test_key")
        assert result == "simple_string"

        # 测试非JSON格式的字符串
        mock_client.get.return_value = "not_json_data"
        result = self.redis_manager.get("test_key")
        assert result == "not_json_data"

    def test_get_not_found(self):
        """测试同步GET操作Key不存在"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.get.return_value = None

        result = self.redis_manager.get("nonexistent_key", default="default_value")
        assert result == "default_value"

    def test_get_no_client(self, caplog):
        """测试同步GET操作客户端未初始化"""
        self.redis_manager._sync_client = None

        with caplog.at_level(logging.WARNING):
            result = self.redis_manager.get("test_key", default="default")
            assert result == "default"

            # 验证warning日志被记录
            assert "同步Redis客户端未初始化" in caplog.text

    def test_get_redis_error(self, caplog):
        """测试同步GET操作Redis错误"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client

        from redis.exceptions import RedisError

        mock_client.get.side_effect = RedisError("Redis connection failed")

        with caplog.at_level(logging.ERROR):
            result = self.redis_manager.get("test_key", default="error_default")
            assert result == "error_default"

            # 验证error日志被记录
            assert "Redis GET操作失败" in caplog.text
            assert "Redis connection failed" in caplog.text

    def test_set_success(self):
        """测试同步SET操作成功"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.setex.return_value = True

        # 测试字典数据
        test_data = {"key": "value", "number": 123}
        result = self.redis_manager.set("test_key", test_data, ttl=3600)

        assert result is True
        mock_client.setex.assert_called_once_with(
            "test_key", 3600, json.dumps(test_data, ensure_ascii=False, default=str)
        )

    def test_set_with_cache_type(self):
        """测试SET操作使用缓存类型TTL"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.setex.return_value = True

        result = self.redis_manager.set("test_key", "value", cache_type="match_info")

        assert result is True
        # 应该使用match_info对应的TTL（1800秒）
        mock_client.setex.assert_called_once_with("test_key", 1800, "value")

    def test_set_string_data(self):
        """测试SET操作字符串数据"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.setex.return_value = True

        result = self.redis_manager.set("test_key", "string_value", ttl=1800)

        assert result is True
        mock_client.setex.assert_called_once_with("test_key", 1800, "string_value")

    def test_set_no_client(self):
        """测试SET操作客户端未初始化"""
        self.redis_manager._sync_client = None

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = self.redis_manager.set("test_key", "value")
            assert result is False
            mock_logger.warning.assert_called_once()

    def test_set_redis_error(self):
        """测试SET操作Redis错误"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client

        mock_client.setex.side_effect = RedisError("Redis set failed")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = self.redis_manager.set("test_key", "value")
            assert result is False
            mock_logger.error.assert_called_once()

    def test_delete_success(self):
        """测试同步DELETE操作成功"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.delete.return_value = 2  # 删除了2个key

        result = self.redis_manager.delete("key1", "key2")
        assert result == 2
        mock_client.delete.assert_called_once_with("key1", "key2")

    def test_delete_no_keys(self):
        """测试DELETE操作无Key"""
        result = self.redis_manager.delete()
        assert result == 0

    def test_delete_no_client(self):
        """测试DELETE操作客户端未初始化"""
        self.redis_manager._sync_client = None

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = self.redis_manager.delete("key1")
            assert result == 0
            mock_logger.warning.assert_called_once()

    def test_exists_success(self):
        """测试EXISTS操作成功"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.exists.return_value = 1

        result = self.redis_manager.exists("key1")
        assert result == 1
        mock_client.exists.assert_called_once_with("key1")

    def test_ttl_success(self):
        """测试TTL操作成功"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.ttl.return_value = 300  # 5分钟

        result = self.redis_manager.ttl("key1")
        assert result == 300
        mock_client.ttl.assert_called_once_with("key1")

    @pytest.mark.asyncio
    async def test_aget_success(self):
        """测试异步GET操作成功"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client

        test_data = {"async": "data"}
        mock_client.get.return_value = json.dumps(test_data)

        result = await self.redis_manager.aget("async_key")
        assert result == test_data
        mock_client.get.assert_called_once_with("async_key")

    @pytest.mark.asyncio
    async def test_aget_no_client(self):
        """测试异步GET操作客户端获取失败"""
        with patch.object(self.redis_manager, "get_async_client", return_value=None):
            with patch("src.cache.redis_manager.logger") as mock_logger:
                result = await self.redis_manager.aget("key", default="default")
                assert result == "default"
                mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_aset_success(self):
        """测试异步SET操作成功"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client
        mock_client.setex.return_value = True

        result = await self.redis_manager.aset("async_key", {"data": "value"}, ttl=1800)
        assert result is True
        mock_client.setex.assert_called_once_with(
            "async_key",
            1800,
            json.dumps({"data": "value"}, ensure_ascii=False, default=str),
        )

    @pytest.mark.asyncio
    async def test_adelete_success(self):
        """测试异步DELETE操作成功"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client
        mock_client.delete.return_value = 1

        result = await self.redis_manager.adelete("async_key")
        assert result == 1
        mock_client.delete.assert_called_once_with("async_key")

    @pytest.mark.asyncio
    async def test_aexists_success(self):
        """测试异步EXISTS操作成功"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client
        mock_client.exists.return_value = 1

        result = await self.redis_manager.aexists("async_key")
        assert result == 1
        mock_client.exists.assert_called_once_with("async_key")

    @pytest.mark.asyncio
    async def test_attl_success(self):
        """测试异步TTL操作成功"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client
        mock_client.ttl.return_value = 600

        result = await self.redis_manager.attl("async_key")
        assert result == 600
        mock_client.ttl.assert_called_once_with("async_key")

    def test_mget_success(self):
        """测试批量GET操作成功"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client

        # 模拟返回混合数据
        mock_client.mget.return_value = [
            json.dumps({"data": 1}),  # JSON数据
            b"string_data",  # 字符串数据
            None,  # 不存在的key
        ]

        result = self.redis_manager.mget(["key1", "key2", "key3"], default="default")
        expected = [{"data": 1}, "string_data", "default"]
        assert result == expected
        mock_client.mget.assert_called_once_with(["key1", "key2", "key3"])

    def test_mget_empty_keys(self):
        """测试批量GET操作空Key列表"""
        result = self.redis_manager.mget([], default="default")
        assert result == []

    def test_mset_success(self):
        """测试批量SET操作成功"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.mset.return_value = True

        # 创建pipeline模拟
        mock_pipeline = Mock()
        mock_client.pipeline.return_value = mock_pipeline
        mock_pipeline.execute.return_value = [True, True]

        mapping = {"key1": {"data": 1}, "key2": "string_data"}

        result = self.redis_manager.mset(mapping, ttl=3600)
        assert result is True

        # 验证序列化后的数据
        expected_mapping = {
            "key1": json.dumps({"data": 1}, ensure_ascii=False, default=str),
            "key2": "string_data",
        }
        mock_client.mset.assert_called_once_with(expected_mapping)

        # 验证TTL设置
        mock_pipeline.expire.assert_any_call("key1", 3600)
        mock_pipeline.expire.assert_any_call("key2", 3600)
        mock_pipeline.execute.assert_called_once()

    def test_mset_no_ttl(self):
        """测试批量SET操作不设置TTL"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.mset.return_value = True

        result = self.redis_manager.mset({"key": "value"})
        assert result is True
        mock_client.mset.assert_called_once()
        # 不应该调用pipeline设置TTL
        mock_client.pipeline.assert_not_called()

    @pytest.mark.asyncio
    async def test_amget_success(self):
        """测试异步批量GET操作成功"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client
        mock_client.mget.return_value = [json.dumps({"async": True}), None]

        result = await self.redis_manager.amget(
            ["key1", "key2"], default="async_default"
        )
        expected = [{"async": True}, "async_default"]
        assert result == expected
        mock_client.mget.assert_called_once_with(["key1", "key2"])

    @pytest.mark.asyncio
    async def test_amset_success(self):
        """测试异步批量SET操作成功（无TTL）"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client
        mock_client.mset.return_value = True

        # 测试不带TTL的情况，避免pipeline复杂性
        result = await self.redis_manager.amset({"async_key": "async_value"})
        assert result is True

        expected_mapping = {"async_key": "async_value"}
        mock_client.mset.assert_called_once_with(expected_mapping)

    def test_ping_success(self):
        """测试同步PING操作成功"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.ping.return_value = True

        result = self.redis_manager.ping()
        assert result is True
        mock_client.ping.assert_called_once()

    def test_ping_no_client(self):
        """测试PING操作客户端未初始化"""
        self.redis_manager._sync_client = None
        result = self.redis_manager.ping()
        assert result is False

    def test_ping_error(self):
        """测试PING操作异常"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.ping.side_effect = Exception("Ping failed")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = self.redis_manager.ping()
            assert result is False
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_aping_success(self):
        """测试异步PING操作成功"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client
        mock_client.ping.return_value = True

        result = await self.redis_manager.aping()
        assert result is True
        mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_aping_no_client(self):
        """测试异步PING操作客户端获取失败"""
        with patch.object(self.redis_manager, "get_async_client", return_value=None):
            result = await self.redis_manager.aping()
            assert result is False

    def test_get_info_success(self):
        """测试获取Redis信息成功"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client

        mock_info = {
            "redis_version": "7.0.0",
            "redis_mode": "standalone",
            "connected_clients": 5,
            "used_memory_human": "1.2M",
            "keyspace_hits": 1000,
            "keyspace_misses": 100,
            "total_commands_processed": 5000,
        }
        mock_client.info.return_value = mock_info

        result = self.redis_manager.get_info()
        expected = {
            "version": "7.0.0",
            "mode": "standalone",
            "connected_clients": 5,
            "used_memory_human": "1.2M",
            "keyspace_hits": 1000,
            "keyspace_misses": 100,
            "total_commands_processed": 5000,
        }
        assert result == expected
        mock_client.info.assert_called_once()

    def test_get_info_no_client(self):
        """测试获取Redis信息客户端未初始化"""
        self.redis_manager._sync_client = None
        result = self.redis_manager.get_info()
        assert result == {}

    def test_get_info_error(self):
        """测试获取Redis信息异常"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.info.side_effect = Exception("Info failed")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = self.redis_manager.get_info()
            assert result == {}
            mock_logger.error.assert_called_once()

    def test_close_success(self):
        """测试关闭同步连接池成功"""
        mock_pool = Mock()
        self.redis_manager._sync_pool = mock_pool
        self.redis_manager._sync_client = Mock()

        with patch("src.cache.redis_manager.logger") as mock_logger:
            self.redis_manager.close()

            mock_pool.disconnect.assert_called_once()
            assert self.redis_manager._sync_pool is None
            assert self.redis_manager._sync_client is None
            mock_logger.info.assert_called_once()

    def test_close_error(self):
        """测试关闭同步连接池异常"""
        mock_pool = Mock()
        mock_pool.disconnect.side_effect = Exception("Close failed")
        self.redis_manager._sync_pool = mock_pool

        with patch("src.cache.redis_manager.logger") as mock_logger:
            self.redis_manager.close()
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_success(self):
        """测试关闭异步连接池成功"""
        mock_client = AsyncMock()
        mock_pool = AsyncMock()
        self.redis_manager._async_client = mock_client
        self.redis_manager._async_pool = mock_pool

        with patch("src.cache.redis_manager.logger") as mock_logger:
            await self.redis_manager.aclose()

            # 根据实际实现，只关闭 pool，不关闭 client
            mock_pool.aclose.assert_called_once()
            assert self.redis_manager._async_pool is None
            mock_logger.info.assert_called_once()

    def test_sync_context_manager(self):
        """测试同步上下文管理器"""
        with self.redis_manager.sync_context() as manager:
            assert manager is self.redis_manager

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """测试异步上下文管理器"""
        async with self.redis_manager.async_context() as manager:
            assert manager is self.redis_manager


class TestGlobalFunctions:
    """测试全局函数和单例模式"""

    def test_get_redis_manager_singleton(self):
        """测试Redis管理器单例模式"""
        # 清理全局实例
        import src.cache.redis_manager

        src.cache.redis_manager._redis_manager = None

        # 获取实例
        manager1 = get_redis_manager()
        manager2 = get_redis_manager()

        # 应该是同一个实例
        assert manager1 is manager2
        assert isinstance(manager1, RedisManager)

    @patch("src.cache.redis_manager.get_redis_manager")
    def test_convenience_functions_sync(self, mock_get_manager):
        """测试便捷函数（同步）"""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        # 测试get_cache
        mock_manager.get.return_value = "cached_value"
        result = get_cache("key", default="default")
        assert result == "cached_value"
        mock_manager.get.assert_called_once_with("key", "default")

        # 测试set_cache
        mock_manager.set.return_value = True
        result = set_cache("key", "value", ttl=3600, cache_type="test")
        assert result is True
        mock_manager.set.assert_called_once_with("key", "value", 3600, "test")

        # 测试delete_cache
        mock_manager.delete.return_value = 1
        result = delete_cache("key1", "key2")
        assert result == 1
        mock_manager.delete.assert_called_once_with("key1", "key2")

    @pytest.mark.asyncio
    @patch("src.cache.redis_manager.get_redis_manager")
    async def test_convenience_functions_async(self, mock_get_manager):
        """测试便捷函数（异步）"""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        # 测试aget_cache
        mock_manager.aget = AsyncMock(return_value="async_cached_value")
        result = await aget_cache("async_key", default="async_default")
        assert result == "async_cached_value"
        mock_manager.aget.assert_called_once_with("async_key", "async_default")

        # 测试aset_cache
        mock_manager.aset = AsyncMock(return_value=True)
        result = await aset_cache(
            "async_key", "async_value", ttl=1800, cache_type="async_test"
        )
        assert result is True
        mock_manager.aset.assert_called_once_with(
            "async_key", "async_value", 1800, "async_test"
        )

        # 测试adelete_cache
        mock_manager.adelete = AsyncMock(return_value=2)
        result = await adelete_cache("async_key1", "async_key2")
        assert result == 2
        mock_manager.adelete.assert_called_once_with("async_key1", "async_key2")


class TestErrorHandling:
    """测试错误处理和边界情况"""

    def setup_method(self):
        """测试前设置"""
        self.redis_manager = RedisManager()

    def test_json_decode_error_handling(self):
        """测试JSON解码错误处理"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client

        # 返回无效JSON
        mock_client.get.return_value = b"invalid_json{"

        result = self.redis_manager.get("test_key", default="default")
        # 应该返回原始字符串而不是抛出异常
        assert result == "invalid_json{"

    def test_various_redis_errors(self):
        """测试各种Redis错误类型"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client

        # 测试不同类型的Redis错误

        errors_to_test = [
            ConnectionError("Connection failed"),
            TimeoutError("Operation timed out"),
            Exception("Generic error"),
        ]

        for error in errors_to_test:
            mock_client.get.side_effect = error
            with patch("src.cache.redis_manager.logger") as mock_logger:
                result = self.redis_manager.get("test_key", default="error_default")
                assert result == "error_default"
                mock_logger.error.assert_called_once()
                mock_logger.reset_mock()

    def test_empty_and_none_values(self):
        """测试空值和None值处理"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client

        # 测试设置None值
        _ = self.redis_manager.set("test_key", None)  # Result for testing
        mock_client.setex.assert_called_with("test_key", 1800, "None")

        # 测试设置空字符串
        _ = self.redis_manager.set("test_key", "")  # Result for testing
        mock_client.setex.assert_called_with("test_key", 1800, "")

        # 测试设置空列表
        _ = self.redis_manager.set("test_key", [])  # Result for testing
        expected_json = json.dumps([], ensure_ascii=False, default=str)
        mock_client.setex.assert_called_with("test_key", 1800, expected_json)


@pytest.mark.integration
class TestRedisManagerIntegration:
    """Redis管理器集成测试（需要实际Redis服务）"""

    def setup_method(self):
        """测试前设置"""
        # 注意：这些测试需要实际的Redis服务运行
        # 在CI / CD中应该使用测试Redis容器
        self.redis_manager = RedisManager(
            redis_url="redis://localhost:6379 / 15"
        )  # 使用测试数据库

    def test_real_redis_operations(self):
        """测试实际Redis操作"""
        # 跳过测试如果Redis不可用
        if not self.redis_manager.ping():
            pytest.skip("Redis不可用，跳过集成测试")

        test_key = "integration_test_key"
        test_value = {"test": "integration", "timestamp": str(datetime.now())}

        try:
            # 测试设置
            success = self.redis_manager.set(test_key, test_value, ttl=60)
            assert success is True

            # 测试获取
            retrieved = self.redis_manager.get(test_key)
            assert retrieved == test_value

            # 测试TTL
            ttl = self.redis_manager.ttl(test_key)
            assert 50 <= ttl <= 60  # TTL应该在这个范围内

            # 测试删除
            deleted = self.redis_manager.delete(test_key)
            assert deleted == 1

            # 验证删除
            result = self.redis_manager.get(test_key)
            assert result is None

        finally:
            # 清理测试数据
            self.redis_manager.delete(test_key)

    @pytest.mark.asyncio
    async def test_real_redis_async_operations(self):
        """测试实际Redis异步操作"""
        if not await self.redis_manager.aping():
            pytest.skip("Redis不可用，跳过异步集成测试")

        test_key = "async_integration_test_key"
        test_value = {"async_test": "integration", "timestamp": str(datetime.now())}

        try:
            # 测试异步设置
            success = await self.redis_manager.aset(test_key, test_value, ttl=60)
            assert success is True

            # 测试异步获取
            retrieved = await self.redis_manager.aget(test_key)
            assert retrieved == test_value

            # 测试异步TTL
            ttl = await self.redis_manager.attl(test_key)
            assert 50 <= ttl <= 60

            # 测试异步删除
            deleted = await self.redis_manager.adelete(test_key)
            assert deleted == 1

        finally:
            # 清理测试数据
            await self.redis_manager.adelete(test_key)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--cov=src.cache", "--cov - report=term - missing"])
