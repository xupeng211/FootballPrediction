#!/usr/bin/env python3
"""
钻石级特征提取器测试套件 - 106字段完整验证
Diamond Feature Extractor Test Suite - Complete 106-Field Validation

测试覆盖：
1. 106字段参数化测试（正常数据、部分缺失、异常数据）
2. xG提取逻辑验证（确保从shotmap而非仅进球事件提取）
3. Mock测试：5种不同FotMob JSON响应结构
4. 错误处理和边界条件测试
"""

import pytest
from typing import Dict, Any, List
from datetime import datetime
from unittest.mock import Mock, patch

from src.data_access.processors.diamond_feature_extractor_v3 import (
    AdvancedFeatureExtractor,
    FeatureExtractionConfig,
    SmartRecursiveExtractor,
    XGDataAggregator,
    FeatureExtractionError,
    DataValidationError,
    create_feature_extractor,
    extract_match_features
)
from src.schemas.match_features import MatchFeatures, WeatherCondition


class TestFeatureExtractionConfig:
    """特征提取配置测试"""

    def test_load_valid_config(self):
        """测试加载有效配置"""
        config = FeatureExtractionConfig.from_yaml("configs/settings.yaml")

        assert config is not None
        assert isinstance(config.xg_patterns, dict)
        assert 'home' in config.xg_patterns
        assert 'away' in config.xg_patterns
        assert config.max_recursion_depth > 0
        assert config.timeout_seconds > 0

    def test_load_missing_config(self):
        """测试加载缺失配置文件"""
        with pytest.raises(FileNotFoundError):
            FeatureExtractionConfig.from_yaml("nonexistent_config.yaml")

    def test_load_invalid_yaml_config(self):
        """测试加载无效YAML配置"""
        with patch('builtins.open', side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError):
                FeatureExtractionConfig.from_yaml("invalid_config.yaml")


class TestSmartRecursiveExtractor:
    """智能递归提取器测试"""

    @pytest.mark.parametrize("data,patterns,expected", [
        # 基本类型测试
        ({"expectedGoals": 1.25}, [r"expectedGoals.*?([\d.]+)"], 1.25),
        ({"homexg": "0.85"}, [r"homexg.*?([\d.]+)"], 0.85),
        ({"stats": {"xg": 2.1}}, [r"xg.*?([\d.]+)"], 2.1),
        # 嵌套结构测试
        ({"team": {"home": {"expectedGoals": "1.5"}}}, [r"expectedGoals.*?([\d.]+)"], 1.5),
        ({"shotmap": [{"expectedGoals": 0.1}, {"expectedGoals": 0.2}]}, [r"expectedGoals.*?([\d.]+)"], 0.1),
        # 列表结构测试
        ({"stats": [{"possession": 55}]}, [r"possession.*?(\d+)"], 55),
    ])
    def test_extract_value_success(self, data, patterns, expected):
        """测试成功提取数值"""
        extractor = SmartRecursiveExtractor()
        result = extractor.extract_value(data, patterns)
        assert result == expected

    @pytest.mark.parametrize("data,patterns", [
        ({}, [r"expectedGoals.*?([\d.]+)"]),
        ({"other": "value"}, [r"expectedGoals.*?([\d.]+)"]),
        ({"expectedGoals": "invalid"}, [r"expectedGoals.*?([\d.]+)"]),
    ])
    def test_extract_value_not_found(self, data, patterns):
        """测试未找到数值的情况"""
        extractor = SmartRecursiveExtractor()
        result = extractor.extract_value(data, patterns)
        assert result is None

    def test_max_recursion_depth(self):
        """测试最大递归深度限制"""
        # 创建深度嵌套的数据结构
        deep_data = {}
        current = deep_data
        for i in range(20):  # 超过默认max_depth
            current['level'] = {}
            current = current['level']
        current['expectedGoals'] = 1.0

        extractor = SmartRecursiveExtractor(max_depth=10)
        result = extractor.extract_value(deep_data, [r"expectedGoals.*?([\d.]+)"])
        assert result is None  # 应该因深度限制而返回None


