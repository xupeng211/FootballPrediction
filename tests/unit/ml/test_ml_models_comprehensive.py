"""
机器学习模型综合测试
Comprehensive ML Model Tests

测试所有机器学习模型的核心功能，包括：
- BaseModel抽象类和dataclass
- PoissonModel泊松分布模型
- EloModel ELO评分模型
- 模型训练、预测、评估流程
- 模型保存和加载
- 错误处理和边界条件
"""

import os

# 导入ML模块
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../src"))

try:
    from ml.models.base_model import BaseModel, PredictionResult, TrainingResult
    from ml.models.elo_model import EloModel
    from ml.models.poisson_model import PoissonModel

    CAN_IMPORT = True
except ImportError as e:
    logger.warning(f"Warning: 无法导入ML模型: {e}")  # TODO: Add logger import if needed
    CAN_IMPORT = False


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模型导入失败")
class TestBaseModel:
    """测试基础模型抽象类"""

    def test_prediction_result_dataclass(self):
        """测试预测结果数据类"""
        result = PredictionResult(
            match_id="test_match_1",
            home_team="Team_A",
            away_team="Team_B",
            home_win_prob=0.6,
            draw_prob=0.25,
            away_win_prob=0.15,
            predicted_outcome="home_win",
            confidence=0.75,
            model_name="TestModel",
            model_version="1.0",
            created_at=datetime.now(),
        )

        # 验证数据类属性
        assert result.match_id == "test_match_1"
        assert result.home_team == "Team_A"
        assert result.away_team == "Team_B"
        assert result.home_win_prob == 0.6
        assert result.draw_prob == 0.25
        assert result.away_win_prob == 0.15
        assert result.predicted_outcome == "home_win"
        assert result.confidence == 0.75
        assert result.model_name == "TestModel"
        assert result.model_version == "1.0"

        # 验证概率总和
        total_prob = result.home_win_prob + result.draw_prob + result.away_win_prob
        assert abs(total_prob - 1.0) < 1e-6

        # 测试to_dict方法
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["match_id"] == "test_match_1"
        assert "created_at" in result_dict

    def test_training_result_dataclass(self):
        """测试训练结果数据类"""
        result = TrainingResult(
            model_name="TestModel",
            model_version="1.0",
            accuracy=0.85,
            precision=0.82,
            recall=0.88,
            f1_score=0.85,
            confusion_matrix=[[10, 2], [3, 15]],
            training_samples=100,
            validation_samples=30,
            training_time=45.5,
            features_used=["feature1", "feature2"],
            hyperparameters={"param1": 1.0, "param2": 2.0},
            created_at=datetime.now(),
        )

        # 验证数据类属性
        assert result.model_name == "TestModel"
        assert result.accuracy == 0.85
        assert result.training_samples == 100
        assert result.training_time == 45.5
        assert len(result.features_used) == 2
        assert isinstance(result.hyperparameters, dict)

        # 测试to_dict方法
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict["accuracy"] == 0.85
        assert "created_at" in result_dict

    def test_base_model_is_abstract(self):
        """测试BaseModel是抽象类"""
        with pytest.raises(TypeError):
            BaseModel("TestModel", "1.0")

    def test_base_model_subclass_requirements(self):
        """测试BaseModel子类必须实现的方法"""

        class IncompleteModel(BaseModel):
            pass  # 没有实现必需的抽象方法

        with pytest.raises(TypeError):
            IncompleteModel("IncompleteModel", "1.0")


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模型导入失败")
class TestPoissonModel:
    """测试泊松分布模型"""

    @pytest.fixture
    def poisson_model(self):
        """创建泊松模型实例"""
        return PoissonModel("1.0")

    @pytest.fixture
    def sample_training_data(self):
        """创建示例训练数据"""
        np.random.seed(42)
        n_matches = 100

        teams = [f"Team_{i}" for i in range(1, 11)]  # 10支球队

        data = []
        for _i in range(n_matches):
            home_team = np.random.choice(teams)
            away_team = np.random.choice([t for t in teams if t != home_team])

            # 生成比分（基于泊松分布）
            home_goals = np.random.poisson(1.5)
            away_goals = np.random.poisson(1.1)

            # 确定结果
            if home_goals > away_goals:
                result = "home_win"
            elif home_goals < away_goals:
                result = "away_win"
            else:
                result = "draw"

            data.append(
                {
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_score": home_goals,
                    "away_score": away_goals,
                    "result": result,
                }
            )

        return pd.DataFrame(data)

    def test_poisson_model_initialization(self, poisson_model):
        """测试泊松模型初始化"""
        assert poisson_model.model_name == "PoissonModel"
        assert poisson_model.model_version == "1.0"
        assert not poisson_model.is_trained
        assert hasattr(poisson_model, "team_attack_strength")
        assert hasattr(poisson_model, "team_defense_strength")
        assert hasattr(poisson_model, "home_advantage")
        assert isinstance(poisson_model.home_advantage, (int, float))

    def test_prepare_features(self, poisson_model):
        """测试特征准备"""
        match_data = {"home_team": "Team_A", "away_team": "Team_B"}

        features = poisson_model.prepare_features(match_data)

        assert isinstance(features, np.ndarray)
        assert (
            len(features) == 4
        )  # [home_attack, home_defense, away_attack, away_defense]
        assert all(isinstance(f, (int, float)) for f in features)

    def test_team_strength_calculation(self, poisson_model, sample_training_data):
        """测试球队强度计算"""
        # 训练模型
        poisson_model.train(sample_training_data)

        # 验证所有球队都有强度数据
        unique_teams = set(
            sample_training_data["home_team"].tolist()
            + sample_training_data["away_team"].tolist()
        )

        assert len(poisson_model.team_attack_strength) == len(unique_teams)
        assert len(poisson_model.team_defense_strength) == len(unique_teams)

        # 验证强度值在合理范围内
        for attack_strength in poisson_model.team_attack_strength.values():
            assert 0.2 <= attack_strength <= 3.0

        for defense_strength in poisson_model.team_defense_strength.values():
            assert 0.2 <= defense_strength <= 3.0

    def test_expected_goals_calculation(self, poisson_model, sample_training_data):
        """测试期望进球计算"""
        # 训练模型
        poisson_model.train(sample_training_data)

        # 设置测试数据
        home_team = list(poisson_model.team_attack_strength.keys())[0]
        away_team = list(poisson_model.team_attack_strength.keys())[1]

        # 计算期望进球
        home_expected = poisson_model._calculate_expected_goals(
            home_team, away_team, is_home=True
        )
        away_expected = poisson_model._calculate_expected_goals(
            away_team, home_team, is_home=False
        )

        # 验证期望进球
        assert home_expected > 0
        assert away_expected > 0
        assert isinstance(home_expected, (int, float))
        assert isinstance(away_expected, (int, float))

    def test_match_probabilities_calculation(self, poisson_model, sample_training_data):
        """测试比赛概率计算"""
        # 训练模型
        poisson_model.train(sample_training_data)

        # 获取两个球队
        teams = list(poisson_model.team_attack_strength.keys())[:2]
        home_team, away_team = teams[0], teams[1]

        # 计算期望进球
        home_expected = poisson_model._calculate_expected_goals(
            home_team, away_team, is_home=True
        )
        away_expected = poisson_model._calculate_expected_goals(
            away_team, home_team, is_home=False
        )

        # 计算比赛概率
        home_win_prob, draw_prob, away_win_prob = (
            poisson_model._calculate_match_probabilities(home_expected, away_expected)
        )

        # 验证概率
        assert all(0 <= p <= 1 for p in [home_win_prob, draw_prob, away_win_prob])
        assert abs(sum([home_win_prob, draw_prob, away_win_prob]) - 1.0) < 1e-6

    def test_model_training(self, poisson_model, sample_training_data):
        """测试模型训练"""
        # 分割数据
        train_size = int(0.8 * len(sample_training_data))
        train_data = sample_training_data[:train_size]
        val_data = sample_training_data[train_size:]

        # 训练模型
        result = poisson_model.train(train_data, val_data)

        # 验证训练结果
        assert isinstance(result, TrainingResult)
        assert result.model_name == "PoissonModel"
        assert result.training_samples == len(train_data)
        assert result.validation_samples == len(val_data)
        assert result.accuracy >= 0.0
        assert result.training_time > 0

        # 验证模型状态
        assert poisson_model.is_trained
        assert poisson_model.last_training_time is not None

    def test_model_prediction(self, poisson_model, sample_training_data):
        """测试模型预测"""
        # 训练模型
        poisson_model.train(sample_training_data)

        # 获取训练过的球队
        teams = list(poisson_model.team_attack_strength.keys())[:2]
        home_team, away_team = teams[0], teams[1]

        # 进行预测
        match_data = {
            "home_team": home_team,
            "away_team": away_team,
            "match_id": f"{home_team}_vs_{away_team}",
        }

        prediction = poisson_model.predict(match_data)

        # 验证预测结果
        assert isinstance(prediction, PredictionResult)
        assert prediction.home_team == home_team
        assert prediction.away_team == away_team
        assert prediction.model_name == "PoissonModel"
        assert prediction.predicted_outcome in ["home_win", "draw", "away_win"]
        assert 0 <= prediction.confidence <= 1

        # 验证概率总和
        total_prob = (
            prediction.home_win_prob + prediction.draw_prob + prediction.away_win_prob
        )
        assert abs(total_prob - 1.0) < 1e-6

    def test_predict_proba(self, poisson_model, sample_training_data):
        """测试概率预测方法"""
        # 训练模型
        poisson_model.train(sample_training_data)

        # 获取训练过的球队
        teams = list(poisson_model.team_attack_strength.keys())[:2]
        home_team, away_team = teams[0], teams[1]

        # 进行概率预测
        match_data = {"home_team": home_team, "away_team": away_team}

        probabilities = poisson_model.predict_proba(match_data)

        # 验证概率
        assert isinstance(probabilities, tuple)
        assert len(probabilities) == 3
        assert all(0 <= p <= 1 for p in probabilities)
        assert abs(sum(probabilities) - 1.0) < 1e-6

    def test_model_evaluation(self, poisson_model, sample_training_data):
        """测试模型评估"""
        # 训练模型
        poisson_model.train(sample_training_data)

        # 评估模型
        metrics = poisson_model.evaluate(sample_training_data)

        # 验证评估指标
        assert isinstance(metrics, dict)
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert "confusion_matrix" in metrics
        assert "total_predictions" in metrics

        # 验证指标范围
        assert 0 <= metrics["accuracy"] <= 1
        assert 0 <= metrics["precision"] <= 1
        assert 0 <= metrics["recall"] <= 1
        assert 0 <= metrics["f1_score"] <= 1
        assert metrics["total_predictions"] > 0

    def test_model_save_and_load(self, poisson_model, sample_training_data, tmp_path):
        """测试模型保存和加载"""
        # 训练模型
        poisson_model.train(sample_training_data)
        original_strengths = poisson_model.team_attack_strength.copy()
        original_defense = poisson_model.team_defense_strength.copy()

        # 保存模型
        model_path = tmp_path / "poisson_model.pkl"
        success = poisson_model.save_model(str(model_path))
        assert success
        assert model_path.exists()

        # 加载模型
        new_model = PoissonModel("1.0")
        success = new_model.load_model(str(model_path))
        assert success

        # 验证加载的模型
        assert new_model.is_trained
        assert new_model.team_attack_strength == original_strengths
        assert new_model.team_defense_strength == original_defense
        assert new_model.home_advantage == poisson_model.home_advantage

    def test_error_handling(self, poisson_model):
        """测试错误处理"""
        # 测试未训练模型的预测
        match_data = {"home_team": "Team_A", "away_team": "Team_B"}

        with pytest.raises(RuntimeError):
            poisson_model.predict(match_data)

        with pytest.raises(RuntimeError):
            poisson_model.predict_proba(match_data)

        # 测试无效输入
        with pytest.raises(ValueError):
            poisson_model.prepare_features({})  # 缺少必需的team信息


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模型导入失败")
class TestEloModel:
    """测试ELO评分模型"""

    @pytest.fixture
    def elo_model(self):
        """创建ELO模型实例"""
        return EloModel("1.0")

    @pytest.fixture
    def sample_training_data(self):
        """创建示例训练数据"""
        np.random.seed(42)
        n_matches = 200

        teams = [f"Team_{i}" for i in range(1, 21)]  # 20支球队

        data = []
        for _i in range(n_matches):
            home_team = np.random.choice(teams)
            away_team = np.random.choice([t for t in teams if t != home_team])

            # 生成比分
            home_goals = np.random.poisson(1.4)
            away_goals = np.random.poisson(1.0)

            # 确定结果
            if home_goals > away_goals:
                result = "home_win"
            elif home_goals < away_goals:
                result = "away_win"
            else:
                result = "draw"

            data.append(
                {
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_score": home_goals,
                    "away_score": away_goals,
                    "result": result,
                    "date": datetime.now() - timedelta(days=np.random.randint(0, 365)),
                }
            )

        return pd.DataFrame(data)

    def test_elo_model_initialization(self, elo_model):
        """测试ELO模型初始化"""
        assert elo_model.model_name == "EloModel"
        assert elo_model.model_version == "1.0"
        assert not elo_model.is_trained
        assert hasattr(elo_model, "team_elos")
        assert hasattr(elo_model, "k_factor")
        assert hasattr(elo_model, "home_advantage")

        # 检查默认值
        assert isinstance(elo_model.k_factor, (int, float))
        assert elo_model.k_factor > 0
        assert isinstance(elo_model.home_advantage, (int, float))
        assert hasattr(elo_model, "initial_elo")

    def test_elo_rating_calculation(self, elo_model):
        """测试ELO评分计算"""
        # 测试期望得分计算
        expectation = elo_model._calculate_expectation(1500, 1500)
        assert expectation == 0.5  # 相同评分应该有相同的期望得分

        # 测试不同评分的队伍
        expectation_higher = elo_model._calculate_expectation(1600, 1400)
        expectation_lower = elo_model._calculate_expectation(1400, 1600)

        assert expectation_higher > 0.5
        assert expectation_lower < 0.5
        assert abs(expectation_higher + expectation_lower - 1.0) < 1e-6

    def test_rating_update_after_match(self, elo_model):
        """测试比赛后评分更新"""
        old_rating = 1500
        opponent_rating = 1500

        # 测试胜利情况
        new_rating_win = elo_model._update_rating(
            old_rating, opponent_rating, actual_result=1.0
        )
        assert new_rating_win > old_rating

        # 测试失败情况
        new_rating_loss = elo_model._update_rating(
            old_rating, opponent_rating, actual_result=0.0
        )
        assert new_rating_loss < old_rating

        # 测试平局情况
        new_rating_draw = elo_model._update_rating(
            old_rating, opponent_rating, actual_result=0.5
        )
        assert abs(new_rating_draw - old_rating) < 5  # 平局时评级变化应该很小

    def test_outcome_conversion(self, elo_model):
        """测试结果转换"""
        assert elo_model._convert_outcome_to_score("home_win") == 1.0
        assert elo_model._convert_outcome_to_score("away_win") == 0.0
        assert elo_model._convert_outcome_to_score("draw") == 0.5

        # 测试无效结果
        with pytest.raises(ValueError):
            elo_model._convert_outcome_to_score("invalid_result")

    def test_team_elos_initialization(self, elo_model, sample_training_data):
        """测试队伍ELO初始化"""
        # 训练模型以初始化ELO
        elo_model.train(sample_training_data)

        # 检查所有队伍都有ELO
        unique_teams = set(
            sample_training_data["home_team"].tolist()
            + sample_training_data["away_team"].tolist()
        )

        assert len(elo_model.team_elos) == len(unique_teams)

        # 检查ELO在合理范围内
        for elo in elo_model.team_elos.values():
            assert isinstance(elo, (int, float))
            assert 1000 <= elo <= 2000  # 典型的ELO范围

    def test_feature_preparation(self, elo_model, sample_training_data):
        """测试特征准备"""
        # 先训练模型
        elo_model.train(sample_training_data)

        # 测试特征准备
        match_data = {"home_team": "Team_1", "away_team": "Team_2"}

        features = elo_model.prepare_features(match_data)

        assert isinstance(features, np.ndarray)
        assert len(features) >= 2  # 至少包含主客队ELO

        # 检查特征值为正数
        assert all(f > 0 for f in features)

    def test_model_training(self, elo_model, sample_training_data):
        """测试模型训练"""
        # 分割数据
        train_size = int(0.8 * len(sample_training_data))
        train_data = sample_training_data[:train_size]
        val_data = sample_training_data[train_size:]

        # 训练模型
        result = elo_model.train(train_data, val_data)

        # 验证训练结果
        assert isinstance(result, TrainingResult)
        assert result.model_name == "EloModel"
        assert result.training_samples == len(train_data)
        assert result.validation_samples == len(val_data)
        assert result.accuracy >= 0.0
        assert result.training_time > 0

        # 验证模型状态
        assert elo_model.is_trained
        assert elo_model.last_training_time is not None

    def test_model_prediction(self, elo_model, sample_training_data):
        """测试模型预测"""
        # 训练模型
        elo_model.train(sample_training_data)

        # 获取训练过的球队
        teams = list(elo_model.team_elos.keys())[:2]
        home_team, away_team = teams[0], teams[1]

        # 进行预测
        match_data = {
            "home_team": home_team,
            "away_team": away_team,
            "match_id": f"{home_team}_vs_{away_team}",
        }

        prediction = elo_model.predict(match_data)

        # 验证预测结果
        assert isinstance(prediction, PredictionResult)
        assert prediction.home_team == home_team
        assert prediction.away_team == away_team
        assert prediction.model_name == "EloModel"
        assert prediction.predicted_outcome in ["home_win", "draw", "away_win"]
        assert 0 <= prediction.confidence <= 1

        # 验证概率总和
        total_prob = (
            prediction.home_win_prob + prediction.draw_prob + prediction.away_win_prob
        )
        assert abs(total_prob - 1.0) < 1e-6

    def test_model_save_and_load(self, elo_model, sample_training_data, tmp_path):
        """测试模型保存和加载"""
        # 训练模型
        elo_model.train(sample_training_data)
        original_elos = elo_model.team_elos.copy()

        # 保存模型
        model_path = tmp_path / "elo_model.pkl"
        success = elo_model.save_model(str(model_path))
        assert success
        assert model_path.exists()

        # 加载模型
        new_model = EloModel("1.0")
        success = new_model.load_model(str(model_path))
        assert success

        # 验证加载的模型
        assert new_model.is_trained
        assert new_model.team_elos == original_elos
        assert new_model.k_factor == elo_model.k_factor
        assert new_model.home_advantage == elo_model.home_advantage


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模型导入失败")
class TestMLModelIntegration:
    """机器学习模型集成测试"""

    @pytest.fixture
    def sample_data(self):
        """创建综合测试数据"""
        np.random.seed(42)
        n_matches = 150

        teams = [f"Team_{i}" for i in range(1, 16)]  # 15支球队

        data = []
        for _i in range(n_matches):
            home_team = np.random.choice(teams)
            away_team = np.random.choice([t for t in teams if t != home_team])

            # 生成比分
            home_goals = np.random.poisson(1.3)
            away_goals = np.random.poisson(1.1)

            # 确定结果
            if home_goals > away_goals:
                result = "home_win"
            elif home_goals < away_goals:
                result = "away_win"
            else:
                result = "draw"

            data.append(
                {
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_score": home_goals,
                    "away_score": away_goals,
                    "result": result,
                    "date": datetime.now() - timedelta(days=np.random.randint(0, 180)),
                }
            )

        return pd.DataFrame(data)

    def test_multiple_models_comparison(self, sample_data):
        """测试多模型比较"""
        # 分割数据
        train_size = int(0.8 * len(sample_data))
        train_data = sample_data[:train_size]
        test_data = sample_data[train_size:]

        # 创建模型
        poisson_model = PoissonModel("1.0")
        elo_model = EloModel("1.0")

        # 训练模型
        poisson_result = poisson_model.train(train_data, test_data)
        elo_result = elo_model.train(train_data, test_data)

        # 验证训练结果
        assert isinstance(poisson_result, TrainingResult)
        assert isinstance(elo_result, TrainingResult)

        # 比较性能
        poisson_metrics = poisson_model.evaluate(test_data)
        elo_metrics = elo_model.evaluate(test_data)

        assert isinstance(poisson_metrics, dict)
        assert isinstance(elo_metrics, dict)
        assert "accuracy" in poisson_metrics
        assert "accuracy" in elo_metrics

    def test_model_predictions_consistency(self, sample_data):
        """测试模型预测一致性"""
        # 训练泊松模型
        poisson_model = PoissonModel("1.0")
        poisson_model.train(sample_data)

        # 获取训练过的球队
        teams = list(poisson_model.team_attack_strength.keys())[:2]
        home_team, away_team = teams[0], teams[1]

        match_data = {
            "home_team": home_team,
            "away_team": away_team,
            "match_id": "test_match",
        }

        # 多次预测应该得到相同结果
        prediction1 = poisson_model.predict(match_data)
        prediction2 = poisson_model.predict(match_data)

        assert prediction1.home_win_prob == prediction2.home_win_prob
        assert prediction1.draw_prob == prediction2.draw_prob
        assert prediction1.away_win_prob == prediction2.away_win_prob
        assert prediction1.predicted_outcome == prediction2.predicted_outcome

    def test_cross_validation(self, sample_data):
        """测试交叉验证功能"""
        poisson_model = PoissonModel("1.0")

        # 测试交叉验证
        metrics = poisson_model._cross_validate(sample_data, folds=3)

        assert isinstance(metrics, dict)
        assert "accuracy" in metrics
        assert "accuracy_std" in metrics
        assert metrics["accuracy"] >= 0.0
        assert metrics["accuracy"] <= 1.0

    def test_hyperparameter_tuning(self, sample_data):
        """测试超参数调整"""
        poisson_model = PoissonModel("1.0")

        # 更新超参数
        original_home_advantage = poisson_model.home_advantage
        poisson_model.update_hyperparameters(home_advantage=0.4)

        assert poisson_model.home_advantage == 0.4
        assert poisson_model.home_advantage != original_home_advantage

        # 训练模型验证新参数生效
        poisson_model.train(sample_data)
        assert poisson_model.is_trained

    def test_edge_cases_and_boundary_conditions(self, sample_data):
        """测试边界条件和特殊情况"""
        poisson_model = PoissonModel("1.0")
        EloModel("1.0")

        # 测试空数据
        empty_data = pd.DataFrame()
        with pytest.raises((ValueError, pd.errors.EmptyDataError)):
            poisson_model.train(empty_data)

        # 测试单场比赛
        single_match = sample_data.head(1)
        poisson_model.train(single_match)
        assert poisson_model.is_trained

        # 测试未知球队
        trained_model = PoissonModel("1.0")
        trained_model.train(sample_data)

        unknown_match = {
            "home_team": "Unknown_Team_A",
            "away_team": list(trained_model.team_attack_strength.keys())[0],
        }

        # 应该能处理未知球队（使用默认值）
        try:
            prediction = trained_model.predict(unknown_match)
            assert isinstance(prediction, PredictionResult)
        except Exception as e:
            # 如果抛出异常，应该是可预期的异常
            assert isinstance(e, (ValueError, KeyError))

    def test_performance_benchmarks(self, sample_data):
        """测试性能基准"""
        poisson_model = PoissonModel("1.0")
        elo_model = EloModel("1.0")

        # 测试训练时间
        start_time = datetime.now()
        poisson_model.train(sample_data)
        poisson_training_time = (datetime.now() - start_time).total_seconds()

        start_time = datetime.now()
        elo_model.train(sample_data)
        elo_training_time = (datetime.now() - start_time).total_seconds()

        # 验证训练时间合理
        assert poisson_training_time < 60  # 应该在1分钟内完成
        assert elo_training_time < 60

        # 测试预测时间
        if poisson_model.is_trained and elo_model.is_trained:
            teams = list(poisson_model.team_attack_strength.keys())[:2]
            match_data = {
                "home_team": teams[0],
                "away_team": teams[1],
                "match_id": "perf_test",
            }

            # 批量预测性能测试
            start_time = datetime.now()
            for _ in range(100):
                poisson_model.predict(match_data)
                elo_model.predict(match_data)
            prediction_time = (datetime.now() - start_time).total_seconds()

            # 200次预测应该在合理时间内完成
            assert prediction_time < 5.0
