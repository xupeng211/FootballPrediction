"""
import asyncio
预测API端点

提供比赛预测相关的API接口：
- 获取比赛预测结果
- 实时生成预测
- 批量预测接口
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_async_session
from src.database.models import Match, Prediction
from src.models.prediction_service import PredictionService
from src.utils.response import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["predictions"])

# 全局预测服务实例
prediction_service = PredictionService()


@router.get(
    "/{match_id}",
    summary="获取比赛预测结果",
    description="获取指定比赛的预测结果，如果不存在则实时生成",
)
async def get_match_prediction(
    match_id: int,
    force_predict: bool = Query(default=False, description="是否强制重新预测"),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """
    获取指定比赛的预测结果

    Args:
        match_id: 比赛ID
        force_predict: 是否强制重新预测
        session: 数据库会话

    Returns:
        API响应，包含预测结果
    """
    try:
        logger.info(f"获取比赛 {match_id} 的预测结果")

        # 查询比赛信息
        match_query = select(Match).where(Match.id == match_id)
        match_result = await session.execute(match_query)
        match = match_result.scalar_one_or_none()

        if not match:
            raise HTTPException(status_code=404, detail=f"比赛 {match_id} 不存在")

        # 查询现有预测结果
        prediction = None
        if not force_predict:
            prediction_query = (
                select(Prediction)
                .where(Prediction.match_id == match_id)
                .order_by(Prediction.created_at.desc())
            )

            prediction_result = await session.execute(prediction_query)
            prediction = prediction_result.scalar_one_or_none()

        if prediction and not force_predict:
            # 返回缓存的预测结果
            logger.info(f"返回缓存的预测结果：比赛 {match_id}")
            return APIResponse.success(
                data={
                    "match_id": match.id,  # 添加顶级match_id字段以匹配测试期望
                    "match_info": {
                        "match_id": match.id,
                        "home_team_id": match.home_team_id,
                        "away_team_id": match.away_team_id,
                        "league_id": match.league_id,
                        "match_time": match.match_time.isoformat(),
                        "match_status": match.match_status,
                        "season": match.season,
                    },
                    "prediction": {
                        "id": prediction.id,
                        "model_version": prediction.model_version,
                        "model_name": prediction.model_name,
                        "home_win_probability": float(prediction.home_win_probability),
                        "draw_probability": float(prediction.draw_probability),
                        "away_win_probability": float(prediction.away_win_probability),
                        "predicted_result": prediction.predicted_result,
                        "confidence_score": float(prediction.confidence_score),
                        "created_at": prediction.created_at.isoformat(),
                        "is_correct": prediction.is_correct,
                        "actual_result": prediction.actual_result,
                    },
                    "source": "cached",
                }
            )
        else:
            # 实时生成预测
            logger.info(f"实时生成预测：比赛 {match_id}")

            # 检查比赛状态，如果已结束则不允许实时预测
            if match.match_status in ["finished", "completed"]:
                logger.warning(f"尝试为已结束的比赛 {match_id} 生成预测")
                raise HTTPException(status_code=400, detail=f"比赛 {match_id} 已结束，无法生成预测")

            prediction_result = await prediction_service.predict_match(match_id)

            return APIResponse.success(
                data={
                    "match_id": match.id,  # 添加顶级match_id字段以匹配测试期望
                    "match_info": {
                        "match_id": match.id,
                        "home_team_id": match.home_team_id,
                        "away_team_id": match.away_team_id,
                        "league_id": match.league_id,
                        "match_time": match.match_time.isoformat(),
                        "match_status": match.match_status,
                        "season": match.season,
                    },
                    "prediction": prediction_result.to_dict(),
                    "source": "real_time",
                }
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取比赛 {match_id} 预测失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取预测结果失败: {e}")


@router.post(
    "/{match_id}/predict",
    summary="实时预测比赛结果",
    description="对指定比赛进行实时预测",
)
async def predict_match(
    match_id: int, session: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """
    对指定比赛进行实时预测

    Args:
        match_id: 比赛ID
        session: 数据库会话

    Returns:
        API响应，包含预测结果
    """
    try:
        logger.info(f"开始预测比赛 {match_id}")

        # 验证比赛存在
        match_query = select(Match).where(Match.id == match_id)
        match_result = await session.execute(match_query)
        match = match_result.scalar_one_or_none()

        if not match:
            raise HTTPException(status_code=404, detail=f"比赛 {match_id} 不存在")

        # 进行预测
        prediction_result = await prediction_service.predict_match(match_id)

        return APIResponse.success(
            data=prediction_result.to_dict(), message=f"比赛 {match_id} 预测完成"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预测比赛 {match_id} 失败: {e}")
        raise HTTPException(status_code=500, detail="预测失败")


@router.post("/batch", summary="批量预测比赛", description="对多场比赛进行批量预测")
async def batch_predict_matches(
    match_ids: List[int], session: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """
    批量预测多场比赛

    Args:
        match_ids: 比赛ID列表
        session: 数据库会话

    Returns:
        API响应，包含批量预测结果
    """
    try:
        logger.info(f"开始批量预测 {len(match_ids)} 场比赛")

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


@router.get(
    "/history/{match_id}",
    summary="获取比赛历史预测",
    description="获取指定比赛的所有历史预测记录",
)
async def get_match_prediction_history(
    match_id: int,
    limit: int = Query(10, description="返回记录数量限制", ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """
    获取比赛的历史预测记录

    Args:
        match_id: 比赛ID
        limit: 返回记录数量限制
        session: 数据库会话

    Returns:
        API响应，包含历史预测记录
    """
    try:
        # 验证比赛存在
        match_query = select(Match).where(Match.id == match_id)
        match_result = await session.execute(match_query)
        match = match_result.scalar_one_or_none()

        if not match:
            raise HTTPException(status_code=404, detail=f"比赛 {match_id} 不存在")

        # 查询历史预测
        # limit 参数已经被 FastAPI 解析为 int 类型
        limit_value = limit
        history_query = (
            select(Prediction)
            .where(Prediction.match_id == match_id)
            .order_by(desc(Prediction.created_at))
            .limit(limit_value)
        )

        history_result = await session.execute(history_query)
        predictions = history_result.scalars().all()

        prediction_list = []
        for prediction in predictions:
            prediction_list.append(
                {
                    "id": prediction.id,
                    "model_version": prediction.model_version,
                    "model_name": prediction.model_name,
                    "home_win_probability": float(prediction.home_win_probability),
                    "draw_probability": float(prediction.draw_probability),
                    "away_win_probability": float(prediction.away_win_probability),
                    "predicted_result": prediction.predicted_result,
                    "confidence_score": float(prediction.confidence_score),
                    "created_at": prediction.created_at.isoformat(),
                    "is_correct": prediction.is_correct,
                    "actual_result": prediction.actual_result,
                    "verified_at": (
                        prediction.verified_at.isoformat()
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
    except Exception as e:
        logger.error(f"获取比赛 {match_id} 历史预测失败: {e}")
        raise HTTPException(status_code=500, detail="获取历史预测失败")


@router.get("/recent", summary="获取最近的预测", description="获取最近的预测记录")
async def get_recent_predictions(
    hours: int = Query(default=24, description="时间范围（小时）", ge=1, le=168),
    limit: int = Query(50, description="返回记录数量限制", ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """
    获取最近的预测记录

    Args:
        hours: 时间范围（小时）
        limit: 返回记录数量限制
        session: 数据库会话

    Returns:
        API响应，包含最近预测记录
    """
    try:
        # 计算时间范围
        since_time = datetime.now() - timedelta(hours=hours)

        # 查询最近预测
        # limit 参数已经被 FastAPI 解析为 int 类型
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

        result = await session.execute(recent_query)
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
                    "confidence_score": float(pred.confidence_score),
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

    except Exception as e:
        logger.error(f"获取最近预测失败: {e}")
        raise HTTPException(status_code=500, detail="获取最近预测失败")


@router.post(
    "/{match_id}/verify",
    summary="验证预测结果",
    description="验证指定比赛的预测结果（比赛结束后调用）",
)
async def verify_prediction(
    match_id: int, session: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """
    验证预测结果

    Args:
        match_id: 比赛ID
        session: 数据库会话

    Returns:
        API响应，包含验证结果
    """
    try:
        logger.info(f"验证比赛 {match_id} 的预测结果")

        # 验证预测结果
        success = await prediction_service.verify_prediction(match_id)

        if success:
            return APIResponse.success(
                data={"match_id": match_id, "verified": True},
                message="预测结果验证完成",
            )
        else:
            return APIResponse.error(
                message="预测结果验证失败",
                data={"match_id": match_id, "verified": False},
            )

    except Exception as e:
        logger.error(f"验证预测结果失败: {e}")
        raise HTTPException(status_code=500, detail="验证预测结果失败")
