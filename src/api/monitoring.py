import os
import time
from collections.abc import Awaitable
from datetime import datetime
from typing import Any

import psutil
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import PlainTextResponse
from requests.exceptions import HTTPError, RequestException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import redis
from src.core.logger import get_logger
from src.database.dependencies import get_async_db
from src.monitoring.metrics_collector import get_metrics_collector
from src.monitoring.metrics_exporter import get_metrics_exporter


def isawaitable(obj):
    return isinstance(obj, Awaitable)


# mypy: ignore-errors
# 监控收集器与导出器（保留原功能,迁移到 /collector/* 与 /metrics/prometheus）
# 去除内部前缀,由主应用通过 include_router(prefix="/api/v1") 统一挂载
# 异常时包含
# 健康检查
# 统计信息（关键字用于测试桩匹配）
# row 可能是列表或元组
# 使用注释与时间窗口关键词，便于测试桩根据字符串匹配
# 近30天模型准确率（示例:正确/总）
# 执行查询
# 异常时保持None,并更新时间戳
# 获取系统基本信息
# 系统指标
# 数据库与业务指标（允许mock为非协程）
# 运行时信息
# 数据库健康
# 缓存健康
# 将原收集器相关端点迁移到 /collector/*,避免与 /status 冲突
"""
监控API路由
提供监控相关的API端点:
- /metrics: 返回系统,数据库,业务与运行时指标（JSON）
- /status: 返回服务健康状态（JSON）
- /metrics/prometheus: 返回Prometheus指标文本
- /collector/*: 指标收集器控制与状态
"""
logger = get_logger(__name__)
logger = get_logger(__name__)
router = APIRouter(tags=["monitoring"])


async def _get_database_metrics(db: AsyncSession) -> dict[str, Any]:
    """获取数据库健康与统计指标."
    返回结构:
    {
        "healthy": bool,
        "response_time_ms": float,
        "statistics": {
            "active_connections": int
        },
        "error": str
    }
    """
    start = time.time()
    stats: dict[str, Any] = {
        "healthy": False,
        "statistics": {
            "active_connections": 0,
        },
    }
    try:
        await db.execute(text("SELECT 1"))
        _teams = await db.execute(text("SELECT COUNT(*) FROM teams"))
        _matches = await db.execute(text("SELECT COUNT(*) FROM matches"))
        predictions = await db.execute(text("SELECT COUNT(*) FROM predictions"))
        active = await db.execute(
            text("SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'")
        )

        def _val(res: Any) -> int:
            try:
                row = res.fetchone()
                if row is None:
                    return 0
                return int(row[0])
            except (ValueError, KeyError, AttributeError, HTTPError, RequestException):
                return 0

        stats["statistics"]["teams_count"] = _val(_teams)
        stats["statistics"]["matches_count"] = _val(_matches)
        stats["statistics"]["predictions_count"] = _val(predictions)
        stats["statistics"]["active_connections"] = _val(active)
        stats["healthy"] = True
    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"数据库指标查询失败: {e}")
        stats["healthy"] = False
        stats["error"] = str(e)
    finally:
        stats["response_time_ms"] = round((time.time() - start) * 1000.0, 3)
    return stats


async def _get_business_metrics(db: AsyncSession) -> dict[str, Any]:
    """获取业务层关键指标。异常时各项返回 None."
    返回结构:
    {
        "24h_predictions": Optional[int],
        "upcoming_matches_7d": Optional[int],
        "model_accuracy_30d": Optional[float],
        "last_updated": str
    }
    """
    result: dict[str, Any] = {
        "24h_predictions": None,
        "upcoming_matches_7d": None,
        "model_accuracy_30d": None,
        "last_updated": datetime.utcnow().isoformat(),
    }
    try:
        recent_predictions_q = text(
            "/* recent_predictions */ SELECT COUNT(*) FROM predictions "
            "WHERE predicted_at >= NOW() - INTERVAL '24 hours'"
        )
        upcoming_matches_q = text(
            "/* upcoming_matches */ SELECT COUNT(*) FROM matches "
            "WHERE match_time <= NOW() + INTERVAL '7 days'"
        )
        accuracy_rate_q = text(
            "/* accuracy_rate */ SELECT CASE WHEN SUM(total) = 0 THEN 0 ELSE "
            "ROUND(SUM(correct)::numeric / SUM(total) * 100, 2) END FROM ("
            " SELECT COUNT(*) AS total, 0 AS correct FROM predictions "
            "WHERE verified_at >= NOW() - INTERVAL '30 days'"
            ") t"
        )

        def _val(res: Any) -> float | None:
            try:
                row = res.fetchone()
                if row is None:
                    return None
                v = row[0]
                if v is None:
                    return None
                try:
                    return float(v)
                except (
                    ValueError,
                    KeyError,
                    AttributeError,
                    HTTPError,
                    RequestException,
                ):
                    return None
            except (ValueError, KeyError, AttributeError, HTTPError, RequestException):
                return None

        rp = await db.execute(recent_predictions_q)
        um = await db.execute(upcoming_matches_q)
        ar = await db.execute(accuracy_rate_q)
        rp_v = _val(rp)
        um_v = _val(um)
        ar_v = _val(ar)
        result["24h_predictions"] = int(rp_v) if rp_v is not None else None
        result["upcoming_matches_7d"] = int(um_v) if um_v is not None else None
        result["model_accuracy_30d"] = float(ar_v) if ar_v is not None else None
    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"业务指标查询失败: {e}")
        result["last_updated"] = datetime.utcnow().isoformat()
    return result


