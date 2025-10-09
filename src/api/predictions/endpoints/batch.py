"""
批量预测端点
Batch Prediction Endpoints

处理批量预测相关的API端点。
"""

from typing import Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.api.dependencies import get_current_user, get_prediction_engine
from src.core.logging_system import get_logger
from src.core.prediction_engine import PredictionEngine

from ..models import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    UpcomingMatchesRequest,
    UpcomingMatchesResponse,
)

logger = get_logger(__name__)

# 创建路由器
router = APIRouter()


@router.post("/predict/batch", response_model=BatchPredictionResponse)
async def predict_matches_batch(
    request: BatchPredictionRequest,
    background_tasks: BackgroundTasks,
    engine: PredictionEngine = Depends(get_prediction_engine),
    current_user: Dict = Depends(get_current_user),
):
    """
    批量预测比赛结果

    Args:
        request: 批量预测请求
        background_tasks: 后台任务
        engine: 预测引擎
        current_user: 当前用户

    Returns:
        BatchPredictionResponse: 批量预测结果
    """
    try:
        logger.info(
            f"用户 {current_user.get('id')} 请求批量预测 {len(request.match_ids)} 场比赛"
        )

        # 检查请求数量限制
        if len(request.match_ids) > 100:
            raise HTTPException(status_code=400, detail="批量预测最多支持100场比赛")

        # 执行批量预测
        results = await engine.batch_predict(
            match_ids=request.match_ids,
            force_refresh=request.force_refresh,
            include_features=request.include_features,
        )

        # 统计结果
        successful = sum(1 for r in results if "error" not in r)
        failed = len(results) - successful

        # 记录预测日志（后台任务）
        background_tasks.add_task(
            _log_batch_prediction,
            user_id=current_user.get("id"),
            match_ids=request.match_ids,
            successful=successful,
            failed=failed,
        )

        return BatchPredictionResponse(
            total=len(results),
            successful=successful,
            failed=failed,
            results=results,
        )

    except Exception as e:
        logger.error(f"批量预测失败: {e}")
        raise HTTPException(status_code=500, detail="批量预测服务暂时不可用")


@router.post("/predict/upcoming", response_model=UpcomingMatchesResponse)
async def predict_upcoming_matches(
    request: UpcomingMatchesRequest,
    engine: PredictionEngine = Depends(get_prediction_engine),
    current_user: Dict = Depends(get_current_user),
):
    """
    预测即将开始的比赛

    Args:
        request: 即将开始比赛预测请求
        engine: 预测引擎
        current_user: 当前用户

    Returns:
        UpcomingMatchesResponse: 预测结果列表
    """
    try:
        logger.info(
            f"用户 {current_user.get('id')} 请求预测未来 {request.hours_ahead} 小时内的比赛"
        )

        results = await engine.predict_upcoming_matches(
            hours_ahead=request.hours_ahead,
            league_ids=request.league_ids,
            force_refresh=request.force_refresh,
        )

        return UpcomingMatchesResponse(
            total=len(results),
            hours_ahead=request.hours_ahead,
            league_ids=request.league_ids,
            results=results,
        )

    except Exception as e:
        logger.error(f"预测即将开始比赛失败: {e}")
        raise HTTPException(status_code=500, detail="预测服务暂时不可用")


async def _log_batch_prediction(
    user_id: int,
    match_ids: List[int],
    successful: int,
    failed: int,
):
    """记录批量预测日志"""
    logger.info(
        f"用户 {user_id} 批量预测完成: "
        f"比赛数={len(match_ids)}, "
        f"成功={successful}, "
        f"失败={failed}"
    )