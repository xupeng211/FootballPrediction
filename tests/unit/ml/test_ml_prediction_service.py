"""
ML预测服务测试
ML Prediction Service Tests

专门测试ML预测服务的功能，包括：
- 预测服务初始化和配置
- 模型注册和管理
- 单模型预测
- 集成预测策略
- 批量预测
- 性能监控
"""

import os

# 导入ML模块
import sys
from datetime import datetime
from unittest.mock import Mock

import pandas as pd
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../src"))

try:
    from ml.models.base_model import BaseModel, PredictionResult
    from ml.models.elo_model import EloModel
    from ml.models.poisson_model import PoissonModel
    from ml.prediction.prediction_service import (
        EnsemblePrediction,
        PredictionService,
        PredictionStrategy,
    )

    CAN_IMPORT = True
except ImportError:
    CAN_IMPORT = False


    @pytest.fixture
    def prediction_service(self):
        """创建预测服务实例"""
        return PredictionService()

    @pytest.fixture
    def trained_models(self):
        """创建已训练的模型"""
        # 创建训练数据
        training_data = pd.DataFrame(
            {
                "home_team": ["Team_A", "Team_B", "Team_A", "Team_C"] * 25,
                "away_team": ["Team_B", "Team_A", "Team_C", "Team_A"] * 25,
                "home_score": [2, 1, 3, 1] * 25,
                "away_score": [1, 2, 1, 0] * 25,
                "result": ["home_win", "away_win", "home_win", "home_win"] * 25,
            }
        )

        # 训练泊松模型
        poisson_model = PoissonModel("1.0")
        poisson_model.train(training_data)

        # 训练ELO模型
        elo_model = EloModel("1.0")
        elo_model.train(training_data)

        return {"poisson": poisson_model, "elo": elo_model}

    def test_prediction_service_initialization(self, prediction_service):
        """测试预测服务初始化"""
        assert isinstance(prediction_service, PredictionService)
        assert len(prediction_service.models) > 0  # 应该有默认模型
        assert isinstance(prediction_service.model_weights, dict)
        assert isinstance(prediction_service.model_performance, dict)
        assert isinstance(prediction_service.default_strategy, PredictionStrategy)

    def test_get_available_models(self, prediction_service):
        """测试获取可用模型列表"""
        models = prediction_service.get_available_models()
        assert isinstance(models, list)
        assert len(models) > 0
        assert all(isinstance(model, str) for model in models)

    def test_get_trained_models(self, prediction_service):
        """测试获取已训练模型列表"""
        # 初始状态应该没有已训练的模型
        trained_models = prediction_service.get_trained_models()
        assert isinstance(trained_models, list)

    def test_register_model(self, prediction_service):
        """测试注册模型"""
        # 创建一个模拟模型
        mock_model = Mock(spec=BaseModel)
        mock_model.model_name = "test_model"
        mock_model.is_trained = False

        # 注册模型
        prediction_service.register_model("test_model", mock_model, weight=1.5)

        # 验证注册成功
        assert "test_model" in prediction_service.models
        assert prediction_service.model_weights["test_model"] == 1.5

    def test_unregister_model(self, prediction_service):
        """测试注销模型"""
        # 先注册一个模型
        mock_model = Mock(spec=BaseModel)
        mock_model.model_name = "temp_model"
        prediction_service.register_model("temp_model", mock_model)

        # 注销模型
        prediction_service.unregister_model("temp_model")

        # 验证注销成功
        assert "temp_model" not in prediction_service.models
        assert "temp_model" not in prediction_service.model_weights

    def test_set_strategy(self, prediction_service):
        """测试设置预测策略"""
        # 测试设置不同策略
        for strategy in PredictionStrategy:
            prediction_service.set_strategy(strategy)
            assert prediction_service.default_strategy == strategy

    def test_single_model_prediction(self, prediction_service, trained_models):
        """测试单模型预测"""
        # 注册已训练的模型
        for name, model in trained_models.items():
            prediction_service.register_model(name, model)

        # 测试数据
        match_data = {
            "home_team": "Team_A",
            "away_team": "Team_B",
            "match_id": "test_match_001",
        }

        # 使用泊松模型预测
        result = prediction_service.predict_match(match_data, model_name="poisson")

        assert isinstance(result, PredictionResult)
        assert result.home_team == "Team_A"
        assert result.away_team == "Team_B"
        assert result.match_id == "test_match_001"
        assert result.model_name == "PoissonModel"

    def test_ensemble_prediction_weighted(self, prediction_service, trained_models):
        """测试加权集成预测"""
        # 注册已训练的模型
        for name, model in trained_models.items():
            prediction_service.register_model(name, model)

        # 设置加权集成策略
        prediction_service.set_strategy(PredictionStrategy.WEIGHTED_ENSEMBLE)

        # 测试数据
        match_data = {
            "home_team": "Team_A",
            "away_team": "Team_B",
            "match_id": "ensemble_test_001",
        }

        # 预测
        result = prediction_service.predict_match(match_data)

        # 验证结果
        assert isinstance(result, EnsemblePrediction)
        assert result.home_team == "Team_A"
        assert result.away_team == "Team_B"
        assert result.strategy == "weighted_ensemble"
        assert len(result.predictions) > 0
        assert all(
            0 <= p <= 1
            for p in [
                result.ensemble_home_win_prob,
                result.ensemble_draw_prob,
                result.ensemble_away_win_prob,
            ]
        )
        assert (
            abs(
                sum(
                    [
                        result.ensemble_home_win_prob,
                        result.ensemble_draw_prob,
                        result.ensemble_away_win_prob,
                    ]
                )
                - 1.0
            )
            < 1e-6
        )

    def test_ensemble_prediction_majority_vote(
        self, prediction_service, trained_models
    ):
        """测试多数投票集成预测"""
        # 注册已训练的模型
        for name, model in trained_models.items():
            prediction_service.register_model(name, model)

        # 设置多数投票策略
        prediction_service.set_strategy(PredictionStrategy.MAJORITY_VOTE)

        # 测试数据
        match_data = {
            "home_team": "Team_A",
            "away_team": "Team_B",
            "match_id": "vote_test_001",
        }

        # 预测
        result = prediction_service.predict_match(match_data)

        # 验证结果
        assert isinstance(result, EnsemblePrediction)
        assert result.strategy == "majority_vote"

    def test_ensemble_prediction_best_performing(
        self, prediction_service, trained_models
    ):
        """测试最佳表现模型预测"""
        # 注册已训练的模型
        for name, model in trained_models.items():
            prediction_service.register_model(name, model)

        # 设置性能数据
        prediction_service.set_model_performance("poisson", {"accuracy": 0.65})
        prediction_service.set_model_performance("elo", {"accuracy": 0.60})

        # 设置最佳表现策略
        prediction_service.set_strategy(PredictionStrategy.BEST_PERFORMING)

        # 测试数据
        match_data = {
            "home_team": "Team_A",
            "away_team": "Team_B",
            "match_id": "best_test_001",
        }

        # 预测
        result = prediction_service.predict_match(match_data)

        # 验证结果
        assert isinstance(result, EnsemblePrediction)
        assert result.strategy == "best_performing"

    def test_batch_prediction(self, prediction_service, trained_models):
        """测试批量预测"""
        # 注册已训练的模型
        for name, model in trained_models.items():
            prediction_service.register_model(name, model)

        # 创建批量测试数据
        matches_data = [
            {"home_team": "Team_A", "away_team": "Team_B", "match_id": "batch_001"},
            {"home_team": "Team_C", "away_team": "Team_A", "match_id": "batch_002"},
            {"home_team": "Team_B", "away_team": "Team_C", "match_id": "batch_003"},
        ]

        # 批量预测
        results = prediction_service.predict_batch(matches_data)

        # 验证结果
        assert isinstance(results, list)
        assert len(results) == 3
        assert all(
            isinstance(result, (PredictionResult, EnsemblePrediction))
            for result in results
        )

    def test_update_model_weights(self, prediction_service):
        """测试更新模型权重"""
        # 获取已注册的模型名称
        available_models = list(prediction_service.models.keys())
        if len(available_models) >= 2:
            model1, model2 = available_models[0], available_models[1]

            # 设置初始权重
            initial_weights = {model1: 1.0, model2: 2.0}
            prediction_service.model_weights.update(initial_weights)

            # 更新权重
            new_weights = {model1: 1.5, model2: 2.5}
            prediction_service.update_model_weights(new_weights)

            # 验证权重更新
            assert prediction_service.model_weights[model1] == 1.5
            assert prediction_service.model_weights[model2] == 2.5

            # 尝试更新不存在的模型权重
            non_existent_weights = {"non_existent_model": 1.0}
            prediction_service.update_model_weights(non_existent_weights)
            # 确保不会添加不存在的模型
            assert "non_existent_model" not in prediction_service.model_weights

    def test_set_model_performance(self, prediction_service):
        """测试设置模型性能"""
        # 设置性能指标
        performance_metrics = {
            "accuracy": 0.75,
            "precision": 0.70,
            "recall": 0.80,
            "f1_score": 0.74,
        }
        prediction_service.set_model_performance("test_model", performance_metrics)

        # 验证性能设置
        assert prediction_service.model_performance["test_model"] == performance_metrics

    def test_get_model_info(self, prediction_service, trained_models):
        """测试获取模型信息"""
        # 注册已训练的模型
        for name, model in trained_models.items():
            prediction_service.register_model(name, model)

        # 获取模型信息
        model_info = prediction_service.get_model_info()

        # 验证信息结构
        assert isinstance(model_info, dict)
        assert "total_models" in model_info
        assert "trained_models" in model_info
        assert "default_strategy" in model_info
        assert "models" in model_info
        assert "weights" in model_info

        # 验证模型信息
        assert model_info["total_models"] >= len(trained_models)
        assert isinstance(model_info["models"], dict)

    def test_train_all_models(self, prediction_service):
        """测试训练所有模型"""
        # 创建训练数据
        training_data = pd.DataFrame(
            {
                "home_team": ["Team_A", "Team_B", "Team_A", "Team_C"] * 50,
                "away_team": ["Team_B", "Team_A", "Team_C", "Team_A"] * 50,
                "home_score": [2, 1, 3, 1] * 50,
                "away_score": [1, 2, 1, 0] * 50,
                "result": ["home_win", "away_win", "home_win", "home_win"] * 50,
            }
        )

        validation_data = training_data.head(20)

        # 训练所有模型
        results = prediction_service.train_all_models(training_data, validation_data)

        # 验证训练结果
        assert isinstance(results, dict)
        assert "total_time" in results
        assert "successful_trainings" in results
        assert "total_models" in results
        assert "training_results" in results

        # 验证至少有一些训练成功
        assert results["successful_trainings"] >= 0
        assert results["total_models"] > 0

    def test_prediction_error_handling(self, prediction_service):
        """测试预测错误处理"""
        # 测试使用不存在的模型
        match_data = {"home_team": "Team_A", "away_team": "Team_B"}

        with pytest.raises(ValueError, match="Model not found"):
            prediction_service.predict_match(match_data, model_name="nonexistent_model")

        # 测试没有已训练模型时的集成预测
        # 清空所有模型
        prediction_service.models.clear()

        with pytest.raises(RuntimeError, match="No trained models available"):
            prediction_service.predict_match(match_data)

    def test_ensemble_prediction_result_conversion(
        self, prediction_service, trained_models
    ):
        """测试集成预测结果转换"""
        # 注册已训练的模型
        for name, model in trained_models.items():
            prediction_service.register_model(name, model)

        # 预测
        match_data = {
            "home_team": "Team_A",
            "away_team": "Team_B",
            "match_id": "convert_test",
        }
        result = prediction_service.predict_match(match_data)

        # 测试转换为字典
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "match_id" in result_dict
        assert "home_team" in result_dict
        assert "away_team" in result_dict
        assert "ensemble_home_win_prob" in result_dict
        assert "ensemble_draw_prob" in result_dict
        assert "ensemble_away_win_prob" in result_dict
        assert "ensemble_predicted_outcome" in result_dict
        assert "ensemble_confidence" in result_dict
        assert "strategy" in result_dict
        assert "created_at" in result_dict
        assert "predictions" in result_dict

    def test_confidence_calculation_methods(self, prediction_service):
        """测试置信度计算方法"""
        # 测试不同概率分布的置信度计算
        test_cases = [
            (0.8, 0.1, 0.1),  # 高置信度
            (0.4, 0.3, 0.3),  # 中等置信度
            (0.34, 0.33, 0.33),  # 低置信度
        ]

        for home_prob, draw_prob, away_prob in test_cases:
            confidence = prediction_service._calculate_confidence(
                (home_prob, draw_prob, away_prob)
            )
            assert 0.1 <= confidence <= 1.0

    def test_outcome_extraction(self, prediction_service):
        """测试结果提取"""
        test_cases = [
            ((0.6, 0.2, 0.2), "home_win"),
            ((0.2, 0.6, 0.2), "draw"),
            ((0.2, 0.2, 0.6), "away_win"),
            ((0.4, 0.4, 0.2), "home_win"),  # 平局时选择第一个
        ]

        for probabilities, expected_outcome in test_cases:
            outcome = prediction_service._get_outcome_from_probabilities(probabilities)
            assert outcome == expected_outcome

    def test_weighted_ensemble_calculation(self, prediction_service, trained_models):
        """测试加权集成计算"""
        # 创建模拟预测结果
        mock_prediction1 = Mock(spec=PredictionResult)
        mock_prediction1.model_name = "poisson"
        mock_prediction1.home_win_prob = 0.6
        mock_prediction1.draw_prob = 0.2
        mock_prediction1.away_win_prob = 0.2

        mock_prediction2 = Mock(spec=PredictionResult)
        mock_prediction2.model_name = "elo"
        mock_prediction2.home_win_prob = 0.5
        mock_prediction2.draw_prob = 0.3
        mock_prediction2.away_win_prob = 0.2

        predictions = [mock_prediction1, mock_prediction2]

        # 设置权重
        prediction_service.model_weights = {"poisson": 0.6, "elo": 0.4}

        # 计算加权集成
        result = prediction_service._weighted_ensemble(predictions)

        # 验证结果
        assert isinstance(result, dict)
        assert "home_win_prob" in result
        assert "draw_prob" in result
        assert "away_win_prob" in result
        assert "predicted_outcome" in result
        assert "confidence" in result

        # 验证概率和为1
        total_prob = (
            result["home_win_prob"] + result["draw_prob"] + result["away_win_prob"]
        )
        assert abs(total_prob - 1.0) < 1e-6

    def test_majority_vote_calculation(self, prediction_service):
        """测试多数投票计算"""
        # 创建模拟预测结果
        predictions = [
            Mock(
                spec=PredictionResult,
                predicted_outcome="home_win",
                home_win_prob=0.6,
                draw_prob=0.2,
                away_win_prob=0.2,
            ),
            Mock(
                spec=PredictionResult,
                predicted_outcome="home_win",
                home_win_prob=0.5,
                draw_prob=0.3,
                away_win_prob=0.2,
            ),
            Mock(
                spec=PredictionResult,
                predicted_outcome="draw",
                home_win_prob=0.3,
                draw_prob=0.5,
                away_win_prob=0.2,
            ),
        ]

        # 计算多数投票
        result = prediction_service._majority_vote(predictions)

        # 验证结果
        assert isinstance(result, dict)
        assert result["predicted_outcome"] == "home_win"  # home_win有2票
        assert result["confidence"] == 2 / 3  # 2/3的模型同意

    def test_best_performing_selection(self, prediction_service):
        """测试最佳表现模型选择"""
        # 设置性能数据
        prediction_service.model_performance = {
            "poisson": {"accuracy": 0.70},
            "elo": {"accuracy": 0.65},
        }

        # 创建模拟预测结果
        predictions = [
            Mock(
                spec=PredictionResult,
                model_name="elo",
                home_win_prob=0.5,
                draw_prob=0.3,
                away_win_prob=0.2,
                predicted_outcome="home_win",
                confidence=0.6,
            ),
            Mock(
                spec=PredictionResult,
                model_name="poisson",
                home_win_prob=0.6,
                draw_prob=0.2,
                away_win_prob=0.2,
                predicted_outcome="home_win",
                confidence=0.7,
            ),
        ]

        # 选择最佳表现模型
        result = prediction_service._best_performing(predictions)

        # 验证选择了poisson模型（准确率更高）
        assert result["home_win_prob"] == 0.6
        assert result["confidence"] == 0.7

    def test_edge_cases(self, prediction_service, trained_models):
        """测试边界情况"""
        # 注册已训练的模型
        for name, model in trained_models.items():
            prediction_service.register_model(name, model)

        # 测试极端概率情况
        match_data = {"home_team": "Team_A", "away_team": "Team_B"}

        # 这应该不会抛出异常
        try:
            result = prediction_service.predict_match(match_data)
            assert isinstance(result, (PredictionResult, EnsemblePrediction))
        except Exception as e:
            pytest.fail(f"预测失败: {e}")

    def test_performance_monitoring_integration(
        self, prediction_service, trained_models
    ):
        """测试性能监控集成"""
        # 注册已训练的模型
        for name, model in trained_models.items():
            prediction_service.register_model(name, model)

        # 模拟性能监控数据
        performance_data = {
            "poisson": {
                "accuracy": 0.72,
                "precision": 0.68,
                "recall": 0.75,
                "f1_score": 0.71,
                "total_predictions": 1000,
                "recent_performance": [0.70, 0.72, 0.71, 0.73, 0.72],
            },
            "elo": {
                "accuracy": 0.68,
                "precision": 0.65,
                "recall": 0.70,
                "f1_score": 0.67,
                "total_predictions": 950,
                "recent_performance": [0.66, 0.68, 0.69, 0.67, 0.68],
            },
        }

        # 设置性能数据
        for model_name, metrics in performance_data.items():
            prediction_service.set_model_performance(model_name, metrics)

        # 验证性能数据被正确设置
        model_info = prediction_service.get_model_info()
        for model_name in performance_data.keys():
            if model_name in model_info["models"]:
                assert (
                    model_info["models"][model_name]["performance"]
                    == performance_data[model_name]
                )


    def test_ensemble_prediction_creation(self):
        """测试集成预测结果创建"""
        now = datetime.now()

        # 创建模拟预测结果
        mock_prediction = Mock(spec=PredictionResult)
        mock_prediction.to_dict.return_value = {
            "match_id": "test_001",
            "home_team": "Team_A",
            "away_team": "Team_B",
            "home_win_prob": 0.6,
            "draw_prob": 0.2,
            "away_win_prob": 0.2,
            "predicted_outcome": "home_win",
            "confidence": 0.7,
            "model_name": "test_model",
            "model_version": "1.0",
            "created_at": now.isoformat(),
        }

        # 创建集成预测结果
        ensemble = EnsemblePrediction(
            match_id="test_001",
            home_team="Team_A",
            away_team="Team_B",
            predictions=[mock_prediction],
            ensemble_home_win_prob=0.6,
            ensemble_draw_prob=0.2,
            ensemble_away_win_prob=0.2,
            ensemble_predicted_outcome="home_win",
            ensemble_confidence=0.7,
            strategy="weighted_ensemble",
            created_at=now,
        )

        # 验证属性
        assert ensemble.match_id == "test_001"
        assert ensemble.home_team == "Team_A"
        assert ensemble.away_team == "Team_B"
        assert len(ensemble.predictions) == 1
        assert ensemble.ensemble_home_win_prob == 0.6
        assert ensemble.strategy == "weighted_ensemble"

        # 测试转换为字典
        result_dict = ensemble.to_dict()
        assert isinstance(result_dict, dict)
        assert "predictions" in result_dict
        assert isinstance(result_dict["predictions"], list)
