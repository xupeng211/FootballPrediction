"""
历史预测处理器 / History Prediction Handlers

处理历史预测相关的请求。
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Match
from src.database.models import Predictions as Prediction
from src.utils.response import APIResponse

logger = logging.getLogger(__name__)


async def get_match_prediction_history_handler(
    match_id: int,
    limit: int = Query(10, description="返回记录数量限制", ge=1, le=100),
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """
    获取比赛历史预测的处理器

    Args:
        match_id: 比赛ID
        limit: 返回记录数量限制
        session: 数据库会话

    Returns:
        API响应字典

    Raises:
        HTTPException: 当比赛不存在或查询失败时
    """
    try:
        # 验证比赛存在
        match_query = select(Match).where(Match.id == match_id)
        match_result = await session.execute(match_query)  # type: ignore
        match = match_result.scalar_one_or_none()

        if not match:
            raise HTTPException(status_code=404, detail=f"比赛 {match_id} 不存在")

        # 查询历史预测
        limit_value = limit
        history_query = (
            select(Prediction)
            .where(Prediction.match_id == match_id)
            .order_by(desc(Prediction.created_at))
            .limit(limit_value)
        )

        history_result = await session.execute(history_query)  # type: ignore
        predictions = history_result.scalars().all()

        prediction_list = []
        for prediction in predictions:
            prediction_list.append(
                {
                    "id": prediction.id,
                    "model_version": prediction.model_version,
                    "model_name": prediction.model_name,
                    "home_win_probability": (
                        float(prediction.home_win_probability)
                        if prediction.home_win_probability is not None
                        else 0.0
                    ),
                    "draw_probability": (
                        float(prediction.draw_probability)
                        if prediction.draw_probability is not None
                        else 0.0
                    ),
                    "away_win_probability": (
                        float(prediction.away_win_probability)
                        if prediction.away_win_probability is not None
                        else 0.0
                    ),
                    "predicted_result": prediction.predicted_result,
                    "confidence_score": (
                        float(prediction.confidence_score)
                        if prediction.confidence_score is not None
                        else 0.0
                    ),
                    "created_at": prediction.created_at.isoformat(),
                    "is_correct": prediction.is_correct,
                    "actual_result": prediction.actual_result,
                    "verified_at": (
                        prediction.verified_at.isoformat()
                        if prediction.verified_at
                        and hasattr(prediction.verified_at, "isoformat")
                        else None
                        if prediction.verified_at
                        else None
                    ),
                }
            )

        return APIResponse.success(
            data={
                "match_id": match_id,
                "total_predictions": len(prediction_list),
                "predictions": prediction_list,
            }
        )

    except HTTPException:
        raise
    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"获取比赛 {match_id} 历史预测失败: {e}")
        raise HTTPException(status_code=500, detail="获取历史预测失败")


async def get_recent_predictions_handler(
    hours: int = Query(default=24, description="时间范围（小时）", ge=1, le=168),
    limit: int = Query(50, description="返回记录数量限制", ge=1, le=200),
    session: Optional[AsyncSession] = None,
) -> Dict[str, Any]:
    """
    获取最近预测的处理器

    Args:
        hours: 时间范围（小时）
        limit: 返回记录数量限制
        session: 数据库会话

    Returns:
        API响应字典

    Raises:
        HTTPException: 当查询失败时
    """
    try:
        # 计算时间范围
        since_time = datetime.now() - timedelta(hours=hours)

        # 查询最近预测
        limit_value = limit
        recent_query = (
            select(
                Prediction.id,
                Prediction.match_id,
                Prediction.model_version,
                Prediction.model_name,
                Prediction.predicted_result,
                Prediction.confidence_score,
                Prediction.created_at,
                Prediction.is_correct,
                Match.home_team_id,
                Match.away_team_id,
                Match.match_time,
                Match.match_status,
            )
            .select_from(Prediction.__table__.join(Match.__table__))
            .where(Prediction.created_at >= since_time)
            .order_by(desc(Prediction.created_at))
            .limit(limit_value)
        )

        result = await session.execute(recent_query)  # type: ignore
        predictions = result.fetchall()

        prediction_list = []
        for pred in predictions:
            prediction_list.append(
                {
                    "id": pred.id,
                    "match_id": pred.match_id,
                    "model_version": pred.model_version,
                    "model_name": pred.model_name,
                    "predicted_result": pred.predicted_result,
                    "confidence_score": (
                        float(pred.confidence_score)
                        if pred.confidence_score is not None
                        else 0.0
                    ),
                    "created_at": pred.created_at.isoformat(),
                    "is_correct": pred.is_correct,
                    "match_info": {
                        "home_team_id": pred.home_team_id,
                        "away_team_id": pred.away_team_id,
                        "match_time": pred.match_time.isoformat(),
                        "match_status": pred.match_status,
                    },
                }
            )

        return APIResponse.success(
            data={
                "time_range_hours": hours,
                "total_predictions": len(prediction_list),
                "predictions": prediction_list,
            }
        )

    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"获取最近预测失败: {e}")
        raise HTTPException(status_code=500, detail="获取最近预测失败")
