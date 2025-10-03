"""
测试MemoryCache的TTL过期修复
"""

import time
from src.cache.optimization import MemoryCache

def test_cache_ttl_expiration():
    """测试TTL过期功能是否正常工作"""
    cache = MemoryCache(ttl=1)  # 1秒过期

    # 设置值
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    # 等待过期
    time.sleep(1.1)

    # 获取过期的值，应该返回None而不是报错
    value = cache.get("key1")
    assert value is None

    # 检查统计
    assert cache._stats.errors == 0
    assert cache._stats.misses >= 1

    print("✅ TTL过期功能正常工作！")

if __name__ == "__main__":
    test_cache_ttl_expiration()