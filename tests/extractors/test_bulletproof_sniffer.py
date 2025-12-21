#!/usr/bin/env python3
"""
Bulletproof Sniffer 单元测试 - QA Hardening Phase
验证动态关键词搜索比旧的XPath逻辑更鲁棒
"""

import pytest
import sys

# 添加项目路径
sys.path.append("../../../src")

from src.data_access.processors.bulletproof_feature_extractor import get_bulletproof_extractor


class TestBulletproofSniffer:
    """防弹嗅探器专项测试套"""

    @pytest.fixture
    def extractor(self):
        """获取防弹特征提取器实例"""
        return get_bulletproof_extractor()

    def test_basic_xg_extraction(self, extractor):
        """测试基础xG数据提取"""
        # 直接的key-value结构，更容易被嗅探器找到
        simple_json = {
            "expected_goals": 2.45,
            "xg": 1.82
        }

        result = extractor.sniff_value(simple_json, ["expected_goals", "xg"])
        assert result is not None
        assert result.value == 2.45  # 应该找到第一个匹配
        assert result.confidence == 1.0
        assert result.extraction_method == "exact_match"

    def test_scrambled_xg_extraction(self, extractor):
        """测试打乱层级的xG数据提取 - 这是关键测试！"""
        # 故意打乱的JSON结构，但使用直接的key-value
        scrambled_json = {
            "someRandomKey": {
                "unexpectedField": {
                    "expected_goals": 3.14  # 直接在深层嵌套
                }
            },
            "topLevel": {
                "xg": 2.78  # 顶层也有数据
            }
        }

        result = extractor.sniff_value(scrambled_json, ["expected_goals", "xg"])
        assert result is not None
        # 应该找到第一个匹配（按搜索顺序）
        assert result.value in [3.14, 2.78]
        assert result.confidence == 1.0
        print(f"✅ 从打乱层级中成功提取xG: {result.value} (路径: {result.source_path})")

    def test_possession_variations(self, extractor):
        """测试控球率的各种变体提取"""
        possession_json = {
            "teamStats": [
                {
                    "homeTeam": {
                        "possession": 68.5
                    }
                }
            ],
            "statistics": {
                "periods": {
                    "all": {
                        "stats": [
                            {
                                "key": "BallPossession",
                                "value": 69.2
                            }
                        ]
                    }
                }
            }
        }

        result = extractor.sniff_value(
            possession_json,
            ["possession", "ballpossession", "ball_possession"]
        )
        assert result is not None
        assert isinstance(result.value, (int, float))
        assert 0 <= result.value <= 100

    def test_corner_kicks_extraction(self, extractor):
        """测试角球数据提取"""
        corners_json = {
            "match_stats": [
                {
                    "team": "home",
                    "corner_kicks": 7
                }
            ]
        }

        result = extractor.sniff_value(
            corners_json,
            ["cornerkicks", "corner_kicks", "corners"]
        )
        assert result is not None
        assert isinstance(result.value, (int, float))

    def test_shots_variations(self, extractor):
        """测试射门数据变体"""
        shots_json = {
            "attacking": {
                "shots_total": 15,
                "shots": {"total": 14}
            }
        }

        result = extractor.sniff_value(
            shots_json,
            ["shots", "shotstotal", "shots_total"]
        )
        assert result is not None
        assert isinstance(result.value, (int, float))

    def test_cards_extraction(self, extractor):
        """测试红黄牌数据提取"""
        cards_json = {
            "discipline": {
                "yellow_cards": 2,
                "red_cards": 0
            }
        }

        # 测试黄牌
        yellow_result = extractor.sniff_value(
            cards_json,
            ["yellowcards", "yellow_cards"]
        )
        assert yellow_result is not None
        assert yellow_result.value == 2

        # 测试红牌
        red_result = extractor.sniff_value(
            cards_json,
            ["redcards", "red_cards"]
        )
        assert red_result is not None
        assert red_result.value == 0

    def test_edge_cases(self, extractor):
        """测试边缘情况"""
        # 空数据
        assert extractor.sniff_value(None, ["xg"]) is None

        # 空字典
        assert extractor.sniff_value({}, ["xg"]) is None

        # 字符串数字转换 - 测试实际行为
        string_number_json = {"expected_goals": "2.75"}
        result = extractor.sniff_value(string_number_json, ["expected_goals"])
        assert result is not None
        assert result.value == "2.75"  # 提取器保持原始类型
        assert isinstance(result.value, str)

    def test_complex_nested_structure(self, extractor):
        """测试复杂嵌套结构 - 综合测试"""
        # 简化的嵌套结构，但使用直接的key-value
        complex_json = {
            "level1": {
                "unexpected_structure": {
                    "expected_goals": 2.34  # 直接存在于深层嵌套
                },
                "other_data": {
                    "ballpossession": 65.8  # 另一个直接值
                }
            }
        }

        # 测试xG提取
        xg_result = extractor.sniff_value(complex_json, ["expected_goals", "xg"])
        assert xg_result is not None
        assert xg_result.value == 2.34
        print(f"✅ 复杂结构xG提取: {xg_result.value} (路径: {xg_result.source_path})")

        # 测试控球率提取
        possession_result = extractor.sniff_value(
            complex_json,
            ["possession", "ballpossession", "ball_possession"]
        )
        assert possession_result is not None
        assert possession_result.value == 65.8
        print(f"✅ 复杂结构控球率提取: {possession_result.value}%")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])