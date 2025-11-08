# mypy: ignore-errors
"""
性能监控API端点
Performance Monitoring API Endpoints

提供性能监控相关的API:
- 获取实时性能指标
- 获取性能报告
- 启动/停止性能分析
- 获取性能趋势
- 配置性能阈值
"""

import asyncio
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from src.core.logging import get_logger
from src.performance.analyzer import PerformanceAnalyzer
from src.performance.middleware import (
    BackgroundTaskPerformanceMonitor,
    CachePerformanceMiddleware,
    DatabasePerformanceMiddleware,
)
from src.performance.profiler import get_profiler

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
                "memory_total": memory_info.total / 1024 / 1024,
                # MB
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

    except (ValueError, KeyError, AttributeError) as e:
        logger.error(f"Failed to get performance metrics: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve performance metrics"
        ) from e


@router.post("/profiling/start")
async def start_profiling(config: PerformanceRequest):
    """启动性能分析"""
    try:
        profiler = get_profiler()

        if profiler.active_profiling:
            raise HTTPException(
                status_code=400, detail="Profiling is already active"
            )  # TODO: B904 exception chaining

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

    except (ValueError, KeyError, AttributeError) as e:
        logger.error(f"Failed to start profiling: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to start performance profiling"
        ) from e


@router.post("/profiling/stop")
async def stop_profiling():
    """停止性能分析"""
    try:
        profiler = get_profiler()

        if not profiler.active_profiling:
            raise HTTPException(
                status_code=400, detail="No active profiling session"
            )  # TODO: B904 exception chaining

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

    except (ValueError, KeyError, AttributeError) as e:
        logger.error(f"Failed to stop profiling: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to stop performance profiling"
        ) from e


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

    except (ValueError, KeyError, AttributeError) as e:
        logger.error(f"Failed to get profiling results: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve profiling results"
        ) from e


@router.get("/report")
async def get_performance_report(
    background_tasks: BackgroundTasks,
    export_format: str = Query(default="json", regex="^(json|html)$"),
    include_recommendations: bool = Query(default=True),
):
    """生成性能报告"""
    try:
        # 收集性能数据
        api_stats: dict = {}  # 从中间件获取
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

    except (ValueError, KeyError, AttributeError) as e:
        logger.error(f"Failed to generate performance report: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to generate performance report"
        )  # TODO: B904 exception chaining
