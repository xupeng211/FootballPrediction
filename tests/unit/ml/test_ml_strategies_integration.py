#!/usr/bin/env python3
"""
🔄 ML策略集成测试 - 机器学习策略和集成工作流测试

测试ML策略模式、集成预测、工作流编排、策略选择器等功能。
验证不同ML策略的组合使用和整体系统集成。
"""

import asyncio
import warnings
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

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


# 模拟ML策略系统
class MLStrategyType(Enum):
    """ML策略类型"""

    POISSON = "poisson"
    ENSEMBLE = "ensemble"
    WEIGHTED = "weighted"
    ADAPTIVE = "adaptive"


class MockMLStrategy:
    """模拟ML策略"""

    def __init__(self, strategy_type: MLStrategyType, name: str, weight: float = 1.0):
        self.strategy_type = strategy_type
        self.name = name
        self.weight = weight
        self.model = None
        self.is_trained = False
        self.performance_history = []

    async def train(self, training_data: pd.DataFrame) -> dict[str, Any]:
        """训练策略"""
        if self.strategy_type == MLStrategyType.POISSON:
            self.model = PoissonModel(f"{self.name}_poisson")
            training_result = self.model.train(training_data)
            self.is_trained = True
            return {
                "strategy": self.name,
                "accuracy": training_result.accuracy,
                "training_time": training_result.training_time,
                "model_info": self.model.get_model_info(),
            }
        else:
            # 模拟其他策略的训练
            await asyncio.sleep(0.01)  # 模拟训练时间
            self.is_trained = True
            accuracy = np.random.uniform(0.4, 0.8)
            return {
                "strategy": self.name,
                "accuracy": accuracy,
                "training_time": np.random.uniform(0.1, 2.0),
                "model_info": {"model_type": self.strategy_type.value},
            }

    async def predict(self, match_data: dict[str, Any]) -> PredictionResult | None:
        """预测"""
        if not self.is_trained:
            return None

        if self.strategy_type == MLStrategyType.POISSON and self.model:
            return self.model.predict(match_data)
        else:
            # 模拟其他策略的预测
            probabilities = np.random.dirichlet([1, 1, 1])  # 生成随机概率分布
            max_prob_index = np.argmax(probabilities)
            outcomes = ["home_win", "draw", "away_win"]

            return PredictionResult(
                match_id=match_data.get("match_id", "unknown"),
                home_team=match_data["home_team"],
                away_team=match_data["away_team"],
                home_win_prob=float(probabilities[0]),
                draw_prob=float(probabilities[1]),
                away_win_prob=float(probabilities[2]),
                predicted_outcome=outcomes[max_prob_index],
                confidence=float(max(probabilities)),
                model_name=self.name,
                model_version="1.0",
                created_at=datetime.now(),
            )

    def update_performance(self, actual_result: str, prediction: PredictionResult):
        """更新性能历史"""
        is_correct = prediction.predicted_outcome == actual_result
        self.performance_history.append(
            {
                "timestamp": datetime.now(),
                "is_correct": is_correct,
                "confidence": prediction.confidence,
                "predicted_outcome": prediction.predicted_outcome,
                "actual_outcome": actual_result,
            }
        )

    def get_recent_accuracy(self, window_size: int = 50) -> float:
        """获取最近准确率"""
        if not self.performance_history:
            return 0.0

        recent_history = self.performance_history[-window_size:]
        correct_predictions = sum(1 for h in recent_history if h["is_correct"])
        return correct_predictions / len(recent_history)


class MockStrategySelector:
    """模拟策略选择器"""

    def __init__(self):
        self.strategies: dict[str, MockMLStrategy] = {}
        self.selection_history = []

    def register_strategy(self, strategy: MockMLStrategy):
        """注册策略"""
        self.strategies[strategy.name] = strategy

    def select_best_strategy(
        self, match_data: dict[str, Any], selection_method: str = "accuracy"
    ) -> MockMLStrategy | None:
        """选择最佳策略"""
        if not self.strategies:
            return None

        if selection_method == "accuracy":
            # 基于最近准确率选择
            best_strategy = max(
                self.strategies.values(), key=lambda s: s.get_recent_accuracy()
            )
        elif selection_method == "weighted":
            # 基于权重选择
            best_strategy = max(self.strategies.values(), key=lambda s: s.weight)
        else:
            # 随机选择
            best_strategy = np.random.choice(list(self.strategies.values()))

        self.selection_history.append(
            {
                "timestamp": datetime.now(),
                "selected_strategy": best_strategy.name,
                "method": selection_method,
                "match_data": match_data,
            }
        )

        return best_strategy

    def get_strategy_performance_summary(self) -> dict[str, dict[str, float]]:
        """获取策略性能摘要"""
        summary = {}
        for name, strategy in self.strategies.items():
            summary[name] = {
                "recent_accuracy": strategy.get_recent_accuracy(),
                "weight": strategy.weight,
                "total_predictions": len(strategy.performance_history),
                "is_trained": strategy.is_trained,
            }
        return summary


