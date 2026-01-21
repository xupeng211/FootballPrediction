#!/usr/bin/env python3
"""
V41.500 End-to-End Test - 自动化流水线端到端测试
===============================================

测试内容：
1. Schema Map 加载测试
2. Path Resolver 安全路径访问测试
3. Feature Factory 特征生成测试
4. Pipeline Integrator 流水线集成测试
5. 对账看板验证

Author: V41.500 QA Team
Version: V41.500 "The Automated Pipeline"
Date: 2026-01-21
"""

from __future__ import annotations

import json
import logging
import pytest
from datetime import datetime

# 测试导入
from src.config_unified import get_settings
from src.processors.path_resolver import (
    PathResolver,
    SchemaMapConfig,
    get_path_resolver,
    get_schema_config,
)
from src.processors.feature_factory import (
    FeatureFactory,
    get_feature_factory,
)


# =============================================================================
# Test: Schema Map Configuration
# =============================================================================

class TestSchemaMapConfig:
    """Schema Map 配置测试"""

    def test_load_config(self):
        """测试配置文件加载"""
        config = SchemaMapConfig()
        loaded_config = config.load_config()

        assert isinstance(loaded_config, dict)
        assert "fotmob" in loaded_config or loaded_config == {}  # 允许文件不存在

    def test_get_param(self):
        """测试参数获取"""
        config = SchemaMapConfig()

        # 获取疲劳度参数
        busy_threshold = config.get_param("fatigue", "busy_week_threshold", 4)
        assert isinstance(busy_threshold, int)
        assert busy_threshold == 4

        # 获取缺阵参数
        star_mv = config.get_param("unavailability", "star_market_value", 30_000_000)
        assert isinstance(star_mv, int)

    def test_get_default(self):
        """测试默认值获取"""
        config = SchemaMapConfig()

        mv_default = config.get_default("market_value", 0)
        assert mv_default == 0


# =============================================================================
# Test: Path Resolver
# =============================================================================

class TestPathResolver:
    """路径解析器测试"""

    def test_resolve_path_simple(self):
        """测试简单路径解析"""
        resolver = PathResolver()

        data = {
            "content": {
                "lineup": {
                    "homeTeam": {
                        "rating": 6.8
                    }
                }
            }
        }

        result = resolver.resolve_path(data, "content.lineup.homeTeam.rating")
        assert result == 6.8

    def test_resolve_path_with_default(self):
        """测试带默认值的路径解析"""
        resolver = PathResolver()

        data = {
            "content": {
                "lineup": {}
            }
        }

        result = resolver.resolve_path(data, "content.lineup.homeTeam.rating", default=6.0)
        assert result == 6.0

    def test_resolve_path_with_array(self):
        """测试数组路径解析"""
        resolver = PathResolver()

        data = {
            "content": {
                "lineup": {
                    "homeTeam": {
                        "unavailable": [
                            {"id": 1, "name": "Player A"},
                            {"id": 2, "name": "Player B"},
                        ]
                    }
                }
            }
        }

        result = resolver.resolve_path(data, "content.lineup.homeTeam.unavailable[0].name")
        assert result == "Player A"

    def test_resolve_path_json_string(self):
        """测试 JSON 字符串解析"""
        resolver = PathResolver()

        json_str = '{"content": {"lineup": {"homeTeam": {"rating": 7.2}}}}'
        result = resolver.resolve_path(json_str, "content.lineup.homeTeam.rating")
        assert result == 7.2

    def test_get_unavailable_players(self):
        """测试获取缺阵球员"""
        resolver = PathResolver()

        data = {
            "content": {
                "lineup": {
                    "homeTeam": {
                        "unavailable": [
                            {"id": 1, "name": "Injured Player", "unavailability": {"type": "injury"}}
                        ]
                    }
                }
            }
        }

        result = resolver.get_unavailable_players(data, "home")
        assert len(result) == 1
        assert result[0]["name"] == "Injured Player"

    def test_get_player_market_value(self):
        """测试获取球员身价"""
        resolver = PathResolver()

        player = {"marketValue": 50_000_000}
        mv = resolver.get_player_market_value(player)
        assert mv == 50_000_000

        # 测试容错
        player_no_mv = {"name": "Player"}
        mv = resolver.get_player_market_value(player_no_mv)
        assert mv == 0.0

    def test_get_unavailability_type(self):
        """测试缺阵类型识别"""
        resolver = PathResolver()

        injury_player = {"unavailability": {"type": "injury"}}
        assert resolver.get_unavailability_type(injury_player) == "injury"

        suspension_player = {"unavailability": {"type": "suspension"}}
        assert resolver.get_unavailability_type(suspension_player) == "suspension"

        unknown_player = {"unavailability": {"type": "unknown"}}
        assert resolver.get_unavailability_type(unknown_player) == "unknown"


