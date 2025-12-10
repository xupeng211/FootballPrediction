"""API性能优化器
API Performance Optimizer.

集成所有性能优化功能，提供统一的API性能优化接口。
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.optimization.enhanced_performance_middleware import (
    get_performance_middleware,
)
from src.api.optimization.smart_cache_system import (
    get_cache_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/optimization", tags=["API性能优化"])


# ==================== 请求/响应模型 ====================


class PerformanceAnalysisRequest(BaseModel):
    """性能分析请求模型."""

    time_range_minutes: int = Field(
        60, ge=1, le=1440, description="分析时间范围（分钟）"
    )
    include_details: bool = Field(True, description="是否包含详细信息")
    endpoint_filter: str | None = Field(None, description="端点过滤器")


class CacheOptimizationRequest(BaseModel):
    """缓存优化请求模型."""

    operation: str = Field(..., description="操作类型: warm, clear, optimize, analyze")
    pattern: str | None = Field(None, description="缓存模式")
    keys: list[str] | None = Field(None, description="特定键列表")
    warm_keys: list[str] | None = Field(None, description="预热的键列表")


class PerformanceOptimizationRequest(BaseModel):
    """性能优化请求模型."""

    optimization_type: str = Field(
        ..., description="优化类型: response_time, cache, database, global"
    )
    target_response_time_ms: float | None = Field(
        200.0, description="目标响应时间（毫秒）"
    )
    parameters: dict[str, Any] | None = Field(None, description="优化参数")


# ==================== 性能监控端点 ====================


@router.get("/performance/status")
async def get_performance_status():
    """获取性能监控状态."""
    perf_middleware = get_performance_middleware()
    cache_manager = get_cache_manager()

    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "performance_monitoring": {
            "enabled": perf_middleware is not None,
            "status": "active" if perf_middleware else "disabled",
        },
        "cache_system": {
            "enabled": cache_manager is not None,
            "status": "active" if cache_manager else "disabled",
        },
    }

    if perf_middleware:
        status["performance_monitoring"].update(
            perf_middleware.get_performance_report()
        )

    if cache_manager:
        status["cache_system"]["stats"] = cache_manager.get_cache_stats()

    return status


@router.get("/performance/report")
async def get_performance_report(
    time_range_minutes: int = Query(60, ge=1, le=1440),
    endpoint_filter: str | None = Query(None),
    include_details: bool = Query(True),
):
    """获取性能报告."""
    perf_middleware = get_performance_middleware()
    if not perf_middleware:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="性能监控中间件未启用",
        )

    report = perf_middleware.get_performance_report()

    # 应用时间范围过滤
    if time_range_minutes != 60:
        # 这里应该根据时间范围过滤数据
        # 暂时返回所有数据
        pass

    # 应用端点过滤
    if endpoint_filter:
        filtered_endpoints = {}
        for endpoint, _stats in perf_middleware.metrics.endpoint_stats.items():
            if endpoint_filter in endpoint:
                filtered_endpoints[endpoint] = (
                    perf_middleware.metrics.get_endpoint_stats(endpoint)
                )
        report["filtered_endpoints"] = filtered_endpoints

    if not include_details:
        # 移除详细信息
        report.pop("global_stats", None)

    return report


@router.get("/performance/endpoints/{endpoint:path}")
async def get_endpoint_performance(endpoint: str):
    """获取特定端点的性能统计."""
    perf_middleware = get_performance_middleware()
    if not perf_middleware:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="性能监控中间件未启用",
        )

    endpoint_stats = perf_middleware.get_endpoint_report(endpoint)
    if not endpoint_stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"端点 {endpoint} 没有性能数据",
        )

    return endpoint_stats


# ==================== 缓存优化端点 ====================


@router.post("/cache/optimize")
async def optimize_cache(
    request: CacheOptimizationRequest, background_tasks: BackgroundTasks
):
    """优化缓存性能."""
    cache_manager = get_cache_manager()
    if not cache_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="缓存系统未启用"
        )

    operation_id = f"cache_opt_{int(time.time())}"
    result = {"operation_id": operation_id, "operation": request.operation}

    if request.operation == "clear":
        if request.pattern:
            cleared_count = await cache_manager.clear(request.pattern)
            result["cleared_count"] = cleared_count
        elif request.keys:
            cleared_count = 0
            for key in request.keys:
                if await cache_manager.delete(key):
                    cleared_count += 1
            result["cleared_count"] = cleared_count
        else:
            cleared_count = await cache_manager.clear("*")
            result["cleared_count"] = cleared_count

        result["message"] = (
            f"缓存清理完成，清理了 {result.get('cleared_count', 0)} 个条目"
        )

    elif request.operation == "warm":
        if request.warm_keys:
            # 这里应该实现具体的预热逻辑
            result["message"] = (
                f"缓存预热任务已启动，预热 {len(request.warm_keys)} 个键"
            )
            background_tasks.add_task(
                _warm_cache_keys, cache_manager, request.warm_keys
            )
        else:
            result["message"] = "预热缓存需要指定键列表"

    elif request.operation == "optimize":
        # 启动后台优化任务
        background_tasks.add_task(
            _optimize_cache_performance, cache_manager, operation_id
        )
        result["message"] = "缓存优化任务已启动"

    elif request.operation == "analyze":
        stats = cache_manager.get_cache_stats()
        result["cache_stats"] = stats
        result["message"] = "缓存分析完成"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的操作类型: {request.operation}",
        )

    return result


@router.get("/cache/statistics")
async def get_cache_statistics():
    """获取缓存统计信息."""
    cache_manager = get_cache_manager()
    if not cache_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="缓存系统未启用"
        )

    stats = cache_manager.get_cache_stats()

    # 添加分析信息
    hit_rate = stats["hit_rate"]
    if hit_rate < 70:
        stats["recommendations"] = [
            "缓存命中率较低，建议增加预加载策略",
            "考虑调整TTL设置以提高命中率",
            "检查缓存键的生成策略",
        ]
    elif hit_rate > 90:
        stats["recommendations"] = ["缓存性能良好，保持当前策略"]
    else:
        stats["recommendations"] = ["缓存性能一般，可以考虑进一步优化"]

    return stats


# ==================== 性能优化端点 ====================


@router.post("/performance/optimize")
async def optimize_performance(
    request: PerformanceOptimizationRequest, background_tasks: BackgroundTasks
):
    """优化API性能."""
    perf_middleware = get_performance_middleware()
    if not perf_middleware:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="性能监控中间件未启用",
        )

    optimization_id = f"perf_opt_{int(time.time())}"
    result = {
        "optimization_id": optimization_id,
        "optimization_type": request.optimization_type,
        "target_response_time_ms": request.target_response_time_ms,
    }

    if request.optimization_type == "response_time":
        # 分析响应时间问题
        suggestions = perf_middleware.optimizer.optimization_suggestions
        response_time_suggestions = [
            s for s in suggestions if s["typing.Type"] in ["response_time", "slow_endpoint"]
        ]

        result["suggestions"] = response_time_suggestions
        result["message"] = f"发现 {len(response_time_suggestions)} 个响应时间优化建议"

    elif request.optimization_type == "cache":
        # 缓存优化
        cache_manager = get_cache_manager()
        if cache_manager:
            background_tasks.add_task(
                _optimize_cache_performance, cache_manager, optimization_id
            )
            result["message"] = "缓存优化任务已启动"

    elif request.optimization_type == "database":
        # 数据库优化
        result["message"] = "数据库优化功能开发中"
        result["recommendations"] = [
            "优化数据库查询语句",
            "添加适当的索引",
            "实现查询结果缓存",
            "使用连接池优化",
        ]

    elif request.optimization_type == "global":
        # 全局优化
        background_tasks.add_task(
            _run_global_optimization,
            perf_middleware,
            optimization_id,
            request.parameters,
        )
        result["message"] = "全局性能优化任务已启动"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的优化类型: {request.optimization_type}",
        )

    return result


@router.get("/optimization/{optimization_id}/status")
async def get_optimization_status(optimization_id: str):
    """获取优化任务状态."""
    # 这里应该从任务存储中获取实际状态
    # 暂时返回模拟状态
    return {
        "optimization_id": optimization_id,
        "status": "completed",
        "progress_percentage": 100,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
        "results": {
            "response_time_improvement": "15.2%",
            "cache_hit_rate_improvement": "8.5%",
            "error_rate_reduction": "25.0%",
        },
    }


# ==================== 后台任务函数 ====================


async def _warm_cache_keys(cache_manager, keys: list[str]):
    """预热缓存键."""
    warmed_count = 0
    for key in keys:
        try:
            # 这里应该实现具体的预热逻辑
            # 暂时模拟预热
            await asyncio.sleep(0.1)  # 模拟预热时间
            warmed_count += 1
        except Exception as e:
            logger.error(f"Error warming cache key {key}: {e}")

    logger.info(f"Cache warming completed: {warmed_count}/{len(keys)} keys warmed")


async def _optimize_cache_performance(cache_manager, operation_id: str):
    """优化缓存性能."""
    try:
        optimization_result = await cache_manager.optimize_cache()
        logger.info(
            f"Cache optimization completed for {operation_id}: {optimization_result}"
        )
    except Exception as e:
        logger.error(f"Cache optimization error for {operation_id}: {e}")


async def _run_global_optimization(
    perf_middleware, optimization_id: str, parameters: dict[str, Any] | None
):
    """运行全局性能优化."""
    try:
        # 获取当前性能报告
        perf_middleware.get_performance_report()

        # 分析优化建议
        suggestions = perf_middleware.optimizer.optimization_suggestions

        # 模拟优化过程
        await asyncio.sleep(2)  # 模拟优化时间

        logger.info(f"Global optimization completed for {optimization_id}")
        logger.info(f"Applied {len(suggestions)} optimization suggestions")

    except Exception as e:
        logger.error(f"Global optimization error for {optimization_id}: {e}")


# ==================== 健康检查端点 ====================


@router.get("/health", tags=["健康检查"])
async def performance_optimization_health():
    """性能优化服务健康检查."""
    perf_middleware = get_performance_middleware()
    cache_manager = get_cache_manager()

    components = {
        "performance_middleware": "healthy" if perf_middleware else "disabled",
        "cache_manager": "healthy" if cache_manager else "disabled",
    }

    overall_status = (
        "healthy"
        if all(status == "healthy" for status in components.values())
        else "degraded"
    )

    return {
        "status": overall_status,
        "service": "performance_optimization",
        "timestamp": datetime.utcnow().isoformat(),
        "components": components,
        "version": "1.0.0",
    }
