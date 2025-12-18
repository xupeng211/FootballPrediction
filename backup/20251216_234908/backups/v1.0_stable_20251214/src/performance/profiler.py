"""性能分析器模块
Performance Profiler Module.

提供API端点和系统性能分析功能.
"""

import asyncio
import functools
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class ProfileStats:
    """性能统计信息."""

    call_count: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    recent_calls: deque = field(default_factory=lambda: deque(maxlen=100))
    error_count: int = 0
    last_error: str | None = None


class APIEndpointProfiler:
    """API端点性能分析器."""

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.stats: dict[str, ProfileStats] = defaultdict(ProfileStats)
        self.lock = threading.RLock()
        self.enabled = True

    def record_call(
        self,
        endpoint: str,
        duration: float,
        success: bool = True,
        error: str | None = None,
    ):
        """记录API调用."""
        if not self.enabled:
            return

        with self.lock:
            stats = self.stats[endpoint]
            stats.call_count += 1
            stats.recent_calls.append(duration)

            if success:
                stats.total_time += duration
                stats.avg_time = stats.total_time / stats.call_count
                stats.min_time = min(stats.min_time, duration)
                stats.max_time = max(stats.max_time, duration)
            else:
                stats.error_count += 1
                stats.last_error = error

    def get_stats(
        self, endpoint: str | None = None
    ) -> ProfileStats | dict[str, ProfileStats]:
        """获取性能统计."""
        with self.lock:
            if endpoint:
                return self.stats[endpoint]
            return dict(self.stats)

    def get_top_slowest(self, limit: int = 10) -> list[tuple]:
        """获取最慢的端点."""
        with self.lock:
            return sorted(
                [
                    (name, stats.avg_time, stats.call_count)
                    for name, stats in self.stats.items()
                    if stats.call_count > 0
                ],
                key=lambda x: x[1],
                reverse=True,
            )[:limit]

    def get_recent_performance(self, endpoint: str, minutes: int = 5) -> dict[str, Any]:
        """获取最近的性能数据."""
        _cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        with self.lock:
            stats = self.stats[endpoint]
            recent_times = [
                duration
                for i, duration in enumerate(stats.recent_calls)
                if datetime.utcnow() - timedelta(seconds=i) >= _cutoff_time
            ]

            if not recent_times:
                return {"avg_time": 0, "call_count": 0, "min_time": 0, "max_time": 0}

            return {
                "avg_time": sum(recent_times) / len(recent_times),
                "call_count": len(recent_times),
                "min_time": min(recent_times),
                "max_time": max(recent_times),
            }

    def clear_stats(self, endpoint: str | None = None):
        """清空统计数据."""
        with self.lock:
            if endpoint:
                if endpoint in self.stats:
                    del self.stats[endpoint]
            else:
                self.stats.clear()

    def enable(self):
        """启用性能分析."""
        self.enabled = True

    def disable(self):
        """禁用性能分析."""
        self.enabled = False

    def profile_endpoint(self, endpoint_name: str):
        """装饰器：分析API端点性能."""

        def decorator(func: Callable):
            if asyncio.iscoroutinefunction(func):

                @functools.wraps(func)
                async def async_wrapper(*args, **kwargs):
                    if not self.enabled:
                        return await func(*args, **kwargs)

                    start_time = time.time()
                    try:
                        result = await func(*args, **kwargs)
                        duration = time.time() - start_time
                        self.record_call(endpoint_name, duration, success=True)
                        return result
                    except Exception as e:
                        duration = time.time() - start_time
                        self.record_call(
                            endpoint_name, duration, success=False, error=str(e)
                        )
                        raise

                return async_wrapper
            else:

                @functools.wraps(func)
                def sync_wrapper(*args, **kwargs):
                    if not self.enabled:
                        return func(*args, **kwargs)

                    start_time = time.time()
                    try:
                        result = func(*args, **kwargs)
                        duration = time.time() - start_time
                        self.record_call(endpoint_name, duration, success=True)
                        return result
                    except Exception as e:
                        duration = time.time() - start_time
                        self.record_call(
                            endpoint_name, duration, success=False, error=str(e)
                        )
                        raise

                return sync_wrapper

        return decorator

    def record_endpoint_request(
        self,
        endpoint: str,
        method: str,
        duration: float,
        status_code: int,
        request_size: int = 0,
        response_size: int = 0,
    ) -> None:
        """记录端点请求性能数据.

        Args:
            endpoint: API端点路径
            method: HTTP方法
            duration: 请求持续时间(秒)
            status_code: HTTP状态码
            request_size: 请求大小(字节)
            response_size: 响应大小(字节)
        """
        success = status_code < 400
        error = f"HTTP {status_code}" if not success else None

        # 记录到现有统计系统
        self.record_call(endpoint, duration, success, error)

        # 额外记录HTTP方法信息
        with self.lock:
            stats = self.stats[endpoint]
            if not hasattr(stats, "method_info"):
                stats.method_info = {}

            method_key = f"{method}_{status_code}"
            if method_key not in stats.method_info:
                stats.method_info[method_key] = {
                    "count": 0,
                    "total_duration": 0.0,
                    "request_size_total": 0,
                    "response_size_total": 0,
                }

            method_stats = stats.method_info[method_key]
            method_stats["count"] += 1
            method_stats["total_duration"] += duration
            method_stats["request_size_total"] += request_size
            method_stats["response_size_total"] += response_size

    def get_endpoint_stats(self, endpoint: str) -> dict[str, Any]:
        """获取端点性能统计.

        Args:
            endpoint: 端点路径

        Returns:
            端点性能统计数据
        """
        with self.lock:
            stats = self.stats.get(endpoint, ProfileStats())

            result = {
                "call_count": stats.call_count,
                "avg_time": stats.avg_time,
                "min_time": stats.min_time if stats.min_time != float("inf") else 0.0,
                "max_time": stats.max_time,
                "error_count": stats.error_count,
                "error_rate": (
                    (stats.error_count / stats.call_count)
                    if stats.call_count > 0
                    else 0.0
                ),
                "success_rate": (
                    ((stats.call_count - stats.error_count) / stats.call_count)
                    if stats.call_count > 0
                    else 1.0
                ),
            }

            # 添加HTTP方法统计
            if hasattr(stats, "method_info") and stats.method_info:
                result["method_stats"] = {}
                for method_key, method_stats in stats.method_info.items():
                    method, status_code = method_key.split("_", 1)
                    if method not in result["method_stats"]:
                        result["method_stats"][method] = {
                            "requests": 0,
                            "avg_duration": 0.0,
                            "avg_request_size": 0.0,
                            "avg_response_size": 0.0,
                        }

                    result["method_stats"][method]["requests"] += method_stats["count"]
                    result["method_stats"][method]["avg_duration"] = (
                        method_stats["total_duration"] / method_stats["count"]
                    )
                    result["method_stats"][method]["avg_request_size"] = (
                        method_stats["request_size_total"] / method_stats["count"]
                    )
                    result["method_stats"][method]["avg_response_size"] = (
                        method_stats["response_size_total"] / method_stats["count"]
                    )

            return result

    def get_slow_endpoints(self, threshold: float = 0.5) -> list[dict[str, Any]]:
        """获取慢端点列表.

        Args:
            threshold: 慢端点阈值(秒)

        Returns:
            慢端点列表，按平均响应时间降序排列
        """
        slow_endpoints = []

        with self.lock:
            for endpoint, stats in self.stats.items():
                if stats.call_count > 0 and stats.avg_time > threshold:
                    slow_endpoints.append(
                        {
                            "endpoint": endpoint,
                            "avg_time": stats.avg_time,
                            "call_count": stats.call_count,
                            "max_time": stats.max_time,
                            "error_rate": (
                                (stats.error_count / stats.call_count)
                                if stats.call_count > 0
                                else 0.0
                            ),
                        }
                    )

        # 按平均响应时间降序排列
        return sorted(slow_endpoints, key=lambda x: x["avg_time"], reverse=True)

    def get_summary_report(self) -> dict[str, Any]:
        """获取摘要报告."""
        with self.lock:
            total_calls = sum(stats.call_count for stats in self.stats.values())
            total_errors = sum(stats.error_count for stats in self.stats.values())

            if total_calls == 0:
                return {
                    "total_calls": 0,
                    "total_errors": 0,
                    "error_rate": 0.0,
                    "top_slowest": [],
                    "endpoint_count": 0,
                }

            return {
                "total_calls": total_calls,
                "total_errors": total_errors,
                "error_rate": (total_errors / total_calls) * 100,
                "top_slowest": self.get_top_slowest(5),
                "endpoint_count": len(self.stats),
                "slow_endpoints": self.get_slow_endpoints(0.5)[:10],  # 前10个最慢端点
            }