# =============================================================================
# Test: Feature Factory
# =============================================================================

class TestFeatureFactory:
    """特征工厂测试"""

    def test_extract_fatigue_features(self):
        """测试疲劳度特征提取"""
        factory = FeatureFactory()

        # Mock match data
        match_data = {
            "match_id": "test_001",
            "home_team": "Team A",
            "away_team": "Team B",
            "match_date": datetime(2025, 1, 15, 15, 0),
            "league_name": "Premier League",
        }

        features = factory._extract_fatigue_features(match_data)

        # 应该包含疲劳度特征
        assert "home_rest_days" in features
        assert "away_rest_days" in features
        assert "diff_rest_days" in features

        # 数据类型检查
        assert isinstance(features["home_rest_days"], (int, float))

    def test_extract_unavailability_features(self):
        """测试缺阵特征提取"""
        factory = FeatureFactory()

        # Mock l2_raw_json
        l2_json = {
            "content": {
                "lineup": {
                    "homeTeam": {
                        "unavailable": [
                            {
                                "id": 1,
                                "name": "Injured Player",
                                "marketValue": 50_000_000,
                                "unavailability": {"type": "injury"}
                            }
                        ]
                    },
                    "awayTeam": {
                        "unavailable": []
                    }
                }
            }
        }

        features = factory._extract_unavailability_features(l2_json)

        # 应该包含缺阵特征
        assert "home_unavailable_total_count" in features
        assert "away_unavailable_total_count" in features
        assert features["home_unavailable_total_count"] == 1.0
        assert features["away_unavailable_total_count"] == 0.0

    def test_extract_league_features(self):
        """测试联赛等级特征提取"""
        factory = FeatureFactory()

        # 五大联赛
        match_data = {"league_name": "Premier League"}
        features = factory._extract_league_features(match_data)
        assert features["is_top_5_league"] == 1.0

        # 非五大联赛
        match_data = {"league_name": "Eredivisie"}
        features = factory._extract_league_features(match_data)
        assert features["is_top_5_league"] == 0.0

    def test_process_match_integration(self):
        """测试完整比赛处理流程"""
        factory = FeatureFactory()

        match_data = {
            "match_id": "test_001",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "match_date": datetime(2025, 1, 15, 15, 0),
            "league_name": "Premier League",
            "l2_raw_json": {
                "content": {
                    "lineup": {
                        "homeTeam": {
                            "unavailable": [],
                            "starters": [],
                            "rating": 6.8
                        },
                        "awayTeam": {
                            "unavailable": [],
                            "starters": [],
                            "rating": 7.2
                        }
                    }
                }
            }
        }

        features = factory.process_match(match_data)

        # 应该包含多类特征
        assert "is_top_5_league" in features
        assert "home_rest_days" in features
        assert len(features) > 0


# =============================================================================
# Test: Pipeline Integrator (Integration Test)
# =============================================================================

class TestPipelineIntegration:
    """流水线集成测试（需要数据库）"""

    @pytest.mark.skip(reason="需要数据库连接")
    def test_process_match_pipeline(self):
        """测试完整的流水线处理"""
        from src.api.collectors.v41_500_pipeline_integration import PipelineIntegrator

        integrator = PipelineIntegrator()

        # 使用一个真实的 match_id 进行测试
        # 这里需要数据库中有测试数据
        # result = integrator.process_match("test_match_id")
        # assert result is True

        integrator.cleanup()


