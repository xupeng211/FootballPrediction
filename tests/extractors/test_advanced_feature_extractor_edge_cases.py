#!/usr/bin/env python3
"""
高级特征提取器边界测试
Advanced Feature Extractor Edge Cases Tests

测试极端和异常的 JSON 数据情况：
1. 只有比分没有 xG 数据
2. 赔率为 0 或 NULL
3. 队名包含特殊字符
4. 缺失关键字段
5. 数据类型异常
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import json
from typing import Dict, Any, List

from src.data_access.processors.advanced_feature_extractor import (
    AdvancedFeatureExtractor,
    FeatureExtractionConfig,
    SmartRecursiveExtractor,
    XGDataAggregator,
    FeatureExtractionError,
)
from src.core.exceptions import ValidationError


class TestAdvancedFeatureExtractorEdgeCases:
    """高级特征提取器边界测试"""

    @pytest.fixture
    def extractor(self):
        """创建特征提取器实例"""
        config = FeatureExtractionConfig(
            strict_validation=False,  # 允许部分数据缺失
            fill_missing_values=True,  # 填充缺失值
            validate_ranges=True,  # 验证数据范围
        )
        return AdvancedFeatureExtractor(config)

    def test_extract_features_without_xg_data(self, extractor):
        """测试只有比分没有 xG 数据的情况"""
        # 只有比分，没有 xG 数据的 JSON
        match_data = {
            "content": {
                "stats": {
                    "Periods": {
                        "All": {
                            "stats": [
                                {"key": "Goals", "stats": [2, 1]},
                                {"key": "Shots", "stats": [15, 8]},
                                {"key": "BallPossesion", "stats": [60, 40]},
                            ]
                        }
                    }
                },
                "general": {"homeTeam": {"name": "Team A"}, "awayTeam": {"name": "Team B"}},
                "status": {"finished": True, "scoreStr": "2-1"},
            }
        }

        # 提取特征
        features = extractor.extract_features(match_data)

        # 验证 xG 相关字段被正确处理
        assert features["home_xg"] == 0.0 or features["home_xg"] is None
        assert features["away_xg"] == 0.0 or features["away_xg"] is None
        assert features["xg_total"] == 0.0 or features["xg_total"] is None
        assert features["xg_diff"] == 0.0 or features["xg_diff"] is None

        # 验证其他字段正常提取
        assert features["home_goals"] == 2
        assert features["away_goals"] == 1
        assert features["home_shots_total"] == 15
        assert features["away_shots_total"] == 8
        assert features["home_possession"] == 60.0
        assert features["away_possession"] == 40.0

    def test_extract_features_with_zero_or_null_odds(self, extractor):
        """测试赔率为 0 或 NULL 的情况"""
        match_data = {
            "content": {
                "stats": {
                    "Periods": {
                        "All": {
                            "stats": [
                                {"key": "expected_goals", "stats": [1.5, 0.8]},
                                {"key": "BallPossesion", "stats": [55, 45]},
                            ]
                        }
                    }
                },
                "betting": {
                    "odds": {"home_win": 0.0, "draw": None, "away_win": "invalid"}  # 零赔率  # NULL 赔率  # 无效赔率
                },
                "general": {"homeTeam": {"name": "Team A"}, "awayTeam": {"name": "Team B"}},
            }
        }

        features = extractor.extract_features(match_data)

        # 验证赔率字段被正确处理
        assert features["home_odds"] == 0.0 or features["home_odds"] is None
        assert features["draw_odds"] == 0.0 or features["draw_odds"] is None
        assert features["away_odds"] == 0.0 or features["away_odds"] is None

        # 验证赔率变化率字段
        assert "odds_movement" in features
        assert features["odds_movement"] is not None

    def test_extract_features_with_special_characters_in_team_names(self, extractor):
        """测试队名包含特殊字符的情况"""
        match_data = {
            "content": {
                "stats": {"Periods": {"All": {"stats": [{"key": "expected_goals", "stats": [1.2, 0.9]}]}}},
                "general": {
                    "homeTeam": {"name": "FC Barcelona 🏆"},
                    "awayTeam": {"name": "Real Madrid CF®"},
                    "matchTimeUTC": "2024-01-15T20:00:00Z",
                },
            }
        }

        features = extractor.extract_features(match_data)

        # 验证特殊字符被正确处理
        assert "FC Barcelona" in features["home_team_name"] or "Barcelona" in features["home_team_name"]
        assert "Real Madrid" in features["away_team_name"] or "Madrid" in features["away_team_name"]

        # 验证特征提取成功
        assert features["home_xg"] == 1.2
        assert features["away_xg"] == 0.9

    def test_extract_features_with_missing_critical_fields(self, extractor):
        """测试缺失关键字段的情况"""
        # 缺失 stats 数据
        match_data_missing_stats = {
            "content": {
                "general": {"homeTeam": {"name": "Team A"}, "awayTeam": {"name": "Team B"}},
                "status": {"finished": True},
                # 缺失 stats 字段
            }
        }

        features = extractor.extract_features(match_data_missing_stats)

        # 验证缺失字段被正确处理
        assert features["home_xg"] == 0.0 or features["home_xg"] is None
        assert features["away_xg"] == 0.0 or features["away_xg"] is None
        assert features["home_possession"] == 0.0 or features["home_possession"] is None
        assert features["away_possession"] == 0.0 or features["away_possession"] is None

    def test_extract_features_with_invalid_data_types(self, extractor):
        """测试数据类型异常的情况"""
        match_data_invalid_types = {
            "content": {
                "stats": {
                    "Periods": {
                        "All": {
                            "stats": [
                                {"key": "expected_goals", "stats": ["1.5", "invalid_number"]},  # 字符串而非数字
                                {"key": "BallPossesion", "stats": [None, 45.5]},  # NULL 值
                                {"key": "Shots", "stats": [{"value": 15}, 8]},  # 对象而非数字
                            ]
                        }
                    }
                },
                "general": {"homeTeam": {"name": "Team A"}, "awayTeam": {"name": "Team B"}},
            }
        }

        features = extractor.extract_features(match_data_invalid_types)

        # 验证无效数据类型被正确处理
        assert isinstance(features["home_xg"], (int, float)) or features["home_xg"] is None
        assert isinstance(features["away_xg"], (int, float)) or features["away_xg"] is None
        assert isinstance(features["home_possession"], (int, float)) or features["home_possession"] is None
        assert isinstance(features["away_possession"], (int, float)) or features["away_possession"] is None
        assert isinstance(features["home_shots_total"], (int, float)) or features["home_shots_total"] is None

    def test_extract_features_with_empty_or_null_response(self, extractor):
        """测试空响应或 NULL 响应的情况"""
        # 测试 None 响应
        features_none = extractor.extract_features(None)
        assert isinstance(features_none, dict)
        assert len(features_none) > 0  # 应该返回默认特征

        # 测试空字典
        features_empty = extractor.extract_features({})
        assert isinstance(features_empty, dict)
        assert len(features_empty) > 0

        # 测试空 content
        features_empty_content = extractor.extract_features({"content": {}})
        assert isinstance(features_empty_content, dict)
        assert len(features_empty_content) > 0

    def test_extract_features_with_malformed_json_structure(self, extractor):
        """测试格式错误的 JSON 结构"""
        # 嵌套层级错误
        match_data_nested_error = {
            "content": {
                "stats": {
                    # 错误：直接在 stats 下而不是 Periods.All.stats
                    "expected_goals": {"stats": [1.5, 0.8]},
                    "BallPossesion": {"stats": [60, 40]},
                }
            }
        }

        features = extractor.extract_features(match_data_nested_error)

        # 验证提取器能够处理错误结构
        assert isinstance(features, dict)
        assert len(features) > 0

    def test_extract_features_with_extreme_values(self, extractor):
        """测试极端数值的情况"""
        match_data_extreme = {
            "content": {
                "stats": {
                    "Periods": {
                        "All": {
                            "stats": [
                                {"key": "expected_goals", "stats": [999.99, -5.0]},  # 极端 xG 值
                                {"key": "BallPossesion", "stats": [150.0, -10.0]},  # 极端控球率
                                {"key": "Shots", "stats": [1000, -100]},  # 极端射门数
                            ]
                        }
                    }
                },
                "general": {"homeTeam": {"name": "Team A"}, "awayTeam": {"name": "Team B"}},
            }
        }

        features = extractor.extract_features(match_data_extreme)

        # 验证极端值被正确处理（可能是裁剪或填充）
        assert isinstance(features["home_xg"], (int, float))
        assert features["home_xg"] >= 0  # xG 不应该是负数
        assert features["away_xg"] >= 0
        assert 0 <= features["home_possession"] <= 100  # 控球率应该在 0-100 之间
        assert 0 <= features["away_possession"] <= 100
        assert features["home_shots_total"] >= 0  # 射门数不应该是负数
        assert features["away_shots_total"] >= 0

    def test_extract_features_with_unicode_and_encoding_issues(self, extractor):
        """测试 Unicode 和编码问题"""
        match_data_unicode = {
            "content": {
                "stats": {"Periods": {"All": {"stats": [{"key": "expected_goals", "stats": [1.5, 0.8]}]}}},
                "general": {
                    "homeTeam": {"name": "北京国安™"},  # 中文和商标符号
                    "awayTeam": {"name": "上海海港©"},  # 中文和版权符号
                    "venue": {"name": "工人体育场 🏟️"},  # 表情符号
                },
            }
        }

        features = extractor.extract_features(match_data_unicode)

        # 验证 Unicode 字符被正确处理
        assert isinstance(features["home_team_name"], str)
        assert isinstance(features["away_team_name"], str)
        assert len(features["home_team_name"]) > 0
        assert len(features["away_team_name"]) > 0

    def test_feature_extraction_performance_with_large_dataset(self, extractor):
        """测试大数据集的特征提取性能"""
        # 创建包含大量统计数据的匹配数据
        large_stats = []
        for i in range(100):  # 100 个统计项
            large_stats.append({"key": f"stat_{i}", "stats": [float(i), float(i + 1)]})

        match_data_large = {
            "content": {
                "stats": {"Periods": {"All": {"stats": large_stats}}},
                "general": {"homeTeam": {"name": "Team A"}, "awayTeam": {"name": "Team B"}},
            }
        }

        # 测试性能
        start_time = datetime.now()
        features = extractor.extract_features(match_data_large)
        end_time = datetime.now()

        # 验证性能（应该在合理时间内完成）
        processing_time = (end_time - start_time).total_seconds()
        assert processing_time < 5.0  # 应该在 5 秒内完成

        # 验证仍然返回了有效的特征
        assert isinstance(features, dict)
        assert len(features) > 0

    def test_extract_features_with_concurrent_access(self, extractor):
        """测试并发访问特征提取器"""
        import threading
        import time

        match_data = {
            "content": {
                "stats": {"Periods": {"All": {"stats": [{"key": "expected_goals", "stats": [1.5, 0.8]}]}}},
                "general": {"homeTeam": {"name": "Team A"}, "awayTeam": {"name": "Team B"}},
            }
        }

        results = []
        errors = []

        def extract_features_worker():
            try:
                for _ in range(10):
                    features = extractor.extract_features(match_data)
                    results.append(features)
                    time.sleep(0.001)  # 小延迟
            except Exception as e:
                errors.append(e)

        # 创建多个线程
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=extract_features_worker)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"并发访问产生错误: {errors}"
        assert len(results) == 50  # 5 线程 × 10 次调用
        assert all(isinstance(r, dict) for r in results)
