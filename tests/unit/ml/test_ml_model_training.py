#!/usr/bin/env python3
"""
🤖 ML模型训练测试 - 机器学习模型训练流程测试

测试ML模型的完整训练流程，包括数据预处理、模型训练、验证、
保存和加载等功能。覆盖PoissonModel和其他ML模型的训练场景。
"""

import asyncio
import os
import tempfile
import warnings
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

# 抑制warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# 模拟导入，避免循环依赖问题
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../src"))

# 尝试导入ML模块
try:
    from src.ml.model_training import (ModelTrainer, ModelType, TrainingConfig,
                                       TrainingStatus)
    from src.ml.models.base_model import (BaseModel, PredictionResult,
                                          TrainingResult)
    from src.ml.models.poisson_model import PoissonModel

    CAN_IMPORT = True
except ImportError as e:
    print(f"Warning: 无法导入ML模块: {e}")
    CAN_IMPORT = False


def create_training_data(num_matches: int = 500) -> pd.DataFrame:
    """创建训练数据"""
    teams = [f"Team_{chr(65+i)}" for i in range(20)]  # Team_A 到 Team_T
    data = []

    for i in range(num_matches):
        home_team = np.random.choice(teams)
        away_team = np.random.choice([t for t in teams if t != home_team])

        # 基于球队强度生成比分
        team_strengths = {team: np.random.uniform(0.5, 2.0) for team in teams}
        home_strength = team_strengths[home_team]
        away_strength = team_strengths[away_team]

        # 主场优势
        home_advantage = 0.3
        home_expected = (home_strength * (1 + home_advantage)) / away_strength * 1.5
        away_expected = away_strength / home_strength * 1.1

        home_goals = np.random.poisson(max(home_expected, 0.1))
        away_goals = np.random.poisson(max(away_expected, 0.1))

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
                "match_date": datetime.now()
                - timedelta(days=np.random.randint(0, 365)),
                "home_team_strength": home_strength,
                "away_team_strength": away_strength,
            }
        )

    return pd.DataFrame(data)


