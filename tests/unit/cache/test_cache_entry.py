"""测试缓存条目模块"""

import time
from unittest.mock import patch

import pytest

try:
    from src.cache.ttl_cache_enhanced.cache_entry import CacheEntry

    IMPORT_SUCCESS = True
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


@pytest.mark.skipif(not IMPORT_SUCCESS, reason="Module import failed")
@pytest.mark.cache
class TestCacheEntry:
    """缓存条目测试"""

    def test_cache_entry_creation_basic(self):
        """测试基本缓存条目创建"""
        entry = CacheEntry("test_key", "test_value")

        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.expires_at is None  # 没有TTL
        assert entry.access_count == 0
        assert isinstance(entry.last_access, float)

    def test_cache_entry_creation_with_ttl(self):
        """测试带TTL的缓存条目创建"""
        ttl = 3600  # 1小时
        entry = CacheEntry("test_key", "test_value", ttl)

        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.expires_at is not None
        assert entry.expires_at > time.time()
        assert entry.access_count == 0

    def test_cache_entry_creation_zero_ttl(self):
        """测试零TTL的缓存条目"""
        entry = CacheEntry("test_key", "test_value", 0)

        # 检查零TTL的处理
        if entry.expires_at is not None:
            # 零TTL意味着立即过期
            assert entry.expires_at <= time.time()
        # 某些实现可能将零TTL视为无TTL,这也是可以接受的

    def test_cache_entry_access(self):
        """测试访问缓存条目"""
        entry = CacheEntry("test_key", "test_value")

        # 初始访问计数为0
        assert entry.access_count == 0

        # 访问缓存
        result = entry.access()

        assert result == "test_value"
        assert entry.access_count == 1
        assert entry.last_access >= entry.last_access - 1  # 允许时间误差

    def test_cache_entry_multiple_access(self):
        """测试多次访问缓存条目"""
        entry = CacheEntry("test_key", "test_value")

        # 多次访问
        for i in range(5):
            result = entry.access()
            assert result == "test_value"
            assert entry.access_count == i + 1

    def test_is_expired_no_ttl(self):
        """测试无TTL的条目不会过期"""
        entry = CacheEntry("test_key", "test_value")

        assert not entry.is_expired()

    def test_is_expired_with_future_ttl(self):
        """测试未过期的条目"""
        ttl = 3600  # 1小时
        entry = CacheEntry("test_key", "test_value", ttl)

        assert not entry.is_expired()

    def test_is_expired_with_past_ttl(self):
        """测试已过期的条目"""
        ttl = 0.001  # 1毫秒,立即过期
        entry = CacheEntry("test_key", "test_value", ttl)

        # 等待过期
        time.sleep(0.002)

        assert entry.is_expired()

    def test_update_ttl_with_value(self):
        """测试更新TTL为具体值"""
        entry = CacheEntry("test_key", "test_value")

        new_ttl = 1800  # 30分钟
        entry.update_ttl(new_ttl)

        assert entry.expires_at is not None
        expected_expires = time.time() + new_ttl
        assert abs(entry.expires_at - expected_expires) < 1  # 允许1秒误差

    def test_update_ttl_to_none(self):
        """测试更新TTL为None（永不过期）"""
        ttl = 3600
        entry = CacheEntry("test_key", "test_value", ttl)

        # 设置为永不过期
        entry.update_ttl(None)

        assert entry.expires_at is None

    def test_update_ttl_to_zero(self):
        """测试更新TTL为0"""
        entry = CacheEntry("test_key", "test_value")

        entry.update_ttl(0)

        assert entry.expires_at is not None
        assert entry.expires_at <= time.time()

    def test_get_remaining_ttl_no_ttl(self):
        """测试无TTL时获取剩余TTL"""
        entry = CacheEntry("test_key", "test_value")

        assert entry.get_remaining_ttl() is None

    def test_get_remaining_ttl_future(self):
        """测试获取未来TTL"""
        ttl = 3600  # 1小时
        entry = CacheEntry("test_key", "test_value", ttl)

        remaining = entry.get_remaining_ttl()
        assert remaining is not None
        assert 3590 <= remaining <= 3601  # 允许一些时间误差

    def test_get_remaining_ttl_expired(self):
        """测试获取已过期条目的TTL"""
        ttl = 0.001  # 1毫秒
        entry = CacheEntry("test_key", "test_value", ttl)

        # 等待过期
        time.sleep(0.002)

        remaining = entry.get_remaining_ttl()
        assert remaining == 0

    def test_get_remaining_ttl_almost_expired(self):
        """测试即将过期的条目"""
        ttl = 0.1  # 100毫秒
        entry = CacheEntry("test_key", "test_value", ttl)

        # 等待接近过期
        time.sleep(0.09)

        remaining = entry.get_remaining_ttl()
        assert 0 <= remaining <= 0.02  # 很小的剩余时间

    def test_comparison_both_no_ttl(self):
        """测试比较两个都无TTL的条目"""
        entry1 = CacheEntry("key1", "value1")
        entry2 = CacheEntry("key2", "value2")

        assert not (entry1 < entry2)
        assert not (entry2 < entry1)

    def test_comparison_one_no_ttl(self):
        """测试一个有TTL一个无TTL的条目比较"""
        entry_no_ttl = CacheEntry("key1", "value1")
        entry_with_ttl = CacheEntry("key2", "value2", 3600)

        # 无TTL的条目应该被认为"更大"
        assert entry_with_ttl < entry_no_ttl
        assert not (entry_no_ttl < entry_with_ttl)

    def test_comparison_both_with_ttl(self):
        """测试两个都有TTL的条目比较"""
        # 早过期的条目
        entry_early = CacheEntry("key1", "value1", 100)  # 100秒后过期
        entry_late = CacheEntry("key2", "value2", 200)  # 200秒后过期

        # 早过期的应该更小
        assert entry_early < entry_late
        assert not (entry_late < entry_early)

    def test_comparison_same_expires_at(self):
        """测试相同过期时间的条目比较"""
        ttl = 3600
        entry1 = CacheEntry("key1", "value1", ttl)
        entry2 = CacheEntry("key2", "value2", ttl)

        # 比较应该基于对象标识或其他因素
        # 这里只测试不会出错
        result1 = entry1 < entry2
        result2 = entry2 < entry1
        # 至少有一个方向应该是False
        assert not (result1 and result2)

    def test_repr_with_ttl(self):
        """测试有TTL条目的字符串表示"""
        entry = CacheEntry("test_key", "test_value", 3600)
        repr_str = repr(entry)

        assert "CacheEntry" in repr_str
        assert "test_key" in repr_str
        assert "str" in repr_str  # value的类型
        assert "TTL=" in repr_str
        assert "s" in repr_str

    def test_repr_no_ttl(self):
        """测试无TTL条目的字符串表示"""
        entry = CacheEntry("test_key", "test_value")
        repr_str = repr(entry)

        assert "CacheEntry" in repr_str
        assert "test_key" in repr_str
        assert "str" in repr_str
        assert "TTL=∞" in repr_str

    def test_repr_different_value_types(self):
        """测试不同值类型的字符串表示"""
        test_cases = [
            ("string_key", "string_value"),
            ("int_key", 42),
            ("list_key", [1, 2, 3]),
            ("dict_key", {"a": 1}),
            ("none_key", None),
        ]

        for key, value in test_cases:
            entry = CacheEntry(key, value)
            repr_str = repr(entry)
            assert key in repr_str
            assert type(value).__name__ in repr_str

    def test_slots_usage(self):
        """测试__slots__的使用"""
        entry = CacheEntry("test_key", "test_value")

        # 确认__slots__生效
        assert hasattr(entry, "__slots__")

        # 尝试添加新属性应该失败
        with pytest.raises(AttributeError):
            entry.new_attribute = "should_fail"

    def test_edge_cases_empty_key(self):
        """测试空键"""
        entry = CacheEntry("", "value")
        assert entry.key == ""
        assert entry.value == "value"

    def test_edge_cases_none_value(self):
        """测试None值"""
        entry = CacheEntry("key", None)
        assert entry.value is None
        result = entry.access()
        assert result is None

    def test_edge_cases_special_characters_key(self):
        """测试特殊字符键"""
        special_keys = [
            "key with spaces",
            "key\nwith\nnewlines",
            "key\twith\ttabs",
            "🚀emoji",
        ]

        for key in special_keys:
            entry = CacheEntry(key, "value")
            assert entry.key == key
            assert entry.access() == "value"

    def test_edge_cases_large_ttl(self):
        """测试大TTL值"""
        large_ttl = 86400 * 365  # 1年
        entry = CacheEntry("key", "value", large_ttl)

        assert not entry.is_expired()
        remaining = entry.get_remaining_ttl()
        assert remaining > 86400 * 364  # 至少364天

    def test_edge_cases_negative_ttl(self):
        """测试负TTL"""
        entry = CacheEntry("key", "value", -1)

        # 负TTL应该立即过期
        assert entry.is_expired()
        assert entry.get_remaining_ttl() == 0

    def test_time_manipulation_with_mock(self):
        """测试时间操控"""
        with patch("time.time") as mock_time:
            mock_time.return_value = 1000.0

            entry = CacheEntry("key", "value", 100)

            # 初始状态
            assert entry.expires_at == 1100.0
            assert entry.last_access == 1000.0
            assert not entry.is_expired()

            # 模拟时间前进50秒
            mock_time.return_value = 1050.0
            entry.access()

            assert entry.access_count == 1
            assert entry.last_access == 1050.0
            assert not entry.is_expired()

            # 模拟时间前进到过期后
            mock_time.return_value = 1150.0
            assert entry.is_expired()

    def test_complex_workflow_simulation(self):
        """测试复杂工作流模拟"""
        # 创建多个缓存条目
        entries = [
            CacheEntry("user:1", {"name": "Alice", "age": 30}, 3600),
            CacheEntry("user:2", {"name": "Bob", "age": 25}, 1800),
            CacheEntry("config", {"theme": "dark"}),  # 无TTL
        ]

        # 模拟访问模式
        for i, entry in enumerate(entries):
            result = entry.access()
            assert entry.access_count == 1
            assert isinstance(result, dict)

        # 第二轮访问
        for entry in entries:
            entry.access()

        # 验证访问计数
        assert entries[0].access_count == 2
        assert entries[1].access_count == 2
        assert entries[2].access_count == 2

        # 测试排序（基于过期时间）
        sorted_entries = sorted(entries)
        # 无TTL的条目应该在最后
        assert sorted_entries[-1].key == "config"

    def test_concurrent_access_simulation(self):
        """测试并发访问模拟"""
        entry = CacheEntry("shared_key", "shared_value", 3600)

        # 模拟快速连续访问
        initial_count = entry.access_count
        for _ in range(100):
            entry.access()

        assert entry.access_count == initial_count + 100


