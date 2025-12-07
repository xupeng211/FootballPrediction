"""Prometheus Metrics API
P4-1: 增强的Prometheus指标API端点.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Response, Query
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

logger = logging.getLogger(__name__)

# P4-1: 尝试导入增强的监控模块
try:
    from src.monitoring.prometheus_instrumentator import (
        HTTP_REQUESTS_TOTAL,
        HTTP_REQUEST_DURATION_SECONDS,
        PREDICTION_REQUESTS_TOTAL,
        PREDICTION_REQUEST_DURATION_SECONDS,
        ACTIVE_CONNECTIONS,
        generate_latest as enhanced_generate_latest,
    )
    ENHANCED_MONITORING_AVAILABLE = True
    logger.info("✅ 增强监控模块加载成功")
except ImportError as e:
    ENHANCED_MONITORING_AVAILABLE = False
    logger.warning(f"⚠️ 增强监控模块加载失败: {e}")

# 创建Prometheus指标
router = APIRouter(prefix="/metrics", tags=["monitoring"])

# HTTP请求计数器
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status_code"]
)

# HTTP请求响应时间直方图
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# 业务指标计数器
prediction_requests_total = Counter(
    "prediction_requests_total", "Total prediction requests", ["model_type", "status"]
)

# 活跃用户数
active_users = Gauge("active_users", "Number of active users")

# 数据库连接池状态
db_connections_active = Gauge("db_connections_active", "Active database connections")

# Redis连接状态
redis_connections_active = Gauge("redis_connections_active", "Active Redis connections")

# 系统资源使用
system_cpu_usage = Gauge("system_cpu_usage_percent", "System CPU usage percentage")

system_memory_usage = Gauge(
    "system_memory_usage_percent", "System memory usage percentage"
)


@router.get("/")
async def prometheus_metrics(
    format: Optional[str] = Query(None, description="输出格式: prometheus 或 json"),
):
    """P4-1: 增强的Prometheus指标端点."""
    try:
        # 更新系统指标
        await update_system_metrics()

        # 根据格式参数返回不同格式的数据
        if format == "json":
            return await get_metrics_json()
        else:
            # 优先使用增强监控模块
            if ENHANCED_MONITORING_AVAILABLE:
                metrics_data = enhanced_generate_latest()
            else:
                metrics_data = generate_latest()

            return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)

    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return Response(
            content="# Error generating metrics\n" + str(e),
            media_type="text/plain",
            status_code=500
        )


@router.get("/json")
async def prometheus_metrics_json():
    """JSON格式的指标端点（兼容性接口）."""
    try:
        await update_system_metrics()
        return await get_metrics_json()
    except Exception as e:
        logger.error(f"Error generating JSON metrics: {e}")
        return {"error": str(e), "status": "failed"}


async def get_metrics_json():
    """获取JSON格式的指标数据."""
    try:
        import psutil

        # 获取系统指标
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        metrics = {
            "timestamp": logger.handlers[0].formatter.formatTime(
                logger.makeRecord(
                    "metrics", logging.INFO, "", (), "", ""
                )
            ) if logger.handlers else "",
            "system": {
                "cpu_usage_percent": cpu_percent,
                "memory_usage_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_usage_percent": (disk.used / disk.total) * 100,
                "disk_free_gb": disk.free / (1024**3),
            },
            "application": {
                "http_requests_total": HTTP_REQUESTS_TOTAL._value._sum._value if ENHANCED_MONITORING_AVAILABLE else 0,
                "active_connections": {
                    "database": ACTIVE_CONNECTIONS.labels(connection_type="database")._value._value if ENHANCED_MONITORING_AVAILABLE else 0,
                    "redis": ACTIVE_CONNECTIONS.labels(connection_type="redis")._value._value if ENHANCED_MONITORING_AVAILABLE else 0,
                },
            },
            "monitoring": {
                "enhanced_monitoring": ENHANCED_MONITORING_AVAILABLE,
                "prometheus_available": True,
            }
        }

        return metrics

    except Exception as e:
        logger.error(f"Error collecting system metrics: {e}")
        # 返回基本指标
        return {
            "error": str(e),
            "timestamp": "",
            "system": {},
            "application": {},
            "monitoring": {
                "enhanced_monitoring": ENHANCED_MONITORING_AVAILABLE,
                "prometheus_available": False,
            }
        }


async def update_system_metrics():
    """更新系统指标."""
    try:
        import psutil

        # 更新CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        system_cpu_usage.set(cpu_percent)

        # 更新内存使用率
        memory = psutil.virtual_memory()
        system_memory_usage.set(memory.percent)

        logger.debug(
            f"Updated system metrics: CPU={cpu_percent}%, Memory={memory.percent}%"
        )

    except Exception as e:
        logger.error(f"Error updating system metrics: {e}")


def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """记录HTTP请求指标."""
    try:
        http_requests_total.labels(
            method=method, endpoint=endpoint, status_code=str(status_code)
        ).inc()

        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
            duration
        )

    except Exception as e:
        logger.error(f"Error recording HTTP request metrics: {e}")


def record_prediction_request(model_type: str, status: str):
    """记录预测请求指标."""
    try:
        prediction_requests_total.labels(model_type=model_type, status=status).inc()

    except Exception as e:
        logger.error(f"Error recording prediction request metrics: {e}")


def update_active_users(count: int):
    """更新活跃用户数."""
    try:
        active_users.set(count)
    except Exception as e:
        logger.error(f"Error updating active users metric: {e}")


def update_db_connections(count: int):
    """更新数据库连接数."""
    try:
        db_connections_active.set(count)
    except Exception as e:
        logger.error(f"Error updating DB connections metric: {e}")


def update_redis_connections(count: int):
    """更新Redis连接数."""
    try:
        redis_connections_active.set(count)
    except Exception as e:
        logger.error(f"Error updating Redis connections metric: {e}")
