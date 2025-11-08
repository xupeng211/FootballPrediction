from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware

from .enhanced_optimizer import monitor_performance, performance_optimizer
from .middleware import PerformanceMonitoringMiddleware

"""
性能优化系统集成
Performance Optimization Integration

整合所有性能优化组件到FastAPI应用中，包括异步优化、数据库优化、缓存优化、并发控制等。
"""


def setup_performance_optimization(app: FastAPI, config: dict[str, Any] = None) -> None:
    """
    设置性能优化系统

    包括中间件配置、数据库优化、缓存优化、并发控制等。
    """
    config = config or {}

    # 1. 配置基础性能中间件
    setup_basic_performance_middleware(app)

    # 2. 配置性能监控中间件
    setup_monitoring_middleware(app, config)

    # 3. 配置异步优化
    setup_async_optimization(app)

    # 4. 添加性能端点
    setup_performance_endpoints(app)


def setup_basic_performance_middleware(app: FastAPI) -> None:
    """设置基础性能中间件"""

    # Gzip压缩中间件
    app.add_middleware(
        GZipMiddleware,
        minimum_size=1000,  # 大于1KB的响应启用压缩
    )

    # 性能监控中间件
    app.add_middleware(
        PerformanceMonitoringMiddleware,
        track_memory=True,
        track_concurrency=True,
        sample_rate=1.0,  # 100%采样
    )


def setup_monitoring_middleware(app: FastAPI, config: dict[str, Any]) -> None:
    """设置性能监控中间件"""

    config.get("enable_detailed_logging", False)

    # 添加详细的性能监控中间件
    @app.middleware("http")
    async def performance_middleware(request: Request, call_next):
        start_time = __import__("time").time()

        response = await call_next(request)

        process_time = __import__("time").time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"

        # 记录慢请求
        if process_time > 1.0:  # 超过1秒
            import logging

            logger = logging.getLogger("performance")
            logger.warning(
                f"Slow request: {request.method} {request.url.path} - {process_time:.4f}s"
            )

        return response


def setup_async_optimization(app: FastAPI) -> None:
    """设置异步优化"""

    @app.on_event("startup")
    async def startup_event():
        """启动事件：初始化性能优化组件"""
        try:
            # 初始化性能优化器
            database_url = "sqlite+aiosqlite:///./football_prediction.db"
            await performance_optimizer.initialize(
                database_url=database_url, max_concurrent_requests=1000
            )

            import logging

            logger = logging.getLogger(__name__)
            logger.info("性能优化系统初始化完成")

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"性能优化系统初始化失败: {e}")

    @app.on_event("shutdown")
    async def shutdown_event():
        """关闭事件：清理性能优化组件"""
        await performance_optimizer.shutdown()
        import logging

        logger = logging.getLogger(__name__)
        logger.info("性能优化系统已关闭")


def setup_performance_endpoints(app: FastAPI) -> None:
    """设置性能监控端点"""

    @app.get("/performance/health")
    @monitor_performance("performance_health")
    async def performance_health():
        """性能健康检查"""
        return {
            "status": "healthy",
            "message": "性能优化系统运行正常",
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }

    @app.get("/performance/metrics")
    @monitor_performance("performance_metrics")
    async def get_performance_metrics():
        """获取性能指标"""
        try:
            metrics = await performance_optimizer.get_comprehensive_metrics()
            return {
                "status": "success",
                "metrics": metrics,
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }

    @app.get("/performance/database")
    @monitor_performance("performance_database")
    async def get_database_metrics():
        """获取数据库性能指标"""
        try:
            db_metrics = performance_optimizer.db_optimizer.get_database_metrics()
            return {
                "status": "success",
                "database": db_metrics.__dict__,
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }

    @app.get("/performance/cache")
    @monitor_performance("performance_cache")
    async def get_cache_metrics():
        """获取缓存性能指标"""
        try:
            cache_metrics = performance_optimizer.cache_optimizer.get_cache_metrics()
            return {
                "status": "success",
                "cache": cache_metrics.__dict__,
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }

    @app.get("/performance/concurrency")
    @monitor_performance("performance_concurrency")
    async def get_concurrency_metrics():
        """获取并发性能指标"""
        try:
            concurrency_metrics = (
                performance_optimizer.concurrency_optimizer.get_concurrency_metrics()
            )
            return {
                "status": "success",
                "concurrency": concurrency_metrics,
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }

    @app.post("/performance/cache/warmup")
    @monitor_performance("performance_cache_warmup")
    async def warm_up_cache():
        """缓存预热"""
        try:
            # 示例预热数据
            warm_up_data = {
                "system:status": "online",
                "api:version": "2.0.0",
                "performance:enabled": True,
            }

            await performance_optimizer.cache_optimizer.warm_up_cache(warm_up_data)

            return {
                "status": "success",
                "message": "缓存预热完成",
                "items_count": len(warm_up_data),
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            }