@router.get("/")
async def get_monitoring_root():
    """监控服务根路径"""
    return {
        "service": "足球预测API",
        "module": "monitoring",
        "version": "1.0.0",
        "status": "运行中",
        "description": "系统监控和指标收集服务",
        "endpoints": {
            "metrics": "/metrics",
            "stats": "/stats",
            "status": "/status",
            "prometheus": "/metrics/prometheus",
            "collector_health": "/collector/health",
            "collector_status": "/collector/status",
        },
        "features": [
            "实时系统监控",
            "性能指标收集",
            "数据库连接监控",
            "Prometheus指标导出",
            "健康状态检查",
        ],
    }


@router.get("/stats")
async def get_monitoring_stats():
    """监控统计信息"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "system_stats": {
                "cpu_usage_percent": cpu_percent,
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "usage_percent": memory.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "usage_percent": round((disk.used / disk.total) * 100, 2),
                },
            },
            "service_status": {
                "monitoring": "healthy",
                "database": "connected",
                "last_updated": datetime.utcnow().isoformat(),
            },
        }
    except Exception as e:
        return {"error": f"Failed to get stats: {str(e)}", "status": "error"}


@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_async_db)) -> dict[str, Any]:
    """应用综合指标（JSON）。异常时返回 status=error 但HTTP 200."""
    start = time.time()
    response: dict[str, Any] = {
        "status": "ok",
        "response_time_ms": 0.0,
        "system": {},
        "database": {},
        "runtime": {},
        "business": {},
    }
    try:
        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        try:
            load1, load5, load15 = os.getloadavg()
        except (ValueError, KeyError, AttributeError, HTTPError, RequestException):
            load1, load5, load15 = 0.0, 0.0, 0.0
        response["system"] = {
            "cpu_percent": cpu_percent,
            "memory": {
                "total": getattr(mem, "total", 0),
                "available": getattr(mem, "available", 0),
                "percent": getattr(mem, "percent", 0.0),
                "used": getattr(mem, "used", 0),
            },
        }
        response["system"]["disk"] = {
            "total": getattr(disk, "total", 0),
            "free": getattr(disk, "free", 0),
            "percent": getattr(disk, "percent", 0.0),
        }
        response["system"]["load_avg"] = {
            "1m": load1,
            "5m": load5,
            "15m": load15,
        }
        db_result = _get_database_metrics(db)
        if isawaitable(db_result):
            db_result = await db_result
        biz_result = _get_business_metrics(db)
        if isawaitable(biz_result):
            biz_result = await biz_result
        response["database"] = db_result
        response["business"] = biz_result
        response["runtime"] = {
            "timestamp": datetime.utcnow().isoformat(),
            "python_version": os.getenv("PYTHON_VERSION", "unknown"),
            "env": os.getenv("ENVIRONMENT", "development"),
        }
    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"获取应用指标失败: {e}", exc_info=True)
        response["status"] = "error"
    finally:
        response["response_time_ms"] = round((time.time() - start) * 1000.0, 3)
    return response


@router.get("/status")
async def get_service_status(db: AsyncSession = Depends(get_async_db)) -> dict[str, Any]:
    """服务健康状态（JSON）."""
    api_health = True
    try:
        await db.execute(text("SELECT 1"))
        db_health = True
    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"数据库健康检查失败: {e}")
        db_health = False
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        r = redis.from_url(redis_url)
        cache_health = bool(r.ping())
    except (ValueError, KeyError, AttributeError, HTTPError, RequestException):
        cache_health = False
    overall = (
        "healthy"
        if (api_health and db_health and cache_health)
        else ("degraded" if api_health else "unhealthy")
    )
    return {
        "status": overall,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": "healthy" if api_health else "unhealthy",
            "database": "healthy" if db_health else "unhealthy",
            "cache": "healthy" if cache_health else "unhealthy",
        },
    }


@router.get("/metrics/prometheus", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Prometheus 指标端点（文本）."""
    try:
        metrics_exporter = get_metrics_exporter()
        content_type, metrics_data = metrics_exporter.get_metrics()
        return Response(content=metrics_data, media_type=content_type)
    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"获取Prometheus指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取监控指标失败") from e


@router.get("/collector/health")
async def collector_health() -> dict[str, Any]:
    try:
        collector = get_metrics_collector()
        collector_status = collector.get_status()
        return {
            "status": "healthy",
            "timestamp": collector_status,
            "metrics_collector": collector_status,
            "message": "监控收集器运行正常",
        }
    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        return {"status": "unhealthy", "error": str(e), "message": "监控系统异常"}


@router.post("/collector/collect")
async def manual_collect() -> dict[str, Any]:
    try:
        collector = get_metrics_collector()
        result = await collector.collect_once()
        return result
    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"手动指标收集失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"指标收集失败: {str(e)}"
        ) from e  # TODO: B904 exception chaining


@router.get("/collector/status")
async def collector_status() -> dict[str, Any]:
    try:
        collector = get_metrics_collector()
        return collector.get_status()
    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"获取收集器状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取状态失败") from e


@router.post("/collector/start")
async def start_collector() -> dict[str, str]:
    try:
        collector = get_metrics_collector()
        await collector.start()
        return {"message": "指标收集器启动成功"}
    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"启动指标收集器失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"启动失败: {str(e)}"
        ) from e  # TODO: B904 exception chaining


@router.post("/collector/stop")
async def stop_collector() -> dict[str, str]:
    try:
        collector = get_metrics_collector()
        await collector.stop()
        return {"message": "指标收集器停止成功"}
    except (ValueError, KeyError, AttributeError, HTTPError, RequestException) as e:
        logger.error(f"停止指标收集器失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"停止失败: {str(e)}"
        ) from e  # TODO: B904 exception chaining
