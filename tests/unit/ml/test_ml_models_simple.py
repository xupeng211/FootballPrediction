"""
机器学习模型简化测试
Simple ML Model Tests

专注于核心功能测试，避免复杂依赖问题。
测试BaseModel、PoissonModel、EloModel的核心功能。
"""

import os

# 直接导入，避免通过__init__.py
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../src/ml/models"))

try:
    from base_model import BaseModel, PredictionResult, TrainingResult
    from elo_model import EloModel
    from poisson_model import PoissonModel

    CAN_IMPORT = True
except ImportError as e:
    print(f"Warning: 无法直接导入ML模型: {e}")
    CAN_IMPORT = False


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模型直接导入失败")
class TestBaseModelSimple:
    """测试基础模型核心功能"""

    def test_prediction_result_creation(self):
        """测试预测结果创建"""
        now = datetime.now()
        result = PredictionResult(
            match_id="test_1",
            home_team="A",
            away_team="B",
            home_win_prob=0.5,
            draw_prob=0.3,
            away_win_prob=0.2,
            predicted_outcome="home_win",
            confidence=0.7,
            model_name="Test",
            model_version="1.0",
            created_at=now,
        )

        assert result.match_id == "test_1"
        assert (
            abs(result.home_win_prob + result.draw_prob + result.away_win_prob - 1.0)
            < 1e-6
        )

        # 测试to_dict
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["match_id"] == "test_1"

    def test_training_result_creation(self):
        """测试训练结果创建"""
        now = datetime.now()
        result = TrainingResult(
            model_name="Test",
            model_version="1.0",
            accuracy=0.8,
            precision=0.75,
            recall=0.85,
            f1_score=0.8,
            confusion_matrix=[[10, 2], [1, 12]],
            training_samples=100,
            validation_samples=25,
            training_time=30.5,
            features_used=["f1", "f2"],
            hyperparameters={"p1": 1.0},
            created_at=now,
        )

        assert result.model_name == "Test"
        assert result.accuracy == 0.8

        # 测试to_dict
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["accuracy"] == 0.8

    def test_base_model_abstract(self):
        """测试BaseModel是抽象的"""
        with pytest.raises(TypeError):
            BaseModel("Test", "1.0")


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模型直接导入失败")
class TestPoissonModelSimple:
    """测试泊松模型核心功能"""

    @pytest.fixture
    def model(self):
        return PoissonModel("1.0")

    @pytest.fixture
    def simple_data(self):
        """简单测试数据"""
        return pd.DataFrame(
            [
                {
                    "home_team": "A",
                    "away_team": "B",
                    "home_score": 2,
                    "away_score": 1,
                    "result": "home_win",
                },
                {
                    "home_team": "B",
                    "away_team": "C",
                    "home_score": 1,
                    "away_score": 1,
                    "result": "draw",
                },
                {
                    "home_team": "C",
                    "away_team": "A",
                    "home_score": 0,
                    "away_score": 2,
                    "result": "away_win",
                },
                {
                    "home_team": "A",
                    "away_team": "C",
                    "home_score": 3,
                    "away_score": 1,
                    "result": "home_win",
                },
                {
                    "home_team": "B",
                    "away_team": "A",
                    "home_score": 1,
                    "away_score": 2,
                    "result": "away_win",
                },
            ]
        )

    def test_model_initialization(self, model):
        """测试模型初始化"""
        assert model.model_name == "PoissonModel"
        assert model.model_version == "1.0"
        assert not model.is_trained
        assert hasattr(model, "home_advantage")
        assert hasattr(model, "team_attack_strength")
        assert hasattr(model, "team_defense_strength")

    def test_prepare_features(self, model):
        """测试特征准备"""
        match_data = {"home_team": "A", "away_team": "B"}
        features = model.prepare_features(match_data)

        assert isinstance(features, np.ndarray)
        assert len(features) == 4
        assert all(isinstance(f, (int, float)) for f in features)

    def test_basic_training(self, model, simple_data):
        """测试基础训练"""
        result = model.train(simple_data)

        assert isinstance(result, TrainingResult)
        assert result.model_name == "PoissonModel"
        assert result.training_samples == len(simple_data)
        assert model.is_trained

    def test_expected_goals_calculation(self, model, simple_data):
        """测试期望进球计算"""
        model.train(simple_data)

        # 使用训练后的球队
        teams = list(model.team_attack_strength.keys())
        if len(teams) >= 2:
            home_expected = model._calculate_expected_goals(
                teams[0], teams[1], is_home=True
            )
            away_expected = model._calculate_expected_goals(
                teams[1], teams[0], is_home=False
            )

            assert home_expected > 0
            assert away_expected > 0
            assert isinstance(home_expected, (int, float))
            assert isinstance(away_expected, (int, float))

    def test_team_strength_calculation(self, model, simple_data):
        """测试球队强度计算"""
        model.train(simple_data)

        assert len(model.team_attack_strength) > 0
        assert len(model.team_defense_strength) > 0

        # 检查强度值合理性
        for strength in model.team_attack_strength.values():
            assert 0.2 <= strength <= 3.0

        for strength in model.team_defense_strength.values():
            assert 0.2 <= strength <= 3.0

    def test_prediction_workflow(self, model, simple_data):
        """测试预测工作流"""
        model.train(simple_data)

        teams = list(model.team_attack_strength.keys())
        if len(teams) >= 2:
            match_data = {
                "home_team": teams[0],
                "away_team": teams[1],
                "match_id": "test_match",
            }

            prediction = model.predict(match_data)

            assert isinstance(prediction, PredictionResult)
            assert prediction.home_team == teams[0]
            assert prediction.away_team == teams[1]
            assert prediction.model_name == "PoissonModel"
            assert prediction.predicted_outcome in ["home_win", "draw", "away_win"]
            assert 0 <= prediction.confidence <= 1

            # 验证概率总和
            total = (
                prediction.home_win_prob
                + prediction.draw_prob
                + prediction.away_win_prob
            )
            assert abs(total - 1.0) < 1e-6

    def test_predict_proba(self, model, simple_data):
        """测试概率预测"""
        model.train(simple_data)

        teams = list(model.team_attack_strength.keys())
        if len(teams) >= 2:
            match_data = {"home_team": teams[0], "away_team": teams[1]}

            probs = model.predict_proba(match_data)

            assert isinstance(probs, tuple)
            assert len(probs) == 3
            assert all(0 <= p <= 1 for p in probs)
            assert abs(sum(probs) - 1.0) < 1e-6

    def test_model_evaluation(self, model, simple_data):
        """测试模型评估"""
        model.train(simple_data)

        metrics = model.evaluate(simple_data)

        assert isinstance(metrics, dict)
        assert "accuracy" in metrics
        assert 0 <= metrics["accuracy"] <= 1

    def test_save_and_load(self, model, simple_data, tmp_path):
        """测试保存和加载"""
        model.train(simple_data)

        # 保存
        path = tmp_path / "poisson.pkl"
        success = model.save_model(str(path))
        assert success
        assert path.exists()

        # 加载
        new_model = PoissonModel("1.0")
        success = new_model.load_model(str(path))
        assert success
        assert new_model.is_trained

    def test_error_handling(self, model):
        """测试错误处理"""
        # 未训练模型的预测
        with pytest.raises(RuntimeError):
            model.predict({"home_team": "A", "away_team": "B"})

        with pytest.raises(RuntimeError):
            model.predict_proba({"home_team": "A", "away_team": "B"})


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模型直接导入失败")
class TestEloModelSimple:
    """测试ELO模型核心功能"""

    @pytest.fixture
    def model(self):
        return EloModel("1.0")

    @pytest.fixture
    def simple_data(self):
        """简单测试数据"""
        return pd.DataFrame(
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
                    "away_score": 1,
                    "result": "draw",
                    "date": datetime.now(),
                },
                {
                    "home_team": "C",
                    "away_team": "A",
                    "home_score": 0,
                    "away_score": 2,
                    "result": "away_win",
                    "date": datetime.now(),
                },
                {
                    "home_team": "A",
                    "away_team": "C",
                    "home_score": 3,
                    "away_score": 1,
                    "result": "home_win",
                    "date": datetime.now(),
                },
                {
                    "home_team": "B",
                    "away_team": "A",
                    "home_score": 1,
                    "away_score": 2,
                    "result": "away_win",
                    "date": datetime.now(),
                },
            ]
        )

    def test_model_initialization(self, model):
        """测试模型初始化"""
        assert model.model_name == "EloModel"
        assert model.model_version == "1.0"
        assert not model.is_trained
        assert hasattr(model, "team_elos")
        assert hasattr(model, "k_factor")
        assert hasattr(model, "home_advantage")
        assert hasattr(model, "initial_elo")

    def test_expectation_calculation(self, model):
        """测试期望得分计算"""
        # 相同评分
        exp = model._calculate_expectation(1500, 1500)
        assert exp == 0.5

        # 不同评分
        exp_high = model._calculate_expectation(1600, 1400)
        exp_low = model._calculate_expectation(1400, 1600)

        assert exp_high > 0.5
        assert exp_low < 0.5
        assert abs(exp_high + exp_low - 1.0) < 1e-6

    def test_rating_update(self, model):
        """测试评分更新"""
        old_rating = 1500

        # 胜利
        new_win = model._update_rating(old_rating, 1500, 1.0)
        assert new_win > old_rating

        # 失败
        new_loss = model._update_rating(old_rating, 1500, 0.0)
        assert new_loss < old_rating

        # 平局
        new_draw = model._update_rating(old_rating, 1500, 0.5)
        assert abs(new_draw - old_rating) < 10

    def test_outcome_conversion(self, model):
        """测试结果转换"""
        assert model._convert_outcome_to_score("home_win") == 1.0
        assert model._convert_outcome_to_score("away_win") == 0.0
        assert model._convert_outcome_to_score("draw") == 0.5

        with pytest.raises(ValueError):
            model._convert_outcome_to_score("invalid")

    def test_basic_training(self, model, simple_data):
        """测试基础训练"""
        result = model.train(simple_data)

        assert isinstance(result, TrainingResult)
        assert result.model_name == "EloModel"
        assert result.training_samples == len(simple_data)
        assert model.is_trained

    def test_team_elos_after_training(self, model, simple_data):
        """测试训练后的球队ELO"""
        model.train(simple_data)

        assert len(model.team_elos) > 0

        # 检查ELO范围
        for elo in model.team_elos.values():
            assert isinstance(elo, (int, float))
            assert 1000 <= elo <= 2000

    def test_feature_preparation(self, model, simple_data):
        """测试特征准备"""
        model.train(simple_data)

        teams = list(model.team_elos.keys())
        if len(teams) >= 2:
            match_data = {"home_team": teams[0], "away_team": teams[1]}
            features = model.prepare_features(match_data)

            assert isinstance(features, np.ndarray)
            assert len(features) >= 2
            assert all(f > 0 for f in features)

    def test_prediction_workflow(self, model, simple_data):
        """测试预测工作流"""
        model.train(simple_data)

        teams = list(model.team_elos.keys())
        if len(teams) >= 2:
            match_data = {
                "home_team": teams[0],
                "away_team": teams[1],
                "match_id": "test_match",
            }

            prediction = model.predict(match_data)

            assert isinstance(prediction, PredictionResult)
            assert prediction.home_team == teams[0]
            assert prediction.away_team == teams[1]
            assert prediction.model_name == "EloModel"
            assert prediction.predicted_outcome in ["home_win", "draw", "away_win"]
            assert 0 <= prediction.confidence <= 1

    def test_save_and_load(self, model, simple_data, tmp_path):
        """测试保存和加载"""
        model.train(simple_data)

        # 保存
        path = tmp_path / "elo.pkl"
        success = model.save_model(str(path))
        assert success
        assert path.exists()

        # 加载
        new_model = EloModel("1.0")
        success = new_model.load_model(str(path))
        assert success
        assert new_model.is_trained

    def test_hyperparameter_updates(self, model):
        """测试超参数更新"""
        original_k = model.k_factor
        model.update_hyperparameters(k_factor=40)
        assert model.k_factor == 40
        assert model.k_factor != original_k


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模型直接导入失败")
class TestMLIntegrationSimple:
    """ML模型集成测试"""

    @pytest.fixture
    def test_data(self):
        """测试数据"""
        return pd.DataFrame(
            [
                {
                    "home_team": "A",
                    "away_team": "B",
                    "home_score": 2,
                    "away_score": 1,
                    "result": "home_win",
                },
                {
                    "home_team": "C",
                    "away_team": "D",
                    "home_score": 1,
                    "away_score": 2,
                    "result": "away_win",
                },
                {
                    "home_team": "B",
                    "away_team": "A",
                    "home_score": 1,
                    "away_team": "1",
                    "result": "draw",
                },
                {
                    "home_team": "D",
                    "away_team": "C",
                    "home_score": 3,
                    "away_score": 0,
                    "result": "home_win",
                },
            ]
        )

    def test_both_models_training(self, test_data):
        """测试两个模型都能训练"""
        poisson = PoissonModel("1.0")
        elo = EloModel("1.0")

        # 训练
        poisson_result = poisson.train(test_data)
        elo_result = elo.train(test_data)

        assert isinstance(poisson_result, TrainingResult)
        assert isinstance(elo_result, TrainingResult)
        assert poisson.is_trained
        assert elo.is_trained

    def test_model_comparison(self, test_data):
        """测试模型比较"""
        # 分割数据
        train = test_data[:3]
        test = test_data[3:]

        poisson = PoissonModel("1.0")
        elo = EloModel("1.0")

        # 训练
        poisson.train(train)
        elo.train(train)

        # 评估
        poisson_metrics = poisson.evaluate(test)
        elo_metrics = elo.evaluate(test)

        assert isinstance(poisson_metrics, dict)
        assert isinstance(elo_metrics, dict)
        assert "accuracy" in poisson_metrics
        assert "accuracy" in elo_metrics

    def test_prediction_consistency(self, test_data):
        """测试预测一致性"""
        poisson = PoissonModel("1.0")
        poisson.train(test_data)

        teams = list(poisson.team_attack_strength.keys())
        if len(teams) >= 2:
            match_data = {
                "home_team": teams[0],
                "away_team": teams[1],
                "match_id": "test",
            }

            # 多次预测应该一致
            pred1 = poisson.predict(match_data)
            pred2 = poisson.predict(match_data)

            assert pred1.home_win_prob == pred2.home_win_prob
            assert pred1.predicted_outcome == pred2.predicted_outcome

    def test_edge_cases(self, test_data):
        """测试边界情况"""
        poisson = PoissonModel("1.0")

        # 空数据
        empty = pd.DataFrame()
        with pytest.raises((ValueError, pd.errors.EmptyDataError)):
            poisson.train(empty)

        # 单条数据
        single = test_data.head(1)
        poisson.train(single)
        assert poisson.is_trained
