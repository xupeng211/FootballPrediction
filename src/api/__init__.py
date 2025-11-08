from .data_router import router as data_router
from .events import router as events_router
from .health import router as health_router
from .observers import router as observers_router
from .predictions import router as predictions_router
from .repositories import router as repositories_router

"""
API Module
"""

__all__ = [
    "data_router",
    "health_router",
    "predictions_router",
    "events_router",
    "observers_router",
    "repositories_router",
]
