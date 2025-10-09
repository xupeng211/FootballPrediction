"""
Prometheus指标管理 / Prometheus Metrics Management

定义和管理所有的Prometheus指标。
"""

from typing import Optional, Dict, Any

# 可选的prometheus_client导入
try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        CollectorRegistry,
        generate_latest,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # 创建空的替代类
    class CollectorRegistry:
        def __init__(self):
            self._metrics = []

        def register(self, metric):
            self._metrics.append(metric)

    def generate_latest(registry):
        return b"# Prometheus metrics not available"

    class _MockMetric:
        def __init__(self, *args, **kwargs):
            # 忽略所有参数，包括 registry
            pass

        def inc(self, value=1):
            pass

        def observe(self, value):
            pass

        def set(self, value):
            pass

        def labels(self, **kwargs):
            return self

        def time(self):
            return _MockContextManager()

        def _child(self):
            return self

    class _MockContextManager:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __call__(self, func):
            return func

    # 创建空的指标类
    Counter = _MockMetric
    Histogram = _MockMetric
    Gauge = _MockMetric


class PrometheusMetricsManager:
    """Prometheus指标管理器

    负责初始化和管理所有的Prometheus指标。
    提供统一的指标更新接口。
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        初始化指标管理器

        Args:
            registry: Prometheus注册表，如果为None则创建新的
        """
        self.registry = registry or CollectorRegistry()
        self._init_business_metrics()
        self._init_performance_metrics()
        self._init_system_metrics()
        self._init_custom_metrics()

    def _init_business_metrics(self):
        """初始化业务指标"""
        # 预测总数
        self.prediction_counter = Counter(
            "predictions_total",
            "Total number of predictions",
            ["model_version", "result"],
            registry=self.registry,
        )

        # 预测准确率
        self.prediction_accuracy = Gauge(
            "prediction_accuracy",
            "Prediction accuracy rate",
            ["model_version", "time_window"],
            registry=self.registry,
        )

        # 模型加载次数
        self.model_load_counter = Counter(
            "model_loads_total",
            "Total number of model loads",
            ["model_name", "status"],
            registry=self.registry,
        )

        # 价值投注次数
        self.value_bets_counter = Counter(
            "value_bets_total",
            "Total number of value bets identified",
            ["confidence_level"],
            registry=self.registry,
        )

    def _init_performance_metrics(self):
        """初始化性能指标"""
        # 请求处理时间
        self.request_duration = Histogram(
            "request_duration_seconds",
            "Request processing duration",
            ["endpoint", "method"],
            registry=self.registry,
        )

        # 预测时间
        self.prediction_duration = Histogram(
            "prediction_duration_seconds",
            "Prediction processing duration",
            ["model_version"],
            registry=self.registry,
        )

        # 数据处理时间
        self.data_processing_duration = Histogram(
            "data_processing_duration_seconds",
            "Data processing duration",
            ["stage"],
            registry=self.registry,
        )

        # 并发请求数
        self.concurrent_requests = Gauge(
            "concurrent_requests",
            "Number of concurrent requests",
            registry=self.registry,
        )

    def _init_system_metrics(self):
        """初始化系统指标"""
        # CPU使用率
        self.cpu_usage = Gauge(
            "cpu_usage_percent",
            "CPU usage percentage",
            registry=self.registry,
        )

        # 内存使用
        self.memory_usage = Gauge(
            "memory_usage_bytes",
            "Memory usage in bytes",
            registry=self.registry,
        )

        # 错误计数
        self.error_counter = Counter(
            "errors_total",
            "Total number of errors",
            ["error_type", "component"],
            registry=self.registry,
        )

        # 缓存命中率
        self.cache_hit_rate = Gauge(
            "cache_hit_rate",
            "Cache hit rate",
            ["cache_type"],
            registry=self.registry,
        )

    def _init_custom_metrics(self):
        """初始化自定义指标"""
        # 自定义计数器
        self.custom_counters: Dict[str, Counter] = {}

        # 自定义仪表
        self.custom_gauges: Dict[str, Gauge] = {}

        # 自定义直方图
        self.custom_histograms: Dict[str, Histogram] = {}

    def create_counter(self, name: str, description: str, labels: list = None) -> Counter:
        """创建新的计数器"""
        counter = Counter(
            name,
            description,
            labels or [],
            registry=self.registry,
        )
        self.custom_counters[name] = counter
        return counter

    def create_gauge(self, name: str, description: str, labels: list = None) -> Gauge:
        """创建新的仪表"""
        gauge = Gauge(
            name,
            description,
            labels or [],
            registry=self.registry,
        )
        self.custom_gauges[name] = gauge
        return gauge

    def create_histogram(
        self, name: str, description: str, labels: list = None, buckets=None
    ) -> Histogram:
        """创建新的直方图"""
        histogram = Histogram(
            name,
            description,
            labels or [],
            registry=self.registry,
            buckets=buckets,
        )
        self.custom_histograms[name] = histogram
        return histogram

    def get_metric(self, name: str):
        """获取指标"""
        if name in self.custom_counters:
            return self.custom_counters[name]
        elif name in self.custom_gauges:
            return self.custom_gauges[name]
        elif name in self.custom_histograms:
            return self.custom_histograms[name]

        # 检查内置指标
        for attr in dir(self):
            if name == attr and isinstance(getattr(self, attr), (Counter, Gauge, Histogram)):
                return getattr(self, attr)

        return None

    def update_all_system_metrics(self, metrics_data: Dict[str, Any]):
        """批量更新系统指标"""
        if "cpu_percent" in metrics_data:
            self.cpu_usage.set(metrics_data["cpu_percent"])

        if "memory_bytes" in metrics_data:
            self.memory_usage.set(metrics_data["memory_bytes"])

        if "cache_hit_rates" in metrics_data:
            for cache_type, hit_rate in metrics_data["cache_hit_rates"].items():
                self.cache_hit_rate.labels(cache_type=cache_type).set(hit_rate)

    def increment_error(self, error_type: str, component: str):
        """增加错误计数"""
        self.error_counter.labels(error_type=error_type, component=component).inc()

    def time_request(self, endpoint: str, method: str):
        """请求计时上下文管理器"""
        return self.request_duration.labels(endpoint=endpoint, method=method).time()

    def time_prediction(self, model_version: str):
        """预测计时上下文管理器"""
        return self.prediction_duration.labels(model_version=model_version).time()

    def time_data_processing(self, stage: str):
        """数据处理计时上下文管理器"""
        return self.data_processing_duration.labels(stage=stage).time()

    def generate_metrics(self) -> bytes:
        """生成Prometheus格式的指标"""
        if PROMETHEUS_AVAILABLE:
            return generate_latest(self.registry)
        else:
            return b"# Prometheus metrics not available"

    def reset_metrics(self):
        """重置所有指标（仅用于测试）"""
        if PROMETHEUS_AVAILABLE:
            # 注意：这需要重新创建注册表
            self.registry = CollectorRegistry()
            self._init_business_metrics()
            self._init_performance_metrics()
            self._init_system_metrics()
            self._init_custom_metrics()