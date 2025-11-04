"""
Elo模型简化测试
Simple Elo Model Tests

专门测试EloModel功能，避免复杂的依赖问题。
"""

import os
import sys
import tempfile
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

# 直接导入，避免通过__init__.py
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../src/ml/models"))

try:
    from base_model import BaseModel, PredictionResult, TrainingResult
    from elo_model import EloModel

    CAN_IMPORT = True
except ImportError as e:
    print(f"Warning: 无法导入Elo模型: {e}")
    CAN_IMPORT = False


@pytest.mark.skipif(not CAN_IMPORT, reason="Elo模型导入失败")
class TestEloModelSimple:
    """测试Elo模型核心功能"""

    @pytest.fixture
    def model(self):
        """创建Elo模型实例"""
        return EloModel("1.0")

    @pytest.fixture
    def sample_data(self):
        """创建简单测试数据"""
        return pd.DataFrame(
            [
                {
                    "home_team": "Team_A",
                    "away_team": "Team_B",
                    "home_score": 2,
                    "away_score": 1,
                    "result": "home_win",
                    "date": datetime.now(),
                },
                {
                    "home_team": "Team_B",
                    "away_team": "Team_C",
                    "home_score": 1,
                    "away_score": 1,
                    "result": "draw",
                    "date": datetime.now(),
                },
                {
                    "home_team": "Team_C",
                    "away_team": "Team_A",
                    "home_score": 0,
                    "away_score": 2,
                    "result": "away_win",
                    "date": datetime.now(),
                },
                {
                    "home_team": "Team_A",
                    "away_team": "Team_C",
                    "home_score": 3,
                    "away_score": 1,
                    "result": "home_win",
                    "date": datetime.now(),
                },
                {
                    "home_team": "Team_B",
                    "away_team": "Team_A",
                    "home_score": 1,
                    "away_score": 2,
                    "result": "away_win",
                    "date": datetime.now(),
                },
                {
                    "home_team": "Team_C",
                    "away_team": "Team_B",
                    "home_score": 2,
                    "away_score": 0,
                    "result": "home_win",
                    "date": datetime.now(),
                },
                {
                    "home_team": "Team_A",
                    "away_team": "Team_B",
                    "home_score": 1,
                    "away_score": 1,
                    "result": "draw",
                    "date": datetime.now(),
                },
                {
                    "home_team": "Team_B",
                    "away_team": "Team_C",
                    "home_score": 2,
                    "away_score": 1,
                    "result": "home_win",
                    "date": datetime.now(),
                },
            ]
        )

    def test_model_initialization(self, model):
        """测试模型初始化"""
        assert model.model_name == "EloModel"
        assert model.model_version == "1.0"
        assert not model.is_trained
        assert hasattr(model, "initial_elo")
        assert hasattr(model, "k_factor")
        assert hasattr(model, "home_advantage")
        assert hasattr(model, "team_elos")
        assert hasattr(model, "team_matches")
        assert hasattr(model, "elo_history")
        assert hasattr(model, "hyperparameters")

        # 检查默认值
        assert model.initial_elo == 1500.0
        assert model.k_factor == 32.0
        assert model.home_advantage == 100.0
        assert isinstance(model.team_elos, dict)
        assert isinstance(model.hyperparameters, dict)

    def test_expectation_calculation(self, model):
        """测试期望得分计算"""
        # 相同评分
        exp_same = model._calculate_expectation(1500, 1500)
        assert exp_same == 0.5

        # 不同评分 - 高评分队伍应该有更高期望
        exp_high = model._calculate_expectation(1600, 1400)
        exp_low = model._calculate_expectation(1400, 1600)

        assert exp_high > 0.5
        assert exp_low < 0.5
        assert abs(exp_high + exp_low - 1.0) < 1e-6

        # 测试极端情况
        exp_extreme_high = model._calculate_expectation(2000, 1000)
        exp_extreme_low = model._calculate_expectation(1000, 2000)

        assert exp_extreme_high > 0.9
        assert exp_extreme_low < 0.1

    def test_rating_update(self, model):
        """测试评分更新计算"""
        old_rating = 1500
        opponent_rating = 1500

        # 胜利情况
        new_rating_win = model._update_rating(
            old_rating, opponent_rating, actual_result=1.0
        )
        assert new_rating_win > old_rating

        # 失败情况
        new_rating_loss = model._update_rating(
            old_rating, opponent_rating, actual_result=0.0
        )
        assert new_rating_loss < old_rating

        # 平局情况
        new_rating_draw = model._update_rating(
            old_rating, opponent_rating, actual_result=0.5
        )
        assert abs(new_rating_draw - old_rating) < 5  # 平局时变化应该很小

        # 验证K因子的影响
        original_k = model.k_factor
        model.k_factor = 64  # 双倍K因子

        new_rating_big_k = model._update_rating(
            old_rating, opponent_rating, actual_result=1.0
        )
        model.k_factor = original_k

        new_rating_small_k = model._update_rating(
            old_rating, opponent_rating, actual_result=1.0
        )
        assert new_rating_big_k > new_rating_small_k  # K因子越大，变化越大

    def test_outcome_conversion(self, model):
        """测试结果转换"""
        assert model._convert_outcome_to_score("home_win") == 1.0
        assert model._convert_outcome_to_score("away_win") == 0.0
        assert model._convert_outcome_to_score("draw") == 0.5

        # 测试无效结果
        with pytest.raises(ValueError):
            model._convert_outcome_to_score("invalid_result")

        with pytest.raises(ValueError):
            model._convert_outcome_to_score("")
            model._convert_outcome_to_score(None)

    def test_basic_training(self, model, sample_data):
        """测试基础训练功能"""
        result = model.train(sample_data)

        # 验证训练结果
        assert isinstance(result, TrainingResult)
        assert result.model_name == "EloModel"
        assert result.model_version == "1.0"
        assert result.training_samples == len(sample_data)
        assert result.training_time > 0
        assert model.is_trained
        assert model.last_training_time is not None

    def test_team_elos_after_training(self, model, sample_data):
        """测试训练后的球队ELO"""
        model.train(sample_data)

        # 验证所有球队都有ELO评分
        unique_teams = set(
            sample_data["home_team"].tolist() + sample_data["away_team"].tolist()
        )
        assert len(model.team_elos) == len(unique_teams)

        # 验证ELO评分在合理范围内
        for elo in model.team_elos.values():
            assert isinstance(elo, (int, float))
            assert 1000 <= elo <= 2000  # 典型ELO范围

        # 验证至少有一些球队偏离了初始评分
        non_default_elos = [
            elo for elo in model.team_elos.values() if elo != model.initial_elo
        ]
        assert len(non_default_elos) > 0  # 应该有队伍的ELO发生变化

    def test_feature_preparation(self, model, sample_data):
        """测试特征准备"""
        model.train(sample_data)

        teams = list(model.team_elos.keys())
        if len(teams) >= 2:
            match_data = {"home_team": teams[0], "away_team": teams[1]}
            features = model.prepare_features(match_data)

            assert isinstance(features, np.ndarray)
            assert len(features) >= 2  # 至少包含主客队ELO
            assert all(isinstance(f, (int, float)) for f in features)
            assert all(f > 0 for f in features)  # ELO应该都是正数

    def test_prediction_workflow(self, model, sample_data):
        """测试预测工作流"""
        model.train(sample_data)

        teams = list(model.team_elos.keys())
        if len(teams) >= 2:
            match_data = {
                "home_team": teams[0],
                "away_team": teams[1],
                "match_id": "test_match_001",
            }

            prediction = model.predict(match_data)

            # 验证预测结果
            assert isinstance(prediction, PredictionResult)
            assert prediction.home_team == teams[0]
            assert prediction.away_team == teams[1]
            assert prediction.match_id == "test_match_001"
            assert prediction.model_name == "EloModel"
            assert prediction.model_version == "1.0"
            assert prediction.predicted_outcome in ["home_win", "draw", "away_win"]
            assert 0 <= prediction.confidence <= 1

            # 验证概率总和
            total_prob = (
                prediction.home_win_prob
                + prediction.draw_prob
                + prediction.away_win_prob
            )
            assert abs(total_prob - 1.0) < 1e-6

            # 验证概率值都在有效范围内
            assert all(
                0 <= prob <= 1
                for prob in [
                    prediction.home_win_prob,
                    prediction.draw_prob,
                    prediction.away_win_prob,
                ]
            )

    def test_predict_proba(self, model, sample_data):
        """测试概率预测方法"""
        model.train(sample_data)

        teams = list(model.team_elos.keys())
        if len(teams) >= 2:
            match_data = {"home_team": teams[0], "away_team": teams[1]}

            probabilities = model.predict_proba(match_data)

            assert isinstance(probabilities, tuple)
            assert len(probabilities) == 3
            assert all(0 <= p <= 1 for p in probabilities)
            assert abs(sum(probabilities) - 1.0) < 1e-6

    def test_match_probabilities_calculation(self, model, sample_data):
        """测试比赛概率计算"""
        model.train(sample_data)

        teams = list(model.team_elos.keys())
        if len(teams) >= 2:
            home_team, away_team = teams[0], teams[1]

            # 计算概率
            home_prob, draw_prob, away_prob = model._calculate_match_probabilities(
                home_team, away_team
            )

            # 验证概率
            assert all(0 <= p <= 1 for p in [home_prob, draw_prob, away_prob])
            assert abs(sum([home_prob, draw_prob, away_prob]) - 1.0) < 1e-6

    def test_model_evaluation(self, model, sample_data):
        """测试模型评估"""
        model.train(sample_data)

        metrics = model.evaluate(sample_data)

        # 验证评估指标
        assert isinstance(metrics, dict)
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert "total_predictions" in metrics

        # 验证指标范围
        assert 0 <= metrics["accuracy"] <= 1
        assert 0 <= metrics["precision"] <= 1
        assert 0 <= metrics["recall"] <= 1
        assert 0 <= metrics["f1_score"] <= 1
        assert metrics["total_predictions"] > 0

    def test_save_and_load(self, model, sample_data, tmp_path):
        """测试模型保存和加载"""
        model.train(sample_data)
        original_elos = model.team_elos.copy()
        original_k = model.k_factor
        original_home_adv = model.home_advantage

        # 保存模型
        model_path = tmp_path / "elo_model_test.pkl"
        success = model.save_model(str(model_path))
        assert success
        assert model_path.exists()

        # 加载模型
        new_model = EloModel("1.0")
        success = new_model.load_model(str(model_path))
        assert success

        # 验证加载的模型状态
        assert new_model.is_trained
        assert new_model.team_elos == original_elos
        assert new_model.k_factor == original_k
        assert new_model.home_advantage == original_home_adv
        assert new_model.model_name == model.model_name
        assert new_model.model_version == model.model_version

    def test_hyperparameter_updates(self, model):
        """测试超参数更新"""
        # 测试K因子更新
        original_k = model.k_factor
        model.update_hyperparameters(k_factor=40)
        assert model.k_factor == 40
        assert model.k_factor != original_k

        # 测试主场优势更新
        original_advantage = model.home_advantage
        model.update_hyperparameters(home_advantage=75)
        assert model.home_advantage == 75
        assert model.home_advantage != original_advantage

        # 测试初始ELO更新
        original_initial = model.initial_elo
        model.update_hyperparameters(initial_elo=1400)
        assert model.initial_elo == 1400
        assert model.initial_elo != original_initial

    def test_error_handling(self, model):
        """测试错误处理"""
        # 测试未训练模型的预测
        match_data = {"home_team": "Team_A", "away_team": "Team_B"}

        with pytest.raises(RuntimeError):
            model.predict(match_data)

        with pytest.raises(RuntimeError):
            model.predict_proba(match_data)

        # 测试未训练模型的评估
        with pytest.raises(RuntimeError):
            model.evaluate(pd.DataFrame([{"test": "data"}]))

        # 测试保存未训练的模型（应该允许）
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            try:
                success = model.save_model(tmp.name)
                assert success  # 应该能保存未训练的模型
            finally:
                os.unlink(tmp.name)

    def test_sequential_rating_updates(self, model):
        """测试顺序评分更新"""
        # 创建一个简单的比赛序列
        matches = pd.DataFrame(
            [
                {
                    "home_team": "A",
                    "away_team": "B",
                    "home_score": 2,
                    "away_score": 1,
                    "result": "home_win",
                    "date": datetime.now(),
                },
                {
                    "home_team": "B",
                    "away_team": "C",
                    "home_score": 1,
                    "away_score": 0,
                    "result": "home_win",
                    "date": datetime.now(),
                },
                {
                    "home_team": "A",
                    "away_team": "C",
                    "home_score": 0,
                    "away_score": 1,
                    "result": "away_win",
                    "date": datetime.now(),
                },
            ]
        )

        model.train(matches)

        # 验证所有队伍都有ELO评分
        assert len(model.team_elos) == 3
        assert all(team in model.team_elos for team in ["A", "B", "C"])

        # 验证ELO评分的相对合理性
        # A队：2胜1负，B队：1胜1负，C队：1胜2负
        # 所以A的评分应该最高，C的评分最低
        elo_a = model.team_elos["A"]
        elo_b = model.team_elos["B"]
        elo_c = model.team_elos["C"]

        # 允许一定的误差，但总体趋势应该正确
        assert elo_a > elo_c  # A应该比C高
        # A vs B 的结果要看具体比赛，这里不做强制要求

    def test_prediction_consistency(self, model, sample_data):
        """测试预测一致性"""
        model.train(sample_data)

        teams = list(model.team_elos.keys())
        if len(teams) >= 2:
            match_data = {
                "home_team": teams[0],
                "away_team": teams[1],
                "match_id": "consistency_test",
            }

            # 多次预测应该得到相同结果
            prediction1 = model.predict(match_data)
            prediction2 = model.predict(match_data)
            prediction3 = model.predict(match_data)

            assert (
                prediction1.home_win_prob
                == prediction2.home_win_prob
                == prediction3.home_win_prob
            )
            assert (
                prediction1.predicted_outcome
                == prediction2.predicted_outcome
                == prediction3.predicted_outcome
            )
            assert (
                prediction1.confidence
                == prediction2.confidence
                == prediction3.confidence
            )

    def test_edge_cases(self, model, sample_data):
        """测试边界条件"""
        # 测试单场比赛数据
        single_match = sample_data.head(1)
        model.train(single_match)
        assert model.is_trained
        assert len(model.team_elos) == 2  # 只有两支球队

        # 重置模型
        model.reset_model()

        # 测试空数据
        empty_data = pd.DataFrame()
        with pytest.raises((ValueError, pd.errors.EmptyDataError)):
            model.train(empty_data)

    def test_large_rating_difference(self, model):
        """测试大评分差异的情况"""
        # 手动设置极端ELO差异
        model.team_elos = {"StrongTeam": 2000, "WeakTeam": 1000}
        model.is_trained = True

        # 计算强队对弱队的概率
        strong_prob, draw_prob, weak_prob = model._calculate_match_probabilities(
            "StrongTeam", "WeakTeam"
        )

        # 强队应该有明显优势
        assert strong_prob > 0.7
        assert weak_prob < 0.1

        # 反过来测试
        weak_home, draw_home, strong_home = model._calculate_match_probabilities(
            "WeakTeam", "StrongTeam"
        )

        # 即使主场，弱队胜率也应该较低
        assert weak_home < 0.3
        assert strong_home > 0.5
