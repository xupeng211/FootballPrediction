from unittest.mock import Mock, patch
"""
测试 PredictionCacheManager 的覆盖率补充
Test coverage supplement for PredictionCacheManager
"""

import pytest

from src.core.prediction.cache_manager import PredictionCacheManager


@pytest.mark.unit
@pytest.mark.cache

class TestPredictionCacheManager:
    """PredictionCacheManager 测试类"""

    def test_init(self):
        """测试缓存管理器初始化"""
        manager = PredictionCacheManager()

        assert hasattr(manager, "_cache")
        assert hasattr(manager, "logger")
        assert manager._cache == {}
        assert manager.logger is not None

    @patch("src.core.prediction.cache_manager.logging.getLogger")
    def test_init_logger_creation(self, mock_get_logger):
        """测试初始化时logger的创建"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        manager = PredictionCacheManager()

        # 验证logger被正确创建
        mock_get_logger.assert_called_once()
        assert manager.logger == mock_logger

    def test_get_existing_key(self):
        """测试获取存在的缓存项"""
        manager = PredictionCacheManager()
        test_data = {"prediction": "win", "confidence": 0.85}
        manager._cache["test_key"] = test_data

        result = manager.get("test_key")

        assert result == test_data

    def test_get_nonexistent_key(self):
        """测试获取不存在的缓存项"""
        manager = PredictionCacheManager()

        result = manager.get("nonexistent_key")

        assert result is None

    def test_get_empty_cache(self):
        """测试在空缓存中获取数据"""
        manager = PredictionCacheManager()

        result = manager.get("any_key")

        assert result is None

    def test_set_without_ttl(self):
        """测试设置缓存项（无TTL）"""
        manager = PredictionCacheManager()
        test_data = {"prediction": "draw", "confidence": 0.60}

        manager.set("test_key", test_data)

        assert manager._cache["test_key"] == test_data

    def test_set_with_ttl(self):
        """测试设置缓存项（有TTL）"""
        manager = PredictionCacheManager()
        test_data = {"prediction": "loss", "confidence": 0.25}

        # 当前实现忽略TTL参数，但应该接受它
        manager.set("test_key", test_data, ttl=3600)

        assert manager._cache["test_key"] == test_data

    def test_set_overwrite_existing(self):
        """测试覆盖已存在的缓存项"""
        manager = PredictionCacheManager()
        original_data = {"prediction": "win", "confidence": 0.80}
        new_data = {"prediction": "loss", "confidence": 0.90}

        manager.set("test_key", original_data)
        manager.set("test_key", new_data)

        assert manager._cache["test_key"] == new_data

    def test_delete_existing_key(self):
        """测试删除存在的缓存项"""
        manager = PredictionCacheManager()
        test_data = {"prediction": "win", "confidence": 0.75}
        manager._cache["test_key"] = test_data

        result = manager.delete("test_key")

        assert result is True
        assert "test_key" not in manager._cache

    def test_delete_nonexistent_key(self):
        """测试删除不存在的缓存项"""
        manager = PredictionCacheManager()

        result = manager.delete("nonexistent_key")

        assert result is False

    def test_clear_empty_cache(self):
        """测试清空空缓存"""
        manager = PredictionCacheManager()

        manager.clear()

        assert manager._cache == {}

    def test_clear_populated_cache(self):
        """测试清空有数据的缓存"""
        manager = PredictionCacheManager()
        manager._cache["key1"] = {"data": "value1"}
        manager._cache["key2"] = {"data": "value2"}
        manager._cache["key3"] = {"data": "value3"}

        manager.clear()

        assert manager._cache == {}

    def test_multiple_operations_sequence(self):
        """测试多个操作的序列"""
        manager = PredictionCacheManager()

        # 设置多个缓存项
        manager.set("key1", {"value": 1})
        manager.set("key2", {"value": 2})
        manager.set("key3", {"value": 3})

        # 验证获取
        assert manager.get("key1") == {"value": 1}
        assert manager.get("key2") == {"value": 2}
        assert manager.get("key3") == {"value": 3}

        # 删除一个
        assert manager.delete("key2") is True
        assert manager.get("key2") is None

        # 清空所有
        manager.clear()
        assert manager.get("key1") is None
        assert manager.get("key3") is None

    def test_cache_data_types(self):
        """测试不同数据类型的缓存值"""
        manager = PredictionCacheManager()

        # 测试字典类型
        dict_data = {"prediction": "win", "details": {"score": "2-1"}}
        manager.set("dict_key", dict_data)
        assert manager.get("dict_key") == dict_data

        # 测试列表类型
        list_data = ["prediction1", "prediction2"]
        manager.set("list_key", list_data)
        assert manager.get("list_key") == list_data

        # 测试字符串类型
        string_data = "simple prediction"
        manager.set("string_key", string_data)
        assert manager.get("string_key") == string_data

    def test_edge_case_empty_string_key(self):
        """测试空字符串键的边界情况"""
        manager = PredictionCacheManager()
        test_data = {"test": "data"}

        manager.set("", test_data)
        assert manager.get("") == test_data
        assert manager.delete("") is True

    def test_edge_case_special_characters_key(self):
        """测试特殊字符键的边界情况"""
        manager = PredictionCacheManager()
        test_data = {"test": "data"}
        special_key = "key-with_special.chars_123"

        manager.set(special_key, test_data)
        assert manager.get(special_key) == test_data
        assert manager.delete(special_key) is True
