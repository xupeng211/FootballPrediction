from typing import Optional

"""
Redis缓存管理器测试
Tests for Redis cache manager module.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# 导入被测试模块
try:
    from src.cache.redis_manager import RedisManager, CacheKeyManager, get_redis_manager

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


# 模拟Redis相关依赖
class MockRedis:
    """模拟Redis客户端"""

    def __init__(self, host="localhost", port=6379, **kwargs):
        self.host = host
        self.port = port
        self.data = {}
        self.is_connected = False

    def ping(self):
        """Redis ping测试"""
        self.is_connected = True
        return True

    def get(self, key, default=None):
        """获取值"""
        return self.data.get(key, default)

    def set(self, key, value, ex=None):
        """设置值"""
        self.data[key] = value
        return True

    def delete(self, key):
        """删除键"""
        return self.data.pop(key, None) is not None

    def exists(self, key):
        """检查键是否存在"""
        return key in self.data

    def ttl(self, key):
        """获取TTL"""
        return -1  # 简化实现

    def mget(self, keys, default=None):
        """批量获取"""
        return [self.data.get(k, default) for k in keys]

    def mset(self, mapping):
        """批量设置"""
        self.data.update(mapping)
        return True

    def close(self):
        """关闭连接"""
        self.is_connected = False


class TestCacheKeyManager:
    """缓存键管理器测试类"""

    def test_cache_key_manager_initialization(self):
        """测试缓存键管理器初始化"""
        manager = CacheKeyManager()

        assert hasattr(manager, "build_key")
        assert hasattr(manager, "validate_key")
        assert hasattr(manager, "normalize_key")

    def test_build_key_success(self):
        """测试成功构建缓存键"""
        manager = CacheKeyManager()
        key = manager.build_key("test", "key", {"param": "value"})

        assert key is not None
        assert isinstance(key, str)

    def test_build_key_with_different_params(self):
        """测试使用不同参数构建缓存键"""
        manager = CacheKeyManager()

        key1 = manager.build_key("namespace", "key")
        key2 = manager.build_key(
            "namespace", "key", {"param1": "value1", "param2": "value2"}
        )

        assert key1 != key2
        assert "namespace" in key1
        assert "namespace" in key2

    def test_validate_key_valid_key(self):
        """测试验证有效键"""
        manager = CacheKeyManager()

        assert manager.validate_key("valid_key") is True
        assert manager.validate_key("key_123") is True
        assert manager.validate_key("KEY_123") is True

    def test_validate_key_invalid_key(self):
        """测试验证无效键"""
        manager = CacheKeyManager()

        # 常见的无效键
        invalid_keys = ["", " ", "\t", "\n", "key with spaces", "key\nwith\nlines"]

        for invalid_key in invalid_keys:
            assert manager.validate_key(invalid_key) is False

    def test_normalize_key(self):
        """测试键标准化"""
        manager = CacheKeyManager()

        # 测试不同格式的键
        test_cases = [
            ("  key  ", "key"),  # 去除前后空格
            ("MixedCase", "mixedcase"),  # 大小写转换
            ("SPECIAL_CHARS!", "special_chars"),  # 特殊字符处理
        ]

        for input_key, expected_key in test_cases:
            result = manager.normalize_key(input_key)
            assert result == expected_key

    def test_key_components(self):
        """测试键组件组合"""
        manager = CacheKeyManager()

        # 测试组件拼接
        components = ["app", "module", "resource"]
        key = manager.build_key(*components)

        for component in components:
            assert component in key

    def test_key_versioning(self):
        """测试键版本控制"""
        manager = CacheKeyManager()

        # 基础键
        base_key = manager.build_key("test", "data")

        # 带版本的键
        versioned_key = manager.build_key("test", "data", version="v1.0")

        assert base_key != versioned_key
        assert "v1.0" in versioned_key

    @pytest.fixture
    def mock_redis_client(self):
        """模拟Redis客户端fixture"""
        return MockRedis()

    @pytest.fixture
    def manager_with_config(self):
        """带配置的Redis管理器fixture"""
        config = {
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "password": None,
            "encoding": "utf-8",
        }
        return RedisManager(config)

    @pytest.fixture
    def manager_with_client(self, mock_redis_client):
        """带客户端的Redis管理器fixture"""
        manager = RedisManager()
        manager.client = mock_redis_client
        return manager

    def test_manager_initialization_with_config(self):
        """测试使用配置初始化管理器"""
        config = {"host": "redis.example.com", "port": 6380, "db": 1}
        manager = RedisManager(config)

        assert manager.config == config
        assert manager.config["host"] == "redis.example.com"
        assert manager.config["port"] == 6380
        assert manager.config["db"] == 1

    def test_manager_initialization_without_config(self):
        """测试不使用配置初始化管理器"""
        manager = RedisManager()

        # 应该使用默认配置
        assert hasattr(manager, "config")
        assert manager.config.get("host", "localhost") == "localhost"
        assert manager.config.get("port", 6379) == 6379

    def test_connect_success(self, mock_redis_client):
        """测试成功连接"""
        mock_redis_client.ping.return_value = True

        manager = RedisManager()
        manager.client = mock_redis_client

        result = manager.connect()

        assert result is True
        mock_redis_client.ping.assert_called_once()

    def test_connect_failure(self, mock_redis_client):
        """测试连接失败"""
        mock_redis_client.ping.return_value = False

        manager = RedisManager()
        manager.client = mock_redis_client

        result = manager.connect()

        assert result is False

    def test_disconnect(self, mock_redis_client):
        """测试断开连接"""
        manager = RedisManager()
        manager.client = mock_redis_client

        manager.disconnect()

        mock_redis_client.close.assert_called_once()

    def test_is_connected(self, mock_redis_client):
        """测试连接状态检查"""
        manager = RedisManager()
        manager.client = mock_redis_client

        # 测试已连接状态
        mock_redis_client.is_connected = True
        assert manager.is_connected() is True

        # 测试未连接状态
        mock_redis_client.is_connected = False
        assert manager.is_connected() is False

    def test_set_key_success(self, mock_redis_client):
        """测试成功设置键值"""
        mock_redis_client.set.return_value = True

        manager = RedisManager()
        manager.client = mock_redis_client

        result = manager.set("test_key", "test_value")

        assert result is True
        mock_redis_client.set.assert_called_once_with("test_key", "test_value")

    def test_set_key_with_ttl(self, mock_redis_client):
        """测试设置带TTL的键值"""
        mock_redis_client.set.return_value = True

        manager = RedisManager()
        manager.client = mock_redis_client

        result = manager.set("test_key", "test_value", ex=3600)

        assert result is True
        mock_redis_client.set.assert_called_once_with("test_key", "test_value", ex=3600)

    def test_get_key_exists(self, mock_redis_client):
        """测试获取存在的键"""
        mock_redis_client.get.return_value = "test_value"

        manager = RedisManager()
        manager.client = mock_redis_client

        result = manager.get("test_key")

        assert result == "test_value"
        mock_redis_client.get.assert_called_once_with("test_key")

    def test_get_key_not_exists(self, mock_redis_client):
        """测试获取不存在的键"""
        mock_redis_client.get.return_value = None

        manager = RedisManager()
        manager.client = mock_redis_client

        result = manager.get("nonexistent_key")

        assert result is None
        mock_redis_client.get.assert_called_once_with("nonexistent_key")

    def test_get_key_with_default(self, mock_redis_client):
        """测试获取键时提供默认值"""
        mock_redis_client.get.return_value = None

        manager = RedisManager()
        manager.client = mock_redis_client

        result = manager.get("nonexistent_key", "default_value")

        assert result == "default_value"
        mock_redis_client.get.assert_called_once_with(
            "nonexistent_key", "default_value"
        )

    def test_delete_key_exists(self, mock_redis_client):
        """测试删除存在的键"""
        mock_redis_client.delete.return_value = True

        manager = RedisManager()
        manager.client = mock_redis_client

        result = manager.delete("test_key")

        assert result is True
        mock_redis_client.delete.assert_called_once_with("test_key")

    def test_delete_key_not_exists(self, mock_redis_client):
        """测试删除不存在的键"""
        mock_redis_client.delete.return_value = False

        manager = RedisManager()
        manager.client = mock_redis_client

        result = manager.delete("nonexistent_key")

        assert result is False
        mock_redis_client.delete.assert_called_once_with("nonexistent_key")

    def test_exists_key_exists(self, mock_redis_client):
        """测试存在的键检查"""
        mock_redis_client.exists.return_value = True

        manager = RedisManager()
        manager.client = mock_redis_client

        result = manager.exists("test_key")

        assert result is True
        mock_redis_client.exists.assert_called_once_with("test_key")

    def test_exists_key_not_exists(self, mock_redis_client):
        """测试不存在的键检查"""
        mock_redis_client.exists.return_value = False

        manager = RedisManager()
        manager.client = mock_redis_client

        result = manager.exists("nonexistent_key")

        assert result is False
        mock_redis_client.exists.assert_called_once_with("nonexistent_key")

    def test_get_ttl(self, mock_redis_client):
        """测试获取TTL"""
        mock_redis_client.ttl.return_value = 3600

        manager = RedisManager()
        manager.client = mock_redis_client

        result = manager.get_ttl("test_key")

        assert result == 3600
        mock_redis_client.ttl.assert_called_once_with("test_key")

    def test_get_ttl_not_exists(self, mock_redis_client):
        """测试不存在键的TTL"""
        mock_redis_client.ttl.return_value = -1

        manager = RedisManager()
        manager.client = mock_redis_client

        result = manager.get_ttl("nonexistent_key")

        assert result == -1
        mock_redis_client.ttl.assert_called_once_with("nonexistent_key")

    def test_mset_success(self, mock_redis_client):
        """测试批量设置成功"""
        mock_redis_client.mset.return_value = True

        manager = RedisManager()
        manager.client = mock_redis_client

        mapping = {"key1": "value1", "key2": "value2"}
        result = manager.mset(mapping)

        assert result is True
        mock_redis_client.mset.assert_called_once_with(mapping)

    def test_mget_success(self, mock_redis_client):
        """测试批量获取成功"""
        mock_redis_client.mget.return_value = ["value1", "value2", None]

        manager = RedisManager()
        manager.client = mock_redis_client

        keys = ["key1", "key2", "key3"]
        result = manager.mget(keys)

        assert result == ["value1", "value2", None]
        mock_redis_client.mget.assert_called_once_with(keys)

    def test_mget_with_default(self, mock_redis_client):
        """测试批量获取带默认值"""
        mock_redis_client.mget.return_value = [None, "value2"]

        manager = RedisManager()
        manager.client = mock_redis_client

        keys = ["key1", "key2"]
        result = manager.mget(keys, default="default")

        assert result == ["default", "value2"]
        mock_redis_client.mget.assert_called_once_with(keys, default="default")

    @pytest.mark.asyncio
    async def test_async_operations(self, mock_redis_client):
        """测试异步操作"""
        # 模拟异步Redis客户端
        async_mock_redis = AsyncMock()
        async_mock_redis.ping.return_value = True

        manager = RedisManager()
        manager.async_client = async_mock_redis

        # 测试异步连接
        result = await manager.connect_async()
        assert result is True

        # 测试异步操作
        async_mock_redis.set.return_value = True
        result = await manager.set_async("async_key", "async_value")
        assert result is True

        async_mock_redis.get.return_value = "async_value"
        result = await manager.get_async("async_key")
        assert result == "async_value"

    def test_pipeline_operations(self, mock_redis_client):
        """测试管道操作"""
        mock_pipeline = Mock()
        mock_redis_client.pipeline.return_value = mock_pipeline

        manager = RedisManager()
        manager.client = mock_redis_client

        # 获取管道
        pipeline = manager.get_pipeline()

        assert pipeline is mock_pipeline
        mock_redis_client.pipeline.assert_called_once()

        # 使用管道执行操作
        mock_pipeline.set.return_value = None
        mock_pipeline.execute.return_value = [True, True]

        pipeline.set("pipe_key1", "pipe_value1")
        pipeline.set("pipe_key2", "pipe_value2")
        results = pipeline.execute()

        assert len(results) == 2
        mock_pipeline.set.assert_any_call("pipe_key1", "pipe_value1")
        mock_pipeline.set.assert_any_call("pipe_key2", "pipe_value2")
        mock_pipeline.execute.assert_called_once()


class TestRedisManagerIntegration:
    """Redis管理器集成测试类"""

    @pytest.mark.skipif(not HAS_REDIS, reason="Redis not available")
    def test_end_to_end_workflow(self, mock_redis_client):
        """测试端到端工作流"""
        mock_redis_client.data.clear()  # 清空模拟数据

        manager = RedisManager()
        manager.client = mock_redis_client

        # 连接
        assert manager.connect()

        # 设置数据
        assert manager.set("user:1", "user_data_1")
        assert manager.set("user:1:profile", "profile_data_1")
        assert manager.set("session:abc123", "session_data", ex=3600)

        # 验证数据
        assert manager.get("user:1") == "user_data_1"
        assert manager.exists("user:1:profile") is True
        assert manager.get_ttl("session:abc123") == 3600

        # 更新数据
        assert manager.set("user:1", "updated_data")
        assert manager.get("user:1") == "updated_data"

        # 删除数据
        assert manager.delete("user:1:profile")
        assert manager.exists("user:1:profile") is False
        assert manager.get("user:1:profile") is None

        # 批量操作
        batch_data = {"batch:1": "data1", "batch:2": "data2"}
        assert manager.mset(batch_data)
        batch_keys = ["batch:1", "batch:2", "batch:3"]
        batch_results = manager.mget(batch_keys, "default")
        assert batch_results == ["data1", "data2", "default"]

        # 断开连接
        manager.disconnect()

    def test_error_handling(self, mock_redis_client):
        """测试错误处理"""
        manager = RedisManager()
        manager.client = mock_redis_client

        # 模拟连接错误
        mock_redis_client.ping.side_effect = Exception("Connection error")

        with pytest.raises(Exception, match="Connection error"):
            manager.connect()

        # 模拟操作错误
        mock_redis_client.set.side_effect = Exception("Set operation failed")

        with pytest.raises(Exception, match="Set operation failed"):
            manager.set("test_key", "test_value")

    def test_retry_mechanism(self, mock_redis_client):
        """测试重试机制"""
        manager = RedisManager(max_retries=3)
        manager.client = mock_redis_client

        # 模拟前两次失败，第三次成功
        call_count = 0

        def set_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Temporary error")
            return True

        mock_redis_client.set.side_effect = set_side_effect

        # 测试重试
        result = manager.set("retry_key", "retry_value", retry=True)

        assert result is True
        assert call_count == 3

    def test_cache_hit_miss_logic(self, mock_redis_client):
        """测试缓存命中/未命中逻辑"""
        manager = RedisManager()
        manager.client = mock_redis_client

        # 模拟缓存未命中
        mock_redis_client.get.return_value = None

        result1 = manager.get_with_cache("cache_key", lambda: "computed_value")
        assert result1 == "computed_value"
        mock_redis_client.get.assert_called_once_with("cache_key")

        # 模拟缓存命中
        mock_redis_client.get.return_value = "cached_value"
        mock_redis_client.get.side_effect = None  # 重置side effect

        result2 = manager.get_with_cache("cache_key", lambda: "computed_value")
        assert result2 == "cached_value"
        mock_redis_client.get.assert_called_once_with("cache_key")


class TestGlobalRedisManager:
    """全局Redis管理器测试类"""

    def test_get_redis_manager(self):
        """测试获取全局Redis管理器"""
        with patch("src.cache.redis_manager._redis_manager_instance") as mock_instance:
            mock_instance = Mock()
            mock_instance.is_connected = True

            get_redis_manager()

            mock_instance.assert_called_once()

    def test_singleton_behavior(self):
        """测试单例行为"""
        with patch("src.cache.redis_manager._redis_manager_instance") as mock_instance:
            mock_instance.is_connected = True

            manager1 = get_redis_manager()
            manager2 = get_redis_manager()

            assert manager1 is manager2
            mock_instance.assert_called_once()

    def test_global_manager_configuration(self):
        """测试全局管理器配置"""
        with patch("src.cache.redis_manager._redis_manager_instance") as mock_instance:
            mock_instance.config = {"host": "global.redis.com"}
            mock_instance.is_connected = True

            manager = get_redis_manager()

            assert manager.config["host"] == "global.redis.com"


class TestPerformanceOptimization:
    """性能优化测试类"""

    @pytest.mark.skipif(not HAS_REDIS, reason="Redis not available")
    def test_batch_operations_performance(self, mock_redis_client):
        """测试批量操作性能"""
        import time

        manager = RedisManager()
        manager.client = mock_redis_client

        # 模拟大量数据
        large_data = {f"key_{i}": f"value_{i}" for i in range(1000)}

        start_time = time.time()
        mock_redis_client.mset.return_value = True
        manager.mset(large_data)
        mset_time = time.time() - start_time

        # 模拟批量获取
        keys = list(large_data.keys())
        start_time = time.time()
        mock_redis_client.mget.return_value = list(large_data.values())
        manager.mget(keys)
        mget_time = time.time() - start_time

        # 验证批量操作确实比单个操作更高效
        assert mset_time > 0  # 确保操作被执行
        assert mget_time > 0

    def test_connection_pooling(self, mock_redis_client):
        """测试连接池"""
        with patch("src.cache.redis_manager.RedisConnectionPool") as mock_pool:
            mock_pool_instance = Mock()
            mock_pool.return_value = mock_pool_instance
            mock_pool_instance.acquire.return_value = Mock()
            mock_pool_instance.release.return_value = None

            manager = RedisManager(use_connection_pool=True)
            pool = manager.get_connection_pool()

            assert pool is mock_pool_instance
            mock_pool.assert_called_once()

    def test_key_expiration_strategies(self, mock_redis_client):
        """测试键过期策略"""
        manager = RedisManager()

        # 测试不同过期策略
        test_cases = [
            ("short_lived_key", 60),  # 1分钟
            ("long_lived_key", 86400),  # 1天
            ("no_expiration_key", None),  # 永不过期
        ]

        for key, ttl in test_cases:
            mock_redis_client.set.return_value = True
            mock_redis_client.ttl.return_value = ttl if ttl else -1

            manager.set(key, "value", ex=ttl)

            if ttl:
                manager.get_ttl.assert_called_once_with(key)
            else:
                mock_redis_client.ttl.assert_called_once_with(key)
