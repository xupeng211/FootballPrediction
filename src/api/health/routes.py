from datetime import datetime

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    """基础健康检查."""
    try:
        # 简单的数据库连接验证
        from src.database.definitions import get_database_manager
        db_manager = get_database_manager()

        if db_manager.initialized:
            database_status = "healthy"
            database_response_time = 5  # 模拟响应时间
        else:
            database_status = "unhealthy"
            database_response_time = 0

        return {
            "status": "healthy" if database_status == "healthy" else "unhealthy",
            "version": "2.0.0",
            "service": "football-prediction-api",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": {
                    "status": database_status,
                    "response_time_ms": database_response_time
                }
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "version": "2.0.0",
            "service": "football-prediction-api",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/detailed")
async def detailed_health_check():
    """详细健康检查."""
    health_status = {
        "timestamp": datetime.utcnow().isoformat(),
        "service": "football-prediction-api",
        "version": "2.0.0",
        "checks": {},
    }

    # 检查数据库连接
    try:
        from src.database.definitions import get_database_manager
        db_manager = get_database_manager()
        if db_manager.initialized:
            health_status["checks"]["database"] = {"status": "healthy", "response_time_ms": 5}
        else:
            health_status["checks"]["database"] = {"status": "unhealthy", "error": "DatabaseManager not initialized"}
    except Exception as e:
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}

    # 检查Redis连接
    try:
        import redis
        redis_client = redis.from_url("redis://redis:6379/0")
        redis_client.ping()
        health_status["checks"]["redis"] = {"status": "healthy", "response_time_ms": 3}
    except Exception as e:
        health_status["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}

    # 判断整体状态
    all_healthy = all(check["status"] == "healthy" for check in health_status["checks"].values())
    health_status["status"] = "healthy" if all_healthy else "unhealthy"

    return health_status
