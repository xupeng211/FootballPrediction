"""缓存性能监控API端点
Cache Performance Monitoring API Endpoints.

提供完整的缓存性能监控、分析和优化功能的REST API接口。
"""

import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.cache.cache_consistency_manager import get_cache_consistency_manager
from src.cache.distributed_cache_manager import get_distributed_cache_manager
from src.cache.intelligent_cache_warmup import get_intelligent_warmup_manager
from src.cache.redis_cluster_manager import get_redis_cluster_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cache", tags=["缓存性能监控"])


# ==================== 请求/响应模型 ====================


class CacheAnalysisRequest(BaseModel):
    """缓存分析请求模型."""

    analysis_type: str = Field(
        ..., description="分析类型: performance, patterns, consistency, warmup"
    )
    time_range_hours: int = Field(24, ge=1, le=168, description="分析时间范围（小时）")
    key_pattern: str | None = Field(None, description="键模式过滤")
    include_details: bool = Field(True, description="是否包含详细信息")


class CacheOptimizationRequest(BaseModel):
    """缓存优化请求模型."""

    optimization_type: str = Field(
        ..., description="优化类型: cleanup, warmup, rebalance, consistency"
    )
    target_keys: list[str] | None = Field(None, description="目标键列表")
    parameters: dict[str, Any] | None = Field(None, description="优化参数")


class WarmupRequest(BaseModel):
    """预热请求模型."""

    strategy: str = Field(
        "hybrid",
        description="预热策略: access_pattern, business_rules, predictive, hybrid, scheduled",
    )
    keys: list[str] | None = Field(None, description="预热键列表")
    priority_levels: list[str] | None = Field(None, description="优先级过滤")
    scheduled_at: datetime | None = Field(None, description="计划执行时间")


class ConsistencyRequest(BaseModel):
    """一致性请求模型."""

    operation: str = Field(
        ..., description="操作类型: read, write, invalidate, resolve_conflict"
    )
    key: str = Field(..., description="键名")
    value: Any | None = Field(None, description="值（写操作时使用）")
    session_id: str | None = Field(None, description="会话ID")
    version: int | None = Field(None, description="版本号")


class CacheInvalidateRequest(BaseModel):
    """缓存失效请求模型."""

    keys: list[str] = Field(..., description="要失效的键列表")
    pattern: str | None = Field(None, description="失效模式（可选）")


class CacheWarmupRequest(BaseModel):
    """缓存预热请求模型."""

    keys: list[str] = Field(..., description="要预热的键列表")
    ttl: int = Field(3600, ge=1, le=86400, description="TTL秒数")


class ConsistencyOperationRequest(BaseModel):
    """一致性操作请求模型."""

    operation_type: str = Field(..., description="操作类型")
    target_keys: list[str] = Field(..., description="目标键列表")
    parameters: dict[str, Any] = Field(default_factory=dict, description="操作参数")


# ==================== 缓存状态监控端点 ====================


@router.get("/status")
async def get_cache_status():
    """获取缓存系统整体状态."""
    redis_manager = get_redis_cluster_manager()
    distributed_cache = get_distributed_cache_manager()
    consistency_manager = get_cache_consistency_manager()
    warmup_manager = get_intelligent_warmup_manager()

    # 计算整体状态
    all_disabled = all(
        manager is None
        for manager in [
            redis_manager,
            distributed_cache,
            consistency_manager,
            warmup_manager,
        ]
    )
    any_active = any(
        manager is not None
        for manager in [
            redis_manager,
            distributed_cache,
            consistency_manager,
            warmup_manager,
        ]
    )

    if all_disabled:
        overall_status = "unhealthy"
    elif any_active:
        overall_status = "healthy"
    else:
        overall_status = "degraded"

    status = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "redis_cluster": {
                "enabled": redis_manager is not None,
                "status": "active" if redis_manager else "disabled",
            },
            "distributed_cache": {
                "enabled": distributed_cache is not None,
                "status": "active" if distributed_cache else "disabled",
            },
            "consistency_manager": {
                "enabled": consistency_manager is not None,
                "status": "active" if consistency_manager else "disabled",
            },
            "warmup_manager": {
                "enabled": warmup_manager is not None,
                "status": "active" if warmup_manager else "disabled",
            },
        },
    }

    # 获取各组件详细状态
    if redis_manager:
        status["components"]["redis_cluster"]["details"] = await redis_manager.get_cluster_status()

    if distributed_cache:
        status["components"]["distributed_cache"][
            "details"
        ] = await distributed_cache.get_cache_status()

    if consistency_manager:
        status["components"]["consistency_manager"][
            "details"
        ] = await consistency_manager.get_statistics()

    if warmup_manager:
        status["components"]["warmup_manager"][
            "details"
        ] = await warmup_manager.get_warmup_statistics()

    return status


