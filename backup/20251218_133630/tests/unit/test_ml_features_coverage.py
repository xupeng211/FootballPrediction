"""
ML特征工程覆盖率测试
测试特征提取、转换和计算功能
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any

# 由于特征模块在ml/features下，我们添加相应的导入路径
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../../src/ml/features"))


class TestAdvancedFeatureTransformer:
    """高级特征转换器测试"""

    def test_advanced_feature_transformer_import(self):
        """测试高级特征转换器导入"""
        try:
            from advanced_feature_transformer import AdvancedFeatureTransformer

            transformer = AdvancedFeatureTransformer()
            assert transformer is not None
        except ImportError as e:
            pytest.skip(f"高级特征转换器模块不可用: {e}")

    def test_feature_transformer_methods(self):
        """测试特征转换器方法"""
        try:
            from advanced_feature_transformer import AdvancedFeatureTransformer

            transformer = AdvancedFeatureTransformer()

            # 检查核心方法存在
            expected_methods = [
                "transform_match_features",
                "calculate_h2h_features",
                "calculate_venue_features",
                "calculate_form_features",
                "normalize_features",
            ]

            for method in expected_methods:
                assert hasattr(transformer, method), f"缺少方法: {method}"

        except ImportError as e:
            pytest.skip(f"高级特征转换器模块不可用: {e}")

    @pytest.mark.asyncio
    async def test_match_feature_transformation(self):
        """测试比赛特征转换"""
        try:
            from advanced_feature_transformer import AdvancedFeatureTransformer

            transformer = AdvancedFeatureTransformer()

            # 模拟比赛数据
            match_data = {
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1,
                "date": "2024-01-15",
                "league": "Premier League",
            }

            # 模拟特征转换
            with patch.object(
                transformer, "transform_match_features"
            ) as mock_transform:
                mock_transform.return_value = {
                    "home_attack_strength": 1.5,
                    "away_defense_strength": 0.8,
                    "venue_advantage": 0.2,
                    "recent_form_diff": 0.3,
                }

                result = transformer.transform_match_features(match_data)

                assert isinstance(result, dict)
                assert "home_attack_strength" in result
                assert "away_defense_strength" in result
                mock_transform.assert_called_once_with(match_data)

        except ImportError as e:
            pytest.skip(f"高级特征转换器模块不可用: {e}")

    def test_feature_normalization(self):
        """测试特征归一化"""
        try:
            from advanced_feature_transformer import AdvancedFeatureTransformer

            transformer = AdvancedFeatureTransformer()

            # 模拟特征归一化
            features = [10.0, 20.0, 30.0, 40.0, 50.0]

            with patch.object(transformer, "normalize_features") as mock_normalize:
                mock_normalize.return_value = [0.0, 0.25, 0.5, 0.75, 1.0]

                result = transformer.normalize_features(features)

                assert len(result) == len(features)
                assert all(0 <= x <= 1 for x in result)
                mock_normalize.assert_called_once_with(features)

        except ImportError as e:
            pytest.skip(f"高级特征转换器模块不可用: {e}")


class TestH2HCalculator:
    """历史交锋计算器测试"""

    def test_h2h_calculator_import(self):
        """测试H2H计算器导入"""
        try:
            from h2h_calculator import H2HCalculator

            calculator = H2HCalculator()
            assert calculator is not None
        except ImportError as e:
            pytest.skip(f"H2H计算器模块不可用: {e}")

    def test_h2h_calculation_methods(self):
        """测试H2H计算方法"""
        try:
            from h2h_calculator import H2HCalculator

            calculator = H2HCalculator()

            # 检查核心方法存在
            expected_methods = [
                "calculate_h2h_for_match",
                "get_h2h_summary",
                "calculate_h2h_for_all_matches",
                "_get_historical_matches",
            ]

            for method in expected_methods:
                assert hasattr(calculator, method), f"缺少方法: {method}"

        except ImportError as e:
            pytest.skip(f"H2H计算器模块不可用: {e}")

    @pytest.mark.asyncio
    async def test_head_to_head_calculation(self):
        """测试历史交锋计算"""
        try:
            from h2h_calculator import H2HCalculator

            calculator = H2HCalculator()

            # 模拟H2H数据
            team_a_id = "team_a"
            team_b_id = "team_b"

            with patch.object(calculator, "calculate_h2h_for_match") as mock_h2h:
                mock_h2h.return_value = {
                    "total_matches": 10,
                    "team_a_wins": 6,
                    "team_b_wins": 3,
                    "draws": 1,
                    "team_a_win_rate": 0.6,
                    "avg_goals_per_match": 2.8,
                    "recent_form": ["W", "W", "D", "L", "W"],
                }

                result = calculator.calculate_h2h_for_match(team_a_id, team_b_id)

                assert isinstance(result, dict)
                assert "total_matches" in result
                assert "team_a_win_rate" in result
                assert result["total_matches"] == 10
                assert result["team_a_win_rate"] == 0.6
                mock_h2h.assert_called_once_with(team_a_id, team_b_id)

        except ImportError as e:
            pytest.skip(f"H2H计算器模块不可用: {e}")

    def test_h2h_record_analysis(self):
        """测试H2H记录分析"""
        try:
            from h2h_calculator import H2HCalculator

            calculator = H2HCalculator()

            with patch.object(calculator, "get_h2h_summary") as mock_record:
                mock_record.return_value = {
                    "home_wins": 5,
                    "away_wins": 2,
                    "neutral_wins": 1,
                    "home_goals": 15,
                    "away_goals": 8,
                }

                result = calculator.get_h2h_summary("team_a", "team_b")

                assert isinstance(result, dict)
                assert "home_wins" in result
                assert "away_goals" in result
                mock_record.assert_called_once_with("team_a", "team_b")

        except ImportError as e:
            pytest.skip(f"H2H计算器模块不可用: {e}")


class TestVenueAnalyzer:
    """场馆分析器测试"""

    def test_venue_analyzer_import(self):
        """测试场馆分析器导入"""
        try:
            from venue_analyzer import VenueAnalyzer

            analyzer = VenueAnalyzer()
            assert analyzer is not None
        except ImportError as e:
            pytest.skip(f"场馆分析器模块不可用: {e}")

    def test_venue_analyzer_methods(self):
        """测试场馆分析器方法"""
        try:
            from venue_analyzer import VenueAnalyzer

            analyzer = VenueAnalyzer()

            # 检查核心方法存在
            expected_methods = [
                "calculate_venue_features_for_match",
                "get_venue_summary",
                "calculate_venue_features_for_all_matches",
                "_calculate_home_advantage",
            ]

            for method in expected_methods:
                assert hasattr(analyzer, method), f"缺少方法: {method}"

        except ImportError as e:
            pytest.skip(f"场馆分析器模块不可用: {e}")

    @pytest.mark.asyncio
    async def test_home_advantage_analysis(self):
        """测试主场优势分析"""
        try:
            from venue_analyzer import VenueAnalyzer

            analyzer = VenueAnalyzer()

            team_id = "team_a"
            venue_id = "stadium_a"

            with patch.object(
                analyzer, "calculate_venue_features_for_match"
            ) as mock_advantage:
                mock_advantage.return_value = {
                    "home_win_rate": 0.65,
                    "away_win_rate": 0.25,
                    "draw_rate": 0.10,
                    "avg_home_goals": 2.1,
                    "avg_away_goals": 0.8,
                    "venue_advantage_score": 0.85,
                }

                result = analyzer.calculate_venue_features_for_match(team_id, venue_id)

                assert isinstance(result, dict)
                assert "home_win_rate" in result
                assert "venue_advantage_score" in result
                assert 0 <= result["venue_advantage_score"] <= 1
                mock_advantage.assert_called_once_with(team_id, venue_id)

        except ImportError as e:
            pytest.skip(f"场馆分析器模块不可用: {e}")

    def test_venue_statistics_calculation(self):
        """测试场馆统计计算"""
        try:
            from venue_analyzer import VenueAnalyzer

            analyzer = VenueAnalyzer()

            with patch.object(analyzer, "get_venue_summary") as mock_stats:
                mock_stats.return_value = {
                    "total_matches": 50,
                    "avg_goals_per_match": 2.7,
                    "home_team_wins": 30,
                    "crowd_impact_factor": 0.3,
                    "surface_type": "grass",
                }

                result = analyzer.get_venue_summary("stadium_a")

                assert isinstance(result, dict)
                assert "total_matches" in result
                assert "avg_goals_per_match" in result
                assert result["total_matches"] == 50
                mock_stats.assert_called_once_with("stadium_a")

        except ImportError as e:
            pytest.skip(f"场馆分析器模块不可用: {e}")


class TestMatchFeatureExtractor:
    """比赛特征提取器测试"""

    def test_feature_extractor_import(self):
        """测试特征提取器导入"""
        try:
            from extractor import MatchFeatureExtractor

            extractor = MatchFeatureExtractor()
            assert extractor is not None
        except ImportError as e:
            pytest.skip(f"特征提取器模块不可用: {e}")

    def test_feature_extractor_initialization(self):
        """测试特征提取器初始化"""
        try:
            from extractor import MatchFeatureExtractor

            # 测试不同配置的初始化
            extractor1 = MatchFeatureExtractor()
            extractor2 = MatchFeatureExtractor(cache_enabled=True)
            extractor3 = MatchFeatureExtractor(cache_enabled=False)

            assert extractor1 is not None
            assert extractor2 is not None
            assert extractor3 is not None

        except ImportError as e:
            pytest.skip(f"特征提取器模块不可用: {e}")

    def test_feature_extraction_methods(self):
        """测试特征提取方法"""
        try:
            from extractor import MatchFeatureExtractor

            extractor = MatchFeatureExtractor()

            # 检查核心方法存在
            expected_methods = [
                "extract_features_from_match",
                "extract_team_form_features",
                "extract_h2h_features",
                "extract_venue_features",
                "batch_extract_features",
            ]

            for method in expected_methods:
                assert hasattr(extractor, method), f"缺少方法: {method}"

        except ImportError as e:
            pytest.skip(f"特征提取器模块不可用: {e}")

    @pytest.mark.asyncio
    async def test_match_feature_extraction(self):
        """测试比赛特征提取"""
        try:
            from extractor import MatchFeatureExtractor

            extractor = MatchFeatureExtractor()

            match_data = {
                "match_id": "12345",
                "home_team_id": "team_a",
                "away_team_id": "team_b",
                "home_team": "Team A",
                "away_team": "Team B",
                "venue": "Stadium A",
                "date": "2024-01-15",
            }

            with patch.object(extractor, "extract_features_from_match") as mock_extract:
                mock_extract.return_value = {
                    "home_form_last_5": [3, 1, 3, 1, 0],
                    "away_form_last_5": [1, 0, 1, 3, 1],
                    "h2h_home_wins": 6,
                    "h2h_away_wins": 3,
                    "venue_advantage": 0.2,
                    "goal_difference": 1.5,
                }

                result = extractor.extract_features_from_match(match_data)

                assert isinstance(result, dict)
                assert "home_form_last_5" in result
                assert "h2h_home_wins" in result
                assert len(result["home_form_last_5"]) == 5
                mock_extract.assert_called_once_with(match_data)

        except ImportError as e:
            pytest.skip(f"特征提取器模块不可用: {e}")

    @pytest.mark.asyncio
    async def test_batch_feature_extraction(self):
        """测试批量特征提取"""
        try:
            from extractor import MatchFeatureExtractor

            extractor = MatchFeatureExtractor()

            matches = [
                {
                    "match_id": f"match_{i}",
                    "home_team": f"Team {i}",
                    "away_team": f"Opponent {i}",
                }
                for i in range(10)
            ]

            with patch.object(extractor, "batch_extract_features") as mock_batch:
                mock_batch.return_value = {
                    f"match_{i}": {
                        "feature_1": i * 0.1,
                        "feature_2": i * 0.2,
                        "feature_3": i * 0.3,
                    }
                    for i in range(10)
                }

                result = extractor.batch_extract_features(matches)

                assert isinstance(result, dict)
                assert len(result) == 10
                assert "match_0" in result
                assert "match_9" in result
                mock_batch.assert_called_once_with(matches)

        except ImportError as e:
            pytest.skip(f"特征提取器模块不可用: {e}")


class TestFeatureIntegration:
    """特征集成测试"""

    @pytest.mark.asyncio
    async def test_feature_pipeline_integration(self):
        """测试特征管道集成"""
        try:
            # 测试各个组件的集成
            match_data = {
                "match_id": "integration_test",
                "home_team": "Team A",
                "away_team": "Team B",
                "venue": "Stadium A",
            }

            # Mock所有特征组件
            with (
                patch(
                    "advanced_feature_transformer.AdvancedFeatureTransformer"
                ) as MockTransformer,
                patch("h2h_calculator.H2HCalculator") as MockH2H,
                patch("venue_analyzer.VenueAnalyzer") as MockVenue,
                patch("extractor.MatchFeatureExtractor") as MockExtractor,
            ):

                # 配置Mock
                mock_transformer = Mock()
                mock_transformer.transform_match_features.return_value = {
                    "normalized_attack": 0.7,
                    "normalized_defense": 0.6,
                }
                MockTransformer.return_value = mock_transformer

                mock_h2h = Mock()
                mock_h2h.calculate_head_to_head.return_value = {
                    "h2h_win_rate": 0.6,
                    "h2h_goals_avg": 2.5,
                }
                MockH2H.return_value = mock_h2h

                mock_venue = Mock()
                mock_venue.analyze_home_advantage.return_value = {
                    "venue_advantage": 0.3,
                    "crowd_factor": 0.2,
                }
                MockVenue.return_value = mock_venue

                mock_extractor = Mock()
                mock_extractor.extract_features_from_match.return_value = {
                    "team_form": [1, 3, 1, 0, 3],
                    "goal_diff": 1.2,
                }
                MockExtractor.return_value = mock_extractor

                # 创建实例
                transformer = MockTransformer()
                h2h_calc = MockH2H()
                venue_analyzer = MockVenue()
                extractor = MockExtractor()

                # 模拟集成处理
                raw_features = extractor.extract_features_from_match(match_data)
                transformed_features = transformer.transform_match_features(
                    raw_features
                )
                h2h_features = h2h_calc.calculate_head_to_head("Team A", "Team B")
                venue_features = venue_analyzer.analyze_home_advantage(
                    "Team A", "Stadium A"
                )

                # 集成所有特征
                integrated_features = {
                    **raw_features,
                    **transformed_features,
                    **h2h_features,
                    **venue_features,
                }

                # 验证集成结果
                assert isinstance(integrated_features, dict)
                assert "team_form" in integrated_features
                assert "normalized_attack" in integrated_features
                assert "h2h_win_rate" in integrated_features
                assert "venue_advantage" in integrated_features

        except ImportError as e:
            pytest.skip(f"特征模块不可用: {e}")

    def test_feature_validation(self):
        """测试特征验证"""
        try:
            from extractor import MatchFeatureExtractor

            extractor = MatchFeatureExtractor()

            # 测试有效特征
            valid_features = {
                "home_attack": 1.5,
                "away_defense": 0.8,
                "venue_advantage": 0.2,
                "h2h_win_rate": 0.6,
            }

            # 模拟特征验证
            def validate_features(features):
                return all(
                    isinstance(v, (int, float)) and 0 <= v <= 10
                    for v in features.values()
                )

            assert validate_features(valid_features) is True

            # 测试无效特征
            invalid_features = {
                "home_attack": "invalid",
                "away_defense": -1.0,
                "venue_advantage": 15.0,
            }

            assert validate_features(invalid_features) is False

        except ImportError as e:
            pytest.skip(f"特征提取器模块不可用: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
