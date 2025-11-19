#!/usr/bin/env python3
"""简化的健康检查和指标服务器
用于在主应用修复期间提供基础的监控功能.
"""

import logging
import time

import uvicorn
from fastapi import FastAPI, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(title="Football Prediction Health Server", version="1.0.0")

# Prometheus指标
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

prediction_requests_total = Counter(
    'prediction_requests_total',
    'Total prediction requests',
    ['model_type', 'status']
)

active_users = Gauge(
    'active_users',
    'Number of active users'
)

system_cpu_usage = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage'
)

system_memory_usage = Gauge(
    'system_memory_usage_percent',
    'System memory usage percentage'
)

@app.get("/")
async def root():
    """根端点."""
    return {"status": "healthy", "service": "football-prediction-health", "version": "1.0.0"}

@app.get("/health")
async def health():
    """健康检查."""
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/metrics")
async def metrics():
    """Prometheus指标端点."""
    try:
        # 更新系统指标
        await update_system_metrics()

        # 生成指标数据
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
    """更新系统指标."""
    try:
        import psutil

        # 更新CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        system_cpu_usage.set(cpu_percent)

        # 更新内存使用率
        memory = psutil.virtual_memory()
        system_memory_usage.set(memory.percent)

        # 更新活跃用户数（模拟数据）
        active_users.set(42)  # 模拟42个活跃用户

        logger.info(f"Updated metrics: CPU={cpu_percent}%, Memory={memory.percent}%")

    except Exception as e:
        logger.error(f"Error updating system metrics: {e}")

@app.middleware("http")
async def metrics_middleware(request, call_next):
    """指标收集中间件."""
    start_time = time.time()

    response = await call_next(request)

    # 记录请求指标
    duration = time.time() - start_time
    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=str(response.status_code)
    ).inc()

    http_request_duration_seconds.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response

if __name__ == "__main__":
    logger.info("Starting Football Prediction Health Server...")
    logger.info("Available endpoints:")
    logger.info("  GET /      - Root endpoint")
    logger.info("  GET /health - Health check")
    logger.info("  GET /metrics - Prometheus metrics")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