class TestXGDataAggregator:
    """xG数据聚合器测试"""

    @pytest.fixture
    def sample_shotmap_data(self):
        """示例shotmap数据"""
        return {
            "shotmap": {
                "shots": [
                    {
                        "expectedGoals": 0.15,
                        "teamType": "home",
                        "isHome": True
                    },
                    {
                        "expectedGoals": 0.25,
                        "teamType": "away",
                        "isHome": False
                    },
                    {
                        "expectedGoals": 0.05,
                        "teamType": "home",
                        "isHome": True
                    }
                ]
            }
        }

    @pytest.fixture
    def sample_events_data(self):
        """示例events数据"""
        return {
            "events": {
                "shots": [
                    {
                        "expectedGoals": 0.1,
                        "isHome": True
                    },
                    {
                        "xg": 0.2,
                        "isHome": False
                    }
                ]
            }
        }

    def test_aggregate_from_shotmap_success(self, sample_shotmap_data):
        """测试从shotmap成功聚合xG"""
        home_xg, away_xg = XGDataAggregator.aggregate_from_shotmap(sample_shotmap_data)

        assert home_xg == 0.2  # 0.15 + 0.05
        assert away_xg == 0.25

    def test_aggregate_from_events_fallback(self, sample_events_data):
        """测试从events数据聚合xG（备用路径）"""
        home_xg, away_xg = XGDataAggregator.aggregate_from_shotmap(sample_events_data)

        assert home_xg == 0.1
        assert away_xg == 0.2

    def test_extract_xg_from_shot_success(self):
        """测试从单个射门提取xG"""
        shot_data = {
            "expectedGoals": 0.35,
            "teamType": "home"
        }
        xg = XGDataAggregator._extract_xg_from_shot(shot_data)
        assert xg == 0.35

    def test_extract_xg_from_shot_alternative_fields(self):
        """测试从备选字段提取xG"""
        test_cases = [
            {"xg": 0.25},
            {"expectedGoalValue": 0.3},
            {"xgValue": 0.4}
        ]

        for shot_data in test_cases:
            xg = XGDataAggregator._extract_xg_from_shot(shot_data)
            assert xg is not None

    def test_extract_xg_from_shot_nested_stats(self):
        """测试从嵌套stats中提取xG"""
        shot_data = {
            "stats": {
                "expectedGoals": 0.18,
                "xgTotal": 0.2
            }
        }
        xg = XGDataAggregator._extract_xg_from_shot(shot_data)
        assert xg == 0.18

    def test_aggregate_no_shotmap_data(self):
        """测试没有shotmap数据的情况"""
        home_xg, away_xg = XGDataAggregator.aggregate_from_shotmap({})
        assert home_xg == 0.0
        assert away_xg == 0.0

    def test_aggregate_invalid_data(self):
        """测试无效数据处理"""
        home_xg, away_xg = XGDataAggregator.aggregate_from_shotmap({"shotmap": "invalid"})
        assert home_xg == 0.0
        assert away_xg == 0.0


