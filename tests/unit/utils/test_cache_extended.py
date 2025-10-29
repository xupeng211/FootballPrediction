import pytest

from src.cache.ttl_cache import TTLCache


@pytest.mark.unit
@pytest.mark.cache
def test_ttl_cache_extended():
    cache = TTLCache(maxsize=100, ttl=60)

    # 测试基本操作
    cache.set("key1", "value1")
    cache.set("key2", "value2")

    assert cache.get("key1") == "value1"
    assert cache.get("key2") == "value2"

    # 测试更新
    cache.set("key1", "new_value")
    assert cache.get("key1") == "new_value"

    # 测试删除
    cache.delete("key1")
    assert cache.get("key1") is None


def test_cache_size_limit():
    cache = TTLCache(maxsize=2, ttl=60)
    cache.set("1", "a")
    cache.set("2", "b")
    cache.set("3", "c")  # 应该淘汰"1"

    assert cache.get("1") is None
    assert cache.get("2") == "b"
    assert cache.get("3") == "c"
