"""
Redis管理器真实实现测试
基于实际的RedisManager实现创建测试
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.cache.redis_manager import RedisManager, CacheKeyManager


@pytest.mark.unit
class TestCacheKeyManager:
    """CacheKeyManager测试"""

    def test_build_key(self):
        """测试构建缓存Key"""
        # 基础Key构建
        key = CacheKeyManager.build_key("match", 123, "features")
        assert key == "match:123:features"

        # 包含额外信息
        key = CacheKeyManager.build_key("team", 1, "stats", type="recent")
        assert key == "team:1:stats:recent"

    def test_get_ttl(self):
        """测试获取TTL"""
        # 已知数据类型的TTL
        ttl = CacheKeyManager.get_ttl("match_info")
        assert ttl == 3600

        # 未知数据类型的默认TTL
        ttl = CacheKeyManager.get_ttl("unknown_type")
        assert ttl == 3600

    def test_static_key_methods(self):
        """测试静态Key方法"""
        # 比赛特征Key
        key = CacheKeyManager.match_features_key(123)
        assert key == "match:123:features"

        # 球队统计Key
        key = CacheKeyManager.team_stats_key(1, "recent")
        assert key == "team:1:stats:recent"

        # 赔率Key
        key = CacheKeyManager.odds_key(123, "all")
        assert key == "odds:123:all"

        # 预测结果Key
        key = CacheKeyManager.prediction_key(123, "latest")
        assert key == "predictions:123:latest"


@pytest.mark.unit
class TestRedisManager:
    """RedisManager测试"""

    @pytest.fixture
    def redis_manager(self):
        """创建Redis管理器实例"""
        # 在测试环境中使用test_redis_host
        with patch.dict("os.environ", {"REDIS_URL": "redis://test-redis:6379/0"}):
            manager = RedisManager()
            manager.logger = MagicMock()
            manager._sync_client = MagicMock()
            manager._async_client = MagicMock()
            return manager

    # === 初始化测试 ===

    def test_redis_manager_initialization(self, redis_manager):
        """测试Redis管理器初始化"""
        assert redis_manager.redis_url is not None
        assert redis_manager.max_connections == 50
        assert redis_manager.socket_timeout == 3.0
        assert redis_manager._sync_client is not None
        assert redis_manager._async_client is not None

    # === 同步操作测试 ===

    def test_get_sync(self, redis_manager):
        """测试同步获取值"""
        redis_manager._sync_client.get.return_value = b'"test_value"'

        result = redis_manager.get("test_key")

        assert result == "test_value"
        redis_manager._sync_client.get.assert_called_once_with("test_key")

    def test_get_sync_raw_string(self, redis_manager):
        """测试同步获取原始字符串"""
        redis_manager._sync_client.get.return_value = b"raw_string"

        result = redis_manager.get("test_key")

        assert result == "raw_string"

    def test_get_sync_not_found(self, redis_manager):
        """测试同步获取不存在的值"""
        redis_manager._sync_client.get.return_value = None

        result = redis_manager.get("test_key", default="default")

        assert result == "default"

    def test_get_sync_no_client(self, redis_manager):
        """测试同步获取值（无客户端）"""
        redis_manager._sync_client = None

        result = redis_manager.get("test_key", default="default")

        assert result == "default"

    def test_set_sync(self, redis_manager):
        """测试同步设置值"""
        redis_manager._sync_client.setex.return_value = True

        result = redis_manager.set("test_key", "test_value")

        assert result is True
        call_args = redis_manager._sync_client.setex.call_args[0]
        assert call_args[0] == "test_key"
        assert call_args[1] == 3600  # 默认TTL
        assert call_args[2] == "test_value"

    def test_set_sync_with_ttl(self, redis_manager):
        """测试同步设置带TTL的值"""
        redis_manager._sync_client.setex.return_value = True

        result = redis_manager.set("test_key", "test_value", ttl=60)

        assert result is True
        call_args = redis_manager._sync_client.setex.call_args[0]
        assert call_args[1] == 60

    def test_set_sync_with_cache_type(self, redis_manager):
        """测试同步设置值（带缓存类型）"""
        redis_manager._sync_client.setex.return_value = True

        result = redis_manager.set("test_key", "test_value", cache_type="match_info")

        assert result is True
        call_args = redis_manager._sync_client.setex.call_args[0]
        assert call_args[1] == 3600  # match_info的TTL

    def test_set_sync_json_dict(self, redis_manager):
        """测试同步设置JSON字典"""
        redis_manager._sync_client.setex.return_value = True
        test_data = {"key": "value", "number": 123}

        result = redis_manager.set("test_key", test_data)

        assert result is True
        call_args = redis_manager._sync_client.setex.call_args[0]
        assert '"key": "value"' in call_args[2]
        assert '"number": 123' in call_args[2]

    def test_set_sync_no_client(self, redis_manager):
        """测试同步设置值（无客户端）"""
        redis_manager._sync_client = None

        result = redis_manager.set("test_key", "test_value")

        assert result is False

    def test_delete_sync(self, redis_manager):
        """测试同步删除"""
        redis_manager._sync_client.delete.return_value = 1

        result = redis_manager.delete("test_key")

        assert result == 1
        redis_manager._sync_client.delete.assert_called_once_with("test_key")

    def test_delete_sync_multiple(self, redis_manager):
        """测试同步删除多个键"""
        redis_manager._sync_client.delete.return_value = 2

        result = redis_manager.delete("key1", "key2")

        assert result == 2
        redis_manager._sync_client.delete.assert_called_once_with("key1", "key2")

    def test_delete_sync_no_keys(self, redis_manager):
        """测试同步删除（无键）"""
        result = redis_manager.delete()

        assert result == 0

    def test_delete_sync_no_client(self, redis_manager):
        """测试同步删除（无客户端）"""
        redis_manager._sync_client = None

        result = redis_manager.delete("test_key")

        assert result == 0

    def test_exists_sync(self, redis_manager):
        """测试同步检查键存在"""
        redis_manager._sync_client.exists.return_value = 1

        result = redis_manager.exists("test_key")

        assert result == 1
        redis_manager._sync_client.exists.assert_called_once_with("test_key")

    def test_exists_sync_multiple(self, redis_manager):
        """测试同步检查多个键存在"""
        redis_manager._sync_client.exists.return_value = 2

        result = redis_manager.exists("key1", "key2")

        assert result == 2
        redis_manager._sync_client.exists.assert_called_once_with("key1", "key2")

    def test_exists_sync_no_keys(self, redis_manager):
        """测试同步检查键存在（无键）"""
        result = redis_manager.exists()

        assert result == 0

    def test_exists_sync_no_client(self, redis_manager):
        """测试同步检查键存在（无客户端）"""
        redis_manager._sync_client = None

        result = redis_manager.exists("test_key")

        assert result == 0

    def test_ttl_sync(self, redis_manager):
        """测试同步获取TTL"""
        redis_manager._sync_client.ttl.return_value = 60

        result = redis_manager.ttl("test_key")

        assert result == 60
        redis_manager._sync_client.ttl.assert_called_once_with("test_key")

    def test_ttl_sync_not_exists(self, redis_manager):
        """测试同步获取TTL（键不存在）"""
        redis_manager._sync_client.ttl.return_value = -2

        result = redis_manager.ttl("test_key")

        assert result == -2

    def test_ttl_sync_no_client(self, redis_manager):
        """测试同步获取TTL（无客户端）"""
        redis_manager._sync_client = None

        result = redis_manager.ttl("test_key")

        assert result == -2

    # === 异步操作测试 ===

    @pytest.mark.asyncio
    async def test_get_async(self, redis_manager):
        """测试异步获取值"""
        redis_manager._async_client.get.return_value = b'"test_value"'

        result = await redis_manager.aget("test_key")

        assert result == "test_value"
        redis_manager._async_client.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_async_not_found(self, redis_manager):
        """测试异步获取不存在的值"""
        redis_manager._async_client.get.return_value = None

        result = await redis_manager.aget("test_key", default="default")

        assert result == "default"

    @pytest.mark.asyncio
    async def test_get_async_no_client(self, redis_manager):
        """测试异步获取值（无客户端）"""
        redis_manager._async_client = None

        result = await redis_manager.aget("test_key", default="default")

        assert result == "default"

    @pytest.mark.asyncio
    async def test_set_async(self, redis_manager):
        """测试异步设置值"""
        redis_manager._async_client.setex.return_value = True

        result = await redis_manager.aset("test_key", "test_value")

        assert result is True
        call_args = redis_manager._async_client.setex.call_args[0]
        assert call_args[0] == "test_key"
        assert call_args[1] == 3600  # 默认TTL
        assert call_args[2] == "test_value"

    @pytest.mark.asyncio
    async def test_set_async_with_ttl(self, redis_manager):
        """测试异步设置带TTL的值"""
        redis_manager._async_client.setex.return_value = True

        result = await redis_manager.aset("test_key", "test_value", ttl=60)

        assert result is True
        call_args = redis_manager._async_client.setex.call_args[0]
        assert call_args[1] == 60

    @pytest.mark.asyncio
    async def test_set_async_json_dict(self, redis_manager):
        """测试异步设置JSON字典"""
        redis_manager._async_client.setex.return_value = True
        test_data = {"key": "value", "number": 123}

        result = await redis_manager.aset("test_key", test_data)

        assert result is True
        call_args = redis_manager._async_client.setex.call_args[0]
        assert '"key": "value"' in call_args[2]
        assert '"number": 123' in call_args[2]

    @pytest.mark.asyncio
    async def test_set_async_no_client(self, redis_manager):
        """测试异步设置值（无客户端）"""
        redis_manager._async_client = None

        result = await redis_manager.aset("test_key", "test_value")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_async(self, redis_manager):
        """测试异步删除"""
        redis_manager._async_client.delete.return_value = 1

        result = await redis_manager.adelete("test_key")

        assert result == 1
        redis_manager._async_client.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_delete_async_no_client(self, redis_manager):
        """测试异步删除（无客户端）"""
        redis_manager._async_client = None

        result = await redis_manager.adelete("test_key")

        assert result == 0

    @pytest.mark.asyncio
    async def test_exists_async(self, redis_manager):
        """测试异步检查键存在"""
        redis_manager._async_client.exists.return_value = 1

        result = await redis_manager.aexists("test_key")

        assert result == 1
        redis_manager._async_client.exists.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_exists_async_no_client(self, redis_manager):
        """测试异步检查键存在（无客户端）"""
        redis_manager._async_client = None

        result = await redis_manager.aexists("test_key")

        assert result == 0

    @pytest.mark.asyncio
    async def test_ttl_async(self, redis_manager):
        """测试异步获取TTL"""
        redis_manager._async_client.ttl.return_value = 60

        result = await redis_manager.attl("test_key")

        assert result == 60
        redis_manager._async_client.ttl.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_ttl_async_no_client(self, redis_manager):
        """测试异步获取TTL（无客户端）"""
        redis_manager._async_client = None

        result = await redis_manager.attl("test_key")

        assert result == -2

    # === 属性测试 ===

    def test_sync_client_property(self, redis_manager):
        """测试同步客户端属性"""
        assert redis_manager.sync_client is redis_manager._sync_client

    @pytest.mark.asyncio
    async def test_get_async_client(self, redis_manager):
        """测试获取异步客户端"""
        # 客户端已存在
        redis_manager._async_client = MagicMock()
        client = await redis_manager.get_async_client()
        assert client is redis_manager._async_client

        # 客户端不存在，需要初始化
        redis_manager._async_client = None
        redis_manager._init_async_pool = AsyncMock()
        redis_manager._async_client = MagicMock()
        redis_manager._init_async_pool.return_value = None
        client = await redis_manager.get_async_client()
        assert client is redis_manager._async_client

    # === 错误处理测试 ===

    def test_get_sync_error(self, redis_manager):
        """测试同步获取值错误处理"""
        import redis

        redis_manager._sync_client.get.side_effect = redis.ConnectionError(
            "Connection lost"
        )

        result = redis_manager.get("test_key", default="default")

        assert result == "default"
        redis_manager.logger.error.assert_called()

    def test_set_sync_error(self, redis_manager):
        """测试同步设置值错误处理"""
        import redis

        redis_manager._sync_client.setex.side_effect = redis.ConnectionError(
            "Connection lost"
        )

        result = redis_manager.set("test_key", "test_value")

        assert result is False
        redis_manager.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_get_async_error(self, redis_manager):
        """测试异步获取值错误处理"""
        import redis

        redis_manager._async_client.get.side_effect = redis.ConnectionError(
            "Connection lost"
        )

        result = await redis_manager.aget("test_key", default="default")

        assert result == "default"
        redis_manager.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_set_async_error(self, redis_manager):
        """测试异步设置值错误处理"""
        import redis

        redis_manager._async_client.setex.side_effect = redis.ConnectionError(
            "Connection lost"
        )

        result = await redis_manager.aset("test_key", "test_value")

        assert result is False
        redis_manager.logger.error.assert_called()

    # === 初始化池测试 ===

    def test_init_sync_pool(self, redis_manager):
        """测试初始化同步连接池"""
        with patch("redis.ConnectionPool.from_url") as mock_pool:
            with patch("redis.Redis") as mock_redis:
                mock_redis_instance = MagicMock()
                mock_redis.return_value = mock_redis_instance

                redis_manager._init_sync_pool()

                assert redis_manager._sync_pool is not None
                assert redis_manager._sync_client is mock_redis_instance
                redis_manager.logger.info.assert_called_with(
                    "同步Redis连接池初始化成功"
                )

    def test_init_sync_pool_error(self, redis_manager):
        """测试初始化同步连接池错误"""
        with patch("redis.ConnectionPool.from_url") as mock_pool:
            mock_pool.side_effect = Exception("Connection failed")

            redis_manager._init_sync_pool()

            assert redis_manager._sync_pool is None
            assert redis_manager._sync_client is None
            redis_manager.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_init_async_pool(self, redis_manager):
        """测试初始化异步连接池"""
        with patch("redis.asyncio.ConnectionPool.from_url") as mock_pool:
            with patch("redis.asyncio.Redis") as mock_redis:
                mock_redis_instance = MagicMock()
                mock_redis.return_value = mock_redis_instance

                await redis_manager._init_async_pool()

                assert redis_manager._async_pool is not None
                assert redis_manager._async_client is mock_redis_instance
                redis_manager.logger.info.assert_called_with(
                    "异步Redis连接池初始化成功"
                )

    @pytest.mark.asyncio
    async def test_init_async_pool_error(self, redis_manager):
        """测试初始化异步连接池错误"""
        with patch("redis.asyncio.ConnectionPool.from_url") as mock_pool:
            mock_pool.side_effect = Exception("Connection failed")

            await redis_manager._init_async_pool()

            assert redis_manager._async_pool is None
            assert redis_manager._async_client is None
            redis_manager.logger.error.assert_called()

    # === 工具方法测试 ===

    def test_mask_password(self, redis_manager):
        """测试隐藏密码"""
        url = "redis://user:password123@localhost:6379/0"
        masked = redis_manager._mask_password(url)
        assert masked == "redis://user:****@localhost:6379/0"

    def test_mask_password_no_password(self, redis_manager):
        """测试隐藏密码（无密码）"""
        url = "redis://localhost:6379/0"
        masked = redis_manager._mask_password(url)
        assert masked == url

    # === 关闭测试 ===

    def test_close(self, redis_manager):
        """测试关闭连接"""
        redis_manager._sync_client = MagicMock()
        redis_manager._async_client = MagicMock()
        redis_manager._sync_pool = MagicMock()
        redis_manager._async_pool = MagicMock()

        # 测试同步客户端有close方法
        redis_manager._sync_client.close = MagicMock()
        redis_manager._async_client.close = MagicMock()
        redis_manager._sync_pool.disconnect = MagicMock()
        redis_manager._async_pool.disconnect = MagicMock()

        redis_manager.close()

        # 验证客户端被置空
        assert redis_manager._sync_client is None
        assert redis_manager._async_client is None