class MockEnsemblePredictor:
    """模拟集成预测器"""

    def __init__(self, ensemble_method: str = "weighted_average"):
        self.ensemble_method = ensemble_method
        self.strategies: list[MockMLStrategy] = []
        self.prediction_history = []

    def add_strategy(self, strategy: MockMLStrategy):
        """添加策略"""
        self.strategies.append(strategy)

    async def predict(self, match_data: dict[str, Any]) -> PredictionResult | None:
        """集成预测"""
        if not self.strategies:
            return None

        # 获取所有策略的预测
        individual_predictions = []
        for strategy in self.strategies:
            if strategy.is_trained:
                prediction = await strategy.predict(match_data)
                if prediction:
                    individual_predictions.append((prediction, strategy))

        if not individual_predictions:
            return None

        # 集成方法
        if self.ensemble_method == "weighted_average":
            return self._weighted_average_ensemble(individual_predictions)
        elif self.ensemble_method == "majority_vote":
            return self._majority_vote_ensemble(individual_predictions)
        elif self.ensemble_method == "confidence_weighted":
            return self._confidence_weighted_ensemble(individual_predictions)
        else:
            return self._simple_average_ensemble(individual_predictions)

    def _weighted_average_ensemble(
        self, predictions: list[tuple[PredictionResult, MockMLStrategy]]
    ) -> PredictionResult:
        """加权平均集成"""
        total_weight = sum(strategy.weight for _, strategy in predictions)

        home_win_prob = (
            sum(pred.home_win_prob * strategy.weight for pred, strategy in predictions)
            / total_weight
        )
        draw_prob = (
            sum(pred.draw_prob * strategy.weight for pred, strategy in predictions)
            / total_weight
        )
        away_win_prob = (
            sum(pred.away_win_prob * strategy.weight for pred, strategy in predictions)
            / total_weight
        )

        # 归一化概率
        total_prob = home_win_prob + draw_prob + away_win_prob
        if total_prob > 0:
            home_win_prob /= total_prob
            draw_prob /= total_prob
            away_win_prob /= total_prob

        # 确定预测结果
        probs = [home_win_prob, draw_prob, away_win_prob]
        outcomes = ["home_win", "draw", "away_win"]
        predicted_outcome = outcomes[np.argmax(probs)]
        confidence = max(probs)

        return PredictionResult(
            match_id=predictions[0][0].match_id,
            home_team=predictions[0][0].home_team,
            away_team=predictions[0][0].away_team,
            home_win_prob=home_win_prob,
            draw_prob=draw_prob,
            away_win_prob=away_win_prob,
            predicted_outcome=predicted_outcome,
            confidence=confidence,
            model_name=f"ensemble_{self.ensemble_method}",
            model_version="1.0",
            created_at=datetime.now(),
        )

    def _majority_vote_ensemble(
        self, predictions: list[tuple[PredictionResult, MockMLStrategy]]
    ) -> PredictionResult:
        """多数投票集成"""
        outcomes = [pred.predicted_outcome for pred, _ in predictions]
        outcome_counts = {outcome: outcomes.count(outcome) for outcome in set(outcomes)}

        # 找到最多票数的结果
        predicted_outcome = max(outcome_counts, key=outcome_counts.get)

        # 平均概率
        home_win_prob = np.mean([pred.home_win_prob for pred, _ in predictions])
        draw_prob = np.mean([pred.draw_prob for pred, _ in predictions])
        away_win_prob = np.mean([pred.away_win_prob for pred, _ in predictions])

        # 归一化
        total_prob = home_win_prob + draw_prob + away_win_prob
        if total_prob > 0:
            home_win_prob /= total_prob
            draw_prob /= total_prob
            away_win_prob /= total_prob

        confidence = max(home_win_prob, draw_prob, away_win_prob)

        return PredictionResult(
            match_id=predictions[0][0].match_id,
            home_team=predictions[0][0].home_team,
            away_team=predictions[0][0].away_team,
            home_win_prob=home_win_prob,
            draw_prob=draw_prob,
            away_win_prob=away_win_prob,
            predicted_outcome=predicted_outcome,
            confidence=confidence,
            model_name=f"ensemble_{self.ensemble_method}",
            model_version="1.0",
            created_at=datetime.now(),
        )

    def _confidence_weighted_ensemble(
        self, predictions: list[tuple[PredictionResult, MockMLStrategy]]
    ) -> PredictionResult:
        """置信度加权集成"""
        total_confidence = sum(pred.confidence for pred, _ in predictions)

        if total_confidence == 0:
            return self._simple_average_ensemble(predictions)

        home_win_prob = (
            sum(pred.home_win_prob * pred.confidence for pred, _ in predictions)
            / total_confidence
        )
        draw_prob = (
            sum(pred.draw_prob * pred.confidence for pred, _ in predictions)
            / total_confidence
        )
        away_win_prob = (
            sum(pred.away_win_prob * pred.confidence for pred, _ in predictions)
            / total_confidence
        )

        # 归一化
        total_prob = home_win_prob + draw_prob + away_win_prob
        if total_prob > 0:
            home_win_prob /= total_prob
            draw_prob /= total_prob
            away_win_prob /= total_prob

        probs = [home_win_prob, draw_prob, away_win_prob]
        outcomes = ["home_win", "draw", "away_win"]
        predicted_outcome = outcomes[np.argmax(probs)]
        confidence = max(probs)

        return PredictionResult(
            match_id=predictions[0][0].match_id,
            home_team=predictions[0][0].home_team,
            away_team=predictions[0][0].away_team,
            home_win_prob=home_win_prob,
            draw_prob=draw_prob,
            away_win_prob=away_win_prob,
            predicted_outcome=predicted_outcome,
            confidence=confidence,
            model_name=f"ensemble_{self.ensemble_method}",
            model_version="1.0",
            created_at=datetime.now(),
        )

    def _simple_average_ensemble(
        self, predictions: list[tuple[PredictionResult, MockMLStrategy]]
    ) -> PredictionResult:
        """简单平均集成"""
        home_win_prob = np.mean([pred.home_win_prob for pred, _ in predictions])
        draw_prob = np.mean([pred.draw_prob for pred, _ in predictions])
        away_win_prob = np.mean([pred.away_win_prob for pred, _ in predictions])

        # 归一化
        total_prob = home_win_prob + draw_prob + away_win_prob
        if total_prob > 0:
            home_win_prob /= total_prob
            draw_prob /= total_prob
            away_win_prob /= total_prob

        probs = [home_win_prob, draw_prob, away_win_prob]
        outcomes = ["home_win", "draw", "away_win"]
        predicted_outcome = outcomes[np.argmax(probs)]
        confidence = max(probs)

        return PredictionResult(
            match_id=predictions[0][0].match_id,
            home_team=predictions[0][0].home_team,
            away_team=predictions[0][0].away_team,
            home_win_prob=home_win_prob,
            draw_prob=draw_prob,
            away_win_prob=away_win_prob,
            predicted_outcome=predicted_outcome,
            confidence=confidence,
            model_name=f"ensemble_{self.ensemble_method}",
            model_version="1.0",
            created_at=datetime.now(),
        )


