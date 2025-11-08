"""
性能监控API端点
Performance Monitoring API Endpoints

提供实时性能监控和指标查询API。
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance", tags=["performance"])


# Pydantic模型
class PerformanceStats(BaseModel):
    """性能统计模型"""

    cpu_usage: float = Field(..., description="CPU使用率(%)")
    memory_usage: float = Field(..., description="内存使用率(%)")
    disk_usage: float = Field(..., description="磁盘使用率(%)")
    active_connections: int = Field(..., description="活跃连接数")
    network_io: float = Field(..., description="网络IO(bytes)")
    timestamp: datetime = Field(..., description="时间戳")


class TaskStats(BaseModel):
    """任务统计模型"""

    total_executions: int = Field(..., description="总执行次数")
    successful_executions: int = Field(..., description="成功执行次数")
    failed_executions: int = Field(..., description="失败执行次数")
    avg_execution_time: float = Field(..., description="平均执行时间(s)")
    max_execution_time: float = Field(..., description="最大执行时间(s)")
    min_execution_time: float = Field(..., description="最小执行时间(s)")


class PerformanceReport(BaseModel):
    """性能报告模型"""

    system_resources: PerformanceStats
    averages: dict[str, float]
    concurrency: dict[str, Any]
    optimization_status: dict[str, bool]
    task_performance: dict[str, TaskStats]
    timestamp: datetime


class Recommendation(BaseModel):
    """性能建议模型"""

    message: str = Field(..., description="建议消息")
    priority: str = Field(..., description="优先级")
    category: str = Field(..., description="建议类别")


class OptimizationConfig(BaseModel):
    """优化配置模型"""

    concurrency_limit: int = Field(..., description="并发限制")
    monitoring_interval: int = Field(..., description="监控间隔(s)")
    cache_size: int = Field(..., description="缓存大小")
    connection_pool_size: int = Field(..., description="连接池大小")
    profile: str = Field(..., description="配置文件")


# API端点实现
@router.get("/status", response_model=dict[str, Any])
async def get_performance_status():
    """获取性能状态"""
    try:
        from ..performance.performance_enhancement_service import (
            get_performance_enhancement_service,
        )

        perf_service = await get_performance_enhancement_service()
        stats = perf_service.get_performance_stats()

        return {
            "status": "active" if perf_service.resource_monitor_active else "inactive",
            "stats": stats,
            "monitoring_active": perf_service.resource_monitor_active,
            "optimization_applied": perf_service.optimization_applied,
        }

    except Exception as e:
        logger.error(f"获取性能状态失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取性能状态失败: {str(e)}"
        ) from e


@router.get("/metrics", response_model=list[PerformanceStats])
async def get_performance_metrics(
    limit: int = Query(default=100, ge=1, le=1000, description="获取指标数量限制")
):
    """获取性能指标历史数据"""
    try:
        from ..performance.performance_enhancement_service import (
            get_performance_enhancement_service,
        )

        perf_service = await get_performance_enhancement_service()

        # 获取最近的性能指标
        recent_metrics = list(perf_service.performance_metrics)[-limit:]

        return [
            PerformanceStats(
                cpu_usage=metric.cpu_usage,
                memory_usage=metric.memory_usage,
                disk_usage=metric.disk_usage,
                active_connections=metric.active_connections,
                network_io=metric.network_io,
                timestamp=metric.timestamp,
            )
            for metric in recent_metrics
        ]

    except Exception as e:
        logger.error(f"获取性能指标失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取性能指标失败: {str(e)}"
        ) from e


@router.get("/report", response_model=PerformanceReport)
async def get_performance_report():
    """获取完整的性能报告"""
    try:
        from ..performance.performance_enhancement_service import (
            get_performance_enhancement_service,
        )

        perf_service = await get_performance_enhancement_service()
        report = perf_service.get_performance_report()

        # 转换为Pydantic模型
        performance_stats = PerformanceStats(
            cpu_usage=report["system_resources"]["cpu_usage"],
            memory_usage=report["system_resources"]["memory_usage"],
            disk_usage=report["system_resources"]["disk_usage"],
            active_connections=report["system_resources"]["active_connections"],
            network_io=report["system_resources"]["network_io"],
            timestamp=datetime.fromisoformat(report["timestamp"]),
        )

        task_performance = {
            task_name: TaskStats(**stats)
            for task_name, stats in report["task_performance"].items()
        }

        return PerformanceReport(
            system_resources=performance_stats,
            averages=report["averages"],
            concurrency=report["concurrency"],
            optimization_status=report["optimization_status"],
            task_performance=task_performance,
            timestamp=performance_stats.timestamp,
        )

    except Exception as e:
        logger.error(f"获取性能报告失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取性能报告失败: {str(e)}"
        ) from e


@router.get("/recommendations", response_model=list[Recommendation])
async def get_performance_recommendations():
    """获取性能优化建议"""
    try:
        from ..performance.performance_enhancement_service import (
            get_performance_enhancement_service,
        )

        perf_service = await get_performance_enhancement_service()
        recommendations = perf_service.get_performance_recommendations()

        # 转换为Recommendation模型
        result = []
        priority_map = {"✅": "low", "⚠️": "medium", "🔥": "high"}

        for rec in recommendations:
            priority = "medium"  # 默认优先级
            for icon, level in priority_map.items():
                if rec.startswith(icon):
                    priority = level
                    break

            result.append(
                Recommendation(message=rec, priority=priority, category="performance")
            )

        return result

    except Exception as e:
        logger.error(f"获取性能建议失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取性能建议失败: {str(e)}"
        ) from e


@router.post("/optimize")
async def apply_performance_optimization(config: OptimizationConfig) -> dict[str, Any]:
    """应用性能优化配置"""
    try:
        from ..performance.performance_enhancement_service import (
            get_performance_enhancement_service,
        )

        perf_service = await get_performance_enhancement_service()
        result = await perf_service.apply_performance_tuning(config.profile)

        return result

    except Exception as e:
        logger.error(f"应用性能优化失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"应用性能优化失败: {str(e)}"
        ) from e


@router.get("/health")
async def performance_health_check():
    """性能监控健康检查"""
    try:
        from ..performance.performance_enhancement_service import (
            get_performance_enhancement_service,
        )

        perf_service = await get_performance_enhancement_service()

        if not perf_service.performance_metrics:
            return {
                "status": "unhealthy",
                "reason": "没有性能数据",
                "monitoring_active": perf_service.resource_monitor_active,
            }

        latest = perf_service.performance_metrics[-1]

        # 健康检查
        health_issues = []
        if latest.cpu_usage > 90:
            health_issues.append("CPU使用率过高")
        if latest.memory_usage > 90:
            health_issues.append("内存使用率过高")
        if not perf_service.resource_monitor_active:
            health_issues.append("性能监控未启动")

        return {
            "status": "healthy" if not health_issues else "unhealthy",
            "issues": health_issues,
            "monitoring_active": perf_service.resource_monitor_active,
            "latest_metrics": {
                "cpu": latest.cpu_usage,
                "memory": latest.memory_usage,
                "connections": latest.active_connections,
            },
        }

    except Exception as e:
        logger.error(f"性能健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "reason": f"健康检查失败: {str(e)}",
            "monitoring_active": False,
        }


@router.get("/tasks/stats")
async def get_task_statistics():
    """获取任务执行统计"""
    try:
        from ..performance.async_task_manager import get_async_task_manager

        task_manager = await get_async_task_manager()
        stats = task_manager.get_task_stats()

        return {
            "task_queue_size": stats["queue_size"],
            "active_tasks": stats["active_tasks"],
            "completed_tasks": stats["completed_tasks"],
            "failed_tasks": stats["failed_tasks"],
            "workers_active": stats["workers_active"],
            "total_executions": sum(
                task_stats.get("total_executions", 0)
                for task_stats in stats["task_stats"].values()
            ),
            "success_rate": (
                stats["completed_tasks"]
                / (stats["completed_tasks"] + stats["failed_tasks"])
                * 100
                if (stats["completed_tasks"] + stats["failed_tasks"]) > 0
                else 0
            ),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"获取任务统计失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取任务统计失败: {str(e)}"
        ) from e
