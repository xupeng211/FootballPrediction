"""
from unittest.mock import AsyncMock, Mock, patch
import asyncio
额外的Redis缓存测试，专门覆盖遗漏的代码路径
"""

import json
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest
from redis import RedisError

# 添加src目录到Python路径
src_path = os.path.join(os.path.dirname(__file__), "..", "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.cache.redis_manager import CacheKeyManager, RedisManager  # noqa: E402


class TestMissingCodePaths:
    """测试遗漏的代码路径以提高覆盖率"""

    def setup_method(self):
        self.redis_manager = RedisManager()

    def test_get_with_json_decode_error_exception(self):
        """测试get操作的通用异常处理"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.get.side_effect = Exception("Generic error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = self.redis_manager.get("key", "default")
            assert result == "default"
            mock_logger.error.assert_called()

    def test_set_with_generic_exception(self):
        """测试set操作的通用异常处理"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.setex.side_effect = Exception("Generic set error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = self.redis_manager.set("key", "value")
            assert result is False
            mock_logger.error.assert_called()

    def test_delete_with_generic_exception(self):
        """测试delete操作的通用异常处理"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.delete.side_effect = Exception("Generic delete error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = self.redis_manager.delete("key")
            assert result == 0
            mock_logger.error.assert_called()

    def test_exists_with_redis_error(self):
        """测试exists操作Redis错误"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client

        from redis.exceptions import RedisError

        mock_client.exists.side_effect = RedisError("Exists error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = self.redis_manager.exists("key")
            assert result == 0
            mock_logger.error.assert_called()

    def test_exists_with_generic_exception(self):
        """测试exists操作通用异常"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.exists.side_effect = Exception("Generic exists error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = self.redis_manager.exists("key")
            assert result == 0
            mock_logger.error.assert_called()

    def test_ttl_with_redis_error(self):
        """测试ttl操作Redis错误"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client

        mock_client.ttl.side_effect = RedisError("TTL error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = self.redis_manager.ttl("key")
            assert result == -2
            mock_logger.error.assert_called()

    def test_ttl_with_generic_exception(self):
        """测试ttl操作通用异常"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.ttl.side_effect = Exception("Generic TTL error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = self.redis_manager.ttl("key")
            assert result == -2
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_aget_with_generic_exception(self):
        """测试异步get的通用异常处理"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client
        mock_client.get.side_effect = Exception("Async generic error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = await self.redis_manager.aget("key", "default")
            assert result == "default"
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_aset_with_generic_exception(self):
        """测试异步set的通用异常处理"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client
        mock_client.setex.side_effect = Exception("Async set error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = await self.redis_manager.aset("key", "value")
            assert result is False
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_adelete_with_generic_exception(self):
        """测试异步delete的通用异常处理"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client
        mock_client.delete.side_effect = Exception("Async delete error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = await self.redis_manager.adelete("key")
            assert result == 0
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_aexists_with_redis_error(self):
        """测试异步exists操作Redis错误"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client

        mock_client.exists.side_effect = RedisError("Async exists error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = await self.redis_manager.aexists("key")
            assert result == 0
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_aexists_with_generic_exception(self):
        """测试异步exists操作通用异常"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client
        mock_client.exists.side_effect = Exception("Generic async exists error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = await self.redis_manager.aexists("key")
            assert result == 0
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_attl_with_redis_error(self):
        """测试异步ttl操作Redis错误"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client

        mock_client.ttl.side_effect = RedisError("Async TTL error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = await self.redis_manager.attl("key")
            assert result == -2
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_attl_with_generic_exception(self):
        """测试异步ttl操作通用异常"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client
        mock_client.ttl.side_effect = Exception("Generic async TTL error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = await self.redis_manager.attl("key")
            assert result == -2
            mock_logger.error.assert_called()

    def test_mget_with_generic_exception(self):
        """测试mget操作通用异常"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.mget.side_effect = Exception("Generic mget error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = self.redis_manager.mget(["key1", "key2"], "default")
            assert result == ["default", "default"]
            mock_logger.error.assert_called()

    def test_mset_with_generic_exception(self):
        """测试mset操作通用异常"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.mset.side_effect = Exception("Generic mset error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = self.redis_manager.mset({"key": "value"})
            assert result is False
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_amget_with_redis_error(self):
        """测试异步mget Redis错误"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client

        mock_client.mget.side_effect = RedisError("Async mget error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = await self.redis_manager.amget(["key"], "default")
            assert result == ["default"]
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_amget_with_generic_exception(self):
        """测试异步mget通用异常"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client
        mock_client.mget.side_effect = Exception("Generic async mget error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = await self.redis_manager.amget(["key"], "default")
            assert result == ["default"]
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_amset_no_client(self):
        """测试异步mset无客户端"""
        with patch.object(self.redis_manager, "get_async_client", return_value=None):
            result = await self.redis_manager.amset({"key": "value"})
            assert result is False

    @pytest.mark.asyncio
    async def test_amset_empty_mapping(self):
        """测试异步mset空mapping"""
        result = await self.redis_manager.amset({})
        assert result is False

    @pytest.mark.asyncio
    async def test_amset_with_redis_error(self):
        """测试异步mset Redis错误"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client

        mock_client.mset.side_effect = RedisError("Async mset error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = await self.redis_manager.amset({"key": "value"})
            assert result is False
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_amset_with_generic_exception(self):
        """测试异步mset通用异常"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client
        mock_client.mset.side_effect = Exception("Generic async mset error")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = await self.redis_manager.amset({"key": "value"})
            assert result is False
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_aping_with_redis_error(self):
        """测试异步ping Redis错误"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client
        mock_client.ping.side_effect = Exception("Async ping failed")

        with patch("src.cache.redis_manager.logger") as mock_logger:
            result = await self.redis_manager.aping()
            assert result is False
            mock_logger.error.assert_called()

    def test_set_with_cache_type_none_ttl(self):
        """测试set操作cache_type为None时的TTL处理"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.setex.return_value = True

        # 测试ttl为None且cache_type为None
        result = self.redis_manager.set("key", "value", ttl=None, cache_type=None)
        assert result is True
        # 应该使用默认TTL
        mock_client.setex.assert_called_with("key", 1800, "value")

    @pytest.mark.asyncio
    async def test_aset_with_cache_type_none_ttl(self):
        """测试异步set操作cache_type为None时的TTL处理"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client
        mock_client.setex.return_value = True

        # 测试ttl为None且cache_type为None
        result = await self.redis_manager.aset(
            "key", "value", ttl=None, cache_type=None
        )
        assert result is True
        # 应该使用默认TTL
        mock_client.setex.assert_called_with("key", 1800, "value")

    def test_set_debug_logging(self):
        """测试set操作的debug日志"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.setex.return_value = True

        with patch("src.cache.redis_manager.logger") as mock_logger:
            self.redis_manager.set("test_key", "test_value", ttl=3600)
            # 应该记录debug日志
            mock_logger.debug.assert_called()

    def test_delete_debug_logging(self):
        """测试delete操作的debug日志"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.delete.return_value = 2

        with patch("src.cache.redis_manager.logger") as mock_logger:
            self.redis_manager.delete("key1", "key2")
            # 应该记录debug日志
            mock_logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_async_delete_debug_logging(self):
        """测试异步delete操作的debug日志"""
        mock_client = AsyncMock()
        self.redis_manager._async_client = mock_client
        mock_client.delete.return_value = 1

        with patch("src.cache.redis_manager.logger") as mock_logger:
            await self.redis_manager.adelete("async_key")
            # 应该记录debug日志
            mock_logger.debug.assert_called()

    def test_list_serialization(self):
        """测试列表序列化"""
        mock_client = Mock()
        self.redis_manager._sync_client = mock_client
        mock_client.setex.return_value = True

        test_list = [1, 2, {"nested": "object"}]
        result = self.redis_manager.set("list_key", test_list)

        assert result is True
        expected_json = json.dumps(test_list, ensure_ascii=False, default=str)
        mock_client.setex.assert_called_with("list_key", 1800, expected_json)

    def test_unknown_prefix_warning(self):
        """测试未知前缀警告"""
        with patch("src.cache.redis_manager.logger") as mock_logger:
            key = CacheKeyManager.build_key("unknown_prefix", 123)
            assert key == "unknown_prefix:123"
            mock_logger.warning.assert_called_with("未知的Key前缀: unknown_prefix")

    def test_multiple_kwargs_key_building(self):
        """测试多个kwargs的Key构建"""
        key = CacheKeyManager.build_key(
            "complex", 123, "data", type="special", version="v2", status="active"
        )
        assert "type:special" in key
        assert "version:v2" in key
        assert "status:active" in key

    @pytest.mark.asyncio
    async def test_get_async_client_already_exists(self):
        """测试获取已存在的异步客户端"""
        # 设置已存在的客户端
        mock_client = Mock()
        self.redis_manager._async_client = mock_client

        client = await self.redis_manager.get_async_client()
        assert client is mock_client

    @pytest.mark.asyncio
    async def test_async_init_pool_failure_logging(self):
        """测试异步连接池初始化失败日志"""
        with patch("redis.asyncio.ConnectionPool.from_url") as mock_pool:
            mock_pool.side_effect = Exception("Async pool failed")

            with patch("src.cache.redis_manager.logger") as mock_logger:
                await self.redis_manager._init_async_pool()
                mock_logger.error.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
