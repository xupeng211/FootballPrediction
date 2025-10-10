"""
Prometheus 指标定义 / Prometheus Metric Definitions

定义所有用于监控的 Prometheus 指标。
"""

from typing import Optional, List
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
)

# 可选的 prometheus_client 导入，用于测试兼容性
try:
    from prometheus_client import REGISTRY

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    REGISTRY = None  # type: ignore


class MetricsDefinitions:
    """Prometheus 指标定义类

    包含所有监控指标的初始化和定义。
    """

    def __init__(
        self,
        registry: Optional[CollectorRegistry] = None,
        tables_to_monitor: Optional[List[str]] = None,
    ):
        """
        初始化指标定义

        Args:
            registry: Prometheus 注册表，默认使用全局注册表
            tables_to_monitor: 需要监控的表列表
        """
        self.registry = registry or REGISTRY

        # 数据采集指标
        self.data_collection_total = self._create_counter(
            "football_data_collection_total",
            "数据采集总次数",
            ["data_source", "collection_type"],
        )

        self.data_collection_errors = self._create_counter(
            "football_data_collection_errors_total",
            "数据采集错误总数",
            ["data_source", "collection_type", "error_type"],
        )

        self.data_collection_duration = self._create_histogram(
            "football_data_collection_duration_seconds",
            "数据采集耗时（秒）",
            ["data_source", "collection_type"],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
        )

        # 数据清洗指标
        self.data_cleaning_total = self._create_counter(
            "football_data_cleaning_total", "数据清洗总次数", ["data_type"]
        )

        self.data_cleaning_errors = self._create_counter(
            "football_data_cleaning_errors_total",
            "数据清洗错误总数",
            ["data_type", "error_type"],
        )

        self.data_cleaning_duration = self._create_histogram(
            "football_data_cleaning_duration_seconds",
            "数据清洗耗时（秒）",
            ["data_type"],
        )

        # 调度器指标
        self.scheduler_task_delay = self._create_gauge(
            "football_scheduler_task_delay_seconds",
            "调度任务延迟时间（秒）",
            ["task_name"],
        )

        self.scheduler_task_failures = self._create_counter(
            "football_scheduler_task_failures_total",
            "调度任务失败总数",
            ["task_name", "failure_reason"],
        )

        self.scheduler_task_duration = self._create_histogram(
            "football_scheduler_task_duration_seconds",
            "调度任务执行时间（秒）",
            ["task_name"],
        )

        # 数据库表行数指标
        self.table_row_count = self._create_gauge(
            "football_table_row_count", "数据表行数统计", ["table_name"]
        )

        # 数据库性能指标
        self.database_connections = self._create_gauge(
            "football_database_connections", "数据库连接数", ["connection_state"]
        )

        self.database_query_duration = self._create_histogram(
            "football_database_query_duration_seconds",
            "数据库查询耗时（秒）",
            ["query_type"],
        )

        # 系统健康指标
        self.system_info = self._create_info("football_system_info", "系统信息")

        self.last_update_timestamp = self._create_gauge(
            "football_metrics_last_update_timestamp", "指标最后更新时间戳"
        )

        # 设置系统信息
        if hasattr(self.system_info, "info"):
            self.system_info.info(
                {
                    "version": "1.0.0",
                    "component": "football_prediction_platform",
                    "environment": "production",
                }
            )

    def _create_counter(self, name: str, description: str, labels: list):
        """创建或获取 Counter 指标"""
        if not PROMETHEUS_AVAILABLE:
            return _MockCounter()
        try:
            return Counter(name, description, labels, registry=self.registry)
        except ValueError:
            # 指标已存在，返回 Mock 实例
            return _MockCounter()

    def _create_gauge(self, name: str, description: str, labels: list = None):
        """创建或获取 Gauge 指标"""
        if not PROMETHEUS_AVAILABLE:
            return _MockGauge()
        try:
            return Gauge(name, description, labels or [], registry=self.registry)
        except ValueError:
            # 指标已存在，返回 Mock 实例
            return _MockGauge()

    def _create_histogram(
        self, name: str, description: str, labels: list, buckets=None
    ):
        """创建或获取 Histogram 指标"""
        if not PROMETHEUS_AVAILABLE:
            return _MockHistogram()

        # 为 Histogram 提供默认桶
        if buckets is None:
            buckets = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, float("inf")]

        try:
            return Histogram(
                name, description, labels, registry=self.registry, buckets=buckets
            )
        except ValueError:
            # 指标已存在，返回 Mock 实例
            return _MockHistogram()

    def _create_info(self, name: str, description: str):
        """创建或获取 Info 指标"""
        if not PROMETHEUS_AVAILABLE:
            return _MockInfo()
        try:
            return Info(name, description, registry=self.registry)
        except ValueError:
            # 指标已存在，返回 Mock 实例
            return _MockInfo()


# Mock 类用于测试环境
class _MockCounter:
    """Mock Counter for testing"""

    def inc(self, value=1):
        pass

    def labels(self, **kwargs):
        return self


class _MockGauge:
    """Mock Gauge for testing"""

    def set(self, value):
        pass

    def labels(self, **kwargs):
        return self


class _MockHistogram:
    """Mock Histogram for testing"""

    def observe(self, value):
        pass

    def labels(self, **kwargs):
        return self


class _MockInfo:
    """Mock Info for testing"""

    def info(self, data):
        pass