# 全局性能分析器实例
_profiler_instance: APIEndpointProfiler | None = None
_profiler_lock = threading.Lock()


def get_profiler() -> APIEndpointProfiler:
    """获取全局性能分析器实例."""
    global _profiler_instance
    if _profiler_instance is None:
        with _profiler_lock:
            if _profiler_instance is None:
                _profiler_instance = APIEndpointProfiler()
    return _profiler_instance


def profile_api_endpoint(endpoint_name: str):
    """便捷的API端点性能分析装饰器."""
    return get_profiler().profile_endpoint(endpoint_name)


# 数据库查询性能分析器
class DatabaseQueryProfiler:
    """数据库查询性能分析器."""

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.queries: dict[str, list[float]] = defaultdict(list)
        self.lock = threading.Lock()
        self.enabled = True

    def record_query(self, query_type: str, duration: float):
        """记录数据库查询."""
        if not self.enabled:
            return

        with self.lock:
            self.queries[query_type].append(duration)
            # 保留最近的查询记录
            if len(self.queries[query_type]) > self.max_history:
                self.queries[query_type] = self.queries[query_type][-self.max_history :]

    def get_query_stats(self, query_type: str) -> dict[str, float]:
        """获取查询统计."""
        with self.lock:
            times = self.queries.get(query_type, [])
            if not times:
                return {
                    "avg_time": 0.0,
                    "min_time": 0.0,
                    "max_time": 0.0,
                    "count": 0,
                    "total_time": 0.0,
                }

            return {
                "avg_time": sum(times) / len(times),
                "min_time": min(times),
                "max_time": max(times),
                "count": len(times),
                "total_time": sum(times),
            }

    def get_all_stats(self) -> dict[str, dict[str, float]]:
        """获取所有查询统计."""
        with self.lock:
            return {
                query_type: self.get_query_stats(query_type)
                for query_type in self.queries.keys()
            }


