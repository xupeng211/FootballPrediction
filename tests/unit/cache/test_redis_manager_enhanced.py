"""
Redis Manager 增强测试文件
为 cache/redis_manager.py 模块提供参数化测试和边界条件测试
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import json
import time


class TestRedisManagerEnhanced:
    """增强版Redis管理器测试"""

    @pytest.mark.parametrize("key,value,ttl,expected_success", [
        ("test_key", "test_value", 300, True),
        ("user_123", {"name": "John", "age": 30}, 600, True),
        ("session_abc", "session_data", 0, True),  # No TTL (uses default)
        ("counter_1", 42, 3600, True),
        ("", "empty_key_value", 300, False),  # Empty key
        ("valid_key", None, 300, False),  # None value
        ("unicode_key", "测试值", 300, True),  # Unicode values
    ])
    def test_set_operation_parametrized(self, key, value, ttl, expected_success):
        """参数化测试Redis设置操作"""
        with patch('src.cache.redis_manager.redis') as mock_redis:
            from src.cache.redis_manager import RedisManager

            manager = RedisManager()

            # Mock the sync client directly
            sync_client_mock = Mock()
            manager._sync_client = sync_client_mock

            if expected_success:
                # Mock successful Redis operation - always uses setex
                sync_client_mock.setex.return_value = True

                result = manager.set(key, value, ttl=ttl)
                sync_client_mock.setex.assert_called_once()

                assert result is True
            else:
                # Mock failed Redis operation
                sync_client_mock.setex.side_effect = Exception("Invalid key")

                result = manager.set(key, value, ttl=ttl)
                assert result is False

    @pytest.mark.parametrize("key,default_value,expected_type", [
        ("existing_key", None, str),
        ("numeric_key", 0, int),
        ("json_key", {}, dict),
        ("list_key", [], list),
        ("nonexistent_key", "default", str),
        ("", "default", str),  # Empty key
    ])
    def test_get_operation_parametrized(self, key, default_value, expected_type):
        """参数化测试Redis获取操作"""
        with patch('src.cache.redis_manager.redis') as mock_redis:
            from src.cache.redis_manager import RedisManager

            manager = RedisManager()

            # Mock the sync client directly
            sync_client_mock = Mock()
            manager._sync_client = sync_client_mock

            # Mock Redis responses
            if key == "existing_key":
                sync_client_mock.get.return_value = "stored_value"
            elif key == "numeric_key":
                sync_client_mock.get.return_value = "42"
            elif key == "json_key":
                sync_client_mock.get.return_value = '{"name": "test"}'
            elif key == "list_key":
                sync_client_mock.get.return_value = '[1, 2, 3]'
            else:
                sync_client_mock.get.return_value = None

            result = manager.get(key, default=default_value)

            if key == "numeric_key":
                assert result == 42
            elif key == "json_key":
                assert result == {"name": "test"}
            elif key == "list_key":
                assert result == [1, 2, 3]
            elif key in ["existing_key"]:
                assert result == "stored_value"
            else:
                assert result == default_value

    # Removed keys operation test - method doesn't exist in RedisManager

    # Removed counter operations test - methods don't exist in RedisManager

    # Removed hash operations test - methods don't exist in RedisManager

    @pytest.mark.parametrize("ttl_seconds,expected_success", [
        (300, True),
        (0, True),  # Zero TTL is valid in Redis
        (-1, True),  # Negative TTL is valid in Redis
        (3600, True),
    ])
    def test_expire_operation_parametrized(self, ttl_seconds, expected_success):
        """参数化测试Redis过期操作"""
        with patch('src.cache.redis_manager.redis') as mock_redis:
            from src.cache.redis_manager import RedisManager

            manager = RedisManager()

            # Mock the sync client directly
            sync_client_mock = Mock()
            manager._sync_client = sync_client_mock

            sync_client_mock.expire.return_value = True

            result = manager.expire("test_key", ttl_seconds)

            assert result is expected_success
            sync_client_mock.expire.assert_called_once_with("test_key", ttl_seconds)

    def test_redis_connection_error_handling(self):
        """测试Redis连接错误处理"""
        with patch('src.cache.redis_manager.redis') as mock_redis:
            from src.cache.redis_manager import RedisManager

            # Mock connection error - don't set sync_client to trigger the error
            manager = RedisManager()
            manager._sync_client = None

            # Test that operations handle connection errors gracefully
            result = manager.get("test_key")
            assert result is None

    def test_redis_serialization_deserialization(self):
        """测试Redis序列化和反序列化"""
        with patch('src.cache.redis_manager.redis') as mock_redis:
            from src.cache.redis_manager import RedisManager

            manager = RedisManager()

            # Mock the sync client directly
            sync_client_mock = Mock()
            manager._sync_client = sync_client_mock

            # Test complex object serialization
            complex_obj = {
                "name": "Test",
                "data": [1, 2, 3],
                "nested": {"key": "value"},
                "timestamp": datetime.now().isoformat()
            }

            sync_client_mock.set.return_value = True
            sync_client_mock.get.return_value = json.dumps(complex_obj)

            # Test serialization
            result = manager.set("complex_key", complex_obj)
            assert result is True

            # Test deserialization
            retrieved = manager.get("complex_key")
            assert retrieved == complex_obj

    # Removed pipeline operations test - method doesn't exist in RedisManager

    # Removed memory management test - method doesn't exist in RedisManager

    # Removed connection pool management test - method doesn't exist in RedisManager


if __name__ == "__main__":
    pytest.main([__file__, "-v"])