def create_test_data(num_matches: int = 100) -> pd.DataFrame:
    """创建测试数据"""
    return create_training_data(num_matches)


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模块导入失败")
@pytest.mark.unit
@pytest.mark.ml
class TestMLModelTraining:
    """ML模型训练测试"""

    def test_poisson_model_training_workflow(self):
        """测试Poisson模型完整训练流程"""
        # 创建训练数据
        training_data = create_training_data(300)
        test_data = create_test_data(100)

        # 初始化模型
        model = PoissonModel("test_poisson")

        # 验证初始状态
        assert not model.is_trained
        assert model.model is None
        assert len(model.team_attack_strength) == 0

        # 训练模型
        training_result = model.train(training_data)

        # 验证训练结果
        assert model.is_trained
        assert isinstance(training_result, TrainingResult)
        assert training_result.model_name == "PoissonModel"
        assert training_result.training_samples == len(training_data)
        assert training_result.accuracy > 0.0
        assert training_result.training_time > 0
        assert len(model.team_attack_strength) > 0
        assert len(model.team_defense_strength) > 0

        # 验证模型预测功能
        test_match = {
            "home_team": training_data["home_team"].iloc[0],
            "away_team": training_data["away_team"].iloc[1],
            "match_id": "test_match_001",
        }

        prediction = model.predict(test_match)
        assert isinstance(prediction, PredictionResult)
        assert prediction.home_team == test_match["home_team"]
        assert prediction.away_team == test_match["away_team"]
        assert (
            abs(
                prediction.home_win_prob
                + prediction.draw_prob
                + prediction.away_win_prob
                - 1.0
            )
            < 0.01
        )
        assert prediction.confidence > 0.0
        assert prediction.model_name == "PoissonModel"

        print(
            f"✅ Poisson模型训练完成: 准确率={training_result.accuracy:.3f}, 训练时间={training_result.training_time:.2f}s"
        )

    def test_model_training_with_validation_data(self):
        """测试带验证数据的模型训练"""
        # 创建数据
        training_data = create_training_data(200)
        validation_data = create_test_data(50)

        # 初始化模型
        model = PoissonModel("validation_test")

        # 训练模型（带验证数据）
        training_result = model.train(training_data, validation_data)

        # 验证训练结果包含验证信息
        assert training_result.validation_samples == len(validation_data)
        assert training_result.accuracy > 0.0

        # 在验证数据上评估
        validation_metrics = model.evaluate(validation_data)
        assert "accuracy" in validation_metrics
        assert "precision" in validation_metrics
        assert "recall" in validation_metrics
        assert "f1_score" in validation_metrics

        print(
            f"✅ 验证训练完成: 训练准确率={training_result.accuracy:.3f}, 验证准确率={validation_metrics['accuracy']:.3f}"
        )

    def test_model_cross_validation(self):
        """测试模型交叉验证"""
        # 创建较小数据集用于交叉验证
        training_data = create_training_data(100)

        # 初始化模型
        model = PoissonModel("cv_test")

        # 设置超参数
        model.update_hyperparameters(min_matches_per_team=5)

        # 训练模型（会使用交叉验证）
        training_result = model.train(training_data)

        # 验证交叉验证结果
        assert training_result.accuracy > 0.0
        assert model.is_trained
        assert len(model.team_attack_strength) > 0

        # 验证模型可以正常预测
        test_match = {
            "home_team": training_data["home_team"].iloc[0],
            "away_team": training_data["away_team"].iloc[1],
        }

        probabilities = model.predict_proba(test_match)
        assert len(probabilities) == 3
        assert all(0 <= p <= 1 for p in probabilities)
        assert abs(sum(probabilities) - 1.0) < 0.01

        print(f"✅ 交叉验证完成: 准确率={training_result.accuracy:.3f}")

    def test_model_hyperparameter_optimization(self):
        """测试模型超参数优化"""
        # 创建训练数据
        training_data = create_training_data(200)

        # 测试不同的超参数配置
        hyperparameter_configs = [
            {"home_advantage": 0.1, "min_matches_per_team": 5},
            {"home_advantage": 0.3, "min_matches_per_team": 10},
            {"home_advantage": 0.5, "min_matches_per_team": 15},
        ]

        results = []

        for config in hyperparameter_configs:
            model = PoissonModel(f"hyperparam_test_{len(results)}")
            model.update_hyperparameters(**config)

            training_result = model.train(training_data)
            results.append(
                {
                    "config": config,
                    "accuracy": training_result.accuracy,
                    "training_time": training_result.training_time,
                }
            )

        # 验证不同配置产生不同结果
        accuracies = [r["accuracy"] for r in results]
        assert len(set(acc for acc in accuracies)) > 1  # 至少有两个不同的准确率

        # 找到最佳配置
        best_result = max(results, key=lambda x: x["accuracy"])
        print(
            f"✅ 超参数优化完成: 最佳配置={best_result['config']}, 准确率={best_result['accuracy']:.3f}"
        )

    def test_model_save_and_load_workflow(self):
        """测试模型保存和加载工作流"""
        # 创建训练数据
        training_data = create_training_data(150)

        # 训练模型
        original_model = PoissonModel("save_test_original")
        training_result = original_model.train(training_data)

        # 获取训练后的预测结果作为基准
        test_match = {
            "home_team": training_data["home_team"].iloc[0],
            "away_team": training_data["away_team"].iloc[1],
            "match_id": "save_load_test",
        }

        original_prediction = original_model.predict(test_match)
        original_team_strengths = original_model.team_attack_strength.copy()

        # 保存模型到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as tmp_file:
            model_path = tmp_file.name

        try:
            # 保存模型
            save_success = original_model.save_model(model_path)
            assert save_success
            assert os.path.exists(model_path)

            # 创建新模型并加载
            loaded_model = PoissonModel("save_test_loaded")
            load_success = loaded_model.load_model(model_path)
            assert load_success

            # 验证加载的模型状态
            assert loaded_model.is_trained == original_model.is_trained
            assert loaded_model.model_name == original_model.model_name
            assert loaded_model.model_version == original_model.model_version
            assert (
                loaded_model.team_attack_strength == original_model.team_attack_strength
            )
            assert (
                loaded_model.team_defense_strength
                == original_model.team_defense_strength
            )

            # 验证加载模型的预测结果一致性
            loaded_prediction = loaded_model.predict(test_match)

            assert loaded_prediction.home_team == original_prediction.home_team
            assert loaded_prediction.away_team == original_prediction.away_team
            assert (
                abs(loaded_prediction.home_win_prob - original_prediction.home_win_prob)
                < 0.001
            )
            assert (
                abs(loaded_prediction.draw_prob - original_prediction.draw_prob) < 0.001
            )
            assert (
                abs(loaded_prediction.away_win_prob - original_prediction.away_win_prob)
                < 0.001
            )

            print("✅ 模型保存加载测试通过: 预测结果一致")

        finally:
            # 清理临时文件
            if os.path.exists(model_path):
                os.unlink(model_path)

    def test_model_training_with_different_data_sizes(self):
        """测试不同数据大小的模型训练"""
        data_sizes = [50, 100, 200, 500]
        training_results = []

        for size in data_sizes:
            training_data = create_training_data(size)
            model = PoissonModel(f"size_test_{size}")

            start_time = datetime.now()
            training_result = model.train(training_data)
            end_time = datetime.now()

            actual_training_time = (end_time - start_time).total_seconds()

            training_results.append(
                {
                    "data_size": size,
                    "training_time": training_result.training_time,
                    "actual_time": actual_training_time,
                    "accuracy": training_result.accuracy,
                    "team_count": len(model.team_attack_strength),
                }
            )

            # 验证基本训练结果
            assert model.is_trained
            assert training_result.training_samples == size
            assert training_result.accuracy > 0.0

        # 分析训练时间随数据大小的变化
        print("✅ 不同数据大小训练测试完成:")
        for result in training_results:
            print(
                f"  数据量={result['data_size']}, 训练时间={result['training_time']:.2f}s, "
                f"实际时间={result['actual_time']:.2f}s, 准确率={result['accuracy']:.3f}"
            )

    def test_model_training_error_handling(self):
        """测试模型训练错误处理"""
        model = PoissonModel("error_test")

        # 测试空数据
        empty_data = pd.DataFrame()
        with pytest.raises(ValueError, match="Invalid training data"):
            model.train(empty_data)

        # 测试缺少必要列的数据
        invalid_data = pd.DataFrame(
            {
                "home_team": ["Team_A", "Team_B"],
                "away_team": ["Team_C", "Team_D"],
                # 缺少 score 和 result 列
            }
        )
        with pytest.raises(ValueError, match="Invalid training data"):
            model.train(invalid_data)

        # 测试数据量不足
        small_data = pd.DataFrame(
            {
                "home_team": ["Team_A"],
                "away_team": ["Team_B"],
                "home_score": [1],
                "away_score": [0],
                "result": ["home_win"],
            }
        )
        # 应该能训练但会有警告
        training_result = model.train(small_data)
        assert training_result.training_samples == 1

        print("✅ 错误处理测试通过")

    def test_model_training_progress_tracking(self):
        """测试模型训练进度跟踪"""
        training_data = create_training_data(100)
        model = PoissonModel("progress_test")

        # 验证初始状态
        assert len(model.training_history) == 0
        assert model.last_training_time is None

        # 训练模型
        training_result = model.train(training_data)

        # 验证训练状态更新
        assert model.is_trained
        assert model.last_training_time is not None
        assert isinstance(model.last_training_time, datetime)

        # 验证模型信息
        model_info = model.get_model_info()
        assert model_info["model_name"] == "PoissonModel"
        assert model_info["is_trained"] is True
        assert (
            model_info["feature_count"] == 4
        )  # home_attack, home_defense, away_attack, away_defense
        assert "hyperparameters" in model_info

        print("✅ 训练进度跟踪测试通过")


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模块导入失败")
@pytest.mark.unit
@pytest.mark.ml
@pytest.mark.asyncio
class TestAsyncModelTraining:
    """异步模型训练测试"""

    async def test_async_model_trainer_workflow(self):
        """测试异步模型训练器工作流"""
        # 创建训练数据
        training_data = create_training_data(200)
        target_column = "result"
        feature_columns = ["home_team", "away_team", "home_score", "away_score"]

        # 创建训练器
        config = TrainingConfig()
        config.model_type = ModelType.RANDOM_FOREST
        config.epochs = 5  # 减少epoch以加快测试

        trainer = ModelTrainer(config)

        # 准备数据
        X_train, X_test, y_train, y_test = await trainer.prepare_data(
            training_data, target_column, feature_columns
        )

        assert len(X_train) > 0
        assert len(X_test) > 0
        assert len(y_train) == len(X_train)
        assert len(y_test) == len(X_test)

        # 训练模型
        training_result = await trainer.train(X_train, y_train, X_test, y_test)

        assert training_result["status"] == "completed"
        assert "model_name" in training_result
        assert "training_time" in training_result
        assert "metrics" in training_result

        # 评估模型
        evaluation_metrics = await trainer.evaluate(X_test, y_test)

        assert "accuracy" in evaluation_metrics
        assert "precision" in evaluation_metrics
        assert "recall" in evaluation_metrics
        assert "f1_score" in evaluation_metrics

        # 获取训练摘要
        summary = trainer.get_training_summary()
        assert summary["status"] == "completed"
        assert summary["training_epochs"] > 0
        assert summary["model_name"] is not None

        print(f"✅ 异步训练器测试完成: 准确率={evaluation_metrics['accuracy']:.3f}")

    async def test_async_model_save_load(self):
        """测试异步模型保存和加载"""
        # 创建数据
        training_data = create_training_data(100)
        target_column = "result"
        feature_columns = ["home_team", "away_team", "home_score", "away_score"]

        # 创建训练器
        trainer = ModelTrainer()
        X_train, X_test, y_train, y_test = await trainer.prepare_data(
            training_data, target_column, feature_columns
        )

        # 训练模型
        await trainer.train(X_train, y_train)

        # 保存模型
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pkl") as tmp_file:
            model_path = tmp_file.name

        try:
            save_success = await trainer.save_model(model_path)
            assert save_success
            assert os.path.exists(model_path)

            # 创建新的训练器并加载模型
            new_trainer = ModelTrainer()
            load_success = await new_trainer.load_model(model_path)
            assert load_success
            assert new_trainer.model is not None

            print("✅ 异步模型保存加载测试通过")

        finally:
            if os.path.exists(model_path):
                os.unlink(model_path)

    async def test_concurrent_model_training(self):
        """测试并发模型训练"""
        # 创建数据
        training_data = create_training_data(150)
        target_column = "result"
        feature_columns = ["home_team", "away_team", "home_score", "away_score"]

        async def train_model(model_id: int):
            config = TrainingConfig()
            config.model_type = ModelType.RANDOM_FOREST
            config.epochs = 3  # 减少epoch以加快测试

            trainer = ModelTrainer(config)
            X_train, X_test, y_train, y_test = await trainer.prepare_data(
                training_data, target_column, feature_columns
            )

            result = await trainer.train(X_train, y_train, X_test, y_test)
            return model_id, result

        # 并发训练多个模型
        tasks = [train_model(i) for i in range(3)]
        results = await asyncio.gather(*tasks)

        # 验证结果
        assert len(results) == 3
        for model_id, result in results:
            assert result["status"] == "completed"
            assert "model_name" in result

        print(f"✅ 并发模型训练测试通过: 训练了{len(results)}个模型")


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模块导入失败")
@pytest.mark.unit
@pytest.mark.ml
class TestMLModelIntegration:
    """ML模型集成测试"""

    def test_end_to_end_prediction_pipeline(self):
        """测试端到端预测流水线"""
        # 1. 创建训练数据
        training_data = create_training_data(300)
        test_matches = [
            {
                "home_team": training_data["home_team"].iloc[0],
                "away_team": training_data["away_team"].iloc[1],
                "match_id": "pipeline_test_001",
            },
            {
                "home_team": training_data["home_team"].iloc[2],
                "away_team": training_data["away_team"].iloc[3],
                "match_id": "pipeline_test_002",
            },
        ]

        # 2. 训练模型
        model = PoissonModel("pipeline_test")
        training_result = model.train(training_data)

        # 3. 批量预测
        predictions = []
        for match in test_matches:
            prediction = model.predict(match)
            predictions.append(prediction)

        # 4. 验证预测结果
        assert len(predictions) == len(test_matches)
        for i, prediction in enumerate(predictions):
            assert prediction.match_id == test_matches[i]["match_id"]
            assert (
                abs(
                    prediction.home_win_prob
                    + prediction.draw_prob
                    + prediction.away_win_prob
                    - 1.0
                )
                < 0.01
            )
            assert prediction.confidence > 0.0

        # 5. 评估模型在测试数据上的表现
        test_data = create_test_data(50)
        evaluation_metrics = model.evaluate(test_data)

        assert evaluation_metrics["accuracy"] > 0.0
        assert evaluation_metrics["f1_score"] > 0.0

        print(
            f"✅ 端到端流水线测试完成: 训练准确率={training_result.accuracy:.3f}, "
            f"测试准确率={evaluation_metrics['accuracy']:.3f}"
        )

    def test_model_ensemble_prediction(self):
        """测试模型集成预测"""
        # 创建训练数据
        training_data = create_training_data(200)

        # 训练多个具有不同超参数的模型
        models = []
        hyperparams = [
            {"home_advantage": 0.1},
            {"home_advantage": 0.3},
            {"home_advantage": 0.5},
        ]

        for i, params in enumerate(hyperparams):
            model = PoissonModel(f"ensemble_model_{i}")
            model.update_hyperparameters(**params)
            model.train(training_data)
            models.append(model)

        # 测试比赛
        test_match = {
            "home_team": training_data["home_team"].iloc[0],
            "away_team": training_data["away_team"].iloc[1],
            "match_id": "ensemble_test",
        }

        # 集成预测（简单平均）
        ensemble_probs = [0.0, 0.0, 0.0]  # [home_win, draw, away_win]
        individual_predictions = []

        for model in models:
            prediction = model.predict(test_match)
            individual_predictions.append(prediction)
            ensemble_probs[0] += prediction.home_win_prob
            ensemble_probs[1] += prediction.draw_prob
            ensemble_probs[2] += prediction.away_win_prob

        # 平均概率
        ensemble_probs = [p / len(models) for p in ensemble_probs]

        # 验证集成预测
        assert abs(sum(ensemble_probs) - 1.0) < 0.01
        assert all(0 <= p <= 1 for p in ensemble_probs)

        # 计算集成置信度
        max_prob = max(ensemble_probs)
        ensemble_confidence = max_prob

        print(
            f"✅ 集成预测测试完成: 集成置信度={ensemble_confidence:.3f}, "
            f"模型数量={len(models)}"
        )

    def test_model_performance_comparison(self):
        """测试模型性能比较"""
        # 创建训练和测试数据
        training_data = create_training_data(300)
        test_data = create_test_data(100)

        # 不同配置的模型
        model_configs = [
            {"name": "conservative", "home_advantage": 0.1, "min_matches_per_team": 15},
            {"name": "balanced", "home_advantage": 0.3, "min_matches_per_team": 10},
            {"name": "aggressive", "home_advantage": 0.5, "min_matches_per_team": 5},
        ]

        results = []

        for config in model_configs:
            model = PoissonModel(f"comparison_{config['name']}")
            model.update_hyperparameters(
                home_advantage=config["home_advantage"],
                min_matches_per_team=config["min_matches_per_team"],
            )

            # 训练
            training_result = model.train(training_data)

            # 评估
            evaluation_metrics = model.evaluate(test_data)

            results.append(
                {
                    "config": config["name"],
                    "training_accuracy": training_result.accuracy,
                    "test_accuracy": evaluation_metrics["accuracy"],
                    "precision": evaluation_metrics["precision"],
                    "recall": evaluation_metrics["recall"],
                    "f1_score": evaluation_metrics["f1_score"],
                    "training_time": training_result.training_time,
                }
            )

        # 验证结果差异
        test_accuracies = [r["test_accuracy"] for r in results]
        assert len(set(acc for acc in test_accuracies)) > 1  # 至少有两个不同的准确率

        # 找到最佳模型
        best_model = max(results, key=lambda x: x["test_accuracy"])

        print("✅ 模型比较测试完成:")
        for result in results:
            print(
                f"  {result['config']}: 测试准确率={result['test_accuracy']:.3f}, "
                f"F1分数={result['f1_score']:.3f}"
            )
        print(f"最佳模型: {best_model['config']}")

    def test_model_robustness_testing(self):
        """测试模型鲁棒性"""
        # 创建训练数据
        training_data = create_training_data(200)
        model = PoissonModel("robustness_test")
        model.train(training_data)

        # 测试边界情况
        edge_cases = [
            # 强队 vs 弱队
            {
                "home_team": training_data["home_team"].iloc[0],
                "away_team": training_data["away_team"].iloc[-1],
                "match_id": "strong_vs_weak",
            },
            # 相同队伍（应该失败）
            {"home_team": "Team_A", "away_team": "Team_A", "match_id": "same_team"},
            # 未知队伍
            {
                "home_team": "Unknown_Team_X",
                "away_team": "Unknown_Team_Y",
                "match_id": "unknown_teams",
            },
        ]

        results = []

        for case in edge_cases:
            try:
                prediction = model.predict(case)
                results.append(
                    {
                        "case": case["match_id"],
                        "success": True,
                        "prediction": prediction,
                    }
                )
            except Exception as e:
                results.append(
                    {"case": case["match_id"], "success": False, "error": str(e)}
                )

        # 验证结果
        successful_predictions = [r for r in results if r["success"]]
        failed_predictions = [r for r in results if not r["success"]]

        # 至少应该有一些成功的预测
        assert len(successful_predictions) > 0

        # 相同队伍应该失败
        same_team_result = next(r for r in results if r["case"] == "same_team")
        assert not same_team_result["success"]

        print(
            f"✅ 鲁棒性测试完成: 成功预测={len(successful_predictions)}, "
            f"失败预测={len(failed_predictions)}"
        )


