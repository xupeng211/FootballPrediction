"""
API性能优化模块
API Performance Optimization Module

提供统一的API性能优化功能集成。
"""

from .enhanced_performance_middleware import (
    EnhancedPerformanceMiddleware,
    create_performance_middleware,
    get_performance_middleware
)
from .smart_cache_system import (
    SmartCacheManager,
    CacheMiddleware,
    initialize_cache_system,
    get_cache_manager,
    get_cache_middleware
)
from .api_performance_optimizer import router as optimization_router

__all__ = [
    "EnhancedPerformanceMiddleware",
    "create_performance_middleware",
    "get_performance_middleware",
    "SmartCacheManager",
    "CacheMiddleware",
    "initialize_cache_system",
    "get_cache_manager",
    "get_cache_middleware",
    "optimization_router"
]