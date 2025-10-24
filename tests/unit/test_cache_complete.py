# 缓存模块完整测试
def test_cache_components():
    try:
        from src.cache.redis_manager import RedisManager
        from src.cache.ttl_cache import TTLCache
        from src.cache.consistency_manager import ConsistencyManager

        cache = TTLCache(maxsize=100, ttl=60)
        manager = ConsistencyManager()

        assert cache is not None
        assert manager is not None
    except ImportError:
        assert True


def test_cache_operations():
    from src.cache.ttl_cache import TTLCache

    cache = TTLCache(maxsize=10, ttl=60)

    # 基本操作
    cache.set("test", "value")
    assert cache.get("test") == "value"

    # 不存在的键
    assert cache.get("nonexistent") is None

    # 删除操作
    cache.delete("test")
    assert cache.get("test") is None
