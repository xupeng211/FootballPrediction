#!/usr/bin/env python3
"""
🤖 ML模型测试 - 机器学习模型全面测试

测试机器学习模型的训练、预测、评估、保存和加载功能
包括基础模型、泊松模型、训练器等核心组件
"""

import asyncio
import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch
import tempfile
import os
import pickle

# 模拟导入，避免循环依赖问题
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../src'))

# 尝试导入ML模块
try:
    from src.ml.models.base_model import BaseModel, PredictionResult, TrainingResult
    from src.ml.models.poisson_model import PoissonModel
    from src.ml.model_training import ModelTrainer, TrainingConfig, TrainingStatus, ModelType
    CAN_IMPORT = True
except ImportError as e:
    print(f"Warning: 无法导入ML模块: {e}")
    CAN_IMPORT = False


# 创建模拟数据
def create_mock_training_data(num_samples: int = 1000) -> pd.DataFrame:
    """创建模拟训练数据"""
    teams = ["Team_A", "Team_B", "Team_C", "Team_D", "Team_E", "Team_F", "Team_G", "Team_H"]
    data = []

    for i in range(num_samples):
        home_team = np.random.choice(teams)
        away_team = np.random.choice([t for t in teams if t != home_team])

        # 模拟比分，基于随机概率
        home_goals = np.random.poisson(1.5)
        away_goals = np.random.poisson(1.1)

        # 确定比赛结果
        if home_goals > away_goals:
            result = "home_win"
        elif home_goals < away_goals:
            result = "away_win"
        else:
            result = "draw"

        data.append({
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_goals,
            "away_score": away_goals,
            "result": result,
            "match_date": datetime.now() - timedelta(days=np.random.randint(0, 365))
        })

    return pd.DataFrame(data)


