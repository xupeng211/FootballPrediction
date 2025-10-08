from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from src.cache.redis_manager import CacheKeyManager, RedisManager

"""
Redis管理器测试（修复版）
基于实际实现创建的简化测试
"""


@pytest.mark.unit
class TestCacheKeyManager:
    """CacheKeyManager测试"""

    def test_build_key(self):
        """测试构建缓存Key"""
        # 基础Key构建
        key = CacheKeyManager.build_key("match", 123, "features")
        assert "match:123:features" in key

        # 包含额外信息
        key = CacheKeyManager.build_key("team", 1, "stats", type="recent")
        assert "team:1:stats" in key
        assert "recent" in key

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
        assert "match:123:features" in key

        # 球队统计Key
        key = CacheKeyManager.team_stats_key(1, "recent")
        assert "team:1:stats" in key
        assert "recent" in key

        # 赔率Key
        key = CacheKeyManager.odds_key(123, "all")
        assert "odds:123:all" in key

        # 预测结果Key
        key = CacheKeyManager.prediction_key(123, "latest")
        assert "predictions:123:latest" in key


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

    def test_set_sync_json_dict(self, redis_manager):
        """测试同步设置JSON字典"""
        redis_manager._sync_client.setex.return_value = True
        test_data = {"key": "value", "number": 123}

        result = redis_manager.set("test_key", test_data)

        assert result is True
        call_args = redis_manager._sync_client.setex.call_args[0]
        assert '"key": "value"' in call_args[2]
        assert '"number": 123' in call_args[2]

    def test_delete_sync(self, redis_manager):
        """测试同步删除"""
        redis_manager._sync_client.delete.return_value = 1

        result = redis_manager.delete("test_key")

        assert result == 1
        redis_manager._sync_client.delete.assert_called_once_with("test_key")

    def test_exists_sync(self, redis_manager):
        """测试同步检查键存在"""
        redis_manager._sync_client.exists.return_value = 1

        result = redis_manager.exists("test_key")

        assert result == 1
        redis_manager._sync_client.exists.assert_called_once_with("test_key")

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

    # === 异步操作测试 ===

    @pytest.mark.asyncio
    async def test_get_async(self, redis_manager):
        """测试异步获取值"""
        redis_manager.get_async_client = AsyncMock(
            return_value=redis_manager._async_client
        )
        redis_manager._async_client.get = AsyncMock(return_value=b'"test_value"')

        result = await redis_manager.aget("test_key")

        assert result == "test_value"
        redis_manager._async_client.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_async_not_found(self, redis_manager):
        """测试异步获取不存在的值"""
        redis_manager.get_async_client = AsyncMock(
            return_value=redis_manager._async_client
        )
        redis_manager._async_client.get = AsyncMock(return_value=None)

        result = await redis_manager.aget("test_key", default="default")

        assert result == "default"

    @pytest.mark.asyncio
    async def test_set_async(self, redis_manager):
        """测试异步设置值"""
        redis_manager.get_async_client = AsyncMock(
            return_value=redis_manager._async_client
        )
        redis_manager._async_client.setex = AsyncMock(return_value=True)

        result = await redis_manager.aset("test_key", "test_value")

        assert result is True
        call_args = redis_manager._async_client.setex.call_args[0]
        assert call_args[0] == "test_key"
        assert call_args[1] == 3600  # 默认TTL
        assert call_args[2] == "test_value"

    @pytest.mark.asyncio
    async def test_set_async_with_ttl(self, redis_manager):
        """测试异步设置带TTL的值"""
        redis_manager.get_async_client = AsyncMock(
            return_value=redis_manager._async_client
        )
        redis_manager._async_client.setex = AsyncMock(return_value=True)

        result = await redis_manager.aset("test_key", "test_value", ttl=60)

        assert result is True
        call_args = redis_manager._async_client.setex.call_args[0]
        assert call_args[1] == 60

    @pytest.mark.asyncio
    async def test_set_async_json_dict(self, redis_manager):
        """测试异步设置JSON字典"""
        redis_manager.get_async_client = AsyncMock(
            return_value=redis_manager._async_client
        )
        redis_manager._async_client.setex = AsyncMock(return_value=True)
        test_data = {"key": "value", "number": 123}

        result = await redis_manager.aset("test_key", test_data)

        assert result is True
        call_args = redis_manager._async_client.setex.call_args[0]
        assert '"key": "value"' in call_args[2]
        assert '"number": 123' in call_args[2]

    @pytest.mark.asyncio
    async def test_delete_async(self, redis_manager):
        """测试异步删除"""
        redis_manager.get_async_client = AsyncMock(
            return_value=redis_manager._async_client
        )
        redis_manager._async_client.delete = AsyncMock(return_value=1)

        result = await redis_manager.adelete("test_key")

        assert result == 1
        redis_manager._async_client.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_exists_async(self, redis_manager):
        """测试异步检查键存在"""
        redis_manager.get_async_client = AsyncMock(
            return_value=redis_manager._async_client
        )
        redis_manager._async_client.exists = AsyncMock(return_value=1)

        result = await redis_manager.aexists("test_key")

        assert result == 1
        redis_manager._async_client.exists.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_ttl_async(self, redis_manager):
        """测试异步获取TTL"""
        redis_manager.get_async_client = AsyncMock(
            return_value=redis_manager._async_client
        )
        redis_manager._async_client.ttl = AsyncMock(return_value=60)

        result = await redis_manager.attl("test_key")

        assert result == 60
        redis_manager._async_client.ttl.assert_called_once_with("test_key")

    # === 属性测试 ===

    def test_sync_client_property(self, redis_manager):
        """测试同步客户端属性"""
        assert redis_manager.sync_client is redis_manager._sync_client

    @pytest.mark.asyncio
    async def test_get_async_client_property(self, redis_manager):
        """测试获取异步客户端"""
        # 客户端已存在
        redis_manager._async_client = MagicMock()
        client = await redis_manager.get_async_client()
        assert client is redis_manager._async_client

        # 客户端不存在，需要初始化
        redis_manager._async_client = None
        redis_manager._init_async_pool = AsyncMock()
        redis_manager._init_async_pool.return_value = None
        redis_manager._async_client = MagicMock()
        client = await redis_manager.get_async_client()
        assert client is redis_manager._async_client

    # === 错误处理测试 ===

    def test_get_sync_no_client(self, redis_manager):
        """测试同步获取值（无客户端）"""
        redis_manager._sync_client = None

        result = redis_manager.get("test_key", default="default")

        assert result == "default"

    def test_set_sync_no_client(self, redis_manager):
        """测试同步设置值（无客户端）"""
        redis_manager._sync_client = None

        result = redis_manager.set("test_key", "test_value")

        assert result is False

    def test_delete_sync_no_client(self, redis_manager):
        """测试同步删除（无客户端）"""
        redis_manager._sync_client = None

        result = redis_manager.delete("test_key")

        assert result == 0

    def test_exists_sync_no_client(self, redis_manager):
        """测试同步检查键存在（无客户端）"""
        redis_manager._sync_client = None

        result = redis_manager.exists("test_key")

        assert result == 0

    def test_ttl_sync_no_client(self, redis_manager):
        """测试同步获取TTL（无客户端）"""
        redis_manager._sync_client = None

        result = redis_manager.ttl("test_key")

        assert result == -2

    @pytest.mark.asyncio
    async def test_get_async_no_client(self, redis_manager):
        """测试异步获取值（无客户端）"""
        redis_manager.get_async_client = AsyncMock(return_value=None)

        result = await redis_manager.aget("test_key", default="default")

        assert result == "default"

    @pytest.mark.asyncio
    async def test_set_async_no_client(self, redis_manager):
        """测试异步设置值（无客户端）"""
        redis_manager.get_async_client = AsyncMock(return_value=None)

        result = await redis_manager.aset("test_key", "test_value")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_async_no_client(self, redis_manager):
        """测试异步删除（无客户端）"""
        redis_manager.get_async_client = AsyncMock(return_value=None)

        result = await redis_manager.adelete("test_key")

        assert result == 0

    @pytest.mark.asyncio
    async def test_exists_async_no_client(self, redis_manager):
        """测试异步检查键存在（无客户端）"""
        redis_manager.get_async_client = AsyncMock(return_value=None)

        result = await redis_manager.aexists("test_key")

        assert result == 0

    @pytest.mark.asyncio
    async def test_ttl_async_no_client(self, redis_manager):
        """测试异步获取TTL（无客户端）"""
        redis_manager.get_async_client = AsyncMock(return_value=None)

        result = await redis_manager.attl("test_key")

        assert result == -2

    # === 边界条件测试 ===

    def test_delete_sync_no_keys(self, redis_manager):
        """测试同步删除（无键）"""
        result = redis_manager.delete()

        assert result == 0

    def test_exists_sync_no_keys(self, redis_manager):
        """测试同步检查键存在（无键）"""
        result = redis_manager.exists()

        assert result == 0

    def test_set_sync_list_value(self, redis_manager):
        """测试同步设置列表值"""
        redis_manager._sync_client.setex.return_value = True
        test_list = [1, 2, 3]

        result = redis_manager.set("test_key", test_list)

        assert result is True
        call_args = redis_manager._sync_client.setex.call_args[0]
        assert "[1, 2, 3]" in call_args[2]

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
