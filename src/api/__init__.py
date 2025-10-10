"""
API Module
"""

# 导入各个模块的路由器
from .data_router import router as data_router
from .health import router as health_router
from .predictions import router as predictions_router
from .events import router as events_router
from .observers import router as observers_router
from .repositories import router as repositories_router

__all__ = [
    "data_router",
    "health_router",
    "predictions_router",
    "events_router",
    "observers_router",
    "repositories_router",
]
