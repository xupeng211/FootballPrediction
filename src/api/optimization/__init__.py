"""
API性能优化模块
API Performance Optimization Module

提供统一的API性能优化功能集成，包括缓存、数据库查询优化、连接池管理等。
"""

from .api_performance_optimizer import router as optimization_router
from .connection_pool_optimizer import (
    ConnectionPoolOptimizer,
    PoolMetrics,
    PoolOptimizationConfig,
    get_connection_pool_optimizer,
    initialize_connection_pool_optimizer,
)
from .database_performance_api import router as database_optimization_router
from .database_performance_middleware import (
    DatabasePerformanceMiddleware,
    QueryOptimizationAdvisor,
    get_database_middleware,
    get_optimization_advisor,
    initialize_database_monitoring,
)
from .database_query_optimizer import (
    DatabasePerformanceAnalyzer,
    QueryMetrics,
    get_database_analyzer,
    initialize_database_analyzer,
)
from .enhanced_performance_middleware import (
    EnhancedPerformanceMiddleware,
    create_performance_middleware,
    get_performance_middleware,
)
from .query_execution_analyzer import (
    ExecutionPlanAnalysis,
    ExecutionPlanNode,
    QueryExecutionAnalyzer,
    get_query_execution_analyzer,
    initialize_query_execution_analyzer,
)
from .smart_cache_system import (
    CacheMiddleware,
    SmartCacheManager,
    get_cache_manager,
    get_cache_middleware,
    initialize_cache_system,
)

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