def create_test_dataset(num_matches: int = 200) -> tuple[pd.DataFrame, pd.DataFrame]:
    """创建测试数据集"""
    teams = [f"Team_{chr(65+i)}" for i in range(20)]
    training_data = []
    test_data = []

    # 训练数据
    for i in range(num_matches):
        home_team = np.random.choice(teams)
        away_team = np.random.choice([t for t in teams if t != home_team])

        home_goals = np.random.poisson(1.5)
        away_goals = np.random.poisson(1.1)

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
                - timedelta(days=np.random.randint(1, 365)),
            }
        )

    # 测试数据
    for i in range(num_matches // 4):
        home_team = np.random.choice(teams)
        away_team = np.random.choice([t for t in teams if t != home_team])

        home_goals = np.random.poisson(1.5)
        away_goals = np.random.poisson(1.1)

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
            }
        )

    return pd.DataFrame(training_data), pd.DataFrame(test_data)


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模块导入失败")
@pytest.mark.unit
@pytest.mark.ml
@pytest.mark.asyncio
class TestMLStrategySystem:
    """ML策略系统测试"""

    async def test_single_strategy_training_and_prediction(self):
        """测试单一策略训练和预测"""
        training_data, test_data = create_test_dataset(150, 50)

        # 创建策略
        strategy = MockMLStrategy(MLStrategyType.POISSON, "single_test", weight=1.0)

        # 训练策略
        training_result = await strategy.train(training_data)

        assert training_result["strategy"] == "single_test"
        assert "accuracy" in training_result
        assert "training_time" in training_result
        assert strategy.is_trained

        # 预测
        test_match = test_data.iloc[0]
        match_data = {
            "home_team": test_match["home_team"],
            "away_team": test_match["away_team"],
            "match_id": "single_strategy_test",
        }

        prediction = await strategy.predict(match_data)

        assert prediction is not None
        assert prediction.home_team == match_data["home_team"]
        assert prediction.away_team == match_data["away_team"]
        assert prediction.match_id == match_data["match_id"]
        assert (
            abs(
                prediction.home_win_prob
                + prediction.draw_prob
                + prediction.away_win_prob
                - 1.0
            )
            < 0.01
        )

        print(
            f"✅ 单一策略测试通过: {strategy.name}, 准确率={training_result['accuracy']:.3f}"
        )

    async def test_multiple_strategy_training(self):
        """测试多策略训练"""
        training_data, test_data = create_test_dataset(200, 50)

        # 创建多个策略
        strategies = [
            MockMLStrategy(MLStrategyType.POISSON, "poisson_strategy", weight=1.0),
            MockMLStrategy(MLStrategyType.ENSEMBLE, "ensemble_strategy", weight=0.8),
            MockMLStrategy(MLStrategyType.WEIGHTED, "weighted_strategy", weight=1.2),
            MockMLStrategy(MLStrategyType.ADAPTIVE, "adaptive_strategy", weight=0.9),
        ]

        # 并行训练所有策略
        training_tasks = [strategy.train(training_data) for strategy in strategies]
        training_results = await asyncio.gather(*training_tasks)

        # 验证训练结果
        assert len(training_results) == len(strategies)

        for i, (strategy, result) in enumerate(zip(strategies, training_results)):
            assert strategy.is_trained
            assert result["strategy"] == strategy.name
            assert "accuracy" in result
            assert "training_time" in result
            print(
                f"  策略 {strategy.name}: 准确率={result['accuracy']:.3f}, 训练时间={result['training_time']:.2f}s"
            )

        print(f"✅ 多策略训练测试通过: {len(strategies)}个策略训练完成")

    async def test_strategy_selector_functionality(self):
        """测试策略选择器功能"""
        training_data, test_data = create_test_dataset(150, 50)

        # 创建策略选择器
        selector = MockStrategySelector()

        # 创建并注册策略
        strategies = [
            MockMLStrategy(MLStrategyType.POISSON, "high_accuracy", weight=1.0),
            MockMLStrategy(MLStrategyType.ENSEMBLE, "medium_accuracy", weight=1.5),
            MockMLStrategy(MLStrategyType.WEIGHTED, "low_accuracy", weight=2.0),
        ]

        for strategy in strategies:
            selector.register_strategy(strategy)
            await strategy.train(training_data)

        # 模拟不同的性能历史
        strategies[0].performance_history = [
            {"is_correct": True, "confidence": 0.8} for _ in range(20)
        ]  # 高准确率

        strategies[1].performance_history = [
            {"is_correct": True, "confidence": 0.6} for _ in range(15)
        ] + [
            {"is_correct": False, "confidence": 0.4} for _ in range(5)
        ]  # 中等准确率

        strategies[2].performance_history = [
            {"is_correct": True, "confidence": 0.7} for _ in range(10)
        ] + [
            {"is_correct": False, "confidence": 0.5} for _ in range(10)
        ]  # 低准确率

        # 测试不同的选择方法
        test_match = test_data.iloc[0]
        match_data = {
            "home_team": test_match["home_team"],
            "away_team": test_match["away_team"],
        }

        selection_methods = ["accuracy", "weighted", "random"]
        selected_strategies = []

        for method in selection_methods:
            selected = selector.select_best_strategy(match_data, method)
            selected_strategies.append((method, selected.name if selected else None))

        # 验证选择结果
        assert len(selected_strategies) == len(selection_methods)

        # 基于准确率的选择应该选择最高准确率的策略
        accuracy_selection = next(s for s in selected_strategies if s[0] == "accuracy")
        assert accuracy_selection[1] == "high_accuracy"

        # 基于权重的选择应该选择最高权重的策略
        weighted_selection = next(s for s in selected_strategies if s[0] == "weighted")
        assert weighted_selection[1] == "low_accuracy"

        print("✅ 策略选择器测试通过:")
        for method, strategy_name in selected_strategies:
            print(f"  {method}方法: 选择了{strategy_name}")

    async def test_ensemble_prediction_methods(self):
        """测试集成预测方法"""
        training_data, test_data = create_test_dataset(200, 50)

        # 创建策略
        strategies = [
            MockMLStrategy(MLStrategyType.POISSON, "poisson_ensemble", weight=1.0),
            MockMLStrategy(MLStrategyType.ENSEMBLE, "ensemble_ensemble", weight=0.8),
            MockMLStrategy(MLStrategyType.WEIGHTED, "weighted_ensemble", weight=1.2),
        ]

        # 训练策略
        for strategy in strategies:
            await strategy.train(training_data)

        # 测试不同的集成方法
        ensemble_methods = [
            "weighted_average",
            "majority_vote",
            "confidence_weighted",
            "simple_average",
        ]
        ensemble_results = []

        test_match = test_data.iloc[0]
        match_data = {
            "home_team": test_match["home_team"],
            "away_team": test_match["away_team"],
            "match_id": "ensemble_test",
        }

        for method in ensemble_methods:
            ensemble = MockEnsemblePredictor(ensemble_method=method)
            for strategy in strategies:
                ensemble.add_strategy(strategy)

            prediction = await ensemble.predict(match_data)
            ensemble_results.append((method, prediction))

        # 验证集成结果
        assert len(ensemble_results) == len(ensemble_methods)

        for method, prediction in ensemble_results:
            assert prediction is not None
            assert prediction.model_name.startswith("ensemble_")
            assert (
                abs(
                    prediction.home_win_prob
                    + prediction.draw_prob
                    + prediction.away_win_prob
                    - 1.0
                )
                < 0.01
            )
            print(
                f"  {method}: {prediction.predicted_outcome} (置信度: {prediction.confidence:.3f})"
            )

        print(f"✅ 集成预测方法测试通过: {len(ensemble_methods)}种方法")

    async def test_strategy_performance_tracking(self):
        """测试策略性能跟踪"""
        training_data, test_data = create_test_dataset(150, 50)

        # 创建策略
        strategy = MockMLStrategy(
            MLStrategyType.POISSON, "performance_test", weight=1.0
        )
        await strategy.train(training_data)

        # 模拟预测和性能跟踪
        performance_results = []

        for _, test_match in test_data.iterrows():
            match_data = {
                "home_team": test_match["home_team"],
                "away_team": test_match["away_team"],
                "match_id": f"perf_test_{len(performance_results)}",
            }

            prediction = await strategy.predict(match_data)
            if prediction:
                # 更新性能
                strategy.update_performance(test_match["result"], prediction)

                # 记录结果
                performance_results.append(
                    {
                        "predicted": prediction.predicted_outcome,
                        "actual": test_match["result"],
                        "confidence": prediction.confidence,
                        "correct": prediction.predicted_outcome == test_match["result"],
                    }
                )

        # 验证性能跟踪
        assert len(strategy.performance_history) == len(performance_results)
        assert len(strategy.performance_history) > 0

        # 计算统计指标
        total_predictions = len(performance_results)
        correct_predictions = sum(1 for r in performance_results if r["correct"])
        overall_accuracy = correct_predictions / total_predictions

        recent_accuracy = strategy.get_recent_accuracy(window_size=20)

        # 验证性能指标
        assert 0 <= overall_accuracy <= 1
        assert 0 <= recent_accuracy <= 1
        assert len(strategy.performance_history) == total_predictions

        # 验证最近准确率的计算
        recent_history = strategy.performance_history[-20:]
        expected_recent_accuracy = sum(
            1 for h in recent_history if h["is_correct"]
        ) / len(recent_history)
        assert abs(recent_accuracy - expected_recent_accuracy) < 0.001

        print("✅ 策略性能跟踪测试通过:")
        print(f"  总预测数: {total_predictions}")
        print(f"  总准确率: {overall_accuracy:.3f}")
        print(f"  最近准确率: {recent_accuracy:.3f}")

    async def test_adaptive_strategy_selection(self):
        """测试自适应策略选择"""
        training_data, test_data = create_test_dataset(200, 80)

        # 创建策略选择器
        selector = MockStrategySelector()

        # 创建策略
        strategies = [
            MockMLStrategy(MLStrategyType.POISSON, "adaptive_poisson", weight=1.0),
            MockMLStrategy(MLStrategyType.ENSEMBLE, "adaptive_ensemble", weight=1.0),
            MockMLStrategy(MLStrategyType.WEIGHTED, "adaptive_weighted", weight=1.0),
        ]

        # 训练并注册策略
        for strategy in strategies:
            await strategy.train(training_data)
            selector.register_strategy(strategy)

        # 模拟自适应选择过程
        selection_counts = {strategy.name: 0 for strategy in strategies}

        for _, test_match in test_data.iterrows():
            match_data = {
                "home_team": test_match["home_team"],
                "away_team": test_match["away_team"],
            }

            # 模拟性能更新
            for strategy in strategies:
                prediction = await strategy.predict(match_data)
                if prediction:
                    # 随机决定是否正确，模拟真实性能变化
                    np.random.random() < 0.6  # 60%准确率
                    strategy.update_performance(test_match["result"], prediction)

            # 选择最佳策略
            best_strategy = selector.select_best_strategy(match_data, "accuracy")
            if best_strategy:
                selection_counts[best_strategy.name] += 1

        # 验证自适应选择
        total_selections = sum(selection_counts.values())
        assert total_selections > 0

        # 应该有不同的策略被选择
        selected_strategies = [
            name for name, count in selection_counts.items() if count > 0
        ]
        assert len(selected_strategies) >= 1

        # 验证选择历史
        assert len(selector.selection_history) == total_selections

        print("✅ 自适应策略选择测试通过:")
        for strategy_name, count in selection_counts.items():
            percentage = count / total_selections * 100
            print(f"  {strategy_name}: 被选择{count}次 ({percentage:.1f}%)")


