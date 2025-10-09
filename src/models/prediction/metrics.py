"""
预测服务监控指标
Prediction Service Metrics

定义预测服务的Prometheus监控指标。
"""

try:
    from prometheus_client import Counter, Histogram, Gauge

    # 预测计数器
    predictions_total = Counter(
        "predictions_total",
        "Total number of predictions made",
        ["model_name", "model_version", "result"]
    )

    # 预测耗时直方图
    prediction_duration_seconds = Histogram(
        "prediction_duration_seconds",
        "Time spent making predictions",
        ["model_name", "model_version"]
    )

    # 预测准确率
    prediction_accuracy = Gauge(
        "prediction_accuracy",
        "Prediction accuracy over time",
        ["model_name", "model_version", "time_window"]
    )

    # 模型加载耗时
    model_load_duration_seconds = Histogram(
        "model_load_duration_seconds",
        "Time spent loading models from MLflow",
        ["model_name"]
    )

    # 缓存命中率
    cache_hit_ratio = Gauge(
        "prediction_cache_hit_ratio",
        "Prediction cache hit ratio",
        ["cache_type"]
    )

    # 特征准备耗时
    feature_preparation_duration_seconds = Histogram(
        "feature_preparation_duration_seconds",
        "Time spent preparing features for prediction",
        ["feature_type"]
    )

    # 模型使用次数
    model_usage_count = Counter(
        "model_usage_count",
        "Number of times a model version is used",
        ["model_name", "model_version"]
    )

    # 预测错误计数
    prediction_errors_total = Counter(
        "prediction_errors_total",
        "Total number of prediction errors",
        ["error_type", "model_name"]
    )

except ImportError:
    # 测试环境下的模拟实现
    class MockMetric:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, **kwargs):
            return self

        def inc(self, *args):
            return self

        def observe(self, *args):
            return self

        def set(self, *args):
            return self

    predictions_total = MockMetric
    prediction_duration_seconds = MockMetric
    prediction_accuracy = MockMetric
    model_load_duration_seconds = MockMetric
    cache_hit_ratio = MockMetric
    feature_preparation_duration_seconds = MockMetric
    model_usage_count = MockMetric
    prediction_errors_total = MockMetric