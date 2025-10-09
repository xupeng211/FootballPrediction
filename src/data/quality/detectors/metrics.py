"""


"""




    """


    """














    from prometheus_client import REGISTRY
import logging
from prometheus_client import Counter, Gauge, Histogram

异常检测监控指标
Anomaly Detection Metrics
提供Prometheus监控指标定义。
logger = logging.getLogger(__name__)
def _get_or_create_metric(metric_class, name: str, description: str, labels: list):
    安全地获取或创建Prometheus指标，避免重复注册错误
    Args:
        metric_class: 指标类型 (Counter, Gauge, Histogram)
        name: 指标名称
        description: 指标描述
        labels: 标签列表
    Returns:
        Prometheus指标实例
    # 尝试从已注册的指标中查找
    for collector in list(REGISTRY._collector_to_names.keys()):
        if hasattr(collector, "_name") and collector._name == name:
            return collector
    # 如果不存在，创建新指标
    try:
        return metric_class(name, description, labels)
    except ValueError as e:
        # 如果仍然失败，记录警告并返回一个虚拟指标
        logger.warning(f"无法创建Prometheus指标 {name}: {e}")
        # 返回一个虚拟对象，避免代码崩溃
        class DummyMetric:
            def labels(self, *args, **kwargs):
                return self
            def inc(self, *args, **kwargs):
                pass
            def set(self, *args, **kwargs):
                pass
            def observe(self, *args, **kwargs):
                pass
        return DummyMetric()
# 异常检测总计指标
anomalies_detected_total = _get_or_create_metric(
    Counter,
    "football_data_anomalies_detected_total",
    "Total number of data anomalies detected",
    ["table_name", "anomaly_type", "detection_method", "severity"],
)
# 数据漂移评分指标
data_drift_score = _get_or_create_metric(
    Gauge,
    "football_data_drift_score",
    "Data drift score indicating distribution changes",
    ["table_name", "feature_name"],
)
# 异常检测执行时间
anomaly_detection_duration_seconds = _get_or_create_metric(
    Histogram,
    "football_data_anomaly_detection_duration_seconds",
    "Time taken to complete anomaly detection",
    ["table_name", "detection_method"],
)
# 异常检测覆盖率
anomaly_detection_coverage = _get_or_create_metric(
    Gauge,
    "football_data_anomaly_detection_coverage",
    "Percentage of data covered by anomaly detection",
    ["table_name"],
)