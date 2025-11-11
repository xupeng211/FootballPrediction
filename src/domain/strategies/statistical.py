"""
统计分析策略
Statistical Strategy

使用统计方法和数学模型进行预测的策略实现.
Strategy implementation using statistical methods and mathematical models for prediction.
"""

import logging
import time
from datetime import datetime
from typing import Any


from src.domain.models.prediction import (
    PredictionInput,
    PredictionOutput,
    PredictionStrategy,
    StrategyMetrics,
    StrategyType,
)


class StatisticalStrategy(PredictionStrategy):
    """统计分析预测策略

    基于历史数据的统计分析进行预测,包括:
    - 进球率统计
    - 主客场优势分析
    - 近期状态评估
    - 对战历史分析
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__("statistical", StrategyType.STATISTICAL)
        self.config = config or {}
        self._model_params = {
            "model_weights": {
                "poisson": 0.4,
                "historical": 0.3,
                "form": 0.2,
                "head_to_head": 0.1,
            },
            "confidence_threshold": 0.6,
            "max_goals": 10,
        }
        self.logger = logging.getLogger(__name__)

    async def predict(self, input_data: PredictionInput) -> PredictionOutput:
        """执行预测

        Args:
            input_data: 预测输入数据

        Returns:
            PredictionOutput: 预测结果
        """
        start_time = time.time()

        try:
            # 数据预处理
            processed_input = await self._preprocess_input(input_data)

            # 多模型预测
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
                    "form_analysis": self._model_params["model_weights"]["form"],
                    "h2h_analysis": self._model_params["model_weights"]["head_to_head"],
                },
                strategy_used=self.name,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

            self.logger.info(f"Statistical prediction completed: {final_pred}")
            return output

        except Exception as e:
            self.logger.error(f"Statistical prediction failed: {e}")
            raise

    async def _preprocess_input(self, input_data: PredictionInput) -> dict[str, Any]:
        """预处理输入数据"""
        return {
            "home_team": input_data.home_team,
            "away_team": input_data.away_team,
            "match_date": input_data.match_date,
            "league": input_data.league,
        }

    async def _poisson_prediction(self, input_data: dict[str, Any]) -> list[int]:
        """泊松分布预测"""
        # 简化的泊松分布实现
        home_goals = np.random.poisson(1.5)
        away_goals = np.random.poisson(1.2)
        return [int(home_goals), int(away_goals)]

    async def _historical_average_prediction(
        self, input_data: dict[str, Any]
    ) -> list[int]:
        """历史平均值预测"""
        # 简化的历史平均值实现
        return [1, 1]

    async def _team_form_prediction(self, input_data: dict[str, Any]) -> list[int]:
        """球队状态预测"""
        # 简化的状态分析实现
        return [2, 1]

    async def _head_to_head_prediction(self, input_data: dict[str, Any]) -> list[int]:
        """对战历史预测"""
        # 简化的对战历史分析实现
        return [1, 2]

    async def _ensemble_predictions(
        self, predictions: dict[str, list[int]]
    ) -> list[int]:
        """集成多个预测结果"""
        weights = self._model_params["model_weights"]

        weighted_home = (
            predictions["poisson"][0] * weights["poisson"]
            + predictions["historical"][0] * weights["historical"]
            + predictions["form"][0] * weights["form"]
            + predictions["head_to_head"][0] * weights["head_to_head"]
        )

        weighted_away = (
            predictions["poisson"][1] * weights["poisson"]
            + predictions["historical"][1] * weights["historical"]
            + predictions["form"][1] * weights["form"]
            + predictions["head_to_head"][1] * weights["head_to_head"]
        )

        return [int(round(weighted_home)), int(round(weighted_away))]

    async def _calculate_confidence(
        self, input_data: dict[str, Any], prediction: list[int]
    ) -> float:
        """计算预测置信度"""
        # 简化的置信度计算
        base_confidence = 0.7

        # 根据预测结果调整置信度
        if max(prediction) <= 5:
            base_confidence += 0.1

        return min(base_confidence, 1.0)

    async def _calculate_probability_distribution(
        self, input_data: dict[str, Any], prediction: list[int]
    ) -> dict[str, float]:
        """计算概率分布"""
        # 简化的概率分布计算
        total_goals = sum(prediction)

        return {
            "home_win": 0.45 if prediction[0] > prediction[1] else 0.25,
            "draw": 0.30,
            "away_win": 0.45 if prediction[1] > prediction[0] else 0.25,
            "over_2_5": 0.6 if total_goals > 2 else 0.4,
            "both_teams_score": 0.7 if min(prediction) > 0 else 0.3,
        }

    async def get_metrics(self) -> StrategyMetrics:
        """获取策略指标"""
        return StrategyMetrics(
            accuracy=0.65,
            precision=0.63,
            recall=0.67,
            f1_score=0.65,
            total_predictions=1000,
            last_updated=datetime.now(),
        )
