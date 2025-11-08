"""
性能配置管理
Performance Configuration Management

定义性能监控和优化相关的配置参数。
Defines performance monitoring and optimization related configuration parameters.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class CacheConfig:
    """缓存配置"""

    # 预测相关缓存配置
    prediction_ttl: int = 1800  # 30分钟
    prediction_model_ttl: int = 86400  # 24小时
    team_stats_ttl: int = 1800  # 30分钟
    match_data_ttl: int = 900  # 15分钟
    odds_data_ttl: int = 300  # 5分钟

    # API响应缓存配置
    api_response_ttl: int = 300  # 5分钟
    user_session_ttl: int = 1800  # 30分钟
    auth_token_ttl: int = 1800  # 30分钟

    # 本地缓存配置
    local_cache_size: int = 1000
    lru_eviction_policy: bool = True

    # Redis配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_max_connections: int = 10


@dataclass
class MonitoringConfig:
    """监控配置"""

    # 系统监控间隔
    metrics_collection_interval: int = 30  # 秒
    history_retention_size: int = 1000  # 数据点数量

    # 性能阈值
    cpu_warning_threshold: float = 70.0  # 百分比
    cpu_critical_threshold: float = 90.0
    memory_warning_threshold: float = 80.0
    memory_critical_threshold: float = 95.0
    disk_warning_threshold: float = 85.0
    disk_critical_threshold: float = 95.0

    # 响应时间阈值
    response_time_warning: float = 1.0  # 秒
    response_time_critical: float = 2.0

    # 错误率阈值
    error_rate_warning: float = 0.02  # 2%
    error_rate_critical: float = 0.05  # 5%

    # 连接数阈值
    connection_warning: int = 100
    connection_critical: int = 200


@dataclass
class OptimizationConfig:
    """优化配置"""

    # 数据库优化
    enable_query_optimization: bool = True
    enable_index_optimization: bool = True
    enable_connection_pooling: bool = True

    # 查询优化
    slow_query_threshold: float = 1.0  # 秒
    enable_query_caching: bool = True
    query_cache_ttl: int = 300  # 5分钟

    # 连接池配置
    min_connections: int = 5
    max_connections: int = 20
    connection_timeout: int = 30
    connection_recycle_time: int = 3600

    # 异步处理
    enable_async_processing: bool = True
    max_concurrent_requests: int = 100
    request_timeout: int = 30


class PerformanceConfig:
    """性能配置管理器"""

    def __init__(self):
        self.cache = CacheConfig()
        self.monitoring = MonitoringConfig()
        self.optimization = OptimizationConfig()

    def get_cache_config(self) -> dict[str, Any]:
        """获取缓存配置字典"""
        return {
            "prediction": {
                "ttl": self.cache.prediction_ttl,
                "model_ttl": self.cache.prediction_model_ttl,
                "team_stats_ttl": self.cache.team_stats_ttl,
                "match_data_ttl": self.cache.match_data_ttl,
                "odds_data_ttl": self.cache.odds_data_ttl,
            },
            "api": {
                "response_ttl": self.cache.api_response_ttl,
                "session_ttl": self.cache.user_session_ttl,
                "token_ttl": self.cache.auth_token_ttl,
            },
            "local": {
                "size": self.cache.local_cache_size,
                "lru_policy": self.cache.lru_eviction_policy,
            },
            "redis": {
                "host": self.cache.redis_host,
                "port": self.cache.redis_port,
                "db": self.cache.redis_db,
                "max_connections": self.cache.redis_max_connections,
            },
        }

    def get_monitoring_config(self) -> dict[str, Any]:
        """获取监控配置字典"""
        return {
            "collection": {
                "interval": self.monitoring.metrics_collection_interval,
                "retention_size": self.monitoring.history_retention_size,
            },
            "thresholds": {
                "cpu": {
                    "warning": self.monitoring.cpu_warning_threshold,
                    "critical": self.monitoring.cpu_critical_threshold,
                },
                "memory": {
                    "warning": self.monitoring.memory_warning_threshold,
                    "critical": self.monitoring.memory_critical_threshold,
                },
                "disk": {
                    "warning": self.monitoring.disk_warning_threshold,
                    "critical": self.monitoring.disk_critical_threshold,
                },
                "response_time": {
                    "warning": self.monitoring.response_time_warning,
                    "critical": self.monitoring.response_time_critical,
                },
                "error_rate": {
                    "warning": self.monitoring.error_rate_warning,
                    "critical": self.monitoring.error_rate_critical,
                },
                "connections": {
                    "warning": self.monitoring.connection_warning,
                    "critical": self.monitoring.connection_critical,
                },
            },
        }

    def get_optimization_config(self) -> dict[str, Any]:
        """获取优化配置字典"""
        return {
            "database": {
                "enable_query_optimization": self.optimization.enable_query_optimization,
                "enable_index_optimization": self.optimization.enable_index_optimization,
                "enable_connection_pooling": self.optimization.enable_connection_pooling,
            },
            "query": {
                "slow_threshold": self.optimization.slow_query_threshold,
                "enable_caching": self.optimization.enable_query_caching,
                "cache_ttl": self.optimization.query_cache_ttl,
            },
            "connection_pool": {
                "min_connections": self.optimization.min_connections,
                "max_connections": self.optimization.max_connections,
                "timeout": self.optimization.connection_timeout,
                "recycle_time": self.optimization.connection_recycle_time,
            },
            "async": {
                "enable_processing": self.optimization.enable_async_processing,
                "max_concurrent_requests": self.optimization.max_concurrent_requests,
                "request_timeout": self.optimization.request_timeout,
            },
        }

    def update_cache_config(self, **kwargs):
        """更新缓存配置"""
        for key, value in kwargs.items():
            if hasattr(self.cache, key):
                setattr(self.cache, key, value)

    def update_monitoring_config(self, **kwargs):
        """更新监控配置"""
        for key, value in kwargs.items():
            if hasattr(self.monitoring, key):
                setattr(self.monitoring, key, value)

    def update_optimization_config(self, **kwargs):
        """更新优化配置"""
        for key, value in kwargs.items():
            if hasattr(self.optimization, key):
                setattr(self.optimization, key, value)


# 全局配置实例
_performance_config: PerformanceConfig = None


def get_performance_config() -> PerformanceConfig:
    """获取性能配置实例"""
    global _performance_config
    if _performance_config is None:
        _performance_config = PerformanceConfig()
    return _performance_config


# 预定义的缓存TTL配置
CACHE_TTL_CONFIG = {
    "short": 300,  # 5分钟 - 高频变化数据
    "medium": 1800,  # 30分钟 - 中频变化数据
    "long": 3600,  # 1小时 - 低频变化数据
    "daily": 86400,  # 24小时 - 每日更新数据
}

# 预定义的性能阈值
PERFORMANCE_THRESHOLDS = {
    "excellent": {"cpu": 50, "memory": 60, "response_time": 0.5, "error_rate": 0.01},
    "good": {"cpu": 70, "memory": 75, "response_time": 1.0, "error_rate": 0.02},
    "warning": {"cpu": 85, "memory": 85, "response_time": 2.0, "error_rate": 0.05},
    "critical": {"cpu": 90, "memory": 95, "response_time": 5.0, "error_rate": 0.1},
}