@router.get("/performance/metrics")
async def get_performance_metrics(
    time_range_hours: int = Query(24, ge=1, le=168),
    component: str | None = Query(
        None, description="组件过滤: redis, distributed, consistency, warmup"
    ),
):
    """获取性能指标."""
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "time_range_hours": time_range_hours,
        "metrics": {},
    }

    # Redis集群指标
    if not component or component == "redis":
        redis_manager = get_redis_cluster_manager()
        if redis_manager:
            cluster_status = await redis_manager.get_cluster_status()
            metrics["metrics"]["redis_cluster"] = {
                "hit_rate": cluster_status["metrics"]["cache_hit_rate"],
                "avg_response_time": cluster_status["metrics"]["avg_response_time"],
                "total_operations": cluster_status["metrics"]["total_operations"],
                "failed_operations": cluster_status["metrics"]["failed_operations"],
                "operation_stats": cluster_status["metrics"]["operation_stats"],
                "cluster_health": {
                    "total_nodes": cluster_status["cluster_info"]["total_nodes"],
                    "healthy_nodes": cluster_status["cluster_info"]["healthy_nodes"],
                    "failed_nodes": cluster_status["cluster_info"]["failed_nodes"],
                },
            }

    # 分布式缓存指标
    if not component or component == "distributed":
        distributed_cache = get_distributed_cache_manager()
        if distributed_cache:
            cache_status = await distributed_cache.get_cache_status()
            metrics["metrics"]["distributed_cache"] = cache_status["performance"]

    # 一致性管理器指标
    if not component or component == "consistency":
        consistency_manager = get_cache_consistency_manager()
        if consistency_manager:
            consistency_stats = await consistency_manager.get_statistics()
            metrics["metrics"]["consistency_manager"] = {
                "consistency_level": consistency_stats["consistency_level"],
                "conflict_strategy": consistency_stats["conflict_strategy"],
                "statistics": consistency_stats["statistics"],
                "error_rate": consistency_stats["error_rate"],
                "conflict_rate": consistency_stats["conflict_rate"],
                "active_sessions": consistency_stats["active_sessions"],
            }

    # 预热管理器指标
    if not component or component == "warmup":
        warmup_manager = get_intelligent_warmup_manager()
        if warmup_manager:
            warmup_stats = await warmup_manager.get_warmup_statistics()
            metrics["metrics"]["warmup_manager"] = warmup_stats

    return metrics


# ==================== Redis集群管理端点 ====================


@router.get("/cluster/status")
async def get_redis_cluster_status():
    """获取Redis集群状态."""
    redis_manager = get_redis_cluster_manager()
    if not redis_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis集群管理器未启用",
        )

    try:
        cluster_status = await redis_manager.get_cluster_status()
        return cluster_status

    except Exception as e:
        logger.error(f"Error getting Redis cluster status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取Redis集群状态失败: {str(e)}",
        ) from None


@router.post("/cluster/nodes")
async def add_redis_node(node_config: dict[str, Any]):
    """添加Redis节点."""
    redis_manager = get_redis_cluster_manager()
    if not redis_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis集群管理器未启用",
        )

    try:
        success = await redis_manager.add_node(node_config)
        if success:
            return {"message": f"Redis节点 {node_config.get('node_id')} 添加成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="添加Redis节点失败"
            )

    except Exception as e:
        logger.error(f"Error adding Redis node: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加Redis节点失败: {str(e)}",
        ) from e


@router.delete("/cluster/nodes/{node_id}")
async def remove_redis_node(node_id: str):
    """移除Redis节点."""
    redis_manager = get_redis_cluster_manager()
    if not redis_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis集群管理器未启用",
        )

    try:
        success = await redis_manager.remove_node(node_id)
        if success:
            return {"message": f"Redis节点 {node_id} 移除成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Redis节点 {node_id} 不存在",
            )

    except Exception as e:
        logger.error(f"Error removing Redis node: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"移除Redis节点失败: {str(e)}",
        ) from e


# ==================== 分布式缓存管理端点 ====================


@router.get("/distributed/status")
async def get_distributed_cache_status():
    """获取分布式缓存状态."""
    distributed_cache = get_distributed_cache_manager()
    if not distributed_cache:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="分布式缓存管理器未启用",
        )

    try:
        cache_status = await distributed_cache.get_cache_status()
        return cache_status

    except Exception as e:
        logger.error(f"Error getting distributed cache status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取分布式缓存状态失败: {str(e)}",
        ) from e


