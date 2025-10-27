# 缓存简单测试
import pytest

from src.cache.consistency_manager import ConsistencyManager
from src.cache.ttl_cache import TTLCache


@pytest.mark.unit
@pytest.mark.cache
def test_ttl_cache_basic():
    cache = TTLCache(maxsize=10, ttl=60)
    cache.set("key", "value")
    assert cache.get("key") == "value"


def test_consistency_manager():
    manager = ConsistencyManager()
    assert manager is not None


def test_cache_size_limit():
    cache = TTLCache(maxsize=2, ttl=60)
    cache.set("1", "a")
    cache.set("2", "b")
    cache.set("3", "c")  # 应该淘汰"1"
    assert cache.get("1") is None
    assert cache.get("2") == "b"
    assert cache.get("3") == "c"
