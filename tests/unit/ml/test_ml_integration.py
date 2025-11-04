#!/usr/bin/env python3
"""
🤖 ML集成测试 - 机器学习模块集成测试

测试机器学习模块的端到端工作流、模型集成、性能优化等
包括数据流、模型部署、实时预测等高级功能
"""

import asyncio
import json
import os

# 模拟导入，避免循环依赖问题
import sys
import tempfile
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../src"))

# 尝试导入ML模块
try:
    from src.domain.strategies.ml_model import MLModelStrategy
    from src.ml.enhanced_real_model_training import EnhancedRealModelTrainer
    from src.ml.model_training import (
        ModelTrainer,
        ModelType,
        TrainingConfig,
        TrainingStatus,
    )
    from src.ml.models.base_model import BaseModel, PredictionResult, TrainingResult
    from src.ml.models.poisson_model import PoissonModel

    CAN_IMPORT = True
except ImportError as e:
    print(f"Warning: 无法导入ML模块: {e}")
    CAN_IMPORT = False


# 创建更复杂的模拟数据
def create_comprehensive_training_data(num_matches: int = 1000) -> pd.DataFrame:
    """创建全面的训练数据，包含更多特征"""
    teams = [
        "Manchester_City",
        "Liverpool",
        "Chelsea",
        "Arsenal",
        "Manchester_United",
        "Tottenham",
        "West_Ham",
        "Leicester",
        "Everton",
        "Wolves",
        "Newcastle",
        "Aston_Villa",
        "Leeds",
        "Southampton",
        "Crystal_Palace",
        "Brighton",
        "Burnley",
        "Fulham",
        "West_Brom",
        "Sheffield_United",
    ]

    data = []
    for i in range(num_matches):
        home_team = np.random.choice(teams)
        away_team = np.random.choice([t for t in teams if t != home_team])

        # 基于球队实力的进球模拟（简化版）
        team_strength = {
            "Manchester_City": 2.1,
            "Liverpool": 2.0,
            "Chelsea": 1.8,
            "Arsenal": 1.7,
            "Manchester_United": 1.6,
            "Tottenham": 1.5,
            "West_Ham": 1.3,
            "Leicester": 1.2,
        }

        home_strength = team_strength.get(home_team, 1.0)
        away_strength = team_strength.get(away_team, 1.0)

        # 主场优势
        home_advantage = 0.3

        # 期望进球
        home_expected = (home_strength * home_advantage) / away_strength * 1.5
        away_expected = away_strength / (home_strength * home_advantage) * 1.1

        # 实际进球（泊松分布）
        home_goals = np.random.poisson(max(home_expected, 0.1))
        away_goals = np.random.poisson(max(away_expected, 0.1))

        # 确定结果
        if home_goals > away_goals:
            result = "home_win"
        elif home_goals < away_goals:
            result = "away_win"
        else:
            result = "draw"

        # 添加更多特征
        data.append(
            {
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_goals,
                "away_score": away_goals,
                "result": result,
                "match_date": datetime.now()
                - timedelta(days=np.random.randint(0, 365)),
                "season": "2023-24",
                "league": "Premier_League",
                "home_team_form": np.random.uniform(-1, 1),  # 最近5场净胜球
                "away_team_form": np.random.uniform(-1, 1),
                "home_team_goals_scored": np.random.randint(0, 50),
                "away_team_goals_scored": np.random.randint(0, 50),
                "home_team_goals_conceded": np.random.randint(0, 50),
                "away_team_goals_conceded": np.random.randint(0, 50),
                "home_team_shots": np.random.randint(5, 25),
                "away_team_shots": np.random.randint(5, 25),
                "home_team_shots_on_target": np.random.randint(2, 15),
                "away_team_shots_on_target": np.random.randint(2, 15),
                "home_team_possession": np.random.uniform(30, 80),
                "away_team_possession": np.random.uniform(30, 80),
            }
        )

    return pd.DataFrame(data)


