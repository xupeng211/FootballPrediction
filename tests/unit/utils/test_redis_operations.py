"""
测试Redis操作类
"""

import json
import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.cache.redis.core.connection_manager import RedisConnectionManager
from src.cache.redis.operations.sync_operations import RedisSyncOperations
from src.cache.redis.operations.async_operations import RedisAsyncOperations


class TestRedisSyncOperations:
    """测试Redis同步操作"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_connection_manager = Mock(spec=RedisConnectionManager)
        self.sync_ops = RedisSyncOperations(self.mock_connection_manager)

    def test_get_success(self):
        """测试成功的get操作"""
        mock_client = Mock()
        mock_client.get.return_value = b'"test_value"'
        self.mock_connection_manager._ensure_sync_client.return_value = mock_client

        _result = self.sync_ops.get("test_key")

        assert _result == '"test_value"'

    def test_get_none(self):
        """测试获取不存在的key"""
        mock_client = Mock()
        mock_client.get.return_value = None
        self.mock_connection_manager._ensure_sync_client.return_value = mock_client

        _result = self.sync_ops.get("test_key", "default")

        assert _result == "default"

    def test_get_json(self):
        """测试获取JSON数据"""
        mock_client = Mock()
        mock_client.get.return_value = b'{"key": "value"}'
        self.mock_connection_manager._ensure_sync_client.return_value = mock_client

        _result = self.sync_ops.get("test_key")

        assert _result == '{"key": "value"}'

    def test_set_with_string(self):
        """测试设置字符串值"""
        mock_client = Mock()
        mock_client.set.return_value = True
        self.mock_connection_manager._ensure_sync_client.return_value = mock_client

        _result = self.sync_ops.set("test_key", "test_value")

        assert result is True

    def test_set_with_dict(self):
        """测试设置字典值"""
        mock_client = Mock()
        mock_client.set.return_value = True
        self.mock_connection_manager._ensure_sync_client.return_value = mock_client

        _result = self.sync_ops.set("test_key", {"key": "value"})

        assert result is True
        # 验证JSON序列化
        mock_client.set.assert_called_once()
        args, kwargs = mock_client.set.call_args
        assert json.loads(kwargs["value"]) == {"key": "value"}

    def test_delete_success(self):
        """测试成功的删除操作"""
        mock_client = Mock()
        mock_client.delete.return_value = 3
        self.mock_connection_manager._ensure_sync_client.return_value = mock_client

        _result = self.sync_ops.delete("key1", "key2", "key3")

        assert _result == 3

    def test_exists_success(self):
        """测试检查key存在"""
        mock_client = Mock()
        mock_client.exists.return_value = 2
        self.mock_connection_manager._ensure_sync_client.return_value = mock_client

        _result = self.sync_ops.exists("key1", "key2", "key3")

        assert _result == 2

    def test_ttl_success(self):
        """测试获取TTL"""
        mock_client = Mock()
        mock_client.ttl.return_value = 300
        self.mock_connection_manager._ensure_sync_client.return_value = mock_client

        _result = self.sync_ops.ttl("test_key")

        assert _result == 300

    def test_mget_success(self):
        """测试批量获取"""
        mock_client = Mock()
        mock_client.mget.return_value = [b'{"a": 1}', b'{"b": 2}', None]
        self.mock_connection_manager._ensure_sync_client.return_value = mock_client

        _result = self.sync_ops.mget(["key1", "key2", "key3"], "default")

        assert _result == [{"a": 1}, {"b": 2}, "default"]

    def test_mset_success(self):
        """测试批量设置"""
        mock_client = Mock()
        mock_client.mset.return_value = True
        mock_pipeline = Mock()
        mock_client.pipeline.return_value = mock_pipeline
        mock_pipeline.__enter__ = Mock(return_value=mock_pipeline)
        mock_pipeline.__exit__ = Mock(return_value=None)
        self.mock_connection_manager._ensure_sync_client.return_value = mock_client

        mapping = {"key1": {"a": 1}, "key2": "value"}
        _result = self.sync_ops.mset(mapping, ttl=60)

        assert result is True

    def test_clear_all(self):
        """测试清空数据库"""
        mock_client = Mock()
        mock_client.flushdb.return_value = True
        self.mock_connection_manager._ensure_sync_client.return_value = mock_client

        _result = self.sync_ops.clear_all()

        assert result is True


class TestRedisAsyncOperations:
    """测试Redis异步操作"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_connection_manager = Mock(spec=RedisConnectionManager)
        self.async_ops = RedisAsyncOperations(self.mock_connection_manager)

    @pytest.mark.asyncio
    async def test_aget_success(self):
        """测试成功的异步get操作"""
        mock_client = AsyncMock()
        mock_client.get.return_value = b'"test_value"'
        self.mock_connection_manager.get_async_client.return_value = mock_client

        _result = await self.async_ops.aget("test_key")

        assert _result == '"test_value"'

    @pytest.mark.asyncio
    async def test_aset_with_dict(self):
        """测试异步设置字典值"""
        mock_client = AsyncMock()
        mock_client.setex.return_value = True
        self.mock_connection_manager.get_async_client.return_value = mock_client

        _result = await self.async_ops.aset("test_key", {"key": "value"})

        assert result is True

    @pytest.mark.asyncio
    async def test_adelete_success(self):
        """测试成功的异步删除操作"""
        mock_client = AsyncMock()
        mock_client.delete.return_value = 2
        self.mock_connection_manager.get_async_client.return_value = mock_client

        _result = await self.async_ops.adelete("key1", "key2")

        assert _result == 2

    @pytest.mark.asyncio
    async def test_aexists_success(self):
        """测试异步检查key存在"""
        mock_client = AsyncMock()
        mock_client.exists.return_value = 1
        self.mock_connection_manager.get_async_client.return_value = mock_client

        _result = await self.async_ops.aexists("test_key")

        assert _result == 1

    @pytest.mark.asyncio
    async def test_attl_success(self):
        """测试异步获取TTL"""
        mock_client = AsyncMock()
        mock_client.ttl.return_value = 300
        self.mock_connection_manager.get_async_client.return_value = mock_client

        _result = await self.async_ops.attl("test_key")

        assert _result == 300

    @pytest.mark.asyncio
    async def test_amget_success(self):
        """测试异步批量获取"""
        mock_client = AsyncMock()
        mock_client.mget.return_value = [b'{"a": 1}', b'{"b": 2}']
        self.mock_connection_manager.get_async_client.return_value = mock_client

        _result = await self.async_ops.amget(["key1", "key2"])

        assert _result == [{"a": 1}, {"b": 2}]

    @pytest.mark.asyncio
    async def test_amset_success(self):
        """测试异步批量设置"""
        mock_client = AsyncMock()
        mock_client.mset.return_value = True
        self.mock_connection_manager.get_async_client.return_value = mock_client

        # 测试不使用TTL的批量设置
        mapping = {"key1": {"a": 1}, "key2": {"b": 2}}
        _result = await self.async_ops.amset(mapping)

        assert result is True
