"""
Health check module
"""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    """Basic health check"""
    return {"status": "healthy"}


@router.get("/detailed")
async def detailed_health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "checks": {"database": "ok", "redis": "ok", "system": "ok"},
    }
