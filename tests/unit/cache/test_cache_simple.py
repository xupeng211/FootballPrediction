"""
缓存系统简单测试

测试Redis缓存和TTL缓存的基本功能
"""

import pytest
from unittest.mock import Mock, patch
import time


@pytest.mark.unit
class TestCacheSimple:
    """缓存系统基础测试类"""

    def test_redis_manager_import(self):
        """测试Redis管理器导入"""
        from src.cache.redis_manager import RedisManager

        # 验证类可以导入
        assert RedisManager is not None

    def test_redis_manager_initialization(self):
        """测试Redis管理器初始化"""
        from src.cache.redis_manager import RedisManager

        # 使用默认配置初始化
        redis_manager = RedisManager()

        # 验证基本属性
        assert hasattr(redis_manager, 'redis_client')
        assert hasattr(redis_manager, 'config')

    def test_ttl_cache_import(self):
        """测试TTL缓存导入"""
        from src.cache.ttl_cache import TTLCache

        # 验证类可以导入
        assert TTLCache is not None

    def test_ttl_cache_initialization(self):
        """测试TTL缓存初始化"""
        from src.cache.ttl_cache import TTLCache

        # 创建TTL缓存实例
        cache = TTLCache(ttl=60)

        # 验证基本属性
        assert hasattr(cache, 'cache')
        assert hasattr(cache, 'ttl')
        assert cache.ttl == 60

    def test_ttl_cache_set_and_get(self):
        """测试TTL缓存设置和获取"""
        from src.cache.ttl_cache import TTLCache

        cache = TTLCache(ttl=60)

        # 设置缓存
        cache.set('test_key', 'test_value')

        # 获取缓存
        value = cache.get('test_key')
        assert value == 'test_value'

    def test_ttl_cache_expiration(self):
        """测试TTL缓存过期"""
        from src.cache.ttl_cache import TTLCache

        # 创建短TTL缓存
        cache = TTLCache(ttl=1)

        # 设置缓存
        cache.set('test_key', 'test_value')

        # 立即获取，应该存在
        value = cache.get('test_key')
        assert value == 'test_value'

        # 等待过期
        time.sleep(2)

        # 获取缓存，应该已过期
        value = cache.get('test_key')
        assert value is None

    def test_ttl_cache_delete(self):
        """测试TTL缓存删除"""
        from src.cache.ttl_cache import TTLCache

        cache = TTLCache(ttl=60)

        # 设置缓存
        cache.set('test_key', 'test_value')

        # 删除缓存
        cache.delete('test_key')

        # 获取缓存，应该不存在
        value = cache.get('test_key')
        assert value is None

    def test_ttl_cache_clear(self):
        """测试TTL缓存清空"""
        from src.cache.ttl_cache import TTLCache

        cache = TTLCache(ttl=60)

        # 设置多个缓存
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')

        # 清空缓存
        cache.clear()

        # 验证缓存已清空
        assert cache.get('key1') is None
        assert cache.get('key2') is None

    def test_ttl_cache_exists(self):
        """测试TTL缓存存在性检查"""
        from src.cache.ttl_cache import TTLCache

        cache = TTLCache(ttl=60)

        # 检查不存在的键
        assert not cache.exists('nonexistent_key')

        # 设置缓存
        cache.set('test_key', 'test_value')

        # 检查存在的键
        assert cache.exists('test_key')

    def test_ttl_cache_keys(self):
        """测试TTL缓存键列表"""
        from src.cache.ttl_cache import TTLCache

        cache = TTLCache(ttl=60)

        # 设置多个缓存
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')

        # 获取键列表
        keys = cache.keys()
        assert 'key1' in keys
        assert 'key2' in keys

    @patch('src.cache.redis_manager.Redis')
    def test_redis_connection(self, mock_redis):
        """测试Redis连接"""
        from src.cache.redis_manager import RedisManager

        # Mock Redis客户端
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client

        # 创建Redis管理器
        redis_manager = RedisManager()

        # 验证Redis连接被创建
        mock_redis.assert_called_once()
        assert redis_manager.redis_client == mock_redis_client

    @patch('src.cache.redis_manager.Redis')
    def test_redis_set_and_get(self, mock_redis):
        """测试Redis设置和获取"""
        from src.cache.redis_manager import RedisManager

        # Mock Redis客户端
        mock_redis_client = Mock()
        mock_redis.return_value = mock_redis_client
        mock_redis_client.get.return_value = 'test_value'

        redis_manager = RedisManager()

        # 设置值
        redis_manager.set('test_key', 'test_value')

        # 获取值
        value = redis_manager.get('test_key')
        assert value == 'test_value'

        # 验证Redis操作被调用
        mock_redis_client.set.assert_called_once_with('test_key', 'test_value')
        mock_redis_client.get.assert_called_once_with('test_key')

    def test_cache_statistics(self):
        """测试缓存统计"""
        from src.cache.ttl_cache import TTLCache

        cache = TTLCache(ttl=60)

        # 获取初始统计
        stats = cache.get_statistics()
        assert isinstance(stats, dict)
        assert 'hits' in stats
        assert 'misses' in stats
        assert 'total_requests' in stats

        # 设置并获取缓存
        cache.set('test_key', 'test_value')
        cache.get('test_key')

        # 获取更新后的统计
        updated_stats = cache.get_statistics()
        assert updated_stats['hits'] > stats['hits']
        assert updated_stats['total_requests'] > stats['total_requests']


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.cache", "--cov-report=term-missing"])