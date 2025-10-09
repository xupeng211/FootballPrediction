"""
健康检查模块
Health Check Module
"""

# 创建一个默认的router
from fastapi import APIRouter

# 临时创建一个基本的router以避免导入错误
router = APIRouter()


@router.get("/health")
async def health_check():
    """基本健康检查"""
    return {"status": "healthy"}


# 尝试从其他文件导入
try:
    from .health_checker import HealthChecker
except ImportError:
    HealthChecker = None

__all__ = ["router", "HealthChecker"]