# =============================================================================
# Test: V41.510 Robustness Tests - Edge Case & Null Value Tests
# =============================================================================

class TestV41_510Robustness:
    """V41.510 鲁棒性测试 - 暴力 Null 值测试"""

    def test_empty_json_handling(self):
        """测试全空 JSON 处理"""
        resolver = PathResolver()

        # 测试空字典
        result = resolver.resolve_path({}, "content.lineup.homeTeam.rating", default=6.0)
        assert result == 6.0

        # 测试空 JSON 字符串
        result = resolver.resolve_path("{}", "content.lineup.homeTeam.rating", default=6.0)
        assert result == 6.0

        # 测试 None
        result = resolver.resolve_path(None, "content.lineup.homeTeam.rating", default=6.0)
        assert result == 6.0

    def test_corrupted_json_handling(self):
        """测试损坏 JSON 处理"""
        resolver = PathResolver()

        # 测试无效 JSON 字符串
        result = resolver.resolve_path("{invalid json}", "content.rating", default=6.0)
        assert result == 6.0

        # 测试半截 JSON
        result = resolver.resolve_path('{"content": ', "content.rating", default=6.0)
        assert result == 6.0

    def test_null_values_in_data(self):
        """测试数据中的 Null 值处理"""
        resolver = PathResolver()

        data = {
            "content": {
                "lineup": {
                    "homeTeam": {
                        "rating": None,  # Null 值
                        "unavailable": None
                    }
                }
            }
        }

        # 应该返回默认值而非崩溃
        result = resolver.resolve_path(data, "content.lineup.homeTeam.rating", default=6.0)
        assert result == 6.0 or result is None

        # get_unavailable_players 应该返回空列表
        result = resolver.get_unavailable_players(data, "home")
        assert isinstance(result, list)
        assert len(result) == 0

    def test_missing_nested_fields(self):
        """测试缺失嵌套字段处理"""
        resolver = PathResolver()

        # 完全缺失的路径
        data = {"some_other_field": "value"}
        result = resolver.resolve_path(data, "content.lineup.homeTeam.rating", default=6.0)
        assert result == 6.0

        # 部分缺失路径
        data = {"content": {"some_field": "value"}}
        result = resolver.resolve_path(data, "content.lineup.homeTeam.rating", default=6.0)
        assert result == 6.0

    def test_empty_arrays_handling(self):
        """测试空数组处理"""
        resolver = PathResolver()

        data = {
            "content": {
                "lineup": {
                    "homeTeam": {
                        "unavailable": [],
                        "starters": []
                    }
                }
            }
        }

        # 应该正常处理空数组
        result = resolver.get_unavailable_players(data, "home")
        assert result == []

        # 访问空数组的元素应返回默认值
        result = resolver.resolve_path(data, "content.lineup.homeTeam.unavailable[0].name", default=None)
        assert result is None

    def test_factory_with_null_match_data(self):
        """测试 FeatureFactory 处理 Null 比赛数据"""
        factory = FeatureFactory()

        # 测试所有字段为 None
        match_data = {
            "match_id": None,
            "home_team": None,
            "away_team": None,
            "match_date": None,
            "league_name": None,
            "l2_raw_json": None
        }

        # 不应该抛出异常
        features = factory.process_match(match_data)

        # 应该返回空字典或只包含联赛特征
        assert isinstance(features, dict)

    def test_factory_with_corrupted_l2_json(self):
        """测试 FeatureFactory 处理损坏的 l2_raw_json"""
        factory = FeatureFactory()

        match_data = {
            "match_id": "test_001",
            "home_team": "Team A",
            "away_team": "Team B",
            "match_date": datetime(2025, 1, 15, 15, 0),
            "league_name": "Premier League",
            "l2_raw_json": "{corrupted json data"
        }

        # 不应该抛出异常
        features = factory.process_match(match_data)

        # 应该至少有联赛等级特征
        assert "is_top_5_league" in features

    def test_factory_with_empty_l2_json(self):
        """测试 FeatureFactory 处理空的 l2_raw_json"""
        factory = FeatureFactory()

        match_data = {
            "match_id": "test_001",
            "home_team": "Team A",
            "away_team": "Team B",
            "match_date": datetime(2025, 1, 15, 15, 0),
            "league_name": "Premier League",
            "l2_raw_json": {}
        }

        # 不应该抛出异常
        features = factory.process_match(match_data)

        # 应该至少有联赛等级特征
        assert "is_top_5_league" in features

    def test_type_safety_with_wrong_types(self):
        """测试类型安全 - 错误类型处理"""
        resolver = PathResolver()

        # 字符串代替数字
        player = {"marketValue": "50 million"}  # 字符串而非数字
        mv = resolver.get_player_market_value(player)
        # 应该返回默认值
        assert mv == 0.0

        # 列表代替字典
        result = resolver.resolve_path(["not", "a", "dict"], "content.rating", default=6.0)
        assert result == 6.0

    def test_deeply_nested_path_with_missing_intermediate(self):
        """测试深层嵌套路径中中间层缺失"""
        resolver = PathResolver()

        data = {
            "content": {
                "lineup": {}  # homeTeam 缺失
            }
        }

        result = resolver.resolve_path(
            data,
            "content.lineup.homeTeam.unavailable[0].name",
            default="Unknown"
        )
        assert result == "Unknown"

    def test_array_index_out_of_bounds(self):
        """测试数组索引越界处理"""
        resolver = PathResolver()

        data = {
            "content": {
                "lineup": {
                    "homeTeam": {
                        "unavailable": [{"name": "Player A"}]
                    }
                }
            }
        }

        # 索引 10 不存在
        result = resolver.resolve_path(
            data,
            "content.lineup.homeTeam.unavailable[10].name",
            default="Unknown"
        )
        assert result == "Unknown"

    def test_no_exception_on_all_edge_cases(self):
        """
        V41.510 综合测试：所有边界情况都不应该抛出异常
        """
        factory = FeatureFactory()
        resolver = PathResolver()

        edge_cases = [
            ("None", None),
            ("Empty dict", {}),
            ("Empty list", []),
            ("Invalid JSON", "{invalid"),
            ("Empty JSON", "{}"),
            ("Null values", {"a": None, "b": {"c": None}}),
            ("Empty string", ""),
            ("Wrong type", 12345),
        ]

        for case_name, case_value in edge_cases:
            try:
                # PathResolver 测试
                resolver.resolve_path(case_value, "any.path", default="default")
                resolver.get_unavailable_players(case_value, "home")

                # FeatureFactory 测试
                match_data = {
                    "match_id": "test",
                    "home_team": "A",
                    "away_team": "B",
                    "match_date": datetime(2025, 1, 15),
                    "league_name": "Premier League",
                    "l2_raw_json": case_value
                }
                factory.process_match(match_data)

            except Exception as e:
                pytest.fail(f"Edge case '{case_name}' raised exception: {e}")


