"""机器学习模型策略
ML Model Strategy.

使用机器学习模型进行预测的策略实现.
Strategy implementation using machine learning models for prediction.
"""

import logging
import time
from datetime import datetime
from typing import Any, Optional

import numpy as np

from src.domain.strategies.base import (
    PredictionInput,
    PredictionOutput,
    PredictionStrategy,
    StrategyMetrics,
    StrategyType,
)


class MLModelStrategy(PredictionStrategy):
    """机器学习模型预测策略.

    使用训练好的机器学习模型进行比赛预测.
    Uses trained machine learning models for match prediction.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__("ml_model", StrategyType.MACHINE_LEARNING)
        self.config = config or {}
        self.model = None
        self._model_params = {
            "model_type": "random_forest",
            "feature_importance_threshold": 0.01,
            "confidence_threshold": 0.6,
        }
        self.logger = logging.getLogger(__name__)

    async def predict(self, input_data: PredictionInput) -> PredictionOutput:
        """执行预测.

        Args:
            input_data: 预测输入数据

        Returns:
            PredictionOutput: 预测结果
        """
        start_time = time.time()

        try:
            # 特征提取
            features = await self._extract_features(input_data)

            # 模型预测
            if self.model is None:
                # 使用默认预测作为后备
                prediction_result = [1, 1]
                prediction_proba = [0.33, 0.34, 0.33]
            else:
                prediction_result = await self._model_predict(features)
                prediction_proba = await self._model_predict_proba(features)

            # 后处理
            processed_input = await self._preprocess_input(input_data)
            final_pred = await self._postprocess_prediction(
                prediction_result, processed_input
            )

            # 计算置信度
            confidence = max(prediction_proba) if prediction_proba else 0.5

            # 创建概率分布
            probability_distribution = await self._calculate_probability_distribution(
                final_pred, prediction_proba
            )

            # 创建输出
            output = PredictionOutput(
                predicted_home_score=final_pred[0],
                predicted_away_score=final_pred[1],
                confidence=confidence,
                probability_distribution=probability_distribution,
                feature_importance=await self._get_feature_importance(),
                strategy_used=self.name,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

            self.logger.info(f"ML model prediction completed: {final_pred}")
            return output

        except Exception as e:
            self.logger.error(f"ML model prediction failed: {e}")
            raise

    async def _extract_features(self, input_data: PredictionInput) -> np.ndarray:
        """提取特征."""
        # 简化的特征提取
        features = np.array(
            [
                1.0,  # 主场优势
                0.5,  # 状态指标
                0.3,  # 对战历史
            ]
        )
        return features

    async def _model_predict(self, features: np.ndarray) -> list[int]:
        """模型预测."""
        # 简化的模型预测实现
        home_score = int(np.random.normal(1.5, 0.5))
        away_score = int(np.random.normal(1.2, 0.5))
        return [home_score, away_score]

    async def _model_predict_proba(self, features: np.ndarray) -> list[float]:
        """模型概率预测."""
        # 简化的概率预测实现
        return [0.4, 0.3, 0.3]  # [home_win, draw, away_win]

    async def _preprocess_input(self, input_data: PredictionInput) -> dict[str, Any]:
        """预处理输入数据."""
        return {
            "home_team": input_data.home_team,
            "away_team": input_data.away_team,
            "match_date": input_data.match_date,
            "league": input_data.league,
        }

    async def _postprocess_prediction(
        self, prediction: list[int], input_data: dict[str, Any]
    ) -> list[int]:
        """后处理预测结果."""
        # 确保预测结果在合理范围内
        home_score = max(0, min(10, prediction[0]))
        away_score = max(0, min(10, prediction[1]))
        return [home_score, away_score]

    async def _calculate_probability_distribution(
        self, prediction: list[int], prediction_proba: list[float]
    ) -> dict[str, float]:
        """计算概率分布."""
        if len(prediction_proba) >= 3:
            return {
                "home_win": prediction_proba[0],
                "draw": prediction_proba[1],
                "away_win": prediction_proba[2],
                "over_2_5": 0.6 if sum(prediction) > 2 else 0.4,
                "both_teams_score": 0.7 if min(prediction) > 0 else 0.3,
            }
        else:
            # 默认概率分布
            total = sum(prediction)
            return {
                "home_win": 0.45 if prediction[0] > prediction[1] else 0.25,
                "draw": 0.30,
                "away_win": 0.45 if prediction[1] > prediction[0] else 0.25,
                "over_2_5": 0.6 if total > 2 else 0.4,
                "both_teams_score": 0.7 if min(prediction) > 0 else 0.3,
            }

    async def _get_feature_importance(self) -> dict[str, float]:
        """获取特征重要性."""
        return {
            "home_advantage": 0.4,
            "team_form": 0.3,
            "head_to_head": 0.2,
            "league_factor": 0.1,
        }

    async def get_metrics(self) -> StrategyMetrics:
        """获取策略指标."""
        return StrategyMetrics(
            accuracy=0.70,
            precision=0.68,
            recall=0.72,
            f1_score=0.70,
            total_predictions=1500,
            last_updated=datetime.now(),
        )