# 内存性能分析器
class MemoryProfiler:
    """内存性能分析器."""

    def __init__(self):
        self.samples: list[dict[str, Any]] = []
        self.lock = threading.Lock()
        self.enabled = True

    def sample_memory(self):
        """采样内存使用情况."""
        if not self.enabled:
            return

        try:
            import gc

            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()

            sample = {
                "timestamp": datetime.utcnow(),
                "rss": memory_info.rss,  # 物理内存
                "vms": memory_info.vms,  # 虚拟内存
                "percent": process.memory_percent(),
                "gc_count": tuple(gc.get_count()),
                "gc_objects": len(gc.get_objects()),
            }

            with self.lock:
                self.samples.append(sample)
                # 保留最近1000个样本
                if len(self.samples) > 1000:
                    self.samples = self.samples[-1000:]

        except ImportError:
            # psutil不可用时跳过内存采样
            pass

    def get_memory_trend(self, minutes: int = 5) -> dict[str, Any]:
        """获取内存使用趋势."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        with self.lock:
            recent_samples = [
                sample for sample in self.samples if sample["timestamp"] >= cutoff_time
            ]

            if not recent_samples:
                return {"avg_rss": 0, "avg_vms": 0, "avg_percent": 0, "sample_count": 0}

            return {
                "avg_rss": sum(s["rss"] for s in recent_samples) / len(recent_samples),
                "avg_vms": sum(s["vms"] for s in recent_samples) / len(recent_samples),
                "avg_percent": sum(s["percent"] for s in recent_samples)
                / len(recent_samples),
                "sample_count": len(recent_samples),
                "max_rss": max(s["rss"] for s in recent_samples),
                "min_rss": min(s["rss"] for s in recent_samples),
            }


# 通用性能分析器
class PerformanceProfiler:
    """通用性能分析器."""

    def __init__(self):
        self.api_profiler = APIEndpointProfiler()
        self.db_profiler = DatabaseQueryProfiler()
        self.memory_profiler = MemoryProfiler()
        self.system_profiler = SystemProfiler()

    def get_comprehensive_report(self) -> dict[str, Any]:
        """获取综合性能报告."""
        return {
            "api_stats": self.api_profiler.get_summary_report(),
            "db_stats": self.db_profiler.get_all_stats(),
            "memory_trend": self.memory_profiler.get_memory_trend(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def enable_all(self):
        """启用所有分析器."""
        self.api_profiler.enable()
        self.db_profiler.enabled = True
        self.memory_profiler.enabled = True

    def disable_all(self):
        """禁用所有分析器."""
        self.api_profiler.disable()
        self.db_profiler.enabled = False
        self.memory_profiler.enabled = False


def get_performance_report() -> dict[str, Any]:
    """获取性能报告的便捷函数."""
    profiler = PerformanceProfiler()
    return profiler.get_comprehensive_report()


# 系统级性能监控
class SystemProfiler:
    """系统性能分析器."""

    def __init__(self):
        self.metrics: dict[str, list[float]] = defaultdict(list)
        self.lock = threading.Lock()

    def record_metric(self, name: str, value: float):
        """记录系统指标."""
        with self.lock:
            self.metrics[name].append(value)
            # 保留最近1000个数据点
            if len(self.metrics[name]) > 1000:
                self.metrics[name] = self.metrics[name][-1000:]

    def get_metric_summary(self, name: str, minutes: int = 5) -> dict[str, float]:
        """获取指标摘要."""
        _cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)

        with self.lock:
            values = self.metrics.get(name, [])
            if not values:
                return {"avg": 0.0, "min": 0.0, "max": 0.0, "count": 0}

            return {
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "count": len(values),
            }


# 全局系统分析器
_system_profiler: SystemProfiler | None = None


def get_system_profiler() -> SystemProfiler:
    """获取系统分析器实例."""
    global _system_profiler
    if _system_profiler is None:
        with _profiler_lock:
            if _system_profiler is None:
                _system_profiler = SystemProfiler()
    return _system_profiler


# 装饰器函数
def profile_function(func: Callable) -> Callable:
    """函数性能分析装饰器."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        profiler = get_profiler()
        return profiler.profile_function(func.__name__)(func)(*args, **kwargs)

    return wrapper


def profile_method(method: Callable) -> Callable:
    """方法性能分析装饰器."""

    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        profiler = get_profiler()
        return profiler.profile_method(method.__name__)(method)(*args, **kwargs)

    return wrapper


# 全局性能控制
_profiling_enabled = False
_profiler_lock = threading.Lock()


def start_profiling():
    """启动性能分析."""
    global _profiling_enabled
    with _profiler_lock:
        _profiling_enabled = True
        profiler = get_profiler()
        profiler.enabled = True


def stop_profiling():
    """停止性能分析."""
    global _profiling_enabled
    with _profiler_lock:
        _profiling_enabled = False
        profiler = get_profiler()
        profiler.enabled = False


def is_profiling_enabled() -> bool:
    """检查是否启用性能分析."""
    return _profiling_enabled


# 导出的公共接口
__all__ = [
    "ProfileStats",
    "APIEndpointProfiler",
    "DatabaseQueryProfiler",
    "MemoryProfiler",
    "PerformanceProfiler",
    "SystemProfiler",
    "get_profiler",
    "profile_api_endpoint",
    "profile_function",
    "profile_method",
    "start_profiling",
    "stop_profiling",
    "is_profiling_enabled",
    "get_system_profiler",
    "get_performance_report",
]
