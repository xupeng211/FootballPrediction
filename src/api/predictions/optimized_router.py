"""
优化版预测路由
Optimized Prediction Router

提供高性能的预测API端点，包括缓存策略和性能监控。
Provides high-performance prediction API endpoints with caching strategies and performance monitoring.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from ...cache.unified_cache import get_cache_manager, cached, performance_monitor
from ...performance.monitoring import get_system_monitor
from ...performance.optimizer import get_performance_optimizer
from ...core.dependencies import get_current_user_optional, get_db_session
from ...database.base import get_db
from ...domain.models import Prediction, Match
from ...services.prediction_service import PredictionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions/v2", tags=["optimized-predictions"])

# 全局服务实例
_prediction_service: Optional[PredictionService] = None
_cache_manager = get_cache_manager()
_system_monitor = get_system_monitor()

def get_prediction_service() -> PredictionService:
    """获取预测服务实例"""
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = PredictionService()
    return _prediction_service


@router.get("/health")
async def health_check():
    """健康检查端点"""
    try:
        # 检查缓存系统
        cache_stats = await _cache_manager.get_cache_stats()

        # 检查系统资源
        current_metrics = _system_monitor.get_current_metrics()

        # 检查服务状态
        service_status = "healthy"
        if current_metrics.cpu_percent > 90:
            service_status = "degraded"
        if current_metrics.memory_percent > 95:
            service_status = "critical"

        return JSONResponse(content={
            "status": service_status,
            "timestamp": datetime.utcnow().isoformat(),
            "cache_stats": {
                "hit_rate": cache_stats.get("hit_rate", 0),
                "local_cache_size": cache_stats.get("local_cache_size", 0)
            },
            "system_metrics": {
                "cpu_percent": current_metrics.cpu_percent,
                "memory_percent": current_metrics.memory_percent,
                "response_time_avg": current_metrics.response_time_avg
            }
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/matches/{match_id}/prediction")
@cached(cache_type="prediction_result", ttl=1800)
@performance_monitor(threshold=1.0)
async def get_optimized_prediction(
    match_id: int,
    background_tasks: BackgroundTasks,
    include_details: bool = Query(False, description="是否包含详细分析"),
    current_user = Depends(get_current_user_optional)
):
    """
    获取优化的比赛预测结果
    Get optimized match prediction results
    """
    try:
        # 记录性能指标
        start_time = datetime.utcnow()

        # 获取预测服务
        prediction_service = get_prediction_service()

        # 尝试从缓存获取
        cache_key = f"prediction_{match_id}_{include_details}"
        cached_prediction = await _cache_manager.get(cache_key, "prediction_result")

        if cached_prediction:
            logger.info(f"Cache hit for prediction {match_id}")
            return JSONResponse(content={
                "status": "success",
                "data": cached_prediction,
                "cached": True,
                "execution_time_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
            })

        # 缓存未命中，生成预测
        logger.info(f"Generating prediction for match {match_id}")

        # 模拟预测生成（实际应该调用机器学习模型）
        prediction_data = await _generate_prediction_data(match_id, include_details)

        # 异步缓存结果
        background_tasks.add_task(
            _cache_manager.set,
            cache_key,
            prediction_data,
            "prediction_result",
            1800  # 30分钟缓存
        )

        # 记录系统指标
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        _system_monitor.record_metrics(
            _system_monitor.get_current_metrics()
        )

        return JSONResponse(content={
            "status": "success",
            "data": prediction_data,
            "cached": False,
            "execution_time_ms": execution_time * 1000
        })

    except Exception as e:
        logger.error(f"Error generating prediction for match {match_id}: {e}")
        raise HTTPException(status_code=500, detail=f"预测生成失败: {str(e)}")


@router.get("/popular")
@cached(cache_type="popular_predictions", ttl=600)
@performance_monitor(threshold=0.5)
async def get_popular_predictions(
    limit: int = Query(10, ge=1, le=50, description="返回数量限制"),
    time_range: str = Query("24h", description="时间范围 (1h, 24h, 7d)"),
    current_user = Depends(get_current_user_optional)
):
    """
    获取热门预测
    Get popular predictions
    """
    try:
        # 解析时间范围
        time_mapping = {
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7)
        }
        time_delta = time_mapping.get(time_range, timedelta(hours=24))

        # 生成缓存键
        cache_key = f"popular_{limit}_{time_range}"

        # 模拟热门预测数据
        popular_data = await _get_popular_predictions_data(limit, time_delta)

        return JSONResponse(content={
            "status": "success",
            "data": popular_data,
            "time_range": time_range,
            "limit": limit
        })

    except Exception as e:
        logger.error(f"Error getting popular predictions: {e}")
        raise HTTPException(status_code=500, detail=f"获取热门预测失败: {str(e)}")


@router.get("/user/{user_id}/history")
@cached(cache_type="user_predictions", ttl=300)
@performance_monitor(threshold=0.8)
async def get_user_prediction_history(
    user_id: int,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    status_filter: Optional[str] = Query(None, description="状态过滤"),
    current_user = Depends(get_current_user_optional)
):
    """
    获取用户预测历史
    Get user prediction history
    """
    try:
        # 权限检查
        if current_user and current_user.id != user_id:
            raise HTTPException(status_code=403, detail="无权访问其他用户的预测历史")

        # 生成缓存键
        cache_key = f"user_history_{user_id}_{page}_{size}_{status_filter}"

        # 模拟用户历史数据
        history_data = await _get_user_prediction_history_data(
            user_id, page, size, status_filter
        )

        return JSONResponse(content={
            "status": "success",
            "data": history_data,
            "pagination": {
                "page": page,
                "size": size,
                "has_more": len(history_data) == size
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user prediction history: {e}")
        raise HTTPException(status_code=500, detail=f"获取预测历史失败: {str(e)}")


@router.get("/statistics")
@cached(cache_type="analytics", ttl=1800)
@performance_monitor(threshold=1.0)
async def get_prediction_statistics(
    time_range: str = Query("7d", description="统计时间范围"),
    current_user = Depends(get_current_user_optional)
):
    """
    获取预测统计信息
    Get prediction statistics
    """
    try:
        # 解析时间范围
        time_mapping = {
            "1d": timedelta(days=1),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30)
        }
        time_delta = time_mapping.get(time_range, timedelta(days=7))

        # 生成统计数据
        stats_data = await _get_prediction_statistics_data(time_delta)

        return JSONResponse(content={
            "status": "success",
            "data": stats_data,
            "time_range": time_range,
            "generated_at": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting prediction statistics: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.post("/cache/warmup")
async def warmup_cache(
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user_optional)
):
    """
    缓存预热
    Cache warmup
    """
    try:
        # 权限检查 - 只有管理员可以执行缓存预热
        if not current_user or not current_user.is_admin:
            raise HTTPException(status_code=403, detail="需要管理员权限")

        # 异步执行缓存预热
        background_tasks.add_task(_execute_cache_warmup)

        return JSONResponse(content={
            "status": "success",
            "message": "缓存预热任务已启动",
            "timestamp": datetime.utcnow().isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting cache warmup: {e}")
        raise HTTPException(status_code=500, detail=f"缓存预热启动失败: {str(e)}")


@router.delete("/cache/clear")
async def clear_cache(
    pattern: Optional[str] = Query(None, description="清除模式"),
    current_user = Depends(get_current_user_optional)
):
    """
    清除缓存
    Clear cache
    """
    try:
        # 权限检查
        if not current_user or not current_user.is_admin:
            raise HTTPException(status_code=403, detail="需要管理员权限")

        # 清除缓存
        if pattern:
            await _cache_manager.invalidate_pattern(pattern)
        else:
            await _cache_manager.invalidate_pattern("")

        return JSONResponse(content={
            "status": "success",
            "message": f"缓存已清除: {pattern or '全部'}",
            "timestamp": datetime.utcnow().isoformat()
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"缓存清除失败: {str(e)}")


# 辅助函数
async def _generate_prediction_data(match_id: int, include_details: bool) -> Dict[str, Any]:
    """生成预测数据"""
    # 模拟预测算法
    import random

    base_prediction = {
        "match_id": match_id,
        "prediction_id": f"pred_{match_id}_{int(datetime.utcnow().timestamp())}",
        "predicted_outcome": random.choice(["home_win", "draw", "away_win"]),
        "confidence_score": round(random.uniform(0.6, 0.95), 3),
        "probabilities": {
            "home_win": round(random.uniform(0.2, 0.6), 3),
            "draw": round(random.uniform(0.2, 0.4), 3),
            "away_win": round(random.uniform(0.2, 0.6), 3)
        },
        "created_at": datetime.utcnow().isoformat(),
        "model_version": "v2.1.0"
    }

    if include_details:
        base_prediction.update({
            "analysis": {
                "team_form": random.uniform(0.3, 0.9),
                "head_to_head": random.uniform(0.2, 0.8),
                "injuries": random.uniform(0.0, 0.3),
                "weather_impact": random.uniform(0.0, 0.2)
            },
            "key_factors": [
                "主队近期状态良好",
                "客场作战能力",
                "历史交锋记录"
            ]
        })

    return base_prediction


async def _get_popular_predictions_data(limit: int, time_delta: timedelta) -> List[Dict[str, Any]]:
    """获取热门预测数据"""
    # 模拟热门预测
    import random

    popular_data = []
    for i in range(limit):
        popular_data.append({
            "prediction_id": f"popular_{i}",
            "match_id": random.randint(1000, 9999),
            "predicted_outcome": random.choice(["home_win", "draw", "away_win"]),
            "confidence_score": round(random.uniform(0.7, 0.95), 3),
            "popularity_score": round(random.uniform(0.5, 1.0), 3),
            "created_at": (datetime.utcnow() - random.uniform(0, time_delta.total_seconds())).isoformat()
        })

    return popular_data


async def _get_user_prediction_history_data(
    user_id: int, page: int, size: int, status_filter: Optional[str]
) -> List[Dict[str, Any]]:
    """获取用户预测历史数据"""
    # 模拟历史数据
    import random

    history_data = []
    offset = (page - 1) * size

    for i in range(size):
        prediction_id = f"user_{user_id}_pred_{offset + i}"
        history_data.append({
            "prediction_id": prediction_id,
            "match_id": random.randint(1000, 9999),
            "predicted_outcome": random.choice(["home_win", "draw", "away_win"]),
            "actual_outcome": random.choice(["home_win", "draw", "away_win", "pending"]),
            "confidence_score": round(random.uniform(0.6, 0.95), 3),
            "status": random.choice(["correct", "incorrect", "pending"]) if not status_filter else status_filter,
            "created_at": (datetime.utcnow() - timedelta(days=random.randint(1, 30))).isoformat()
        })

    return history_data


async def _get_prediction_statistics_data(time_delta: timedelta) -> Dict[str, Any]:
    """获取预测统计数据"""
    # 模拟统计数据
    import random

    return {
        "total_predictions": random.randint(1000, 5000),
        "accuracy_rate": round(random.uniform(0.6, 0.8), 3),
        "average_confidence": round(random.uniform(0.7, 0.85), 3),
        "popular_outcomes": {
            "home_win": random.randint(300, 800),
            "draw": random.randint(200, 500),
            "away_win": random.randint(200, 600)
        },
        "performance_metrics": {
            "avg_response_time_ms": round(random.uniform(100, 500), 2),
            "cache_hit_rate": round(random.uniform(0.7, 0.95), 3),
            "daily_predictions": random.randint(50, 200)
        },
        "time_period": {
            "start": (datetime.utcnow() - time_delta).isoformat(),
            "end": datetime.utcnow().isoformat()
        }
    }


async def _execute_cache_warmup():
    """执行缓存预热"""
    try:
        logger.info("Starting cache warmup...")

        # 预热热门预测缓存
        popular_data = await _get_popular_predictions_data(20, timedelta(hours=24))
        await _cache_manager.set("popular_20_24h", popular_data, "popular_predictions", 600)

        # 预热统计数据缓存
        stats_data = await _get_prediction_statistics_data(timedelta(days=7))
        await _cache_manager.set("stats_7d", stats_data, "analytics", 1800)

        logger.info("Cache warmup completed successfully")

    except Exception as e:
        logger.error(f"Cache warmup failed: {e}")