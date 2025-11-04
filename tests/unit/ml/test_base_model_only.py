"""
BaseModel专用测试
BaseModel Only Tests

只测试BaseModel抽象类和相关数据类，避免scipy依赖问题。
"""

import os
import sys
from datetime import datetime
from typing import Any

import pytest

# 直接导入base_model，避免通过__init__.py
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../src/ml/models"))

try:
    from base_model import BaseModel, PredictionResult, TrainingResult

    CAN_IMPORT = True
except ImportError as e:
    print(f"Warning: 无法导入BaseModel: {e}")
    CAN_IMPORT = False


@pytest.mark.skipif(not CAN_IMPORT, reason="BaseModel导入失败")
class TestBaseModel:
    """测试BaseModel核心功能"""

    def test_prediction_result_dataclass(self):
        """测试PredictionResult数据类"""
        now = datetime.now()

        result = PredictionResult(
            match_id="test_match_001",
            home_team="Team_A",
            away_team="Team_B",
            home_win_prob=0.6,
            draw_prob=0.25,
            away_win_prob=0.15,
            predicted_outcome="home_win",
            confidence=0.75,
            model_name="TestModel",
            model_version="1.0",
            created_at=now,
        )

        # 验证基本属性
        assert result.match_id == "test_match_001"
        assert result.home_team == "Team_A"
        assert result.away_team == "Team_B"
        assert result.home_win_prob == 0.6
        assert result.draw_prob == 0.25
        assert result.away_win_prob == 0.15
        assert result.predicted_outcome == "home_win"
        assert result.confidence == 0.75
        assert result.model_name == "TestModel"
        assert result.model_version == "1.0"
        assert result.created_at == now

        # 验证概率总和
        total_prob = result.home_win_prob + result.draw_prob + result.away_win_prob
        assert abs(total_prob - 1.0) < 1e-6

        # 验证预测结果值的有效性
        assert result.predicted_outcome in ["home_win", "draw", "away_win"]
        assert 0 <= result.confidence <= 1.0
        assert all(
            0 <= prob <= 1
            for prob in [result.home_win_prob, result.draw_prob, result.away_win_prob]
        )

    def test_prediction_result_to_dict(self):
        """测试PredictionResult.to_dict方法"""
        now = datetime.now()

        result = PredictionResult(
            match_id="test_002",
            home_team="Home",
            away_team="Away",
            home_win_prob=0.4,
            draw_prob=0.3,
            away_win_prob=0.3,
            predicted_outcome="draw",
            confidence=0.6,
            model_name="TestModel",
            model_version="2.0",
            created_at=now,
        )

        result_dict = result.to_dict()

        # 验证字典结构
        assert isinstance(result_dict, dict)
        assert result_dict["match_id"] == "test_002"
        assert result_dict["home_team"] == "Home"
        assert result_dict["away_team"] == "Away"
        assert result_dict["home_win_prob"] == 0.4
        assert result_dict["draw_prob"] == 0.3
        assert result_dict["away_win_prob"] == 0.3
        assert result_dict["predicted_outcome"] == "draw"
        assert result_dict["confidence"] == 0.6
        assert result_dict["model_name"] == "TestModel"
        assert result_dict["model_version"] == "2.0"
        assert "created_at" in result_dict

        # 验证时间格式
        assert isinstance(result_dict["created_at"], str)

    def test_training_result_dataclass(self):
        """测试TrainingResult数据类"""
        now = datetime.now()

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
            features_used=["feature1", "feature2", "feature3"],
            hyperparameters={"param1": 1.0, "param2": 0.5, "param3": True},
            created_at=now,
        )

        # 验证基本属性
        assert result.model_name == "TestModel"
        assert result.model_version == "1.0"
        assert result.accuracy == 0.85
        assert result.precision == 0.82
        assert result.recall == 0.88
        assert result.f1_score == 0.85
        assert result.confusion_matrix == [[10, 2], [3, 15]]
        assert result.training_samples == 100
        assert result.validation_samples == 30
        assert result.training_time == 45.5
        assert result.features_used == ["feature1", "feature2", "feature3"]
        assert result.hyperparameters == {"param1": 1.0, "param2": 0.5, "param3": True}
        assert result.created_at == now

        # 验证指标范围
        assert 0 <= result.accuracy <= 1
        assert 0 <= result.precision <= 1
        assert 0 <= result.recall <= 1
        assert 0 <= result.f1_score <= 1
        assert result.training_time >= 0
        assert result.training_samples > 0
        assert result.validation_samples >= 0

    def test_training_result_to_dict(self):
        """测试TrainingResult.to_dict方法"""
        now = datetime.now()

        result = TrainingResult(
            model_name="ModelX",
            model_version="3.0",
            accuracy=0.9,
            precision=0.88,
            recall=0.92,
            f1_score=0.9,
            confusion_matrix=[[20, 1], [2, 27]],
            training_samples=50,
            validation_samples=20,
            training_time=30.0,
            features_used=["attacking", "defending"],
            hyperparameters={"learning_rate": 0.01},
            created_at=now,
        )

        result_dict = result.to_dict()

        # 验证字典结构
        assert isinstance(result_dict, dict)
        assert result_dict["model_name"] == "ModelX"
        assert result_dict["model_version"] == "3.0"
        assert result_dict["accuracy"] == 0.9
        assert result_dict["precision"] == 0.88
        assert result_dict["recall"] == 0.92
        assert result_dict["f1_score"] == 0.9
        assert result_dict["confusion_matrix"] == [[20, 1], [2, 27]]
        assert result_dict["training_samples"] == 50
        assert result_dict["validation_samples"] == 20
        assert result_dict["training_time"] == 30.0
        assert result_dict["features_used"] == ["attacking", "defending"]
        assert result_dict["hyperparameters"] == {"learning_rate": 0.01}
        assert "created_at" in result_dict

    def test_base_model_is_abstract(self):
        """测试BaseModel是抽象类，不能直接实例化"""
        with pytest.raises(TypeError):
            BaseModel("TestModel", "1.0")

    def test_base_model_abstract_methods(self):
        """测试BaseModel定义的抽象方法"""
        # 验证抽象方法存在
        assert hasattr(BaseModel, "prepare_features")
        assert hasattr(BaseModel, "train")
        assert hasattr(BaseModel, "predict")
        assert hasattr(BaseModel, "evaluate")
        assert hasattr(BaseModel, "save_model")
        assert hasattr(BaseModel, "load_model")

        # 验证这些方法确实是抽象的
        assert getattr(
            BaseModel.prepare_features, "__isabstractmethod__", False
        )  # 可能有默认实现
        assert getattr(BaseModel.train, "__isabstractmethod__", False)  # 可能有默认实现
        assert getattr(
            BaseModel.predict, "__isabstractmethod__", False
        )  # 可能有默认实现
        assert getattr(
            BaseModel.evaluate, "__isabstractmethod__", False
        )  # 可能有默认实现
        assert getattr(
            BaseModel.save_model, "__isabstractmethod__", False
        )  # 可能有默认实现
        assert getattr(
            BaseModel.load_model, "__isabstractmethod__", False
        )  # 可能有默认实现

    def test_base_model_concrete_subclass(self):
        """测试BaseModel的具体子类"""

        class ConcreteModel(BaseModel):
            """具体的模型实现，用于测试"""

            def __init__(self, name: str, version: str = "1.0"):
                super().__init__(name, version)
                self.is_trained = False

            def prepare_features(self, match_data: dict[str, Any]):
                return [1, 2, 3]  # 简单的特征向量

            def train(self, training_data, validation_data=None):
                self.is_trained = True
                return TrainingResult(
                    model_name=self.model_name,
                    model_version=self.model_version,
                    accuracy=0.8,
                    precision=0.75,
                    recall=0.85,
                    f1_score=0.8,
                    confusion_matrix=[[5, 1], [2, 7]],
                    training_samples=(
                        len(training_data) if hasattr(training_data, "__len__") else 10
                    ),
                    validation_samples=(
                        len(validation_data)
                        if validation_data and hasattr(validation_data, "__len__")
                        else 0
                    ),
                    training_time=5.0,
                    features_used=["test_feature"],
                    hyperparameters={},
                    created_at=datetime.now(),
                )

            def predict(self, match_data):
                if not self.is_trained:
                    raise RuntimeError("Model must be trained before prediction")

                return PredictionResult(
                    match_id=match_data.get("match_id", "unknown"),
                    home_team=match_data.get("home_team", "unknown"),
                    away_team=match_data.get("away_team", "unknown"),
                    home_win_prob=0.5,
                    draw_prob=0.3,
                    away_win_prob=0.2,
                    predicted_outcome="home_win",
                    confidence=0.6,
                    model_name=self.model_name,
                    model_version=self.model_version,
                    created_at=datetime.now(),
                )

            def predict_proba(self, match_data):
                if not self.is_trained:
                    raise RuntimeError("Model must be trained before prediction")

                return (0.5, 0.3, 0.2)  # 简化的概率返回

            def evaluate(self, test_data):
                return {
                    "accuracy": 0.8,
                    "precision": 0.75,
                    "recall": 0.85,
                    "f1_score": 0.8,
                    "total_predictions": 10,
                }

            def save_model(self, file_path):
                return True  # 简化实现

            def load_model(self, file_path):
                self.is_trained = True
                return True  # 简化实现

        # 测试具体子类可以实例化
        model = ConcreteModel("TestConcreteModel", "1.0")

        assert model.model_name == "TestConcreteModel"
        assert model.model_version == "1.0"
        assert not model.is_trained
        assert hasattr(model, "hyperparameters")
        assert hasattr(model, "training_history")
        assert hasattr(model, "last_training_time")

        # 测试训练
        training_data = [{"test": "data"}]
        result = model.train(training_data)

        assert isinstance(result, TrainingResult)
        assert model.is_trained
        assert result.model_name == "TestConcreteModel"

        # 测试预测
        match_data = {
            "home_team": "Team_A",
            "away_team": "Team_B",
            "match_id": "test_001",
        }

        prediction = model.predict(match_data)
        assert isinstance(prediction, PredictionResult)
        assert prediction.home_team == "Team_A"
        assert prediction.away_team == "Team_B"

    def test_prediction_result_edge_cases(self):
        """测试PredictionResult的边界情况"""
        now = datetime.now()

        # 测试极端概率值
        result_extreme = PredictionResult(
            match_id="extreme_test",
            home_team="A",
            away_team="B",
            home_win_prob=1.0,
            draw_prob=0.0,
            away_win_prob=0.0,
            predicted_outcome="home_win",
            confidence=1.0,
            model_name="Test",
            model_version="1.0",
            created_at=now,
        )

        assert result_extreme.home_win_prob == 1.0
        assert result_extreme.confidence == 1.0

        # 测试中等概率值
        result_equal = PredictionResult(
            match_id="equal_test",
            home_team="A",
            away_team="B",
            home_win_prob=0.33,
            draw_prob=0.34,
            away_win_prob=0.33,
            predicted_outcome="draw",
            confidence=0.1,
            model_name="Test",
            model_version="1.0",
            created_at=now,
        )

        assert (
            abs(
                result_equal.home_win_prob
                + result_equal.draw_prob
                + result_equal.away_win_prob
                - 1.0
            )
            < 1e-6
        )
        assert result_equal.predicted_outcome == "draw"  # 最高概率

    def test_training_result_edge_cases(self):
        """测试TrainingResult的边界情况"""
        now = datetime.now()

        # 测试零样本
        result_zero = TrainingResult(
            model_name="ZeroModel",
            model_version="1.0",
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            confusion_matrix=[[0, 0], [0, 0]],
            training_samples=0,
            validation_samples=0,
            training_time=0.0,
            features_used=[],
            hyperparameters={},
            created_at=now,
        )

        assert result_zero.accuracy == 0.0
        assert result_zero.training_samples == 0
        assert result_zero.features_used == []
        assert result_zero.hyperparameters == {}

        # 测试完美模型
        result_perfect = TrainingResult(
            model_name="PerfectModel",
            model_version="1.0",
            accuracy=1.0,
            precision=1.0,
            recall=1.0,
            f1_score=1.0,
            confusion_matrix=[[10, 0], [0, 10]],
            training_samples=20,
            validation_samples=5,
            training_time=1.0,
            features_used=["perfect_feature"],
            hyperparameters={"perfect": True},
            created_at=now,
        )

        assert result_perfect.accuracy == 1.0
        assert result_perfect.precision == 1.0
        assert result_perfect.recall == 1.0
        assert result_perfect.f1_score == 1.0
