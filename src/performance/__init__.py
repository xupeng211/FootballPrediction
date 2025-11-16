"""性能监控模块
Performance Monitoring Module.

提供全面的性能监控功能:
- 性能分析器
- 监控中间件
- 性能分析工具
- API端点
"""

from .analyzer import PerformanceAnalyzer, PerformanceInsight, PerformanceTrend
from .api import router as performance_router

# 导入性能监控组件
try:
    from .monitoring import (
        BackgroundTaskPerformanceMonitor,
        CachePerformanceMiddleware,
        DatabasePerformanceMiddleware,
        PerformanceMonitoringMiddleware,
    )
    from .profiler import (
        APIEndpointProfiler,
        DatabaseQueryProfiler,
    )
except ImportError:
    BackgroundTaskPerformanceMonitor = None
    CachePerformanceMiddleware = None
    DatabasePerformanceMiddleware = None
    PerformanceMonitoringMiddleware = None
    APIEndpointProfiler = None
    DatabaseQueryProfiler = None

__all__ = [
    # 分析器
    "PerformanceAnalyzer",
    "PerformanceInsight",
    "PerformanceTrend",
    # 路由
    "performance_router",
    # 中间件
    "BackgroundTaskPerformanceMonitor",
    "CachePerformanceMiddleware",
    "DatabasePerformanceMiddleware",
    "PerformanceMonitoringMiddleware",
    # 性能分析器
    "APIEndpointProfiler",
    "DatabaseQueryProfiler",
]
