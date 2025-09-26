"""
Enhanced test file for dict_utils.py utility module
Provides comprehensive coverage for dictionary processing utilities
"""

import pytest
from typing import Any, Dict, List, Union
from unittest.mock import patch, Mock

# Import directly to avoid NumPy reload issues
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from utils.dict_utils import DictUtils


class TestDictUtilsDeepMerge:
    """Test deep_merge method"""

    def test_deep_merge_basic_override(self):
        """Test basic override behavior"""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested_simple(self):
        """Test simple nested merge"""
        dict1 = {"a": {"x": 1, "y": 2}, "b": 3}
        dict2 = {"a": {"y": 3, "z": 4}, "c": 5}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"a": {"x": 1, "y": 3, "z": 4}, "b": 3, "c": 5}
        assert result == expected

    def test_deep_merge_deeply_nested(self):
        """Test deeply nested merge"""
        dict1 = {"level1": {"level2": {"level3": {"a": 1, "b": 2}}}}
        dict2 = {"level1": {"level2": {"level3": {"b": 3, "c": 4}, "level4": {"d": 5}}}}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {
            "level1": {
                "level2": {
                    "level3": {"a": 1, "b": 3, "c": 4},
                    "level4": {"d": 5}
                }
            }
        }
        assert result == expected

    def test_deep_merge_dict_with_non_dict(self):
        """Test merging dict with non-dict (should override)"""
        dict1 = {"a": {"x": 1, "y": 2}, "b": 3}
        dict2 = {"a": "string_value", "c": 4}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": "string_value", "b": 3, "c": 4}

    def test_deep_merge_non_dict_with_dict(self):
        """Test merging non-dict with dict (should override)"""
        dict1 = {"a": "string_value", "b": 3}
        dict2 = {"a": {"x": 1, "y": 2}, "c": 4}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": {"x": 1, "y": 2}, "b": 3, "c": 4}

    def test_deep_merge_empty_dicts(self):
        """Test merging empty dictionaries"""
        assert DictUtils.deep_merge({}, {}) == {}
        assert DictUtils.deep_merge({"a": 1}, {}) == {"a": 1}
        assert DictUtils.deep_merge({}, {"a": 1}) == {"a": 1}

    def test_deep_merge_list_values(self):
        """Test merging dictionaries with list values (should override)"""
        dict1 = {"a": [1, 2, 3], "b": {"x": 1}}
        dict2 = {"a": [4, 5, 6], "b": {"y": 2}}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": [4, 5, 6], "b": {"x": 1, "y": 2}}

    def test_deep_merge_complex_data_types(self):
        """Test merging with complex data types"""
        dict1 = {
            "string": "value1",
            "number": 42,
            "boolean": True,
            "list": [1, 2, 3],
            "nested": {"inner": "value1"}
        }
        dict2 = {
            "string": "value2",
            "number": 3.14,
            "boolean": False,
            "list": [4, 5, 6],
            "nested": {"inner": "value2", "extra": "value3"}
        }
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {
            "string": "value2",
            "number": 3.14,
            "boolean": False,
            "list": [4, 5, 6],
            "nested": {"inner": "value2", "extra": "value3"}
        }
        assert result == expected

    def test_deep_merge_preserve_original(self):
        """Test that original dictionaries are not modified"""
        dict1 = {"a": 1, "b": {"x": 1}}
        dict2 = {"b": {"y": 2}, "c": 3}

        original_dict1 = dict1.copy()
        original_dict2 = dict2.copy()

        result = DictUtils.deep_merge(dict1, dict2)

        # Original dicts should be unchanged
        assert dict1 == original_dict1
        assert dict2 == original_dict2

        # Result should be merged
        assert result == {"a": 1, "b": {"x": 1, "y": 2}, "c": 3}

    def test_deep_merge_none_values(self):
        """Test merging with None values"""
        dict1 = {"a": None, "b": {"x": 1}}
        dict2 = {"a": {"y": 2}, "b": None}
        result = DictUtils.deep_merge(dict1, dict2)
        assert result == {"a": {"y": 2}, "b": None}

    def test_deep_merge_unicode_keys(self):
        """Test merging with Unicode keys"""
        dict1 = {"中文": "value1", "emoji": "🎉"}
        dict2 = {"中文": "value2", "special": "©®™"}
        result = DictUtils.deep_merge(dict1, dict2)
        expected = {"中文": "value2", "emoji": "🎉", "special": "©®™"}
        assert result == expected


