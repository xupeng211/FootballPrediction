"""
批量预测处理器 / Batch Prediction Handlers

处理批量预测相关的请求。
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Match
from src.models.prediction_service_mod import PredictionService
from src.utils.response import APIResponse

logger = logging.getLogger(__name__)

# 懒加载prediction服务
_prediction_service = None


def get_prediction_service():
    """获取预测服务实例（懒加载）"""
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = PredictionService()
    return _prediction_service


async def batch_predict_matches_handler(
    request: Request,
    match_ids: List[int],
    session: AsyncSession,
) -> Dict[str, Any]:
    """
    批量预测多场比赛的处理器

    Args:
        request: FastAPI请求对象
        match_ids: 比赛ID列表
        session: 数据库会话

    Returns:
        API响应字典

    Raises:
        HTTPException: 当请求参数错误或预测失败时
    """
    try:
        logger.info(f"开始批量预测 {len(match_ids)} 场比赛")

        # 验证批量大小限制
        if len(match_ids) > 50:
            raise HTTPException(status_code=400, detail="批量预测最多支持50场比赛")

        # 验证比赛存在
        valid_matches_query = select(Match.id).where(Match.id.in_(match_ids))
        valid_matches_result = await session.execute(valid_matches_query)
        valid_match_ids = [row.id for row in valid_matches_result]

        invalid_match_ids = set(match_ids) - set(valid_match_ids)
        if invalid_match_ids:
            logger.warning(f"无效的比赛ID: {invalid_match_ids}")

        # 批量预测
        prediction_service = get_prediction_service()
        results = await prediction_service.batch_predict_matches(valid_match_ids)

        return APIResponse.success(
            data={
                "total_requested": len(match_ids),
                "valid_matches": len(valid_match_ids),
                "successful_predictions": len(results),
                "invalid_match_ids": list(invalid_match_ids),
                "predictions": [result.to_dict() for result in results],
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量预测失败: {e}")
        raise HTTPException(status_code=500, detail="批量预测失败")