# 测试工具函数
def create_mock_training_data_with_noise(
    num_matches: int = 200, noise_level: float = 0.1
) -> pd.DataFrame:
    """创建带噪声的模拟训练数据"""
    data = create_training_data(num_matches)

    # 添加噪声
    if noise_level > 0:
        for col in ["home_score", "away_score"]:
            noise = np.random.normal(0, noise_level, len(data))
            data[col] = np.clip(data[col] + noise, 0, None).astype(int)

    return data


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模块导入失败")
@pytest.mark.unit
@pytest.mark.ml
class TestMLModelPerformanceMetrics:
    """ML模型性能指标测试"""

    def test_comprehensive_model_evaluation(self):
        """测试全面模型评估"""
        # 创建高质量训练数据
        training_data = create_mock_training_data_with_noise(300, noise_level=0.05)
        test_data = create_mock_training_data_with_noise(100, noise_level=0.05)

        # 训练模型
        model = PoissonModel("evaluation_test")
        training_result = model.train(training_data)

        # 全面评估
        evaluation_metrics = model.evaluate(test_data)

        # 验证所有必要指标
        required_metrics = [
            "accuracy",
            "precision",
            "recall",
            "f1_score",
            "confusion_matrix",
        ]
        for metric in required_metrics:
            assert metric in evaluation_metrics
            assert evaluation_metrics[metric] is not None

        # 验证指标范围
        assert 0 <= evaluation_metrics["accuracy"] <= 1
        assert 0 <= evaluation_metrics["precision"] <= 1
        assert 0 <= evaluation_metrics["recall"] <= 1
        assert 0 <= evaluation_metrics["f1_score"] <= 1

        # 验证混淆矩阵
        cm = evaluation_metrics["confusion_matrix"]
        assert isinstance(cm, list)
        assert len(cm) > 0

        print(
            f"✅ 全面模型评估完成: 准确率={evaluation_metrics['accuracy']:.3f}, "
            f"F1分数={evaluation_metrics['f1_score']:.3f}"
        )

    def test_training_stability_analysis(self):
        """测试训练稳定性分析"""
        # 创建多个相似的训练数据集
        base_data = create_training_data(200)
        stability_results = []

        for i in range(5):
            # 轻微扰动数据
            perturbed_data = base_data.copy()
            perturbed_data["home_score"] = np.clip(
                perturbed_data["home_score"]
                + np.random.choice([-1, 0, 1], len(perturbed_data)),
                0,
                None,
            )
            perturbed_data["away_score"] = np.clip(
                perturbed_data["away_score"]
                + np.random.choice([-1, 0, 1], len(perturbed_data)),
                0,
                None,
            )

            # 重新计算结果
            for idx, row in perturbed_data.iterrows():
                if row["home_score"] > row["away_score"]:
                    perturbed_data.loc[idx, "result"] = "home_win"
                elif row["home_score"] < row["away_score"]:
                    perturbed_data.loc[idx, "result"] = "away_win"
                else:
                    perturbed_data.loc[idx, "result"] = "draw"

            # 训练模型
            model = PoissonModel(f"stability_test_{i}")
            training_result = model.train(perturbed_data)
            stability_results.append(training_result.accuracy)

        # 分析稳定性
        mean_accuracy = np.mean(stability_results)
        std_accuracy = np.std(stability_results)
        min_accuracy = np.min(stability_results)
        max_accuracy = np.max(stability_results)

        # 验证稳定性（标准差不应太大）
        assert std_accuracy < 0.2  # 标准差应该小于0.2

        print("✅ 训练稳定性分析完成:")
        print(f"  平均准确率: {mean_accuracy:.3f} ± {std_accuracy:.3f}")
        print(f"  准确率范围: [{min_accuracy:.3f}, {max_accuracy:.3f}]")
        print(f"  变异系数: {std_accuracy/mean_accuracy:.3f}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
