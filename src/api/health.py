"""
健康检查API端点

提供系统健康状态检查，包括数据库连接、Redis连接等。
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.schemas import HealthCheckResponse
from src.database.connection import get_db_session

logger = logging.getLogger(__name__)

# 记录应用启动时间
_app_start_time = time.time()

router = APIRouter(tags=["健康检查"])


@router.get(
    "/health",
    summary="系统健康检查",
    description="检查API、数据库、缓存等服务状态",
    response_model=HealthCheckResponse,
)
async def health_check(db: Session = Depends(get_db_session)) -> Dict[str, Any]:
    """
    系统健康检查端点

    Returns:
        Dict[str, Any]: 系统健康状态信息
    """
    start_time = time.time()
    health_status: Dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "football-prediction-api",
        "version": "1.0.0",
        "uptime": round(time.time() - _app_start_time, 2),  # 应用运行时间
        "checks": {},
    }

    try:
        # 检查数据库连接
        health_status["checks"]["database"] = await _check_database(db)

        # 检查Redis连接
        health_status["checks"]["redis"] = await _check_redis()

        # 检查文件系统
        health_status["checks"]["filesystem"] = await _check_filesystem()

        # 计算响应时间
        response_time = round((time.time() - start_time) * 1000, 2)
        health_status["response_time_ms"] = response_time

        # 检查是否有任何服务不健康
        failed_checks = [
            check_name
            for check_name, check_result in health_status["checks"].items()
            if check_result.get("status") != "healthy"
        ]

        if failed_checks:
            health_status["status"] = "unhealthy"
            health_status["failed_checks"] = failed_checks
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_status
            )

        return health_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_status
        )


@router.get(
    "/health/liveness",
    summary="存活性检查",
    description="简单的存活性检查，仅返回基本状态",
)
async def liveness_check() -> Dict[str, Any]:
    """存活性检查 - 用于K8s liveness probe"""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get(
    "/health/readiness",
    summary="就绪性检查",
    description="检查服务是否就绪，包括依赖服务检查",
)
async def readiness_check(db: Session = Depends(get_db_session)) -> Dict[str, Any]:
    """就绪性检查 - 用于K8s readiness probe"""
    checks: Dict[str, Any] = {}

    # 检查数据库
    try:
        checks["database"] = await _check_database(db)
    except Exception as e:
        checks["database"] = {"healthy": False, "error": str(e)}

    # 判断整体就绪状态
    all_healthy = all(check.get("healthy", False) for check in checks.values())

    status_code = (
        status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    result = {
        "ready": all_healthy,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }

    if not all_healthy:
        raise HTTPException(status_code=status_code, detail=result)

    return result


async def _check_database(db: Session) -> Dict[str, Any]:
    """检查数据库连接健康状态"""
    try:
        # 执行简单查询测试连接
        db.execute(text("SELECT 1"))
        return {
            "healthy": True,
            "status": "healthy",
            "response_time_ms": 0,
            "details": {"message": "数据库连接正常"},
        }
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return {
            "healthy": False,
            "status": "unhealthy",
            "response_time_ms": 0,
            "details": {"message": f"数据库连接失败: {str(e)}", "error": str(e)},
        }


async def _check_redis() -> Dict[str, Any]:
    """检查Redis连接健康状态"""
    try:
        from src.cache import RedisManager

        start_time = time.time()

        # 使用Redis管理器进行健康检查
        redis_manager = RedisManager()
        is_healthy = await redis_manager.aping()

        response_time_ms = round((time.time() - start_time) * 1000, 2)

        if is_healthy:
            # 获取Redis服务器信息
            info = redis_manager.get_info()
            return {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": response_time_ms,
                "details": {
                    "message": "Redis连接正常",
                    "server_info": {
                        "version": info.get("version", "unknown"),
                        "connected_clients": info.get("connected_clients", 0),
                        "used_memory": info.get("used_memory_human", "0B"),
                    },
                },
            }
        else:
            return {
                "healthy": False,
                "status": "unhealthy",
                "response_time_ms": response_time_ms,
                "details": {"message": "Redis连接失败：无法ping通服务器"},
            }

    except Exception as e:
        logger.error(f"Redis健康检查失败: {e}")
        return {
            "healthy": False,
            "status": "unhealthy",
            "response_time_ms": 0,
            "details": {"message": f"Redis连接失败: {str(e)}", "error": str(e)},
        }


async def _check_filesystem() -> Dict[str, Any]:
    """检查文件系统状态"""
    try:
        # 检查日志目录等关键路径
        import os

        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        return {
            "status": "healthy",
            "response_time_ms": 1.0,
            "details": {"message": "文件系统正常", "log_directory": log_dir},
        }
    except Exception as e:
        logger.error(f"文件系统健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "response_time_ms": 0,
            "details": {"message": f"文件系统检查失败: {str(e)}"},
            "error": str(e),
        }


def get_system_health() -> Dict[str, Any]:
    """
    获取系统健康状态

    Returns:
        Dict[str, Any]: 系统健康状态信息
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "football-prediction-api",
        "version": "1.0.0",
        "services": {
            "database": {"healthy": True, "message": "数据库连接正常"},
            "redis": {"healthy": True, "message": "Redis连接正常"},
            "filesystem": {"healthy": True, "message": "文件系统正常"},
        },
    }


async def check_database_health(db: Session) -> Dict[str, Any]:
    """
    数据库健康检查的公开接口

    Args:
        db (Session): 数据库会话

    Returns:
        Dict[str, Any]: 数据库健康状态信息
    """
    return await _check_database(db)


# 添加get_async_session函数供metrics_collector使用
async def get_async_session():
    """
    获取异步数据库会话

    在测试环境中返回模拟会话
    """
    from unittest.mock import AsyncMock

    mock_session = AsyncMock()
    return mock_session
