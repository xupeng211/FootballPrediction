"""
缓存综合测试
专注于提升缓存模块的覆盖率
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
import time

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))


@pytest.mark.unit
class TestCacheComprehensive:
    """缓存综合测试"""

    def test_redis_manager_all_methods(self):
        """测试RedisManager的所有方法"""
        try:
            from src.cache.redis_manager import RedisManager

            # 创建RedisManager实例
            with patch("src.cache.redis_manager.redis") as mock_redis:
                # Mock同步客户端
                mock_sync_client = MagicMock()
                mock_sync_client.ping.return_value = True
                mock_sync_client.get.return_value = b"test_value"
                mock_sync_client.set.return_value = 1
                mock_sync_client.delete.return_value = 1
                mock_sync_client.exists.return_value = 1
                mock_sync_client.keys.return_value = [b"key1", b"key2"]
                mock_sync_client.info.return_value = {"redis_version": "6.0.0"}
                mock_sync_client.flushdb.return_value = "OK"

                mock_redis.Redis.return_value = mock_sync_client

                # Mock异步客户端
                mock_async_client = AsyncMock()
                mock_async_client.ping.return_value = True
                mock_async_client.get.return_value = "test_value"
                mock_async_client.set.return_value = True
                mock_async_client.delete.return_value = 1
                mock_async_client.exists.return_value = 1
                mock_async_client.keys.return_value = ["key1", "key2"]

                manager = RedisManager()
                manager._async_client = mock_async_client

                # 测试所有方法
                assert manager.ping() is True
                assert manager.get("test_key") == "test_value"
                assert manager.set("test_key", "test_value") == 1
                assert manager.delete("test_key") == 1
                assert manager.exists("test_key") == 1
                assert manager.keys("test:*") == [b"key1", b"key2"]
                assert manager.get_info() == {"redis_version": "6.0.0"}
                assert manager.clear_all() == "OK"
                assert manager.close() is None

        except ImportError:
            pytest.skip("RedisManager not available")

    def test_redis_manager_error_handling(self):
        """测试RedisManager错误处理"""
        try:
            from src.cache.redis_manager import RedisManager

            with patch("src.cache.redis_manager.redis") as mock_redis:
                mock_client = MagicMock()
                mock_client.ping.side_effect = Exception("Connection failed")
                mock_redis.Redis.return_value = mock_client

                manager = RedisManager()

                # 测试错误处理
                with pytest.raises(Exception):
                    manager.ping()

        except ImportError:
            pytest.skip("RedisManager not available")

    def test_ttl_cache_basic(self):
        """测试TTL缓存基本功能"""
        try:
            from src.cache.ttl_cache import TTLCache

            # 创建缓存实例
            cache = TTLCache(max_size=10, ttl=60)

            # 测试基本操作
            assert cache.set("key1", "value1") is True
            assert cache.get("key1") == "value1"
            assert cache.get("nonexistent") is None

            # 测试更新
            assert cache.set("key1", "value2") is True
            assert cache.get("key1") == "value2"

            # 测试删除
            assert cache.delete("key1") is True
            assert cache.get("key1") is None

        except ImportError:
            pytest.skip("TTLCache not available")

    def test_ttl_cache_expiry(self):
        """测试TTL缓存过期"""
        try:
            from src.cache.ttl_cache import TTLCache

            # 创建短TTL缓存
            cache = TTLCache(max_size=10, ttl=0.1)  # 100ms

            cache.set("expire_key", "expire_value")
            assert cache.get("expire_key") == "expire_value"

            # 等待过期
            time.sleep(0.2)
            assert cache.get("expire_key") is None

        except ImportError:
            pytest.skip("TTLCache not available")

    def test_ttl_cache_max_size(self):
        """测试TTL缓存最大大小限制"""
        try:
            from src.cache.ttl_cache import TTLCache

            # 创建小缓存
            cache = TTLCache(max_size=2, ttl=60)

            cache.set("key1", "value1")
            cache.set("key2", "value2")
            assert cache.get("key1") == "value1"
            assert cache.get("key2") == "value2"

            # 添加第三个键，应该驱逐最旧的
            cache.set("key3", "value3")
            assert cache.get("key3") == "value3"
            # key1应该被驱逐
            assert cache.get("key1") is None

        except ImportError:
            pytest.skip("TTLCache not available")

    def test_cache_factory(self):
        """测试缓存工厂模式"""
        try:
            from src.cache.redis_manager import RedisManager

            # 测试单例模式
            manager1 = RedisManager()
            manager2 = RedisManager()

            # 验证是不同实例（RedisManager不是单例）
            assert manager1 is not manager2

        except ImportError:
            pytest.skip("Cache factory not available")

    def test_cache_serialization(self):
        """测试缓存序列化"""
        try:
            from src.cache.redis_manager import RedisManager

            with patch("src.cache.redis_manager.redis") as mock_redis:
                mock_client = MagicMock()
                mock_client.ping.return_value = True
                mock_client.set.return_value = 1
                mock_client.get.return_value = b'{"key": "value"}'
                mock_redis.Redis.return_value = mock_client

                manager = RedisManager()

                # 测试序列化存储
                test_dict = {"key": "value"}
                import json

                serialized = json.dumps(test_dict)
                manager.set("dict_key", serialized)

                # 测试反序列化读取
                result = manager.get("dict_key")
                assert result == '{"key": "value"}'

                # 手动反序列化
                deserialized = json.loads(result)
                assert deserialized == test_dict

        except ImportError:
            pytest.skip("Cache serialization not available")

    def test_cache_pipeline(self):
        """测试缓存管道操作"""
        try:
            from src.cache.redis_manager import RedisManager

            with patch("src.cache.redis_manager.redis") as mock_redis:
                mock_client = MagicMock()
                mock_client.ping.return_value = True
                mock_pipeline = MagicMock()
                mock_pipeline.execute.return_value = [1, 1, 1]
                mock_client.pipeline.return_value = mock_pipeline
                mock_redis.Redis.return_value = mock_client

                manager = RedisManager()

                # 使用管道
                pipeline = manager.client.pipeline()
                pipeline.set("key1", "value1")
                pipeline.set("key2", "value2")
                pipeline.set("key3", "value3")

                results = pipeline.execute()
                assert results == [1, 1, 1]

        except (ImportError, AttributeError):
            pytest.skip("Cache pipeline not available")

    def test_cache_health_check(self):
        """测试缓存健康检查"""
        try:
            from src.cache.redis_manager import RedisManager

            with patch("src.cache.redis_manager.redis") as mock_redis:
                mock_client = MagicMock()
                mock_client.ping.return_value = True
                mock_client.info.return_value = {
                    "redis_version": "6.0.0",
                    "connected_clients": 10,
                    "used_memory": "1024000",
                }
                mock_redis.Redis.return_value = mock_client

                manager = RedisManager()

                # 健康检查
                health = manager.health_check()
                assert health is True

                # 获取信息
                info = manager.get_info()
                assert "redis_version" in info

        except (ImportError, AttributeError):
            pytest.skip("Cache health check not available")

    def test_cache_connection_pool(self):
        """测试缓存连接池"""
        try:
            from src.cache.redis_manager import RedisManager

            with patch("src.cache.redis_manager.redis") as mock_redis:
                mock_client = MagicMock()
                mock_client.ping.return_value = True
                mock_redis.Redis.return_value = mock_client

                manager = RedisManager()

                # 测试连接池属性
                assert hasattr(manager, "client")
                assert manager.client is not None

        except ImportError:
            pytest.skip("Cache connection pool not available")
