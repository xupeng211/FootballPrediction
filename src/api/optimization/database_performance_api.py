"""
数据库性能监控API端点
Database Performance Monitoring API Endpoints

提供完整的数据库性能监控、分析和优化功能的REST API接口。
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.optimization.connection_pool_optimizer import get_connection_pool_optimizer
from src.api.optimization.database_performance_middleware import (
    get_database_middleware,
    get_optimization_advisor,
)
from src.api.optimization.database_query_optimizer import get_database_analyzer
from src.api.optimization.query_execution_analyzer import get_query_execution_analyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/database", tags=["数据库性能监控"])


# ==================== 请求/响应模型 ====================


class QueryAnalysisRequest(BaseModel):
    """查询分析请求模型"""

    query_text: str = Field(..., description="要分析的SQL查询语句")
    analyze_execution_plan: bool = Field(True, description="是否分析执行计划")
    analyze_options: dict[str, Any] | None = Field(None, description="分析选项")


class DatabaseOptimizationRequest(BaseModel):
    """数据库优化请求模型"""

    optimization_type: str = Field(..., description="优化类型: query, pool, index, all")
    target_pool: str | None = Field(None, description="目标连接池名称")
    parameters: dict[str, Any] | None = Field(None, description="优化参数")


class PerformanceMonitorRequest(BaseModel):
    """性能监控请求模型"""

    enable_monitoring: bool = Field(True, description="是否启用监控")
    slow_query_threshold: float = Field(1.0, description="慢查询阈值（秒）")
    enable_query_tracking: bool = Field(True, description="是否启用查询跟踪")
    enable_pool_monitoring: bool = Field(True, description="是否启用连接池监控")


# ==================== 数据库性能状态端点 ====================


@router.get("/performance/status")
async def get_database_performance_status():
    """获取数据库性能监控状态"""
    db_analyzer = get_database_analyzer()
    db_middleware = get_database_middleware()
    pool_optimizer = get_connection_pool_optimizer()
    execution_analyzer = get_query_execution_analyzer()

    # 获取各组件状态
    analyzer_summary = db_analyzer.get_performance_summary()
    await db_middleware.get_real_time_metrics()
    pools_status = await pool_optimizer.get_all_pools_status()
    analyzer_stats = execution_analyzer.get_analysis_statistics()

    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "query_analyzer": {
                "enabled": True,
                "status": "active",
                "queries_analyzed": analyzer_summary.get("total_queries", 0),
                "unique_queries": analyzer_summary.get("unique_queries", 0),
                "avg_response_time": analyzer_summary.get("avg_response_time", 0.0),
            },
            "performance_middleware": {
                "enabled": db_middleware.is_monitoring,
                "status": "active" if db_middleware.is_monitoring else "disabled",
                "monitoring_config": {
                    "slow_query_threshold": db_middleware.slow_query_threshold,
                    "query_tracking": db_middleware.enable_query_tracking,
                    "pool_monitoring": db_middleware.enable_connection_pool_monitoring,
                },
            },
            "connection_pool_optimizer": {
                "enabled": pool_optimizer.is_monitoring,
                "status": "active" if pool_optimizer.is_monitoring else "disabled",
                "monitored_pools": pools_status.get("total_pools", 0),
                "total_connections": pools_status.get("summary", {}).get(
                    "total_connections", 0
                ),
                "avg_utilization": pools_status.get("summary", {}).get(
                    "avg_utilization", 0.0
                ),
            },
            "execution_analyzer": {
                "enabled": True,
                "status": "active",
                "cached_plans": analyzer_stats.get("cache_size", 0),
                "total_analyzed": analyzer_stats.get("total_analyzed", 0),
                "avg_execution_time": analyzer_stats.get("avg_execution_time", 0.0),
            },
        },
    }

    return status


# ==================== 查询性能分析端点 ====================


@router.post("/queries/analyze")
async def analyze_query_performance(request: QueryAnalysisRequest):
    """分析查询性能"""
    execution_analyzer = get_query_execution_analyzer()
    optimization_advisor = get_optimization_advisor()

    try:
        # 生成查询哈希
        query_hash = execution_analyzer._generate_query_hash(request.query_text)

        # 执行执行计划分析
        execution_analysis = None
        if request.analyze_execution_plan:
            # 这里需要数据库会话，暂时返回模拟数据
            execution_analysis = {
                "query_hash": query_hash,
                "message": "Execution plan analysis requires database session",
                "suggestions": [],
            }

        # 执行查询优化建议分析
        optimization_analysis = (
            await optimization_advisor.analyze_query_for_optimization(
                request.query_text
            )
        )

        return {
            "query_hash": query_hash,
            "query_analysis": {
                "execution_plan": execution_analysis,
                "optimization_advice": optimization_analysis,
                "analysis_timestamp": datetime.utcnow().isoformat(),
            },
        }

    except Exception as e:
        logger.error(f"Error analyzing query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询分析失败: {str(e)}",
        ) from e


@router.get("/queries/slow")
async def get_slow_queries(limit: int = Query(20, ge=1, le=100)):
    """获取慢查询列表"""
    db_analyzer = get_database_analyzer()

    try:
        slow_queries = await db_analyzer.get_top_slow_queries(limit)

        return {
            "slow_queries": slow_queries,
            "total_count": len(slow_queries),
            "threshold": 1.0,  # 慢查询阈值
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting slow queries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取慢查询失败: {str(e)}",
        ) from e


@router.get("/queries/frequent")
async def get_frequent_queries(limit: int = Query(20, ge=1, le=100)):
    """获取频繁执行的查询"""
    db_analyzer = get_database_analyzer()

    try:
        frequent_queries = await db_analyzer.get_most_frequent_queries(limit)

        return {
            "frequent_queries": frequent_queries,
            "total_count": len(frequent_queries),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting frequent queries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取频繁查询失败: {str(e)}",
        ) from e


@router.get("/queries/errors")
async def get_high_error_queries(min_error_rate: float = Query(5.0, ge=0.0, le=100.0)):
    """获取高错误率查询"""
    db_analyzer = get_database_analyzer()

    try:
        error_queries = await db_analyzer.get_queries_with_high_error_rate(
            min_error_rate
        )

        return {
            "high_error_queries": error_queries,
            "threshold": min_error_rate,
            "total_count": len(error_queries),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting high error queries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取高错误率查询失败: {str(e)}",
        ) from e


# ==================== 连接池监控端点 ====================


@router.get("/pools/status")
async def get_connection_pools_status():
    """获取所有连接池状态"""
    pool_optimizer = get_connection_pool_optimizer()

    try:
        pools_status = await pool_optimizer.get_all_pools_status()

        return pools_status

    except Exception as e:
        logger.error(f"Error getting pools status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取连接池状态失败: {str(e)}",
        ) from e


@router.get("/pools/{pool_name}/status")
async def get_specific_pool_status(pool_name: str):
    """获取特定连接池状态"""
    pool_optimizer = get_connection_pool_optimizer()

    try:
        pool_status = await pool_optimizer.get_pool_status(pool_name)

        if pool_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"连接池 {pool_name} 不存在",
            )

        return pool_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pool status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取连接池状态失败: {str(e)}",
        ) from e


@router.post("/pools/{pool_name}/optimize")
async def optimize_connection_pool(
    pool_name: str, optimization_type: str, parameters: dict[str, Any] | None = None
):
    """优化特定连接池"""
    pool_optimizer = get_connection_pool_optimizer()

    try:
        result = await pool_optimizer.optimize_pool_manually(
            pool_name, optimization_type, **(parameters or {})
        )

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"]
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error optimizing pool: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"连接池优化失败: {str(e)}",
        ) from e


@router.get("/pools/optimization/history")
async def get_pool_optimization_history(limit: int = Query(50, ge=1, le=200)):
    """获取连接池优化历史"""
    pool_optimizer = get_connection_pool_optimizer()

    try:
        history = pool_optimizer.get_optimization_history(limit)

        return {
            "optimization_history": history,
            "total_count": len(history),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting optimization history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取优化历史失败: {str(e)}",
        ) from e


# ==================== 性能优化端点 ====================


@router.post("/performance/optimize")
async def optimize_database_performance(
    request: DatabaseOptimizationRequest, background_tasks: BackgroundTasks
):
    """优化数据库性能"""
    optimization_id = f"db_opt_{int(datetime.utcnow().timestamp())}"
    result = {
        "optimization_id": optimization_id,
        "optimization_type": request.optimization_type,
        "started_at": datetime.utcnow().isoformat(),
    }

    try:
        if request.optimization_type == "query":
            # 查询优化
            db_analyzer = get_database_analyzer()
            suggestions = await db_analyzer.get_optimization_suggestions()

            result["query_optimization"] = {
                "suggestions_count": len(suggestions),
                "high_priority_suggestions": len(
                    [s for s in suggestions if s["priority"] in ["critical", "high"]]
                ),
                "suggestions": suggestions[:10],  # 返回前10个建议
            }
            result["message"] = "查询优化分析完成"

        elif request.optimization_type == "pool":
            # 连接池优化
            if request.target_pool:
                pool_optimizer = get_connection_pool_optimizer()
                optimization_result = await pool_optimizer.optimize_pool_manually(
                    request.target_pool,
                    (
                        request.parameters.get("operation", "auto")
                        if request.parameters
                        else "auto"
                    ),
                )
                result["pool_optimization"] = optimization_result
            else:
                result["message"] = "连接池优化需要指定target_pool"

        elif request.optimization_type == "index":
            # 索引优化
            result["index_optimization"] = {
                "message": "索引优化功能需要数据库会话",
                "suggestions": [
                    "分析查询模式以确定缺失的索引",
                    "检查未使用的索引",
                    "优化复合索引顺序",
                ],
            }

        elif request.optimization_type == "all":
            # 全局优化
            background_tasks.add_task(
                _run_global_database_optimization, optimization_id, request.parameters
            )
            result["message"] = "全局数据库优化任务已启动"
            result["status"] = "running"

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的优化类型: {request.optimization_type}",
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in database optimization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据库优化失败: {str(e)}",
        ) from e


@router.get("/optimization/{optimization_id}/status")
async def get_optimization_status(optimization_id: str):
    """获取优化任务状态"""
    # 这里应该从任务存储中获取实际状态
    # 暂时返回模拟状态
    return {
        "optimization_id": optimization_id,
        "status": "completed",
        "progress_percentage": 100,
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
        "results": {
            "queries_optimized": 15,
            "pools_adjusted": 2,
            "performance_improvement": "12.5%",
        },
    }


# ==================== 性能监控配置端点 ====================


@router.post("/monitoring/configure")
async def configure_performance_monitoring(request: PerformanceMonitorRequest):
    """配置性能监控"""
    db_middleware = get_database_middleware()
    pool_optimizer = get_connection_pool_optimizer()

    try:
        # 配置中间件监控
        if request.enable_monitoring:
            await db_middleware.start_monitoring()
        else:
            db_middleware.stop_monitoring()

        # 更新配置
        db_middleware.slow_query_threshold = request.slow_query_threshold
        db_middleware.enable_query_tracking = request.enable_query_tracking
        db_middleware.enable_connection_pool_monitoring = request.enable_pool_monitoring

        # 配置连接池监控
        if request.enable_monitoring:
            await pool_optimizer.start_monitoring()
        else:
            await pool_optimizer.stop_monitoring()

        return {
            "message": "性能监控配置已更新",
            "configuration": {
                "monitoring_enabled": request.enable_monitoring,
                "slow_query_threshold": request.slow_query_threshold,
                "query_tracking": request.enable_query_tracking,
                "pool_monitoring": request.enable_pool_monitoring,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error configuring monitoring: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配置性能监控失败: {str(e)}",
        ) from e


@router.get("/monitoring/metrics")
async def get_current_metrics():
    """获取当前性能指标"""
    db_middleware = get_database_middleware()

    try:
        metrics = await db_middleware.get_real_time_metrics()
        return metrics

    except Exception as e:
        logger.error(f"Error getting current metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取性能指标失败: {str(e)}",
        ) from None


# ==================== 性能报告端点 ====================


@router.get("/reports/performance")
@router.get("/reports/performance")
async def get_performance_report(
    time_range_hours: int = Query(24, ge=1, le=168),  # 1小时到7天
    include_details: bool = Query(True),
):
    """获取数据库性能报告"""
    db_analyzer = get_database_analyzer()
    pool_optimizer = get_connection_pool_optimizer()

    try:
        # 获取基本性能数据
        performance_summary = db_analyzer.get_performance_summary()
        optimization_suggestions = await db_analyzer.get_optimization_suggestions()
        pools_status = await pool_optimizer.get_all_pools_status()

        # 构建报告
        report = {
            "report_timestamp": datetime.utcnow().isoformat(),
            "time_range_hours": time_range_hours,
            "performance_summary": performance_summary,
            "optimization_suggestions": {
                "total_count": len(optimization_suggestions),
                "critical_priority": len(
                    [s for s in optimization_suggestions if s["priority"] == "critical"]
                ),
                "high_priority": len(
                    [s for s in optimization_suggestions if s["priority"] == "high"]
                ),
                "medium_priority": len(
                    [s for s in optimization_suggestions if s["priority"] == "medium"]
                ),
                "suggestions": optimization_suggestions[:20] if include_details else [],
            },
            "connection_pools": {
                "total_pools": pools_status.get("total_pools", 0),
                "summary": pools_status.get("summary", {}),
                "details": pools_status.get("pools", {}) if include_details else {},
            },
        }

        # 添加健康评估
        report["health_assessment"] = _assess_database_health(report)

        return report

    except Exception as e:
        logger.error(f"Error generating performance report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成性能报告失败: {str(e)}",
        ) from e


def _assess_database_health(report: dict[str, Any]) -> dict[str, Any]:
    """评估数据库健康状态"""
    health_score = 100
    issues = []

    # 检查平均响应时间
    avg_response_time = report["performance_summary"].get("avg_response_time", 0)
    if avg_response_time > 2.0:
        health_score -= 20
        issues.append(f"平均响应时间过长: {avg_response_time:.4f}s")
    elif avg_response_time > 1.0:
        health_score -= 10
        issues.append(f"平均响应时间较长: {avg_response_time:.4f}s")

    # 检查慢查询
    slow_queries_count = report["performance_summary"].get("slow_queries_count", 0)
    if slow_queries_count > 10:
        health_score -= 15
        issues.append(f"慢查询数量过多: {slow_queries_count}")

    # 检查高错误率查询
    high_error_queries = report["performance_summary"].get("high_error_rate_queries", 0)
    if high_error_queries > 5:
        health_score -= 25
        issues.append(f"高错误率查询过多: {high_error_queries}")

    # 检查连接池状态
    pools_summary = report["connection_pools"].get("summary", {})
    critical_pools = pools_summary.get("critical_pools", 0)
    warning_pools = pools_summary.get("warning_pools", 0)

    if critical_pools > 0:
        health_score -= 20
        issues.append(f"存在严重状态的连接池: {critical_pools}")

    if warning_pools > 0:
        health_score -= 10
        issues.append(f"存在警告状态的连接池: {warning_pools}")

    # 确定健康等级
    if health_score >= 90:
        health_status = "excellent"
    elif health_score >= 75:
        health_status = "good"
    elif health_score >= 60:
        health_status = "fair"
    else:
        health_status = "poor"

    return {
        "health_score": max(0, health_score),
        "health_status": health_status,
        "issues": issues,
        "recommendations": [
            "定期监控查询性能",
            "优化慢查询",
            "维护适当的索引",
            "监控连接池状态",
        ],
    }


# ==================== 后台任务函数 ====================


async def _run_global_database_optimization(
    optimization_id: str, parameters: dict[str, Any] | None
):
    """运行全局数据库优化"""
    try:
        logger.info(f"Starting global database optimization: {optimization_id}")

        # 获取分析器
        db_analyzer = get_database_analyzer()
        pool_optimizer = get_connection_pool_optimizer()

        # 清理旧数据
        await db_analyzer.clear_old_data(days_to_keep=7)

        # 生成优化建议
        suggestions = await db_analyzer.get_optimization_suggestions()

        # 应用连接池优化
        pools_status = await pool_optimizer.get_all_pools_status()

        logger.info(f"Global database optimization completed: {optimization_id}")
        logger.info(f"Generated {len(suggestions)} optimization suggestions")
        logger.info(f"Analyzed {pools_status.get('total_pools', 0)} connection pools")

    except Exception as e:
        logger.error(f"Global database optimization error: {e}")


# ==================== 健康检查端点 ====================


@router.get("/health", tags=["健康检查"])
async def database_performance_health():
    """数据库性能监控服务健康检查"""
    db_middleware = get_database_middleware()
    pool_optimizer = get_connection_pool_optimizer()
    get_database_analyzer()

    components = {
        "performance_middleware": (
            "healthy" if db_middleware.is_monitoring else "disabled"
        ),
        "connection_pool_optimizer": (
            "healthy" if pool_optimizer.is_monitoring else "disabled"
        ),
        "query_analyzer": "healthy",
    }

    overall_status = (
        "healthy"
        if all(status in ["healthy", "disabled"] for status in components.values())
        else "degraded"
    )

    return {
        "status": overall_status,
        "service": "database_performance_monitoring",
        "timestamp": datetime.utcnow().isoformat(),
        "components": components,
        "version": "1.0.0",
    }
