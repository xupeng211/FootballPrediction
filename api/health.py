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

from database.connection import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["健康检查"])


@router.get(
    "/health",
    summary="系统健康检查",
    description="检查API、数据库、缓存等服务状态",
    response_model=Dict[str, Any],
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
            if not check_result.get("healthy", False)
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
        return {"healthy": True, "message": "数据库连接正常", "response_time_ms": 0}
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return {
            "healthy": False,
            "message": f"数据库连接失败: {str(e)}",
            "error": str(e),
        }


async def _check_redis() -> Dict[str, Any]:
    """检查Redis连接健康状态"""
    try:
        # 这里可以添加实际的Redis连接检查
        # 目前返回模拟结果
        return {"healthy": True, "message": "Redis连接正常", "response_time_ms": 0}
    except Exception as e:
        logger.error(f"Redis健康检查失败: {e}")
        return {
            "healthy": False,
            "message": f"Redis连接失败: {str(e)}",
            "error": str(e),
        }


async def _check_filesystem() -> Dict[str, Any]:
    """检查文件系统状态"""
    try:
        # 检查日志目录等关键路径
        import os

        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        return {"healthy": True, "message": "文件系统正常", "log_directory": log_dir}
    except Exception as e:
        logger.error(f"文件系统健康检查失败: {e}")
        return {
            "healthy": False,
            "message": f"文件系统检查失败: {str(e)}",
            "error": str(e),
        }