async def get_optimized_db_session():
    """获取优化的数据库会话"""
    async with performance_optimizer.db_optimizer.get_session() as session:
        yield session


PERFORMANCE_CONFIG = {
    "enable_detailed_logging": False,
    "max_concurrent_requests": 1000,
    "database_pool_size": 20,
    "database_max_overflow": 30,
    "cache_default_ttl": 3600,
    "compression_minimum_size": 1000,
    "slow_request_threshold": 1.0,  # 秒
    "slow_query_threshold": 0.1,  # 秒
}
PERFORMANCE_FEATURES = {
    "async_optimization": True,
    "database_connection_pooling": True,
    "caching": True,
    "compression": True,
    "monitoring": True,
    "rate_limiting": False,  # 可选启用
    "request_id_tracking": True,
    "memory_tracking": True,
}


def get_performance_config() -> dict[str, Any]:
    """获取性能配置"""
    return {
        "config": PERFORMANCE_CONFIG,
        "features": PERFORMANCE_FEATURES,
        "optimization_level": "high",
    }


def is_slow_request(process_time: float, threshold: float = None) -> bool:
    """判断是否为慢请求"""
    threshold = threshold or PERFORMANCE_CONFIG["slow_request_threshold"]
    return process_time > threshold


def is_slow_query(query_time: float, threshold: float = None) -> bool:
    """判断是否为慢查询"""
    threshold = threshold or PERFORMANCE_CONFIG["slow_query_threshold"]
    return query_time > threshold


def format_process_time(seconds: float) -> str:
    """格式化处理时间"""
    if seconds < 0.001:
        return f"{seconds * 1000000:.0f}μs"
    elif seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    else:
        return f"{seconds:.2f}s"


def calculate_percentile(values: list[float], percentile: float) -> float:
    """计算百分位数"""
    if not values:
        return 0.0

    sorted_values = sorted(values)
    index = int(len(sorted_values) * percentile / 100)
    return sorted_values[min(index, len(sorted_values) - 1)]


def get_performance_summary(metrics: dict[str, Any]) -> dict[str, Any]:
    """获取性能摘要"""
    system_metrics = metrics.get("system", {})
    db_metrics = metrics.get("database", {})
    cache_metrics = metrics.get("cache", {})

    summary = {"overall_health": "good", "issues": [], "recommendations": []}

    # 检查响应时间
    avg_response_time = system_metrics.get("avg_response_time", 0)
    if avg_response_time > 2.0:
        summary["overall_health"] = "poor"
        summary["issues"].append("响应时间过长")
        summary["recommendations"].append("优化慢端点")
    elif avg_response_time > 1.0:
        summary["overall_health"] = "fair"
        summary["issues"].append("响应时间偏高")
        summary["recommendations"].append("检查性能瓶颈")

    # 检查错误率
    error_rate = system_metrics.get("error_rate", 0)
    if error_rate > 10:
        summary["overall_health"] = "poor"
        summary["issues"].append("错误率过高")
        summary["recommendations"].append("修复应用错误")
    elif error_rate > 5:
        summary["overall_health"] = "fair"
        summary["issues"].append("错误率偏高")
        summary["recommendations"].append("检查错误日志")

    # 检查缓存命中率
    hit_rate = cache_metrics.get("hit_rate", 0)
    if hit_rate < 50:
        summary["issues"].append("缓存命中率偏低")
        summary["recommendations"].append("优化缓存策略")

    # 检查数据库性能
    slow_queries = db_metrics.get("slow_queries", 0)
    if slow_queries > 10:
        summary["issues"].append("存在慢查询")
        summary["recommendations"].append("优化数据库查询")

    return summary
