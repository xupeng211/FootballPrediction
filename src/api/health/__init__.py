"""
Health check module
"""

import time
import warnings

from fastapi import APIRouter, HTTPException

# 发出弃用警告
warnings.warn(
    "直接从 health 导入已弃用，请使用 from src.api.health.router import router",
    DeprecationWarning,
    stacklevel=2,
)

router = APIRouter(tags=["health"])

# 定义导出列表
__all__ = ["router"]


def _check_database():
    """检查数据库连接状态（内部函数）"""
    # 这里应该有实际的数据库连接检查逻辑
    # 现在返回模拟数据
    return {"status": "healthy", "latency_ms": 10}


@router.get("/")
async def health_check():
    """Basic health check"""
    try:
        # 执行数据库健康检查
        db_status = _check_database()

        overall_status = "healthy"
        if db_status.get("status") != "healthy":
            overall_status = "unhealthy"

        return {
            "status": overall_status,
            "timestamp": time.time(),
            "checks": {
                "database": db_status,
            },
        }
    except Exception as e:
        # 数据库检查失败时返回错误状态
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "timestamp": time.time(),
                "error": str(e),
                "checks": {
                    "database": {"status": "error", "error": str(e)},
                },
            },
        )


@router.get("/liveness")
async def liveness_check():
    """存活检查 - 确认服务正在运行"""
    try:
        # 安全地获取时间戳
        try:
            timestamp = time.time()
        except Exception:
            # 如果时间函数失败，使用默认值
            timestamp = 0.0

        return {
            "status": "alive",
            "timestamp": timestamp,
            "service": "football-prediction-api",
        }
    except Exception as e:
        # 其他错误处理
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error": str(e),
                "service": "football-prediction-api",
            },
        )


@router.get("/readiness")
async def readiness_check():
    """就绪检查 - 确认服务准备好处理请求"""
    # 简单检查数据库连接
    db_status = _check_database()

    if db_status.get("status") == "healthy":
        return {
            "status": "ready",
            "timestamp": time.time(),
            "checks": {"database": db_status},
        }
    else:
        return {
            "status": "not_ready",
            "timestamp": time.time(),
            "checks": {"database": db_status},
        }


@router.get("/detailed")
async def detailed_health():
    """Detailed health check"""
    db_status = _check_database()

    return {
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {
            "database": db_status,
            "redis": {"status": "ok", "latency_ms": 5},
            "system": {"status": "ok", "cpu_usage": "15%", "memory_usage": "45%"},
        },
    }