@router.post("/distributed/invalidate")
async def invalidate_cache_keys(request: CacheInvalidateRequest):
    """失效缓存键."""
    distributed_cache = get_distributed_cache_manager()
    if not distributed_cache:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="分布式缓存管理器未启用",
        )

    try:
        if request.pattern:
            # 如果指定了模式，使用模式失效
            count = await distributed_cache.invalidate_pattern(request.pattern)
        else:
            # 否则逐个失效键
            count = 0
            for key in request.keys:
                result = await distributed_cache.invalidate_keys([key])
                count += result.get("invalidated", 0)

        return {
            "invalidated": count,
            "keys": request.keys,
            "pattern": request.pattern,
        }

    except Exception as e:
        logger.error(f"Error invalidating cache keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"缓存失效失败: {str(e)}",
        ) from e


@router.post("/distributed/warmup")
async def warmup_cache(request: CacheWarmupRequest):
    """缓存预热."""
    distributed_cache = get_distributed_cache_manager()
    if not distributed_cache:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="分布式缓存管理器未启用",
        )

    try:
        # 调用mock的warmup_cache方法
        result = await distributed_cache.warmup_cache(request.keys, request.ttl)
        return result

    except Exception as e:
        logger.error(f"Error warming up cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"缓存预热失败: {str(e)}",
        ) from e


# ==================== 缓存一致性管理端点 ====================


@router.post("/consistency/operations")
async def consistency_operation(request: ConsistencyOperationRequest):
    """一致性操作."""
    consistency_manager = get_cache_consistency_manager()
    if not consistency_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="缓存一致性管理器未启用",
        )

    try:
        # 生成操作ID
        operation_id = f"op_{hash(str(request.target_keys))}_{len(request.target_keys)}"

        # 模拟执行操作
        success = True
        if request.operation_type in ["verify", "read", "write", "invalidate"]:
            # 根据操作类型调用相应的方法
            if hasattr(consistency_manager, request.operation_type):
                method = getattr(consistency_manager, request.operation_type)
                if callable(method):
                    result = await method(request.target_keys, **request.parameters)
                    success = (
                        result.get("success", True)
                        if isinstance(result, dict)
                        else True
                    )

        return {
            "operation_id": operation_id,
            "operation_type": request.operation_type,
            "target_keys": request.target_keys,
            "status": "completed" if success else "failed",
            "parameters": request.parameters,
        }

    except Exception as e:
        logger.error(f"Error in consistency operation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"一致性操作失败: {str(e)}",
        ) from e


@router.get("/consistency/statistics")
async def get_consistency_statistics():
    """获取一致性统计信息."""
    consistency_manager = get_cache_consistency_manager()
    if not consistency_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="缓存一致性管理器未启用",
        )

    try:
        stats = await consistency_manager.get_statistics()
        return stats

    except Exception as e:
        logger.error(f"Error getting consistency statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取一致性统计失败: {str(e)}",
        ) from e


@router.delete("/consistency/sessions/{session_id}")
async def cleanup_consistency_session(session_id: str):
    """清理会话数据."""
    consistency_manager = get_cache_consistency_manager()
    if not consistency_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="缓存一致性管理器未启用",
        )

    try:
        await consistency_manager.cleanup_session(session_id)
        return {"message": f"会话 {session_id} 数据已清理"}

    except Exception as e:
        logger.error(f"Error cleaning up session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理会话失败: {str(e)}",
        ) from e


# ==================== 智能预热管理端点 ====================


@router.post("/warmup/plans")
async def create_warmup_plan(request: WarmupRequest, background_tasks: BackgroundTasks):
    """创建预热计划."""
    warmup_manager = get_intelligent_warmup_manager()
    if not warmup_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="智能预热管理器未启用",
        )

    try:
        # 转换策略枚举
        from src.cache.intelligent_cache_warmup import WarmupStrategy

        strategy_map = {
            "access_pattern": WarmupStrategy.ACCESS_PATTERN,
            "business_rules": WarmupStrategy.BUSINESS_RULES,
            "predictive": WarmupStrategy.PREDICTIVE,
            "hybrid": WarmupStrategy.HYBRID,
            "scheduled": WarmupStrategy.SCHEDULED,
        }

        strategy = strategy_map.get(request.strategy, WarmupStrategy.HYBRID)

        # 创建预热计划
        plan_id = await warmup_manager.create_warmup_plan(
            strategy=strategy,
            keys=request.keys,
            priority_filter=request.priority_levels,
            scheduled_at=request.scheduled_at,
        )

        # 如果是立即执行，启动后台任务
        if not request.scheduled_at or request.scheduled_at <= datetime.utcnow():
            background_tasks.add_task(warmup_manager.execute_warmup_plan, plan_id)

        return {
            "plan_id": plan_id,
            "strategy": request.strategy,
            "keys_count": len(request.keys) if request.keys else 0,
            "scheduled_at": (
                request.scheduled_at.isoformat() if request.scheduled_at else None
            ),
            "message": "预热计划创建成功",
        }

    except Exception as e:
        logger.error(f"Error creating warmup plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建预热计划失败: {str(e)}",
        ) from e


