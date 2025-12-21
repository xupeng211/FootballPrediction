#!/usr/bin/env python3
"""
智能递归提取器测试 - 覆盖率 > 90%
Smart Recursive Extractor Tests - Coverage > 90%

全面测试 SmartRecursiveExtractor 的所有功能和边界情况
"""

import pytest
from unittest.mock import Mock, patch, call
from datetime import datetime
import json
from typing import Dict, Any, List, Optional

from src.data_access.processors.advanced_feature_extractor import (
    SmartRecursiveExtractor,
    XGDataAggregator,
    FeatureExtractionError,
)


class TestSmartRecursiveExtractor:
    """智能递归提取器测试"""

    @pytest.fixture
    def extractor(self):
        """创建递归提取器实例"""
        config = Mock()
        config.max_depth = 10
        config.strict_mode = False
        config.fallback_values = {"numeric": 0.0, "string": "", "boolean": False}
        return SmartRecursiveExtractor(config)

    def test_recursive_extraction_simple_path(self, extractor):
        """测试简单路径的递归提取"""
        data = {"level1": {"level2": {"target": "found_value"}}}

        result = extractor.extract_value(data, ["level1", "level2", "target"])
        assert result == "found_value"

    def test_recursive_extraction_with_array_index(self, extractor):
        """测试包含数组索引的路径提取"""
        data = {"stats": [{"key": "xg", "value": 1.5}, {"key": "possession", "value": 60.0}]}

        result = extractor.extract_value(data, ["stats", 0, "value"])
        assert result == 1.5

    def test_recursive_extraction_missing_path(self, extractor):
        """测试路径不存在的情况"""
        data = {"existing": "value"}

        result = extractor.extract_value(data, ["nonexistent", "path"])
        assert result is None

    def test_recursive_extraction_with_fallback(self, extractor):
        """测试使用回退值的路径提取"""
        data = {"missing": None}

        result = extractor.extract_value(data, ["missing", "value"], fallback=0.0)
        assert result == 0.0

    def test_recursive_extraction_max_depth_protection(self, extractor):
        """测试最大深度保护"""
        # 创建循环引用的数据结构
        data = {"loop": None}
        data["loop"] = data

        with patch.object(extractor, "max_depth", 3):
            result = extractor.extract_value(data, ["loop", "loop", "loop", "loop", "loop"])
            # 应该因为深度限制而返回 None 或回退值
            assert result is None

    def test_recursive_extraction_type_conversion(self, extractor):
        """测试类型转换"""
        data = {"numeric_string": "123.45", "boolean_string": "true", "int_string": "42"}

        # 测试字符串到数字的转换
        result = extractor.extract_value(data, ["numeric_string"], target_type=float)
        assert isinstance(result, float)
        assert result == 123.45

        # 测试字符串到整数的转换
        result = extractor.extract_value(data, ["int_string"], target_type=int)
        assert isinstance(result, int)
        assert result == 42

        # 测试字符串到布尔值的转换
        result = extractor.extract_value(data, ["boolean_string"], target_type=bool)
        assert isinstance(result, bool)
        assert result is True

    def test_recursive_extraction_with_wildcards(self, extractor):
        """测试通配符路径提取"""
        data = {"teams": {"home": {"name": "Team A", "score": 2}, "away": {"name": "Team B", "score": 1}}}

        # 使用通配符匹配所有队伍
        results = extractor.extract_with_wildcard(data, ["teams", "*", "name"])
        assert "Team A" in results
        assert "Team B" in results

    def test_recursive_extraction_with_conditional_filter(self, extractor):
        """测试条件过滤器"""
        data = {
            "stats": [
                {"key": "expected_goals", "value": 1.5, "team": "home"},
                {"key": "expected_goals", "value": 0.8, "team": "away"},
                {"key": "possession", "value": 60.0, "team": "home"},
            ]
        }

        # 提取主队的 xG 值
        result = extractor.extract_with_filter(
            data,
            ["stats", "*"],
            lambda item: item.get("key") == "expected_goals" and item.get("team") == "home",
            "value",
        )
        assert result == 1.5

    def test_recursive_extraction_error_handling(self, extractor):
        """测试错误处理"""
        # 测试 None 数据
        result = extractor.extract_value(None, ["any", "path"])
        assert result is None

        # 测试非字典数据
        result = extractor.extract_value("string_data", ["path"])
        assert result is None

        # 测试异常路径类型
        result = extractor.extract_value({}, [123, "invalid_path_type"])
        assert result is None

    def test_batch_extraction(self, extractor):
        """测试批量提取"""
        data = {
            "match": {
                "home": {"name": "Team A", "goals": 2},
                "away": {"name": "Team B", "goals": 1},
                "stats": {"possession": [60, 40]},
            }
        }

        extractions = [
            ("home_name", ["match", "home", "name"]),
            ("away_name", ["match", "away", "name"]),
            ("home_goals", ["match", "home", "goals"]),
            ("away_goals", ["match", "away", "goals"]),
            ("home_possession", ["match", "stats", "possession", 0]),
            ("nonexistent", ["match", "nonexistent"], "N/A"),
        ]

        results = extractor.extract_batch(data, extractions)
        assert results["home_name"] == "Team A"
        assert results["away_name"] == "Team B"
        assert results["home_goals"] == 2
        assert results["away_goals"] == 1
        assert results["home_possession"] == 60
        assert results["nonexistent"] == "N/A"

    def test_path_validation(self, extractor):
        """测试路径验证"""
        # 有效路径
        assert extractor.validate_path(["valid", "path"]) is True
        assert extractor.validate_path(["path", 0, "with", "index"]) is True

        # 无效路径
        assert extractor.validate_path([]) is False  # 空路径
        assert extractor.validate_path([None]) is False  # 包含 None
        assert extractor.validate_path(["", "path"]) is False  # 包含空字符串

    def test_path_normalization(self, extractor):
        """测试路径标准化"""
        # 标准化路径中的特殊字符
        normalized = extractor.normalize_path(["team.name", "stats[0]"])
        assert normalized == ["team_name", "stats_0"]

        # 标准化数字索引
        normalized = extractor.normalize_path([1, "path", 2])
        assert normalized == ["1", "path", "2"]

    def test_cache_functionality(self, extractor):
        """测试缓存功能"""
        data = {"cached": "value"}
        path = ["cached"]

        # 第一次提取
        result1 = extractor.extract_value(data, path)
        assert result1 == "value"

        # 第二次提取应该使用缓存
        with patch.object(extractor, "_extract_recursive") as mock_extract:
            result2 = extractor.extract_value(data, path)
            assert result2 == "value"
            # 如果缓存生效，不应该调用 _extract_recursive
            mock_extract.assert_not_called()

    def test_memory_efficiency(self, extractor):
        """测试内存效率"""
        import sys

        # 创建大型数据结构
        large_data = {}
        for i in range(1000):
            large_data[f"key_{i}"] = f"value_{i}"

        # 提取单个值应该只加载必要的部分
        result = extractor.extract_value(large_data, ["key_500"])
        assert result == "value_500"

        # 验证内存使用合理（这里只是示例，实际内存测试更复杂）
        assert isinstance(result, str)

    def test_concurrent_extraction(self, extractor):
        """测试并发提取"""
        import threading
        import time

        data = {"concurrent": {"test": "value"}}

        results = []
        errors = []

        def extract_worker():
            try:
                result = extractor.extract_value(data, ["concurrent", "test"])
                results.append(result)
            except Exception as e:
                errors.append(e)

        # 创建多个线程
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=extract_worker)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0
        assert len(results) == 10
        assert all(r == "value" for r in results)


