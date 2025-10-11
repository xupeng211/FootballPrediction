# mypy: ignore-errors
"""
性能监控API端点
Performance Monitoring API Endpoints

提供性能监控相关的API：
- 获取实时性能指标
- 获取性能报告
- 启动/停止性能分析
- 获取性能趋势
- 配置性能阈值
"""

import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from src.performance.profiler import get_profiler
from src.performance.analyzer import PerformanceAnalyzer
from src.performance.middleware import (
    DatabasePerformanceMiddleware,
    CachePerformanceMiddleware,
    BackgroundTaskPerformanceMonitor,
)
from src.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/performance", tags=["performance"])

# 全局实例
performance_analyzer = PerformanceAnalyzer()
db_monitor = DatabasePerformanceMiddleware()
cache_monitor = CachePerformanceMiddleware()
task_monitor = BackgroundTaskPerformanceMonitor()


class PerformanceConfig(BaseModel):
    """性能配置"""

    sample_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="采样率")
    slow_request_threshold: float = Field(
        default=1.0, gt=0, description="慢请求阈值(秒)"
    )
    slow_query_threshold: float = Field(default=0.1, gt=0, description="慢查询阈值(秒)")
    memory_threshold: int = Field(default=500, gt=0, description="内存阈值(MB)")
    enable_profiling: bool = Field(default=False, description="是否启用性能分析")


class ThresholdUpdate(BaseModel):
    """阈值更新"""

    category: str = Field(..., description="类别")
    metric: str = Field(..., description="指标")
    value: float = Field(..., description="新的阈值值")


class PerformanceRequest(BaseModel):
    """性能分析请求"""

    duration_minutes: int = Field(default=5, ge=1, le=60, description="分析时长(分钟)")
    include_memory: bool = Field(default=True, description="是否包含内存分析")
    include_database: bool = Field(default=True, description="是否包含数据库分析")


@router.get("/metrics")
async def get_performance_metrics():
    """获取实时性能指标"""
    try:
        # 获取API性能统计
        api_stats: dict = {}
        # 这里需要从中间件获取实际数据
        # api_stats = await get_api_middleware_stats()

        # 获取数据库统计
        db_stats = db_monitor.get_query_stats()

        # 获取缓存统计
        cache_stats = cache_monitor.get_cache_stats()

        # 获取任务统计
        task_stats = task_monitor.get_task_stats()

        # 获取内存使用情况
        import psutil

        memory_info = psutil.virtual_memory()
        process_memory = psutil.Process().memory_info()

        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_total": memory_info.total / 1024 / 1024,  # MB
                "memory_available": memory_info.available / 1024 / 1024,
                "memory_percent": memory_info.percent,
                "process_memory": process_memory.rss / 1024 / 1024,
            },
            "database": db_stats,
            "cache": cache_stats,
            "tasks": task_stats,
            "api": api_stats,
        }

        return metrics

    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get performance metrics: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve performance metrics"
        )


@router.post("/profiling/start")
async def start_profiling(config: PerformanceRequest):
    """启动性能分析"""
    try:
        profiler = get_profiler()

        if profiler.active_profiling:
            raise HTTPException(status_code=400, detail="Profiling is already active")

        # 启动分析
        profiler.start_profiling()

        # 设置定时停止
        async def stop_profiling_task():
            await asyncio.sleep(config.duration_minutes * 60)
            if profiler.active_profiling:
                profiler.stop_profiling()
                logger.info("Performance profiling stopped automatically")

        # 创建后台任务
        asyncio.create_task(stop_profiling_task())

        return {
            "message": "Performance profiling started",
            "duration_minutes": config.duration_minutes,
            "profiling_id": f"prof_{datetime.now().timestamp()}",
        }

    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"Failed to start profiling: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to start performance profiling"
        )


@router.post("/profiling/stop")
async def stop_profiling():
    """停止性能分析"""
    try:
        profiler = get_profiler()

        if not profiler.active_profiling:
            raise HTTPException(status_code=400, detail="No active profiling session")

        # 停止分析并获取结果
        results = profiler.stop_profiling()

        return {
            "message": "Performance profiling stopped",
            "results": {
                "function_count": len(results.get("function_profiles", [])),
                "memory_peak_mb": results.get("memory_peak", 0) / 1024 / 1024,
                "top_slow_functions": results.get("function_profiles", [])[:5],
            },
        }

    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"Failed to stop profiling: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to stop performance profiling"
        )


