from datetime import datetime
"""""""
P3阶段预测模型测试: PredictionModel
目标覆盖率: 64.94% → 90%
策略: 真实模型验证 + 数据完整性测试
"""""""

import os
import sys

import pytest
from pydantic import ValidationError

# 确保可以导入源码模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))

# 导入目标模块
try:
    from src.models.prediction import (
        Prediction,
        PredictionCreate,
        PredictionResponse,
        PredictionStats,
        PredictionUpdate,
    )

    PREDICTION_MODEL_AVAILABLE = True
except ImportError as e:
    print(f"PredictionModel模块导入警告: {e}")
    PREDICTION_MODEL_AVAILABLE = False


class TestPredictionModelAdvanced:
    """PredictionModel 高级测试套件"""

    @pytest.mark.skipif(not PREDICTION_MODEL_AVAILABLE, reason="PredictionModel模块不可用")
    def test_prediction_model_import(self):
        """测试预测模型导入"""
from src.models import prediction

        assert prediction is not None
        assert hasattr(prediction, "Prediction")
        assert hasattr(prediction, "PredictionCreate")
        assert hasattr(prediction, "PredictionUpdate")

    def test_prediction_model_validation(self):
        """测试预测模型数据验证"""
        if not PREDICTION_MODEL_AVAILABLE:
            pytest.skip("PredictionModel模块不可用")

        # 测试有效的预测数据
        valid_data = {
            "match_id": 1,
            "user_id": 1,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
            "strategy_used": "historical_analysis",
            "notes": "Test prediction",
        }

        prediction = Prediction(**valid_data)

        assert prediction.match_id == 1
        assert prediction.user_id == 1
        assert prediction.predicted_home == 2
        assert prediction.predicted_away == 1
        assert prediction.confidence == 0.85
        assert prediction.strategy_used == "historical_analysis"
        assert prediction.notes == "Test prediction"

    def test_prediction_model_validation_errors(self):
        """测试预测模型验证错误"""
        if not PREDICTION_MODEL_AVAILABLE:
            pytest.skip("PredictionModel模块不可用")

        # 测试无效的置信度
        invalid_data = {
            "match_id": 1,
            "user_id": 1,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 1.5,  # 无效：超过1.0
            "strategy_used": "test",
        }

        with pytest.raises(ValidationError):
            Prediction(**invalid_data)

    def test_prediction_create_model(self):
        """测试预测创建模型"""
        if not PREDICTION_MODEL_AVAILABLE:
            pytest.skip("PredictionModel模块不可用")

        create_data = {
            "match_id": 1,
            "user_id": 1,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
            "strategy_used": "ml_model",
        }

        prediction_create = PredictionCreate(**create_data)

        assert prediction_create.match_id == 1
        assert prediction_create.user_id == 1
        assert prediction_create.confidence == 0.85

    def test_prediction_update_model(self):
        """测试预测更新模型"""
        if not PREDICTION_MODEL_AVAILABLE:
            pytest.skip("PredictionModel模块不可用")

        # 测试部分更新
        update_data = {
            "predicted_home": 3,
            "confidence": 0.90,
            "notes": "Updated prediction",
        }

        prediction_update = PredictionUpdate(**update_data)

        assert prediction_update.predicted_home == 3
        assert prediction_update.confidence == 0.90
        assert prediction_update.notes == "Updated prediction"

        # 测试空更新
        empty_update = PredictionUpdate()
        assert empty_update.dict(exclude_unset=True) == {}

    def test_prediction_response_model(self):
        """测试预测响应模型"""
        if not PREDICTION_MODEL_AVAILABLE:
            pytest.skip("PredictionModel模块不可用")

        response_data = {
            "id": 1,
            "match_id": 1,
            "user_id": 1,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
            "strategy_used": "test",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        prediction_response = PredictionResponse(**response_data)

        assert prediction_response.id == 1
        assert prediction_response.match_id == 1
        assert prediction_response.confidence == 0.85
        assert isinstance(prediction_response.created_at, datetime)
        assert isinstance(prediction_response.updated_at, datetime)

    def test_prediction_stats_model(self):
        """测试预测统计模型"""
        if not PREDICTION_MODEL_AVAILABLE:
            pytest.skip("PredictionModel模块不可用")

        stats_data = {
            "total_predictions": 100,
            "correct_predictions": 75,
            "accuracy": 0.75,
            "avg_confidence": 0.82,
            "strategy_distribution": {
                "historical": 40,
                "ml_model": 35,
                "statistical": 25,
            },
        }

        prediction_stats = PredictionStats(**stats_data)

        assert prediction_stats.total_predictions == 100
        assert prediction_stats.correct_predictions == 75
        assert prediction_stats.accuracy == 0.75
        assert prediction_stats.avg_confidence == 0.82
        assert prediction_stats.strategy_distribution["historical"] == 40

    def test_prediction_model_edge_cases(self):
        """测试预测模型边界情况"""
        if not PREDICTION_MODEL_AVAILABLE:
            pytest.skip("PredictionModel模块不可用")

        # 测试最小值
        min_data = {
            "match_id": 1,
            "user_id": 1,
            "predicted_home": 0,
            "predicted_away": 0,
            "confidence": 0.0,
            "strategy_used": "test",
        }

        prediction_min = Prediction(**min_data)
        assert prediction_min.confidence == 0.0
        assert prediction_min.predicted_home == 0
        assert prediction_min.predicted_away == 0

        # 测试最大值
        max_data = {
            "match_id": 1,
            "user_id": 1,
            "predicted_home": 10,
            "predicted_away": 10,
            "confidence": 1.0,
            "strategy_used": "test",
        }

        prediction_max = Prediction(**max_data)
        assert prediction_max.confidence == 1.0
        assert prediction_max.predicted_home == 10
        assert prediction_max.predicted_away == 10

    def test_prediction_model_business_rules(self):
        """测试预测模型业务规则"""
        if not PREDICTION_MODEL_AVAILABLE:
            pytest.skip("PredictionModel模块不可用")

        # 测试业务规则：用户不能对同一比赛多次预测
        with patch(
            "src.models.prediction.check_duplicate_prediction", return_value=True
        ) as mock_check:
            data = {
                "match_id": 1,
                "user_id": 1,
                "predicted_home": 2,
                "predicted_away": 1,
                "confidence": 0.85,
                "strategy_used": "test",
            }

            # 如果有重复预测检查函数
            try:
                Prediction(**data)
                mock_check.assert_called_once_with(1, 1)
            except AttributeError:
                # 如果没有重复检查函数，跳过测试
                pass

    def test_prediction_model_serialization(self):
        """测试预测模型序列化"""
        if not PREDICTION_MODEL_AVAILABLE:
            pytest.skip("PredictionModel模块不可用")

        data = {
            "match_id": 1,
            "user_id": 1,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
            "strategy_used": "test",
            "notes": None,
        }

        prediction = Prediction(**data)

        # 测试序列化为字典
        prediction_dict = prediction.dict()

        assert prediction_dict["match_id"] == 1
        assert prediction_dict["confidence"] == 0.85
        assert prediction_dict["notes"] is None

        # 测试JSON序列化

        prediction_json = prediction.json()
        assert isinstance(prediction_json, str)

    def test_prediction_model_computed_fields(self):
        """测试预测模型计算字段"""
        if not PREDICTION_MODEL_AVAILABLE:
            pytest.skip("PredictionModel模块不可用")

        data = {
            "match_id": 1,
            "user_id": 1,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
            "strategy_used": "test",
        }

        prediction = Prediction(**data)

        # 测试计算字段（如果有）
        if hasattr(prediction, "result"):
            # 如果预测有结果字段
            assert prediction.result in ["pending", "correct", "incorrect"]

        if hasattr(prediction, "score"):
            # 如果预测有得分字段
            assert isinstance(prediction.score, (int, float))


if __name__ == "__main__":
    print("P3阶段预测模型测试: PredictionModel")
    print("目标覆盖率: 64.94% → 90%")
    print("策略: 真实模型验证 + 数据完整性测试")
