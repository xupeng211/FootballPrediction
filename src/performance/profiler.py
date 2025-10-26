"""
性能分析器模块
Performance Profiler Module

提供多种性能分析工具：
- 函数级性能分析
- 内存使用分析
- 数据库查询分析
- API端点性能跟踪
- 异步任务性能分析
"""

import asyncio
import cProfile
import io
import json
import pstats
import time
import tracemalloc
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import psutil

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetric:
    """性能指标数据结构"""

    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FunctionProfile:
    """函数性能分析结果"""

    function_name: str
    call_count: int
    total_time: float
    average_time: float
    min_time: float
    max_time: float
    cpu_time: float
    memory_usage: int = 0


@dataclass
class QueryProfile:
    """数据库查询性能分析结果"""

    query: str
    execution_time: float
    rows_affected: int
    index_used: Optional[str] = None
    explain_plan: Optional[Dict] = None


class PerformanceProfiler:
    """性能分析器主类"""

    def __init__(self):
        """初始化性能分析器"""
        self.metrics: List[PerformanceMetric] = []
        self.function_profiles: Dict[str, FunctionProfile] = {}
        self.query_profiles: List[QueryProfile] = []
        self.active_profiling = False
        self.profiler = cProfile.Profile()

    def start_profiling(self):
        """开始性能分析"""
        self.active_profiling = True
        self.profiler.enable()
        tracemalloc.start()
        logger.info("Performance profiling started")

    def stop_profiling(self) -> Dict[str, Any]:
        """停止性能分析并返回结果"""
        self.profiler.disable()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # 获取统计信息
        stats_stream = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=stats_stream)
        ps.sort_stats("cumulative")
        ps.print_stats(20)

        self.active_profiling = False

        result = {
            "stats": stats_stream.getvalue(),
            "memory_current": current,
            "memory_peak": peak,
            "function_profiles": self._parse_function_stats(ps),
        }

        logger.info(
            f"Performance profiling completed. Peak memory: {peak / 1024 / 1024:.2f} MB"
        )
        return result

    def _parse_function_stats(self, ps: pstats.Stats) -> List[FunctionProfile]:
        """解析函数统计信息"""
        profiles = []
        stats_dict = ps.stats

        for func_info, (cc, nc, tt, ct, callers) in stats_dict.items():
            filename, line, func_name = func_info
            if not filename.startswith("<") and "/site-packages/" not in filename:
                profile = FunctionProfile(
                    function_name=func_name,
                    call_count=cc,
                    total_time=tt,
                    average_time=tt / cc if cc > 0 else 0,
                    min_time=0,  # pstats doesn't provide min_time directly
                    max_time=0,  # pstats doesn't provide max_time directly
                    cpu_time=tt,
                )
                profiles.append(profile)

        return sorted(profiles, key=lambda x: x.total_time, reverse=True)

    @contextmanager
    def profile_function(self, name: Optional[str] = None):
        """函数性能分析上下文管理器"""
        start_time = time.perf_counter()
        start_memory = psutil.Process().memory_info().rss

        try:
            yield
        finally:
            end_time = time.perf_counter()
            end_memory = psutil.Process().memory_info().rss

            execution_time = end_time - start_time
            memory_delta = end_memory - start_memory

            func_name = name or "anonymous_function"

            # 记录指标
            metric = PerformanceMetric(
                name=f"function_duration_{func_name}",
                value=execution_time,
                unit="seconds",
            )
            self.metrics.append(metric)

            memory_metric = PerformanceMetric(
                name=f"function_memory_{func_name}", value=memory_delta, unit="bytes"
            )
            self.metrics.append(memory_metric)

            logger.debug(
                f"Function {func_name}: {execution_time:.4f}s, Memory: {memory_delta / 1024:.2f}KB"
            )

    @asynccontextmanager
    async def profile_async_function(self, name: Optional[str] = None):
        """异步函数性能分析上下文管理器"""
        start_time = time.perf_counter()
        start_memory = psutil.Process().memory_info().rss

        try:
            yield
        finally:
            end_time = time.perf_counter()
            end_memory = psutil.Process().memory_info().rss

            execution_time = end_time - start_time
            end_memory - start_memory

            func_name = name or "async_anonymous_function"

            # 记录指标
            metric = PerformanceMetric(
                name=f"async_function_duration_{func_name}",
                value=execution_time,
                unit="seconds",
            )
            self.metrics.append(metric)

            logger.debug(f"Async function {func_name}: {execution_time:.4f}s")

    def record_query_profile(
        self,
        query: str,
        execution_time: float,
        rows_affected: int = 0,
        index_used: Optional[str] = None,
        explain_plan: Optional[Dict] = None,
    ):
        """记录数据库查询性能"""
        profile = QueryProfile(
            query=query,
            execution_time=execution_time,
            rows_affected=rows_affected,
            index_used=index_used,
            explain_plan=explain_plan,
        )
        self.query_profiles.append(profile)

        # 记录指标
        metric = PerformanceMetric(
            name="database_query_duration",
            value=execution_time,
            unit="seconds",
            metadata={"query": query[:100], "rows": rows_affected},
        )
        self.metrics.append(metric)

    def get_slow_functions(self, threshold: float = 0.1) -> List[FunctionProfile]:
        """获取慢函数列表"""
        return [
            f for f in self.function_profiles.values() if f.average_time > threshold
        ]

    def get_slow_queries(self, threshold: float = 0.5) -> List[QueryProfile]:
        """获取慢查询列表"""
        return [q for q in self.query_profiles if q.execution_time > threshold]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取性能指标摘要"""
        if not self.metrics:
            return {}

        # 按名称分组指标
        grouped_metrics = {}
        for metric in self.metrics:
            if metric.name not in grouped_metrics:
                grouped_metrics[metric.name] = []
            grouped_metrics[metric.name].append(metric.value)

        # 计算统计信息
        summary = {}
        for name, values in grouped_metrics.items():
            summary[name] = {
                "count": len(values),
                "total": sum(values),
                "average": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
            }

        return summary

    def export_metrics(self, format: str = "json") -> str:
        """导出性能指标"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "metrics_summary": self.get_metrics_summary(),
            "slow_functions": [
                {
                    "name": f.function_name,
                    "average_time": f.average_time,
                    "call_count": f.call_count,
                }
                for f in self.get_slow_functions()
            ],
            "slow_queries": [
                {
                    "query": q.query[:100] + "..." if len(q.query) > 100 else q.query,
                    "execution_time": q.execution_time,
                    "rows_affected": q.rows_affected,
                }
                for q in self.get_slow_queries()
            ],
        }

        if format == "json":
            return json.dumps(data, indent=2)
        else:
            return str(data)

    def reset(self):
        """重置所有性能数据"""
        self.metrics.clear()
        self.function_profiles.clear()
        self.query_profiles.clear()
        self.profiler = cProfile.Profile()
        logger.info("Performance profiler reset")