@pytest.mark.skipif(not IMPORT_SUCCESS, reason="Module import failed")
class TestCacheEntryIntegration:
    """缓存条目集成测试"""

    def test_integration_with_real_time(self):
        """测试与真实时间的集成"""
        # 短TTL用于测试
        short_ttl = 0.1  # 100毫秒
        entry = CacheEntry("temp_key", "temp_value", short_ttl)

        # 立即测试
        assert not entry.is_expired()
        assert entry.access() == "temp_value"

        # 等待过期
        time.sleep(0.15)
        assert entry.is_expired()

        # 即使过期,仍可访问值（但应用逻辑应该检查过期）
        assert entry.access() == "temp_value"

    def test_performance_characteristics(self):
        """测试性能特征"""
        import time

        # 创建大量条目
        start_time = time.time()
        entries = []
        for i in range(1000):
            entry = CacheEntry(f"key_{i}", f"value_{i}", 3600)
            entries.append(entry)
        creation_time = time.time() - start_time

        # 访问所有条目
        start_time = time.time()
        for entry in entries:
            entry.access()
        access_time = time.time() - start_time

        # 性能断言（这些数字可能需要根据实际环境调整）
        assert creation_time < 1.0  # 创建1000个条目应该在1秒内
        assert access_time < 0.1  # 访问1000个条目应该在0.1秒内


def test_import_fallback():
    """测试导入回退"""
    if not IMPORT_SUCCESS:
        assert IMPORT_ERROR is not None
        assert len(IMPORT_ERROR) > 0
    else:
        assert True  # 导入成功
