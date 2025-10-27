"""
性能监控模块
Performance Monitoring Module

提供全面的性能监控功能：
- 性能分析器
- 监控中间件
- 性能分析工具
- API端点
"""

from .analyzer import PerformanceAnalyzer, PerformanceInsight, PerformanceTrend
from .api import router as performance_router
from .middleware import (BackgroundTaskPerformanceMonitor,
                         CachePerformanceMiddleware,
                         DatabasePerformanceMiddleware,
                         PerformanceMonitoringMiddleware)
from .profiler import (APIEndpointProfiler, DatabaseQueryProfiler,
                       MemoryProfiler, PerformanceProfiler,
                       get_performance_report, get_profiler, profile_function,
                       profile_method, start_profiling, stop_profiling)

__all__ = [
    # Profiler
    "PerformanceProfiler",
    "get_profiler",
    "profile_function",
    "profile_method",
    "DatabaseQueryProfiler",
    "APIEndpointProfiler",
    "MemoryProfiler",
    "start_profiling",
    "stop_profiling",
    "get_performance_report",
    # Middleware
    "PerformanceMonitoringMiddleware",
    "DatabasePerformanceMiddleware",
    "CachePerformanceMiddleware",
    "BackgroundTaskPerformanceMonitor",
    # Analyzer
    "PerformanceAnalyzer",
    "PerformanceInsight",
    "PerformanceTrend",
    # API
    "performance_router",
]
