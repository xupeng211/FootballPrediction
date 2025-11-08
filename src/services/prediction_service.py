"""
预测服务
Prediction Service

提供足球预测的核心业务逻辑。
Provides core business logic for football predictions.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """预测结果"""

    match_id: int
    home_team_id: int
    away_team_id: int
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    confidence_score: float
    predicted_outcome: str
    created_at: datetime


class PredictionService:
    """预测服务类"""

    def __init__(self):
        """初始化预测服务"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def predict_match(
        self, match_data: dict[str, Any], model_name: str = "default"
    ) -> PredictionResult:
        """
        预测单场比赛结果
        Predict single match result

        Args:
            match_data: 比赛数据
            model_name: 模型名称

        Returns:
            预测结果
        """
        try:
            self.logger.info(
                f"Predicting match {match_data.get('match_id')} using model {model_name}"
            )

            # 基础预测逻辑（这里应该实现实际的机器学习模型）
            home_team_id = match_data.get("home_team_id")
            away_team_id = match_data.get("away_team_id")

            # 简单的预测算法（实际应该使用机器学习模型）
            import random

            home_prob = random.uniform(0.2, 0.8)
            away_prob = random.uniform(0.1, 0.6)
            draw_prob = max(0.1, 1.0 - home_prob - away_prob)

            # 归一化概率
            total = home_prob + draw_prob + away_prob
            home_prob /= total
            draw_prob /= total
            away_prob /= total

            # 确定预测结果
            if home_prob > draw_prob and home_prob > away_prob:
                predicted_outcome = "home_win"
            elif away_prob > home_prob and away_prob > draw_prob:
                predicted_outcome = "away_win"
            else:
                predicted_outcome = "draw"

            # 计算置信度
            confidence_score = max(home_prob, draw_prob, away_prob)

            result = PredictionResult(
                match_id=match_data.get("match_id"),
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                home_win_prob=home_prob,
                draw_prob=draw_prob,
                away_win_prob=away_prob,
                confidence_score=confidence_score,
                predicted_outcome=predicted_outcome,
                created_at=datetime.utcnow(),
            )

            self.logger.info(
                f"Prediction completed for match {match_data.get('match_id')}"
            )
            return result

        except Exception as e:
            self.logger.error(
                f"Error predicting match {match_data.get('match_id')}: {e}"
            )
            raise

    async def predict_match_async(
        self, match_data: dict[str, Any], model_name: str = "default"
    ) -> PredictionResult:
        """
        异步预测单场比赛结果
        Asynchronously predict single match result

        Args:
            match_data: 比赛数据
            model_name: 模型名称

        Returns:
            预测结果
        """
        return await asyncio.get_event_loop().run_in_executor(
            None, self.predict_match, match_data, model_name
        )

    def predict_batch(
        self, matches_data: list[dict[str, Any]], model_name: str = "default"
    ) -> list[PredictionResult]:
        """
        批量预测比赛结果
        Batch predict match results

        Args:
            matches_data: 比赛数据列表
            model_name: 模型名称

        Returns:
            预测结果列表
        """
        results = []
        for match_data in matches_data:
            try:
                result = self.predict_match(match_data, model_name)
                results.append(result)
            except Exception as e:
                self.logger.error(
                    f"Error in batch prediction for match {match_data.get('match_id')}: {e}"
                )
                # 可以选择跳过失败的预测或创建一个默认结果
                continue

        self.logger.info(
            f"Batch prediction completed: {len(results)} out of {len(matches_data)} matches"
        )
        return results

    async def predict_batch_async(
        self,
        matches_data: list[dict[str, Any]],
        model_name: str = "default",
        max_concurrent: int = 10,
    ) -> list[PredictionResult]:
        """
        异步批量预测比赛结果
        Asynchronously batch predict match results

        Args:
            matches_data: 比赛数据列表
            model_name: 模型名称
            max_concurrent: 最大并发数

        Returns:
            预测结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def predict_single(match_data):
            async with semaphore:
                return await self.predict_match_async(match_data, model_name)

        tasks = [predict_single(match_data) for match_data in matches_data]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤异常结果
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Error in async batch prediction: {result}")
            else:
                valid_results.append(result)

        return valid_results

    def get_prediction_confidence(
        self, prediction_result: PredictionResult
    ) -> dict[str, Any]:
        """
        获取预测置信度分析
        Get prediction confidence analysis

        Args:
            prediction_result: 预测结果

        Returns:
            置信度分析
        """
        confidence = prediction_result.confidence_score

        if confidence >= 0.8:
            level = "high"
            description = "高置信度预测"
        elif confidence >= 0.6:
            level = "medium"
            description = "中等置信度预测"
        else:
            level = "low"
            description = "低置信度预测"

        return {
            "confidence_score": confidence,
            "confidence_level": level,
            "description": description,
            "recommended": confidence >= 0.6,
        }

    def validate_prediction_input(self, match_data: dict[str, Any]) -> bool:
        """
        验证预测输入数据
        Validate prediction input data

        Args:
            match_data: 比赛数据

        Returns:
            验证结果
        """
        required_fields = ["match_id", "home_team_id", "away_team_id"]

        for field in required_fields:
            if field not in match_data:
                self.logger.error(f"Missing required field: {field}")
                return False

        return True


# 全局预测服务实例
_prediction_service: PredictionService | None = None


def get_prediction_service() -> PredictionService:
    """获取预测服务实例"""
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = PredictionService()
    return _prediction_service


# 便捷函数
def predict_match(
    match_data: dict[str, Any], model_name: str = "default"
) -> PredictionResult:
    """
    便捷的预测函数
    Convenience prediction function

    Args:
        match_data: 比赛数据
        model_name: 模型名称

    Returns:
        预测结果
    """
    service = get_prediction_service()
    return service.predict_match(match_data, model_name)


async def predict_match_async(
    match_data: dict[str, Any], model_name: str = "default"
) -> PredictionResult:
    """
    便捷的异步预测函数
    Convenience async prediction function

    Args:
        match_data: 比赛数据
        model_name: 模型名称

    Returns:
        预测结果
    """
    service = get_prediction_service()
    return await service.predict_match_async(match_data, model_name)
