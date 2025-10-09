"""
系统监控模块

提供全面的系统监控功能，包括：
- 应用性能监控
- 数据库连接监控
- 缓存监控
- API性能监控
- 资源使用监控
- 业务指标监控
"""

# 导入重构后的模块化组件
from .monitor import SystemMonitor as _SystemMonitor
from .metrics import (
    PrometheusMetrics,
    get_prometheus_metrics,
)
from .collectors import (
    SystemMetricsCollector,
    DatabaseMetricsCollector,
    CacheMetricsCollector,
    ApplicationMetricsCollector,
    MetricsCollectorManager,
)
from .health_checks import (
    HealthChecker,
    DatabaseHealthChecker,
    RedisHealthChecker,
    SystemResourceHealthChecker,
    ApplicationHealthChecker,
    ExternalServiceHealthChecker,
    DataPipelineHealthChecker,
)
from .utils import (
    get_system_monitor,
    record_http_request,
    record_db_query,
    record_cache_op,
    record_prediction,
    start_system_monitoring,
    stop_system_monitoring,
)


# 保持向后兼容的包装类
class SystemMonitor(_SystemMonitor):
    """
    系统监控器（向后兼容包装器）
    System Monitor (Backward compatibility wrapper)

    注意：此类继承自重构后的模块化监控器。
    建议直接使用 system_monitor_mod.SystemMonitor 获取最新功能。
    """

    pass  # 直接继承，所有功能都在基类中实现


# 导出所有公共接口以保持向后兼容
__all__ = [
    # 核心类
    "SystemMonitor",
    # 指标管理
    "PrometheusMetrics",
    "get_prometheus_metrics",
    # 数据收集器
    "SystemMetricsCollector",
    "DatabaseMetricsCollector",
    "CacheMetricsCollector",
    "ApplicationMetricsCollector",
    "MetricsCollectorManager",
    # 健康检查器
    "HealthChecker",
    "DatabaseHealthChecker",
    "RedisHealthChecker",
    "SystemResourceHealthChecker",
    "ApplicationHealthChecker",
    "ExternalServiceHealthChecker",
    "DataPipelineHealthChecker",
    # 便捷函数
    "get_system_monitor",
    "record_http_request",
    "record_db_query",
    "record_cache_op",
    "record_prediction",
    "start_system_monitoring",
    "stop_system_monitoring",
]