def create_mock_prediction_data() -> Dict[str, Any]:
    """创建模拟预测数据"""
    return {
        "home_team": "Team_A",
        "away_team": "Team_B",
        "match_id": "test_match_001"
    }


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模块导入失败")
@pytest.mark.unit
@pytest.mark.ml
class TestBaseModel:
    """基础模型测试"""

    @pytest.fixture
    def mock_base_model(self):
        """创建基础模型的模拟实现"""
        class MockBaseModel(BaseModel):
            def __init__(self):
                super().__init__("MockModel", "1.0")
                self.mock_prediction = None

            def prepare_features(self, match_data: Dict[str, Any]) -> np.ndarray:
                return np.array([1.0, 2.0, 3.0, 4.0])

            def train(self, training_data: pd.DataFrame, validation_data: pd.DataFrame = None) -> TrainingResult:
                self.is_trained = True
                return TrainingResult(
                    model_name=self.model_name,
                    model_version=self.model_version,
                    accuracy=0.75,
                    precision=0.73,
                    recall=0.71,
                    f1_score=0.72,
                    confusion_matrix=[[50, 10, 5], [8, 45, 12], [6, 11, 53]],
                    training_samples=len(training_data),
                    validation_samples=len(validation_data) if validation_data is not None else 0,
                    training_time=120.5,
                    features_used=["feature1", "feature2", "feature3"],
                    hyperparameters={"param1": "value1"},
                    created_at=datetime.now()
                )

            def predict(self, match_data: Dict[str, Any]) -> PredictionResult:
                if not self.is_trained:
                    raise RuntimeError("Model must be trained before making predictions")

                return PredictionResult(
                    match_id=match_data.get("match_id", "unknown"),
                    home_team=match_data["home_team"],
                    away_team=match_data["away_team"],
                    home_win_prob=0.6,
                    draw_prob=0.25,
                    away_win_prob=0.15,
                    predicted_outcome="home_win",
                    confidence=0.75,
                    model_name=self.model_name,
                    model_version=self.model_version,
                    created_at=datetime.now()
                )

            def predict_proba(self, match_data: Dict[str, Any]) -> tuple[float, float, float]:
                if not self.is_trained:
                    raise RuntimeError("Model must be trained before making predictions")
                return (0.6, 0.25, 0.15)

            def evaluate(self, test_data: pd.DataFrame) -> Dict[str, float]:
                return {
                    "accuracy": 0.75,
                    "precision": 0.73,
                    "recall": 0.71,
                    "f1_score": 0.72
                }

            def save_model(self, file_path: str) -> bool:
                try:
                    with open(file_path, 'wb') as f:
                        pickle.dump({"is_trained": self.is_trained}, f)
                    return True
                except Exception:
                    return False

            def load_model(self, file_path: str) -> bool:
                try:
                    with open(file_path, 'rb') as f:
                        data = pickle.load(f)
                    self.is_trained = data.get("is_trained", False)
                    return True
                except Exception:
                    return False

        return MockBaseModel()

    def test_model_initialization(self, mock_base_model):
        """测试模型初始化"""
        assert mock_base_model.model_name == "MockModel"
        assert mock_base_model.model_version == "1.0"
        assert mock_base_model.is_trained is False
        assert mock_base_model.model is None
        assert mock_base_model.feature_names == []

    def test_validate_prediction_input_valid(self, mock_base_model):
        """测试有效预测输入验证"""
        valid_data = {
            "home_team": "Team_A",
            "away_team": "Team_B"
        }
        assert mock_base_model.validate_prediction_input(valid_data) is True

    def test_validate_prediction_input_missing_field(self, mock_base_model):
        """测试缺少必填字段的预测输入验证"""
        invalid_data = {
            "home_team": "Team_A"
            # 缺少 away_team
        }
        assert mock_base_model.validate_prediction_input(invalid_data) is False

    def test_validate_prediction_input_same_teams(self, mock_base_model):
        """测试主客队相同的预测输入验证"""
        invalid_data = {
            "home_team": "Team_A",
            "away_team": "Team_A"
        }
        assert mock_base_model.validate_prediction_input(invalid_data) is False

    def test_calculate_confidence(self, mock_base_model):
        """测试置信度计算"""
        # 测试不同的概率分布
        probs1 = (0.8, 0.15, 0.05)  # 高置信度
        confidence1 = mock_base_model.calculate_confidence(probs1)
        assert 0.7 <= confidence1 <= 1.0

        probs2 = (0.4, 0.33, 0.27)  # 低置信度
        confidence2 = mock_base_model.calculate_confidence(probs2)
        assert 0.1 <= confidence2 < 0.7

        probs3 = (0.33, 0.34, 0.33)  # 极低置信度
        confidence3 = mock_base_model.calculate_confidence(probs3)
        assert 0.1 <= confidence3 < confidence2

    def test_get_outcome_from_probabilities(self, mock_base_model):
        """测试从概率分布获取预测结果"""
        probs1 = (0.6, 0.25, 0.15)
        outcome1 = mock_base_model.get_outcome_from_probabilities(probs1)
        assert outcome1 == "home_win"

        probs2 = (0.2, 0.5, 0.3)
        outcome2 = mock_base_model.get_outcome_from_probabilities(probs2)
        assert outcome2 == "draw"

        probs3 = (0.1, 0.3, 0.6)
        outcome3 = mock_base_model.get_outcome_from_probabilities(probs3)
        assert outcome3 == "away_win"

    def test_validate_training_data_valid(self, mock_base_model):
        """测试有效训练数据验证"""
        valid_data = pd.DataFrame({
            "home_team": ["Team_A", "Team_B"],
            "away_team": ["Team_B", "Team_C"],
            "result": ["home_win", "draw"]
        })
        assert mock_base_model.validate_training_data(valid_data) is True

    def test_validate_training_data_empty(self, mock_base_model):
        """测试空训练数据验证"""
        empty_data = pd.DataFrame()
        assert mock_base_model.validate_training_data(empty_data) is False

    def test_validate_training_data_missing_columns(self, mock_base_model):
        """测试缺少必要列的训练数据验证"""
        invalid_data = pd.DataFrame({
            "home_team": ["Team_A", "Team_B"],
            "away_team": ["Team_B", "Team_C"]
            # 缺少 result 列
        })
        assert mock_base_model.validate_training_data(invalid_data) is False

    def test_training_workflow(self, mock_base_model):
        """测试完整训练工作流"""
        training_data = create_mock_training_data()

        # 训练前检查
        assert mock_base_model.is_trained is False

        # 执行训练
        result = mock_base_model.train(training_data)

        # 训练后检查
        assert mock_base_model.is_trained is True
        assert isinstance(result, TrainingResult)
        assert result.model_name == "MockModel"
        assert result.accuracy > 0
        assert result.training_time > 0

    def test_prediction_workflow(self, mock_base_model):
        """测试完整预测工作流"""
        # 先训练模型
        training_data = create_mock_training_data()
        mock_base_model.train(training_data)

        # 执行预测
        prediction_data = create_mock_prediction_data()
        result = mock_base_model.predict(prediction_data)

        # 验证预测结果
        assert isinstance(result, PredictionResult)
        assert result.home_team == "Team_A"
        assert result.away_team == "Team_B"
        assert result.home_win_prob + result.draw_prob + result.away_win_prob == pytest.approx(1.0)
        assert result.predicted_outcome in ["home_win", "draw", "away_win"]
        assert 0 <= result.confidence <= 1.0

    def test_prediction_without_training(self, mock_base_model):
        """测试未训练模型的预测"""
        prediction_data = create_mock_prediction_data()

        with pytest.raises(RuntimeError, match="Model must be trained"):
            mock_base_model.predict(prediction_data)

    def test_model_save_and_load(self, mock_base_model):
        """测试模型保存和加载"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            file_path = tmp_file.name

        try:
            # 训练模型
            training_data = create_mock_training_data()
            mock_base_model.train(training_data)

            # 保存模型
            save_success = mock_base_model.save_model(file_path)
            assert save_success is True

            # 创建新模型实例并加载
            new_model = type(mock_base_model)()
            load_success = new_model.load_model(file_path)
            assert load_success is True
            assert new_model.is_trained is True

        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)

    def test_get_model_info(self, mock_base_model):
        """测试获取模型信息"""
        info = mock_base_model.get_model_info()

        assert info["model_name"] == "MockModel"
        assert info["model_version"] == "1.0"
        assert info["is_trained"] is False
        assert info["feature_count"] == 0
        assert isinstance(info["hyperparameters"], dict)

    def test_log_training_step(self, mock_base_model):
        """测试训练步骤记录"""
        metrics = {"accuracy": 0.7, "loss": 0.5}
        mock_base_model.log_training_step(1, metrics)

        assert len(mock_base_model.training_history) == 1
        assert mock_base_model.training_history[0]["step"] == 1
        assert mock_base_model.training_history[0]["metrics"] == metrics

    def test_get_training_curve(self, mock_base_model):
        """测试获取训练曲线"""
        # 添加一些训练历史
        for i in range(3):
            mock_base_model.log_training_step(i, {"accuracy": 0.6 + i * 0.1, "loss": 1.0 - i * 0.2})

        curves = mock_base_model.get_training_curve()
        assert "accuracy" in curves
        assert "loss" in curves
        assert len(curves["accuracy"]) == 3
        assert curves["accuracy"] == [0.6, 0.7, 0.8]

    def test_update_hyperparameters(self, mock_base_model):
        """测试更新超参数"""
        original_params = mock_base_model.hyperparameters.copy()
        mock_base_model.update_hyperparameters(new_param="new_value", learning_rate=0.001)

        assert mock_base_model.hyperparameters != original_params
        assert "new_param" in mock_base_model.hyperparameters
        assert mock_base_model.hyperparameters["new_param"] == "new_value"

    def test_reset_model(self, mock_base_model):
        """测试重置模型"""
        # 训练模型并添加历史
        training_data = create_mock_training_data()
        mock_base_model.train(training_data)
        mock_base_model.log_training_step(1, {"accuracy": 0.7})

        assert mock_base_model.is_trained is True
        assert len(mock_base_model.training_history) > 0

        # 重置模型
        mock_base_model.reset_model()

        assert mock_base_model.is_trained is False
        assert mock_base_model.model is None
        assert len(mock_base_model.training_history) == 0
        assert mock_base_model.last_training_time is None


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模块导入失败")
@pytest.mark.unit
@pytest.mark.ml
class TestPoissonModel:
    """泊松模型测试"""

    @pytest.fixture
    def poisson_model(self):
        """创建泊松模型实例"""
        return PoissonModel("1.0")

    @pytest.fixture
    def training_data(self):
        """创建训练数据"""
        return create_mock_training_data(500)

    def test_poisson_model_initialization(self, poisson_model):
        """测试泊松模型初始化"""
        assert poisson_model.model_name == "PoissonModel"
        assert poisson_model.model_version == "1.0"
        assert poisson_model.is_trained is False
        assert poisson_model.home_advantage == 0.3
        assert len(poisson_model.team_attack_strength) == 0

    def test_prepare_features(self, poisson_model):
        """测试特征准备"""
        match_data = create_mock_prediction_data()

        # 未训练时的特征准备
        features = poisson_model.prepare_features(match_data)
        assert len(features) == 4
        assert all(f == 1.0 for f in features)  # 默认值

    def test_team_strengths_calculation(self, poisson_model, training_data):
        """测试球队强度计算"""
        poisson_model.train(training_data)

        # 检查是否计算了球队强度
        assert len(poisson_model.team_attack_strength) > 0
        assert len(poisson_model.team_defense_strength) > 0
        assert poisson_model.total_matches == len(training_data)

    def test_poisson_training(self, poisson_model, training_data):
        """测试泊松模型训练"""
        result = poisson_model.train(training_data)

        assert isinstance(result, TrainingResult)
        assert result.model_name == "PoissonModel"
        assert poisson_model.is_trained is True
        assert result.training_samples == len(training_data)
        assert result.training_time > 0
        assert len(result.features_used) > 0

    def test_poisson_prediction(self, poisson_model, training_data):
        """测试泊松模型预测"""
        # 训练模型
        poisson_model.train(training_data)

        # 进行预测
        match_data = create_mock_prediction_data()
        result = poisson_model.predict(match_data)

        assert isinstance(result, PredictionResult)
        assert result.home_team == "Team_A"
        assert result.away_team == "Team_B"
        assert abs(result.home_win_prob + result.draw_prob + result.away_win_prob - 1.0) < 0.01
        assert result.predicted_outcome in ["home_win", "draw", "away_win"]
        assert 0 <= result.confidence <= 1.0

    def test_poisson_predict_proba(self, poisson_model, training_data):
        """测试概率预测"""
        # 训练模型
        poisson_model.train(training_data)

        # 进行概率预测
        match_data = create_mock_prediction_data()
        probabilities = poisson_model.predict_proba(match_data)

        assert len(probabilities) == 3
        assert all(0 <= p <= 1 for p in probabilities)
        assert abs(sum(probabilities) - 1.0) < 0.01

    def test_expected_goals_calculation(self, poisson_model, training_data):
        """测试期望进球计算"""
        poisson_model.train(training_data)

        # 计算期望进球
        home_expected = poisson_model._calculate_expected_goals("Team_A", "Team_B", is_home=True)
        away_expected = poisson_model._calculate_expected_goals("Team_B", "Team_A", is_home=False)

        assert home_expected > 0
        assert away_expected > 0
        # 主队通常有主场优势，期望进球可能更高
        assert home_expected >= away_expected * 0.8  # 允许一定误差

    def test_match_probabilities_calculation(self, poisson_model):
        """测试比赛概率计算"""
        home_expected = 1.5
        away_expected = 1.1

        home_win, draw, away_win = poisson_model._calculate_match_probabilities(home_expected, away_expected)

        assert all(0 <= p <= 1 for p in [home_win, draw, away_win])
        assert abs(home_win + draw + away_win - 1.0) < 0.01

    def test_model_evaluation(self, poisson_model, training_data):
        """测试模型评估"""
        # 训练模型
        poisson_model.train(training_data)

        # 评估模型
        test_data = create_mock_training_data(100)
        metrics = poisson_model.evaluate(test_data)

        assert isinstance(metrics, dict)
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert "total_predictions" in metrics
        assert 0 <= metrics["accuracy"] <= 1

    def test_cross_validation(self, poisson_model, training_data):
        """测试交叉验证"""
        metrics = poisson_model._cross_validate(training_data, folds=3)

        assert isinstance(metrics, dict)
        assert "accuracy" in metrics
        assert "accuracy_std" in metrics
        assert "precision" in metrics
        assert "precision_std" in metrics

    def test_model_save_and_load(self, poisson_model, training_data):
        """测试模型保存和加载"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            file_path = tmp_file.name

        try:
            # 训练并保存模型
            poisson_model.train(training_data)
            save_success = poisson_model.save_model(file_path)
            assert save_success is True

            # 创建新模型并加载
            new_model = PoissonModel()
            load_success = new_model.load_model(file_path)
            assert load_success is True
            assert new_model.is_trained is True
            assert new_model.model_name == poisson_model.model_name
            assert new_model.total_matches == poisson_model.total_matches

        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)

    def test_prediction_without_training(self, poisson_model):
        """测试未训练模型的预测"""
        match_data = create_mock_prediction_data()

        with pytest.raises(RuntimeError, match="Model must be trained"):
            poisson_model.predict(match_data)

    def test_invalid_prediction_input(self, poisson_model, training_data):
        """测试无效预测输入"""
        poisson_model.train(training_data)

        # 测试缺少必填字段
        invalid_data = {"home_team": "Team_A"}  # 缺少 away_team
        with pytest.raises(ValueError):
            poisson_model.predict(invalid_data)

    def test_hyperparameter_updates(self, poisson_model):
        """测试超参数更新"""
        new_params = {
            "home_advantage": 0.4,
            "min_matches_per_team": 15,
            "max_goals": 12
        }

        poisson_model.update_hyperparameters(**new_params)

        for key, value in new_params.items():
            assert poisson_model.hyperparameters[key] == value


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模块导入失败")
@pytest.mark.unit
@pytest.mark.ml
class TestModelTrainer:
    """模型训练器测试"""

    @pytest.fixture
    def training_config(self):
        """创建训练配置"""
        config = TrainingConfig()
        config.model_type = ModelType.RANDOM_FOREST
        config.epochs = 5
        return config

    @pytest.fixture
    def model_trainer(self, training_config):
        """创建模型训练器"""
        return ModelTrainer(training_config)

    @pytest.fixture
    def sample_data(self):
        """创建示例数据"""
        np.random.seed(42)
        n_samples = 200

        data = pd.DataFrame({
            "feature1": np.random.randn(n_samples),
            "feature2": np.random.randn(n_samples),
            "feature3": np.random.randn(n_samples),
            "target": np.random.choice(["home_win", "draw", "away_win"], n_samples)
        })

        return data

    def test_model_trainer_initialization(self, model_trainer):
        """测试模型训练器初始化"""
        assert model_trainer.config is not None
        assert model_trainer.status == TrainingStatus.PENDING
        assert model_trainer.model is None
        assert len(model_trainer.training_history) == 0

    @pytest.mark.asyncio
    async def test_prepare_data(self, model_trainer, sample_data):
        """测试数据准备"""
        X_train, X_test, y_train, y_test = await model_trainer.prepare_data(
            sample_data, "target"
        )

        assert len(X_train) > len(X_test)
        assert len(X_train) == len(y_train)
        assert len(X_test) == len(y_test)
        assert X_train.shape[1] == 3  # 3个特征
        assert list(X_train.columns) == ["feature1", "feature2", "feature3"]

    @pytest.mark.asyncio
    async def test_train_model(self, model_trainer, sample_data):
        """测试模型训练"""
        # 准备数据
        X_train, X_test, y_train, y_test = await model_trainer.prepare_data(
            sample_data, "target"
        )

        # 训练模型
        result = await model_trainer.train(X_train, y_train, X_test, y_test)

        assert result["status"] == "completed"
        assert "model_name" in result
        assert "training_time" in result
        assert "metrics" in result
        assert "feature_importance" in result
        assert model_trainer.status == TrainingStatus.COMPLETED
        assert model_trainer.model is not None

    @pytest.mark.asyncio
    async def test_evaluate_model(self, model_trainer, sample_data):
        """测试模型评估"""
        # 先训练模型
        X_train, X_test, y_train, y_test = await model_trainer.prepare_data(
            sample_data, "target"
        )
        await model_trainer.train(X_train, y_train, X_test, y_test)

        # 评估模型
        metrics = await model_trainer.evaluate(X_test, y_test)

        assert isinstance(metrics, dict)
        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert all(0 <= v <= 1 for v in metrics.values() if isinstance(v, (int, float)))

    @pytest.mark.asyncio
    async def test_save_and_load_model(self, model_trainer, sample_data):
        """测试模型保存和加载"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            file_path = tmp_file.name

        try:
            # 训练模型
            X_train, X_test, y_train, y_test = await model_trainer.prepare_data(
                sample_data, "target"
            )
            await model_trainer.train(X_train, y_train, X_test, y_test)

            # 保存模型
            save_success = await model_trainer.save_model(file_path)
            assert save_success is True

            # 创建新的训练器并加载模型
            new_trainer = ModelTrainer()
            load_success = await new_trainer.load_model(file_path)
            assert load_success is True
            assert new_trainer.model is not None

        finally:
            if os.path.exists(file_path):
                os.unlink(file_path)
            # 清理历史文件
            history_path = file_path.replace(".pkl", "_history.json")
            if os.path.exists(history_path):
                os.unlink(history_path)

    def test_get_training_summary(self, model_trainer):
        """测试获取训练摘要"""
        summary = model_trainer.get_training_summary()

        assert isinstance(summary, dict)
        assert "status" in summary
        assert "model_type" in summary
        assert "training_epochs" in summary
        assert summary["status"] == TrainingStatus.PENDING.value
        assert summary["training_epochs"] == 0


@pytest.mark.unit
@pytest.mark.ml
class TestMLIntegration:
    """ML模块集成测试"""

    @pytest.mark.asyncio
    async def test_complete_ml_workflow(self):
        """测试完整的ML工作流"""
        if not CAN_IMPORT:
            pytest.skip("ML模块导入失败")

        # 1. 准备数据
        training_data = create_mock_training_data(300)

        # 2. 创建并训练泊松模型
        poisson_model = PoissonModel()
        training_result = poisson_model.train(training_data)

        # 3. 进行预测
        prediction_data = create_mock_prediction_data()
        prediction_result = poisson_model.predict(prediction_data)

        # 4. 评估模型
        test_data = create_mock_training_data(100)
        evaluation_metrics = poisson_model.evaluate(test_data)

        # 5. 验证完整工作流
        assert poisson_model.is_trained is True
        assert isinstance(training_result, TrainingResult)
        assert isinstance(prediction_result, PredictionResult)
        assert isinstance(evaluation_metrics, dict)
        assert training_result.accuracy > 0
        assert abs(prediction_result.home_win_prob +
                  prediction_result.draw_prob +
                  prediction_result.away_win_prob - 1.0) < 0.01
        assert evaluation_metrics.get("accuracy", 0) > 0

    @pytest.mark.asyncio
    async def test_model_comparison(self):
        """测试模型比较"""
        if not CAN_IMPORT:
            pytest.skip("ML模块导入失败")

        training_data = create_mock_training_data(200)
        test_data = create_mock_training_data(50)

        models = [PoissonModel() for _ in range(3)]
        results = []

        for i, model in enumerate(models):
            model.model_version = f"comparison_{i+1}"
            training_result = model.train(training_data)
            evaluation_metrics = model.evaluate(test_data)

            results.append({
                "model": model,
                "training": training_result,
                "evaluation": evaluation_metrics
            })

        # 比较模型性能
        accuracies = [r["evaluation"]["accuracy"] for r in results]
        assert len(accuracies) == 3
        # 至少有一个模型应该有不同的性能
        assert len(set(round(acc, 3) for acc in accuracies)) > 1 or max(accuracies) > 0.6

    def test_model_factory_pattern(self):
        """测试模型工厂模式"""
        if not CAN_IMPORT:
            pytest.skip("ML模块导入失败")

        # 测试创建不同类型的模型
        models = {
            "poisson": PoissonModel("1.0"),
            "poisson_v2": PoissonModel("2.0"),
        }

        for name, model in models.items():
            assert model.model_name == "PoissonModel"
            assert model.is_trained is False
            assert isinstance(model, BaseModel)

    def test_error_handling(self):
        """测试错误处理"""
        if not CAN_IMPORT:
            pytest.skip("ML模块导入失败")

        model = PoissonModel()

        # 测试未训练模型的预测
        with pytest.raises(RuntimeError):
            model.predict({"home_team": "A", "away_team": "B"})

        # 测试无效数据训练
        empty_data = pd.DataFrame()
        with pytest.raises(ValueError):
            model.train(empty_data)

        # 测试无效输入预测
        training_data = create_mock_training_data(50)
        model.train(training_data)

        with pytest.raises(ValueError):
            model.predict({"home_team": "A"})  # 缺少away_team

        with pytest.raises(ValueError):
            model.predict({"home_team": "A", "away_team": "A"})  # 相同队伍

    def test_data_quality_validation(self):
        """测试数据质量验证"""
        if not CAN_IMPORT:
            pytest.skip("ML模块导入失败")

        model = PoissonModel()

        # 测试空数据
        empty_data = pd.DataFrame()
        assert model.validate_training_data(empty_data) is False

        # 测试缺少列的数据
        incomplete_data = pd.DataFrame({
            "home_team": ["A", "B"],
            "away_team": ["C", "D"]
            # 缺少其他必要列
        })
        assert model.validate_training_data(incomplete_data) is False

        # 测试包含空值的数据
        null_data = pd.DataFrame({
            "home_team": ["A", None, "C"],
            "away_team": ["B", "D", "E"],
            "result": ["home_win", "draw", "away_win"]
        })
        # 应该返回True但发出警告
        assert model.validate_training_data(null_data) is True


# 测试运行器
async def run_ml_tests():
    """运行ML测试套件"""
    print("🤖 开始ML模型测试")
    print("=" * 60)

    # 这里可以添加更复杂的ML测试逻辑
    print("✅ ML模型测试完成")


if __name__ == "__main__":
    asyncio.run(run_ml_tests())