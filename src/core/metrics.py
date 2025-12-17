"""
Prometheus 指标管理系统

使用单例模式确保指标只注册一次，避免重复注册错误。
"""
from typing import Optional
from prometheus_client import Counter, Histogram, CollectorRegistry, generate_latest


class MetricsManager:
    """
    指标管理器 - 单例模式确保指标只注册一次
    """
    _instance: Optional["MetricsManager"] = None
    _initialized = False
    
    def __new__(cls) -> "MetricsManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        # 使用自定义注册表避免与默认注册表冲突
        self._registry = CollectorRegistry()
        
        # 业务指标
        self.prediction_requests_total = Counter(
            'prediction_requests_total',
            'Total number of prediction requests',
            ['model_name', 'prediction_type'],
            registry=self._registry
        )
        
        self.model_inference_latency = Histogram(
            'model_inference_latency_seconds',
            'Time spent on model inference',
            ['model_name'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self._registry
        )
        
        self.prediction_accuracy_total = Counter(
            'prediction_accuracy_total',
            'Prediction accuracy counter',
            ['model_name', 'result_type'],
            registry=self._registry
        )
        
        self.data_collection_requests_total = Counter(
            'data_collection_requests_total',
            'Total number of data collection requests',
            ['data_source', 'status'],
            registry=self._registry
        )
        
        self.feature_computation_latency = Histogram(
            'feature_computation_latency_seconds',
            'Time spent on feature computation',
            ['feature_type'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self._registry
        )
        
        self.cache_operations_total = Counter(
            'cache_operations_total',
            'Total number of cache operations',
            ['cache_type', 'operation'],
            registry=self._registry
        )
        
        self._initialized = True
    
    def get_registry(self) -> CollectorRegistry:
        """获取指标注册表"""
        return self._registry
    
    def generate_metrics(self) -> bytes:
        """生成指标数据"""
        return generate_latest(self._registry)


# 创建全局指标管理器实例
_metrics_manager = MetricsManager()

# 导出指标实例
prediction_requests_total = _metrics_manager.prediction_requests_total
model_inference_latency = _metrics_manager.model_inference_latency
prediction_accuracy_total = _metrics_manager.prediction_accuracy_total
data_collection_requests_total = _metrics_manager.data_collection_requests_total
feature_computation_latency = _metrics_manager.feature_computation_latency
cache_operations_total = _metrics_manager.cache_operations_total


def get_metrics() -> bytes:
    """获取指标数据"""
    return _metrics_manager.generate_metrics()