# 全局性能分析器实例
_global_profiler = PerformanceProfiler()


def get_profiler() -> PerformanceProfiler:
    """获取全局性能分析器实例"""
    return _global_profiler


def profile_function(name: Optional[str] = None):
    """函数性能分析装饰器"""

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                async with _global_profiler.profile_async_function(
                    name or func.__name__
                ):
                    return await func(*args, **kwargs)

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with _global_profiler.profile_function(name or func.__name__):
                    return func(*args, **kwargs)

            return sync_wrapper

    return decorator


def profile_method(cls_attr: Optional[str] = None):
    """方法性能分析装饰器（用于类方法）"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取类名
            if args and hasattr(args[0], "__class__"):
                class_name = args[0].__class__.__name__
                func_name = f"{class_name}.{func.__name__}"
            else:
                func_name = func.__name__

            with _global_profiler.profile_function(func_name):
                return func(*args, **kwargs)

        return wrapper

    return decorator


class DatabaseQueryProfiler:
    """数据库查询性能分析器"""

    def __init__(self, profiler: PerformanceProfiler):
        self.profiler = profiler

    def profile_query(self, query: str, execute_func: Callable) -> Any:
        """分析数据库查询性能"""
        start_time = time.perf_counter()

        try:
            result = execute_func(query)

            # 尝试获取影响行数
            rows_affected = 0
            if hasattr(result, "rowcount"):
                rows_affected = result.rowcount
            elif isinstance(result, list):
                rows_affected = len(result)

            execution_time = time.perf_counter() - start_time

            # 记录查询性能
            self.profiler.record_query_profile(
                query=query, execution_time=execution_time, rows_affected=rows_affected
            )

            return result

        except (ValueError, RuntimeError, TimeoutError) as e:
            execution_time = time.perf_counter() - start_time

            # 记录失败的查询
            self.profiler.record_query_profile(
                query=query, execution_time=execution_time, rows_affected=0
            )

            logger.error(f"Query failed after {execution_time:.4f}s: {str(e)}")
            raise


class APIEndpointProfiler:
    """API端点性能分析器"""

    def __init__(self, profiler: PerformanceProfiler):
        self.profiler = profiler
        self.endpoint_stats: Dict[str, Dict] = {}

    def record_endpoint_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration: float,
        request_size: int = 0,
        response_size: int = 0,
    ):
        """记录API端点请求性能"""
        key = f"{method} {endpoint}"

        if key not in self.endpoint_stats:
            self.endpoint_stats[key] = {
                "request_count": 0,
                "total_duration": 0,
                "status_codes": {},
                "avg_request_size": 0,
                "avg_response_size": 0,
                "min_duration": float("inf"),
                "max_duration": 0,
            }

        stats = self.endpoint_stats[key]
        stats["request_count"] += 1
        stats["total_duration"] += duration
        stats["min_duration"] = min(stats["min_duration"], duration)
        stats["max_duration"] = max(stats["max_duration"], duration)

        # 状态码统计
        if status_code not in stats["status_codes"]:
            stats["status_codes"][status_code] = 0
        stats["status_codes"][status_code] += 1

        # 更新平均大小
        stats["avg_request_size"] = (
            stats["avg_request_size"] * (stats["request_count"] - 1) + request_size
        ) / stats["request_count"]
        stats["avg_response_size"] = (
            stats["avg_response_size"] * (stats["request_count"] - 1) + response_size
        ) / stats["request_count"]

        # 记录指标
        metric = PerformanceMetric(
            name=f"api_endpoint_duration_{key}",
            value=duration,
            unit="seconds",
            metadata={
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
            },
        )
        self.profiler.metrics.append(metric)

    def get_endpoint_stats(self) -> Dict[str, Dict]:
        """获取端点性能统计"""
        # 计算平均持续时间
        for stats in self.endpoint_stats.values():
            if stats["request_count"] > 0:
                stats["average_duration"] = (
                    stats["total_duration"] / stats["request_count"]
                )
            else:
                stats["average_duration"] = 0

        return self.endpoint_stats

    def get_slow_endpoints(self, threshold: float = 1.0) -> List[Dict]:
        """获取慢端点列表"""
        slow_endpoints = []

        for endpoint, stats in self.get_endpoint_stats().items():
            if stats["average_duration"] > threshold:
                slow_endpoints.append(
                    {
                        "endpoint": endpoint,
                        "average_duration": stats["average_duration"],
                        "request_count": stats["request_count"],
                        "max_duration": stats["max_duration"],
                    }
                )

        return sorted(slow_endpoints, key=lambda x: x["average_duration"], reverse=True)


class MemoryProfiler:
    """内存使用分析器"""

    def __init__(self):
        self.snapshots: List[Dict] = []

    def take_snapshot(self, label: str = ""):
        """获取内存快照"""
        process = psutil.Process()
        memory_info = process.memory_info()

        snapshot = {
            "timestamp": datetime.now(),
            "label": label,
            "rss": memory_info.rss,  # 物理内存
            "vms": memory_info.vms,  # 虚拟内存
            "percent": process.memory_percent(),
            "available": psutil.virtual_memory().available,
        }

        self.snapshots.append(snapshot)
        return snapshot

    def get_memory_trend(self) -> Dict[str, List]:
        """获取内存使用趋势"""
        if not self.snapshots:
            return {}

        return {
            "timestamps": [s["timestamp"].isoformat() for s in self.snapshots],
            "rss": [s["rss"] / 1024 / 1024 for s in self.snapshots],  # MB
            "vms": [s["vms"] / 1024 / 1024 for s in self.snapshots],  # MB
            "percent": [s["percent"] for s in self.snapshots],
            "labels": [s["label"] for s in self.snapshots],
        }

    def detect_memory_leaks(self, threshold: float = 50.0) -> bool:
        """检测内存泄漏（MB）"""
        if len(self.snapshots) < 2:
            return False

        first_rss = self.snapshots[0]["rss"] / 1024 / 1024
        last_rss = self.snapshots[-1]["rss"] / 1024 / 1024

        return (last_rss - first_rss) > threshold


# 创建性能分析器的便捷函数
def start_profiling():
    """开始全局性能分析"""
    _global_profiler.start_profiling()


def stop_profiling() -> Dict[str, Any]:
    """停止全局性能分析"""
    return _global_profiler.stop_profiling()


def get_performance_report() -> str:
    """获取性能报告"""
    return _global_profiler.export_metrics()