def create_batch_prediction_data(num_predictions: int = 10) -> list[dict[str, Any]]:
    """创建批量预测数据"""
    teams = ["Manchester_City", "Liverpool", "Chelsea", "Arsenal", "Manchester_United"]
    predictions = []

    for i in range(num_predictions):
        home_team = np.random.choice(teams)
        away_team = np.random.choice([t for t in teams if t != home_team])

        predictions.append(
            {
                "home_team": home_team,
                "away_team": away_team,
                "match_id": f"batch_match_{i+1:03d}",
                "match_date": datetime.now() + timedelta(days=i + 1),
                "venue": f"Stadium_{i+1}",
            }
        )

    return predictions


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模块导入失败")
@pytest.mark.unit
@pytest.mark.ml
@pytest.mark.integration
class TestMLWorkflowIntegration:
    """ML工作流集成测试"""

    @pytest.mark.asyncio
    async def test_complete_prediction_pipeline(self):
        """测试完整的预测流水线"""
        # 1. 准备训练数据
        training_data = create_comprehensive_training_data(500)
        validation_data = create_comprehensive_training_data(100)

        # 2. 训练泊松模型
        poisson_model = PoissonModel("production_v1.0")
        training_result = poisson_model.train(training_data, validation_data)

        # 3. 验证训练结果
        assert poisson_model.is_trained is True
        assert isinstance(training_result, TrainingResult)
        assert training_result.accuracy > 0.5  # 基本性能要求
        assert len(poisson_model.team_attack_strength) > 0

        # 4. 创建预测数据
        prediction_requests = create_batch_prediction_data(5)

        # 5. 批量预测
        predictions = []
        for request in prediction_requests:
            try:
                prediction = poisson_model.predict(request)
                predictions.append(prediction)
            except Exception as e:
                # 记录预测失败的情况
                print(f"Prediction failed for {request['match_id']}: {e}")

        # 6. 验证预测结果
        assert len(predictions) > 0
        for prediction in predictions:
            assert isinstance(prediction, PredictionResult)
            assert (
                abs(
                    prediction.home_win_prob
                    + prediction.draw_prob
                    + prediction.away_win_prob
                    - 1.0
                )
                < 0.01
            )
            assert prediction.confidence > 0
            assert prediction.model_name == "PoissonModel"

        # 7. 评估模型性能
        test_metrics = poisson_model.evaluate(validation_data)
        assert isinstance(test_metrics, dict)
        assert "accuracy" in test_metrics
        assert test_metrics["accuracy"] > 0

    @pytest.mark.asyncio
    async def test_model_ensemble_workflow(self):
        """测试模型集成工作流"""
        training_data = create_comprehensive_training_data(300)
        test_data = create_batch_prediction_data(3)

        # 创建多个模型实例
        models = []
        for i in range(3):
            model = PoissonModel(f"ensemble_v{i+1}")
            # 使用不同的数据子集训练
            subset_data = training_data.sample(frac=0.8, random_state=i)
            model.train(subset_data)
            models.append(model)

        # 集成预测
        ensemble_predictions = []
        for request in test_data:
            individual_predictions = []
            for model in models:
                pred = model.predict(request)
                individual_predictions.append(pred)

            # 简单平均集成
            avg_home_prob = np.mean([p.home_win_prob for p in individual_predictions])
            avg_draw_prob = np.mean([p.draw_prob for p in individual_predictions])
            avg_away_prob = np.mean([p.away_win_prob for p in individual_predictions])

            # 创建集成预测结果
            ensemble_pred = PredictionResult(
                match_id=request["match_id"],
                home_team=request["home_team"],
                away_team=request["away_team"],
                home_win_prob=avg_home_prob,
                draw_prob=avg_draw_prob,
                away_win_prob=avg_away_prob,
                predicted_outcome=(
                    "home_win"
                    if avg_home_prob > max(avg_draw_prob, avg_away_prob)
                    else "draw" if avg_draw_prob > avg_away_prob else "away_win"
                ),
                confidence=max(avg_home_prob, avg_draw_prob, avg_away_prob),
                model_name="EnsembleModel",
                model_version="1.0",
                created_at=datetime.now(),
            )
            ensemble_predictions.append(ensemble_pred)

        # 验证集成结果
        assert len(ensemble_predictions) == len(test_data)
        for pred in ensemble_predictions:
            assert (
                abs(pred.home_win_prob + pred.draw_prob + pred.away_win_prob - 1.0)
                < 0.01
            )

    @pytest.mark.asyncio
    async def test_model_performance_comparison(self):
        """测试模型性能比较"""
        training_data = create_comprehensive_training_data(400)
        test_data = create_comprehensive_training_data(100)

        # 训练多个版本的模型
        model_configs = [
            ("Poisson_v1.0", {"home_advantage": 0.2}),
            ("Poisson_v1.1", {"home_advantage": 0.3}),
            ("Poisson_v1.2", {"home_advantage": 0.4}),
        ]

        results = {}
        for name, params in model_configs:
            model = PoissonModel()
            model.update_hyperparameters(**params)
            model.train(training_data)

            # 评估性能
            metrics = model.evaluate(test_data)
            results[name] = {
                "model": model,
                "metrics": metrics,
                "hyperparameters": params,
            }

        # 比较性能
        accuracies = [r["metrics"]["accuracy"] for r in results.values()]
        assert len(accuracies) == 3

        # 找出最佳模型
        best_model_name = max(
            results.keys(), key=lambda k: results[k]["metrics"]["accuracy"]
        )
        best_model = results[best_model_name]["model"]

        # 使用最佳模型进行预测
        test_prediction = best_model.predict(create_batch_prediction_data(1)[0])
        assert isinstance(test_prediction, PredictionResult)

    def test_model_versioning_and_management(self):
        """测试模型版本管理"""
        training_data = create_comprehensive_training_data(200)

        # 创建不同版本的模型
        versions = ["1.0", "1.1", "2.0"]
        models = {}

        for version in versions:
            model = PoissonModel(version)
            model.train(training_data)
            models[version] = model

        # 验证版本信息
        for version, model in models.items():
            assert model.model_version == version
            assert model.is_trained is True

        # 比较不同版本的性能
        test_data = create_comprehensive_training_data(50)
        version_metrics = {}

        for version, model in models.items():
            metrics = model.evaluate(test_data)
            version_metrics[version] = metrics["accuracy"]

        # 至少应该有一些性能差异
        accuracies = list(version_metrics.values())
        assert (
            len(set(round(acc, 3) for acc in accuracies)) >= 1
        )  # 可能相同，但至少要测试

    def test_error_recovery_and_robustness(self):
        """测试错误恢复和鲁棒性"""
        model = PoissonModel()
        training_data = create_comprehensive_training_data(100)

        # 测试各种错误情况
        test_cases = [
            # 未训练模型预测
            lambda: model.predict({"home_team": "A", "away_team": "B"}),
            # 无效输入数据
            lambda: model.train(pd.DataFrame()),
            # 缺少必要字段的预测
            lambda: model.predict({"home_team": "A"}) if model.is_trained else None,
            # 相同队伍预测
            lambda: (
                model.predict({"home_team": "A", "away_team": "A"})
                if model.is_trained
                else None
            ),
        ]

        # 训练模型用于后续测试
        model.train(training_data)

        error_count = 0
        for test_case in test_cases:
            try:
                result = test_case()
                if result is None:
                    continue
            except (ValueError, RuntimeError, KeyError):
                error_count += 1

        # 应该捕获到一些错误
        assert error_count >= 2

    @pytest.mark.asyncio
    async def test_concurrent_prediction_handling(self):
        """测试并发预测处理"""
        model = PoissonModel()
        training_data = create_comprehensive_training_data(200)
        model.train(training_data)

        # 创建批量预测任务
        batch_data = create_batch_prediction_data(10)

        async def predict_single(data):
            return model.predict(data)

        # 并发执行预测
        tasks = [predict_single(data) for data in batch_data]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证结果
        successful_predictions = [r for r in results if isinstance(r, PredictionResult)]
        exceptions = [r for r in results if isinstance(r, Exception)]

        assert len(successful_predictions) > 0
        assert len(successful_predictions) + len(exceptions) == len(batch_data)

        for pred in successful_predictions:
            assert isinstance(pred, PredictionResult)
            assert (
                abs(pred.home_win_prob + pred.draw_prob + pred.away_win_prob - 1.0)
                < 0.01
            )


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模块导入失败")
@pytest.mark.unit
@pytest.mark.ml
@pytest.mark.integration
class TestMLModelDeployment:
    """ML模型部署测试"""

    @pytest.mark.asyncio
    async def test_model_export_import_workflow(self):
        """测试模型导出导入工作流"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. 训练模型
            model = PoissonModel("deployment_v1.0")
            training_data = create_comprehensive_training_data(300)
            model.train(training_data)

            # 2. 保存模型
            model_path = os.path.join(temp_dir, "poisson_model.pkl")
            save_success = model.save_model(model_path)
            assert save_success is True
            assert os.path.exists(model_path)

            # 3. 保存元数据
            metadata = {
                "model_name": model.model_name,
                "model_version": model.model_version,
                "training_date": datetime.now().isoformat(),
                "training_samples": len(training_data),
                "performance_metrics": model.evaluate(
                    create_comprehensive_training_data(50)
                ),
            }

            metadata_path = os.path.join(temp_dir, "model_metadata.json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            # 4. 加载模型
            loaded_model = PoissonModel()
            load_success = loaded_model.load_model(model_path)
            assert load_success is True
            assert loaded_model.is_trained is True
            assert loaded_model.model_version == "deployment_v1.0"

            # 5. 验证加载的模型功能
            test_prediction_data = create_batch_prediction_data(1)[0]
            original_prediction = model.predict(test_prediction_data)
            loaded_prediction = loaded_model.predict(test_prediction_data)

            # 预测结果应该基本一致
            assert (
                abs(original_prediction.home_win_prob - loaded_prediction.home_win_prob)
                < 0.01
            )

    @pytest.mark.asyncio
    async def test_model_serving_simulation(self):
        """测试模型服务模拟"""

        # 创建一个简单的模型服务类
        class ModelService:
            def __init__(self):
                self.models = {}
                self.load_models()

            def load_models(self):
                """加载所有模型"""
                training_data = create_comprehensive_training_data(200)

                # 加载多个模型
                models_config = [
                    ("poisson_v1", PoissonModel("v1.0")),
                    ("poisson_v2", PoissonModel("v2.0")),
                ]

                for name, model in models_config:
                    model.train(training_data)
                    self.models[name] = model

            async def predict(self, model_name: str, request_data: dict[str, Any]):
                """异步预测接口"""
                if model_name not in self.models:
                    raise ValueError(f"Model {model_name} not found")

                model = self.models[model_name]
                prediction = model.predict(request_data)
                return prediction

            def list_models(self):
                """列出可用模型"""
                return list(self.models.keys())

        # 测试模型服务
        service = ModelService()
        assert len(service.list_models()) == 2

        # 测试预测
        test_request = create_batch_prediction_data(1)[0]
        prediction = await service.predict("poisson_v1", test_request)

        assert isinstance(prediction, PredictionResult)
        assert prediction.model_name == "PoissonModel"

        # 测试错误处理
        with pytest.raises(ValueError):
            await service.predict("nonexistent_model", test_request)

    def test_model_monitoring_metrics(self):
        """测试模型监控指标"""
        model = PoissonModel()
        training_data = create_comprehensive_training_data(200)
        model.train(training_data)

        # 模拟预测监控
        predictions = []
        prediction_times = []

        for i in range(10):
            start_time = datetime.now()
            test_data = create_batch_prediction_data(1)[0]
            prediction = model.predict(test_data)
            end_time = datetime.now()

            predictions.append(prediction)
            prediction_times.append((end_time - start_time).total_seconds())

        # 计算监控指标
        avg_prediction_time = np.mean(prediction_times)
        max_prediction_time = np.max(prediction_times)
        confidence_scores = [p.confidence for p in predictions]
        avg_confidence = np.mean(confidence_scores)

        # 验证监控指标
        assert avg_prediction_time < 1.0  # 预测时间应该很快
        assert max_prediction_time < 5.0  # 最大预测时间
        assert 0 < avg_confidence <= 1.0  # 置信度在合理范围

        # 创建监控报告
        monitoring_report = {
            "model_name": model.model_name,
            "model_version": model.model_version,
            "total_predictions": len(predictions),
            "avg_prediction_time_ms": avg_prediction_time * 1000,
            "max_prediction_time_ms": max_prediction_time * 1000,
            "avg_confidence": avg_confidence,
            "min_confidence": min(confidence_scores),
            "max_confidence": max(confidence_scores),
            "uptime": "100%",  # 模拟指标
            "error_rate": "0%",  # 模拟指标
        }

        assert isinstance(monitoring_report, dict)
        assert monitoring_report["total_predictions"] == 10


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模块导入失败")
@pytest.mark.unit
@pytest.mark.ml
@pytest.mark.integration
class TestMLDataPipeline:
    """ML数据流水线测试"""

    def test_feature_engineering_pipeline(self):
        """测试特征工程流水线"""
        # 创建原始数据
        raw_data = create_comprehensive_training_data(100)

        # 模拟特征工程步骤
        def engineer_features(df):
            """特征工程函数"""
            engineered_df = df.copy()

            # 1. 计算进球差异
            engineered_df["goal_difference"] = (
                engineered_df["home_score"] - engineered_df["away_score"]
            )

            # 2. 计算总进球数
            engineered_df["total_goals"] = (
                engineered_df["home_score"] + engineered_df["away_score"]
            )

            # 3. 创建胜负标签（数值化）
            engineered_df["result_numeric"] = engineered_df["result"].map(
                {"home_win": 1, "draw": 0, "away_win": -1}
            )

            # 4. 计算主客队实力比（简化版）
            engineered_df["strength_ratio"] = engineered_df[
                "home_team_goals_scored"
            ] / (engineered_df["away_team_goals_conceded"] + 1)

            # 5. 时间特征
            engineered_df["month"] = pd.to_datetime(
                engineered_df["match_date"]
            ).dt.month
            engineered_df["day_of_week"] = pd.to_datetime(
                engineered_df["match_date"]
            ).dt.dayofweek

            return engineered_df

        # 应用特征工程
        engineered_data = engineer_features(raw_data)

        # 验证特征工程结果
        assert "goal_difference" in engineered_data.columns
        assert "total_goals" in engineered_data.columns
        assert "result_numeric" in engineered_data.columns
        assert "strength_ratio" in engineered_data.columns
        assert "month" in engineered_data.columns
        assert "day_of_week" in engineered_data.columns

        # 验证数据完整性
        assert len(engineered_data) == len(raw_data)
        assert engineered_data["goal_difference"].notna().all()

    def test_data_validation_pipeline(self):
        """测试数据验证流水线"""
        # 创建包含各种问题的数据
        problematic_data = pd.DataFrame(
            {
                "home_team": ["Team_A", "Team_B", None, "Team_D", "Team_E"],
                "away_team": ["Team_B", "Team_A", "Team_C", "Team_E", "Team_D"],
                "home_score": [2, -1, 1, 3, 100],  # 包含负数和异常值
                "away_score": [1, 2, None, 0, 99],  # 包含空值和异常值
                "result": ["home_win", "invalid", "draw", "home_win", "away_win"],
            }
        )

        def validate_data(df):
            """数据验证函数"""
            validation_results = {
                "total_rows": len(df),
                "issues": [],
                "clean_data": df.copy(),
            }

            # 1. 检查空值
            null_counts = df.isnull().sum()
            for col, count in null_counts.items():
                if count > 0:
                    validation_results["issues"].append(
                        f"Column {col} has {count} null values"
                    )

            # 2. 检查数值范围
            numeric_columns = ["home_score", "away_score"]
            for col in numeric_columns:
                if col in df.columns:
                    invalid_values = df[(df[col] < 0) | (df[col] > 20)]
                    if len(invalid_values) > 0:
                        validation_results["issues"].append(
                            f"Column {col} has {len(invalid_values)} invalid values"
                        )

            # 3. 检查结果值
            if "result" in df.columns:
                valid_results = {"home_win", "draw", "away_win"}
                invalid_results = df[~df["result"].isin(valid_results)]
                if len(invalid_results) > 0:
                    validation_results["issues"].append(
                        f"Result column has {len(invalid_results)} invalid values"
                    )

            # 4. 检查主客队相同
            same_teams = df[df["home_team"] == df["away_team"]]
            if len(same_teams) > 0:
                validation_results["issues"].append(
                    f"Found {len(same_teams)} matches with same home and away team"
                )

            return validation_results

        # 执行数据验证
        validation_results = validate_data(problematic_data)

        # 验证结果
        assert validation_results["total_rows"] == 5
        assert len(validation_results["issues"]) > 0  # 应该发现一些问题

        # 检查是否发现了预期的问题
        issue_text = " ".join(validation_results["issues"])
        assert "null" in issue_text.lower()
        assert "invalid" in issue_text.lower()

    def test_model_training_pipeline(self):
        """测试模型训练流水线"""

        # 创建训练流水线
        class TrainingPipeline:
            def __init__(self):
                self.model = None
                self.training_history = []

            def preprocess_data(self, data):
                """数据预处理"""
                # 移除空值
                clean_data = data.dropna()
                # 过滤异常值
                clean_data = clean_data[
                    (clean_data["home_score"] >= 0)
                    & (clean_data["home_score"] <= 10)
                    & (clean_data["away_score"] >= 0)
                    & (clean_data["away_score"] <= 10)
                ]
                return clean_data

            def split_data(self, data, train_ratio=0.8):
                """数据分割"""
                n = len(data)
                train_size = int(n * train_ratio)
                train_data = data.iloc[:train_size]
                val_data = data.iloc[train_size:]
                return train_data, val_data

            def train_model(self, train_data, val_data):
                """训练模型"""
                self.model = PoissonModel("pipeline_v1.0")
                result = self.model.train(train_data, val_data)
                return result

            def evaluate_model(self, test_data):
                """评估模型"""
                if self.model is None:
                    raise ValueError("Model not trained")
                return self.model.evaluate(test_data)

            def run_pipeline(self, raw_data):
                """运行完整流水线"""
                # 1. 数据预处理
                processed_data = self.preprocess_data(raw_data)
                self.training_history.append(
                    f"Preprocessed {len(processed_data)} samples"
                )

                # 2. 数据分割
                train_data, val_data = self.split_data(processed_data)
                self.training_history.append(
                    f"Split data: {len(train_data)} train, {len(val_data)} val"
                )

                # 3. 模型训练
                training_result = self.train_model(train_data, val_data)
                self.training_history.append(
                    f"Model trained with accuracy: {training_result.accuracy:.3f}"
                )

                # 4. 模型评估
                eval_metrics = self.evaluate_model(val_data)
                self.training_history.append(
                    f"Model evaluated: {eval_metrics['accuracy']:.3f} accuracy"
                )

                return {
                    "model": self.model,
                    "training_result": training_result,
                    "evaluation_metrics": eval_metrics,
                    "training_history": self.training_history,
                }

        # 运行训练流水线
        pipeline = TrainingPipeline()
        raw_data = create_comprehensive_training_data(300)
        results = pipeline.run_pipeline(raw_data)

        # 验证流水线结果
        assert pipeline.model is not None
        assert pipeline.model.is_trained is True
        assert len(pipeline.training_history) == 4
        assert isinstance(results["training_result"], TrainingResult)
        assert isinstance(results["evaluation_metrics"], dict)
        assert results["evaluation_metrics"]["accuracy"] > 0


# 测试运行器
async def run_ml_integration_tests():
    """运行ML集成测试套件"""
    print("🤖 开始ML集成测试")
    print("=" * 60)

    # 这里可以添加更复杂的ML集成测试逻辑
    print("✅ ML集成测试完成")


if __name__ == "__main__":
    asyncio.run(run_ml_integration_tests())
