"""系统管理API路由
System Management API Router.

提供系统管理相关的API端点：
- 系统统计信息
- API版本信息
- 队列状态
- 健康检查

Provides system management API endpoints:
- System statistics
- API version information
- Queue status
- Health checks
"""

from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["系统管理"])


@router.get("/stats")
async def get_system_stats() -> dict[str, Any]:
    """获取系统统计信息
    Get system statistics.

    Returns:
        系统统计信息
    """
    try:
        from src.services.monitoring import get_system_service

        system_service = get_system_service()
        stats = system_service.get_stats()

        return stats

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取系统统计信息失败: {str(e)}"
        ) from e


@router.get("/version")
async def get_api_version() -> dict[str, Any]:
    """获取API版本信息
    Get API version information.

    Returns:
        API版本信息
    """
    try:
        from src.services.version import get_version_service

        version_service = get_version_service()
        version_info = version_service.get_version()

        return version_info

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取API版本信息失败: {str(e)}"
        ) from e


@router.get("/queue")
async def get_queue_status() -> dict[str, Any]:
    """获取队列状态信息
    Get queue status information.

    Returns:
        队列状态信息
    """
    try:
        from src.services.queue import get_queue_service

        queue_service = get_queue_service()
        queue_status = queue_service.get_status()

        return queue_status

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取队列状态信息失败: {str(e)}"
        ) from e


@router.post("/queue/status")
async def get_queue_status_post() -> dict[str, Any]:
    """获取队列状态信息 (POST端点)
    Get queue status information (POST endpoint).

    Returns:
        队列状态信息
    """
    try:
        from src.services.queue import get_queue_service

        queue_service = get_queue_service()
        queue_status = queue_service.get_status()

        return queue_status

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取队列状态信息失败: {str(e)}"
        ) from e


@router.get("/health")
async def system_health_check() -> dict[str, Any]:
    """系统健康检查
    System health check.

    Returns:
        健康状态信息
    """
    try:
        from src.services.monitoring import get_system_service

        system_service = get_system_service()
        health_status = system_service.health_check()

        return health_status

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"系统健康检查失败: {str(e)}"
        ) from e
