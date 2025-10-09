"""
预测API路由器 / Predictions API Router

整合所有预测相关的API端点。
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Path, Query, Request

from src.database.connection_mod import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession

from .batch_handlers import batch_predict_matches_handler
from .history_handlers import (
    get_match_prediction_history_handler,
    get_recent_predictions_handler,
)
from .prediction_handlers import (
    get_match_prediction_handler,
    predict_match_handler,
    verify_prediction_handler,
)
from .rate_limiter import get_rate_limiter
from .schemas import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    PredictionHistoryResponse,
    PredictionResponse,
    RecentPredictionsResponse,
    VerificationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["predictions"])

# 获取速率限制器
limiter = get_rate_limiter()


@router.get(
    "/{match_id:int}",
    summary="获取比赛预测结果 / Get Match Prediction",
    description=(
        "获取指定比赛的预测结果，如果不存在则实时生成 / "
        "Get prediction result for specified match, generate in real-time if not exists"
    ),
    responses={
        200: {
            "description": "成功获取预测结果 / Successfully retrieved prediction",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "match_id": 12345,
                            "match_info": {
                                "match_id": 12345,
                                "home_team_id": 10,
                                "away_team_id": 20,
                                "league_id": 1,
                                "match_time": "2025-09-15T15:00:00",
                                "match_status": "scheduled",
                                "season": "2024-25",
                            },
                            "prediction": {
                                "model_version": "1.0",
                                "home_win_probability": 0.45,
                                "draw_probability": 0.30,
                                "away_win_probability": 0.25,
                                "predicted_result": "home",
                                "confidence_score": 0.45,
                            },
                        },
                    }
                }
            },
        },
        404: {"description": "比赛不存在 / Match not found"},
        500: {"description": "服务器内部错误 / Internal server error"},
    },
)
@limiter.limit("20/minute")  # 每分钟最多20次请求
async def get_match_prediction(
    request: Request,
    match_id: int = Path(
        ...,
        description="比赛唯一标识符 / Unique match identifier",
        ge=1,
        examples=[12345],
    ),
    force_predict: bool = Query(
        default=False, description="是否强制重新预测 / Whether to force re-prediction"
    ),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """
    获取指定比赛的预测结果 / Get Prediction for Specified Match

    该端点首先检查数据库中是否存在该比赛的缓存预测结果。
    如果存在且未设置force_predict参数，则直接返回缓存结果。
    否则，实时生成新的预测结果并存储到数据库。

    This endpoint first checks if there's a cached prediction result for the match in the database.
    If it exists and force_predict is not set, it returns the cached result directly.
    Otherwise, it generates a new prediction in real-time and stores it in the database.

    Args:
        match_id (int): 比赛唯一标识符，必须大于0 / Unique match identifier, must be greater than 0
        force_predict (bool): 是否强制重新预测，默认为False / Whether to force re-prediction,
            defaults to False
        session (AsyncSession): 数据库会话，由依赖注入提供 / Database session,
            provided by dependency injection

    Returns:
        Dict[str, Any]: API响应字典 / API response dictionary
            - success (bool): 请求是否成功 / Whether request was successful
            - data (Dict): 预测数据 / Prediction data
                - match_id (int): 比赛ID / Match ID
                - match_info (Dict): 比赛信息 / Match information
                - prediction (Dict): 预测结果 / Prediction result

    Raises:
        HTTPException:
            - 404: 当比赛不存在时 / When match does not exist
            - 500: 当预测过程发生错误时 / When prediction process fails
    """
    return await get_match_prediction_handler(request, match_id, force_predict, session)


@router.post(
    "/{match_id:int}/predict",
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
    return await predict_match_handler(match_id, session)


@router.post(
    "/batch",
    summary="批量预测比赛",
    description="对多场比赛进行批量预测",
    response_model=Dict[str, Any],
)
@limiter.limit("5/minute")  # 批量预测：每分钟最多5次（更耗费资源）
async def batch_predict_matches(
    request: Request,
    match_ids: List[int],
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """
    批量预测多场比赛

    Args:
        match_ids: 比赛ID列表
        session: 数据库会话

    Returns:
        API响应，包含批量预测结果
    """
    return await batch_predict_matches_handler(request, match_ids, session)


@router.get(
    "/history/{match_id:int}",
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
    return await get_match_prediction_history_handler(match_id, limit, session)


@router.get(
    "/recent",
    summary="获取最近的预测",
    description="获取最近的预测记录",
)
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
    return await get_recent_predictions_handler(hours, limit, session)


@router.post(
    "/{match_id:int}/verify",
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
    return await verify_prediction_handler(match_id, session)