class TestDictUtilsFlattenDict:
    """Test flatten_dict method"""

    def test_flatten_dict_basic(self):
        """Test basic flattening"""
        d = {"a": 1, "b": 2, "c": 3}
        result = DictUtils.flatten_dict(d)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_flatten_dict_nested(self):
        """Test nested flattening"""
        d = {"a": {"x": 1, "y": 2}, "b": 3}
        result = DictUtils.flatten_dict(d)
        assert result == {"a.x": 1, "a.y": 2, "b": 3}

    def test_flatten_dict_deeply_nested(self):
        """Test deeply nested flattening"""
        d = {"a": {"b": {"c": {"d": 1, "e": 2}}, "f": 3}, "g": 4}
        result = DictUtils.flatten_dict(d)
        expected = {"a.b.c.d": 1, "a.b.c.e": 2, "a.f": 3, "g": 4}
        assert result == expected

    def test_flatten_dict_custom_separator(self):
        """Test custom separator"""
        d = {"a": {"x": 1}, "b": 2}
        result = DictUtils.flatten_dict(d, sep="_")
        assert result == {"a_x": 1, "b": 2}

    def test_flatten_dict_empty_separator(self):
        """Test empty separator"""
        d = {"a": {"x": 1}, "b": 2}
        result = DictUtils.flatten_dict(d, sep="")
        assert result == {"ax": 1, "b": 2}

    def test_flatten_dict_with_parent_key(self):
        """Test with parent key"""
        d = {"x": 1, "y": {"z": 2}}
        result = DictUtils.flatten_dict(d, parent_key="parent")
        assert result == {"parent.x": 1, "parent.y.z": 2}

    def test_flatten_dict_empty_dict(self):
        """Test empty dictionary"""
        assert DictUtils.flatten_dict({}) == {}

    def test_flatten_dict_mixed_types(self):
        """Test mixed value types"""
        d = {
            "string": "value",
            "number": 42,
            "boolean": True,
            "none": None,
            "list": [1, 2, 3],
            "nested": {"inner": "value"}
        }
        result = DictUtils.flatten_dict(d)
        expected = {
            "string": "value",
            "number": 42,
            "boolean": True,
            "none": None,
            "list": [1, 2, 3],
            "nested.inner": "value"
        }
        assert result == expected

    def test_flatten_dict_list_in_nested(self):
        """Test list values in nested dict"""
        d = {"a": {"b": [1, 2, 3], "c": {"d": [4, 5]}}}
        result = DictUtils.flatten_dict(d)
        expected = {"a.b": [1, 2, 3], "a.c.d": [4, 5]}
        assert result == expected

    def test_flatten_dict_unicode_keys(self):
        """Test Unicode keys in flattening"""
        d = {"中文": {"测试": "value"}, "emoji": {"🎉": "fun"}}
        result = DictUtils.flatten_dict(d)
        expected = {"中文.测试": "value", "emoji.🎉": "fun"}
        assert result == expected

    def test_flatten_dict_special_characters(self):
        """Test special characters in keys"""
        d = {"key.with.dots": {"nested": "value"}, "key with spaces": {"another": "value"}}
        result = DictUtils.flatten_dict(d)
        expected = {"key.with.dots.nested": "value", "key with spaces.another": "value"}
        assert result == expected

    def test_flatten_dict_numeric_keys(self):
        """Test numeric keys"""
        d = {"1": {"2": 3}, "a": {"4": 5}}
        result = DictUtils.flatten_dict(d)
        expected = {"1.2": 3, "a.4": 5}
        assert result == expected

    def test_flatten_dict_preserve_original(self):
        """Test that original dictionary is not modified"""
        d = {"a": {"b": 1}, "c": 2}
        original = d.copy()
        result = DictUtils.flatten_dict(d)
        assert d == original
        assert result != d


class TestDictUtilsFilterNoneValues:
    """Test filter_none_values method"""

    def test_filter_none_values_basic(self):
        """Test basic None filtering"""
        d = {"a": 1, "b": None, "c": 3, "d": None}
        result = DictUtils.filter_none_values(d)
        assert result == {"a": 1, "c": 3}

    def test_filter_none_values_no_none(self):
        """Test dictionary with no None values"""
        d = {"a": 1, "b": 2, "c": 3}
        result = DictUtils.filter_none_values(d)
        assert result == d

    def test_filter_none_values_all_none(self):
        """Test dictionary with all None values"""
        d = {"a": None, "b": None, "c": None}
        result = DictUtils.filter_none_values(d)
        assert result == {}

    def test_filter_none_values_mixed_falsy(self):
        """Test filtering with mixed falsy values"""
        d = {"a": 0, "b": None, "c": "", "d": False, "e": [], "f": None, "g": {}}
        result = DictUtils.filter_none_values(d)
        # Should only filter None, keep other falsy values
        expected = {"a": 0, "c": "", "d": False, "e": [], "g": {}}
        assert result == expected

    def test_filter_none_values_nested_none(self):
        """Test None values in nested structures"""
        d = {"a": 1, "b": {"inner": None, "other": 2}, "c": None}
        result = DictUtils.filter_none_values(d)
        # Should only filter top-level None values
        expected = {"a": 1, "b": {"inner": None, "other": 2}}
        assert result == expected

    def test_filter_none_values_empty_dict(self):
        """Test empty dictionary"""
        assert DictUtils.filter_none_values({}) == {}

    def test_filter_none_values_complex_types(self):
        """Test with complex data types"""
        d = {
            "string": "value",
            "number": 0,
            "boolean": False,
            "none": None,
            "list": [],
            "dict": {},
            "set": set(),
            "tuple": ()
        }
        result = DictUtils.filter_none_values(d)
        expected = {
            "string": "value",
            "number": 0,
            "boolean": False,
            "list": [],
            "dict": {},
            "set": set(),
            "tuple": ()
        }
        assert result == expected

    def test_filter_none_values_preserve_original(self):
        """Test that original dictionary is not modified"""
        d = {"a": 1, "b": None, "c": 3}
        original = d.copy()
        result = DictUtils.filter_none_values(d)
        assert d == original
        assert result != d

    def test_filter_none_values_unicode_strings(self):
        """Test Unicode strings with None"""
        d = {"中文": "value", "emoji": "🎉", "none": None}
        result = DictUtils.filter_none_values(d)
        expected = {"中文": "value", "emoji": "🎉"}
        assert result == expected