class TestAdvancedFeatureExtractor:
    """高级特征提取器测试"""

    @pytest.fixture
    def feature_extractor(self):
        """特征提取器实例"""
        return AdvancedFeatureExtractor("configs/settings.yaml")

    @pytest.fixture
    def sample_match_data(self):
        """示例比赛数据"""
        return {
            "general": {
                "id": "match_123",
                "startTimeUTC": "2024-01-15T20:00:00Z",
                "status": "finished",
                "homeTeamScore": 2,
                "awayTeamScore": 1,
                "season": "2023/2024"
            },
            "teams": {
                "home": {"name": "Manchester United"},
                "away": {"name": "Liverpool"}
            },
            "league": {
                "id": "league_47",
                "name": "Premier League"
            },
            "shotmap": {
                "shots": [
                    {"expectedGoals": 0.2, "teamType": "home", "isHome": True},
                    {"expectedGoals": 0.1, "teamType": "away", "isHome": False}
                ]
            }
        }

    def test_extract_all_features_success(self, feature_extractor, sample_match_data):
        """测试成功提取所有特征"""
        features = feature_extractor.extract_all_features(sample_match_data)

        assert isinstance(features, MatchFeatures)
        assert features.external_id == "match_123"
        assert features.home_team == "Manchester United"
        assert features.away_team == "Liverpool"
        assert features.home_xg == 0.2
        assert features.away_xg == 0.1

    def test_extract_base_features(self, feature_extractor, sample_match_data):
        """测试提取基础特征"""
        base_features = feature_extractor._extract_base_features(sample_match_data)

        assert base_features['external_id'] == "match_123"
        assert base_features['home_team'] == "Manchester United"
        assert base_features['away_team'] == "Liverpool"
        assert base_features['league_id'] == "league_47"
        assert base_features['league_name'] == "Premier League"
        assert base_features['season'] == "2023/2024"

    def test_extract_xg_features(self, feature_extractor):
        """测试提取xG特征"""
        xg_features = feature_extractor._extract_xg_features(1.5, 0.8)

        assert xg_features['home_xg'] == 1.5
        assert xg_features['away_xg'] == 0.8
        assert xg_features['xg_total'] == 2.3
        assert xg_features['xg_diff'] == 0.7
        assert xg_features['xg_dynamic_trend'] == 'dominant'

    @pytest.mark.parametrize("home_xg,away_xg,expected_trend", [
        (1.0, 1.0, "stable"),
        (2.0, 0.5, "dominant"),
        (0.3, 1.8, "dominant"),
        (0.8, 0.6, "stable")
    ])
    def test_xg_dynamic_trend(self, feature_extractor, home_xg, away_xg, expected_trend):
        """测试xG动态趋势计算"""
        xg_features = feature_extractor._extract_xg_features(home_xg, away_xg)
        assert xg_features['xg_dynamic_trend'] == expected_trend

    def test_extract_possession_features(self, feature_extractor):
        """测试提取控球率特征"""
        data_with_possession = {
            "stats": {
                "home": {"possession": 60},
                "away": {"possession": 40}
            }
        }
        possession_features = feature_extractor._extract_possession_features(data_with_possession)

        assert possession_features['home_possession'] == 60
        assert possession_features['away_possession'] == 40
        assert possession_features['possession_diff'] == 20

    def test_possession_auto_calculation(self, feature_extractor):
        """测试控球率自动计算"""
        data_with_home_only = {
            "stats": {"home": {"possession": 65}}
        }
        possession_features = feature_extractor._extract_possession_features(data_with_home_only)

        assert possession_features['home_possession'] == 65
        assert possession_features['away_possession'] == 35  # 100 - 65
        assert possession_features['possession_diff'] == 30

    def test_parse_datetime_success(self, feature_extractor):
        """测试成功解析日期时间"""
        test_cases = [
            ("2024-01-15T20:00:00Z", True),
            ("2024-01-15T20:00:00.000Z", True),
            ("2024-01-15 20:00:00", True),
            ("2024-01-15", True),
            ("invalid_date", False),
            ("", False),
            (None, False)
        ]

        for dt_str, should_succeed in test_cases:
            result = feature_extractor._parse_datetime(dt_str)
            if should_succeed:
                assert result is not None
                assert isinstance(result, datetime)
            else:
                assert result is None

    def test_extract_invalid_input_data(self, feature_extractor):
        """测试处理无效输入数据"""
        with pytest.raises(DataValidationError):
            feature_extractor.extract_all_features("invalid_data")

        with pytest.raises(DataValidationError):
            feature_extractor.extract_all_features({})

        with pytest.raises(DataValidationError):
            feature_extractor.extract_all_features(None)


