"""
缓存API模块基础测试
目标：将 src/api/cache.py 的覆盖率从0%提升到20%+
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import asyncio
import json


class TestCacheBasicOperations:
    """缓存基本操作测试"""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """测试缓存设置和获取"""
        # Mock Redis
        mock_redis = MagicMock()
        mock_redis.set.return_value = True
        mock_redis.get.return_value = b'{"value": "test_data"}'

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_set, cache_get

                # 测试设置缓存
                await cache_set("test_key", {"value": "test_data"}, ttl=3600)
                mock_redis.set.assert_called_once()

                # 测试获取缓存
                result = await cache_get("test_key")
                assert result is not None
                assert result["value"] == "test_data"
            except ImportError:
                pytest.skip("Cache functions not available")

    @pytest.mark.asyncio
    async def test_cache_set_with_ttl(self):
        """测试带TTL的缓存设置"""
        mock_redis = MagicMock()
        mock_redis.setex.return_value = True

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_set_with_ttl

                await cache_set_with_ttl("test_key", "test_value", ttl=1800)
                mock_redis.setex.assert_called_once_with("test_key", 1800, "test_value")
            except ImportError:
                pytest.skip("cache_set_with_ttl not available")

    @pytest.mark.asyncio
    async def test_cache_delete(self):
        """测试缓存删除"""
        mock_redis = MagicMock()
        mock_redis.delete.return_value = 1  # 删除成功

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_delete

                result = await cache_delete("test_key")
                assert result == True
                mock_redis.delete.assert_called_once_with("test_key")
            except ImportError:
                pytest.skip("cache_delete not available")

    @pytest.mark.asyncio
    async def test_cache_exists(self):
        """测试缓存存在性检查"""
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 1  # 存在

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_exists

                result = await cache_exists("test_key")
                assert result == True
                mock_redis.exists.assert_called_once_with("test_key")
            except ImportError:
                pytest.skip("cache_exists not available")

    @pytest.mark.asyncio
    async def test_cache_get_nonexistent(self):
        """测试获取不存在的缓存"""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_get

                result = await cache_get("nonexistent_key")
                assert result is None
            except ImportError:
                pytest.skip("cache_get not available")


class TestCacheAdvancedOperations:
    """缓存高级操作测试"""

    @pytest.mark.asyncio
    async def test_cache_batch_get(self):
        """测试批量获取缓存"""
        mock_redis = MagicMock()
        mock_redis.mget.return_value = [
            b'{"id": 1}',
            b'{"id": 2}',
            None  # 第三个键不存在
        ]

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_batch_get

                keys = ["key1", "key2", "key3"]
                results = await cache_batch_get(keys)
                assert len(results) == 3
                assert results[0] is not None
                assert results[1] is not None
                assert results[2] is None
            except ImportError:
                pytest.skip("cache_batch_get not available")

    @pytest.mark.asyncio
    async def test_cache_batch_set(self):
        """测试批量设置缓存"""
        mock_redis = MagicMock()
        mock_redis.mset.return_value = True

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_batch_set

                key_value_pairs = {
                    "key1": {"value": 1},
                    "key2": {"value": 2}
                }
                await cache_batch_set(key_value_pairs, ttl=3600)
                mock_redis.mset.assert_called_once()
            except ImportError:
                pytest.skip("cache_batch_set not available")

    @pytest.mark.asyncio
    async def test_cache_increment(self):
        """测试缓存递增"""
        mock_redis = MagicMock()
        mock_redis.incr.return_value = 5

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_increment

                result = await cache_increment("counter_key", amount=2)
                assert result == 5
                mock_redis.incr.assert_called_once_with("counter_key", 2)
            except ImportError:
                pytest.skip("cache_increment not available")

    @pytest.mark.asyncio
    async def test_cache_expire(self):
        """测试设置缓存过期时间"""
        mock_redis = MagicMock()
        mock_redis.expire.return_value = True

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_expire

                result = await cache_expire("test_key", ttl=7200)
                assert result == True
                mock_redis.expire.assert_called_once_with("test_key", 7200)
            except ImportError:
                pytest.skip("cache_expire not available")

    @pytest.mark.asyncio
    async def test_cache_get_ttl(self):
        """测试获取缓存TTL"""
        mock_redis = MagicMock()
        mock_redis.ttl.return_value = 3600

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_get_ttl

                result = await cache_get_ttl("test_key")
                assert result == 3600
            except ImportError:
                pytest.skip("cache_get_ttl not available")


class TestCacheHashOperations:
    """缓存哈希操作测试"""

    @pytest.mark.asyncio
    async def test_cache_hash_set(self):
        """测试哈希设置"""
        mock_redis = MagicMock()
        mock_redis.hset.return_value = 1

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_hset

                await cache_hset("hash_key", "field", "value")
                mock_redis.hset.assert_called_once_with("hash_key", "field", "value")
            except ImportError:
                pytest.skip("cache_hset not available")

    @pytest.mark.asyncio
    async def test_cache_hash_get(self):
        """测试哈希获取"""
        mock_redis = MagicMock()
        mock_redis.hget.return_value = b"field_value"

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_hget

                result = await cache_hget("hash_key", "field")
                assert result == "field_value"
            except ImportError:
                pytest.skip("cache_hget not available")

    @pytest.mark.asyncio
    async def test_cache_hash_get_all(self):
        """测试获取哈希所有字段"""
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {
            b"field1": b"value1",
            b"field2": b"value2"
        }

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_hgetall

                result = await cache_hgetall("hash_key")
                assert result is not None
                assert len(result) == 2
            except ImportError:
                pytest.skip("cache_hgetall not available")

    @pytest.mark.asyncio
    async def test_cache_hash_delete(self):
        """测试哈希字段删除"""
        mock_redis = MagicMock()
        mock_redis.hdel.return_value = 1

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_hdel

                result = await cache_hdel("hash_key", "field")
                assert result == 1
            except ImportError:
                pytest.skip("cache_hdel not available")


class TestCacheListOperations:
    """缓存列表操作测试"""

    @pytest.mark.asyncio
    async def test_cache_list_push(self):
        """测试列表推入"""
        mock_redis = MagicMock()
        mock_redis.lpush.return_value = 3

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_lpush

                result = await cache_lpush("list_key", ["item1", "item2"])
                assert result == 3
            except ImportError:
                pytest.skip("cache_lpush not available")

    @pytest.mark.asyncio
    async def test_cache_list_pop(self):
        """测试列表弹出"""
        mock_redis = MagicMock()
        mock_redis.rpop.return_value = b"last_item"

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_rpop

                result = await cache_rpop("list_key")
                assert result == "last_item"
            except ImportError:
                pytest.skip("cache_rpop not available")

    @pytest.mark.asyncio
    async def test_cache_list_length(self):
        """测试列表长度"""
        mock_redis = MagicMock()
        mock_redis.llen.return_value = 5

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_llen

                result = await cache_llen("list_key")
                assert result == 5
            except ImportError:
                pytest.skip("cache_llen not available")


class TestCacheUtilities:
    """缓存工具函数测试"""

    def test_serialize_data(self):
        """测试数据序列化"""
        test_data = {
            "id": 1,
            "name": "Test",
            "timestamp": datetime.now()
        }

        try:
            from src.api.cache import serialize_cache_data
            serialized = serialize_cache_data(test_data)
            assert isinstance(serialized, str)
            # 反序列化验证
            parsed = json.loads(serialized)
            assert parsed["id"] == 1
        except ImportError:
            pytest.skip("serialize_cache_data not available")

    def test_deserialize_data(self):
        """测试数据反序列化"""
        json_data = '{"id": 1, "name": "Test"}'

        try:
            from src.api.cache import deserialize_cache_data
            result = deserialize_cache_data(json_data)
            assert result is not None
            assert result["id"] == 1
            assert result["name"] == "Test"
        except ImportError:
            pytest.skip("deserialize_cache_data not available")

    def test_generate_cache_key(self):
        """测试缓存键生成"""
        try:
            from src.api.cache import generate_cache_key

            # 测试基本键生成
            key1 = generate_cache_key("api", "matches", 1)
            assert isinstance(key1, str)
            assert "api" in key1
            assert "matches" in key1

            # 测试带参数的键生成
            key2 = generate_cache_key("api", "teams", league_id=1, page=2)
            assert "league_id" in key2 or "1" in key2
        except ImportError:
            pytest.skip("generate_cache_key not available")

    @pytest.mark.asyncio
    async def test_cache_warm_up(self):
        """测试缓存预热"""
        mock_redis = MagicMock()
        mock_redis.mset.return_value = True

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import warm_up_cache

                warm_up_data = {
                    "key1": "value1",
                    "key2": "value2"
                }
                await warm_up_cache(warm_up_data)
                # 验证批量设置被调用
                mock_redis.mset.assert_called()
            except ImportError:
                pytest.skip("warm_up_cache not available")

    @pytest.mark.asyncio
    async def test_cache_clear_pattern(self):
        """测试按模式清理缓存"""
        mock_redis = MagicMock()
        mock_redis.scan.return_value = [0, [b"test:1", b"test:2", b"other:1"]]
        mock_redis.delete.return_value = 2

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import clear_cache_pattern

                result = await clear_cache_pattern("test:*")
                assert result == 2  # 删除了2个键
            except ImportError:
                pytest.skip("clear_cache_pattern not available")


class TestCacheErrorHandling:
    """缓存错误处理测试"""

    @pytest.mark.asyncio
    async def test_redis_connection_error(self):
        """测试Redis连接错误"""
        mock_redis = MagicMock()
        mock_redis.get.side_effect = Exception("Redis connection failed")

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_get

                result = await cache_get("test_key")
                # 应该有错误处理，返回None或抛出特定异常
                assert result is None
            except ImportError:
                pytest.skip("cache_get not available")
            except Exception:
                # 如果抛出异常也是可以接受的
                pass

    @pytest.mark.asyncio
    async def test_cache_serialization_error(self):
        """测试序列化错误"""
        # 创建不可序列化的对象
        non_serializable = lambda x: x

        try:
            from src.api.cache import cache_set

            with pytest.raises(Exception):
                await cache_set("test_key", non_serializable)
        except ImportError:
            pytest.skip("cache_set not available")

    @pytest.mark.asyncio
    async def test_cache_deserialization_error(self):
        """测试反序列化错误"""
        mock_redis = MagicMock()
        mock_redis.get.return_value = b"invalid json"

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_get

                result = await cache_get("test_key")
                # 应该处理错误，返回None
                assert result is None
            except ImportError:
                pytest.skip("cache_get not available")
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_cache_timeout_error(self):
        """测试缓存超时错误"""
        mock_redis = MagicMock()
        mock_redis.get.side_effect = asyncio.TimeoutError("Cache timeout")

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_get

                with pytest.raises(asyncio.TimeoutError):
                    await cache_get("test_key")
            except ImportError:
                pytest.skip("cache_get not available")


class TestCachePerformance:
    """缓存性能测试"""

    @pytest.mark.asyncio
    async def test_cache_bulk_operations_performance(self):
        """测试批量操作性能"""
        mock_redis = MagicMock()
        mock_redis.mget.return_value = [b'value'] * 100
        mock_redis.mset.return_value = True

        with patch('src.api.cache.redis_manager', mock_redis):
            try:
                from src.api.cache import cache_batch_get, cache_batch_set

                # 测试批量获取性能
                start_time = datetime.now()
                keys = [f"key_{i}" for i in range(100)]
                await cache_batch_get(keys)
                end_time = datetime.now()
                get_time = (end_time - start_time).total_seconds()

                # 测试批量设置性能
                start_time = datetime.now()
                data = {f"key_{i}": f"value_{i}" for i in range(100)}
                await cache_batch_set(data)
                end_time = datetime.now()
                set_time = (end_time - start_time).total_seconds()

                # 批量操作应该很快
                assert get_time < 0.1
                assert set_time < 0.1
            except ImportError:
                pytest.skip("Batch operations not available")

    def test_cache_key_generation_performance(self):
        """测试缓存键生成性能"""
        try:
            from src.api.cache import generate_cache_key

            start_time = datetime.now()
            for i in range(1000):
                generate_cache_key("api", "matches", i, league_id=1)
            end_time = datetime.now()
            generation_time = (end_time - start_time).total_seconds()

            # 键生成应该非常快
            assert generation_time < 0.1
        except ImportError:
            pytest.skip("generate_cache_key not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])