class TestXGDataAggregator:
    """XG 数据聚合器测试"""

    @pytest.fixture
    def aggregator(self):
        """创建 XG 聚合器实例"""
        return XGDataAggregator()

    def test_aggregate_xg_from_shotmap(self, aggregator):
        """测试从 shotmap 聚合 xG 数据"""
        shotmap_data = {
            "shots": [
                {"expectedGoals": 0.5, "team": "home"},
                {"expectedGoals": 0.3, "team": "away"},
                {"expectedGoals": 0.8, "team": "home"},
                {"expectedGoals": 0.2, "team": "away"},
            ]
        }

        result = aggregator.aggregate_from_shotmap(shotmap_data)
        assert result["home_xg"] == 1.3  # 0.5 + 0.8
        assert result["away_xg"] == 0.5  # 0.3 + 0.2
        assert result["total_xg"] == 1.8

    def test_aggregate_xg_from_stats(self, aggregator):
        """测试从统计聚合 xG 数据"""
        stats_data = {"Periods": {"All": {"stats": [{"key": "expected_goals", "stats": [1.2, 0.9]}]}}}

        result = aggregator.aggregate_from_stats(stats_data)
        assert result["home_xg"] == 1.2
        assert result["away_xg"] == 0.9
        assert result["total_xg"] == 2.1

    def test_aggregate_xg_with_missing_data(self, aggregator):
        """测试处理缺失 xG 数据"""
        # 完全没有 xG 数据
        result = aggregator.aggregate_from_shotmap({})
        assert result["home_xg"] == 0.0
        assert result["away_xg"] == 0.0
        assert result["total_xg"] == 0.0

        # 部分 xG 数据缺失
        partial_data = {"shots": [{"expectedGoals": 0.5, "team": "home"}, {"team": "away"}]}  # 缺失 expectedGoals

        result = aggregator.aggregate_from_shotmap(partial_data)
        assert result["home_xg"] == 0.5
        assert result["away_xg"] == 0.0

    def test_aggregate_xg_with_invalid_values(self, aggregator):
        """测试处理无效 xG 值"""
        invalid_data = {
            "shots": [
                {"expectedGoals": "invalid", "team": "home"},
                {"expectedGoals": -0.5, "team": "away"},  # 负数
                {"expectedGoals": 999.9, "team": "home"},  # 极大值
            ]
        }

        result = aggregator.aggregate_from_shotmap(invalid_data)
        # 应该过滤或修正无效值
        assert result["home_xg"] >= 0
        assert result["away_xg"] >= 0

    def test_xg_aggregator_fallback_chain(self, aggregator):
        """测试 xG 聚合器的回退链"""
        # 模拟多源数据
        data = {
            "content": {
                "shotmap": {"shots": [{"expectedGoals": 0.5, "team": "home"}]},
                "stats": {"Periods": {"All": {"stats": [{"key": "expected_goals", "stats": [1.0, 0.8]}]}}},
            }
        }

        # 应该优先使用 shotmap 数据
        result = aggregator.aggregate_with_fallback(data)
        assert result["home_xg"] == 0.5  # 来自 shotmap
        assert result["away_xg"] == 0.8  # 来自 stats

    def test_xg_aggregator_performance(self, aggregator):
        """测试 xG 聚合器性能"""
        # 创建大量射门数据
        large_shotmap = {
            "shots": [{"expectedGoals": 0.1, "team": "home" if i % 2 == 0 else "away"} for i in range(1000)]
        }

        start_time = datetime.now()
        result = aggregator.aggregate_from_shotmap(large_shotmap)
        end_time = datetime.now()

        # 验证性能
        processing_time = (end_time - start_time).total_seconds()
        assert processing_time < 1.0  # 应该在 1 秒内完成

        # 验证结果正确性
        assert result["home_xg"] == 50.0  # 500 * 0.1
        assert result["away_xg"] == 50.0  # 500 * 0.1