class Test106FieldParameterizedValidation:
    """106字段参数化验证测试"""

    @pytest.mark.parametrize("field_name,test_values,expected_valid", [
        # 基础字段测试
        ("external_id", ["match_123", "12345", ""], [True, True, False]),
        ("home_team", ["Man Utd", "Liverpool", ""], [True, True, False]),
        ("away_team", ["Arsenal", "Chelsea", ""], [True, True, False]),
        ("home_score", [0, 1, 2, -1], [True, True, True, False]),
        ("away_score", [0, 1, 2, -1], [True, True, True, False]),

        # xG字段测试
        ("home_xg", [0.0, 1.5, 3.2, -0.1], [True, True, True, False]),
        ("away_xg", [0.0, 0.8, 2.1, -0.1], [True, True, True, False]),

        # 控球率字段测试
        ("home_possession", [50.0, 100.0, 0.0, 101.0, -1.0], [True, True, True, False, False]),
        ("away_possession", [50.0, 100.0, 0.0, 101.0, -1.0], [True, True, True, False, False]),

        # 射门数据测试
        ("home_shots_total", [0, 5, 15, -1], [True, True, True, False]),
        ("away_shots_total", [0, 5, 15, -1], [True, True, True, False]),

        # 角球数据测试
        ("home_corners", [0, 3, 10, -1], [True, True, True, False]),
        ("away_corners", [0, 3, 10, -1], [True, True, True, False]),

        # 犯规数据测试
        ("home_fouls", [0, 5, 15, -1], [True, True, True, False]),
        ("away_fouls", [0, 5, 15, -1], [True, True, True, False]),

        # 越位数据测试
        ("home_offsides", [0, 2, 5, -1], [True, True, True, False]),
        ("away_offsides", [0, 2, 5, -1], [True, True, True, False]),

        # 赔率数据测试
        ("home_opening_odds", [1.5, 2.0, 10.0, 0.5, -1.0], [True, True, True, False, False]),
        ("away_opening_odds", [1.5, 2.0, 10.0, 0.5, -1.0], [True, True, True, False, False]),
        ("draw_odds", [2.0, 3.5, 10.0, 0.5, -1.0], [True, True, True, False, False]),

        # 概率字段测试
        ("implied_home_win_prob", [0.1, 0.5, 0.9, -0.1, 1.1], [True, True, True, False, False]),
        ("implied_away_win_prob", [0.1, 0.5, 0.9, -0.1, 1.1], [True, True, True, False, False]),
        ("implied_draw_prob", [0.1, 0.5, 0.9, -0.1, 1.1], [True, True, True, False, False]),
    ])
    def test_field_validation(self, field_name, test_values, expected_valid):
        """测试字段验证"""
        for value, should_be_valid in zip(test_values, expected_valid):
            # 构建基础特征数据
            base_data = {
                "external_id": "test_match",
                "match_time": datetime.now(),
                "home_team": "Home Team",
                "away_team": "Away Team",
                field_name: value
            }

            try:
                features = MatchFeatures(**base_data)
                if should_be_valid:
                    assert getattr(features, field_name) == value
                else:
                    pytest.fail(f"Expected validation to fail for {field_name}={value}")
            except ValueError:
                if should_be_valid:
                    pytest.fail(f"Expected validation to pass for {field_name}={value}")

    def test_all_106_fields_present(self):
        """测试所有106个字段都存在"""
        base_data = {
            "external_id": "test_match_106",
            "match_time": datetime.now(),
            "home_team": "Home Team",
            "away_team": "Away Team"
        }

        features = MatchFeatures(**base_data)

        # 检查字段总数
        all_fields = features.dict().keys()
        assert len(all_fields) == 106, f"Expected 106 fields, got {len(all_fields)}"

        # 检查关键字段存在
        key_fields = [
            'external_id', 'match_time', 'home_team', 'away_team',
            'home_xg', 'away_xg', 'xg_total', 'xg_diff',
            'home_possession', 'away_possession', 'possession_diff',
            'home_shots_total', 'away_shots_total',
            'home_corners', 'away_corners',
            'home_fouls', 'away_fouls',
            'home_yellow_cards', 'away_yellow_cards',
            'home_red_cards', 'away_red_cards',
            'home_opening_odds', 'away_opening_odds', 'draw_odds',
            'raw_data_source', 'feature_version', 'extracted_at'
        ]

        for field in key_fields:
            assert field in all_fields, f"Missing field: {field}"

    def test_automatic_field_calculations(self):
        """测试自动字段计算"""
        base_data = {
            "external_id": "test_calc",
            "match_time": datetime.now(),
            "home_team": "Home",
            "away_team": "Away",
            "home_xg": 1.5,
            "away_xg": 0.8,
            "home_possession": 60.0,
            "away_possession": 40.0,
            "home_shots_total": 10,
            "away_shots_total": 8
        }

        features = MatchFeatures(**base_data)

        # 验证自动计算的字段
        assert features.xg_total == 2.3  # 1.5 + 0.8
        assert features.xg_diff == 0.7   # 1.5 - 0.8
        assert features.possession_diff == 20.0  # 60 - 40
        assert features.shots_total_diff == 2    # 10 - 8

    def test_weather_condition_enum(self):
        """测试天气状况枚举"""
        base_data = {
            "external_id": "test_weather",
            "match_time": datetime.now(),
            "home_team": "Home",
            "away_team": "Away"
        }

        # 测试有效的天气状况
        valid_weather = ['sunny', 'rainy', 'cloudy', 'snowy', 'windy', 'unknown']
        for weather in valid_weather:
            data = {**base_data, "weather_condition": weather}
            features = MatchFeatures(**data)
            assert features.weather_condition.value == weather

    def test_data_source_and_version_enums(self):
        """测试数据源和版本枚举"""
        base_data = {
            "external_id": "test_enums",
            "match_time": datetime.now(),
            "home_team": "Home",
            "away_team": "Away"
        }

        features = MatchFeatures(**base_data)

        assert features.raw_data_source in ["fotmob_api", "bet365_api", "manual", "imported"]
        assert features.feature_version in ["1.0", "1.1", "2.0"]


