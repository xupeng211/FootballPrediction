"""
API Endpoints Package - API端点定义

包含所有FastAPI路由端点的定义。
"""

from .prediction import router as prediction_router

__all__ = [
    "prediction_router"
]