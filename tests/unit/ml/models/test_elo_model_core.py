"""ELO模型核心单元测试
Core Unit Tests for ELO Rating Model.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Any

# 导入被测试的模块
from src.ml.models.elo_model import EloModel
from src.ml.models.base_model import PredictionResult, TrainingResult


@pytest.fixture
def elo_model():
    """创建ELO模型实例."""
    return EloModel(version="test")


@pytest.fixture
def minimal_training_data():
    """最小化训练数据集."""
    data = {
        "date": [
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            datetime(2024, 1, 3),
            datetime(2024, 1, 4),
            datetime(2024, 1, 5),
            datetime(2024, 1, 6),
            datetime(2024, 1, 7),
            datetime(2024, 1, 8),
        ],
        "home_team": [
            "Team_A", "Team_B", "Team_A", "Team_C",
            "Team_B", "Team_C", "Team_A", "Team_B"
        ],
        "away_team": [
            "Team_B", "Team_C", "Team_C", "Team_A",
            "Team_A", "Team_B", "Team_B", "Team_C"
        ],
        "home_score": [2, 1, 3, 0, 1, 2, 1, 1],
        "away_score": [1, 1, 2, 1, 2, 0, 1, 3],
        "result": ["home_win", "draw", "home_win", "away_win",
                  "away_win", "home_win", "draw", "away_win"]
    }
    return pd.DataFrame(data)


@pytest.fixture
def validation_data():
    """验证数据集."""
    data = {
        "date": [datetime(2024, 1, 9), datetime(2024, 1, 10)],
        "home_team": ["Team_A", "Team_C"],
        "away_team": ["Team_B", "Team_A"],
        "home_score": [1, 2],
        "away_score": [0, 1],
        "result": ["home_win", "home_win"]
    }
    return pd.DataFrame(data)


class TestEloModelInitialization:
    """ELO模型初始化测试."""

    def test_default_initialization(self, elo_model):
        """测试默认初始化参数."""
        assert elo_model.model_name == "EloModel"
        assert elo_model.model_version == "test"
        assert elo_model.initial_elo == 1500.0
        assert elo_model.k_factor == 32.0
        assert elo_model.home_advantage == 100.0
        assert len(elo_model.team_elos) == 0
        assert not elo_model.is_trained

    def test_hyperparameters_initialization(self, elo_model):
        """测试超参数初始化."""
        expected_hyperparams = {
            "initial_elo": 1500.0,
            "initial_rating": 1500.0,
            "k_factor": 32.0,
            "home_advantage": 100.0,
            "min_matches_per_team": 10,
            "elo_decay_factor": 0.95,
            "max_elo_difference": 400.0,
        }
        assert elo_model.hyperparameters == expected_hyperparams


class TestExpectedScoreCalculation:
    """期望得分计算测试."""

    @pytest.mark.parametrize(
        "team_elo,opponent_elo,is_home,expected_approx",
        [
            (1500, 1500, False, 0.5),      # 同分，无主场优势
            (1500, 1500, True, 0.64),      # 同分，有主场优势
            (2000, 1000, False, 0.91),     # 强队vs弱队
            (2000, 1000, True, 0.91),      # 强队主场优势
            (1000, 2000, False, 0.09),     # 弱队vs强队
            (1000, 2000, True, 0.09),      # 弱队主场优势
            (2500, 500, False, 0.91),      # 极端差异（会被限制）
            (1400, 1600, False, 0.24),     # 接近比分
        ]
    )
    def test_calculate_expected_score(
        self, elo_model, team_elo, opponent_elo, is_home, expected_approx
    ):
        """测试期望得分计算的各种情况."""
        expected = elo_model._calculate_expected_score(team_elo, opponent_elo, is_home)
        assert expected == pytest.approx(expected_approx, abs=0.01)

    def test_max_elo_difference_limiting(self, elo_model):
        """测试ELO差异限制."""
        # 极端差异应该被限制在max_elo_difference以内
        expected_1 = elo_model._calculate_expected_score(3000, 0, False)
        expected_2 = elo_model._calculate_expected_score(2500, 500, False)
        # 由于限制，两个结果应该相同或非常接近
        assert expected_1 == pytest.approx(expected_2, abs=0.01)

    def test_legacy_calculate_expectation(self, elo_model):
        """测试兼容性方法."""
        result_1 = elo_model._calculate_expectation(1500, 1400)
        result_2 = elo_model._calculate_expected_score(1500, 1400, False)
        assert result_1 == result_2


class TestEloRatingUpdate:
    """ELO评分更新测试."""

    @pytest.mark.parametrize(
        "old_rating,opponent_rating,actual_result,expected_direction",
        [
            (1500, 1400, 1.0, "up"),      # 强队获胜，评分应该上升
            (1500, 1600, 1.0, "up"),      # 弱队获胜（冷门），评分应该大幅上升
            (1500, 1400, 0.0, "down"),    # 强队败北，评分应该下降
            (1500, 1600, 0.0, "down"),    # 弱队败北，评分应该小幅下降
            (1500, 1500, 0.5, "same"),    # 同分平局，评分应该基本不变
        ]
    )
    def test_rating_update_direction(
        self, elo_model, old_rating, opponent_rating, actual_result, expected_direction
    ):
        """测试评分更新方向."""
        new_rating = elo_model._update_rating(old_rating, opponent_rating, actual_result)

        if expected_direction == "up":
            assert new_rating > old_rating
        elif expected_direction == "down":
            assert new_rating < old_rating
        else:  # same
            assert new_rating == pytest.approx(old_rating, abs=1.0)

    def test_k_factor_impact(self, elo_model):
        """测试K因子对更新的影响."""
        elo_model.k_factor = 16.0  # 降低K因子
        new_rating_16 = elo_model._update_rating(1500, 1400, 1.0)

        elo_model.k_factor = 64.0  # 提高K因子
        new_rating_64 = elo_model._update_rating(1500, 1400, 1.0)

        # 高K因子应该产生更大的变化
        assert new_rating_64 > new_rating_16 > 1500

    def test_convert_outcome_to_score(self, elo_model):
        """测试比赛结果转换."""
        assert elo_model._convert_outcome_to_score("home_win") == 1.0
        assert elo_model._convert_outcome_to_score("away_win") == 0.0
        assert elo_model._convert_outcome_to_score("draw") == 0.5

        with pytest.raises(ValueError):
            elo_model._convert_outcome_to_score("invalid")


class TestProbabilityConversion:
    """概率转换测试."""

    @pytest.mark.parametrize(
        "home_expected,away_expected,elo_diff",
        [
            (0.7, 0.3, 200),    # 强队主场
            (0.3, 0.7, -200),   # 弱队主场
            (0.5, 0.5, 0),      # 同分
            (0.9, 0.1, 400),    # 极端差异
        ]
    )
    def test_convert_expected_scores_to_probabilities(
        self, elo_model, home_expected, away_expected, elo_diff
    ):
        """测试期望得分转换为概率."""
        home_win, draw_prob, away_win = elo_model._convert_expected_scores_to_probabilities(
            home_expected, away_expected, elo_diff
        )

        # 概率应该在合理范围内
        assert 0.0 <= home_win <= 1.0
        assert 0.0 <= draw_prob <= 1.0
        assert 0.0 <= away_win <= 1.0

        # 概率总和应该为1
        total_prob = home_win + draw_prob + away_win
        assert total_prob == pytest.approx(1.0, abs=0.01)

        # 主队期望得分高时，主胜概率应该更高
        if home_expected > away_expected:
            assert home_win > away_win

    def test_draw_probability_elo_difference_impact(self, elo_model):
        """测试ELO差异对平局概率的影响."""
        # 大ELO差异，平局概率应该较低
        _, draw_big_diff, _ = elo_model._convert_expected_scores_to_probabilities(
            0.8, 0.2, 400
        )

        # 小ELO差异，平局概率应该较高
        _, draw_small_diff, _ = elo_model._convert_expected_scores_to_probabilities(
            0.6, 0.4, 50
        )

        assert draw_small_diff > draw_big_diff

    def test_confidence_calculation(self, elo_model):
        """测试置信度计算."""
        # 明确的概率分布，高置信度
        high_conf = (0.8, 0.1, 0.1)
        confidence_high = elo_model.calculate_confidence(high_conf)

        # 均匀的概率分布，低置信度
        low_conf = (0.4, 0.2, 0.4)
        confidence_low = elo_model.calculate_confidence(low_conf)

        assert 0.1 <= confidence_high <= 1.0
        assert 0.1 <= confidence_low <= 1.0
        assert confidence_high > confidence_low


class TestEloModelTraining:
    """ELO模型训练测试."""

    def test_model_training_workflow(self, elo_model, minimal_training_data):
        """测试完整的训练工作流."""
        # 训练前状态
        assert not elo_model.is_trained
        assert len(elo_model.team_elos) == 0

        # 执行训练
        result = elo_model.train(minimal_training_data)

        # 训练后状态
        assert elo_model.is_trained
        assert len(elo_model.team_elos) == 3  # Team_A, Team_B, Team_C
        assert isinstance(result, TrainingResult)
        assert result.model_name == "EloModel"
        assert result.model_version == "test"
        assert result.training_samples == len(minimal_training_data)

    def test_team_elos_initialization(self, elo_model, minimal_training_data):
        """测试球队ELO初始化."""
        elo_model.train(minimal_training_data)

        # 所有球队应该被初始化
        expected_teams = {"Team_A", "Team_B", "Team_C"}
        assert set(elo_model.team_elos.keys()) == expected_teams

        # 初始评分应该是设置的初始值
        initial_elo = elo_model.hyperparameters["initial_elo"]
        # 由于训练过程中的更新，某些球队的评分可能不再是初始值
        for team in expected_teams:
            assert elo_model.team_elos[team] > 0
            assert elo_model.team_elos[team] < 3000  # 合理范围

    def test_elo_updates_during_training(self, elo_model, minimal_training_data):
        """测试训练过程中ELO更新."""
        # 获取第一场比赛前的初始状态
        elo_model._initialize_team_elos(minimal_training_data.iloc[[0]])
        initial_team_a = elo_model.team_elos["Team_A"]
        initial_team_b = elo_model.team_elos["Team_B"]

        # 处理第一场比赛：Team_A 2-1 Team_B (home_win)
        first_match = minimal_training_data.iloc[0]
        elo_model._update_elo_after_match(first_match)

        # Team_A获胜，ELO应该上升
        assert elo_model.team_elos["Team_A"] > initial_team_a
        # Team_B败北，ELO应该下降
        assert elo_model.team_elos["Team_B"] < initial_team_b

    def test_training_data_validation(self, elo_model):
        """测试训练数据验证."""
        # 空数据
        empty_df = pd.DataFrame()
        assert not elo_model.validate_training_data(empty_df)

        # 缺少必要列
        invalid_df = pd.DataFrame({"team": ["A", "B"]})
        assert not elo_model.validate_training_data(invalid_df)

        # 负分数据
        negative_scores = pd.DataFrame({
            "home_team": ["A"], "away_team": ["B"],
            "home_score": [-1], "away_score": [0], "result": ["home_win"]
        })
        assert not elo_model.validate_training_data(negative_scores)

    def test_hyperparameter_updates(self, elo_model):
        """测试超参数更新."""
        # 更新K因子
        elo_model.update_hyperparameters(k_factor=64.0)
        assert elo_model.k_factor == 64.0
        assert elo_model.hyperparameters["k_factor"] == 64.0

        # 更新主场优势
        elo_model.update_hyperparameters(home_advantage=150.0)
        assert elo_model.home_advantage == 150.0
        assert elo_model.hyperparameters["home_advantage"] == 150.0

    def test_model_reset(self, elo_model, minimal_training_data):
        """测试模型重置."""
        # 先训练模型
        elo_model.train(minimal_training_data)
        assert elo_model.is_trained
        assert len(elo_model.team_elos) > 0

        # 重置模型
        elo_model.reset_model()
        assert not elo_model.is_trained
        assert len(elo_model.team_elos) == 0
        assert elo_model.last_training_time is None


class TestEloModelPrediction:
    """ELO模型预测测试."""

    def test_prediction_before_training_error(self, elo_model):
        """测试未训练模型的预测错误."""
        match_data = {
            "home_team": "Team_A",
            "away_team": "Team_B",
        }

        with pytest.raises(RuntimeError, match="Model must be trained"):
            elo_model.predict(match_data)

        with pytest.raises(RuntimeError, match="Model must be trained"):
            elo_model.predict_proba(match_data)

    def test_prediction_workflow(self, elo_model, minimal_training_data):
        """测试预测工作流."""
        # 训练模型
        elo_model.train(minimal_training_data)

        # 进行预测
        match_data = {
            "home_team": "Team_A",
            "away_team": "Team_B",
            "match_id": "test_match"
        }

        result = elo_model.predict(match_data)

        # 验证预测结果
        assert isinstance(result, PredictionResult)
        assert result.home_team == "Team_A"
        assert result.away_team == "Team_B"
        assert result.match_id == "test_match"
        assert result.model_name == "EloModel"
        assert result.model_version == "test"

        # 验证概率
        assert 0.0 <= result.home_win_prob <= 1.0
        assert 0.0 <= result.draw_prob <= 1.0
        assert 0.0 <= result.away_win_prob <= 1.0
        total_prob = result.home_win_prob + result.draw_prob + result.away_win_prob
        assert total_prob == pytest.approx(1.0, abs=0.01)

        # 验证置信度
        assert 0.1 <= result.confidence <= 1.0

    def test_predict_proba(self, elo_model, minimal_training_data):
        """测试概率预测."""
        elo_model.train(minimal_training_data)

        match_data = {
            "home_team": "Team_A",
            "away_team": "Team_B"
        }

        probabilities = elo_model.predict_proba(match_data)
        assert len(probabilities) == 3

        home_win, draw, away_win = probabilities
        assert all(0.0 <= p <= 1.0 for p in probabilities)
        assert sum(probabilities) == pytest.approx(1.0, abs=0.01)

    def test_prediction_with_new_teams(self, elo_model, minimal_training_data):
        """测试对新球队的预测."""
        elo_model.train(minimal_training_data)

        # 测试包含新球队的预测
        match_data = {
            "home_team": "Team_A",  # 已训练球队
            "away_team": "New_Team"  # 新球队
        }

        result = elo_model.predict(match_data)
        assert result.home_team == "Team_A"
        assert result.away_team == "New_Team"

        # 新球队应该使用初始ELO
        new_team_elo = elo_model.get_team_elo("New_Team")
        assert new_team_elo == elo_model.initial_elo


class TestEloModelEvaluation:
    """ELO模型评估测试."""

    def test_model_evaluation(self, elo_model, minimal_training_data, validation_data):
        """测试模型评估."""
        # 训练模型
        elo_model.train(minimal_training_data)

        # 评估模型
        metrics = elo_model.evaluate(validation_data)

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

    def test_cross_validation(self, elo_model, minimal_training_data):
        """测试交叉验证."""
        metrics = elo_model._cross_validate(minimal_training_data, folds=3)

        # 验证交叉验证指标
        expected_keys = ["accuracy", "precision", "recall", "f1_score"]
        for key in expected_keys:
            assert key in metrics
            if f"{key}_std" in metrics:
                assert metrics[f"{key}_std"] >= 0.0


class TestEloModelUtilities:
    """ELO模型工具方法测试."""

    def test_get_team_elo(self, elo_model, minimal_training_data):
        """测试获取球队ELO."""
        # 训练前
        assert elo_model.get_team_elo("NonExistentTeam") == elo_model.initial_elo

        # 训练后
        elo_model.train(minimal_training_data)
        team_a_elo = elo_model.get_team_elo("Team_A")
        assert team_a_elo != elo_model.initial_elo  # 应该已经更新

    def test_get_team_elo_history(self, elo_model, minimal_training_data):
        """测试获取球队ELO历史."""
        # 训练前
        history = elo_model.get_team_elo_history("Team_A")
        assert history == [elo_model.initial_elo]

        # 训练后
        elo_model.train(minimal_training_data)
        history = elo_model.get_team_elo_history("Team_A")
        assert len(history) > 1  # 应该有历史记录

    def test_get_top_teams(self, elo_model, minimal_training_data):
        """测试获取顶级球队."""
        elo_model.train(minimal_training_data)

        top_teams = elo_model.get_top_teams(limit=2)
        assert len(top_teams) <= 2

        if top_teams:
            # 验证排序（降序）
            for i in range(len(top_teams) - 1):
                assert top_teams[i][1] >= top_teams[i + 1][1]

    def test_prepare_features(self, elo_model, minimal_training_data):
        """测试特征准备."""
        elo_model.train(minimal_training_data)

        match_data = {
            "home_team": "Team_A",
            "away_team": "Team_B"
        }

        features = elo_model.prepare_features(match_data)

        # 验证特征向量
        assert isinstance(features, np.ndarray)
        assert len(features) == 4  # [home_elo, away_elo, elo_difference, home_advantage_adjusted]

        # 验证所有特征为正数
        assert all(feature >= 0 for feature in features)


class TestModelPersistence:
    """模型持久化测试."""

    def test_model_save_and_load(self, elo_model, minimal_training_data, tmp_path):
        """测试模型保存和加载."""
        # 训练模型
        elo_model.train(minimal_training_data)

        # 保存模型状态
        original_elos = elo_model.team_elos.copy()
        original_is_trained = elo_model.is_trained

        # 保存模型
        model_path = tmp_path / "test_elo_model.pkl"
        save_success = elo_model.save_model(str(model_path))
        assert save_success
        assert model_path.exists()

        # 创建新模型并加载
        new_model = EloModel()
        load_success = new_model.load_model(str(model_path))
        assert load_success

        # 验证加载的模型状态
        assert new_model.is_trained == original_is_trained
        assert new_model.team_elos == original_elos
        assert new_model.model_name == elo_model.model_name
        assert new_model.model_version == elo_model.model_version

    def test_load_nonexistent_model(self, elo_model):
        """测试加载不存在的模型."""
        load_success = elo_model.load_model("/nonexistent/path/model.pkl")
        assert not load_success


class TestEdgeCases:
    """边界情况测试."""

    def test_minimum_training_data(self, elo_model):
        """测试最小训练数据."""
        # 创建最小的有效数据集
        minimal_data = pd.DataFrame({
            "date": [datetime(2024, 1, 1), datetime(2024, 1, 2)],
            "home_team": ["Team_A", "Team_B"],
            "away_team": ["Team_B", "Team_A"],
            "home_score": [2, 1],
            "away_score": [1, 2],
            "result": ["home_win", "away_win"]
        })

        # 应该能够成功训练
        result = elo_model.train(minimal_data)
        assert elo_model.is_trained
        assert len(elo_model.team_elos) == 2

    def test_extreme_scores(self, elo_model, minimal_training_data):
        """测试极端比分."""
        # 创建包含极端比分的数据
        extreme_data = minimal_training_data.copy()
        extreme_data.loc[0, "home_score"] = 10  # 大比分
        extreme_data.loc[1, "away_score"] = 0

        # 应该能够处理极端比分
        result = elo_model.train(extreme_data)
        assert elo_model.is_trained

    def test_prediction_input_validation(self, elo_model, minimal_training_data):
        """测试预测输入验证."""
        elo_model.train(minimal_training_data)

        # 测试无效输入
        invalid_inputs = [
            {},  # 空字典
            {"home_team": "Team_A"},  # 缺少away_team
            {"away_team": "Team_B"},  # 缺少home_team
        ]

        for invalid_input in invalid_inputs:
            with pytest.raises((ValueError, KeyError)):
                elo_model.predict(invalid_input)