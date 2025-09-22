"""

import asyncio
Redis缓存管理器基础测试

专注于核心功能的单元测试，避免复杂的依赖问题
"""

import json
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

# 添加src目录到Python路径
src_path = os.path.join(os.path.dirname(__file__), "..", "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.cache.redis_manager import CacheKeyManager, RedisManager  # noqa: E402


class TestCacheKeyManager:
    """测试缓存Key管理器"""

    def test_build_key_basic(self):
        """测试基础Key构建"""
        key = CacheKeyManager.build_key("match", 123, "features")
        assert key == "match:123:features"

    def test_build_key_with_kwargs(self):
        """测试带参数的Key构建"""
        key = CacheKeyManager.build_key("team", 1, "stats", type="recent")
        assert key == "team:1:stats:type:recent"

    def test_get_ttl(self):
        """测试TTL获取"""
        assert CacheKeyManager.get_ttl("match_info") == 1800
        assert CacheKeyManager.get_ttl("team_stats") == 3600
        assert CacheKeyManager.get_ttl("unknown_type") == 1800

    def test_predefined_key_methods(self):
        """测试预定义的Key生成方法"""
        assert CacheKeyManager.match_features_key(123) == "match:123:features"
        assert CacheKeyManager.team_stats_key(1, "recent") == "team:1:stats:type:recent"
        assert CacheKeyManager.odds_key(123, "bet365") == "odds:123:bet365"
        assert CacheKeyManager.prediction_key(123, "v1") == "predictions:123:v1"


class TestRedisManager:
    """测试Redis管理器核心功能"""

    def setup_method(self):
        """测试前设置"""
        self.redis_manager = RedisManager(redis_url="redis://localhost:6379/0")

    def test_init(self):
        """测试初始化"""
        manager = RedisManager()
        # 使用实际配置的Redis URL，而不是硬编码localhost
        assert manager.redis_url in [
            "redis://localhost:6379/0",
            "redis://redis:6379/0",
            "redis://:redis_pass@localhost:6379/0",
        ]
        assert manager.max_connections == 20

    def test_mask_password(self):
        """测试密码掩码"""
        url = "redis://user:secret123@localhost:6379/0"
        masked = self.redis_manager._mask_password(url)
        assert masked == "redis://user:****@localhost:6379/0"

    @patch("redis.Redis")
    @patch("redis.ConnectionPool.from_url")
    def test_sync_operations_success(self, mock_pool, mock_redis):
        """测试同步操作成功"""
        # 设置mock
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_pool.return_value = Mock()

        # 重新初始化连接池
        self.redis_manager._init_sync_pool()

        # 测试GET操作
        test_data = {"key": "value"}
        mock_client.get.return_value = json.dumps(test_data)

        result = self.redis_manager.get("test_key")
        assert result == test_data
        mock_client.get.assert_called_once_with("test_key")

        # 测试SET操作
        mock_client.setex.return_value = True
        success = self.redis_manager.set("test_key", test_data, ttl=3600)
        assert success is True
        expected_value = json.dumps(test_data, ensure_ascii=False, default=str)
        mock_client.setex.assert_called_with("test_key", 3600, expected_value)

        # 测试DELETE操作
        mock_client.delete.return_value = 1
        deleted = self.redis_manager.delete("test_key")
        assert deleted == 1
        mock_client.delete.assert_called_with("test_key")

    def test_sync_operations_no_client(self):
        """测试同步操作无客户端"""
        self.redis_manager._sync_client = None

        # 应该返回默认值和False
        assert self.redis_manager.get("key", "default") == "default"
        assert self.redis_manager.set("key", "value") is False
        assert self.redis_manager.delete("key") == 0

    @patch("redis.Redis")
    @patch("redis.ConnectionPool.from_url")
    def test_sync_operations_error(self, mock_pool, mock_redis):
        """测试同步操作错误"""
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_pool.return_value = Mock()

        self.redis_manager._init_sync_pool()

        # 模拟Redis错误
        from redis.exceptions import RedisError

        mock_client.get.side_effect = RedisError("Connection failed")
        mock_client.setex.side_effect = RedisError("Set failed")
        mock_client.delete.side_effect = RedisError("Delete failed")

        # 应该处理错误并返回默认值
        assert self.redis_manager.get("key", "default") == "default"
        assert self.redis_manager.set("key", "value") is False
        assert self.redis_manager.delete("key") == 0

    @pytest.mark.asyncio
    async def test_async_operations_success(self):
        """测试异步操作成功"""
        with patch("redis.asyncio.Redis") as mock_redis:
            with patch("redis.asyncio.ConnectionPool.from_url") as mock_pool:
                mock_client = AsyncMock()
                mock_redis.return_value = mock_client
                mock_pool.return_value = Mock()

                await self.redis_manager._init_async_pool()

                # 测试异步GET
                test_data = {"async": "data"}
                mock_client.get.return_value = json.dumps(test_data)

                result = await self.redis_manager.aget("async_key")
                assert result == test_data
                mock_client.get.assert_called_once_with("async_key")

                # 测试异步SET
                mock_client.setex.return_value = True
                success = await self.redis_manager.aset("async_key", test_data)
                assert success is True
                expected_value = json.dumps(test_data, ensure_ascii=False, default=str)
                mock_client.setex.assert_called_with("async_key", 1800, expected_value)

                # 测试异步DELETE
                mock_client.delete.return_value = 1
                deleted = await self.redis_manager.adelete("async_key")
                assert deleted == 1
                mock_client.delete.assert_called_with("async_key")

    def test_batch_operations_success(self):
        """测试批量操作成功"""
        with patch("redis.Redis") as mock_redis:
            with patch("redis.ConnectionPool.from_url") as mock_pool:
                mock_client = Mock()
                mock_redis.return_value = mock_client
                mock_pool.return_value = Mock()

                self.redis_manager._init_sync_pool()

                # 测试MGET
                mock_client.mget.return_value = [
                    json.dumps({"data": 1}),
                    b"string_data",
                    None,
                ]

                result = self.redis_manager.mget(["key1", "key2", "key3"], "default")
                expected = [{"data": 1}, "string_data", "default"]
                assert result == expected
                mock_client.mget.assert_called_once_with(["key1", "key2", "key3"])

                # 测试MSET
                mock_client.mset.return_value = True
                mapping = {"key1": "value1", "key2": {"data": 2}}

                success = self.redis_manager.mset(mapping)
                assert success is True

                expected_mapping = {
                    "key1": "value1",
                    "key2": json.dumps({"data": 2}, ensure_ascii=False, default=str),
                }
                mock_client.mset.assert_called_once_with(expected_mapping)

    def test_health_check_operations(self):
        """测试健康检查操作"""
        with patch("redis.Redis") as mock_redis:
            with patch("redis.ConnectionPool.from_url") as mock_pool:
                mock_client = Mock()
                mock_redis.return_value = mock_client
                mock_pool.return_value = Mock()

                self.redis_manager._init_sync_pool()

                # 测试PING
                mock_client.ping.return_value = True
                assert self.redis_manager.ping() is True
                mock_client.ping.assert_called_once()

                # 测试获取INFO
                mock_info = {
                    "redis_version": "7.0.0",
                    "connected_clients": 5,
                    "used_memory_human": "1.2M",
                }
                mock_client.info.return_value = mock_info

                info = self.redis_manager.get_info()
                assert info["version"] == "7.0.0"
                assert info["connected_clients"] == 5
                assert info["used_memory_human"] == "1.2M"

    def test_string_data_handling(self):
        """测试字符串数据处理"""
        with patch("redis.Redis") as mock_redis:
            with patch("redis.ConnectionPool.from_url") as mock_pool:
                mock_client = Mock()
                mock_redis.return_value = mock_client
                mock_pool.return_value = Mock()

                self.redis_manager._init_sync_pool()

                # 测试字符串返回值
                mock_client.get.return_value = b"simple_string"
                result = self.redis_manager.get("key")
                assert result == "simple_string"

                # 测试无效JSON
                mock_client.get.return_value = b"invalid_json{"
                result = self.redis_manager.get("key")
                assert result == "invalid_json{"

    def test_ttl_operations(self):
        """测试TTL相关操作"""
        with patch("redis.Redis") as mock_redis:
            with patch("redis.ConnectionPool.from_url") as mock_pool:
                mock_client = Mock()
                mock_redis.return_value = mock_client
                mock_pool.return_value = Mock()

                self.redis_manager._init_sync_pool()

                # 测试TTL查询
                mock_client.ttl.return_value = 300
                ttl = self.redis_manager.ttl("key")
                assert ttl == 300
                mock_client.ttl.assert_called_once_with("key")

                # 测试EXISTS
                mock_client.exists.return_value = 1
                exists = self.redis_manager.exists("key")
                assert exists == 1
                mock_client.exists.assert_called_once_with("key")

    def test_context_managers(self):
        """测试上下文管理器"""
        # 测试同步上下文管理器
        with self.redis_manager.sync_context() as manager:
            assert manager is self.redis_manager

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """测试异步上下文管理器"""
        async with self.redis_manager.async_context() as manager:
            assert manager is self.redis_manager


@pytest.mark.skipif(
    not os.getenv("REDIS_INTEGRATION_TEST"),
    reason="需要设置REDIS_INTEGRATION_TEST环境变量来运行集成测试",
)
class TestRedisIntegration:
    """Redis集成测试（需要实际Redis服务）"""

    def setup_method(self):
        self.redis_manager = RedisManager(redis_url="redis://localhost:6379/15")

    def test_real_operations(self):
        """测试实际Redis操作"""
        if not self.redis_manager.ping():
            pytest.skip("Redis不可用")

        test_key = "test:integration:key"
        test_value = {"test": "integration", "number": 123}

        try:
            # 设置
            success = self.redis_manager.set(test_key, test_value, ttl=60)
            assert success is True

            # 获取
            result = self.redis_manager.get(test_key)
            assert result == test_value

            # TTL
            ttl = self.redis_manager.ttl(test_key)
            assert 50 <= ttl <= 60

            # 删除
            deleted = self.redis_manager.delete(test_key)
            assert deleted == 1

        finally:
            self.redis_manager.delete(test_key)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
