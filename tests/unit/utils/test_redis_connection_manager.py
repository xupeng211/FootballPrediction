# TODO: Consider creating a fixture for 14 repeated Mock creations

# TODO: Consider creating a fixture for 14 repeated Mock creations

from unittest.mock import Mock, patch
"""
测试Redis连接管理器
"""

import pytest

from src.cache.redis.core.connection_manager import RedisConnectionManager


@pytest.mark.unit

class TestRedisConnectionManager:
    """测试Redis连接管理器"""

    @patch("src.cache.redis.core.connection_manager.redis")
    def test_init_with_default_url(self, mock_redis):
        """测试使用默认URL初始化"""
        mock_pool = Mock()
        mock_redis.ConnectionPool.from_url.return_value = mock_pool
        mock_redis.Redis.return_value = Mock()

        manager = RedisConnectionManager()

        assert manager.redis_url == "redis://localhost:6379/0"
        assert manager.max_connections == 50
        assert manager.socket_timeout == 3.0

    @patch("src.cache.redis.core.connection_manager.redis")
    @patch.dict("os.environ", {"REDIS_URL": "redis://custom:6380/1"})
    def test_init_with_env_url(self, mock_redis):
        """测试使用环境变量URL初始化"""
        mock_pool = Mock()
        mock_redis.ConnectionPool.from_url.return_value = mock_pool
        mock_redis.Redis.return_value = Mock()

        manager = RedisConnectionManager()

        assert manager.redis_url == "redis://custom:6380/1"

    @patch("src.cache.redis.core.connection_manager.redis")
    @patch.dict("os.environ", {"REDIS_PASSWORD": "secret123"})
    def test_init_with_password(self, mock_redis):
        """测试使用密码初始化"""
        mock_pool = Mock()
        mock_redis.ConnectionPool.from_url.return_value = mock_pool
        mock_redis.Redis.return_value = Mock()

        manager = RedisConnectionManager(redis_url="redis://localhost:6379/0")

        assert "secret123" in manager.redis_url

    def test_mask_password(self):
        """测试密码遮蔽"""
        manager = RedisConnectionManager()
        masked = manager._mask_password("redis://user:secret123@localhost:6379/0")
        assert masked == "redis://user:****@localhost:6379/0"

    @patch("src.cache.redis.core.connection_manager.redis")
    def test_ping_success(self, mock_redis):
        """测试成功的ping"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_pool = Mock()
        mock_redis.ConnectionPool.from_url.return_value = mock_pool
        mock_redis.Redis.return_value = mock_client

        manager = RedisConnectionManager()
        _result = manager.ping()

        assert _result is True

    @patch("src.cache.redis.core.connection_manager.redis")
    def test_ping_failure(self, mock_redis):
        """测试失败的ping"""
        mock_client = Mock()
        mock_client.ping.return_value = False
        mock_pool = Mock()
        mock_redis.ConnectionPool.from_url.return_value = mock_pool
        mock_redis.Redis.return_value = mock_client

        manager = RedisConnectionManager()

        with pytest.raises(Exception):
            manager.ping()

    @patch("src.cache.redis.core.connection_manager.redis")
    def test_health_check(self, mock_redis):
        """测试健康检查"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_pool = Mock()
        mock_redis.ConnectionPool.from_url.return_value = mock_pool
        mock_redis.Redis.return_value = mock_client

        manager = RedisConnectionManager()
        _result = manager.health_check()

        assert _result is True

    @patch("src.cache.redis.core.connection_manager.redis")
    def test_get_info(self, mock_redis):
        """测试获取Redis信息"""
        mock_client = Mock()
        mock_client.info.return_value = {"redis_version": "6.0.0"}
        mock_pool = Mock()
        mock_redis.ConnectionPool.from_url.return_value = mock_pool
        mock_redis.Redis.return_value = mock_client

        manager = RedisConnectionManager()
        info = manager.get_info()

        assert info["redis_version"] == "6.0.0"
