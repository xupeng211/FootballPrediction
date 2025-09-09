"""
应用监控API端点

提供系统性能指标、业务指标监控和运行时统计信息。
"""

import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict

import psutil
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.database.connection import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["监控"])


@router.get(
    "/metrics",
    summary="应用性能指标",
    description="获取系统性能指标、资源使用情况和业务统计",
    response_model=Dict[str, Any],
)
async def get_metrics(db: Session = Depends(get_db_session)) -> Dict[str, Any]:
    """
    获取应用性能指标和系统监控数据

    Returns:
        Dict[str, Any]: 包含系统资源、数据库统计、业务指标的监控数据
    """
    start_time = time.time()

    try:
        # 系统资源监控
        system_metrics = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
                "used": psutil.virtual_memory().used,
            },
            "disk": {
                "total": psutil.disk_usage("/").total,
                "free": psutil.disk_usage("/").free,
                "percent": psutil.disk_usage("/").percent,
            },
            "load_average": os.getloadavg() if hasattr(os, "getloadavg") else None,
        }

        # 数据库连接池监控
        db_metrics = await _get_database_metrics(db)

        # 应用运行时指标
        runtime_metrics = {
            "uptime_seconds": time.time() - start_time,
            "timestamp": datetime.utcnow().isoformat(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "environment": os.getenv("ENVIRONMENT", "development"),
        }

        # 业务指标统计
        business_metrics = await _get_business_metrics(db)

        response_time = round((time.time() - start_time) * 1000, 2)

        return {
            "status": "ok",
            "response_time_ms": response_time,
            "system": system_metrics,
            "database": db_metrics,
            "runtime": runtime_metrics,
            "business": business_metrics,
        }

    except Exception as e:
        logger.error(f"监控指标获取失败: {e}")
        return {
            "status": "error",
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
        }


async def _get_database_metrics(db: Session) -> Dict[str, Any]:
    """获取数据库性能指标"""
    try:
        # 数据库连接测试
        start_time = time.time()
        result = db.execute(text("SELECT 1")).fetchone()
        db_response_time = round((time.time() - start_time) * 1000, 2)

        # 获取数据库统计信息
        stats_queries = {
            "teams_count": "SELECT COUNT(*) FROM teams",
            "matches_count": "SELECT COUNT(*) FROM matches",
            "predictions_count": "SELECT COUNT(*) FROM predictions",
            "active_connections": "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'",
        }

        stats = {}
        for key, query in stats_queries.items():
            try:
                result = db.execute(text(query)).fetchone()
                stats[key] = result[0] if result else 0
            except Exception as e:
                logger.warning(f"获取数据库统计 {key} 失败: {e}")
                stats[key] = None

        return {
            "healthy": True,
            "response_time_ms": db_response_time,
            "statistics": stats,
        }

    except Exception as e:
        logger.error(f"数据库指标获取失败: {e}")
        return {"healthy": False, "error": str(e)}


async def _get_business_metrics(db: Session) -> Dict[str, Any]:
    """获取业务指标统计"""
    try:
        # 最近24小时的业务活动统计
        business_queries = {
            "recent_predictions": """
                SELECT COUNT(*) FROM predictions
                WHERE created_at >= NOW() - INTERVAL '24 hours'
            """,
            "upcoming_matches": """
                SELECT COUNT(*) FROM matches
                WHERE match_date >= NOW() AND match_date <= NOW() + INTERVAL '7 days'
            """,
            "accuracy_rate": """
                SELECT ROUND(
                    AVG(CASE WHEN predicted_result = actual_result THEN 1.0 ELSE 0.0 END) * 100, 2
                ) FROM predictions
                WHERE actual_result IS NOT NULL AND created_at >= NOW() - INTERVAL '30 days'
            """,
        }

        business_stats = {}
        for key, query in business_queries.items():
            try:
                result = db.execute(text(query)).fetchone()
                business_stats[key] = (
                    result[0] if result and result[0] is not None else 0
                )
            except Exception as e:
                logger.warning(f"获取业务指标 {key} 失败: {e}")
                business_stats[key] = None

        return {
            "24h_predictions": business_stats.get("recent_predictions", 0),
            "upcoming_matches_7d": business_stats.get("upcoming_matches", 0),
            "model_accuracy_30d": business_stats.get("accuracy_rate", 0),
            "last_updated": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"业务指标获取失败: {e}")
        return {"error": str(e)}


@router.get(
    "/status",
    summary="服务状态检查",
    description="快速检查所有关键服务的运行状态",
    response_model=Dict[str, Any],
)
async def get_service_status(db: Session = Depends(get_db_session)) -> Dict[str, Any]:
    """
    快速服务状态检查，用于负载均衡器和监控系统

    Returns:
        Dict[str, Any]: 服务状态概要信息
    """
    services = {
        "api": "healthy",  # API服务正在响应
        "database": "unknown",
        "cache": "unknown",
    }

    # 检查数据库连接
    try:
        db.execute(text("SELECT 1")).fetchone()
        services["database"] = "healthy"
    except Exception:
        services["database"] = "unhealthy"

    # 检查Redis缓存（如果配置了）
    try:
        import redis

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        r.ping()
        services["cache"] = "healthy"
    except Exception:
        services["cache"] = "unhealthy"

    overall_status = (
        "healthy"
        if all(status == "healthy" for status in services.values())
        else "degraded"
    )

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "services": services,
    }