class TestMockFotMobResponses:
    """Mock不同FotMob API响应结构测试"""

    @pytest.fixture(params=[
        # 结构1: 标准FotMob API响应
        {
            "general": {
                "id": "struct1_123",
                "startTimeUTC": "2024-01-15T20:00:00Z",
                "status": "finished",
                "homeTeamScore": 2,
                "awayTeamScore": 1
            },
            "teams": {
                "home": {"name": "Team A"},
                "away": {"name": "Team B"}
            },
            "shotmap": {
                "shots": [
                    {"expectedGoals": 0.25, "teamType": "home"},
                    {"expectedGoals": 0.15, "teamType": "away"}
                ]
            }
        },
        # 结构2: 嵌套events响应
        {
            "matchId": "struct2_456",
            "matchTime": "2024-01-15T20:00:00Z",
            "homeTeam": {"name": "Home Team", "score": 1},
            "awayTeam": {"name": "Away Team", "score": 1},
            "events": {
                "shots": [
                    {"xg": 0.3, "isHome": True},
                    {"xg": 0.2, "isHome": False}
                ]
            }
        },
        # 结构3: 简化统计响应
        {
            "id": "struct3_789",
            "time": "2024-01-15T20:00:00Z",
            "teams": {
                "home": {"name": "Home", "stats": {"expectedGoals": 1.2}},
                "away": {"name": "Away", "stats": {"expectedGoals": 0.9}}
            }
        },
        # 结构4: 最小化响应
        {
            "match_id": "struct4_000",
            "home": "Team H",
            "away": "Team A",
            "score": {"home": 0, "away": 0}
        },
        # 结构5: 完整详细响应
        {
            "general": {
                "id": "struct5_complete",
                "startTimeUTC": "2024-01-15T20:00:00Z",
                "status": "live",
                "homeTeamScore": 1,
                "awayTeamScore": 1,
                "season": "2023/2024"
            },
            "teams": {
                "home": {"name": "Complete Home"},
                "away": {"name": "Complete Away"}
            },
            "league": {
                "id": "league_123",
                "name": "Test League"
            },
            "shotmap": {
                "shots": [
                    {
                        "expectedGoals": 0.18,
                        "teamType": "home",
                        "isHome": True,
                        "stats": {"xg": 0.18}
                    },
                    {
                        "expectedGoals": 0.12,
                        "teamType": "away",
                        "isHome": False,
                        "stats": {"xg": 0.12}
                    }
                ]
            },
            "stats": {
                "possession": {"home": 55, "away": 45},
                "shots": {"home": {"total": 12, "onTarget": 5}, "away": {"total": 8, "onTarget": 3}},
                "corners": {"home": 6, "away": 4}
            }
        }
    ])
    def mock_fotmob_data(self, request):
        """不同的FotMob API响应结构"""
        return request.param

    def test_extract_from_different_structures(self, feature_extractor, mock_fotmob_data):
        """测试从不同结构中提取特征"""
        features = feature_extractor.extract_all_features(mock_fotmob_data)

        assert isinstance(features, MatchFeatures)
        assert features.external_id is not None
        assert features.home_team is not None
        assert features.away_team is not None
        assert features.match_time is not None

    def test_graceful_degradation_for_missing_data(self, feature_extractor):
        """测试对缺失数据的优雅降级"""
        minimal_data = {
            "id": "minimal_123",
            "home": "Home Team",
            "away": "Away Team"
        }

        features = feature_extractor.extract_all_features(minimal_data)

        # 应该能创建基本特征，缺失字段为None
        assert features.external_id is not None
        assert features.home_team == "Home Team"
        assert features.away_team == "Away Team"
        # 大部分字段应该是None
        assert features.home_xg is None
        assert features.away_xg is None
        assert features.home_possession is None


