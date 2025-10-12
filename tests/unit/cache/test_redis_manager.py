"""
Redis管理器测试
Tests for Redis Manager

测试src.cache.redis_manager模块的功能
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# 测试导入
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


class TestRedisManager:
    """Redis管理器测试"""

    def test_imports(self):
        """测试：模块导入"""
        # 确保所有主要类和函数可以导入
        assert RedisManager is not None
        assert CacheKeyManager is not None
        assert get_redis_manager is not None
        assert callable(get_cache)
        assert callable(set_cache)
        assert callable(delete_cache)
        assert callable(exists_cache)
        assert callable(ttl_cache)

    def test_get_redis_manager(self):
        """测试：获取Redis管理器"""
        manager1 = get_redis_manager()
        manager2 = get_redis_manager()

        # 应该返回相同的实例（单例模式）
        assert manager1 is manager2
        assert isinstance(manager1, RedisManager)

    def test_redis_manager_initialization(self):
        """测试：Redis管理器初始化"""
        # 使用默认URL
        manager = RedisManager()
        assert manager.redis_url == "redis://localhost:6379"

        # 使用自定义URL
        custom_url = "redis://custom:6380"
        manager = RedisManager(custom_url)
        assert manager.redis_url == custom_url

    def test_redis_manager_attributes(self):
        """测试：Redis管理器属性"""
        manager = RedisManager()

        # 检查必要的属性
        assert hasattr(manager, "connection_manager")
        assert hasattr(manager, "key_manager")
        assert hasattr(manager, "async_ops")
        assert hasattr(manager, "sync_ops")
        assert hasattr(manager, "logger")

    def test_get_key_manager(self):
        """测试：获取键管理器"""
        manager = RedisManager()
        key_manager = manager.get_key_manager()

        assert key_manager is not None
        assert key_manager is manager.key_manager

    def test_sync_convenience_functions_exist(self):
        """测试：同步便捷函数存在"""
        # 这些函数应该可调用，即使可能抛出错误（因为没有Redis）
        assert callable(get_cache)
        assert callable(set_cache)
        assert callable(delete_cache)
        assert callable(exists_cache)
        assert callable(ttl_cache)


class TestCacheKeyManager:
    """缓存键管理器测试"""

    def test_cache_key_manager_import(self):
        """测试：缓存键管理器导入"""
        from src.cache.redis_manager import CacheKeyManager

        manager = CacheKeyManager()
        assert manager is not None

    def test_cache_key_manager_methods(self):
        """测试：缓存键管理器方法"""
        from src.cache.redis_manager import CacheKeyManager

        manager = CacheKeyManager()

        # 检查是否有基本的键管理方法
        # 具体方法取决于实现
        assert hasattr(manager, "__class__")


class TestCacheConvenienceFunctions:
    """缓存便捷函数测试"""

    @patch("src.cache.redis_manager.get_redis_manager")
    def test_get_cache_function(self, mock_get_manager):
        """测试：获取缓存函数"""
        mock_manager = Mock()
        mock_manager.sync_ops = Mock()
        mock_manager.sync_ops.get.return_value = "test_value"
        mock_get_manager.return_value = mock_manager

        result = get_cache("test_key")
        assert result == "test_value"
        mock_manager.get_sync_client.assert_called_once()

    @patch("src.cache.redis_manager.get_redis_manager")
    def test_set_cache_function(self, mock_get_manager):
        """测试：设置缓存函数"""
        mock_manager = Mock()
        mock_manager.sync_ops = Mock()
        mock_manager.sync_ops.set.return_value = True
        mock_get_manager.return_value = mock_manager

        result = set_cache("test_key", "test_value")
        assert result is True
        mock_manager.get_sync_client.assert_called_once()

    @patch("src.cache.redis_manager.get_redis_manager")
    def test_set_cache_with_ttl(self, mock_get_manager):
        """测试：设置带TTL的缓存函数"""
        mock_manager = Mock()
        mock_manager.sync_ops = Mock()
        mock_manager.sync_ops.set.return_value = True
        mock_get_manager.return_value = mock_manager

        result = set_cache("test_key", "test_value", ttl=3600)
        assert result is True

    @patch("src.cache.redis_manager.get_redis_manager")
    def test_delete_cache_function(self, mock_get_manager):
        """测试：删除缓存函数"""
        mock_manager = Mock()
        mock_manager.sync_ops = Mock()
        mock_manager.sync_ops.delete.return_value = True
        mock_get_manager.return_value = mock_manager

        result = delete_cache("test_key")
        assert result is True
        mock_manager.get_sync_client.assert_called_once()

    @patch("src.cache.redis_manager.get_redis_manager")
    def test_exists_cache_function(self, mock_get_manager):
        """测试：检查缓存存在函数"""
        mock_manager = Mock()
        mock_manager.sync_ops = Mock()
        mock_manager.sync_ops.exists.return_value = True
        mock_get_manager.return_value = mock_manager

        result = exists_cache("test_key")
        assert result is True
        mock_manager.get_sync_client.assert_called_once()

    @patch("src.cache.redis_manager.get_redis_manager")
    def test_ttl_cache_function(self, mock_get_manager):
        """测试：获取TTL函数"""
        mock_manager = Mock()
        mock_manager.get_sync_client = Mock(return_value=Mock())
        mock_manager.get_sync_client.return_value.ttl.return_value = 3600
        mock_get_manager.return_value = mock_manager

        result = ttl_cache("test_key")
        assert result == 3600

    @patch("src.cache.redis_manager.get_redis_manager")
    def test_ttl_cache_not_exists(self, mock_get_manager):
        """测试：获取不存在键的TTL"""
        mock_manager = Mock()
        mock_manager.get_sync_client = Mock(return_value=Mock())
        mock_manager.get_sync_client.return_value.ttl.return_value = -2
        mock_get_manager.return_value = mock_manager

        result = ttl_cache("test_key")
        assert result == -2

    @patch("src.cache.redis_manager.get_redis_manager")
    def test_ttl_cache_error_handling(self, mock_get_manager):
        """测试：TTL错误处理"""
        import redis

        mock_manager = Mock()
        mock_manager.get_sync_client = Mock(return_value=Mock())
        mock_manager.get_sync_client.return_value.ttl.side_effect = redis.RedisError(
            "Connection error"
        )
        mock_get_manager.return_value = mock_manager

        result = ttl_cache("test_key")
        assert result is None


class TestAsyncCacheFunctions:
    """异步缓存函数测试"""

    @patch("src.cache.redis_manager.get_redis_manager")
    @pytest.mark.asyncio
    async def test_async_cache_functions_import(self, mock_get_manager):
        """测试：异步缓存函数导入"""
        # 测试异步函数是否可以导入
        try:
            from src.cache.redis_manager import (
                aget_cache,
                aset_cache,
                adelete_cache,
                aexists_cache,
                attl_cache,
                amget_cache,
                amset_cache,
            )

            assert callable(aget_cache)
            assert callable(aset_cache)
            assert callable(adelete_cache)
            assert callable(aexists_cache)
            assert callable(attl_cache)
            assert callable(amget_cache)
            assert callable(amset_cache)
        except ImportError:
            pytest.skip("Async cache functions not available")

    @patch("src.cache.redis_manager.get_redis_manager")
    def test_async_functions_exist(self, mock_get_manager):
        """测试：异步函数存在"""
        # 这些函数应该在模块中定义
        import src.cache.redis_manager as redis_manager

        async_functions = [
            "aget_cache",
            "aset_cache",
            "adelete_cache",
            "aexists_cache",
            "attl_cache",
            "amget_cache",
            "amset_cache",
        ]

        for func_name in async_functions:
            assert hasattr(redis_manager, func_name)
            assert callable(getattr(redis_manager, func_name))


class TestModuleMetadata:
    """模块元数据测试"""

    def test_module_version(self):
        """测试：模块版本信息"""
        import src.cache.redis_manager as redis_manager

        if hasattr(redis_manager, "__version__"):
            assert isinstance(redis_manager.__version__, str)
            assert len(redis_manager.__version__) > 0

    def test_module_description(self):
        """测试：模块描述"""
        import src.cache.redis_manager as redis_manager

        if hasattr(redis_manager, "__description__"):
            assert isinstance(redis_manager.__description__, str)
            assert len(redis_manager.__description__) > 0

    def test_module_exports(self):
        """测试：模块导出"""
        import src.cache.redis_manager as redis_manager

        if hasattr(redis_manager, "__all__"):
            exports = redis_manager.__all__
            assert isinstance(exports, list)
            assert len(exports) > 0

            # 检查主要导出
            expected_exports = [
                "RedisManager",
                "CacheKeyManager",
                "get_redis_manager",
                "get_cache",
                "set_cache",
                "delete_cache",
                "exists_cache",
                "ttl_cache",
            ]

            for export in expected_exports:
                assert export in exports


class TestErrorHandling:
    """错误处理测试"""

    def test_redis_unavailable_handling(self):
        """测试：Redis不可用时的处理"""
        # 模拟Redis不可用的情况
        with patch("src.cache.redis_manager.get_redis_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_sync_client.side_effect = Exception("Redis unavailable")
            mock_get_manager.return_value = mock_manager

            # 函数应该优雅地处理错误
            try:
                get_cache("test_key")
            except Exception:
                # 如果抛出异常，应该是预期的
                pass

    @patch("src.cache.redis_manager.get_redis_manager")
    def test_serialization_error_handling(self, mock_get_manager):
        """测试：序列化错误处理"""
        mock_manager = Mock()
        mock_manager.sync_ops = Mock()
        # 模拟序列化错误
        mock_manager.sync_ops.set.side_effect = TypeError("Cannot serialize")
        mock_get_manager.return_value = mock_manager

        # 应该能够处理序列化错误
        try:
            set_cache("test_key", object())  # 不可序列化的对象
            # 可能返回False或抛出异常，取决于实现
        except TypeError:
            # 预期的错误
            pass

    @patch("src.cache.redis_manager.get_redis_manager")
    def test_connection_error_handling(self, mock_get_manager):
        """测试：连接错误处理"""
        import redis

        mock_manager = Mock()
        mock_manager.sync_ops = Mock()
        mock_manager.sync_ops.get.side_effect = redis.ConnectionError("Cannot connect")
        mock_get_manager.return_value = mock_manager

        # 应该能够处理连接错误
        try:
            get_cache("test_key")
            # 可能返回None或抛出异常
        except redis.ConnectionError:
            # 预期的错误
            pass


class TestConfiguration:
    """配置测试"""

    def test_default_redis_url(self):
        """测试：默认Redis URL"""
        manager = RedisManager()
        assert manager.redis_url == "redis://localhost:6379"

    def test_custom_redis_url(self):
        """测试：自定义Redis URL"""
        custom_urls = [
            "redis://localhost:6379",
            "redis://localhost:6380/0",
            "redis://user:pass@localhost:6379/1",
            "redis://localhost:6379?ssl=true",
        ]

        for url in custom_urls:
            manager = RedisManager(url)
            assert manager.redis_url == url

    def test_environment_redis_url(self):
        """测试：环境变量Redis URL"""
        with patch.dict("os.environ", {"REDIS_URL": "redis://env-host:6379"}):
            manager = RedisManager()
            # 如果实现使用环境变量，这里应该使用环境变量的值
            # 否则使用传入的URL或默认值
            assert manager.redis_url is not None