# =============================================================================
# Test: 对账看板验证
# =============================================================================

class TestVerificationDashboard:
    """对账看板测试"""

    def test_schema_agnostic_check(self):
        """验证 Schema Agnostic 设计"""
        config = SchemaMapConfig()

        # 检查 fotmob 配置存在
        fotmob_config = config.fotmob
        assert isinstance(fotmob_config, dict)

        # 检查路径映射存在
        assert "l2_raw_json" in fotmob_config or fotmob_config == {}

    def test_feature_factory_active_check(self):
        """验证 FeatureFactory 可用"""
        factory = get_feature_factory()
        assert factory is not None
        assert isinstance(factory, FeatureFactory)

    def test_legacy_integration_check(self):
        """验证历史逻辑集成"""
        factory = FeatureFactory()

        # 检查是否集成了疲劳度计算
        assert hasattr(factory, "_extract_fatigue_features")

        # 检查是否集成了缺阵特征
        assert hasattr(factory, "_extract_unavailability_features")

        # 检查是否集成了首发战力
        assert hasattr(factory, "_extract_starting_11_features")

        # 检查是否集成了赔率特征
        assert hasattr(factory, "_extract_odds_features")

        # 检查是否集成了联赛等级
        assert hasattr(factory, "_extract_league_features")


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