@router.get("/warmup/plans/{plan_id}/status")
async def get_warmup_plan_status(plan_id: str):
    """获取预热计划状态."""
    warmup_manager = get_intelligent_warmup_manager()
    if not warmup_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="智能预热管理器未启用",
        )

    try:
        if plan_id not in warmup_manager.warmup_plans:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"预热计划 {plan_id} 不存在",
            )

        plan = warmup_manager.warmup_plans[plan_id]
        return {
            "plan_id": plan_id,
            "strategy": plan.strategy.value,
            "status": plan.status,
            "total_tasks": plan.total_tasks,
            "completed_tasks": plan.completed_tasks,
            "failed_tasks": plan.failed_tasks,
            "created_at": plan.created_at.isoformat(),
            "scheduled_at": (
                plan.scheduled_at.isoformat() if plan.scheduled_at else None
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting warmup plan status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取预热计划状态失败: {str(e)}",
        ) from e


@router.post("/warmup/plans/{plan_id}/execute")
async def execute_warmup_plan(plan_id: str, background_tasks: BackgroundTasks):
    """执行预热计划."""
    warmup_manager = get_intelligent_warmup_manager()
    if not warmup_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="智能预热管理器未启用",
        )

    try:
        if plan_id not in warmup_manager.warmup_plans:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"预热计划 {plan_id} 不存在",
            )

        # 后台执行预热计划
        background_tasks.add_task(warmup_manager.execute_warmup_plan, plan_id)

        return {"message": f"预热计划 {plan_id} 开始执行"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing warmup plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行预热计划失败: {str(e)}",
        ) from e


@router.delete("/warmup/plans/{plan_id}")
async def cancel_warmup_plan(plan_id: str):
    """取消预热计划."""
    warmup_manager = get_intelligent_warmup_manager()
    if not warmup_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="智能预热管理器未启用",
        )

    try:
        success = await warmup_manager.cancel_plan(plan_id)
        if success:
            return {"message": f"预热计划 {plan_id} 已取消"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"预热计划 {plan_id} 不存在或无法取消",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling warmup plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消预热计划失败: {str(e)}",
        ) from e


@router.get("/warmup/statistics")
async def get_warmup_statistics():
    """获取预热统计信息."""
    warmup_manager = get_intelligent_warmup_manager()
    if not warmup_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="智能预热管理器未启用",
        )

    try:
        stats = await warmup_manager.get_warmup_statistics()
        return stats

    except Exception as e:
        logger.error(f"Error getting warmup statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取预热统计失败: {str(e)}",
        ) from e


@router.post("/warmup/record-access")
async def record_cache_access(
    key: str = Query(..., description="缓存键"),
    session_id: str | None = Query(None, description="会话ID"),
    duration: float | None = Query(None, description="访问持续时间"),
):
    """记录缓存访问（用于学习访问模式）."""
    warmup_manager = get_intelligent_warmup_manager()
    if not warmup_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="智能预热管理器未启用",
        )

    try:
        await warmup_manager.record_access(key, session_id, duration or 0.0)
        return {"message": "访问记录已保存"}

    except Exception as e:
        logger.error(f"Error recording access: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"记录访问失败: {str(e)}",
        ) from e


# ==================== 缓存分析和优化端点 ====================


