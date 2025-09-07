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

from src.database.connection import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["健康检查"])


@router.get(
    "/health",
    summary="系统健康检查",
    description="检查API、数据库、缓存等服务状态",
    response_model=Dict[str, Any],
)
async def health_check(db: Session = Depends(get_db_session)):
    """
    系统健康检查端点

    Returns:
        Dict[str, Any]: 系统健康状态信息
    """
    start_time = time.time()
    health_status = {
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
    "/health/live", summary="存活性检查", description="简单的存活性检查，用于Kubernetes liveness probe"
)
async def liveness_check():
    """
    存活性检查 - 仅检查API是否响应

    Returns:
        Dict[str, str]: 简单的存活状态
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/ready", summary="就绪性检查", description="检查服务是否准备好接收流量")
async def readiness_check(db: Session = Depends(get_db_session)):
    """
    就绪性检查 - 检查服务是否准备好处理请求

    Returns:
        Dict[str, str]: 就绪状态
    """
    try:
        # 检查数据库连接
        db.execute(text("SELECT 1"))

        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}

    except Exception as e:
        logger.error(f"就绪性检查失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


async def _check_database(db: Session) -> Dict[str, Any]:
    """检查数据库连接"""
    try:
        start_time = time.time()

        # 执行简单查询
        result = db.execute(text("SELECT 1 as test"))
        row = result.fetchone()

        response_time = round((time.time() - start_time) * 1000, 2)

        if row and row.test == 1:
            return {
                "healthy": True,
                "response_time_ms": response_time,
                "message": "数据库连接正常",
            }
        else:
            return {
                "healthy": False,
                "response_time_ms": response_time,
                "message": "数据库查询结果异常",
            }

    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return {"healthy": False, "error": str(e), "message": "数据库连接失败"}


async def _check_redis() -> Dict[str, Any]:
    """检查Redis连接"""
    try:
        # 这里暂时返回健康状态，实际实现需要Redis客户端
        # TODO: 实现Redis连接检查
        return {"healthy": True, "message": "Redis连接正常（待实现）"}

    except Exception as e:
        logger.error(f"Redis健康检查失败: {e}")
        return {"healthy": False, "error": str(e), "message": "Redis连接失败"}


async def _check_filesystem() -> Dict[str, Any]:
    """检查文件系统"""
    try:
        import os
        import shutil

        # 检查日志目录是否可写
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 检查磁盘空间
        disk_usage = shutil.disk_usage(".")
        free_space_gb = disk_usage.free / (1024**3)

        if free_space_gb < 1.0:  # 少于1GB空间时警告
            return {
                "healthy": False,
                "free_space_gb": round(free_space_gb, 2),
                "message": f"磁盘空间不足: {free_space_gb:.2f}GB",
            }

        return {
            "healthy": True,
            "free_space_gb": round(free_space_gb, 2),
            "message": "文件系统正常",
        }

    except Exception as e:
        logger.error(f"文件系统健康检查失败: {e}")
        return {"healthy": False, "error": str(e), "message": "文件系统检查失败"}
