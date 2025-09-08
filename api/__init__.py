"""
API模块

提供API路由和端点
"""

from .health import router as health_router

__all__ = ["health_router"]