class TestDictUtilsIntegration:
    """Integration tests combining multiple methods"""

    def test_deep_merge_then_flatten(self):
        """Test deep merge followed by flatten"""
        dict1 = {"a": {"x": 1}, "b": 2}
        dict2 = {"a": {"y": 2}, "c": 3}

        merged = DictUtils.deep_merge(dict1, dict2)
        flattened = DictUtils.flatten_dict(merged)

        expected = {"a.x": 1, "a.y": 2, "b": 2, "c": 3}
        assert flattened == expected

    def test_deep_merge_then_filter_none(self):
        """Test deep merge followed by filter None"""
        dict1 = {"a": {"x": 1}, "b": None}
        dict2 = {"a": {"y": None}, "c": 3}

        merged = DictUtils.deep_merge(dict1, dict2)
        filtered = DictUtils.filter_none_values(merged)

        expected = {"a": {"x": 1, "y": None}, "c": 3}
        assert filtered == expected

    def test_flatten_then_filter_none(self):
        """Test flatten followed by filter None"""
        d = {"a": {"x": 1}, "b": None, "c": {"y": None}}

        flattened = DictUtils.flatten_dict(d)
        filtered = DictUtils.filter_none_values(flattened)

        expected = {"a.x": 1, "c.y": None}
        assert filtered == expected

    def test_complex_workflow(self):
        """Test complex workflow with all methods"""
        # Start with multiple dictionaries
        config1 = {
            "database": {"host": "localhost", "port": 5432},
            "cache": {"redis": {"host": "localhost", "port": 6379}},
            "logging": {"level": "INFO"}
        }

        config2 = {
            "database": {"port": 3306, "name": "mydb"},
            "cache": {"redis": {"password": None}, "ttl": 3600},
            "monitoring": {"enabled": True}
        }

        # Merge configurations
        merged = DictUtils.deep_merge(config1, config2)

        # Filter out None values
        filtered = DictUtils.filter_none_values(merged)

        # Flatten for environment variable compatibility
        flattened = DictUtils.flatten_dict(filtered, sep="_")

        expected = {
            "database_host": "localhost",
            "database_port": 3306,
            "database_name": "mydb",
            "cache_redis_host": "localhost",
            "cache_redis_port": 6379,
            "cache_redis_ttl": 3600,
            "logging_level": "INFO",
            "monitoring_enabled": True
        }

        assert flattened == expected

    def test_performance_with_large_dicts(self):
        """Test performance with large dictionaries"""
        # Create large nested dictionary
        large_dict = {}
        for i in range(100):
            large_dict[f"key_{i}"] = {
                f"nested_{i}": {"deep": {"value": i}},
                f"list_{i}": list(range(10))
            }

        # Test operations complete without error
        merged = DictUtils.deep_merge(large_dict, {"additional_key": "value"})
        assert len(merged) == 101

        flattened = DictUtils.flatten_dict(merged)
        assert len(flattened) > len(merged)

        filtered = DictUtils.filter_none_values(merged)
        assert len(filtered) == len(merged)


class TestDictUtilsEdgeCases:
    """Test edge cases and error scenarios"""

    def test_deep_merge_with_self(self):
        """Test deep merging a dictionary with itself"""
        d = {"a": 1, "b": {"x": 2}}
        result = DictUtils.deep_merge(d, d)
        assert result == d

    def test_flatten_dict_with_same_keys(self):
        """Test flattening with same keys at different levels"""
        d = {"a": {"a": {"a": 1}}}
        result = DictUtils.flatten_dict(d)
        assert result == {"a.a.a": 1}

    def test_filter_none_with_custom_none_like(self):
        """Test that only actual None values are filtered"""
        d = {
            "none": None,
            "empty_string": "",
            "zero": 0,
            "false": False,
            "empty_list": [],
            "empty_dict": {},
            "nan": float('nan')
        }
        result = DictUtils.filter_none_values(d)
        # Should only filter the actual None
        assert len(result) == 6  # All except None
        assert "none" not in result

    def test_unicode_separator(self):
        """Test Unicode separator"""
        d = {"a": {"b": 1, "c": 2}}
        result = DictUtils.flatten_dict(d, sep="。")
        assert result == {"a。b": 1, "a。c": 2}

    def test_multicharacter_separator(self):
        """Test multi-character separator"""
        d = {"a": {"b": 1, "c": 2}}
        result = DictUtils.flatten_dict(d, sep="->")
        assert result == {"a->b": 1, "a->c": 2}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])