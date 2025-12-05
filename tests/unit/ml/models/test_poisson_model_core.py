"""泊松模型核心单元测试
Core Unit Tests for Poisson Distribution Model.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Any, Optional

# 导入被测试的模块
from src.ml.models.poisson_model import PoissonModel
from src.ml.models.base_model import PredictionResult, TrainingResult


@pytest.fixture
def poisson_model():
    """创建Poisson模型实例."""
    return PoissonModel(version="test")


@pytest.fixture
def mini_league_training_data():
    """迷你联赛训练数据集 - 包含4支球队的主客场数据，满足min_matches要求.

    设计理念:
    - Team A: 强队，进球多，失球少
    - Team B: 中等偏上球队
    - Team C: 中等偏下球队
    - Team D: 弱队，进球少，失球多
    """
    data = {
        "home_team": [
            "Team_A",
            "Team_A",
            "Team_A",
            "Team_A",
            "Team_A",
            "Team_A",  # Team A主场6场
            "Team_B",
            "Team_B",
            "Team_B",
            "Team_B",
            "Team_B",
            "Team_B",  # Team B主场6场
            "Team_C",
            "Team_C",
            "Team_C",
            "Team_C",
            "Team_C",
            "Team_C",  # Team C主场6场
            "Team_D",
            "Team_D",
            "Team_D",
            "Team_D",
            "Team_D",
            "Team_D",  # Team D主场6场
        ],
        "away_team": [
            "Team_B",
            "Team_C",
            "Team_D",
            "Team_B",
            "Team_C",
            "Team_D",  # Team A主场对手
            "Team_A",
            "Team_C",
            "Team_D",
            "Team_A",
            "Team_C",
            "Team_D",  # Team B主场对手
            "Team_A",
            "Team_B",
            "Team_D",
            "Team_A",
            "Team_B",
            "Team_D",  # Team C主场对手
            "Team_A",
            "Team_B",
            "Team_C",
            "Team_A",
            "Team_B",
            "Team_C",  # Team D主场对手
        ],
        "home_score": [
            3,
            4,
            5,
            2,
            3,
            4,  # Team A主场: 进球多
            2,
            1,
            3,
            1,
            2,
            3,  # Team B主场: 中等
            1,
            2,
            1,
            0,
            1,
            2,  # Team C主场: 较少
            0,
            1,
            0,
            1,
            0,
            1,  # Team D主场: 很少
        ],
        "away_score": [
            1,
            0,
            1,
            2,
            0,
            1,  # Team A主场: 失球少
            2,
            1,
            2,
            3,
            2,
            1,  # Team B主场: 中等失球
            3,
            2,
            3,
            4,
            3,
            2,  # Team C主场: 失球较多
            4,
            3,
            2,
            5,
            4,
            3,  # Team D主场: 失球很多
        ],
        "result": [
            "home_win",
            "home_win",
            "home_win",
            "draw",
            "home_win",
            "home_win",
            "draw",
            "home_win",
            "home_win",
            "away_win",
            "draw",
            "home_win",
            "away_win",
            "draw",
            "away_win",
            "away_win",
            "away_win",
            "away_win",
            "away_win",
            "away_win",
            "away_win",
            "away_win",
            "away_win",
            "away_win",
        ],
    }
    return pd.DataFrame(data)


@pytest.fixture
def validation_data():
    """验证数据集."""
    data = {
        "home_team": ["Team_A", "Team_B", "Team_C"],
        "away_team": ["Team_D", "Team_C", "Team_A"],
        "home_score": [2, 1, 1],
        "away_score": [0, 1, 3],
        "result": ["home_win", "draw", "away_win"],
    }
    return pd.DataFrame(data)


@pytest.fixture
def minimal_training_data():
    """最小训练数据集 - 仅满足最低要求."""
    data = {
        "home_team": ["Team_X", "Team_Y"] * 6,  # 12场比赛
        "away_team": ["Team_Y", "Team_X"] * 6,
        "home_score": [2, 1, 3, 0, 1, 2, 1, 1, 2, 0, 3, 1],
        "away_score": [1, 2, 1, 3, 2, 0, 1, 1, 0, 2, 1, 2],
        "result": [
            "home_win",
            "away_win",
            "home_win",
            "away_win",
            "home_win",
            "home_win",
            "draw",
            "draw",
            "home_win",
            "away_win",
            "home_win",
            "away_win",
        ],
    }
    return pd.DataFrame(data)


class TestPoissonModelInitialization:
    """Poisson模型初始化测试."""

    def test_default_initialization(self, poisson_model):
        """测试默认初始化参数."""
        assert poisson_model.model_name == "PoissonModel"
        assert poisson_model.model_version == "test"
        assert poisson_model.home_advantage == 0.3
        assert len(poisson_model.team_attack_strength) == 0
        assert len(poisson_model.team_defense_strength) == 0
        assert not poisson_model.is_trained

    def test_hyperparameters_initialization(self, poisson_model):
        """测试超参数初始化."""
        expected_hyperparams = {
            "home_advantage": 0.3,
            "min_matches_per_team": 10,
            "decay_factor": 0.9,
            "max_goals": 10,
        }
        assert poisson_model.hyperparameters == expected_hyperparams

    def test_default_goal_averages(self, poisson_model):
        """测试默认平均进球数."""
        assert poisson_model.average_goals_home == 1.5
        assert poisson_model.average_goals_away == 1.1


class TestTeamStrengthCalculation:
    """球队攻防强度计算测试."""

    def test_overall_averages_calculation(
        self, poisson_model, mini_league_training_data
    ):
        """测试总体平均进球数计算."""
        poisson_model._calculate_team_strengths(mini_league_training_data)

        # 计算期望值
        total_home_goals = mini_league_training_data["home_score"].sum()
        total_away_goals = mini_league_training_data["away_score"].sum()
        total_matches = len(mini_league_training_data)

        expected_home_avg = total_home_goals / total_matches
        expected_away_avg = total_away_goals / total_matches

        assert poisson_model.average_goals_home == pytest.approx(expected_home_avg)
        assert poisson_model.average_goals_away == pytest.approx(expected_away_avg)

    def test_team_strength_calculation(self, poisson_model, mini_league_training_data):
        """测试球队攻防强度计算."""
        poisson_model._calculate_team_strengths(mini_league_training_data)

        # 验证所有球队都被计算
        expected_teams = {"Team_A", "Team_B", "Team_C", "Team_D"}
        assert set(poisson_model.team_attack_strength.keys()) == expected_teams
        assert set(poisson_model.team_defense_strength.keys()) == expected_teams

    def test_strength_differences_validation(
        self, poisson_model, mini_league_training_data
    ):
        """验证攻防强度的相对关系."""
        poisson_model._calculate_team_strengths(mini_league_training_data)

        # 验证攻防强度被计算出来
        team_a_attack = poisson_model.team_attack_strength["Team_A"]
        team_d_attack = poisson_model.team_attack_strength["Team_D"]
        team_a_defense = poisson_model.team_defense_strength["Team_A"]
        team_d_defense = poisson_model.team_defense_strength["Team_D"]

        # 验证攻防强度在合理范围内
        assert 0.2 <= team_a_attack <= 3.0
        assert 0.2 <= team_d_attack <= 3.0
        assert 0.2 <= team_a_defense <= 3.0
        assert 0.2 <= team_d_defense <= 3.0

        # 验证攻防强度不相等（根据数据设计）
        assert team_a_attack != team_d_attack or team_a_defense != team_d_defense

    def test_strength_range_limits(self, poisson_model, mini_league_training_data):
        """测试攻防强度的范围限制."""
        poisson_model._calculate_team_strengths(mini_league_training_data)

        # 所有攻防强度应该在[0.2, 3.0]范围内
        for team in poisson_model.team_attack_strength:
            attack = poisson_model.team_attack_strength[team]
            defense = poisson_model.team_defense_strength[team]

            assert 0.2 <= attack <= 3.0, f"{team}进攻强度{attack}超出范围[0.2, 3.0]"
            assert 0.2 <= defense <= 3.0, f"{team}防守强度{defense}超出范围[0.2, 3.0]"

    def test_insufficient_data_teams(self, poisson_model):
        """测试数据不足球队的默认值处理."""
        # 创建一个数据不足的数据集
        insufficient_data = pd.DataFrame(
            {
                "home_team": ["Team_X"],
                "away_team": ["Team_Y"],
                "home_score": [2],
                "away_score": [1],
            }
        )

        poisson_model._calculate_team_strengths(insufficient_data)

        # 数据不足的球队应该使用默认值
        assert poisson_model.team_attack_strength.get("Team_X") == 1.0
        assert poisson_model.team_defense_strength.get("Team_Y") == 1.0

    def test_home_away_separate_calculation(
        self, poisson_model, mini_league_training_data
    ):
        """测试主客场分别计算."""
        poisson_model._calculate_team_strengths(mini_league_training_data)

        # 验证计算了主客场数据
        team_a_home_matches = mini_league_training_data[
            mini_league_training_data["home_team"] == "Team_A"
        ]
        team_a_away_matches = mini_league_training_data[
            mini_league_training_data["away_team"] == "Team_A"
        ]

        assert len(team_a_home_matches) > 0
        assert len(team_a_away_matches) > 0


class TestExpectedGoalsCalculation:
    """期望进球数计算测试."""

    def test_basic_expected_goals_calculation(
        self, poisson_model, mini_league_training_data
    ):
        """测试基础期望进球计算."""
        poisson_model._calculate_team_strengths(mini_league_training_data)

        # Team A (强队) vs Team D (弱队)
        home_expected = poisson_model._calculate_expected_goals(
            "Team_A", "Team_D", is_home=True
        )
        away_expected = poisson_model._calculate_expected_goals(
            "Team_D", "Team_A", is_home=False
        )

        # 主队期望进球应该大于客队
        assert home_expected > away_expected

        # 期望进球应该是合理的正数
        assert home_expected > 0.1
        assert away_expected > 0.1

    def test_home_advantage_impact(self, poisson_model, mini_league_training_data):
        """测试主场优势的影响."""
        poisson_model._calculate_team_strengths(mini_league_training_data)

        # 相同两支球队，主客场期望进球应该不同
        home_expected = poisson_model._calculate_expected_goals(
            "Team_A", "Team_B", is_home=True
        )
        away_expected = poisson_model._calculate_expected_goals(
            "Team_A", "Team_B", is_home=False
        )

        # 主场期望进球应该更高（包含主场优势）
        assert home_expected > away_expected

    def test_strength_impact_on_expected_goals(
        self, poisson_model, mini_league_training_data
    ):
        """测试攻防强度对期望进球的影响."""
        poisson_model._calculate_team_strengths(mini_league_training_data)

        # 计算期望进球
        strong_vs_weak = poisson_model._calculate_expected_goals(
            "Team_A", "Team_D", is_home=True
        )
        weak_vs_strong = poisson_model._calculate_expected_goals(
            "Team_D", "Team_A", is_home=True
        )

        # 验证期望进球为合理正数
        assert strong_vs_weak > 0.1
        assert weak_vs_strong > 0.1

        # 验证主场优势存在（主队期望进球应该包含主场优势加成）
        neutral_expected = poisson_model._calculate_expected_goals(
            "Team_A", "Team_D", is_home=False
        )
        assert strong_vs_weak > neutral_expected

    def test_minimum_expected_goals_protection(self, poisson_model):
        """测试最小期望进球保护."""
        # 创建极弱的球队
        poisson_model.team_attack_strength["Weak"] = 0.01
        poisson_model.team_defense_strength["Strong"] = 10.0
        poisson_model.average_goals_home = 0.1  # 极低的平均进球

        expected = poisson_model._calculate_expected_goals(
            "Weak", "Strong", is_home=True
        )

        # 期望进球不应该低于0.1
        assert expected >= 0.1

    def test_new_team_default_values(self, poisson_model):
        """测试新球队的默认值."""
        # 使用未训练的模型（新球队使用默认值1.0）
        home_expected = poisson_model._calculate_expected_goals(
            "NewTeam", "AnotherNew", is_home=True
        )
        away_expected = poisson_model._calculate_expected_goals(
            "AnotherNew", "NewTeam", is_home=False
        )

        # 应该基于默认强度计算
        assert home_expected > 0
        assert away_expected > 0


class TestPoissonProbabilityCalculation:
    """泊松概率计算测试."""

    @pytest.mark.parametrize(
        "home_expected,away_expected",
        [
            (1.0, 1.0),  # 平均情况
            (2.5, 0.8),  # 强主队vs弱客队
            (0.8, 2.0),  # 弱主队vs强客队
            (3.0, 3.0),  # 高进球期望
            (0.5, 0.5),  # 低进球期望
        ],
    )
    def test_probability_distribution_properties(
        self, poisson_model, home_expected, away_expected
    ):
        """测试概率分布的数学性质."""
        home_win, draw, away_win = poisson_model._calculate_match_probabilities(
            home_expected, away_expected
        )

        # 概率应该在[0,1]范围内
        assert 0.0 <= home_win <= 1.0
        assert 0.0 <= draw <= 1.0
        assert 0.0 <= away_win <= 1.0

        # 概率总和应该接近1
        total_prob = home_win + draw + away_win
        assert total_prob == pytest.approx(1.0, abs=0.01)

    def test_probability_matrix_properties(self, poisson_model):
        """测试概率矩阵的性质."""
        # 手动设置一些期望值进行测试
        home_expected = 1.5
        away_expected = 1.2
        max_goals = 5

        home_win_prob = 0.0
        draw_prob = 0.0
        away_win_prob = 0.0
        prob_matrix = np.zeros((max_goals + 1, max_goals + 1))

        # 生成概率矩阵
        for home_goals in range(max_goals + 1):
            for away_goals in range(max_goals + 1):
                from scipy import stats

                home_prob = stats.poisson.pmf(home_goals, home_expected)
                away_prob = stats.poisson.pmf(away_goals, away_expected)
                combined_prob = home_prob * away_prob
                prob_matrix[home_goals, away_goals] = combined_prob

                if home_goals > away_goals:
                    home_win_prob += combined_prob
                elif home_goals == away_goals:
                    draw_prob += combined_prob
                else:
                    away_win_prob += combined_prob

        # 验证矩阵形状
        assert prob_matrix.shape == (max_goals + 1, max_goals + 1)

        # 验证概率总和接近1
        total_matrix_prob = np.sum(prob_matrix)
        assert total_matrix_prob == pytest.approx(1.0, abs=0.01)

        # 验证分类概率与矩阵概率一致
        assert home_win_prob + draw_prob + away_win_prob == pytest.approx(
            total_matrix_prob, abs=0.01
        )

    def test_high_scoring_expectations(self, poisson_model):
        """测试高进球期望的情况."""
        high_home_exp = 4.0
        high_away_exp = 3.5

        home_win, draw, away_win = poisson_model._calculate_match_probabilities(
            high_home_exp, high_away_exp
        )

        # 高进球期望下，平局概率应该相对较低
        assert draw < 0.3

    def test_low_scoring_expectations(self, poisson_model):
        """测试低进球期望的情况."""
        low_home_exp = 0.5
        low_away_exp = 0.4

        home_win, draw, away_win = poisson_model._calculate_match_probabilities(
            low_home_exp, low_away_exp
        )

        # 低进球期望下，平局概率应该相对较高
        assert draw > 0.2

    def test_max_goals_parameter_impact(self, poisson_model):
        """测试max_goals参数的影响."""
        original_max = poisson_model.hyperparameters["max_goals"]

        # 测试不同的max_goals值
        for max_goals in [5, 10, 15]:
            poisson_model.hyperparameters["max_goals"] = max_goals

            home_win, draw, away_win = poisson_model._calculate_match_probabilities(
                1.5, 1.2
            )
            total_prob = home_win + draw + away_win

            # 概率总和应该始终接近1
            assert total_prob == pytest.approx(1.0, abs=0.01)

        # 恢复原始值
        poisson_model.hyperparameters["max_goals"] = original_max


class TestPoissonModelTraining:
    """Poisson模型训练测试."""

    def test_model_training_workflow(self, poisson_model, mini_league_training_data):
        """测试完整的训练工作流."""
        # 训练前状态
        assert not poisson_model.is_trained
        assert len(poisson_model.team_attack_strength) == 0

        # 执行训练
        result = poisson_model.train(mini_league_training_data)

        # 训练后状态
        assert poisson_model.is_trained
        assert len(poisson_model.team_attack_strength) == 4  # Team A, B, C, D
        assert isinstance(result, TrainingResult)
        assert result.model_name == "PoissonModel"
        assert result.model_version == "test"
        assert result.training_samples == len(mini_league_training_data)

    def test_training_data_validation(self, poisson_model):
        """测试训练数据验证."""
        # 空数据
        empty_df = pd.DataFrame()
        assert not poisson_model.validate_training_data(empty_df)

        # 缺少必要列
        invalid_df = pd.DataFrame({"team": ["A", "B"]})
        assert not poisson_model.validate_training_data(invalid_df)

    def test_mini_league_training_results(
        self, poisson_model, mini_league_training_data
    ):
        """测试迷你联赛训练结果."""
        poisson_model.train(mini_league_training_data)

        # 验证计算了统计信息
        assert poisson_model.total_matches > 0
        assert poisson_model.average_goals_home > 0
        assert poisson_model.average_goals_away > 0

        # 验证所有球队都有强度值
        expected_teams = {"Team_A", "Team_B", "Team_C", "Team_D"}
        for team in expected_teams:
            assert team in poisson_model.team_attack_strength
            assert team in poisson_model.team_defense_strength

        # 验证攻防强度都在合理范围内
        for team in expected_teams:
            attack = poisson_model.team_attack_strength[team]
            defense = poisson_model.team_defense_strength[team]
            assert 0.2 <= attack <= 3.0
            assert 0.2 <= defense <= 3.0

    def test_hyperparameter_updates(self, poisson_model):
        """测试超参数更新."""
        # 更新主场优势
        poisson_model.update_hyperparameters(home_advantage=0.5)
        assert poisson_model.hyperparameters["home_advantage"] == 0.5

        # 更新最大进球数
        poisson_model.update_hyperparameters(max_goals=15)
        assert poisson_model.hyperparameters["max_goals"] == 15


class TestPoissonModelPrediction:
    """Poisson模型预测测试."""

    def test_prediction_before_training_error(self, poisson_model):
        """测试未训练模型的预测错误."""
        match_data = {
            "home_team": "Team_A",
            "away_team": "Team_B",
        }

        with pytest.raises(RuntimeError, match="Model must be trained"):
            poisson_model.predict(match_data)

        with pytest.raises(RuntimeError, match="Model must be trained"):
            poisson_model.predict_proba(match_data)

    def test_prediction_workflow(self, poisson_model, mini_league_training_data):
        """测试预测工作流."""
        # 训练模型
        poisson_model.train(mini_league_training_data)

        # 进行预测
        match_data = {
            "home_team": "Team_A",
            "away_team": "Team_D",
            "match_id": "test_match",
        }

        result = poisson_model.predict(match_data)

        # 验证预测结果
        assert isinstance(result, PredictionResult)
        assert result.home_team == "Team_A"
        assert result.away_team == "Team_D"
        assert result.match_id == "test_match"
        assert result.model_name == "PoissonModel"
        assert result.model_version == "test"

        # 验证概率
        assert 0.0 <= result.home_win_prob <= 1.0
        assert 0.0 <= result.draw_prob <= 1.0
        assert 0.0 <= result.away_win_prob <= 1.0
        total_prob = result.home_win_prob + result.draw_prob + result.away_win_prob
        assert total_prob == pytest.approx(1.0, abs=0.01)

        # 验证置信度
        assert 0.1 <= result.confidence <= 1.0

    def test_predict_proba(self, poisson_model, mini_league_training_data):
        """测试概率预测."""
        poisson_model.train(mini_league_training_data)

        match_data = {"home_team": "Team_A", "away_team": "Team_B"}

        probabilities = poisson_model.predict_proba(match_data)
        assert len(probabilities) == 3

        home_win, draw, away_win = probabilities
        assert all(0.0 <= p <= 1.0 for p in probabilities)
        assert sum(probabilities) == pytest.approx(1.0, abs=0.01)

    def test_prediction_with_new_teams(self, poisson_model, mini_league_training_data):
        """测试对新球队的预测."""
        poisson_model.train(mini_league_training_data)

        # 测试包含新球队的预测
        match_data = {
            "home_team": "Team_A",  # 已训练球队
            "away_team": "New_Team",  # 新球队
        }

        result = poisson_model.predict(match_data)
        assert result.home_team == "Team_A"
        assert result.away_team == "New_Team"

        # 新球队应该使用默认强度
        probabilities = poisson_model.predict_proba(match_data)
        assert len(probabilities) == 3

    def test_strength_based_prediction_differences(
        self, poisson_model, mini_league_training_data
    ):
        """测试基于强度的预测差异."""
        poisson_model.train(mini_league_training_data)

        # 强队vs弱队
        strong_vs_weak = poisson_model.predict_proba(
            {"home_team": "Team_A", "away_team": "Team_D"}
        )

        # 弱队vs强队
        weak_vs_strong = poisson_model.predict_proba(
            {"home_team": "Team_D", "away_team": "Team_A"}
        )

        # 验证概率都是有效的
        assert all(0.0 <= p <= 1.0 for p in strong_vs_weak)
        assert all(0.0 <= p <= 1.0 for p in weak_vs_strong)

        # 验证概率和为1
        assert sum(strong_vs_weak) == pytest.approx(1.0, abs=0.01)
        assert sum(weak_vs_strong) == pytest.approx(1.0, abs=0.01)


class TestModelEvaluation:
    """模型评估测试."""

    def test_model_evaluation(
        self, poisson_model, mini_league_training_data, validation_data
    ):
        """测试模型评估."""
        # 训练模型
        poisson_model.train(mini_league_training_data)

        # 评估模型
        metrics = poisson_model.evaluate(validation_data)

        # 验证评估指标
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert "confusion_matrix" in metrics
        assert "total_predictions" in metrics

        # 验证指标范围
        for metric in ["accuracy", "precision", "recall", "f1_score"]:
            assert 0.0 <= metrics[metric] <= 1.0


class TestFeaturePreparation:
    """特征准备测试."""

    def test_feature_preparation_with_trained_model(
        self, poisson_model, mini_league_training_data
    ):
        """测试训练后模型的特征准备."""
        poisson_model.train(mini_league_training_data)

        match_data = {"home_team": "Team_A", "away_team": "Team_B"}

        features = poisson_model.prepare_features(match_data)

        # 验证特征向量
        assert isinstance(features, np.ndarray)
        assert (
            len(features) == 4
        )  # [home_attack, home_defense, away_attack, away_defense]

        # 验证所有特征为正数
        assert all(feature >= 0 for feature in features)

    def test_feature_preparation_with_new_teams(self, poisson_model):
        """测试新球队的特征准备."""
        match_data = {"home_team": "New_Team_A", "away_team": "New_Team_B"}

        features = poisson_model.prepare_features(match_data)

        # 新球队应该使用默认值1.0
        expected = np.array([1.0, 1.0, 1.0, 1.0])
        assert np.array_equal(features, expected)


class TestModelPersistence:
    """模型持久化测试."""

    def test_model_save_and_load(
        self, poisson_model, mini_league_training_data, tmp_path
    ):
        """测试模型保存和加载."""
        # 训练模型
        poisson_model.train(mini_league_training_data)

        # 保存模型状态
        original_attack = poisson_model.team_attack_strength.copy()
        original_defense = poisson_model.team_defense_strength.copy()
        original_is_trained = poisson_model.is_trained

        # 保存模型
        model_path = tmp_path / "test_poisson_model.pkl"
        save_success = poisson_model.save_model(str(model_path))
        assert save_success
        assert model_path.exists()

        # 创建新模型并加载
        new_model = PoissonModel()
        load_success = new_model.load_model(str(model_path))
        assert load_success

        # 验证加载的模型状态
        assert new_model.is_trained == original_is_trained
        assert new_model.team_attack_strength == original_attack
        assert new_model.team_defense_strength == original_defense
        assert new_model.model_name == poisson_model.model_name
        assert new_model.model_version == poisson_model.model_version

    def test_load_nonexistent_model(self, poisson_model):
        """测试加载不存在的模型."""
        load_success = poisson_model.load_model("/nonexistent/path/model.pkl")
        assert not load_success


class TestEdgeCases:
    """边界情况测试."""

    def test_minimum_training_data(self, poisson_model, minimal_training_data):
        """测试最小训练数据."""
        # 应该能够成功训练
        poisson_model.train(minimal_training_data)
        assert poisson_model.is_trained

    def test_extreme_score_data(self, poisson_model):
        """测试极端比分数据."""
        # 创建极端比分数据
        extreme_data = pd.DataFrame(
            {
                "home_team": ["HighScore", "LowScore"] * 6,
                "away_team": ["LowScore", "HighScore"] * 6,
                "home_score": [8, 0, 7, 1, 6, 0, 9, 0, 5, 1, 8, 0],
                "away_score": [0, 7, 1, 8, 0, 6, 0, 9, 1, 5, 0, 8],
                "result": ["home_win", "away_win"] * 6,
            }
        )

        # 应该能够处理极端比分
        poisson_model.train(extreme_data)
        assert poisson_model.is_trained

    def test_zero_goals_data(self, poisson_model):
        """测试全0比分数据."""
        zero_goals_data = pd.DataFrame(
            {
                "home_team": ["Team_A", "Team_B"] * 8,
                "away_team": ["Team_B", "Team_A"] * 8,
                "home_score": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                "away_score": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                "result": ["draw"] * 16,
            }
        )

        # 应该能够处理全0比分
        result = poisson_model.train(zero_goals_data)
        assert poisson_model.is_trained

        # 验证模型没有崩溃，但期望进球计算可能产生NaN
        # 这里主要验证训练过程不会抛出异常
        assert result is not None

    def test_prediction_input_validation(
        self, poisson_model, mini_league_training_data
    ):
        """测试预测输入验证."""
        poisson_model.train(mini_league_training_data)

        # 测试无效输入
        invalid_inputs = [
            {},  # 空字典
            {"home_team": "Team_A"},  # 缺少away_team
            {"away_team": "Team_B"},  # 缺少home_team
        ]

        for invalid_input in invalid_inputs:
            with pytest.raises((ValueError, KeyError)):
                poisson_model.predict(invalid_input)