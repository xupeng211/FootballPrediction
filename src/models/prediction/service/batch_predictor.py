"""
批量预测器模块
Batch Predictor Module

处理批量比赛预测的逻辑。
"""

import logging
from typing import List, Any

from src.core.logging import get_logger

from .predictors import MatchPredictor

logger = get_logger(__name__)


class BatchPredictor:
    """
    批量预测器 / Batch Predictor

    负责处理多个比赛的批量预测任务。
    """

    def __init__(self, predictor: MatchPredictor):
        """
        初始化批量预测器 / Initialize Batch Predictor

        Args:
            predictor (MatchPredictor): 单个预测器实例 / Single predictor instance
        """
        self.predictor = predictor
        logger.info("批量预测器初始化完成")

    async def predict_matches(self, match_ids: List[int]) -> List[Any]:
        """
        批量预测比赛 / Batch Predict Matches

        Args:
            match_ids (List[int]): 比赛ID列表 / List of match IDs

        Returns:
            List[Any]: 预测结果列表 / List of prediction results
        """
        results = []
        failed_predictions = []

        for match_id in match_ids:
            try:
                result = await self.predictor.predict_match(match_id)
                results.append(result)
                logger.debug(f"比赛 {match_id} 预测成功")
            except Exception as e:
                failed_predictions.append({"match_id": match_id, "error": str(e)})
                logger.error(f"批量预测失败 - 比赛 {match_id}: {e}")

        # 记录批量预测统计
        success_count = len(results)
        total_count = len(match_ids)
        success_rate = success_count / total_count if total_count > 0 else 0

        logger.info(
            f"批量预测完成: {success_count}/{total_count} 成功 "
            f"(成功率: {success_rate:.2%})"
        )

        # 如果有失败的预测，记录详细错误
        if failed_predictions:
            logger.warning(f"失败的预测: {len(failed_predictions)} 个")
            for failure in failed_predictions:
                logger.warning(
                    f"比赛 {failure['match_id']}: {failure['error']}"
                )

        return results

    async def predict_matches_with_details(self, match_ids: List[int]) -> dict:
        """
        带详细信息的批量预测 / Batch Predict with Details

        Args:
            match_ids (List[int]): 比赛ID列表 / List of match IDs

        Returns:
            dict: 包含预测结果和统计信息的字典 / Dictionary containing results and statistics
        """
        results = []
        failed_predictions = []

        for match_id in match_ids:
            try:
                result = await self.predictor.predict_match(match_id)
                results.append(result)
            except Exception as e:
                failed_predictions.append({
                    "match_id": match_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                logger.error(f"批量预测失败 - 比赛 {match_id}: {e}")

        # 计算统计信息
        success_count = len(results)
        total_count = len(match_ids)
        success_rate = success_count / total_count if total_count > 0 else 0

        batch_stats = {
            "total_requested": total_count,
            "successful_predictions": success_count,
            "failed_predictions": len(failed_predictions),
            "success_rate": success_rate,
            "failure_details": failed_predictions
        }

        return {
            "predictions": results,
            "statistics": batch_stats
        }

    def get_batch_performance_metrics(self) -> dict:
        """
        获取批量预测性能指标 / Get Batch Prediction Performance Metrics

        Returns:
            dict: 性能指标 / Performance metrics
        """
        # 这里可以添加性能统计逻辑
        return {
            "total_batches_processed": 0,  # 实现时添加计数器
            "average_batch_size": 0,
            "average_batch_duration": 0,
            "peak_batch_size": 0
        }