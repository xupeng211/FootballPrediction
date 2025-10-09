"""
API Module
"""

from .data_api import router as data_router
from .health_api import router as health_router
from .predictions_api import router as predictions_router
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
