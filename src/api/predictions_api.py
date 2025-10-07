"""
预测API端点
Prediction API Endpoints

提供完整的预测相关API接口，包括：
- 单场比赛预测
- 批量预测
- 预测历史
- 模型性能统计
- 实时预测流

Provides complete prediction-related API endpoints, including:
- Single match prediction
- Batch prediction
- Prediction history
- Model performance statistics
- Real-time prediction stream
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Path
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.api.dependencies import get_current_user, get_prediction_engine
from src.core.prediction_engine import PredictionEngine
from src.database.connection import get_async_session
from src.utils.logger import get_logger

logger = get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])


# Pydantic模型
class PredictionRequest(BaseModel):
    """预测请求模型"""
    match_id: int = Field(..., description="比赛ID", gt=0)
    force_refresh: bool = Field(False, description="是否强制刷新缓存")
    include_features: bool = Field(False, description="是否包含特征信息")


class BatchPredictionRequest(BaseModel):
    """批量预测请求模型"""
    match_ids: List[int] = Field(..., description="比赛ID列表", min_items=1, max_items=100)
    force_refresh: bool = Field(False, description="是否强制刷新缓存")
    include_features: bool = Field(False, description="是否包含特征信息")


class UpcomingMatchesRequest(BaseModel):
    """即将开始比赛预测请求模型"""
    hours_ahead: int = Field(24, description="预测未来多少小时内的比赛", ge=1, le=168)
    league_ids: Optional[List[int]] = Field(None, description="指定联赛ID列表")
    force_refresh: bool = Field(False, description="是否强制刷新缓存")


class PredictionResponse(BaseModel):
    """预测响应模型"""
    match_id: int
    prediction: str
    probabilities: Dict[str, float]
    confidence: float
    model_version: str
    model_name: str
    prediction_time: str
    match_info: Optional[Dict[str, Any]] = None
    features: Optional[Dict[str, Any]] = None
    odds: Optional[Dict[str, Any]] = None


class BatchPredictionResponse(BaseModel):
    """批量预测响应模型"""
    total: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]


class ModelStatsResponse(BaseModel):
    """模型统计响应模型"""
    model_name: str
    period_days: int
    total_predictions: int
    verified_predictions: int
    accuracy: Optional[float]
    avg_confidence: float
    predictions_by_result: Dict[str, int]
    last_updated: str


# API端点实现
@router.post("/predict", response_model=PredictionResponse)
async def predict_match(
    request: PredictionRequest,
    engine: PredictionEngine = Depends(get_prediction_engine),
    current_user: Dict = Depends(get_current_user),
):
    """
    预测单场比赛结果

    Args:
        request: 预测请求
        engine: 预测引擎
        current_user: 当前用户

    Returns:
        PredictionResponse: 预测结果
    """
    try:
        logger.info(f"用户 {current_user.get('id')} 请求预测比赛 {request.match_id}")

        # 执行预测
        result = await engine.predict_match(
            match_id=request.match_id,
            force_refresh=request.force_refresh,
            include_features=request.include_features,
        )

        return PredictionResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"预测比赛 {request.match_id} 失败: {e}")
        raise HTTPException(status_code=500, detail="预测服务暂时不可用")


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
        logger.info(f"用户 {current_user.get('id')} 请求批量预测 {len(request.match_ids)} 场比赛")

        # 检查请求数量限制
        if len(request.match_ids) > 100:
            raise HTTPException(
                status_code=400,
                detail="批量预测最多支持100场比赛"
            )

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


@router.post("/predict/upcoming")
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
        List[Dict]: 预测结果列表
    """
    try:
        logger.info(f"用户 {current_user.get('id')} 请求预测未来 {request.hours_ahead} 小时内的比赛")

        results = await engine.predict_upcoming_matches(
            hours_ahead=request.hours_ahead,
            league_ids=request.league_ids,
            force_refresh=request.force_refresh,
        )

        return {
            "total": len(results),
            "hours_ahead": request.hours_ahead,
            "league_ids": request.league_ids,
            "results": results,
        }

    except Exception as e:
        logger.error(f"预测即将开始比赛失败: {e}")
        raise HTTPException(status_code=500, detail="预测服务暂时不可用")


