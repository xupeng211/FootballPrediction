"""
API Module
"""

from .data_api import router as data_router
from .health_api import router as health_router
from .predictions_api import router as predictions_router

__all__ = ["data_router", "health_router", "predictions_router"]
