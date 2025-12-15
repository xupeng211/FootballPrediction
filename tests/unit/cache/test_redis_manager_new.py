from typing import Optional

"""
Redis缓存管理器测试
Tests for Redis cache manager module.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock

# 导入被测试模块
from src.cache.redis_manager import (
    RedisManager,
    CacheKeyManager,
    get_redis_manager,
    get_cache,
    set_cache,
    delete_cache,
    exists_cache,
    ttl_cache,
)

# 尝试导入便捷函数
try:
    from src.cache.redis_manager import (
        aget_cache,
        aset_cache,
        adelete_cache,
        aexists_cache,
        attl_cache,
        mget_cache,
        mset_cache,
        amget_cache,
        amset_cache,
    )

    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False


class MockCacheKeyManager:
    """模拟缓存键管理器"""

    def __init__(self, prefix="test"):
        self.prefix = prefix

    def generate_key(self, *parts, version=None):
        """生成缓存键"""
        key = ":".join(str(part) for part in parts)
        if self.prefix:
            key = f"{self.prefix}:{key}"
        if version:
            key = f"{key}:v{version}"
        return key

    def validate_key(self, key):
        """验证键的合法性"""
        return isinstance(key, str) and len(key) > 0

    def normalize_key(self, key):
        """规范化键名"""
        return key.strip().lower()


class MockRedisClient:
    """模拟Redis客户端"""

    def __init__(self):
        self.data = {}
        self.ttls = {}
        self.expired_keys = set()

    def get(self, key):
        """获取值"""
        if key in self.expired_keys:
            return None
        return self.data.get(key)

    def set(self, key, value, ex=None):
        """设置值"""
        self.data[key] = value
        if ex:
            self.ttls[key] = ex
        return True

    def delete(self, key):
        """删除键"""
        self.data.pop(key, None)
        self.ttls.pop(key, None)
        self.expired_keys.discard(key)
        return 1

    def exists(self, key):
        """检查键是否存在"""
        return key not in self.expired_keys and key in self.data

    def ttl(self, key):
        """获取TTL"""
        if key not in self.data:
            return -2
        if key in self.expired_keys:
            return -2
        return self.ttls.get(key, -1)

    def mget(self, keys):
        """批量获取"""
        return [self.get(key) for key in keys]

    def mset(self, mapping):
        """批量设置"""
        for key, value in mapping.items():
            self.set(key, value)
        return True

    def close(self):
        """关闭连接"""
        pass


class MockAsyncRedisClient:
    """模拟异步Redis客户端"""

    def __init__(self):
        self.data = {}
        self.ttls = {}
        self.expired_keys = set()

    async def get(self, key):
        """获取值"""
        if key in self.expired_keys:
            return None
        return self.data.get(key)

    async def set(self, key, value, ex=None):
        """设置值"""
        self.data[key] = value
        if ex:
            self.ttls[key] = ex
        return True

    async def delete(self, key):
        """删除键"""
        self.data.pop(key, None)
        self.ttls.pop(key, None)
        self.expired_keys.discard(key)
        return 1

    async def exists(self, key):
        """检查键是否存在"""
        return key not in self.expired_keys and key in self.data

    async def ttl(self, key):
        """获取TTL"""
        if key not in self.data:
            return -2
        if key in self.expired_keys:
            return -2
        return self.ttls.get(key, -1)

    async def mget(self, keys):
        """批量获取"""
        return [self.get(key) for key in keys]

    async def mset(self, mapping):
        """批量设置"""
        for key, value in mapping.items():
            await self.set(key, value)
        return True

    async def close(self):
        """关闭连接"""
        pass


class TestCacheKeyManager:
    """缓存键管理器测试类"""

    def test_key_manager_initialization(self):
        """测试键管理器初始化"""
        manager = CacheKeyManager()
        assert hasattr(manager, "generate_key")
        assert hasattr(manager, "validate_key")
        assert hasattr(manager, "normalize_key")

    def test_generate_key_simple(self):
        """测试简单键生成"""
        manager = CacheKeyManager()
        key = manager.generate_key("test", "key")
        assert isinstance(key, str)
        assert "test" in key
        assert "key" in key

    def test_generate_key_with_version(self):
        """测试带版本的键生成"""
        manager = CacheKeyManager()
        key = manager.generate_key("test", "key", version=1)
        assert "v1" in key

    def test_validate_key_valid(self):
        """测试有效键验证"""
        manager = CacheKeyManager()
        assert manager.validate_key("valid_key") is True

    def test_validate_key_invalid(self):
        """测试无效键验证"""
        manager = CacheKeyManager()
        assert manager.validate_key("") is False
        assert manager.validate_key(None) is False

    def test_normalize_key(self):
        """测试键规范化"""
        manager = CacheKeyManager()
        key = manager.normalize_key("  Test_Key  ")
        assert "test_key" in key.lower()


class TestRedisManager:
    """Redis管理器测试类"""

    def test_manager_initialization_with_config(self):
        """测试使用配置初始化管理器"""
        from src.cache.redis_enhanced import RedisConfig

        config = RedisConfig(host="localhost", port=6379, db=0)
        manager = RedisManager(config=config, use_mock=True)

        assert manager.config.host == "localhost"
        assert manager.config.port == 6379
        assert manager.config.db == 0
        assert manager.use_mock is True

    def test_manager_initialization_without_config(self):
        """测试不使用配置初始化管理器"""
        manager = RedisManager(use_mock=True)

        assert manager.config is not None
        assert manager.use_mock is True

    def test_manager_auto_detect_mock(self):
        """测试自动检测是否使用模拟"""
        manager = RedisManager()

        # 应该自动检测并使用模拟（因为测试环境可能没有redis）
        assert manager.use_mock is True

    @patch("src.cache.redis_enhanced.REDIS_AVAILABLE", True)
    def test_manager_with_real_redis(self):
        """测试使用真实Redis"""
        manager = RedisManager(use_mock=False)

        assert manager.use_mock is False

    @patch("src.cache.redis_enhanced.REDIS_AVAILABLE", False)
    def test_manager_auto_mock_when_redis_unavailable(self):
        """测试Redis不可用时自动使用模拟"""
        manager = RedisManager()

        assert manager.use_mock is True

    def test_get_sync_client(self):
        """测试获取同步客户端"""
        manager = RedisManager(use_mock=True)

        # 访问同步客户端应该自动创建
        client = manager._sync_client or manager._create_sync_client()
        assert client is not None

    def test_get_async_client(self):
        """测试获取异步客户端"""
        manager = RedisManager(use_mock=True)

        # 创建异步客户端
        client = manager._create_async_client()
        assert client is not None


class TestRedisOperations:
    """Redis操作测试类"""

    @pytest.fixture
    def mock_redis_client(self):
        """模拟Redis客户端fixture"""
        return MockRedisClient()

    def test_set_and_get_cache(self, mock_redis_client):
        """测试设置和获取缓存"""
        # 设置缓存
        result = mock_redis_client.set("test_key", "test_value")
        assert result is True

        # 获取缓存
        value = mock_redis_client.get("test_key")
        assert value == "test_value"

    def test_set_cache_with_ttl(self, mock_redis_client):
        """测试设置带TTL的缓存"""
        result = mock_redis_client.set("test_key", "test_value", ex=60)
        assert result is True

        value = mock_redis_client.get("test_key")
        assert value == "test_value"

        ttl = mock_redis_client.ttl("test_key")
        assert ttl == 60

    def test_get_nonexistent_key(self, mock_redis_client):
        """测试获取不存在的键"""
        value = mock_redis_client.get("nonexistent_key")
        assert value is None

    def test_delete_cache(self, mock_redis_client):
        """测试删除缓存"""
        # 先设置值
        mock_redis_client.set("test_key", "test_value")

        # 删除
        result = mock_redis_client.delete("test_key")
        assert result == 1

        # 验证已删除
        value = mock_redis_client.get("test_key")
        assert value is None

    def test_exists_cache(self, mock_redis_client):
        """测试检查键是否存在"""
        # 不存在的键
        exists = mock_redis_client.exists("nonexistent_key")
        assert exists is False

        # 存在的键
        mock_redis_client.set("test_key", "test_value")
        exists = mock_redis_client.exists("test_key")
        assert exists is True

    def test_ttl_operations(self, mock_redis_client):
        """测试TTL操作"""
        # 不存在的键
        ttl = mock_redis_client.ttl("nonexistent_key")
        assert ttl == -2

        # 没有TTL的键
        mock_redis_client.set("test_key", "test_value")
        ttl = mock_redis_client.ttl("test_key")
        assert ttl == -1

        # 有TTL的键
        mock_redis_client.set("ttl_key", "ttl_value", ex=120)
        ttl = mock_redis_client.ttl("ttl_key")
        assert ttl == 120

    @pytest.fixture
    async def mock_async_redis_client(self):
        """模拟异步Redis客户端fixture"""
        return MockAsyncRedisClient()

    @pytest.mark.asyncio
    async def test_async_set_and_get(self, mock_async_redis_client):
        """测试异步设置和获取"""
        await mock_async_redis_client.set("async_key", "async_value")
        value = await mock_async_redis_client.get("async_key")
        assert value == "async_value"

    @pytest.mark.asyncio
    async def test_async_set_with_ttl(self, mock_async_redis_client):
        """测试异步设置带TTL"""
        await mock_async_redis_client.set("ttl_async_key", "ttl_async_value", ex=30)
        value = await mock_async_redis_client.get("ttl_async_key")
        assert value == "ttl_async_value"

        ttl = await mock_async_redis_client.ttl("ttl_async_key")
        assert ttl == 30

    @pytest.mark.asyncio
    async def test_async_delete(self, mock_async_redis_client):
        """测试异步删除"""
        await mock_async_redis_client.set("delete_key", "delete_value")
        result = await mock_async_redis_client.delete("delete_key")
        assert result == 1

        value = await mock_async_redis_client.get("delete_key")
        assert value is None

    @pytest.mark.asyncio
    async def test_async_exists(self, mock_async_redis_client):
        """测试异步存在检查"""
        exists = await mock_async_redis_client.exists("async_key")
        assert exists is False

        await mock_async_redis_client.set("async_key", "async_value")
        exists = await mock_async_redis_client.exists("async_key")
        assert exists is True


class TestBatchOperations:
    """批量操作测试类"""

    def test_mset_and_mget(self):
        """测试批量设置和获取"""
        client = MockRedisClient()

        # 批量设置
        data = {"key1": "value1", "key2": "value2", "key3": "value3"}
        result = client.mset(data)
        assert result is True

        # 批量获取
        values = client.mget(["key1", "key2", "key3", "key4"])
        assert values == ["value1", "value2", "value3", None]

    @pytest.mark.skipif(not ASYNC_AVAILABLE, reason="Async operations not available")
    @pytest.mark.asyncio
    async def test_async_batch_operations(self):
        """测试异步批量操作"""
        client = MockAsyncRedisClient()

        # 批量设置
        data = {"async_key1": "async_value1", "async_key2": "async_value2"}
        await client.mset(data)

        # 批量获取
        values = await client.mget(["async_key1", "async_key2", "async_key3"])
        assert values == ["async_value1", "async_value2", None]


class TestConvenienceFunctions:
    """便捷函数测试类"""

    def test_get_redis_manager_function(self):
        """测试获取Redis管理器便捷函数"""
        manager = get_redis_manager()
        assert manager is not None
        assert isinstance(manager, RedisManager)

    def test_get_set_delete_exists_functions(self):
        """测试基础便捷函数"""
        # 测试获取不存在的键
        value = get_cache("test_key")
        assert value is None

        # 测试设置键
        result = set_cache("test_key", "test_value", ex=60)
        assert result is True

        # 测试获取键
        value = get_cache("test_key")
        assert value == "test_value"

        # 测试检查键是否存在
        exists = exists_cache("test_key")
        assert exists is True

        # 测试删除键
        result = delete_cache("test_key")
        assert result is True

        # 验证键已删除
        exists = exists_cache("test_key")
        assert exists is False

    def test_ttl_function(self):
        """测试TTL便捷函数"""
        # 设置带TTL的键
        set_cache("ttl_test_key", "ttl_test_value", ex=120)

        # 获取TTL
        ttl = ttl_cache("ttl_test_key")
        assert ttl == 120

        # 清理
        delete_cache("ttl_test_key")


class TestIntegrationScenarios:
    """集成场景测试类"""

    def test_cache_workflow_simulation(self):
        """测试缓存工作流模拟"""
        # 模拟一个完整的缓存使用场景

        # 1. 检查缓存中是否有数据
        cache_key = "user:profile:123"
        cached_data = get_cache(cache_key)

        # 第一次应该没有数据
        assert cached_data is None

        # 2. 模拟从数据库获取数据
        user_data = {"id": 123, "name": "Test User", "email": "test@example.com"}

        # 3. 将数据存入缓存
        set_cache(cache_key, user_data, ex=3600)  # 1小时过期

        # 4. 再次检查缓存
        cached_data = get_cache(cache_key)
        assert cached_data == user_data

        # 5. 验证TTL
        ttl = ttl_cache(cache_key)
        assert 3590 <= ttl <= 3600  # 允许一些时间差

        # 6. 更新数据
        updated_data = {**user_data, "name": "Updated User"}
        set_cache(cache_key, updated_data, ex=3600)

        # 7. 验证更新
        cached_data = get_cache(cache_key)
        assert cached_data["name"] == "Updated User"

        # 8. 清理缓存
        delete_cache(cache_key)
        assert not exists_cache(cache_key)

    def test_multi_key_cache_pattern(self):
        """测试多键缓存模式"""
        # 模拟用户相关缓存模式
        user_id = 456

        keys = [
            f"user:{user_id}:profile",
            f"user:{user_id}:settings",
            f"user:{user_id}:permissions",
        ]

        # 批量设置用户数据
        user_data = {
            keys[0]: {"name": "User 456", "email": "user456@example.com"},
            keys[1]: {"theme": "dark", "notifications": True},
            keys[2]: ["read", "write"],
        }

        for key, value in user_data.items():
            set_cache(key, value, ex=1800)

        # 批量验证数据
        cached_data = {key: get_cache(key) for key in keys}
        assert cached_data == user_data

        # 批量检查存在性
        exists_results = {key: exists_cache(key) for key in keys}
        assert all(exists_results.values())

        # 清理
        for key in keys:
            delete_cache(key)

    def test_cache_with_versioning_pattern(self):
        """测试带版本控制的缓存模式"""
        key_manager = CacheKeyManager(prefix="app")
        base_key = "config"
        version = 2

        # 生成版本化键
        versioned_key = key_manager.generate_key(base_key, version=version)

        # 设置数据
        config_data = {"feature_flags": {"new_ui": True, "beta_mode": False}}
        set_cache(versioned_key, config_data, ex=7200)

        # 验证数据
        cached_data = get_cache(versioned_key)
        assert cached_data == config_data

        # 生成不同版本的键
        old_version_key = key_manager.generate_key(base_key, version=1)
        old_data = {"feature_flags": {"new_ui": False, "beta_mode": False}}
        set_cache(old_version_key, old_data, ex=3600)

        # 验证不同版本的数据是独立的
        assert get_cache(versioned_key) != get_cache(old_version_key)

        # 清理
        delete_cache(versioned_key)
        delete_cache(old_version_key)


class TestErrorHandling:
    """错误处理测试类"""

    def test_invalid_key_handling(self):
        """测试无效键处理"""
        # 测试空键
        set_cache("", "value")
        # 应该处理空键而不崩溃

        # 测试None键
        set_cache(None, "value")
        # 应该处理None键而不崩溃

    def test_large_data_handling(self):
        """测试大数据处理"""
        # 测试大数据对象
        large_data = {"items": list(range(1000))}

        # 应该能够处理大数据
        result = set_cache("large_data", large_data)
        assert result is True

        cached_data = get_cache("large_data")
        assert cached_data["items"][0] == 0
        assert cached_data["items"][999] == 999

        # 清理
        delete_cache("large_data")

    def test_serialization_handling(self):
        """测试序列化处理"""
        # 测试复杂数据类型
        complex_data = {
            "timestamp": "2023-01-01T00:00:00Z",
            "nested": {"deep": {"deeper": "value"}},
            "list": [1, 2, 3, {"nested_in_list": True}],
            "boolean": True,
            "none_value": None,
        }

        # 应该能够序列化和反序列化
        result = set_cache("complex_data", complex_data)
        assert result is True

        cached_data = get_cache("complex_data")
        assert cached_data == complex_data

        # 清理
        delete_cache("complex_data")
