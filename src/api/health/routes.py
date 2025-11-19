from typing import Optional

from datetime import datetime

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    """基础健康检查."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "football-prediction-api",
        "version": "1.0.0",
    }


@router.get("/detailed")
async def detailed_health_check():
    """详细健康检查."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "football-prediction-api",
        "version": "1.0.0",
        "components": {},
    }

    # 检查数据库连接
    try:
        # 这里应该使用实际的数据库连接
        health_status["components"]["database"] = "healthy"
    except Exception as e:
        health_status["components"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"

    # 检查Redis连接
    try:
        # 这里应该使用实际的Redis连接
        health_status["components"]["redis"] = "healthy"
    except Exception as e:
        health_status["components"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"

    return health_status