@router.get("/match/{match_id}", response_model=PredictionResponse)
async def get_match_prediction(
    match_id: int = Path(..., description="比赛ID", gt=0),
    include_features: bool = Query(False, description="是否包含特征信息"),
    engine: PredictionEngine = Depends(get_prediction_engine),
    current_user: Dict = Depends(get_current_user),
):
    """
    获取比赛预测结果

    Args:
        match_id: 比赛ID
        include_features: 是否包含特征信息
        engine: 预测引擎
        current_user: 当前用户

    Returns:
        PredictionResponse: 预测结果
    """
    try:
        # 获取缓存中的预测结果
        result = await engine.predict_match(
            match_id=match_id,
            force_refresh=False,
            include_features=include_features,
        )

        return PredictionResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取比赛 {match_id} 预测失败: {e}")
        raise HTTPException(status_code=500, detail="获取预测失败")


@router.get("/history/match/{match_id}")
async def get_match_prediction_history(
    match_id: int = Path(..., description="比赛ID", gt=0),
    limit: int = Query(10, description="返回记录数限制", ge=1, le=100),
    current_user: Dict = Depends(get_current_user),
):
    """
    获取比赛预测历史

    Args:
        match_id: 比赛ID
        limit: 返回记录数限制
        current_user: 当前用户

    Returns:
        Dict: 预测历史记录
    """
    try:
        from src.database.models import Predictions
        from sqlalchemy import select

        async with get_async_session() as session:
            query = select(Predictions).where(
                Predictions.match_id == match_id
            ).order_by(Predictions.created_at.desc()).limit(limit)

            result = await session.execute(query)
            predictions = result.scalars().all()

            history = []
            for pred in predictions:
                history.append({
                    "id": pred.id,
                    "model_version": pred.model_version,
                    "model_name": pred.model_name,
                    "predicted_result": pred.predicted_result,
                    "probabilities": {
                        "home_win": pred.home_win_probability,
                        "draw": pred.draw_probability,
                        "away_win": pred.away_win_probability,
                    },
                    "confidence": pred.confidence_score,
                    "created_at": pred.created_at.isoformat(),
                    "actual_result": pred.actual_result,
                    "is_correct": pred.is_correct,
                    "verified_at": pred.verified_at.isoformat() if pred.verified_at else None,
                })

            return {
                "match_id": match_id,
                "total_records": len(history),
                "history": history,
            }

    except Exception as e:
        logger.error(f"获取比赛 {match_id} 预测历史失败: {e}")
        raise HTTPException(status_code=500, detail="获取预测历史失败")


