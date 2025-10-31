"""
Prometheus Metrics API
Prometheus指标API端点
"""

import logging
import time
from typing import Dict, Any

from fastapi import APIRouter, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger(__name__)

# 创建Prometheus指标
router = APIRouter(prefix="/metrics", tags=["monitoring"])

# HTTP请求计数器
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

# HTTP请求响应时间直方图
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# 业务指标计数器
prediction_requests_total = Counter(
    'prediction_requests_total',
    'Total prediction requests',
    ['model_type', 'status']
)

# 活跃用户数
active_users = Gauge(
    'active_users',
    'Number of active users'
)

# 数据库连接池状态
db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)

# Redis连接状态
redis_connections_active = Gauge(
    'redis_connections_active',
    'Active Redis connections'
)

# 系统资源使用
system_cpu_usage = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage'
)

system_memory_usage = Gauge(
    'system_memory_usage_percent',
    'System memory usage percentage'
)


@router.get("/")
async def prometheus_metrics():
    """
    Prometheus指标端点
    """
    try:
        # 更新系统指标
        await update_system_metrics()

        # 返回Prometheus格式的指标
        metrics_data = generate_latest()
        return Response(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return Response(
            content="# Error generating metrics",
            media_type="text/plain"
        )


async def update_system_metrics():
    """更新系统指标"""
    try:
        import psutil

        # 更新CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        system_cpu_usage.set(cpu_percent)

        # 更新内存使用率
        memory = psutil.virtual_memory()
        system_memory_usage.set(memory.percent)

        logger.debug(f"Updated system metrics: CPU={cpu_percent}%, Memory={memory.percent}%")

    except Exception as e:
        logger.error(f"Error updating system metrics: {e}")


def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """记录HTTP请求指标"""
    try:
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()

        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

    except Exception as e:
        logger.error(f"Error recording HTTP request metrics: {e}")


def record_prediction_request(model_type: str, status: str):
    """记录预测请求指标"""
    try:
        prediction_requests_total.labels(
            model_type=model_type,
            status=status
        ).inc()

    except Exception as e:
        logger.error(f"Error recording prediction request metrics: {e}")


def update_active_users(count: int):
    """更新活跃用户数"""
    try:
        active_users.set(count)
    except Exception as e:
        logger.error(f"Error updating active users metric: {e}")


def update_db_connections(count: int):
    """更新数据库连接数"""
    try:
        db_connections_active.set(count)
    except Exception as e:
        logger.error(f"Error updating DB connections metric: {e}")


def update_redis_connections(count: int):
    """更新Redis连接数"""
    try:
        redis_connections_active.set(count)
    except Exception as e:
        logger.error(f"Error updating Redis connections metric: {e}")