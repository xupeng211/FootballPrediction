"""
API性能优化模块
API Performance Optimization Module

提供统一的API性能优化功能集成，包括缓存、数据库查询优化、连接池管理等。
"""

from .api_performance_optimizer import router as optimization_router

# 导入连接池优化相关类
try:
    from .connection_pool import (
        ConnectionPoolOptimizer,
        PoolMetrics,
        PoolOptimizationConfig,
        get_connection_pool_optimizer,
        initialize_connection_pool_optimizer,
    )
except ImportError:
    ConnectionPoolOptimizer = None
    PoolMetrics = None
    PoolOptimizationConfig = None
    get_connection_pool_optimizer = None
    initialize_connection_pool_optimizer = None

from .database_performance_api import router as database_optimization_router

# 数据库性能中间件相关类 - 模块暂未实现
DatabasePerformanceMiddleware = None
QueryOptimizationAdvisor = None
get_database_middleware = None
get_optimization_advisor = None
initialize_database_monitoring = None

# 数据库性能分析器相关类 - 模块暂未实现
DatabasePerformanceAnalyzer = None
QueryMetrics = None
get_database_analyzer = None
initialize_database_analyzer = None

# 性能中间件相关类 - 模块暂未实现
EnhancedPerformanceMiddleware = None
create_performance_middleware = None
get_performance_middleware = None

# 查询执行分析相关类 - 模块暂未实现
ExecutionPlanAnalysis = None
ExecutionPlanNode = None
QueryExecutionAnalyzer = None
get_query_execution_analyzer = None
initialize_query_execution_analyzer = None

# 缓存相关类 - 模块暂未实现
CacheMiddleware = None
SmartCacheManager = None
get_cache_manager = None
get_cache_middleware = None
initialize_cache_system = None

__all__ = [
    # API性能中间件
    "EnhancedPerformanceMiddleware",
    "create_performance_middleware",
    "get_performance_middleware",
    # 智能缓存系统
    "SmartCacheManager",
    "CacheMiddleware",
    "initialize_cache_system",
    "get_cache_manager",
    "get_cache_middleware",
    # 数据库查询优化
    "DatabasePerformanceAnalyzer",
    "QueryMetrics",
    "get_database_analyzer",
    "initialize_database_analyzer",
    # 数据库性能中间件
    "DatabasePerformanceMiddleware",
    "QueryOptimizationAdvisor",
    "get_database_middleware",
    "get_optimization_advisor",
    "initialize_database_monitoring",
    # 连接池优化
    "ConnectionPoolOptimizer",
    "PoolOptimizationConfig",
    "PoolMetrics",
    "get_connection_pool_optimizer",
    "initialize_connection_pool_optimizer",
    # 查询执行分析
    "QueryExecutionAnalyzer",
    "ExecutionPlanAnalysis",
    "ExecutionPlanNode",
    "get_query_execution_analyzer",
    "initialize_query_execution_analyzer",
    # API路由
    "optimization_router",
    "database_optimization_router",
]
