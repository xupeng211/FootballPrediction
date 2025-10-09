"""
Prometheus指标定义和管理
"""

import logging
from typing import Any, Dict, List, Optional

try:
    from prometheus_client import (
        REGISTRY,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
    )
except ImportError:
    # 提供mock实现用于测试环境
    REGISTRY = None

    class CollectorRegistry:
        pass

    class Counter:
        def __init__(self, *args, **kwargs):
            self.labels = lambda *args, **kwargs: self
            self.inc = lambda: None

    class Gauge:
        def __init__(self, *args, **kwargs):
            self.labels = lambda *args, **kwargs: self
            self.set = lambda x: None
            self.inc = lambda: None
            self.dec = lambda: None

    class Histogram:
        def __init__(self, *args, **kwargs):
            self.labels = lambda *args, **kwargs: self
            self.observe = lambda x: None


logger = logging.getLogger(__name__)


class PrometheusMetrics:
    """
    Prometheus指标管理器

    负责创建和管理所有的Prometheus指标。
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        初始化指标管理器

        Args:
            registry: Prometheus注册表实例
        """
        self.registry = registry or REGISTRY
        self._initialize_all_metrics()

    def _initialize_all_metrics(self):
        """初始化所有指标"""
        # 系统资源指标
        self.system_cpu_percent = self._create_gauge(
            "system_cpu_percent", "System CPU usage percentage"
        )
        self.system_memory_percent = self._create_gauge(
            "system_memory_percent", "System memory usage percentage"
        )
        self.system_disk_percent = self._create_gauge(
            "system_disk_percent", "System disk usage percentage"
        )
        self.process_memory_bytes = self._create_gauge(
            "process_memory_bytes", "Process memory usage in bytes"
        )
        self.process_cpu_percent = self._create_gauge(
            "process_cpu_percent", "Process CPU usage percentage"
        )

        # 应用指标
        self.app_uptime_seconds = self._create_gauge(
            "app_uptime_seconds", "Application uptime in seconds"
        )
        self.app_requests_total = self._create_counter(
            "app_requests_total",
            "Total number of HTTP requests",
            ["method", "endpoint", "status_code"],
        )
        self.app_request_duration_seconds = self._create_histogram(
            "app_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
        )

        # 数据库指标
        self.db_connections_active = self._create_gauge(
            "db_connections_active", "Number of active database connections"
        )
        self.db_connections_total = self._create_gauge(
            "db_connections_total", "Total number of database connections"
        )
        self.db_query_duration_seconds = self._create_histogram(
            "db_query_duration_seconds",
            "Database query duration in seconds",
            ["operation", "table"],
        )
        self.db_slow_queries_total = self._create_counter(
            "db_slow_queries_total",
            "Total number of slow database queries",
            ["operation", "table"],
        )

        # 缓存指标
        self.cache_operations_total = self._create_counter(
            "cache_operations_total",
            "Total number of cache operations",
            ["operation", "cache_type", "result"],
        )
        self.cache_hit_ratio = self._create_gauge(
            "cache_hit_ratio", "Cache hit ratio", ["cache_type"]
        )
        self.cache_size_bytes = self._create_gauge(
            "cache_size_bytes", "Cache size in bytes", ["cache_type"]
        )

        # 业务指标
        self.business_predictions_total = self._create_counter(
            "business_predictions_total",
            "Total number of predictions made",
            ["model_version", "league"],
        )
        self.business_prediction_accuracy = self._create_gauge(
            "business_prediction_accuracy",
            "Prediction accuracy rate",
            ["model_version", "time_period"],
        )
        self.business_data_collection_jobs_total = self._create_counter(
            "business_data_collection_jobs_total",
            "Total number of data collection jobs",
            ["data_source", "status"],
        )

        # ML模型指标
        self.ml_model_inference_duration_seconds = self._create_histogram(
            "ml_model_inference_duration_seconds",
            "ML model inference duration in seconds",
            ["model_name", "model_version"],
        )
        self.ml_model_training_duration_seconds = self._create_histogram(
            "ml_model_training_duration_seconds",
            "ML model training duration in seconds",
            ["model_name", "model_version"],
        )
        self.ml_model_accuracy = self._create_gauge(
            "ml_model_accuracy",
            "ML model accuracy score",
            ["model_name", "model_version", "metric_type"],
        )

    def _create_counter(
        self, name: str, description: str, labels: List[str] = None
    ) -> Counter:
        """
        创建Counter指标

        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签列表

        Returns:
            Counter: Counter指标实例
        """
        try:
            return Counter(name, description, labels or [], registry=self.registry)
        except ValueError:
            logger.warning(f"Failed to create counter {name}, using mock")
            mock = Counter()
            return mock

    def _create_gauge(
        self, name: str, description: str, labels: List[str] = None
    ) -> Gauge:
        """
        创建Gauge指标

        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签列表

        Returns:
            Gauge: Gauge指标实例
        """
        try:
            return Gauge(name, description, labels or [], registry=self.registry)
        except ValueError:
            logger.warning(f"Failed to create gauge {name}, using mock")
            mock = Gauge()
            return mock

    def _create_histogram(
        self, name: str, description: str, labels: List[str] = None
    ) -> Histogram:
        """
        创建Histogram指标

        Args:
            name: 指标名称
            description: 指标描述
            labels: 标签列表

        Returns:
            Histogram: Histogram指标实例
        """
        try:
            return Histogram(name, description, labels or [], registry=self.registry)
        except ValueError:
            logger.warning(f"Failed to create histogram {name}, using mock")
            mock = Histogram()
            return mock

    def get_all_metrics(self) -> Dict[str, Any]:
        """
        获取所有指标

        Returns:
            Dict[str, Any]: 包含所有指标的字典
        """
        return {
            # 系统指标
            "system_cpu_percent": self.system_cpu_percent,
            "system_memory_percent": self.system_memory_percent,
            "system_disk_percent": self.system_disk_percent,
            "process_memory_bytes": self.process_memory_bytes,
            "process_cpu_percent": self.process_cpu_percent,
            # 应用指标
            "app_uptime_seconds": self.app_uptime_seconds,
            "app_requests_total": self.app_requests_total,
            "app_request_duration_seconds": self.app_request_duration_seconds,
            # 数据库指标
            "db_connections_active": self.db_connections_active,
            "db_connections_total": self.db_connections_total,
            "db_query_duration_seconds": self.db_query_duration_seconds,
            "db_slow_queries_total": self.db_slow_queries_total,
            # 缓存指标
            "cache_operations_total": self.cache_operations_total,
            "cache_hit_ratio": self.cache_hit_ratio,
            "cache_size_bytes": self.cache_size_bytes,
            # 业务指标
            "business_predictions_total": self.business_predictions_total,
            "business_prediction_accuracy": self.business_prediction_accuracy,
            "business_data_collection_jobs_total": self.business_data_collection_jobs_total,
            # ML指标
            "ml_model_inference_duration_seconds": self.ml_model_inference_duration_seconds,
            "ml_model_training_duration_seconds": self.ml_model_training_duration_seconds,
            "ml_model_accuracy": self.ml_model_accuracy,
        }


# 全局指标实例
_prometheus_metrics: Optional[PrometheusMetrics] = None


def get_prometheus_metrics() -> PrometheusMetrics:
    """
    获取全局Prometheus指标实例

    Returns:
        PrometheusMetrics: 指标管理器实例
    """
    global _prometheus_metrics
    if _prometheus_metrics is None:
        _prometheus_metrics = PrometheusMetrics()
    return _prometheus_metrics