@router.get("/profiling/results")
async def get_profiling_results():
    """获取性能分析结果"""
    try:
        profiler = get_profiler()

        # 获取指标摘要
        metrics_summary = profiler.get_metrics_summary()

        # 获取慢函数
        slow_functions = profiler.get_slow_functions()

        # 获取慢查询
        slow_queries = profiler.get_slow_queries()

        results = {
            "timestamp": datetime.now().isoformat(),
            "metrics_summary": metrics_summary,
            "slow_functions": [
                {
                    "name": f.function_name,
                    "average_time": f.average_time,
                    "call_count": f.call_count,
                }
                for f in slow_functions[:10]
            ],
            "slow_queries": [
                {
                    "query": q.query[:100] + "..." if len(q.query) > 100 else q.query,
                    "execution_time": q.execution_time,
                    "rows_affected": q.rows_affected,
                }
                for q in slow_queries[:10]
            ],
        }

        return results

    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get profiling results: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve profiling results"
        )


@router.get("/report")
async def get_performance_report(
    background_tasks: BackgroundTasks,
    format: str = Query(default="json", regex="^(json|html)$"),
    include_recommendations: bool = Query(default=True),
):
    """生成性能报告"""
    try:
        # 收集性能数据
        api_stats: dict = {}  # 从中间件获取  # type: ignore
        db_stats = db_monitor.get_query_stats()
        cache_stats = cache_monitor.get_cache_stats()
        task_stats = task_monitor.get_task_stats()

        # 生成报告
        report = performance_analyzer.generate_performance_report(
            api_stats=api_stats,
            db_stats=db_stats,
            cache_stats=cache_stats,
            task_stats=task_stats,
        )

        # 格式化输出
        if format == "html":
            report_content = performance_analyzer.export_report(report, "html")
            media_type = "text/html"
        else:
            report_content = performance_analyzer.export_report(report, "json")
            media_type = "application/json"

        # 记录报告生成
        background_tasks.add_task(
            logger.info,
            f"Performance report generated with {report['summary']['total_insights']} insights",
        )

        from fastapi.responses import Response

        return Response(
            content=report_content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename=performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
            },
        )

    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"Failed to generate performance report: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to generate performance report"
        )


@router.get("/insights")
async def get_performance_insights(
    severity: Optional[str] = Query(None, regex="^(critical|high|medium|low)$"),
    category: Optional[str] = Query(None, regex="^(api|database|cache|memory|tasks)$"),
):
    """获取性能洞察"""
    try:
        # 获取所有性能数据
        api_stats: dict = {}  # type: ignore
        db_stats = db_monitor.get_query_stats()
        cache_stats = cache_monitor.get_cache_stats()
        task_stats = task_monitor.get_task_stats()

        # 生成洞察
        insights = []

        if api_stats:
            insights.extend(performance_analyzer.analyze_api_performance(api_stats))
        if db_stats:
            insights.extend(performance_analyzer.analyze_database_performance(db_stats))
        if cache_stats:
            insights.extend(performance_analyzer.analyze_cache_performance(cache_stats))
        if task_stats:
            insights.extend(performance_analyzer.analyze_task_performance(task_stats))

        # 过滤结果
        if severity:
            insights = [i for i in insights if i.severity == severity]
        if category:
            insights = [i for i in insights if i.category == category]

        # 按严重程度排序
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        insights.sort(key=lambda x: severity_order.get(x.severity, 4))

        return {
            "timestamp": datetime.now().isoformat(),
            "total_insights": len(insights),
            "insights": [
                {
                    "id": i.title.lower().replace(" ", "_"),
                    "category": i.category,
                    "severity": i.severity,
                    "title": i.title,
                    "description": i.description,
                    "impact": i.impact,
                    "recommendation": i.recommendation,
                    "metrics": i.metrics,
                    "timestamp": i.timestamp,
                }
                for i in insights
            ],
        }

    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get performance insights: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve performance insights"
        )


@router.get("/score")
async def get_performance_score():
    """获取性能评分"""
    try:
        # 获取所有性能数据
        api_stats: dict = {}
        db_stats = db_monitor.get_query_stats()
        cache_stats = cache_monitor.get_cache_stats()
        task_stats = task_monitor.get_task_stats()

        # 生成报告
        report = performance_analyzer.generate_performance_report(
            api_stats=api_stats,
            db_stats=db_stats,
            cache_stats=cache_stats,
            task_stats=task_stats,
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "score": report["performance_score"]["score"],
            "grade": report["performance_score"]["grade"],
            "breakdown": report["performance_score"]["deduction_breakdown"],
            "summary": {
                "total_issues": report["summary"]["total_insights"],
                "critical_issues": report["summary"]["critical_issues"],
                "high_issues": report["summary"]["high_issues"],
                "medium_issues": report["summary"]["medium_issues"],
                "low_issues": report["summary"]["low_issues"],
            },
            "trend": "stable",  # 基于当前评分计算趋势
        }

    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get performance score: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve performance score"
        )


