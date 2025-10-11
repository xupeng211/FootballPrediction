# mypy: ignore-errors
"""
集成策略
Ensemble Strategy

组合多个预测策略的结果，通过加权投票或其他集成方法提高预测准确性。
Combines multiple prediction strategies through weighted voting or other ensemble methods.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np
from dataclasses import dataclass
from enum import Enum

from .base import (
    PredictionStrategy,
    PredictionInput,
    PredictionOutput,
    StrategyType,
    StrategyMetrics,
)
from ..models.prediction import Prediction


class EnsembleMethod(Enum):
    """集成方法枚举"""

    WEIGHTED_AVERAGE = "weighted_average"  # 加权平均
    MAJORITY_VOTING = "majority_voting"  # 多数投票
    STACKING = "stacking"  # 堆叠
    BAGGING = "bagging"  # 装袋
    DYNAMIC_WEIGHTING = "dynamic_weighting"  # 动态权重


@dataclass
class StrategyWeight:
    """策略权重配置"""

    strategy_name: str
    base_weight: float
    dynamic_weight: Optional[float] = None
    performance_weight: Optional[float] = None
    recent_accuracy: Optional[float] = None


@dataclass
class EnsembleResult:
    """集成结果"""

    final_prediction: Tuple[int, int]
    confidence: float
    strategy_contributions: Dict[str, Dict[str, Any]]
    consensus_score: float
    disagreement_level: float


class EnsembleStrategy(PredictionStrategy):
    """集成预测策略

    组合多个子策略的预测结果，通过智能加权提高整体准确性。
    Combines predictions from multiple sub-strategies through intelligent weighting.
    """

    def __init__(self, name: str = "ensemble_predictor"):
        super().__init__(name, StrategyType.ENSEMBLE)
        self._sub_strategies: Dict[str, PredictionStrategy] = {}
        self._strategy_weights: Dict[str, StrategyWeight] = {}
        self._ensemble_method = EnsembleMethod.WEIGHTED_AVERAGE
        self._performance_history: Dict[str, List[float]] = {}
        self._consensus_threshold = 0.7
        self._max_disagreement = 2.0

    async def initialize(self, config: Dict[str, Any]) -> None:
        """初始化集成策略

        Args:
            config: 配置参数，包含：
                - sub_strategies: 子策略配置列表
                - ensemble_method: 集成方法
                - strategy_weights: 策略权重配置
                - consensus_threshold: 共识阈值
                - performance_window: 性能评估窗口
        """
        self._config = config
        self._ensemble_method = EnsembleMethod(
            config.get("ensemble_method", "weighted_average")
        )
        self._consensus_threshold = config.get("consensus_threshold", 0.7)
        self._max_disagreement = config.get("max_disagreement", 2.0)
        self._performance_window = config.get("performance_window", 50)

        # 初始化子策略
        await self._initialize_sub_strategies(config.get("sub_strategies", []))

        # 初始化策略权重
        await self._initialize_strategy_weights(config.get("strategy_weights", {}))

        self._is_initialized = True
        print(
            f"集成策略 '{self.name}' 初始化成功，包含 {len(self._sub_strategies)} 个子策略"
        )

    async def _initialize_sub_strategies(
        self, strategies_config: List[Dict[str, Any]]
    ) -> None:
        """初始化子策略"""
        from .ml_model import MLModelStrategy
        from .statistical import StatisticalStrategy
        from .historical import HistoricalStrategy

        strategy_classes = {
            "ml_model": MLModelStrategy,
            "statistical": StatisticalStrategy,
            "historical": HistoricalStrategy,
        }

        for strategy_config in strategies_config:
            strategy_type = strategy_config.get("type")
            strategy_name = strategy_config.get("name", strategy_type)
            strategy_enabled = strategy_config.get("enabled", True)

            if not strategy_enabled:
                continue

            if strategy_type in strategy_classes:
                # 创建策略实例
                strategy = strategy_classes[strategy_type](strategy_name)  # type: ignore

                # 初始化策略
                await strategy.initialize(strategy_config.get("config", {}))

                # 添加到子策略列表
                self._sub_strategies[strategy_name] = strategy

                # 初始化性能历史
                self._performance_history[strategy_name] = []

                print(f"子策略 '{strategy_name}' ({strategy_type}) 初始化成功")

    async def _initialize_strategy_weights(
        self, weights_config: Dict[str, float]
    ) -> None:
        """初始化策略权重"""
        # 默认权重分配
        default_weights = {"ml_model": 0.4, "statistical": 0.35, "historical": 0.25}

        # 使用配置中的权重，如果没有则使用默认值
        for strategy_name in self._sub_strategies.keys():
            base_weight = weights_config.get(
                strategy_name, default_weights.get(strategy_name, 0.33)
            )
            self._strategy_weights[strategy_name] = StrategyWeight(
                strategy_name=strategy_name, base_weight=base_weight
            )

        # 归一化权重
        total_weight = sum(w.base_weight for w in self._strategy_weights.values())
        if total_weight > 0:
            for weight in self._strategy_weights.values():
                weight.base_weight = weight.base_weight / total_weight

    async def predict(self, input_data: PredictionInput) -> PredictionOutput:
        """执行集成预测"""
        if not self._is_initialized:
            raise RuntimeError("策略未初始化")

        start_time = time.time()

        # 验证输入
        if not await self.validate_input(input_data):
            raise ValueError("输入数据无效")

        # 并行执行所有子策略预测
        strategy_predictions = await self._execute_all_strategies(input_data)

        # 根据集成方法组合结果
        if self._ensemble_method == EnsembleMethod.WEIGHTED_AVERAGE:
            ensemble_result = await self._weighted_average_ensemble(
                input_data, strategy_predictions
            )
        elif self._ensemble_method == EnsembleMethod.MAJORITY_VOTING:
            ensemble_result = await self._majority_voting_ensemble(
                input_data, strategy_predictions
            )
        elif self._ensemble_method == EnsembleMethod.DYNAMIC_WEIGHTING:
            ensemble_result = await self._dynamic_weighting_ensemble(
                input_data, strategy_predictions
            )
        else:
            # 默认使用加权平均
            ensemble_result = await self._weighted_average_ensemble(
                input_data, strategy_predictions
            )

        # 计算最终置信度
        final_confidence = await self._calculate_ensemble_confidence(
            input_data, ensemble_result
        )

        # 创建特征重要性（基于策略贡献）
        feature_importance = {
            f"strategy_{name}": contribution.get("weight", 0)
            for name, contribution in ensemble_result.strategy_contributions.items()
        }

        # 创建概率分布
        probability_distribution = await self._calculate_ensemble_probabilities(
            strategy_predictions
        )

        # 创建输出
        output = PredictionOutput(
            predicted_home_score=ensemble_result.final_prediction[0],
            predicted_away_score=ensemble_result.final_prediction[1],
            confidence=final_confidence,
            probability_distribution=probability_distribution,
            feature_importance=feature_importance,
            metadata={
                "method": f"ensemble_{self._ensemble_method.value}",
                "strategies_used": list(strategy_predictions.keys()),
                "consensus_score": ensemble_result.consensus_score,
                "disagreement_level": ensemble_result.disagreement_level,
                "strategy_predictions": {
                    name: {
                        "prediction": (
                            pred.predicted_home_score,
                            pred.predicted_away_score,
                        ),
                        "confidence": pred.confidence,
                    }
                    for name, pred in strategy_predictions.items()
                },
            },
        )

        output.execution_time_ms = (time.time() - start_time) * 1000
        output.strategy_used = self.name

        # 后处理
        output = await self.post_process(output)

        return output

    async def batch_predict(
        self, inputs: List[PredictionInput]
    ) -> List[PredictionOutput]:
        """批量预测"""
        outputs = []
        for input_data in inputs:
            output = await self.predict(input_data)
            outputs.append(output)
        return outputs

    async def _execute_all_strategies(
        self, input_data: PredictionInput
    ) -> Dict[str, PredictionOutput]:
        """并行执行所有子策略"""
        tasks = []
        strategy_names = []

        for name, strategy in self._sub_strategies.items():
            if strategy.is_healthy():
                tasks.append(strategy.predict(input_data))
                strategy_names.append(name)

        # 并行执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 收集成功的结果
        predictions = {}
        for name, result in zip(strategy_names, results):
            if isinstance(result, Exception):
                print(f"策略 '{name}' 预测失败: {result}")
            else:
                predictions[name] = result

        return predictions  # type: ignore

    async def _weighted_average_ensemble(
        self,
        input_data: PredictionInput,
        strategy_predictions: Dict[str, PredictionOutput],
    ) -> EnsembleResult:
        """加权平均集成"""
        total_home = 0.0
        total_away = 0.0
        total_weight = 0.0
        strategy_contributions = {}

        for name, prediction in strategy_predictions.items():
            weight = self._strategy_weights[name].base_weight

            # 考虑策略的置信度调整权重
            confidence_adjusted_weight = weight * prediction.confidence

            total_home += prediction.predicted_home_score * confidence_adjusted_weight
            total_away += prediction.predicted_away_score * confidence_adjusted_weight
            total_weight += confidence_adjusted_weight

            strategy_contributions[name] = {
                "weight": confidence_adjusted_weight,
                "contribution": (
                    prediction.predicted_home_score * confidence_adjusted_weight,
                    prediction.predicted_away_score * confidence_adjusted_weight,
                ),
                "confidence": prediction.confidence,
            }

        # 计算加权平均
        if total_weight > 0:
            final_home = total_home / total_weight
            final_away = total_away / total_weight
        else:
            final_home, final_away = 1, 1

        # 计算共识度和分歧度
        consensus_score = await self._calculate_consensus_score(strategy_predictions)
        disagreement_level = await self._calculate_disagreement_level(
            strategy_predictions
        )

        return EnsembleResult(
            final_prediction=(int(round(final_home)), int(round(final_away))),
            confidence=np.mean([p.confidence for p in strategy_predictions.values()]),  # type: ignore
            strategy_contributions=strategy_contributions,
            consensus_score=consensus_score,
            disagreement_level=disagreement_level,
        )

    async def _majority_voting_ensemble(
        self,
        input_data: PredictionInput,
        strategy_predictions: Dict[str, PredictionOutput],
    ) -> EnsembleResult:
        """多数投票集成"""
        # 收集所有预测结果
        predictions = list(
            p.predicted_home_score for p in strategy_predictions.values()
        )

        # 找到最常见的预测
        prediction_counts = {}  # type: ignore
        for pred in predictions:
            key = pred
            prediction_counts[key] = prediction_counts.get(key, 0) + 1

        # 获取最多票数的预测
        max_votes = max(prediction_counts.values())
        most_common_predictions = [
            k for k, v in prediction_counts.items() if v == max_votes
        ]

        # 如果有多个预测得票相同，使用加权平均
        if len(most_common_predictions) > 1:
            return await self._weighted_average_ensemble(
                input_data, strategy_predictions
            )

        final_home = most_common_predictions[0]

        # 对客队得分做同样处理
        away_predictions = list(
            p.predicted_away_score for p in strategy_predictions.values()
        )
        away_counts = {}  # type: ignore
        for pred in away_predictions:
            key = pred
            away_counts[key] = away_counts.get(key, 0) + 1

        max_away_votes = max(away_counts.values())
        most_common_away = [k for k, v in away_counts.items() if v == max_away_votes]

        if len(most_common_away) > 1:
            final_away = int(np.mean(away_predictions))
        else:
            final_away = most_common_away[0]

        # 计算共识度和分歧度
        consensus_score = max_votes / len(strategy_predictions)
        disagreement_level = 1 - consensus_score

        strategy_contributions = {
            name: {
                "weight": 1.0 / len(strategy_predictions),
                "vote": (pred.predicted_home_score, pred.predicted_away_score),
                "confidence": pred.confidence,
            }
            for name, pred in strategy_predictions.items()
        }

        return EnsembleResult(
            final_prediction=(final_home, final_away),
            confidence=np.mean([p.confidence for p in strategy_predictions.values()]),  # type: ignore
            strategy_contributions=strategy_contributions,
            consensus_score=consensus_score,
            disagreement_level=disagreement_level,
        )

    async def _dynamic_weighting_ensemble(
        self,
        input_data: PredictionInput,
        strategy_predictions: Dict[str, PredictionOutput],
    ) -> EnsembleResult:
        """动态权重集成"""
        # 根据策略最近的性能调整权重
        for name, weight in self._strategy_weights.items():
            if name in self._performance_history:
                recent_performance = self._performance_history[name][-10:]  # 最近10次
                if recent_performance:
                    avg_performance = np.mean(recent_performance)
                    # 性能越好，权重越高
                    weight.dynamic_weight = weight.base_weight * (0.5 + avg_performance)  # type: ignore
                else:
                    weight.dynamic_weight = weight.base_weight
            else:
                weight.dynamic_weight = weight.base_weight

        # 使用动态权重进行加权平均
        total_home = 0.0
        total_away = 0.0
        total_weight = 0.0
        strategy_contributions = {}

        for name, prediction in strategy_predictions.items():
            weight = (
                self._strategy_weights[name].dynamic_weight  # type: ignore
                or self._strategy_weights[name].base_weight
            )

            total_home += prediction.predicted_home_score * weight  # type: ignore
            total_away += prediction.predicted_away_score * weight  # type: ignore
            total_weight += weight  # type: ignore

            strategy_contributions[name] = {
                "weight": weight,
                "dynamic_weight": self._strategy_weights[name].dynamic_weight,
                "base_weight": self._strategy_weights[name].base_weight,
                "confidence": prediction.confidence,
            }

        if total_weight > 0:
            final_home = total_home / total_weight
            final_away = total_away / total_weight
        else:
            final_home, final_away = 1, 1

        consensus_score = await self._calculate_consensus_score(strategy_predictions)
        disagreement_level = await self._calculate_disagreement_level(
            strategy_predictions
        )

        return EnsembleResult(
            final_prediction=(int(round(final_home)), int(round(final_away))),
            confidence=np.mean([p.confidence for p in strategy_predictions.values()]),  # type: ignore
            strategy_contributions=strategy_contributions,
            consensus_score=consensus_score,
            disagreement_level=disagreement_level,
        )

    async def _calculate_consensus_score(
        self, strategy_predictions: Dict[str, PredictionOutput]
    ) -> float:
        """计算策略共识度"""
        if len(strategy_predictions) < 2:
            return 1.0

        home_scores = [p.predicted_home_score for p in strategy_predictions.values()]
        away_scores = [p.predicted_away_score for p in strategy_predictions.values()]

        # 计算标准差，标准差越小，共识度越高
        home_std = np.std(home_scores)
        away_std = np.std(away_scores)

        # 转换为共识度分数 (0-1)
        avg_std = (home_std + away_std) / 2
        consensus = max(0, 1 - avg_std / 2)  # 假设标准差2为完全不一致  # type: ignore

        return consensus  # type: ignore

    async def _calculate_disagreement_level(
        self, strategy_predictions: Dict[str, PredictionOutput]
    ) -> float:
        """计算策略分歧度"""
        if len(strategy_predictions) < 2:
            return 0.0

        home_scores = [p.predicted_home_score for p in strategy_predictions.values()]
        away_scores = [p.predicted_away_score for p in strategy_predictions.values()]

        # 计算最大差异
        max_home_diff = max(home_scores) - min(home_scores)
        max_away_diff = max(away_scores) - min(away_scores)

        # 归一化分歧度
        disagreement = (max_home_diff + max_away_diff) / 2

        return disagreement

    async def _calculate_ensemble_confidence(
        self, input_data: PredictionInput, ensemble_result: EnsembleResult
    ) -> float:
        """计算集成预测的置信度"""
        base_confidence = np.mean(
            [
                contrib.get("confidence", 0.5)
                for contrib in ensemble_result.strategy_contributions.values()
            ]
        )

        # 根据共识度调整置信度
        consensus_bonus = ensemble_result.consensus_score * 0.2

        # 根据分歧度降低置信度
        disagreement_penalty = min(0.3, ensemble_result.disagreement_level * 0.1)

        # 根据策略数量调整置信度
        strategy_count_bonus = min(
            0.1, len(ensemble_result.strategy_contributions) * 0.02
        )

        final_confidence = (
            base_confidence
            + consensus_bonus
            - disagreement_penalty
            + strategy_count_bonus
        )
        final_confidence = max(0.0, min(1.0, final_confidence))

        return final_confidence  # type: ignore

    async def _calculate_ensemble_probabilities(
        self, strategy_predictions: Dict[str, PredictionOutput]
    ) -> Dict[str, float]:
        """计算集成概率分布"""
        # 收集所有策略的概率分布
        all_probabilities = []
        weights = []

        for name, prediction in strategy_predictions.items():
            if prediction.probability_distribution:
                all_probabilities.append(prediction.probability_distribution)
                weights.append(self._strategy_weights[name].base_weight)

        if not all_probabilities:
            return {"home_win": 0.33, "draw": 0.34, "away_win": 0.33}

        # 加权平均概率
        ensemble_probs = {"home_win": 0, "draw": 0, "away_win": 0}
        total_weight = sum(weights)

        for probs, weight in zip(all_probabilities, weights):
            for outcome in ensemble_probs:
                ensemble_probs[outcome] += probs.get(outcome, 0) * weight  # type: ignore

        # 归一化
        if total_weight > 0:
            for outcome in ensemble_probs:
                ensemble_probs[outcome] /= total_weight  # type: ignore

        # 确保概率总和为1
        total_prob = sum(ensemble_probs.values())
        if total_prob > 0:
            for outcome in ensemble_probs:
                ensemble_probs[outcome] /= total_prob  # type: ignore

        return ensemble_probs  # type: ignore

    async def update_metrics(
        self, actual_results: List[Tuple[Prediction, Dict[str, Any]]]
    ) -> None:
        """更新集成策略性能指标"""
        if not actual_results:
            return

        total_predictions = len(actual_results)
        correct_predictions = 0
        score_errors = []

        for pred, actual in actual_results:
            actual_home = actual.get("actual_home_score", 0)
            actual_away = actual.get("actual_away_score", 0)

            # 精确匹配
            if (
                pred.predicted_home == actual_home  # type: ignore
                and pred.predicted_away == actual_away  # type: ignore
            ):
                correct_predictions += 1

            # 计算得分误差
            error = abs(pred.predicted_home - actual_home) + abs(  # type: ignore
                pred.predicted_away - actual_away  # type: ignore
            )
            score_errors.append(error)

        # 计算集成策略的指标
        accuracy = (
            correct_predictions / total_predictions if total_predictions > 0 else 0
        )
        mean_error = np.mean(score_errors) if score_errors else 0
        precision = max(0, 1 - mean_error / 5)
        recall = accuracy
        f1_score = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        self._metrics = StrategyMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            total_predictions=total_predictions,
            last_updated=datetime.utcnow(),
        )

        # 更新子策略的性能历史（需要子策略的结果）
        # 这里简化处理，实际应该传递每个子策略的预测结果
        for strategy_name in self._sub_strategies.keys():
            if strategy_name not in self._performance_history:
                self._performance_history[strategy_name] = []

            # 假设子策略的性能与集成策略相近（实际应该独立计算）
            self._performance_history[strategy_name].append(accuracy)

            # 限制历史记录长度
            if len(self._performance_history[strategy_name]) > self._performance_window:
                self._performance_history[strategy_name] = self._performance_history[
                    strategy_name
                ][-self._performance_window :]

    def add_strategy(self, strategy: PredictionStrategy, weight: float = 1.0) -> None:
        """动态添加子策略"""
        self._sub_strategies[strategy.name] = strategy
        self._strategy_weights[strategy.name] = StrategyWeight(
            strategy_name=strategy.name, base_weight=weight
        )
        self._performance_history[strategy.name] = []
        print(f"动态添加子策略: {strategy.name}")

    def remove_strategy(self, strategy_name: str) -> None:
        """移除子策略"""
        if strategy_name in self._sub_strategies:
            del self._sub_strategies[strategy_name]
        if strategy_name in self._strategy_weights:
            del self._strategy_weights[strategy_name]
        if strategy_name in self._performance_history:
            del self._performance_history[strategy_name]
        print(f"移除子策略: {strategy_name}")

    def update_strategy_weight(self, strategy_name: str, new_weight: float) -> None:
        """更新策略权重"""
        if strategy_name in self._strategy_weights:
            self._strategy_weights[strategy_name].base_weight = new_weight
            # 重新归一化所有权重
            total_weight = sum(w.base_weight for w in self._strategy_weights.values())
            if total_weight > 0:
                for w in self._strategy_weights.values():
                    w.base_weight = w.base_weight / total_weight
