import logging

"""
统计分析策略
Statistical Strategy

使用统计方法和数学模型进行预测的策略实现。
Strategy implementation using statistical methods and mathematical models for prediction.
"""

import time
import math
from typing import Any,  Dict[str, Any],  Any, List[Any], Tuple
import numpy as np
from datetime import datetime

from .base import (
    PredictionStrategy,
    PredictionInput,
    PredictionOutput,
    StrategyType,
    StrategyMetrics,
)
from ..models.prediction import Prediction


class StatisticalStrategy(PredictionStrategy):
    """统计分析预测策略

    基于历史数据的统计分析进行预测，包括：
    - 进球率统计
    - 主客场优势分析
    - 近期状态评估
    - 对战历史分析
    - 泊松分布模型
    """

    def __init__(self, name: str = "statistical_analyzer") -> None:
        super().__init__(name, StrategyType.STATISTICAL)
        self._team_stats = {}
        self._head_to_head_stats = {}
        self._league_stats = {}
        self._model_params = {}
        self._min_sample_size = 5
        self.logger = logging.getLogger(__name__)

    async def initialize(self, config: Dict[str, Any]) -> None:
        """初始化统计策略

        Args:
            config: 配置参数，包含：
                - min_sample_size: 最小样本数量
                - weight_recent_games: 近期比赛权重
                - home_advantage_factor: 主场优势因子
                - model_weights: 不同统计模型的权重
        """
        self.config = config
        self._min_sample_size = config.get("min_sample_size", 5)
        self._model_params = {
            "weight_recent_games": config.get("weight_recent_games", 0.7),
            "home_advantage_factor": config.get("home_advantage_factor", 1.2),
            "poisson_lambda": config.get("poisson_lambda", 1.35),
            "model_weights": config.get(
                "model_weights",
                {"poisson": 0.4, "historical": 0.3, "form": 0.2, "head_to_head": 0.1},
            ),
        }

        self._is_initialized = True
        self.logger.info(f"统计策略 '{self.name}' 初始化成功")

    async def predict(self, input_data: PredictionInput) -> PredictionOutput:
        """执行单次预测"""
        if not self._is_initialized:
            raise RuntimeError("策略未初始化")

        start_time = time.time()

        # 验证输入
        if not await self.validate_input(input_data):
            raise ValueError("输入数据无效")

        # 预处理
        processed_input = await self.pre_process(input_data)

        # 执行各种统计模型
        poisson_pred = await self._poisson_prediction(processed_input)
        historical_pred = await self._historical_average_prediction(processed_input)
        form_pred = await self._team_form_prediction(processed_input)
        h2h_pred = await self._head_to_head_prediction(processed_input)

        # 集成预测结果
        final_pred = await self._ensemble_predictions(
            {
                "poisson": poisson_pred,
                "historical": historical_pred,
                "form": form_pred,
                "head_to_head": h2h_pred,
            }
        )

        # 计算置信度
        confidence = await self._calculate_confidence(processed_input, final_pred)

        # 创建概率分布
        probability_distribution = await self._calculate_probability_distribution(
            processed_input, final_pred
        )

        # 创建输出
        output = PredictionOutput(
            predicted_home_score=final_pred[0],
            predicted_away_score=final_pred[1],
            confidence=confidence,
            probability_distribution=probability_distribution,
            feature_importance={
                "poisson_model": self._model_params["model_weights"]["poisson"],
                "historical_avg": self._model_params["model_weights"]["historical"],
                "team_form": self._model_params["model_weights"]["form"],
                "head_to_head": self._model_params["model_weights"]["head_to_head"],
            },
            metadata={
                "method": "statistical_ensemble",
                "predictions_used": {
                    "poisson": poisson_pred,
                    "historical": historical_pred,
                    "form": form_pred,
                    "head_to_head": h2h_pred,
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

    async def _poisson_prediction(self, input_data: PredictionInput) -> Tuple[int, int]:
        """使用泊松分布预测比分"""
        # 检查球队ID是否为空
        if input_data.home_team.id is None or input_data.away_team.id is None:
            return (1, 1)

        # 获取球队平均进球数
        home_avg_goals = await self._get_team_average_goals(
            input_data.home_team.id,
            True,
        )
        away_avg_goals = await self._get_team_average_goals(
            input_data.away_team.id,
            False,
        )

        # 应用主场优势
        home_avg_goals *= self._model_params["home_advantage_factor"]

        # 泊松分布参数
        lambda_home = max(0.1, home_avg_goals)
        lambda_away = max(0.1, away_avg_goals)

        # 转换为整数，保持合理范围
        lambda_home = float(lambda_home)
        lambda_away = float(lambda_away)

        # 计算最可能的比分
        max_prob = 0
        best_score = (1, 1)

        for home_goals in range(0, 6):
            for away_goals in range(0, 6):
                # 泊松概率公式
                prob_home = (
                    math.exp(-lambda_home) * lambda_home**home_goals
                ) / math.factorial(home_goals)
                prob_away = (
                    math.exp(-lambda_away) * lambda_away**away_goals
                ) / math.factorial(away_goals)
                prob = prob_home * prob_away

                if prob > max_prob:
                    max_prob = prob
                    best_score = (home_goals, away_goals)

        return best_score

    async def _historical_average_prediction(
        self, input_data: PredictionInput
    ) -> Tuple[int, int]:
        """基于历史平均得分预测"""
        # 检查球队ID是否为空
        if input_data.home_team.id is None or input_data.away_team.id is None:
            return (1, 1)

        # 获取主队主场平均得分
        home_scores = await self._get_team_home_scores(input_data.home_team.id)
        # 获取客队客场平均得分
        away_scores = await self._get_team_away_scores(input_data.away_team.id)

        if not home_scores or not away_scores:
            return (1, 1)

        avg_home = np.mean([s[0] for s in home_scores])
        avg_away = np.mean([s[1] for s in away_scores])

        # 应用主场优势
        avg_home *= self._model_params["home_advantage_factor"]

        return (int(round(avg_home)), int(round(avg_away)))

    async def _team_form_prediction(
        self, input_data: PredictionInput
    ) -> Tuple[int, int]:
        """基于球队近期状态预测"""
        # 检查球队ID是否为空
        if input_data.home_team.id is None or input_data.away_team.id is None:
            return (1, 1)

        # 获取最近5场比赛
        home_recent = await self._get_recent_games(input_data.home_team.id, 5)
        away_recent = await self._get_recent_games(input_data.away_team.id, 5)

        if not home_recent or not away_recent:
            return (1, 1)

        # 计算近期平均得分（带权重）
        home_weighted = 0
        away_weighted = 0
        total_weight = 0

        for i, (home_score, away_score, is_home) in enumerate(home_recent):
            weight = (i + 1) / len(home_recent)  # 越近的比赛权重越高
            if is_home:
                home_weighted += home_score * weight
            else:
                home_weighted += away_score * weight
            total_weight += weight

        home_avg = home_weighted / total_weight if total_weight > 0 else 1.0

        away_weighted = 0
        total_weight = 0
        for i, (home_score, away_score, is_home) in enumerate(away_recent):
            weight = (i + 1) / len(away_recent)
            if not is_home:
                away_weighted += away_score * weight
            else:
                away_weighted += home_score * weight
            total_weight += weight

        away_avg = away_weighted / total_weight if total_weight > 0 else 1.0

        # 应用主场优势
        home_avg *= self._model_params["home_advantage_factor"]

        return (int(round(home_avg)), int(round(away_avg)))

    async def _head_to_head_prediction(
        self, input_data: PredictionInput
    ) -> Tuple[int, int]:
        """基于对战历史预测"""
        # 检查球队ID是否为空
        if input_data.home_team.id is None or input_data.away_team.id is None:
            return (1, 1)

        h2h_games = await self._get_head_to_head_games(
            input_data.home_team.id,
            input_data.away_team.id,
            limit=10,
        )

        if not h2h_games:
            return (1, 1)

        # 计算平均比分
        home_goals = []
        away_goals = []

        for game in h2h_games:
            if game["home_team_id"] == input_data.home_team.id:
                home_goals.append(game["home_score"])
                away_goals.append(game["away_score"])
            else:
                home_goals.append(game["away_score"])
                away_goals.append(game["home_score"])

        avg_home = np.mean(home_goals)
        avg_away = np.mean(away_goals)

        # 应用主场优势
        avg_home *= self._model_params["home_advantage_factor"]

        return (int(round(avg_home)), int(round(avg_away)))

    async def _ensemble_predictions(
        self, predictions: Dict[str, Tuple[int, int]]
    ) -> Tuple[int, int]:
        """集成多个预测结果"""
        weights = self._model_params["model_weights"]
        total_home = 0
        total_away = 0
        total_weight = 0

        for method, pred in predictions.items():
            if method in weights and pred:
                weight = weights[method]
                total_home += pred[0] * weight
                total_away += pred[1] * weight
                total_weight += weight

        if total_weight > 0:
            avg_home = total_home / total_weight
            avg_away = total_away / total_weight
        else:
            avg_home, avg_away = 1, 1

        return (int(round(avg_home)), int(round(avg_away)))

    async def _calculate_confidence(
        self, input_data: PredictionInput, prediction: Tuple[int, int]
    ) -> float:
        """计算预测置信度"""
        confidence_factors = []

        # 数据完整性
        if input_data.historical_data:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.4)

        # 样本数量
        if input_data.home_team.id is None or input_data.away_team.id is None:
            confidence_factors.append(0.1)
        else:
            home_games = len(await self._get_team_games(input_data.home_team.id))
            away_games = len(await self._get_team_games(input_data.away_team.id))
        if min(home_games, away_games) >= self._min_sample_size * 2:
            confidence_factors.append(0.8)
        elif min(home_games, away_games) >= self._min_sample_size:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.3)

        # 预测一致性
        # 这里简化处理，实际可以比较不同方法的结果一致性
        confidence_factors.append(0.7)

        # 返回平均置信度
        return np.mean(confidence_factors)

    async def _calculate_probability_distribution(
        self, input_data: PredictionInput, prediction: Tuple[int, int]
    ) -> Dict[str, float]:
        """计算结果概率分布"""
        # 基于泊松分布计算概率
        if input_data.home_team.id is None or input_data.away_team.id is None:
            return {"home_win": 0.33, "draw": 0.34, "away_win": 0.33}

        home_avg = await self._get_team_average_goals(input_data.home_team.id, True)
        away_avg = await self._get_team_average_goals(input_data.away_team.id, False)

        home_avg *= self._model_params["home_advantage_factor"]

        # 计算各种结果的概率
        prob_home_win = 0
        prob_draw = 0
        prob_away_win = 0

        for home_goals in range(0, 10):
            for away_goals in range(0, 10):
                prob_home = (
                    math.exp(-home_avg) * home_avg**home_goals
                ) / math.factorial(home_goals)
                prob_away = (
                    math.exp(-away_avg) * away_avg**away_goals
                ) / math.factorial(away_goals)
                prob = prob_home * prob_away

                if home_goals > away_goals:
                    prob_home_win += prob
                elif home_goals == away_goals:
                    prob_draw += prob
                else:
                    prob_away_win += prob

        return {"home_win": prob_home_win, "draw": prob_draw, "away_win": prob_away_win}

    # 以下为辅助方法，实际项目中需要从数据库或缓存获取数据
    async def _get_team_average_goals(self, team_id: int, is_home: bool) -> float:
        """获取球队平均进球数"""
        # 模拟数据，实际应从数据库获取
        return 1.5 if is_home else 1.2

    async def _get_team_home_scores(self, team_id: int) -> List[Tuple[int, int]:
        """获取球队主场比分历史"""
        # 模拟数据
        return [(2, 1), (1, 1), (3, 0), (1, 2), (2, 0)]

    async def _get_team_away_scores(self, team_id: int) -> List[Tuple[int, int]:
        """获取球队客场比分历史"""
        # 模拟数据
        return [(1, 2), (0, 1), (2, 2), (1, 3), (0, 0)]

    async def _get_recent_games(
        self, team_id: int, limit: int
    ) -> List[Tuple[int, int, bool]:
        """获取最近比赛"""
        # 模拟数据，返回(主场得分, 客场得分, 是否主场)
        return [(2, 1, True), (1, 2, False), (3, 0, True), (0, 0, False), (2, 1, True)]

    async def _get_team_games(self, team_id: int) -> List[Dict[str, Any]:
        """获取球队所有比赛"""
        # 模拟数据
        return [{"game_id": i} for i in range(20)]

    async def _get_head_to_head_games(
        self, home_team_id: int, away_team_id: int, limit: int
    ) -> List[Dict[str, Any]:
        """获取对战历史"""
        # 模拟数据
        return [
            {
                "home_team_id": home_team_id,
                "away_team_id": away_team_id,
                "home_score": 2,
                "away_score": 1,
            },
            {
                "home_team_id": away_team_id,
                "away_team_id": home_team_id,
                "home_score": 1,
                "away_score": 1,
            },
        ]

    async def update_metrics(
        self, actual_results: List[Tuple[Prediction, Dict[str, Any]
    ) -> None:
        """更新策略性能指标"""
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
                pred.predicted_home == actual_home
                and pred.predicted_away == actual_away
            ):
                correct_predictions += 1

            # 计算得分误差
            error = abs(pred.predicted_home - actual_home) + abs(
                pred.predicted_away - actual_away
            )
            score_errors.append(error)

        # 计算指标
        accuracy = (
            correct_predictions / total_predictions if total_predictions > 0 else 0
        )
        mean_error = np.mean(score_errors) if score_errors else 0
        precision = max(0, 1 - mean_error / 5)  # 简化的精确率
        recall = accuracy  # 简化处理
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
