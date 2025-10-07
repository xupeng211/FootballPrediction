"""
API模块

提供API路由和端点
"""

from .health import router as health_router
from .predictions_api import router as predictions_router
from .data_api import router as data_router

__all__ = ["health_router", "predictions_router", "data_router"]