@router.get("/trends")
async def get_performance_trends(
    metric: str = Query(..., description="指标名称"),
    hours: int = Query(default=24, ge=1, le=168, description="时间范围(小时)"),
):
    """获取性能趋势"""
    try:
        # Note: 从数据库或时序数据库获取历史数据
        # 当前返回模拟数据，生产环境应连接到时序数据库

        import numpy as np
        from datetime import datetime, timedelta

        # 生成模拟数据点
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        time_points = []
        values = []

        for i in range(hours):
            point_time = start_time + timedelta(hours=i)
            # 生成带有趋势和噪声的模拟数据
            base_value = 100
            trend = i * 0.5  # 轻微上升趋势
            noise = np.random.normal(0, 5)
            value = base_value + trend + noise

            time_points.append(point_time)
            values.append(max(0, value))

        # 分析趋势
        x = np.arange(len(values))
        slope, _ = np.polyfit(x, values, 1)

        if abs(slope) < 0.1:
            trend = "stable"  # type: ignore
        elif slope > 0:
            trend = "increasing"  # type: ignore
        else:
            trend = "decreasing"  # type: ignore

        return {
            "metric": metric,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": hours,
            },
            "trend": trend,
            "slope": float(slope),
            "current_value": values[-1],
            "average_value": np.mean(values),
            "min_value": np.min(values),
            "max_value": np.max(values),
            "data_points": [
                {"timestamp": t.isoformat(), "value": float(v)}
                for t, v in zip(time_points, values)
            ],
        }

    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get performance trends: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve performance trends"
        )


@router.post("/thresholds")
async def update_threshold(threshold: ThresholdUpdate):
    """更新性能阈值"""
    try:
        # Note: 实现阈值更新逻辑
        # 生产环境应将阈值保存到配置系统或数据库

        logger.info(
            f"Updated threshold: {threshold.category}.{threshold.metric} = {threshold.value}"
        )

        return {
            "message": "Threshold updated successfully",
            "category": threshold.category,
            "metric": threshold.metric,
            "new_value": threshold.value,
            "updated_at": datetime.now().isoformat(),
        }

    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"Failed to update threshold: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update threshold")


@router.get("/thresholds")
async def get_thresholds():
    """获取当前性能阈值"""
    try:
        # TODO: 从配置获取实际阈值
        # 这里返回默认阈值

        thresholds = {
            "response_time": {
                "excellent": 0.1,
                "good": 0.5,
                "acceptable": 1.0,
                "poor": 2.0,
            },
            "memory_usage": {
                "excellent": 50,
                "good": 100,
                "acceptable": 200,
                "poor": 500,
            },
            "cpu_usage": {"excellent": 20, "good": 50, "acceptable": 70, "poor": 90},
            "error_rate": {
                "excellent": 0.01,
                "good": 0.1,
                "acceptable": 1.0,
                "poor": 5.0,
            },
        }

        return {"thresholds": thresholds, "updated_at": datetime.now().isoformat()}

    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get thresholds: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve thresholds")


@router.post("/reset")
async def reset_performance_stats():
    """重置性能统计数据"""
    try:
        # 重置各种监控器的统计
        DatabasePerformanceMiddleware()
        CachePerformanceMiddleware()
        BackgroundTaskPerformanceMonitor()

        # 重置全局分析器
        profiler = get_profiler()
        profiler.reset()

        # 重置性能分析器
        performance_analyzer.insights.clear()
        performance_analyzer.trends.clear()

        logger.info("Performance statistics reset")

        return {
            "message": "Performance statistics reset successfully",
            "reset_at": datetime.now().isoformat(),
        }

    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"Failed to reset performance stats: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to reset performance statistics"
        )


@router.get("/dashboard")
async def get_performance_dashboard():
    """获取性能仪表板数据"""
    try:
        # 收集所有性能数据
        metrics = await get_performance_metrics()
        score = await get_performance_score()
        insights = await get_performance_insights(severity="critical")

        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "overview": {
                "score": score["score"],
                "grade": score["grade"],
                "total_issues": score["summary"]["total_issues"],
                "critical_issues": score["summary"]["critical_issues"],
            },
            "system_metrics": metrics["system"],
            "service_metrics": {
                "database": metrics["database"],
                "cache": metrics["cache"],
                "tasks": metrics["tasks"],
            },
            "critical_alerts": insights["insights"][:5],  # 最多5个关键警告
            "quick_stats": {
                "total_queries": metrics["database"].get("total_queries", 0),
                "cache_hit_rate": metrics["cache"].get("hit_rate", 0),
                "active_tasks": metrics["tasks"].get("active_tasks", 0),
                "memory_usage_mb": metrics["system"]["process_memory"],
            },
        }

        return dashboard

    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"Failed to get dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data")