@pytest.mark.skipif(not CAN_IMPORT, reason="ML模块导入失败")
@pytest.mark.unit
@pytest.mark.ml
@pytest.mark.asyncio
class TestMLWorkflowIntegration:
    """ML工作流集成测试"""

    async def test_end_to_end_ml_workflow(self):
        """测试端到端ML工作流"""
        # 1. 数据准备
        training_data, test_data = create_test_dataset(300, 100)

        # 2. 策略系统初始化
        selector = MockStrategySelector()
        ensemble_predictor = MockEnsemblePredictor(
            ensemble_method="confidence_weighted"
        )

        # 3. 创建和训练策略
        strategies = [
            MockMLStrategy(MLStrategyType.POISSON, "workflow_poisson", weight=1.2),
            MockMLStrategy(MLStrategyType.ENSEMBLE, "workflow_ensemble", weight=0.9),
            MockMLStrategy(MLStrategyType.ADAPTIVE, "workflow_adaptive", weight=1.0),
        ]

        # 4. 并行训练
        training_tasks = [strategy.train(training_data) for strategy in strategies]
        await asyncio.gather(*training_tasks)

        # 5. 注册策略
        for strategy in strategies:
            selector.register_strategy(strategy)
            ensemble_predictor.add_strategy(strategy)

        # 6. 批量预测工作流
        workflow_results = []

        for _, test_match in test_data.iterrows():
            match_data = {
                "home_team": test_match["home_team"],
                "away_team": test_match["away_team"],
                "match_id": f"workflow_{len(workflow_results)}",
            }

            # 6.1 策略选择
            best_strategy = selector.select_best_strategy(match_data, "accuracy")

            # 6.2 集成预测
            ensemble_prediction = await ensemble_predictor.predict(match_data)

            # 6.3 单策略预测（最佳策略）
            single_prediction = None
            if best_strategy:
                single_prediction = await best_strategy.predict(match_data)

            # 6.4 结果记录
            workflow_results.append(
                {
                    "match_id": match_data["match_id"],
                    "actual_result": test_match["result"],
                    "ensemble_prediction": ensemble_prediction,
                    "single_prediction": single_prediction,
                    "selected_strategy": best_strategy.name if best_strategy else None,
                }
            )

        # 7. 工作流结果分析
        successful_predictions = [
            r
            for r in workflow_results
            if r["ensemble_prediction"] and r["single_prediction"]
        ]

        # 集成预测准确率
        ensemble_correct = sum(
            1
            for r in successful_predictions
            if r["ensemble_prediction"].predicted_outcome == r["actual_result"]
        )
        ensemble_accuracy = ensemble_correct / len(successful_predictions)

        # 单策略预测准确率
        single_correct = sum(
            1
            for r in successful_predictions
            if r["single_prediction"].predicted_outcome == r["actual_result"]
        )
        single_accuracy = single_correct / len(successful_predictions)

        # 验证工作流结果
        assert len(workflow_results) == len(test_data)
        assert len(successful_predictions) > 0
        assert 0 <= ensemble_accuracy <= 1
        assert 0 <= single_accuracy <= 1

        print("✅ 端到端ML工作流测试通过:")
        print(f"  处理比赛数: {len(workflow_results)}")
        print(f"  成功预测数: {len(successful_predictions)}")
        print(f"  集成预测准确率: {ensemble_accuracy:.3f}")
        print(f"  单策略预测准确率: {single_accuracy:.3f}")
        print(f"  策略选择历史: {len(selector.selection_history)}次")

    async def test_concurrent_workflow_processing(self):
        """测试并发工作流处理"""
        training_data, test_data = create_test_dataset(200, 60)

        # 创建多个工作流实例
        workflow_count = 3
        workflows = []

        for i in range(workflow_count):
            selector = MockStrategySelector()
            ensemble_predictor = MockEnsemblePredictor(
                ensemble_method="weighted_average"
            )

            # 每个工作流使用不同的策略
            strategies = [
                MockMLStrategy(
                    MLStrategyType.POISSON, f"concurrent_poisson_{i}", weight=1.0
                ),
                MockMLStrategy(
                    MLStrategyType.WEIGHTED, f"concurrent_weighted_{i}", weight=1.0
                ),
            ]

            workflows.append(
                {
                    "selector": selector,
                    "ensemble_predictor": ensemble_predictor,
                    "strategies": strategies,
                }
            )

        # 并发训练所有工作流
        training_tasks = []
        for workflow in workflows:
            for strategy in workflow["strategies"]:
                training_tasks.append(strategy.train(training_data))

        training_results = await asyncio.gather(*training_tasks)
        assert len(training_results) == workflow_count * 2

        # 设置工作流
        for workflow in workflows:
            for strategy in workflow["strategies"]:
                workflow["selector"].register_strategy(strategy)
                workflow["ensemble_predictor"].add_strategy(strategy)

        # 并发预测处理
        async def process_workflow(
            workflow_id: int, workflow_data: dict, test_subset: pd.DataFrame
        ):
            """处理单个工作流"""
            results = []

            for _, test_match in test_subset.iterrows():
                match_data = {
                    "home_team": test_match["home_team"],
                    "away_team": test_match["away_team"],
                    "match_id": f"concurrent_{workflow_id}_{len(results)}",
                }

                prediction = await workflow_data["ensemble_predictor"].predict(
                    match_data
                )
                if prediction:
                    results.append(
                        {
                            "workflow_id": workflow_id,
                            "match_id": match_data["match_id"],
                            "prediction": prediction,
                            "actual": test_match["result"],
                        }
                    )

            return results

        # 分割测试数据给不同工作流
        test_subsets = np.array_split(test_data, workflow_count)

        # 并发执行工作流
        workflow_tasks = [
            process_workflow(i, workflow, test_subset)
            for i, (workflow, test_subset) in enumerate(zip(workflows, test_subsets))
        ]

        workflow_results = await asyncio.gather(*workflow_tasks)

        # 验证并发结果
        total_predictions = sum(len(results) for results in workflow_results)
        assert total_predictions == len(test_data)

        # 计算每个工作流的准确率
        workflow_accuracies = []
        for i, results in enumerate(workflow_results):
            if results:
                correct = sum(
                    1
                    for r in results
                    if r["prediction"].predicted_outcome == r["actual"]
                )
                accuracy = correct / len(results)
                workflow_accuracies.append(accuracy)
                print(f"  工作流{i}: {len(results)}个预测, 准确率={accuracy:.3f}")

        assert len(workflow_accuracies) == workflow_count

        print("✅ 并发工作流处理测试通过:")
        print(f"  工作流数量: {workflow_count}")
        print(f"  总预测数: {total_predictions}")
        print(f"  平均准确率: {np.mean(workflow_accuracies):.3f}")

    async def test_workflow_error_handling_and_recovery(self):
        """测试工作流错误处理和恢复"""
        training_data, test_data = create_test_dataset(150, 50)

        # 创建工作流
        selector = MockStrategySelector()
        ensemble_predictor = MockEnsemblePredictor()

        # 创建正常策略和有问题的策略
        normal_strategy = MockMLStrategy(
            MLStrategyType.POISSON, "normal_strategy", weight=1.0
        )
        await normal_strategy.train(training_data)

        # 创建未训练的策略（会失败）
        untrained_strategy = MockMLStrategy(
            MLStrategyType.ENSEMBLE, "untrained_strategy", weight=1.0
        )
        # 不训练，模拟错误情况

        # 注册策略
        selector.register_strategy(normal_strategy)
        selector.register_strategy(untrained_strategy)
        ensemble_predictor.add_strategy(normal_strategy)
        ensemble_predictor.add_strategy(untrained_strategy)

        # 测试错误处理
        error_handling_results = []

        for _, test_match in test_data.iterrows():
            match_data = {
                "home_team": test_match["home_team"],
                "away_team": test_match["away_team"],
                "match_id": f"error_test_{len(error_handling_results)}",
            }

            try:
                # 1. 策略选择（应该能处理未训练策略）
                best_strategy = selector.select_best_strategy(match_data, "accuracy")

                # 2. 集成预测（应该能处理部分失败）
                ensemble_prediction = await ensemble_predictor.predict(match_data)

                # 3. 单策略预测（可能失败）
                single_prediction = None
                if best_strategy and best_strategy.is_trained:
                    single_prediction = await best_strategy.predict(match_data)

                error_handling_results.append(
                    {
                        "match_id": match_data["match_id"],
                        "success": True,
                        "ensemble_success": ensemble_prediction is not None,
                        "single_success": single_prediction is not None,
                        "selected_strategy": (
                            best_strategy.name if best_strategy else None
                        ),
                    }
                )

            except Exception as e:
                error_handling_results.append(
                    {
                        "match_id": match_data["match_id"],
                        "success": False,
                        "error": str(e),
                    }
                )

        # 验证错误处理结果
        successful_cases = [r for r in error_handling_results if r["success"]]
        failed_cases = [r for r in error_handling_results if not r["success"]]

        # 大部分情况应该成功
        success_rate = len(successful_cases) / len(error_handling_results)
        assert success_rate > 0.8  # 至少80%成功率

        # 集成预测应该有更高的成功率（因为容错性）
        ensemble_success_rate = sum(
            1 for r in successful_cases if r["ensemble_success"]
        ) / len(successful_cases)
        assert ensemble_success_rate > 0.5

        print("✅ 工作流错误处理测试通过:")
        print(
            f"  成功率: {success_rate:.3f} ({len(successful_cases)}/{len(error_handling_results)})"
        )
        print(f"  集成预测成功率: {ensemble_success_rate:.3f}")
        print(f"  失败案例: {len(failed_cases)}")

    async def test_workflow_performance_monitoring(self):
        """测试工作流性能监控"""
        training_data, test_data = create_test_dataset(200, 100)

        # 性能监控器
        class PerformanceMonitor:
            def __init__(self):
                self.metrics = {
                    "training_times": [],
                    "prediction_times": [],
                    "strategy_selections": {},
                    "ensemble_predictions": 0,
                    "single_predictions": 0,
                    "errors": 0,
                }

            def record_training_time(self, strategy_name: str, time: float):
                self.metrics["training_times"].append(
                    {"strategy": strategy_name, "time": time}
                )

            def record_prediction_time(self, prediction_type: str, time: float):
                self.metrics["prediction_times"].append(
                    {"type": prediction_type, "time": time}
                )

            def record_strategy_selection(self, strategy_name: str):
                self.metrics["strategy_selections"][strategy_name] = (
                    self.metrics["strategy_selections"].get(strategy_name, 0) + 1
                )

            def record_prediction_type(self, is_ensemble: bool):
                if is_ensemble:
                    self.metrics["ensemble_predictions"] += 1
                else:
                    self.metrics["single_predictions"] += 1

            def record_error(self):
                self.metrics["errors"] += 1

            def get_summary(self) -> dict[str, Any]:
                training_times = [t["time"] for t in self.metrics["training_times"]]
                prediction_times = [t["time"] for t in self.metrics["prediction_times"]]

                return {
                    "total_strategies": len(
                        set(t["strategy"] for t in self.metrics["training_times"])
                    ),
                    "avg_training_time": (
                        np.mean(training_times) if training_times else 0
                    ),
                    "avg_prediction_time": (
                        np.mean(prediction_times) if prediction_times else 0
                    ),
                    "strategy_selections": self.metrics["strategy_selections"],
                    "ensemble_ratio": self.metrics["ensemble_predictions"]
                    / max(
                        1,
                        self.metrics["ensemble_predictions"]
                        + self.metrics["single_predictions"],
                    ),
                    "error_rate": self.metrics["errors"]
                    / max(1, len(self.metrics["prediction_times"])),
                    "total_predictions": len(self.metrics["prediction_times"]),
                }

        monitor = PerformanceMonitor()

        # 创建工作流
        selector = MockStrategySelector()
        ensemble_predictor = MockEnsemblePredictor()

        # 训练策略并监控性能
        strategies = [
            MockMLStrategy(MLStrategyType.POISSON, "monitor_poisson", weight=1.0),
            MockMLStrategy(MLStrategyType.ENSEMBLE, "monitor_ensemble", weight=0.8),
        ]

        for strategy in strategies:
            start_time = datetime.now()
            await strategy.train(training_data)
            training_time = (datetime.now() - start_time).total_seconds()
            monitor.record_training_time(strategy.name, training_time)

            selector.register_strategy(strategy)
            ensemble_predictor.add_strategy(strategy)

        # 预测并监控性能
        for _, test_match in test_data.iterrows():
            match_data = {
                "home_team": test_match["home_team"],
                "away_team": test_match["away_team"],
                "match_id": f"monitor_{len(monitor.metrics['prediction_times'])}",
            }

            try:
                # 策略选择
                start_time = datetime.now()
                best_strategy = selector.select_best_strategy(match_data, "accuracy")
                selection_time = (datetime.now() - start_time).total_seconds()
                monitor.record_prediction_time("selection", selection_time)

                if best_strategy:
                    monitor.record_strategy_selection(best_strategy.name)

                # 集成预测
                start_time = datetime.now()
                ensemble_prediction = await ensemble_predictor.predict(match_data)
                ensemble_time = (datetime.now() - start_time).total_seconds()
                monitor.record_prediction_time("ensemble", ensemble_time)

                if ensemble_prediction:
                    monitor.record_prediction_type(True)

                # 单策略预测
                if best_strategy and best_strategy.is_trained:
                    start_time = datetime.now()
                    single_prediction = await best_strategy.predict(match_data)
                    single_time = (datetime.now() - start_time).total_seconds()
                    monitor.record_prediction_time("single", single_time)

                    if single_prediction:
                        monitor.record_prediction_type(False)

            except Exception:
                monitor.record_error()

        # 获取性能摘要
        performance_summary = monitor.get_summary()

        # 验证性能监控结果
        assert performance_summary["total_strategies"] == 2
        assert performance_summary["avg_training_time"] > 0
        assert performance_summary["avg_prediction_time"] > 0
        assert len(performance_summary["strategy_selections"]) > 0
        assert 0 <= performance_summary["ensemble_ratio"] <= 1
        assert performance_summary["total_predictions"] > 0

        print("✅ 工作流性能监控测试通过:")
        print(f"  策略数量: {performance_summary['total_strategies']}")
        print(f"  平均训练时间: {performance_summary['avg_training_time']:.3f}s")
        print(f"  平均预测时间: {performance_summary['avg_prediction_time']:.3f}s")
        print(f"  集成预测比例: {performance_summary['ensemble_ratio']:.3f}")
        print(f"  总预测数: {performance_summary['total_predictions']}")
        print(f"  错误率: {performance_summary['error_rate']:.3f}")
        print(f"  策略选择分布: {performance_summary['strategy_selections']}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
