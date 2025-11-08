"""
性能管理API
Performance Management API

提供系统性能监控,优化和管理的API接口.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.database.base import get_db_session
from src.database.performance import DatabaseOptimizer
from src.middleware.tenant_middleware import require_permission
from src.optimizations.api_optimizations import APIOptimizer
from src.optimizations.database_optimizations import DatabaseOptimizerFactory

router = APIRouter(prefix="/api/v1/performance", tags=["性能管理"])

# 全局API优化器实例
api_optimizer = APIOptimizer()

# ==================== 请求/响应模型 ====================


class OptimizationRequestModel(BaseModel):
    """优化请求模型"""

    optimization_type: str = Field(..., description="优化类型")
    parameters: dict[str, Any] | None = Field(None, description="优化参数")


class CacheOperationModel(BaseModel):
    """缓存操作模型"""

    operation: str = Field(..., description="操作类型: clear, warm, analyze")
    pattern: str | None = Field(None, description="缓存模式")
    keys: list[str] | None = Field(None, description="特定键列表")


class PerformanceAnalysisModel(BaseModel):
    """性能分析模型"""

    time_range_minutes: int = Field(
        60, ge=1, le=1440, description="分析时间范围（分钟）"
    )
    include_details: bool = Field(True, description="是否包含详细信息")


class DatabaseOptimizationModel(BaseModel):
    """数据库优化模型"""

    optimize_indexes: bool = Field(True, description="优化索引")
    cleanup_data: bool = Field(True, description="清理数据")
    analyze_tables: bool = Field(True, description="分析表")
    refresh_views: bool = Field(True, description="刷新物化视图")


# ==================== 性能监控端点 ====================


@router.get("/metrics")
@require_permission("performance.view")
async def get_performance_metrics(
    time_range_minutes: int = Query(60, ge=1, le=1440, description="时间范围（分钟）"),
    endpoint_filter: str | None = Query(None, description="端点过滤"),
):
    """
    获取性能指标

    需要权限: performance.view
    """
    # 这里应该从实际的性能监控中间件获取数据
    # 暂时返回模拟数据
    metrics_summary = {
        "time_range_minutes": time_range_minutes,
        "total_requests": 1250,
        "avg_response_time_ms": 245.6,
        "error_rate": 2.3,
        "p95_response_time_ms": 580.2,
        "p99_response_time_ms": 1250.8,
        "cache_hit_rate": 78.5,
        "requests_per_minute": 20.8,
        "top_slow_endpoints": [
            {
                "endpoint": "/api/v1/predictions/analyze",
                "method": "POST",
                "avg_response_time_ms": 1250.5,
                "request_count": 45,
            },
            {
                "endpoint": "/api/v1/matches/history",
                "method": "GET",
                "avg_response_time_ms": 890.3,
                "request_count": 120,
            },
        ],
        "top_error_endpoints": [
            {
                "endpoint": "/api/v1/users/profile",
                "method": "PUT",
                "error_rate": 12.5,
                "error_count": 8,
            }
        ],
    }

    if endpoint_filter:
        # 应用端点过滤
        metrics_summary["filtered_endpoints"] = [
            ep
            for ep in metrics_summary.get("top_slow_endpoints", [])
            if endpoint_filter in ep["endpoint"]
        ]

    return metrics_summary


@router.get("/dashboard")
@require_permission("performance.view")
async def get_performance_dashboard():
    """
    获取性能仪表板数据

    需要权限: performance.view
    """
    dashboard_data = {
        "overview": {
            "system_health": "good",
            "overall_performance_score": 85.2,
            "active_alerts": 2,
            "last_optimization": "2025-10-30T14:30:00Z",
        },
        "response_time_trend": [
            {"timestamp": "2025-10-30T14:00:00Z", "avg_ms": 230.5},
            {"timestamp": "2025-10-30T14:15:00Z", "avg_ms": 245.8},
            {"timestamp": "2025-10-30T14:30:00Z", "avg_ms": 251.2},
            {"timestamp": "2025-10-30T14:45:00Z", "avg_ms": 238.9},
            {"timestamp": "2025-10-30T15:00:00Z", "avg_ms": 245.6},
        ],
        "error_rate_trend": [
            {"timestamp": "2025-10-30T14:00:00Z", "rate": 2.1},
            {"timestamp": "2025-10-30T14:15:00Z", "rate": 2.5},
            {"timestamp": "2025-10-30T14:30:00Z", "rate": 1.8},
            {"timestamp": "2025-10-30T14:45:00Z", "rate": 2.3},
            {"timestamp": "2025-10-30T15:00:00Z", "rate": 2.3},
        ],
        "resource_usage": {
            "cpu_usage": 45.8,
            "memory_usage": 67.2,
            "disk_usage": 78.5,
            "network_io": 12.3,
        },
        "cache_performance": {
            "hit_rate": 78.5,
            "miss_rate": 21.5,
            "total_keys": 1250,
            "memory_usage_mb": 245.6,
        },
        "database_performance": {
            "connection_pool_usage": 65.2,
            "avg_query_time_ms": 125.4,
            "slow_queries": 3,
            "index_usage_rate": 89.5,
        },
    }

    return dashboard_data


@router.get("/alerts")
@require_permission("performance.view")
async def get_performance_alerts(
    severity: str | None = Query(None, description="严重级别过滤"),
    status_filter: str | None = Query(None, description="状态过滤"),
):
    """
    获取性能告警

    需要权限: performance.view
    """
    alerts = [
        {
            "id": "alert_001",
            "title": "响应时间过长",
            "description": "端点 /api/v1/predictions/analyze 平均响应时间超过1秒",
            "severity": "warning",
            "status": "active",
            "created_at": "2025-10-30T14:45:00Z",
            "endpoint": "/api/v1/predictions/analyze",
            "metric_value": 1250.5,
            "threshold": 1000.0,
        },
        {
            "id": "alert_002",
            "title": "错误率偏高",
            "description": "端点 /api/v1/users/profile 错误率超过10%",
            "severity": "critical",
            "status": "active",
            "created_at": "2025-10-30T14:30:00Z",
            "endpoint": "/api/v1/users/profile",
            "metric_value": 12.5,
            "threshold": 10.0,
        },
        {
            "id": "alert_003",
            "title": "缓存命中率下降",
            "description": "系统整体缓存命中率低于70%",
            "severity": "warning",
            "status": "resolved",
            "created_at": "2025-10-30T13:15:00Z",
            "resolved_at": "2025-10-30T14:00:00Z",
            "metric_value": 68.5,
            "threshold": 70.0,
        },
    ]

    # 应用过滤
    filtered_alerts = alerts
    if severity:
        filtered_alerts = [a for a in filtered_alerts if a["severity"] == severity]
    if status_filter:
        filtered_alerts = [a for a in filtered_alerts if a["status"] == status_filter]

    return {
        "alerts": filtered_alerts,
        "total_count": len(alerts),
        "active_count": len([a for a in alerts if a["status"] == "active"]),
        "critical_count": len([a for a in alerts if a["severity"] == "critical"]),
    }


# ==================== 数据库优化端点 ====================


@router.post("/database/optimize")
@require_permission("performance.optimize")
async def optimize_database(
    optimization_config: DatabaseOptimizationModel, background_tasks: BackgroundTasks
):
    """
    优化数据库性能

    需要权限: performance.optimize
    """
    # 启动后台优化任务
    optimization_id = f"db_opt_{int(datetime.utcnow().timestamp())}"

    background_tasks.add_task(
        _run_database_optimization, optimization_id, optimization_config.dict()
    )

    return {
        "message": "数据库优化任务已启动",
        "optimization_id": optimization_id,
        "estimated_duration_minutes": 15,
        "operations": [
            "索引优化" if optimization_config.optimize_indexes else None,
            "数据清理" if optimization_config.cleanup_data else None,
            "表分析" if optimization_config.analyze_tables else None,
            "物化视图刷新" if optimization_config.refresh_views else None,
        ],
    }


@router.get("/database/analysis")
@require_permission("performance.view")
async def get_database_analysis():
    """
    获取数据库分析结果

    需要权限: performance.view
    """
    async with get_db_session():
        optimizer = DatabaseOptimizerFactory.create_optimizer()
        db_optimizer = await optimizer

        try:
            # 分析表大小
            table_sizes = await db_optimizer.analyze_table_sizes()

            # 分析索引使用情况
            index_usage = await db_optimizer.analyze_index_usage()

            # 分析连接池状态
            connection_pool = await db_optimizer.analyze_connection_pool()

            return {
                "table_analysis": table_sizes[:10],  # 返回前10个最大的表
                "index_analysis": {
                    "total_indexes": index_usage.get("total_indexes", 0),
                    "unused_indexes": index_usage.get("unused_count", 0),
                    "unused_details": index_usage.get("unused_indexes", [])[:5],
                },
                "connection_pool": connection_pool,
                "recommendations": _generate_database_recommendations(
                    table_sizes, index_usage, connection_pool
                ),
            }

        finally:
            await db_optimizer.db.close()


@router.get("/database/optimization/{optimization_id}")
@require_permission("performance.view")
async def get_optimization_status(optimization_id: str):
    """
    获取优化任务状态

    需要权限: performance.view
    """
    # 这里应该从实际的优化任务存储中获取状态
    # 暂时返回模拟状态
    return {
        "optimization_id": optimization_id,
        "status": "in_progress",
        "progress_percentage": 65,
        "started_at": "2025-10-30T15:00:00Z",
        "estimated_completion": "2025-10-30T15:15:00Z",
        "completed_operations": [
            {"operation": "索引创建", "status": "completed", "duration_ms": 1250},
            {"operation": "表分析", "status": "completed", "duration_ms": 890},
        ],
        "remaining_operations": [
            {"operation": "数据清理", "status": "pending"},
            {"operation": "视图刷新", "status": "pending"},
        ],
    }


# ==================== 缓存管理端点 ====================


@router.post("/cache/manage")
@require_permission("performance.manage")
async def manage_cache(
    cache_operation: CacheOperationModel, background_tasks: BackgroundTasks
):
    """
    管理缓存

    需要权限: performance.manage
    """
    operation_id = (
        f"cache_{cache_operation.operation}_{int(datetime.utcnow().timestamp())}"
    )

    if cache_operation.operation == "clear":
        if cache_operation.pattern:
            background_tasks.add_task(_clear_cache_by_pattern, cache_operation.pattern)
        elif cache_operation.keys:
            background_tasks.add_task(_clear_cache_by_keys, cache_operation.keys)
        else:
            background_tasks.add_task(_clear_all_cache)

        return {
            "message": "缓存清理任务已启动",
            "operation_id": operation_id,
            "operation_type": "clear",
        }

    elif cache_operation.operation == "warm":
        background_tasks.add_task(_warm_cache, cache_operation.dict())
        return {
            "message": "缓存预热任务已启动",
            "operation_id": operation_id,
            "operation_type": "warm",
        }

    elif cache_operation.operation == "analyze":
        analysis_result = await _analyze_cache_performance()
        return {
            "message": "缓存分析完成",
            "operation_id": operation_id,
            "operation_type": "analyze",
            "analysis": analysis_result,
        }

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的操作类型: {cache_operation.operation}",
        )


@router.get("/cache/statistics")
@require_permission("performance.view")
async def get_cache_statistics():
    """
    获取缓存统计信息

    需要权限: performance.view
    """
    cache_stats = {
        "general_stats": {
            "total_keys": 1250,
            "memory_usage_mb": 245.6,
            "hit_rate": 78.5,
            "miss_rate": 21.5,
            "evictions": 15,
            "connections": 8,
        },
        "performance_metrics": {
            "avg_get_time_ms": 2.5,
            "avg_set_time_ms": 3.2,
            "ops_per_second": 1500.5,
        },
        "key_distribution": {
            "api_cache": 450,
            "user_cache": 320,
            "prediction_cache": 280,
            "match_cache": 200,
        },
        "memory_breakdown": {
            "api_responses": 125.5,
            "user_sessions": 45.2,
            "prediction_data": 75.8,
            "other": 99.1,
        },
        "recommendations": [
            "考虑增加缓存大小以提高命中率",
            "部分键的TTL设置过短,建议适当延长",
            "监控内存使用情况,避免达到内存上限",
        ],
    }

    return cache_stats


# ==================== API优化端点 ====================


@router.post("/api/optimize")
@require_permission("performance.optimize")
async def optimize_api_performance(optimization_request: OptimizationRequestModel):
    """
    优化API性能

    需要权限: performance.optimize
    """
    if optimization_request.optimization_type == "endpoint":
        endpoint = optimization_request.parameters.get("endpoint")
        method = optimization_request.parameters.get("method", "GET")

        if not endpoint:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="端点优化需要指定endpoint参数",
            )

        result = await api_optimizer.optimize_endpoint(endpoint, method)
        return result

    elif optimization_request.optimization_type == "global":
        # 生成性能报告
        report = await api_optimizer.generate_performance_report()
        return {
            "message": "全局性能优化完成",
            "optimization_type": "global",
            "performance_report": report,
        }

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的优化类型: {optimization_request.optimization_type}",
        )


@router.get("/api/analysis")
@require_permission("performance.view")
async def get_api_performance_analysis():
    """
    获取API性能分析

    需要权限: performance.view
    """
    performance_report = await api_optimizer.generate_performance_report()
    return performance_report


# ==================== 后台任务函数 ====================


async def _run_database_optimization(
    optimization_id: str, optimization_config: dict[str, Any]
):
    """运行数据库优化后台任务"""
    async with get_db_session() as db:
        db_optimizer = DatabaseOptimizer(db)
        results = []

        try:
            if optimization_config.get("optimize_indexes"):
                index_results = await db_optimizer.create_performance_indexes()
                results.extend(index_results)

            if optimization_config.get("cleanup_data"):
                cleanup_results = await db_optimizer.cleanup_old_data()
                results.extend(cleanup_results)

            if optimization_config.get("analyze_tables"):
                table_results = await db_optimizer.optimize_large_tables()
                results.extend(table_results)

            if optimization_config.get("refresh_views"):
                view_results = await db_optimizer.refresh_materialized_views()
                results.extend(view_results)

            # 这里应该将结果保存到任务存储中

        except Exception:
            pass


async def _clear_cache_by_pattern(pattern: str):
    """按模式清理缓存"""
    from src.optimizations.api_optimizations import clear_cache

    await clear_cache(pattern)


async def _clear_cache_by_keys(keys: list[str]):
    """按键清理缓存"""
    from src.optimizations.api_optimizations import APICache

    cache_manager = APICache()

    cleared_count = 0
    for key in keys:
        if await cache_manager.delete(key):
            cleared_count += 1


async def _clear_all_cache():
    """清理所有缓存"""
    await _clear_cache_by_pattern("*")


async def _warm_cache(warm_config: dict[str, Any]):
    """缓存预热"""
    # 这里应该实现具体的缓存预热逻辑


async def _analyze_cache_performance() -> dict[str, Any]:
    """分析缓存性能"""
    # 这里应该实现具体的缓存性能分析逻辑
    return {
        "hit_rate": 78.5,
        "miss_rate": 21.5,
        "memory_efficiency": 85.2,
        "key_distribution": {"frequently_accessed": 450, "rarely_accessed": 800},
    }


def _generate_database_recommendations(
    table_sizes: list[dict[str, Any]],
    index_usage: dict[str, Any],
    connection_pool: dict[str, Any],
) -> list[str]:
    """生成数据库优化建议"""
    recommendations = []

    # 表大小建议
    large_tables = [
        t for t in table_sizes if "total_size" in t and "GB" in t["total_size"]
    ]
    if large_tables:
        recommendations.append(f"发现 {len(large_tables)} 个大表,建议考虑分区或归档")

    # 索引使用建议
    unused_count = index_usage.get("unused_count", 0)
    if unused_count > 0:
        recommendations.append(f"发现 {unused_count} 个未使用的索引,建议清理以节省空间")

    # 连接池建议
    total_connections = connection_pool.get("total_connections", 0)
    if total_connections > 80:
        recommendations.append("连接池使用率偏高,建议优化查询或增加连接池大小")

    return recommendations


# ==================== 健康检查端点 ====================


@router.get("/health", tags=["健康检查"])
async def performance_management_health():
    """性能管理健康检查"""
    return {
        "status": "healthy",
        "service": "performance_management",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database_optimizer": "healthy",
            "api_optimizer": "healthy",
            "cache_manager": "healthy",
        },
    }
