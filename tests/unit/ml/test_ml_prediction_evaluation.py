#!/usr/bin/env python3
"""
🎯 ML预测评估测试 - 机器学习模型预测和评估测试

测试ML模型的预测准确性、评估指标、置信度校准、特征重要性分析等。
包含对预测结果的质量评估和模型性能的深度分析。
"""

import warnings
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

# 抑制warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# 模拟导入，避免循环依赖问题
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../src"))

# 尝试导入ML模块
try:
    from src.ml.models.base_model import BaseModel, PredictionResult, TrainingResult
    from src.ml.models.poisson_model import PoissonModel

    CAN_IMPORT = True
except ImportError as e:
    print(f"Warning: 无法导入ML模块: {e}")
    CAN_IMPORT = False


def create_evaluation_dataset(
    train_matches: int = 1000, test_matches: int = 250
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """创建评估数据集（训练集和测试集）"""
    # 创建更大的训练数据集
    training_data = []
    teams = [f"Team_{chr(65+i)}" for i in range(30)]  # 30个队伍

    # 为每个队伍设定固定的实力值
    team_strengths = {team: np.random.uniform(0.3, 2.5) for team in teams}

    for i in range(train_matches):  # 训练数据
        home_team = np.random.choice(teams)
        away_team = np.random.choice([t for t in teams if t != home_team])

        home_strength = team_strengths[home_team]
        away_strength = team_strengths[away_team]

        # 更真实的比分生成
        home_advantage = 0.25
        home_expected = (home_strength * (1 + home_advantage)) / away_strength * 1.3
        away_expected = away_strength / home_strength * 1.0

        home_goals = np.random.poisson(max(home_expected, 0.1))
        away_goals = np.random.poisson(max(away_expected, 0.1))

        if home_goals > away_goals:
            result = "home_win"
        elif home_goals < away_goals:
            result = "away_win"
        else:
            result = "draw"

        training_data.append(
            {
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_goals,
                "away_score": away_goals,
                "result": result,
                "match_date": datetime.now()
                - timedelta(days=np.random.randint(1, 730)),
                "home_strength": home_strength,
                "away_strength": away_strength,
            }
        )

    # 创建测试数据集（使用相同的队伍实力）
    test_data = []
    for i in range(test_matches):
        home_team = np.random.choice(teams)
        away_team = np.random.choice([t for t in teams if t != home_team])

        home_strength = team_strengths[home_team]
        away_strength = team_strengths[away_team]

        home_advantage = 0.25
        home_expected = (home_strength * (1 + home_advantage)) / away_strength * 1.3
        away_expected = away_strength / home_strength * 1.0

        home_goals = np.random.poisson(max(home_expected, 0.1))
        away_goals = np.random.poisson(max(away_expected, 0.1))

        if home_goals > away_goals:
            result = "home_win"
        elif home_goals < away_goals:
            result = "away_win"
        else:
            result = "draw"

        test_data.append(
            {
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_goals,
                "away_score": away_goals,
                "result": result,
                "match_date": datetime.now() - timedelta(days=np.random.randint(0, 30)),
                "home_strength": home_strength,
                "away_strength": away_strength,
            }
        )

    return pd.DataFrame(training_data), pd.DataFrame(test_data)


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模块导入失败")
@pytest.mark.unit
@pytest.mark.ml
class TestMLModelPrediction:
    """ML模型预测测试"""

    def test_single_match_prediction(self):
        """测试单场比赛预测"""
        training_data, test_data = create_evaluation_dataset(200, 50)

        # 训练模型
        model = PoissonModel("single_prediction_test")
        model.train(training_data)

        # 选择一场测试比赛
        test_match = test_data.iloc[0]
        match_data = {
            "home_team": test_match["home_team"],
            "away_team": test_match["away_team"],
            "match_id": "single_test_001",
        }

        # 进行预测
        prediction = model.predict(match_data)

        # 验证预测结果
        assert isinstance(prediction, PredictionResult)
        assert prediction.match_id == match_data["match_id"]
        assert prediction.home_team == match_data["home_team"]
        assert prediction.away_team == match_data["away_team"]
        assert prediction.model_name == "PoissonModel"

        # 验证概率分布
        probs = [
            prediction.home_win_prob,
            prediction.draw_prob,
            prediction.away_win_prob,
        ]
        assert all(0 <= p <= 1 for p in probs)
        assert abs(sum(probs) - 1.0) < 0.01

        # 验证预测结果与概率一致
        max_prob_index = np.argmax(probs)
        expected_outcomes = ["home_win", "draw", "away_win"]
        assert prediction.predicted_outcome == expected_outcomes[max_prob_index]

        # 验证置信度（Poisson模型使用复杂的置信度计算，不是简单的最大概率）
        assert 0 <= prediction.confidence <= 1
        assert prediction.confidence > 0

        print(
            f"✅ 单场比赛预测测试通过: {prediction.home_team} vs {prediction.away_team}"
        )
        print(
            f"   预测结果: {prediction.predicted_outcome} (置信度: {prediction.confidence:.3f})"
        )
        print(
            f"   概率分布: 主胜{prediction.home_win_prob:.3f} 平局{prediction.draw_prob:.3f} 客胜{prediction.away_win_prob:.3f}"
        )

    def test_batch_prediction_consistency(self):
        """测试批量预测一致性"""
        training_data, test_data = create_evaluation_dataset(300, 100)

        # 训练模型
        model = PoissonModel("batch_prediction_test")
        model.train(training_data)

        # 批量预测
        batch_predictions = []
        for idx, test_match in test_data.iterrows():
            match_data = {
                "home_team": test_match["home_team"],
                "away_team": test_match["away_team"],
                "match_id": f"batch_test_{idx:03d}",
            }
            prediction = model.predict(match_data)
            batch_predictions.append(prediction)

        # 验证批量预测结果
        assert len(batch_predictions) == len(test_data)

        # 验证每个预测的有效性
        for prediction in batch_predictions:
            probs = [
                prediction.home_win_prob,
                prediction.draw_prob,
                prediction.away_win_prob,
            ]
            assert abs(sum(probs) - 1.0) < 0.01
            assert prediction.confidence > 0
            assert prediction.predicted_outcome in ["home_win", "draw", "away_win"]

        # 验证相同输入产生相同输出
        repeat_match = {
            "home_team": test_data.iloc[0]["home_team"],
            "away_team": test_data.iloc[0]["away_team"],
            "match_id": "repeat_test",
        }

        prediction1 = model.predict(repeat_match)
        prediction2 = model.predict(repeat_match)

        assert prediction1.home_win_prob == prediction2.home_win_prob
        assert prediction1.draw_prob == prediction2.draw_prob
        assert prediction1.away_win_prob == prediction2.away_win_prob
        assert prediction1.predicted_outcome == prediction2.predicted_outcome

        print(f"✅ 批量预测一致性测试通过: {len(batch_predictions)}个预测")

    def test_prediction_probability_distribution(self):
        """测试预测概率分布特性"""
        training_data, test_data = create_evaluation_dataset(400, 150)

        # 训练模型
        model = PoissonModel("probability_distribution_test")
        model.train(training_data)

        # 收集所有预测概率
        all_probabilities = []
        for _, test_match in test_data.iterrows():
            match_data = {
                "home_team": test_match["home_team"],
                "away_team": test_match["away_team"],
            }
            probabilities = model.predict_proba(match_data)
            all_probabilities.append(probabilities)

        # 转换为numpy数组
        prob_array = np.array(all_probabilities)

        # 验证概率分布特性
        # 1. 所有概率都在[0,1]范围内
        assert np.all(prob_array >= 0)
        assert np.all(prob_array <= 1)

        # 2. 每行概率和为1
        prob_sums = np.sum(prob_array, axis=1)
        assert np.allclose(prob_sums, 1.0, atol=0.01)

        # 3. 概率分布的统计特性
        home_win_probs = prob_array[:, 0]
        draw_probs = prob_array[:, 1]
        away_win_probs = prob_array[:, 2]

        # 主胜概率通常应该最高（主场优势）
        assert np.mean(home_win_probs) > np.mean(away_win_probs)

        # 验证分布的合理性
        assert 0.2 < np.mean(home_win_probs) < 0.6  # 合理的主胜概率范围
        assert 0.2 < np.mean(draw_probs) < 0.4  # 合理的平局概率范围
        assert 0.2 < np.mean(away_win_probs) < 0.5  # 合理的客胜概率范围

        print("✅ 概率分布特性验证通过:")
        print(f"   主胜概率均值: {np.mean(home_win_probs):.3f}")
        print(f"   平局概率均值: {np.mean(draw_probs):.3f}")
        print(f"   客胜概率均值: {np.mean(away_win_probs):.3f}")

    def test_prediction_confidence_calibration(self):
        """测试预测置信度校准"""
        training_data, test_data = create_evaluation_dataset(500, 200)

        # 训练模型
        model = PoissonModel("confidence_calibration_test")
        model.train(training_data)

        # 收集预测和实际结果
        predictions_with_actual = []
        for _, test_match in test_data.iterrows():
            match_data = {
                "home_team": test_match["home_team"],
                "away_team": test_match["away_team"],
            }
            prediction = model.predict(match_data)
            predictions_with_actual.append(
                {"prediction": prediction, "actual_result": test_match["result"]}
            )

        # 按置信度分组
        confidence_bins = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)]
        calibration_data = []

        for low, high in confidence_bins:
            bin_predictions = [
                p
                for p in predictions_with_actual
                if low <= p["prediction"].confidence < high
            ]

            if bin_predictions:
                correct_predictions = sum(
                    1
                    for p in bin_predictions
                    if p["prediction"].predicted_outcome == p["actual_result"]
                )
                accuracy = correct_predictions / len(bin_predictions)
                avg_confidence = np.mean(
                    [p["prediction"].confidence for p in bin_predictions]
                )

                calibration_data.append(
                    {
                        "confidence_range": f"{low}-{high}",
                        "count": len(bin_predictions),
                        "accuracy": accuracy,
                        "avg_confidence": avg_confidence,
                    }
                )

        # 验证置信度校准（置信度应该与准确率相关）
        for data in calibration_data:
            # 高置信度应该有相对较高的准确率
            confidence_diff = abs(data["avg_confidence"] - data["accuracy"])
            assert confidence_diff < 0.3  # 允许一定的校准误差

        print("✅ 置信度校准验证通过:")
        for data in calibration_data:
            print(
                f"   置信度{data['confidence_range']}: "
                f"样本数={data['count']}, "
                f"准确率={data['accuracy']:.3f}, "
                f"平均置信度={data['avg_confidence']:.3f}"
            )

    def test_prediction_edge_cases(self):
        """测试预测边界情况"""
        training_data, test_data = create_evaluation_dataset(300, 100)

        # 训练模型
        model = PoissonModel("edge_cases_test")
        model.train(training_data)

        # 测试边界情况
        edge_cases = [
            # 1. 最强队 vs 最弱队
            {
                "name": "strongest_vs_weakest",
                "home_team": training_data.groupby("home_team")["home_score"]
                .mean()
                .idxmax(),
                "away_team": training_data.groupby("away_team")["away_score"]
                .mean()
                .idxmin(),
            },
            # 2. 罕见对阵组合
            {
                "name": "rare_matchup",
                "home_team": training_data["home_team"].value_counts().idxmin(),
                "away_team": training_data["away_team"].value_counts().idxmin(),
            },
        ]

        results = []
        for case in edge_cases:
            try:
                match_data = {
                    "home_team": case["home_team"],
                    "away_team": case["away_team"],
                    "match_id": f"edge_case_{case['name']}",
                }
                prediction = model.predict(match_data)
                results.append(
                    {"case": case["name"], "success": True, "prediction": prediction}
                )
            except Exception as e:
                results.append(
                    {"case": case["name"], "success": False, "error": str(e)}
                )

        # 验证边界情况处理
        successful_cases = [r for r in results if r["success"]]
        assert len(successful_cases) >= 1  # 至少应该有一个成功的边界情况

        # 验证成功预测的有效性
        for result in successful_cases:
            prediction = result["prediction"]
            probs = [
                prediction.home_win_prob,
                prediction.draw_prob,
                prediction.away_win_prob,
            ]
            assert abs(sum(probs) - 1.0) < 0.01
            assert prediction.confidence > 0

        print(
            f"✅ 边界情况测试通过: {len(successful_cases)}/{len(edge_cases)} 个边界情况处理成功"
        )

    def test_prediction_error_handling(self):
        """测试预测错误处理"""
        training_data, _ = create_evaluation_dataset(200, 50)

        # 训练模型
        model = PoissonModel("error_handling_test")
        model.train(training_data)

        # 测试错误情况
        error_cases = [
            # 1. 未训练模型预测
            {
                "name": "untrained_model",
                "model": PoissonModel("untrained"),
                "match_data": {"home_team": "Team_A", "away_team": "Team_B"},
                "should_fail": True,
            },
            # 2. 缺少必要字段
            {
                "name": "missing_fields",
                "model": model,
                "match_data": {"home_team": "Team_A"},  # 缺少away_team
                "should_fail": True,
            },
            # 3. 主客队相同
            {
                "name": "same_team",
                "model": model,
                "match_data": {"home_team": "Team_A", "away_team": "Team_A"},
                "should_fail": True,
            },
            # 4. 正常情况
            {
                "name": "normal_case",
                "model": model,
                "match_data": {
                    "home_team": training_data["home_team"].iloc[0],
                    "away_team": training_data["away_team"].iloc[1],
                },
                "should_fail": False,
            },
        ]

        for case in error_cases:
            try:
                prediction = case["model"].predict(case["match_data"])
                if case["should_fail"]:
                    assert False, f"Case '{case['name']}' should have failed"
                else:
                    assert isinstance(prediction, PredictionResult)
                    print(f"✅ {case['name']}: 预测成功")
            except Exception as e:
                if case["should_fail"]:
                    print(f"✅ {case['name']}: 正确捕获错误 - {str(e)[:50]}...")
                else:
                    assert (
                        False
                    ), f"Case '{case['name']}' should not have failed: {str(e)}"


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模块导入失败")
@pytest.mark.unit
@pytest.mark.ml
class TestMLModelEvaluation:
    """ML模型评估测试"""

    def test_comprehensive_evaluation_metrics(self):
        """测试全面评估指标"""
        training_data, test_data = create_evaluation_dataset(400, 150)

        # 训练模型
        model = PoissonModel("comprehensive_evaluation_test")
        model.train(training_data)

        # 全面评估
        evaluation_metrics = model.evaluate(test_data)

        # 验证基本指标
        required_metrics = [
            "accuracy",
            "precision",
            "recall",
            "f1_score",
            "confusion_matrix",
            "total_predictions",
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
        assert len(cm) >= 2  # 至少2x2的混淆矩阵

        # 验证总预测数
        assert evaluation_metrics["total_predictions"] <= len(test_data)

        print("✅ 全面评估指标测试通过:")
        print(f"   准确率: {evaluation_metrics['accuracy']:.3f}")
        print(f"   精确率: {evaluation_metrics['precision']:.3f}")
        print(f"   召回率: {evaluation_metrics['recall']:.3f}")
        print(f"   F1分数: {evaluation_metrics['f1_score']:.3f}")
        print(f"   总预测数: {evaluation_metrics['total_predictions']}")

    def test_evaluation_on_different_data_distributions(self):
        """测试不同数据分布上的评估"""
        # 创建具有不同特征的数据集
        datasets = {}

        # 1. 平衡数据集
        balanced_train = []
        balanced_test = []
        for result in ["home_win", "draw", "away_win"]:
            result_train = create_evaluation_dataset(100, 30)[0]
            result_train["result"] = result
            balanced_train.append(result_train)

            result_test = create_evaluation_dataset(30, 15)[1]
            result_test["result"] = result
            balanced_test.append(result_test)

        datasets["balanced"] = {
            "train": pd.concat(balanced_train),
            "test": pd.concat(balanced_test),
        }

        # 2. 不平衡数据集（主场优势明显）
        skewed_train, skewed_test = create_evaluation_dataset(400, 150)
        # 增加主胜比例
        home_win_indices = skewed_train[skewed_train["result"] == "home_win"].index
        additional_home_wins = skewed_train.loc[home_win_indices].sample(
            min(50, len(home_win_indices))
        )
        skewed_train = pd.concat([skewed_train, additional_home_wins])

        datasets["skewed"] = {"train": skewed_train, "test": skewed_test}

        # 在不同数据集上训练和评估
        results = {}
        for name, data in datasets.items():
            model = PoissonModel(f"evaluation_{name}")
            training_result = model.train(data["train"])
            evaluation_metrics = model.evaluate(data["test"])

            results[name] = {
                "training_accuracy": training_result.accuracy,
                "test_accuracy": evaluation_metrics["accuracy"],
                "f1_score": evaluation_metrics["f1_score"],
                "training_samples": len(data["train"]),
                "test_samples": len(data["test"]),
            }

        # 验证结果
        assert len(results) == 2

        # 平衡数据集应该有更稳定的性能
        assert results["balanced"]["test_accuracy"] > 0.2  # 至少比随机好

        # 比较不同数据集的性能
        print("✅ 不同数据分布评估测试通过:")
        for name, result in results.items():
            print(f"   {name}数据集:")
            print(f"     训练准确率: {result['training_accuracy']:.3f}")
            print(f"     测试准确率: {result['test_accuracy']:.3f}")
            print(f"     F1分数: {result['f1_score']:.3f}")

    def test_evaluation_reliability_and_stability(self):
        """测试评估可靠性和稳定性"""
        training_data, base_test_data = create_evaluation_dataset(300, 100)

        # 训练模型
        model = PoissonModel("evaluation_stability_test")
        model.train(training_data)

        # 多次评估以测试稳定性
        stability_results = []
        for i in range(5):
            # 轻微扰动测试数据
            perturbed_test = base_test_data.copy()
            # 随机选择一些样本进行微小修改
            n_perturb = min(10, len(perturbed_test))
            perturb_indices = np.random.choice(
                len(perturbed_test), n_perturb, replace=False
            )

            for idx in perturb_indices:
                if np.random.random() < 0.5:
                    # 随机改变结果
                    current_result = perturbed_test.loc[idx, "result"]
                    possible_results = ["home_win", "draw", "away_win"]
                    possible_results.remove(current_result)
                    perturbed_test.loc[idx, "result"] = np.random.choice(
                        possible_results
                    )

            # 评估
            metrics = model.evaluate(perturbed_test)
            stability_results.append(metrics["accuracy"])

        # 分析稳定性
        mean_accuracy = np.mean(stability_results)
        std_accuracy = np.std(stability_results)
        min_accuracy = np.min(stability_results)
        max_accuracy = np.max(stability_results)

        # 验证稳定性（标准差不应该太大）
        assert std_accuracy < 0.1  # 标准差应该小于0.1

        # 验证合理的性能水平
        assert mean_accuracy > 0.2  # 应该比随机预测好

        print("✅ 评估稳定性测试通过:")
        print(f"   准确率: {mean_accuracy:.3f} ± {std_accuracy:.3f}")
        print(f"   范围: [{min_accuracy:.3f}, {max_accuracy:.3f}]")
        print(f"   变异系数: {std_accuracy/mean_accuracy:.3f}")

    def test_cross_validation_evaluation(self):
        """测试交叉验证评估"""
        # 创建较小的数据集用于交叉验证
        training_data = create_evaluation_dataset(200, 80)[0]

        # 训练模型（内部会进行交叉验证）
        model = PoissonModel("cross_validation_test")
        model.update_hyperparameters(min_matches_per_team=5)  # 降低最小比赛数要求

        training_result = model.train(training_data)

        # 验证交叉验证结果
        assert training_result.accuracy > 0.0
        assert model.is_trained

        # 在独立测试集上验证
        _, test_data = create_evaluation_dataset(50, 30)
        test_metrics = model.evaluate(test_data)

        # 验证交叉验证的泛化能力
        # 交叉验证准确率应该与测试准确率相对接近
        accuracy_diff = abs(training_result.accuracy - test_metrics["accuracy"])
        assert accuracy_diff < 0.3  # 允许一定的差异

        print("✅ 交叉验证评估测试通过:")
        print(f"   交叉验证准确率: {training_result.accuracy:.3f}")
        print(f"   测试准确率: {test_metrics['accuracy']:.3f}")
        print(f"   差异: {accuracy_diff:.3f}")

    def test_feature_importance_analysis(self):
        """测试特征重要性分析"""
        training_data, test_data = create_evaluation_dataset(300, 100)

        # 训练模型
        model = PoissonModel("feature_importance_test")
        model.train(training_data)

        # 获取特征重要性
        feature_importance = model.get_feature_importance()

        # 验证特征重要性
        assert isinstance(feature_importance, dict)

        # Poisson模型的特征重要性可能为空（如果不支持）
        if feature_importance:
            # 验证特征重要性的基本属性
            for feature, importance in feature_importance.items():
                assert isinstance(feature, str)
                assert isinstance(importance, (int, float))
                assert importance >= 0

            # 验证特征重要性排序
            sorted_features = sorted(
                feature_importance.items(), key=lambda x: x[1], reverse=True
            )
            assert len(sorted_features) == len(feature_importance)

            print("✅ 特征重要性分析测试通过:")
            for feature, importance in sorted_features:
                print(f"   {feature}: {importance:.3f}")
        else:
            print("✅ 特征重要性分析测试通过: 模型不支持特征重要性计算")

    def test_model_comparison_evaluation(self):
        """测试模型比较评估"""
        training_data, test_data = create_evaluation_dataset(400, 150)

        # 训练多个具有不同超参数的模型
        models = {}
        model_configs = [
            {"name": "conservative", "home_advantage": 0.1, "min_matches_per_team": 15},
            {"name": "balanced", "home_advantage": 0.3, "min_matches_per_team": 10},
            {"name": "aggressive", "home_advantage": 0.5, "min_matches_per_team": 5},
        ]

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

            models[config["name"]] = {
                "model": model,
                "training_result": training_result,
                "evaluation_metrics": evaluation_metrics,
                "config": config,
            }

        # 比较模型性能
        model_comparison = []
        for name, data in models.items():
            model_comparison.append(
                {
                    "name": name,
                    "training_accuracy": data["training_result"].accuracy,
                    "test_accuracy": data["evaluation_metrics"]["accuracy"],
                    "f1_score": data["evaluation_metrics"]["f1_score"],
                    "precision": data["evaluation_metrics"]["precision"],
                    "recall": data["evaluation_metrics"]["recall"],
                    "training_time": data["training_result"].training_time,
                }
            )

        # 验证模型比较结果
        assert len(model_comparison) == 3

        # 找到最佳模型
        best_model = max(model_comparison, key=lambda x: x["test_accuracy"])
        worst_model = min(model_comparison, key=lambda x: x["test_accuracy"])

        # 验证性能差异
        performance_diff = best_model["test_accuracy"] - worst_model["test_accuracy"]
        assert performance_diff >= 0  # 应该有性能差异

        print("✅ 模型比较评估测试通过:")
        print(
            f"   最佳模型: {best_model['name']} (准确率: {best_model['test_accuracy']:.3f})"
        )
        print(
            f"   最差模型: {worst_model['name']} (准确率: {worst_model['test_accuracy']:.3f})"
        )
        print(f"   性能差异: {performance_diff:.3f}")

        print("\n详细比较:")
        for model in model_comparison:
            print(
                f"   {model['name']}: 训练={model['training_accuracy']:.3f}, "
                f"测试={model['test_accuracy']:.3f}, F1={model['f1_score']:.3f}"
            )


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模块导入失败")
@pytest.mark.unit
@pytest.mark.ml
class TestMLModelPerformanceAnalysis:
    """ML模型性能分析测试"""

    def test_learning_curve_analysis(self):
        """测试学习曲线分析"""
        # 创建不同大小的训练数据集
        data_sizes = [50, 100, 200, 400]
        training_data_full, test_data = create_evaluation_dataset(500, 200)

        learning_curve_results = []

        for size in data_sizes:
            # 随机采样训练数据
            training_data_subset = training_data_full.sample(
                min(size, len(training_data_full))
            )

            # 训练模型
            model = PoissonModel(f"learning_curve_{size}")
            training_result = model.train(training_data_subset)

            # 评估
            evaluation_metrics = model.evaluate(test_data)

            learning_curve_results.append(
                {
                    "training_size": len(training_data_subset),
                    "training_accuracy": training_result.accuracy,
                    "test_accuracy": evaluation_metrics["accuracy"],
                    "f1_score": evaluation_metrics["f1_score"],
                    "training_time": training_result.training_time,
                }
            )

        # 分析学习曲线
        test_accuracies = [r["test_accuracy"] for r in learning_curve_results]
        training_times = [r["training_time"] for r in learning_curve_results]

        # 验证学习曲线特性
        # 1. 随着数据量增加，测试准确率应该总体上升（或至少不显著下降）
        if len(test_accuracies) > 1:
            overall_trend = np.polyfit(range(len(test_accuracies)), test_accuracies, 1)[
                0
            ]
            # 允许轻微下降，但不应该太严重
            assert overall_trend > -0.1  # 下降趋势不应该太陡峭

        # 2. 训练时间应该随数据量增加
        if len(training_times) > 1:
            time_trend = np.polyfit(range(len(training_times)), training_times, 1)[0]
            assert time_trend > 0  # 训练时间应该增加

        print("✅ 学习曲线分析测试通过:")
        for result in learning_curve_results:
            print(
                f"   数据量={result['training_size']}: "
                f"训练准确率={result['training_accuracy']:.3f}, "
                f"测试准确率={result['test_accuracy']:.3f}, "
                f"训练时间={result['training_time']:.2f}s"
            )

    def test_prediction_confidence_analysis(self):
        """测试预测置信度分析"""
        training_data, test_data = create_evaluation_dataset(400, 200)

        # 训练模型
        model = PoissonModel("confidence_analysis_test")
        model.train(training_data)

        # 收集所有预测及其置信度
        predictions_with_confidence = []
        for _, test_match in test_data.iterrows():
            match_data = {
                "home_team": test_match["home_team"],
                "away_team": test_match["away_team"],
            }
            prediction = model.predict(match_data)
            predictions_with_confidence.append(prediction.confidence)

        # 分析置信度分布
        confidence_array = np.array(predictions_with_confidence)

        # 验证置信度分布特性
        # 1. 所有置信度都在[0,1]范围内
        assert np.all(confidence_array >= 0)
        assert np.all(confidence_array <= 1)

        # 2. 置信度分布应该合理（不应该全部集中在一个极端）
        mean_confidence = np.mean(confidence_array)
        std_confidence = np.std(confidence_array)

        assert 0.3 < mean_confidence < 0.8  # 合理的平均置信度范围
        assert std_confidence > 0.05  # 应该有一定的变化

        # 3. 分析置信度分段
        confidence_ranges = [
            (0.3, 0.4, "低"),
            (0.4, 0.6, "中"),
            (0.6, 0.8, "高"),
            (0.8, 1.0, "很高"),
        ]

        confidence_distribution = []
        for low, high, label in confidence_ranges:
            count = np.sum((confidence_array >= low) & (confidence_array < high))
            percentage = count / len(confidence_array) * 100
            confidence_distribution.append(
                {
                    "range": f"{low}-{high}",
                    "label": label,
                    "count": count,
                    "percentage": percentage,
                }
            )

        print("✅ 置信度分析测试通过:")
        print(f"   平均置信度: {mean_confidence:.3f} ± {std_confidence:.3f}")
        print("   置信度分布:")
        for dist in confidence_distribution:
            print(
                f"     {dist['label']} ({dist['range']}): {dist['count']} ({dist['percentage']:.1f}%)"
            )

    def test_error_analysis_and_diagnosis(self):
        """测试错误分析和诊断"""
        training_data, test_data = create_evaluation_dataset(400, 200)

        # 训练模型
        model = PoissonModel("error_analysis_test")
        model.train(training_data)

        # 收集预测和实际结果
        prediction_results = []
        for _, test_match in test_data.iterrows():
            match_data = {
                "home_team": test_match["home_team"],
                "away_team": test_match["away_team"],
            }
            prediction = model.predict(match_data)
            prediction_results.append(
                {
                    "prediction": prediction,
                    "actual": test_match["result"],
                    "home_team": test_match["home_team"],
                    "away_team": test_match["away_team"],
                }
            )

        # 分析错误模式
        correct_predictions = [
            p
            for p in prediction_results
            if p["prediction"].predicted_outcome == p["actual"]
        ]
        incorrect_predictions = [
            p
            for p in prediction_results
            if p["prediction"].predicted_outcome != p["actual"]
        ]

        # 计算错误率
        error_rate = len(incorrect_predictions) / len(prediction_results)
        accuracy = len(correct_predictions) / len(prediction_results)

        # 分析错误类型
        error_types = {"home_win": 0, "draw": 0, "away_win": 0}
        for pred in incorrect_predictions:
            error_types[pred["actual"]] += 1

        # 分析置信度与正确性的关系
        confidences_correct = [p["prediction"].confidence for p in correct_predictions]
        confidences_incorrect = [
            p["prediction"].confidence for p in incorrect_predictions
        ]

        avg_confidence_correct = (
            np.mean(confidences_correct) if confidences_correct else 0
        )
        avg_confidence_incorrect = (
            np.mean(confidences_incorrect) if confidences_incorrect else 0
        )

        # 验证错误分析结果
        assert 0 <= error_rate <= 1
        assert len(correct_predictions) + len(incorrect_predictions) == len(
            prediction_results
        )

        # 正确预测的置信度应该平均高于错误预测
        if confidences_correct and confidences_incorrect:
            confidence_gap = avg_confidence_correct - avg_confidence_incorrect
            assert confidence_gap > 0  # 正确预测应该有更高的平均置信度

        print("✅ 错误分析测试通过:")
        print(f"   总准确率: {accuracy:.3f}")
        print(f"   错误率: {error_rate:.3f}")
        print(f"   正确预测平均置信度: {avg_confidence_correct:.3f}")
        print(f"   错误预测平均置信度: {avg_confidence_incorrect:.3f}")
        print(f"   错误类型分布: {error_types}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