@router.post("/analysis")
async def analyze_cache_performance(request: CacheAnalysisRequest):
    """分析缓存性能."""
    try:
        analysis_result = {
            "analysis_type": request.analysis_type,
            "time_range_hours": request.time_range_hours,
            "timestamp": datetime.utcnow().isoformat(),
            "results": {},
        }

        if request.analysis_type == "performance":
            # 性能分析
            redis_manager = get_redis_cluster_manager()
            if redis_manager:
                cluster_status = await redis_manager.get_cluster_status()
                analysis_result["results"]["performance"] = {
                    "hit_rate": cluster_status["metrics"]["cache_hit_rate"],
                    "response_time": cluster_status["metrics"]["avg_response_time"],
                    "error_rate": (
                        cluster_status["metrics"]["failed_operations"]
                        / max(cluster_status["metrics"]["total_operations"], 1)
                    )
                    * 100,
                }

        elif request.analysis_type == "patterns":
            # 访问模式分析
            warmup_manager = get_intelligent_warmup_manager()
            if warmup_manager:
                pattern_analysis = warmup_manager.pattern_analyzer.analyze_patterns(
                    timedelta(hours=request.time_range_hours)
                )
                analysis_result["results"]["patterns"] = pattern_analysis

        elif request.analysis_type == "consistency":
            # 一致性分析
            consistency_manager = get_cache_consistency_manager()
            if consistency_manager:
                consistency_stats = await consistency_manager.get_statistics()
                analysis_result["results"]["consistency"] = consistency_stats

        elif request.analysis_type == "warmup":
            # 预热效果分析
            warmup_manager = get_intelligent_warmup_manager()
            if warmup_manager:
                warmup_stats = await warmup_manager.get_warmup_statistics()
                analysis_result["results"]["warmup"] = warmup_stats

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的分析类型: {request.analysis_type}",
            )

        return analysis_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in cache analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"缓存分析失败: {str(e)}",
        ) from e


@router.post("/optimization")
async def optimize_cache_system(
    request: CacheOptimizationRequest, background_tasks: BackgroundTasks
):
    """优化缓存系统."""
    optimization_id = f"opt_{int(datetime.utcnow().timestamp())}"
    result = {
        "optimization_id": optimization_id,
        "optimization_type": request.optimization_type,
        "started_at": datetime.utcnow().isoformat(),
    }

    try:
        if request.optimization_type == "cleanup":
            # 缓存清理
            distributed_cache = get_distributed_cache_manager()
            if distributed_cache:
                if request.target_keys:
                    # 清理指定键
                    count = 0
                    for key in request.target_keys:
                        if await distributed_cache.delete(key):
                            count += 1
                    result["cleanup_result"] = {"cleared_keys": count}
                else:
                    # 全局清理
                    result["message"] = "全局缓存清理功能需要更多参数"

        elif request.optimization_type == "warmup":
            # 缓存预热
            warmup_manager = get_intelligent_warmup_manager()
            if warmup_manager and request.target_keys:
                # 创建预热计划
                plan_id = await warmup_manager.create_warmup_plan(
                    strategy=warmup_manager.strategies.get("hybrid"),
                    keys=request.target_keys,
                )
                background_tasks.add_task(warmup_manager.execute_warmup_plan, plan_id)
                result["warmup_plan_id"] = plan_id

        elif request.optimization_type == "rebalance":
            # 负载均衡
            result["message"] = "负载均衡优化功能开发中"

        elif request.optimization_type == "consistency":
            # 一致性优化
            consistency_manager = get_cache_consistency_manager()
            if consistency_manager:
                stats = await consistency_manager.get_statistics()
                result["consistency_stats"] = stats

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的优化类型: {request.optimization_type}",
            )

        result["message"] = "缓存优化任务已启动"
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in cache optimization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"缓存优化失败: {str(e)}",
        ) from e


# ==================== 健康检查端点 ====================


@router.get("/health", tags=["健康检查"])
async def cache_system_health():
    """缓存系统健康检查."""
    components = {
        "redis_cluster": "healthy",
        "distributed_cache": "healthy",
        "consistency_manager": "healthy",
        "warmup_manager": "healthy",
    }

    # 检查各组件健康状态
    redis_manager = get_redis_cluster_manager()
    if redis_manager:
        try:
            cluster_status = await redis_manager.get_cluster_status()
            if cluster_status["cluster_info"]["healthy_nodes"] == 0:
                components["redis_cluster"] = "unhealthy"
        except Exception:
            components["redis_cluster"] = "error"
    else:
        components["redis_cluster"] = "disabled"

    distributed_cache = get_distributed_cache_manager()
    if not distributed_cache:
        components["distributed_cache"] = "disabled"

    consistency_manager = get_cache_consistency_manager()
    if not consistency_manager:
        components["consistency_manager"] = "disabled"

    warmup_manager = get_intelligent_warmup_manager()
    if not warmup_manager:
        components["warmup_manager"] = "disabled"

    overall_status = "healthy"
    if any(status in ["unhealthy", "error"] for status in components.values()):
        overall_status = "unhealthy"
    elif all(status == "disabled" for status in components.values()):
        overall_status = "disabled"

    return {
        "status": overall_status,
        "service": "cache_performance_monitoring",
        "timestamp": datetime.utcnow().isoformat(),
        "components": components,
        "version": "1.0.0",
    }
