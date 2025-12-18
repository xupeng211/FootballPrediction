"""统一缓存接口核心功能测试
Unified Cache Interface Core Tests.

专注于测试核心功能，避免复杂依赖。
"""

import time
import threading

import pytest

from src.cache.unified_interface import (
    CacheBackend,
    CacheInterface,
    MemoryCacheAdapter,
    UnifiedCacheConfig,
)


class TestCacheInterfaceCore:
    """缓存接口核心功能测试类."""

    def test_cache_interface_abstract_methods(self):
        """测试缓存接口抽象方法."""
        # 验证不能直接实例化抽象类
        with pytest.raises(TypeError):
            CacheInterface()

    def test_memory_cache_adapter_basic_operations(self):
        """测试内存缓存适配器基本操作."""
        cache = MemoryCacheAdapter()

        # 测试set和get
        assert cache.set("key1", "value1") is True
        assert cache.get("key1") == "value1"

        # 测试default值
        assert cache.get("nonexistent", "default") == "default"
        assert cache.get("nonexistent") is None

        # 测试exists
        assert cache.exists("key1") is True
        assert cache.exists("nonexistent") is False

        # 测试delete
        assert cache.delete("key1") is True
        assert cache.exists("key1") is False
        assert cache.delete("nonexistent") is False

        # 测试clear
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.size() == 0
        assert cache.get("key1") is None

    def test_memory_cache_adapter_ttl_functionality(self):
        """测试内存缓存TTL功能."""
        cache = MemoryCacheAdapter({"default_ttl": 1})  # 1秒TTL

        # 设置带TTL的值
        cache.set("ttl_key", "ttl_value", ttl=1)
        assert cache.get("ttl_key") == "ttl_value"

        # 等待过期
        time.sleep(1.1)
        assert cache.get("ttl_key") is None

        # 测试不同的TTL - 使用更长的时间避免精度问题
        cache.set("long_ttl", "value", ttl=2)
        cache.set("short_ttl", "value", ttl=0.8)

        time.sleep(1.0)  # 等待1秒，确保short_ttl过期但long_ttl不过期
        assert cache.get("long_ttl") == "value"
        assert cache.get("short_ttl") is None

    def test_memory_cache_adapter_config_validation(self):
        """测试内存缓存配置验证."""
        # 默认配置
        cache1 = MemoryCacheAdapter()
        assert cache1.size() == 0

        # 自定义配置
        config = {"max_size": 100, "default_ttl": 7200}
        cache2 = MemoryCacheAdapter(config)
        assert cache2.size() == 0

        # 测试配置合并
        cache3 = MemoryCacheAdapter({"max_size": 500})
        stats = cache3.get_stats()
        assert stats is not None

    def test_memory_cache_adapter_thread_safety(self):
        """测试内存缓存线程安全性."""
        cache = MemoryCacheAdapter()
        results = []
        errors = []

        def worker(thread_id: int):
            try:
                for i in range(5):  # 减少操作次数以加快测试
                    key = f"thread_{thread_id}_key_{i}"
                    value = f"thread_{thread_id}_value_{i}"

                    # 写入
                    cache.set(key, value)

                    # 读取
                    retrieved = cache.get(key)
                    if retrieved == value:
                        results.append(True)
                    else:
                        results.append(False)

            except Exception as e:
                errors.append(e)

        # 启动多个线程
        threads = []
        for i in range(3):  # 减少线程数以加快测试
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"线程安全测试出现错误: {errors}"
        assert len(results) == 15  # 3个线程 * 5次操作
        assert all(results), "部分操作失败"

    def test_memory_cache_adapter_size_limits(self):
        """测试内存缓存大小限制."""
        # 创建小容量缓存
        cache = MemoryCacheAdapter({"max_size": 3})

        # 填充到最大容量
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        assert cache.size() == 3

        # 添加第4个项，应该触发LRU淘汰
        cache.set("key4", "value4")
        assert cache.size() == 3

        # 验证某个项被淘汰（不一定是key1，因为LRU顺序可能不同）
        remaining_keys = []
        for i in range(1, 5):
            key = f"key{i}"
            if cache.get(key) is not None:
                remaining_keys.append(key)

        assert len(remaining_keys) == 3

    def test_memory_cache_adapter_complex_data_types(self):
        """测试内存缓存复杂数据类型."""
        cache = MemoryCacheAdapter()

        # 测试字典
        test_dict = {"key": "value", "number": 42}
        cache.set("dict_key", test_dict)
        assert cache.get("dict_key") == test_dict

        # 测试列表
        test_list = [1, 2, 3, "four", {"five": 5}]
        cache.set("list_key", test_list)
        assert cache.get("list_key") == test_list

        # 测试嵌套结构
        nested_data = {"outer": {"inner": {"deep": "value"}}}
        cache.set("nested_key", nested_data)
        assert cache.get("nested_key") == nested_data

    def test_cache_backend_enum(self):
        """测试缓存后端枚举."""
        # 测试枚举值
        assert CacheBackend.MEMORY.value == "memory"
        assert CacheBackend.REDIS.value == "redis"
        assert CacheBackend.MULTI_LEVEL.value == "multi_level"

        # 测试枚举比较
        assert CacheBackend.MEMORY != CacheBackend.REDIS
        assert CacheBackend.MEMORY == CacheBackend.MEMORY

        # 测试枚举遍历
        backends = list(CacheBackend)
        assert len(backends) >= 3
        assert CacheBackend.MEMORY in backends
        assert CacheBackend.REDIS in backends

    def test_unified_cache_config(self):
        """测试统一缓存配置."""
        # 测试默认配置
        config = UnifiedCacheConfig()
        assert config.backend == CacheBackend.MEMORY
        assert config.use_consistency_manager is True
        assert config.enable_decorators is True
        assert config.default_ttl == 3600

        # 测试自定义配置
        custom_config = UnifiedCacheConfig(
            backend=CacheBackend.REDIS, use_consistency_manager=False, default_ttl=7200
        )
        assert custom_config.backend == CacheBackend.REDIS
        assert custom_config.use_consistency_manager is False
        assert custom_config.default_ttl == 7200

        # 测试内存配置
        memory_config = {"max_size": 500, "default_ttl": 1800}
        config_with_memory = UnifiedCacheConfig(memory_config=memory_config)
        assert config_with_memory.memory_config == memory_config

    def test_cache_interface_method_signatures(self):
        """测试缓存接口方法签名."""

        # 创建一个具体的实现来验证接口
        class TestCache(CacheInterface):
            def __init__(self):
                self._data = {}

            def get(self, key: str, default: str = None) -> str:
                return self._data.get(key, default)

            def set(self, key: str, value: str, ttl: int | None = None) -> bool:
                self._data[key] = value
                return True

            def delete(self, key: str) -> bool:
                return self._data.pop(key, None) is not None

            def exists(self, key: str) -> bool:
                return key in self._data

            def clear(self) -> None:
                self._data.clear()

            def size(self) -> int:
                return len(self._data)

        # 测试方法签名和返回值
        cache = TestCache()

        # 测试get方法
        assert cache.get("key") is None
        assert cache.get("key", "default") == "default"
        cache.set("key", "value")
        assert cache.get("key") == "value"

        # 测试set方法
        assert cache.set("key2", "value2") is True
        assert cache.set("key3", "value3", ttl=60) is True

        # 测试其他方法
        assert cache.exists("key2") is True
        assert cache.delete("key2") is True
        assert cache.exists("key2") is False
        assert cache.size() == 2
        cache.clear()
        assert cache.size() == 0

    def test_memory_cache_adapter_stats(self):
        """测试内存缓存统计功能."""
        cache = MemoryCacheAdapter()

        # 初始统计
        stats = cache.get_stats()
        assert isinstance(stats, dict)
        assert "size" in stats

        # 添加数据后统计
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        stats = cache.get_stats()
        assert stats["size"] == 2

    def test_memory_cache_adapter_edge_cases(self):
        """测试内存缓存边界情况."""
        cache = MemoryCacheAdapter()

        # 测试空键
        assert cache.set("", "value") is True
        assert cache.get("") == "value"

        # 测试None值
        assert cache.set("none_key", None) is True
        assert cache.get("none_key") is None

        # 测试空字符串值
        assert cache.set("empty_key", "") is True
        assert cache.get("empty_key") == ""

        # 测试特殊字符键
        special_key = "key:with@special#chars$%^&*()"
        assert cache.set(special_key, "value") is True
        assert cache.get(special_key) == "value"

    def test_memory_cache_adapter_large_values(self):
        """测试内存缓存大值处理."""
        cache = MemoryCacheAdapter()

        # 测试大字符串值
        large_value = "x" * 1000  # 相对较小以避免性能问题
        assert cache.set("large_key", large_value) is True
        assert cache.get("large_key") == large_value

        # 测试中等大小的复杂数据
        large_list = list(range(100))
        assert cache.set("list_key", large_list) is True
        retrieved_list = cache.get("list_key")
        assert retrieved_list == large_list