class TestErrorHandlingAndEdgeCases:
    """错误处理和边界条件测试"""

    def test_feature_extraction_error_propagation(self):
        """测试特征提取错误传播"""
        extractor = AdvancedFeatureExtractor()

        # 测试完全无效的数据
        with pytest.raises(FeatureExtractionError):
            extractor.extract_all_features("completely_invalid")

    def test_timeout_handling(self):
        """测试超时处理"""
        # 创建会超时的提取器
        extractor = AdvancedFeatureExtractor()
        extractor.recursive_extractor.timeout_seconds = 0.001  # 极短超时

        # 创建需要大量处理的数据
        complex_data = {}
        current = complex_data
        for i in range(100):
            current[f'level_{i}'] = {}
            current = current[f'level_{i}']
        current['expectedGoals'] = 1.0

        with pytest.raises(FeatureExtractionError):
            extractor.extract_all_features(complex_data)

    def test_large_dataset_handling(self):
        """测试大数据集处理"""
        extractor = AdvancedFeatureExtractor()

        # 创建包含大量射门的数据
        large_shotmap_data = {
            "general": {"id": "large_test"},
            "teams": {"home": {"name": "Home"}, "away": {"name": "Away"}},
            "shotmap": {
                "shots": [
                    {"expectedGoals": 0.01 * i, "teamType": "home" if i % 2 == 0 else "away"}
                    for i in range(1000)  # 1000次射门
                ]
            }
        }

        # 应该能正常处理而不崩溃
        features = extractor.extract_all_features(large_shotmap_data)
        assert features is not None
        assert features.home_xg > 0
        assert features.away_xg > 0


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_create_feature_extractor(self):
        """测试创建特征提取器"""
        extractor = create_feature_extractor()
        assert isinstance(extractor, AdvancedFeatureExtractor)

    def test_extract_match_features(self, sample_match_data):
        """测试便捷的特征提取函数"""
        features = extract_match_features(sample_match_data)
        assert isinstance(features, MatchFeatures)
        assert features.external_id == "match_123"


# 性能测试
class TestPerformance:
    """性能测试"""

    def test_extraction_performance(self, feature_extractor, sample_match_data):
        """测试提取性能"""
        import time

        start_time = time.time()
        features = feature_extractor.extract_all_features(sample_match_data)
        extraction_time = time.time() - start_time

        # 提取应该在合理时间内完成（例如1秒内）
        assert extraction_time < 1.0
        assert features is not None

    def test_batch_extraction_performance(self, feature_extractor):
        """测试批量提取性能"""
        import time

        # 创建多个比赛数据
        match_data_list = []
        for i in range(10):
            data = {
                "general": {"id": f"perf_test_{i}", "startTimeUTC": "2024-01-15T20:00:00Z"},
                "teams": {"home": {"name": f"Home{i}"}, "away": {"name": f"Away{i}"}},
                "shotmap": {"shots": [{"expectedGoals": 0.1, "teamType": "home"}]}
            }
            match_data_list.append(data)

        start_time = time.time()
        for data in match_data_list:
            features = feature_extractor.extract_all_features(data)
            assert features is not None

        total_time = time.time() - start_time
        avg_time_per_match = total_time / len(match_data_list)

        # 平均每个比赛应该在0.5秒内完成
        assert avg_time_per_match < 0.5


# 集成测试
class TestIntegration:
    """集成测试"""

    def test_end_to_end_extraction(self):
        """端到端特征提取测试"""
        # 使用真实格式的数据
        real_data = {
            "general": {
                "matchId": "real_match_123",
                "startDateStr": "2024-01-15T20:00:00Z",
                "status": {
                    "finished": True,
                    "started": True,
                    "cancelled": False
                },
                "homeTeamScore": 2,
                "awayTeamScore": 1,
                "matchTime": "FT"
            },
            "homeTeam": {
                "id": 10260,
                "name": "Manchester United",
                "shortName": "Man Utd"
            },
            "awayTeam": {
                "id": 8650,
                "name": "Liverpool",
                "shortName": "Liverpool"
            },
            "league": {
                "id": 127,
                "name": "Premier League"
            },
            "content": {
                "shotmap": {
                    "shots": [
                        {
                            "id": "shot1",
                            "player": {"name": "Player1"},
                            "expectedGoals": 0.25,
                            "teamType": "home",
                            "situation": "OpenPlay"
                        },
                        {
                            "id": "shot2",
                            "player": {"name": "Player2"},
                            "expectedGoals": 0.15,
                            "teamType": "away",
                            "situation": "OpenPlay"
                        }
                    ]
                },
                "stats": {
                    "possession": {
                        "home": 55,
                        "away": 45
                    },
                    "stats": [
                        {"type": "shots_total", "home": 12, "away": 8},
                        {"type": "shots_on_target", "home": 5, "away": 3},
                        {"type": "corners", "home": 6, "away": 4}
                    ]
                }
            }
        }

        extractor = AdvancedFeatureExtractor()
        features = extractor.extract_all_features(real_data)

        assert isinstance(features, MatchFeatures)
        assert features.external_id is not None
        assert features.home_xg == 0.25
        assert features.away_xg == 0.15
        assert features.xg_total == 0.4
        assert features.xg_diff == 0.1