@router.get("/stats/model/{model_name}", response_model=ModelStatsResponse)
async def get_model_statistics(
    model_name: str = Path(..., description="模型名称"),
    days: int = Query(7, description="统计天数", ge=1, le=365),
    engine: PredictionEngine = Depends(get_prediction_engine),
    current_user: Dict = Depends(get_current_user),
):
    """
    获取模型性能统计

    Args:
        model_name: 模型名称
        days: 统计天数
        engine: 预测引擎
        current_user: 当前用户

    Returns:
        ModelStatsResponse: 模型统计信息
    """
    try:
        # 获取准确率
        accuracy_info = await engine.get_prediction_accuracy(model_name, days)

        # 获取详细统计
        detailed_stats = await engine.prediction_service.get_prediction_statistics(days)

        # 查找指定模型的统计
        model_stats = None
        for stat in detailed_stats.get("statistics", []):
            if stat["model_version"] == model_name:
                model_stats = stat
                break

        if not model_stats:
            raise HTTPException(status_code=404, detail=f"模型 {model_name} 没有统计数据")

        return ModelStatsResponse(
            model_name=model_name,
            period_days=days,
            total_predictions=model_stats["total_predictions"],
            verified_predictions=model_stats["verified_predictions"],
            accuracy=model_stats["accuracy"],
            avg_confidence=model_stats["avg_confidence"],
            predictions_by_result=model_stats["predictions_by_result"],
            last_updated=datetime.now().isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型 {model_name} 统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取模型统计失败")


@router.get("/stats/overview")
async def get_prediction_overview(
    days: int = Query(30, description="统计天数", ge=1, le=365),
    engine: PredictionEngine = Depends(get_prediction_engine),
    current_user: Dict = Depends(get_current_user),
):
    """
    获取预测概览统计

    Args:
        days: 统计天数
        engine: 预测引擎
        current_user: 当前用户

    Returns:
        Dict: 概览统计信息
    """
    try:
        # 获取引擎性能统计
        engine_stats = engine.get_performance_stats()

        # 获取所有模型统计
        detailed_stats = await engine.prediction_service.get_prediction_statistics(days)

        # 计算总体统计
        total_predictions = sum(s["total_predictions"] for s in detailed_stats["statistics"])
        total_verified = sum(s["verified_predictions"] for s in detailed_stats["statistics"])
        total_correct = sum(s["correct_predictions"] for s in detailed_stats["statistics"])

        overall_accuracy = total_correct / total_verified if total_verified > 0 else None

        return {
            "period_days": days,
            "engine_performance": engine_stats,
            "overall_stats": {
                "total_predictions": total_predictions,
                "verified_predictions": total_verified,
                "correct_predictions": total_correct,
                "overall_accuracy": overall_accuracy,
            },
            "models": detailed_stats["statistics"],
            "last_updated": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"获取预测概览失败: {e}")
        raise HTTPException(status_code=500, detail="获取预测概览失败")


@router.post("/verify/{match_id}")
async def verify_match_prediction(
    match_id: int = Path(..., description="比赛ID", gt=0),
    engine: PredictionEngine = Depends(get_prediction_engine),
    current_user: Dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    验证比赛预测结果

    Args:
        match_id: 比赛ID
        background_tasks: 后台任务
        engine: 预测引擎
        current_user: 当前用户

    Returns:
        Dict: 验证结果
    """
    try:
        logger.info(f"用户 {current_user.get('id')} 请求验证比赛 {match_id} 预测")

        # 执行验证
        stats = await engine.verify_predictions([match_id])

        # 记录验证日志（后台任务）
        background_tasks.add_task(
            _log_verification,
            user_id=current_user.get("id"),
            match_id=match_id,
            stats=stats,
        )

        return {
            "match_id": match_id,
            "verified": stats["verified"] > 0,
            "correct": stats["correct"],
            "accuracy": stats["accuracy"],
            "message": "验证完成" if stats["verified"] > 0 else "无可验证的预测",
        }

    except Exception as e:
        logger.error(f"验证比赛 {match_id} 预测失败: {e}")
        raise HTTPException(status_code=500, detail="验证预测失败")


@router.get("/stream/matches/{match_id}")
async def stream_match_predictions(
    match_id: int = Path(..., description="比赛ID", gt=0),
    engine: PredictionEngine = Depends(get_prediction_engine),
    current_user: Dict = Depends(get_current_user),
):
    """
    实时流式获取比赛预测更新

    Args:
        match_id: 比赛ID
        engine: 预测引擎
        current_user: 当前用户

    Returns:
        StreamingResponse: 实时预测更新流
    """
    async def generate():
        """生成实时数据流"""
        try:
            # 初始预测
            prediction = await engine.predict_match(match_id)
            yield f"data: {prediction}\n\n"

            # 监听更新
            last_time = datetime.now()
            while True:
                # 检查是否有更新
                current_prediction = await engine.predict_match(match_id)
                current_time = datetime.now()

                # 如果预测时间更新了，发送新数据
                if current_time - last_time > timedelta(minutes=5):
                    yield f"data: {current_prediction}\n\n"
                    last_time = current_time

                # 等待5秒
                await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"流式预测失败: {e}")
            yield f"event: error\ndata: {str(e)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.delete("/cache")
async def clear_prediction_cache(
    pattern: str = Query("predictions:*", description="缓存键模式"),
    engine: PredictionEngine = Depends(get_prediction_engine),
    current_user: Dict = Depends(get_current_user),
):
    """
    清理预测缓存

    Args:
        pattern: 缓存键模式
        engine: 预测引擎
        current_user: 当前用户

    Returns:
        Dict: 清理结果
    """
    try:
        # 检查权限（只有管理员可以清理缓存）
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="权限不足")

        cleared = await engine.clear_cache(pattern)

        logger.info(f"用户 {current_user.get('id')} 清理了 {cleared} 个缓存项")

        return {
            "pattern": pattern,
            "cleared_items": cleared,
            "message": f"成功清理 {cleared} 个缓存项",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清理缓存失败: {e}")
        raise HTTPException(status_code=500, detail="清理缓存失败")


@router.get("/health")
async def prediction_health_check(
    engine: PredictionEngine = Depends(get_prediction_engine),
):
    """
    预测服务健康检查

    Args:
        engine: 预测引擎

    Returns:
        Dict: 健康状态
    """
    try:
        health_status = await engine.health_check()
        return health_status

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# 辅助函数
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


async def _log_verification(
    user_id: int,
    match_id: int,
    stats: Dict[str, Any],
):
    """记录验证日志"""
    logger.info(
        f"用户 {user_id} 验证比赛 {match_id}: "
        f"验证={stats['verified']}, "
        f"正确={stats['correct']}, "
        f"准确率={stats['accuracy']:.2%}"
    )