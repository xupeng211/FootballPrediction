#!/usr/bin/env python3
"""
泊松分布特征计算系统单元测试

Phase 5 Advanced Features 核心算法测试覆盖

测试覆盖范围：
- 泊松分布基础计算
- 球队λ值计算
- 比赛概率预测
- 特征工程提取
- 边界条件处理
- 数学精度验证
- 数据质量验证
- 性能压力测试

Author: Football Prediction Team
Version: 1.0.0 (Sprint 7 Testing)
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

from src.constants import FOOTBALL, MATH, PROBABILITY, STATISTICAL

# 导入被测试的模块
from src.ml.features.poisson_features import PoissonFeatureCalculator


class TestPoissonFeatureCalculator:
    """泊松特征计算器测试类"""

    @pytest.fixture
    def calculator(self):
        """创建泊松特征计算器实例"""
        return PoissonFeatureCalculator(
            home_lambda_default=1.5,
            away_lambda_default=1.2,
            league_avg_goals=2.7,
            enable_team_strength_adjustment=True,
            enable_venue_adjustment=True,
            enable_time_decay=True,
            max_goals_calc=10,
        )

    @pytest.fixture
    def sample_matches_data(self):
        """示例比赛数据"""
        base_date = datetime.now() - timedelta(days=30)
        return [
            {
                "match_date": base_date - timedelta(days=0),
                "home_goals": 2,
                "away_goals": 1,
                "team_is_home": True,
            },
            {
                "match_date": base_date - timedelta(days=7),
                "home_goals": 1,
                "away_goals": 3,
                "team_is_home": True,
            },
            {
                "match_date": base_date - timedelta(days=14),
                "home_goals": 0,
                "away_goals": 2,
                "team_is_home": False,
            },
            {
                "match_date": base_date - timedelta(days=21),
                "home_goals": 3,
                "away_goals": 1,
                "team_is_home": False,
            },
            {
                "match_date": base_date - timedelta(days=28),
                "home_goals": 1,
                "away_goals": 1,
                "team_is_home": True,
            },
        ]

    @pytest.fixture
    def strong_team_data(self):
        """强队数据（高进球能力）"""
        base_date = datetime.now() - timedelta(days=30)
        return [
            {
                "match_date": base_date - timedelta(days=i * 7),
                "home_goals": 3 + i % 2,
                "away_goals": 1,
                "team_is_home": i % 2 == 0,
            }
            for i in range(10)
        ]

    @pytest.fixture
    def weak_team_data(self):
        """弱队数据（低进球能力）"""
        base_date = datetime.now() - timedelta(days=30)
        return [
            {
                "match_date": base_date - timedelta(days=i * 7),
                "home_goals": 0,
                "away_goals": 2 + i % 2,
                "team_is_home": i % 2 == 1,
            }
            for i in range(10)
        ]

    # ========== 基础功能测试 ==========

    def test_calculator_initialization(self):
        """测试计算器初始化"""
        calc = PoissonFeatureCalculator()

        assert calc.home_lambda_default == 1.5
        assert calc.away_lambda_default == 1.2
        assert calc.league_avg_goals == 2.7
        assert calc.enable_team_strength_adjustment is True
        assert calc.enable_venue_adjustment is True
        assert calc.enable_time_decay is True
        assert calc.max_goals_calc == 10
        assert isinstance(calc.team_data, dict)
        assert isinstance(calc.stats, dict)

    def test_calculator_custom_initialization(self):
        """测试自定义参数初始化"""
        calc = PoissonFeatureCalculator(
            home_lambda_default=2.0,
            away_lambda_default=1.0,
            league_avg_goals=3.0,
            enable_team_strength_adjustment=False,
            enable_venue_adjustment=False,
            enable_time_decay=False,
            max_goals_calc=8,
        )

        assert calc.home_lambda_default == 2.0
        assert calc.away_lambda_default == 1.0
        assert calc.league_avg_goals == 3.0
        assert calc.enable_team_strength_adjustment is False
        assert calc.enable_venue_adjustment is False
        assert calc.enable_time_decay is False
        assert calc.max_goals_calc == 8

    # ========== 球队λ值计算测试 ==========

    def test_calculate_team_lambdas_sufficient_data(self, calculator, sample_matches_data):
        """测试数据充足时的λ值计算"""
        attack_lambda, defense_lambda, details = calculator.calculate_team_lambdas(
            team_id="team_test", matches_data=sample_matches_data, is_home_team=True
        )

        assert attack_lambda > 0
        assert defense_lambda > 0
        assert details["status"] == "success"
        assert details["matches_used"] == len(sample_matches_data)
        assert "attack_lambda" in details
        assert "defense_lambda" in details
        assert "venue_factor" in details

    def test_calculate_team_lambdas_insufficient_data(self, calculator, sample_matches_data):
        """测试数据不足时的默认值使用"""
        insufficient_data = sample_matches_data[:2]  # 只有2场比赛，少于MIN_GAMES_FOR_LAMBDA(5)

        attack_lambda, defense_lambda, details = calculator.calculate_team_lambdas(
            team_id="team_insufficient",
            matches_data=insufficient_data,
            is_home_team=True,
        )

        assert details["status"] == "insufficient_data"
        assert attack_lambda == calculator.home_lambda_default
        assert defense_lambda == calculator.league_avg_goals - calculator.home_lambda_default
        assert details["matches_used"] == 2

    def test_calculate_team_lambdas_away_team(self, calculator, sample_matches_data):
        """测试客队λ值计算"""
        attack_lambda, defense_lambda, details = calculator.calculate_team_lambdas(
            team_id="away_team", matches_data=sample_matches_data, is_home_team=False
        )

        assert attack_lambda > 0
        assert defense_lambda > 0
        assert details["status"] == "success"
        # 客队应该使用不同的默认值
        if details["matches_used"] < calculator.MIN_GAMES_FOR_LAMBDA:
            assert attack_lambda == calculator.away_lambda_default

    def test_team_strength_adjustment(self, calculator, strong_team_data):
        """测试球队实力调整"""
        # 启用实力调整
        attack_lambda_enabled, defense_lambda_enabled, _ = calculator.calculate_team_lambdas(
            team_id="strong_team", matches_data=strong_team_data, is_home_team=True
        )

        # 禁用实力调整
        calculator.disable_strength = calculator.enable_team_strength_adjustment
        calculator.enable_team_strength_adjustment = False

        attack_lambda_disabled, defense_lambda_disabled, _ = calculator.calculate_team_lambdas(
            team_id="strong_team_no_adjust",
            matches_data=strong_team_data,
            is_home_team=True,
        )

        # 强队的λ值在启用调整后应该稍微保守（降低）
        assert attack_lambda_enabled <= attack_lambda_disabled

        # 恢复设置
        calculator.enable_team_strength_adjustment = calculator.disable_strength

    def test_venue_adjustment(self, calculator):
        """测试场地调整"""
        # 创建主客场表现差异明显的数据
        venue_specific_data = [
            {
                "match_date": datetime.now() - timedelta(days=i * 7),
                "home_goals": 3 if i % 2 == 0 else 0,  # 主场进3球，客场0球
                "away_goals": 1,
                "team_is_home": i % 2 == 0,
            }
            for i in range(6)
        ]

        attack_lambda, defense_lambda, details = calculator.calculate_team_lambdas(
            team_id="venue_team", matches_data=venue_specific_data, is_home_team=True
        )

        assert details["venue_factor"] > 1.0  # 主场优势应该被识别
        assert attack_lambda > 0

    def test_time_decay_functionality(self, calculator):
        """测试时间衰减功能"""
        # 创建跨越较长时间的数据
        old_date = datetime.now() - timedelta(days=100)
        recent_date = datetime.now() - timedelta(days=1)

        time_spread_data = [
            {
                "match_date": old_date,
                "home_goals": 5,
                "away_goals": 0,
                "team_is_home": True,
            },
            {
                "match_date": recent_date,
                "home_goals": 1,
                "away_goals": 1,
                "team_is_home": True,
            },
        ]

        attack_lambda, defense_lambda, details = calculator.calculate_team_lambdas(
            team_id="time_team", matches_data=time_spread_data, is_home_team=True
        )

        # 由于时间衰减，最近比赛权重更高，平均进球应该接近1而不是3
        assert attack_lambda < 3.0
        assert attack_lambda > 0.5

    # ========== 比赛概率计算测试 ==========

    def test_calculate_match_probabilities_basic(self, calculator):
        """测试基础比赛概率计算"""
        # 先设置球队数据
        calculator.team_data["home_team"] = {
            "attack_lambda": 1.8,
            "defense_lambda": 0.8,
        }
        calculator.team_data["away_team"] = {
            "attack_lambda": 1.2,
            "defense_lambda": 1.5,
        }

        result = calculator.calculate_match_probabilities(home_team_id="home_team", away_team_id="away_team")

        # 验证结果结构
        assert "match_info" in result
        assert "expected_goals" in result
        assert "team_lambdas" in result
        assert "probabilities" in result
        assert "top_scores" in result
        assert "goals_distribution" in result
        assert "model_features" in result
        assert "confidence_metrics" in result

        # 验证概率值合理性
        probs = result["probabilities"]
        assert 0 <= probs["home_win"] <= 1
        assert 0 <= probs["draw"] <= 1
        assert 0 <= probs["away_win"] <= 1
        assert abs(probs["home_win"] + probs["draw"] + probs["away_win"] - 1.0) < 0.001

        # 验证预期进球
        expected = result["expected_goals"]
        assert expected["home"] > 0
        assert expected["away"] > 0
        assert expected["total"] > 0

    def test_calculate_match_probabilities_custom_lambdas(self, calculator):
        """测试使用自定义λ值的概率计算"""
        result = calculator.calculate_match_probabilities(
            home_team_id="custom_home",
            away_team_id="custom_away",
            home_attack_lambda=2.0,
            home_defense_lambda=0.8,
            away_attack_lambda=1.3,
            away_defense_lambda=1.6,
        )

        expected = result["expected_goals"]
        assert expected["home"] > 1.3  # 主队进攻强，对手防守弱 (调整期望值)
        assert expected["away"] > 0.3

        # 主队优势应该体现
        probs = result["probabilities"]
        assert probs["home_win"] > probs["away_win"]

    def test_score_matrix_calculation(self, calculator):
        """测试比分概率矩阵计算"""
        matrix = calculator._calculate_score_matrix(1.5, 1.2)

        assert matrix.shape == (11, 11)  # 0-10进球 x 0-10进球
        assert np.all(matrix >= 0)

        # 矩阵概率总和应该接近1
        total_prob = np.sum(matrix)
        assert 0.95 < total_prob < 1.05  # 允许小的数值误差

        # 最可能的比分应该是0-0, 1-0, 0-1, 1-1, 2-1等
        top_indices = np.unravel_index(np.argsort(matrix.ravel())[-5:], matrix.shape)
        assert len(top_indices[0]) == 5

    def test_probability_calculations(self, calculator):
        """测试各种概率计算函数"""
        # 创建简单的比分矩阵
        matrix = np.array(
            [
                [0.1, 0.05, 0.02],  # 0-0, 0-1, 0-2
                [0.15, 0.1, 0.03],  # 1-0, 1-1, 1-2
                [0.08, 0.04, 0.01],  # 2-0, 2-1, 2-2
            ]
        )
        calculator.max_goals_calc = 2

        # 主胜概率 (1-0, 2-0, 2-1)
        home_win = calculator._calculate_home_win_probability(matrix)
        expected_home_win = 0.15 + 0.08 + 0.04
        assert abs(home_win - expected_home_win) < 0.001

        # 平局概率 (0-0, 1-1, 2-2)
        draw = calculator._calculate_draw_probability(matrix)
        expected_draw = 0.1 + 0.1 + 0.01
        assert abs(draw - expected_draw) < 0.001

        # 大小球概率
        over_2_5 = calculator._calculate_over_probability(matrix, 2.5)
        expected_over_2_5 = 0.08  # 实际计算值调整
        assert abs(over_2_5 - expected_over_2_5) < 0.001

        # 双方进球概率
        btts = calculator._calculate_btts_probability(matrix)
        expected_btts = 0.1 + 0.03 + 0.04 + 0.01  # 1-1, 1-2, 2-1, 2-2
        assert abs(btts - expected_btts) < 0.001

    def test_top_scores_extraction(self, calculator):
        """测试最可能比分提取"""
        # 创建已知概率矩阵
        matrix = np.zeros((4, 4))
        matrix[1, 0] = 0.25  # 1-0
        matrix[0, 0] = 0.20  # 0-0
        matrix[1, 1] = 0.15  # 1-1
        matrix[2, 1] = 0.10  # 2-1
        matrix[0, 1] = 0.08  # 0-1
        calculator.max_goals_calc = 3

        top_scores = calculator._get_top_probable_scores(matrix, 3)

        assert len(top_scores) == 3
        assert top_scores[0]["score"] == "1-0"
        assert top_scores[0]["probability"] == 0.25
        assert top_scores[1]["score"] == "0-0"
        assert top_scores[1]["probability"] == 0.20
        assert top_scores[2]["score"] == "1-1"
        assert top_scores[2]["probability"] == 0.15

    # ========== 特征工程测试 ==========

    def test_model_features_extraction(self, calculator):
        """测试模型特征提取"""
        matrix = calculator._calculate_score_matrix(1.8, 1.3)
        features = calculator._extract_model_features(1.8, 1.3, matrix)

        # 基础预期特征
        assert features["expected_home_goals"] == 1.8
        assert features["expected_away_goals"] == 1.3
        assert features["expected_total_goals"] == 3.1
        assert features["expected_goal_difference"] == 0.5

        # 概率特征
        assert "home_win_poisson_prob" in features
        assert "draw_poisson_prob" in features
        assert "over_2_5_poisson_prob" in features
        assert "btts_poisson_prob" in features

        # 高阶特征
        assert features["poisson_variance_home"] == 1.8  # 泊松方差=λ
        assert features["poisson_variance_away"] == 1.3
        assert features["poisson_skewness_home"] > 0
        assert features["poisson_skewness_away"] > 0

        # 最可能比分特征
        assert "most_likely_home_goals" in features
        assert "most_likely_away_goals" in features
        assert "most_likely_score_prob" in features

    def test_confidence_metrics_calculation(self, calculator):
        """测试置信度指标计算"""
        # 设置有充足数据的球队
        calculator.team_data["confident_team"] = {
            "matches_analyzed": 20,  # 足够的数据
            "attack_lambda": 1.6,
            "defense_lambda": 1.1,
        }
        calculator.team_data["limited_team"] = {
            "matches_analyzed": 3,  # 数据不足
            "attack_lambda": 1.2,
            "defense_lambda": 1.4,
        }

        # 测试数据充足的球队
        metrics_confident = calculator._calculate_confidence_metrics("confident_team", "confident_team", 1.5, 1.3)
        assert metrics_confident["data_sufficiency_confidence"] >= 1.0
        assert metrics_confident["stability_confidence"] >= 0
        assert metrics_confident["overall_confidence"] >= 0.5

        # 测试数据不足的球队
        metrics_limited = calculator._calculate_confidence_metrics("limited_team", "limited_team", 1.5, 1.3)
        assert metrics_limited["data_sufficiency_confidence"] <= 1.0
        assert metrics_limited["overall_confidence"] < metrics_confident["overall_confidence"]

    def test_matrix_entropy_calculation(self, calculator):
        """测试矩阵熵计算"""
        # 创建确定性高的矩阵（集中分布）
        concentrated_matrix = np.zeros((3, 3))
        concentrated_matrix[1, 1] = 0.9
        concentrated_matrix[0, 0] = 0.1

        entropy_concentrated = calculator._calculate_matrix_entropy(concentrated_matrix)

        # 创建分散的矩阵（均匀分布）
        uniform_matrix = np.ones((3, 3)) / 9
        entropy_uniform = calculator._calculate_matrix_entropy(uniform_matrix)

        # 均匀分布的熵应该更高
        assert entropy_uniform > entropy_concentrated
        assert entropy_concentrated >= 0
        assert entropy_uniform >= 0

    # ========== 边界条件和异常处理测试 ==========

    @pytest.mark.parametrize(
        "home_lambda,away_lambda",
        [
            (0.1, 0.1),  # 极低λ值
            (5.0, 5.0),  # 极高λ值
            (0.5, 2.5),  # 不对称λ值
            (2.7, 2.7),  # 联赛平均值
        ],
    )
    def test_extreme_lambda_values(self, calculator, home_lambda, away_lambda):
        """测试极端λ值处理"""
        result = calculator.calculate_match_probabilities(
            home_team_id="extreme_home",
            away_team_id="extreme_away",
            home_attack_lambda=home_lambda,
            home_defense_lambda=home_lambda,
            away_attack_lambda=away_lambda,
            away_defense_lambda=away_lambda,
        )

        expected = result["expected_goals"]
        assert 0.1 <= expected["home"] <= 6.0
        assert 0.1 <= expected["away"] <= 6.0

        probs = result["probabilities"]
        assert all(0 <= p <= 1 for p in probs.values())
        assert abs(sum([probs["home_win"], probs["draw"], probs["away_win"]]) - 1.0) < 0.001

    def test_zero_goals_scenario(self, calculator):
        """测试零进球场景"""
        result = calculator.calculate_match_probabilities(
            home_team_id="zero_home",
            away_team_id="zero_away",
            home_attack_lambda=0.01,
            home_defense_lambda=0.01,
            away_attack_lambda=0.01,
            away_defense_lambda=0.01,
        )

        expected = result["expected_goals"]
        probs = result["probabilities"]

        # 预期进球应该接近0
        assert expected["home"] <= 0.1
        assert expected["away"] <= 0.1

        # 0-0比分概率应该很高
        top_scores = result["top_scores"]
        zero_zero_score = next((s for s in top_scores if s["score"] == "0-0"), None)
        assert zero_zero_score is not None
        assert zero_zero_score["probability"] > 0.5

    def test_high_scoring_scenario(self, calculator):
        """测试高进球场景"""
        result = calculator.calculate_match_probabilities(
            home_team_id="high_home",
            away_team_id="high_away",
            home_attack_lambda=4.0,
            home_defense_lambda=2.0,
            away_attack_lambda=3.5,
            away_defense_lambda=2.5,
        )

        expected = result["expected_goals"]
        probs = result["probabilities"]

        # 预期进球应该较高
        assert expected["total"] > 3.0

        # 大球概率应该很高
        assert probs["over_2_5"] > 0.7
        assert probs["over_3_5"] > 0.5

    def test_invalid_input_handling(self, calculator):
        """测试无效输入处理"""
        # 测试空比赛数据 - 现在返回默认值而不是异常
        result = calculator.calculate_team_lambdas(team_id="empty_team", matches_data=[], is_home_team=True)
        # 验证返回合理的默认值 (tuple格式: attack_lambda, defense_lambda, metadata)
        attack_lambda, defense_lambda, metadata = result
        assert attack_lambda > 0
        assert defense_lambda > 0
        assert metadata["status"] == "insufficient_data"

        # 测试负数进球
        invalid_data = [
            {
                "match_date": datetime.now(),
                "home_goals": -1,
                "away_goals": 2,
                "team_is_home": True,
            }
        ]

        # 应该能够处理但给出合理的默认值
        attack_lambda, defense_lambda, details = calculator.calculate_team_lambdas(
            team_id="invalid_team", matches_data=invalid_data, is_home_team=True
        )

        assert attack_lambda >= 0
        assert defense_lambda >= 0

    def test_date_string_parsing(self, calculator):
        """测试日期字符串解析"""
        date_string_data = [
            {
                "match_date": "2024-01-15T15:00:00",
                "home_goals": 2,
                "away_goals": 1,
                "team_is_home": True,
            }
        ]

        attack_lambda, defense_lambda, details = calculator.calculate_team_lambdas(
            team_id="date_string_team", matches_data=date_string_data, is_home_team=True
        )

        assert (
            details["status"] == "success"
            if len(date_string_data) >= calculator.MIN_GAMES_FOR_LAMBDA
            else "insufficient_data"
        )

    # ========== 批量处理测试 ==========

    def test_generate_features_for_dataset(self, calculator):
        """测试数据集批量特征生成"""
        # 创建测试数据集
        matches_df = pd.DataFrame(
            [
                {
                    "match_id": 1,
                    "home_team_id": "team_a",
                    "away_team_id": "team_b",
                    "match_date": datetime.now() - timedelta(days=1),
                },
                {
                    "match_id": 2,
                    "home_team_id": "team_c",
                    "away_team_id": "team_d",
                    "match_date": datetime.now() - timedelta(days=2),
                },
            ]
        )

        # 设置球队数据
        calculator.team_data.update(
            {
                "team_a": {"attack_lambda": 1.8, "defense_lambda": 0.9},
                "team_b": {"attack_lambda": 1.3, "defense_lambda": 1.4},
                "team_c": {"attack_lambda": 1.5, "defense_lambda": 1.1},
                "team_d": {"attack_lambda": 1.2, "defense_lambda": 1.6},
            }
        )

        features_df = calculator.generate_features_for_dataset(matches_df)

        assert len(features_df) == 2
        assert "expected_home_goals" in features_df.columns
        assert "expected_away_goals" in features_df.columns
        assert "home_win_poisson_prob" in features_df.columns
        assert "match_id" in features_df.columns

    def test_generate_features_with_missing_data(self, calculator):
        """测试数据缺失时的批量特征生成"""
        # 创建包含未知球队的数据集
        matches_df = pd.DataFrame(
            [
                {
                    "match_id": 1,
                    "home_team_id": "unknown_team_a",
                    "away_team_id": "unknown_team_b",
                    "match_date": datetime.now(),
                },
            ]
        )

        features_df = calculator.generate_features_for_dataset(matches_df)

        # 应该使用默认值生成特征
        assert len(features_df) == 1
        assert "expected_home_goals" in features_df.columns

    # ========== 统计和报告测试 ==========

    def test_team_stats_retrieval(self, calculator, sample_matches_data):
        """测试球队统计信息获取"""
        # 先计算球队λ值
        calculator.calculate_team_lambdas(team_id="stats_team", matches_data=sample_matches_data, is_home_team=True)

        stats = calculator.get_team_stats("stats_team")

        assert "team_id" in stats
        assert "current_lambdas" in stats
        assert "performance_stats" in stats
        assert "data_quality" in stats

        assert stats["team_id"] == "stats_team"
        assert stats["data_quality"]["matches_analyzed"] == len(sample_matches_data)

    def test_team_stats_nonexistent_team(self, calculator):
        """测试不存在球队的统计信息"""
        stats = calculator.get_team_stats("nonexistent_team")

        assert "error" in stats
        assert "nonexistent_team" in stats["error"]

    def test_system_stats_retrieval(self, calculator):
        """测试系统统计信息获取"""
        # 添加一些球队数据
        calculator.team_data["team1"] = {"attack_lambda": 1.5, "defense_lambda": 1.2}
        calculator.team_data["team2"] = {"attack_lambda": 1.8, "defense_lambda": 0.9}

        # 执行一些计算
        calculator.calculate_match_probabilities("team1", "team2")

        stats = calculator.get_system_stats()

        assert "configuration" in stats
        assert "statistics" in stats
        assert "team_data_count" in stats
        assert "average_lambdas" in stats

        assert stats["team_data_count"] == 2
        assert stats["statistics"]["total_calculations"] > 0

    def test_calculation_statistics_update(self, calculator):
        """测试计算统计信息更新"""
        initial_stats = calculator.stats.copy()

        # 执行多次计算
        for i in range(5):
            calculator.calculate_match_probabilities(
                f"team_{i}",
                f"team_{i+1}",
                home_attack_lambda=1.5 + i * 0.1,
                away_attack_lambda=1.2 + i * 0.1,
            )

        updated_stats = calculator.stats

        assert updated_stats["total_calculations"] == initial_stats["total_calculations"] + 5
        assert updated_stats["avg_lambda_home"] != initial_stats["avg_lambda_home"]
        assert updated_stats["avg_lambda_away"] != initial_stats["avg_lambda_away"]
        assert updated_stats["last_updated"] is not None

    # ========== 性能测试 ==========

    def test_performance_single_calculation(self, calculator):
        """测试单次计算性能"""
        import time

        start_time = time.time()
        result = calculator.calculate_match_probabilities(
            "perf_home",
            "perf_away",
            home_attack_lambda=1.7,
            home_defense_lambda=1.1,
            away_attack_lambda=1.4,
            away_defense_lambda=1.5,
        )
        end_time = time.time()

        calculation_time = end_time - start_time
        assert calculation_time < 0.1  # 应该在100ms内完成
        assert result is not None

    def test_performance_batch_calculation(self, calculator):
        """测试批量计算性能"""
        import time

        # 准备批量计算
        teams = [f"team_{i}" for i in range(20)]

        start_time = time.time()
        results = []
        for i, home_team in enumerate(teams):
            for away_team in teams[i + 1 :]:
                result = calculator.calculate_match_probabilities(
                    home_team, away_team, home_attack_lambda=1.5, away_attack_lambda=1.3
                )
                results.append(result)

        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / len(results)

        assert len(results) == 190  # 20C2 = 190
        assert avg_time < 0.05  # 平均每次计算应该很快

    @pytest.mark.parametrize("max_goals", [5, 8, 10, 15])
    def test_performance_matrix_size_impact(self, max_goals):
        """测试矩阵大小对性能的影响"""
        calc = PoissonFeatureCalculator(max_goals_calc=max_goals)

        import time

        start_time = time.time()

        matrix = calc._calculate_score_matrix(2.0, 1.5)

        end_time = time.time()
        calc_time = end_time - start_time

        assert matrix.shape == (max_goals + 1, max_goals + 1)
        assert calc_time < 0.05  # 即使是较大矩阵也应该很快

    # ========== 数值精度测试 ==========

    def test_probability_distribution_sum(self, calculator):
        """测试概率分布总和为1"""
        result = calculator.calculate_match_probabilities(
            "precision_home",
            "precision_away",
            home_attack_lambda=1.8,
            away_attack_lambda=1.4,
        )

        probs = result["probabilities"]
        total_prob = probs["home_win"] + probs["draw"] + probs["away_win"]

        assert abs(total_prob - 1.0) < 1e-10  # 极高精度要求

    def test_poisson_distribution_properties(self, calculator):
        """测试泊松分布数学性质"""
        lambda_val = 2.5

        # 计算进球数分布
        distribution = calculator._calculate_goals_distribution(lambda_val)

        # 验证概率和为1
        total_prob = sum(distribution.values())
        assert abs(total_prob - 1.0) < 0.01

        # 验证期望值等于λ
        expected_value = sum(goals * prob for goals, prob in distribution.items())
        assert abs(expected_value - lambda_val) < 0.1

        # 验证方差等于λ
        variance = sum((goals - lambda_val) ** 2 * prob for goals, prob in distribution.items())
        assert abs(variance - lambda_val) < 0.2

    # ========== 辅助方法测试 ==========

    def test_repr_method(self, calculator):
        """测试字符串表示方法"""
        calculator.team_data["team1"] = {"attack_lambda": 1.5}
        calculator.stats["total_calculations"] = 5

        repr_str = repr(calculator)

        assert "PoissonFeatureCalculator" in repr_str
        assert "teams=1" in repr_str
        assert "calculations=5" in repr_str
        assert "avg_home_λ" in repr_str
        assert "avg_away_λ" in repr_str

    # ========== 集成测试 ==========

    def test_full_workflow_integration(self, calculator, sample_matches_data):
        """测试完整工作流程集成"""
        # 1. 计算球队λ值
        home_attack, home_defense, _ = calculator.calculate_team_lambdas(
            "workflow_home", sample_matches_data, is_home_team=True
        )
        away_attack, away_defense, _ = calculator.calculate_team_lambdas(
            "workflow_away", sample_matches_data, is_home_team=False
        )

        # 2. 计算比赛概率
        match_result = calculator.calculate_match_probabilities(
            "workflow_home",
            "workflow_away",
            home_attack_lambda=home_attack,
            home_defense_lambda=home_defense,
            away_attack_lambda=away_attack,
            away_defense_lambda=away_defense,
        )

        # 3. 获取球队统计
        home_stats = calculator.get_team_stats("workflow_home")
        away_stats = calculator.get_team_stats("workflow_away")

        # 4. 获取系统统计
        system_stats = calculator.get_system_stats()

        # 验证工作流程完整性
        assert match_result is not None
        assert "expected_goals" in match_result
        assert "probabilities" in match_result
        assert home_stats["team_id"] == "workflow_home"
        assert away_stats["team_id"] == "workflow_away"
        assert system_stats["team_data_count"] >= 2
        assert system_stats["statistics"]["total_calculations"] > 0


class TestPoissonFeatureCalculatorEdgeCases:
    """泊松特征计算器边界条件测试"""

    @pytest.fixture
    def minimal_calculator(self):
        """创建最小配置计算器"""
        return PoissonFeatureCalculator(
            home_lambda_default=0.5,
            away_lambda_default=0.3,
            league_avg_goals=1.0,
            max_goals_calc=3,
        )

    def test_minimal_configuration(self, minimal_calculator):
        """测试最小配置下的计算"""
        result = minimal_calculator.calculate_match_probabilities("min_home", "min_away")

        assert result is not None
        assert result["expected_goals"]["total"] > 0

    def test_maximal_configuration(self):
        """测试最大配置下的计算"""
        maximal_calc = PoissonFeatureCalculator(
            home_lambda_default=5.0,
            away_lambda_default=4.0,
            league_avg_goals=5.0,
            max_goals_calc=20,
        )

        result = maximal_calc.calculate_match_probabilities("max_home", "max_away")

        assert result is not None
        assert len(result["top_scores"]) == 5  # 默认Top 5
        assert len(result["goals_distribution"]["home"]) == 21  # 0-20进球
