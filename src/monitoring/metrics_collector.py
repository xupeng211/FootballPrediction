"""
应用指标收集器
Application Metrics Collector
"""

import time
import psutil
from typing import Dict, Any

# 简单的指标存储
_metrics_store = {
    'requests_total': 0,
    'requests_success': 0,
    'requests_error': 0,
    'cache_hits': 0,
    'cache_misses': 0,
    'predictions_total': 0,
    'predictions_correct': 0,
    'response_times': [],
    'active_connections': 0
}

class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self.start_time = time.time()

    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """记录HTTP请求"""
        _metrics_store['requests_total'] += 1
        _metrics_store['response_times'].append(duration)

        if status_code < 400:
            _metrics_store['requests_success'] += 1
        else:
            _metrics_store['requests_error'] += 1

    def record_cache_hit(self):
        """记录缓存命中"""
        _metrics_store['cache_hits'] += 1

    def record_cache_miss(self):
        """记录缓存未命中"""
        _metrics_store['cache_misses'] += 1

    def record_prediction(self, correct: bool):
        """记录预测结果"""
        _metrics_store['predictions_total'] += 1
        if correct:
            _metrics_store['predictions_correct'] += 1

    def get_cache_hit_rate(self) -> float:
        """获取缓存命中率"""
        total = _metrics_store['cache_hits'] + _metrics_store['cache_misses']
        if total == 0:
            return 0.0
        return (_metrics_store['cache_hits'] / total) * 100

    def get_prediction_accuracy(self) -> float:
        """获取预测准确率"""
        if _metrics_store['predictions_total'] == 0:
            return 0.0
        return (_metrics_store['predictions_correct'] / _metrics_store['predictions_total']) * 100

    def get_avg_response_time(self) -> float:
        """获取平均响应时间"""
        times = _metrics_store['response_times']
        if not times:
            return 0.0
        return sum(times) / len(times)

    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)

        return {
            'memory_usage_mb': memory.used / 1024 / 1024,
            'memory_usage_percent': memory.percent,
            'cpu_usage_percent': cpu,
            'uptime_seconds': time.time() - self.start_time
        }

    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        return {
            'requests': {
                'total': _metrics_store['requests_total'],
                'success': _metrics_store['requests_success'],
                'error': _metrics_store['requests_error'],
                'success_rate': (
                    _metrics_store['requests_success'] /
                    max(_metrics_store['requests_total'], 1) * 100
                )
            },
            'cache': {
                'hit_rate': self.get_cache_hit_rate(),
                'hits': _metrics_store['cache_hits'],
                'misses': _metrics_store['cache_misses']
            },
            'predictions': {
                'accuracy': self.get_prediction_accuracy(),
                'total': _metrics_store['predictions_total'],
                'correct': _metrics_store['predictions_correct']
            },
            'performance': {
                'avg_response_time_ms': self.get_avg_response_time() * 1000,
                'active_connections': _metrics_store['active_connections']
            },
            'system': self.get_system_info()
        }

# 全局实例
metrics = MetricsCollector()

def get_metrics_collector():
    """获取指标收集器实例"""
    return metrics

def track_prediction_performance(correct: bool):
    """跟踪预测性能"""
    metrics.record_prediction(correct)

def track_cache_performance(hit: bool):
    """跟踪缓存性能"""
    if hit:
        metrics.record_cache_hit()
    else:
        metrics.record_cache_miss()

def start_metrics_collection():
    """启动指标收集"""
    return True

def stop_metrics_collection():
    """停止指标收集"""
    return True
