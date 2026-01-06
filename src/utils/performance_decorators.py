#!/usr/bin/env python3
"""
性能监控装饰器 - Sprint 4 核心组件

提供函数执行时间监控、内存使用监控和性能统计。
专门用于大规模数据处理的性能分析。

设计原则:
- Non-intrusive Monitoring (非侵入式监控)
- Performance Analytics (性能分析)
- Memory Tracking (内存跟踪)
- Statistical Analysis (统计分析)
"""

import asyncio
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
import functools
import gc
import logging
import threading
import time
from typing import Any

import pandas as pd
import psutil

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""

    function_name: str
    execution_time_seconds: float
    memory_start_mb: float
    memory_peak_mb: float
    memory_end_mb: float
    cpu_percent: float
    gc_collections: int
    call_count: int = 1
    avg_time_seconds: float = 0.0
    total_time_seconds: float = 0.0
    last_called: datetime = field(default_factory=datetime.now)


class PerformanceMonitor:
    """全局性能监控器"""

    def __init__(self):
        self._metrics: dict[str, PerformanceMetrics] = {}
        self._lock = threading.Lock()
        self._process = psutil.Process()

    def get_metrics(self, function_name: str) -> PerformanceMetrics | None:
        """获取函数性能指标"""
        with self._lock:
            return self._metrics.get(function_name)

    def get_all_metrics(self) -> dict[str, PerformanceMetrics]:
        """获取所有性能指标"""
        with self._lock:
            return self._metrics.copy()

    def update_metrics(self, function_name: str, metrics: PerformanceMetrics) -> None:
        """更新性能指标"""
        with self._lock:
            if function_name in self._metrics:
                existing = self._metrics[function_name]
                existing.call_count += 1
                existing.total_time_seconds += metrics.execution_time_seconds
                existing.avg_time_seconds = existing.total_time_seconds / existing.call_count
                existing.memory_peak_mb = max(existing.memory_peak_mb, metrics.memory_peak_mb)
                existing.last_called = metrics.last_called
            else:
                self._metrics[function_name] = metrics

    def reset_metrics(self, function_name: str | None = None) -> None:
        """重置性能指标"""
        with self._lock:
            if function_name:
                self._metrics.pop(function_name, None)
            else:
                self._metrics.clear()

    def get_performance_summary(self) -> dict[str, Any]:
        """获取性能摘要"""
        with self._lock:
            if not self._metrics:
                return {"status": "no_data"}

            summary = {"total_functions": len(self._metrics), "functions": {}}

            for name, metrics in self._metrics.items():
                summary["functions"][name] = {
                    "call_count": metrics.call_count,
                    "avg_time_ms": metrics.avg_time_seconds * 1000,
                    "total_time_ms": metrics.total_time_seconds * 1000,
                    "peak_memory_mb": metrics.memory_peak_mb,
                    "last_called": metrics.last_called.isoformat(),
                }

            return summary


# 全局监控器实例
_global_monitor = PerformanceMonitor()


def monitor_performance(
    log_calls: bool = True,
    track_memory: bool = True,
    track_gc: bool = True,
    min_execution_time_ms: float = 100.0,
):
    """
    性能监控装饰器

    Args:
        log_calls: 是否记录调用日志
        track_memory: 是否跟踪内存使用
        track_gc: 是否跟踪垃圾回收
        min_execution_time_ms: 最小执行时间阈值(ms)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await _monitor_function_execution(
                func,
                args,
                kwargs,
                log_calls,
                track_memory,
                track_gc,
                min_execution_time_ms,
                is_async=True,
            )

        # 根据函数是否为协程函数返回合适的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        # 对于同步函数，返回包装后的异步版本
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(
                _monitor_function_execution(
                    func,
                    args,
                    kwargs,
                    log_calls,
                    track_memory,
                    track_gc,
                    min_execution_time_ms,
                    is_async=False,
                )
            )

        return sync_wrapper

    return decorator


async def _monitor_function_execution(
    func: Callable,
    args: tuple,
    kwargs: dict,
    log_calls: bool,
    track_memory: bool,
    track_gc: bool,
    min_execution_time_ms: float,
    is_async: bool,
) -> Any:
    """执行函数监控的核心逻辑"""
    function_name = f"{func.__module__}.{func.__name__}"

    # 记录初始状态
    start_time = time.time()
    process = psutil.Process()

    if track_memory:
        memory_start = process.memory_info().rss / 1024 / 1024  # MB
    else:
        memory_start = 0.0

    if track_gc:
        gc_start = gc.collect()
    else:
        gc_start = 0

    memory_peak = memory_start
    cpu_start = process.cpu_percent()

    try:
        # 执行函数
        if is_async:
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)

        return result

    finally:
        # 记录结束状态
        end_time = time.time()
        execution_time = end_time - start_time

        if track_memory:
            memory_end = process.memory_info().rss / 1024 / 1024
            memory_peak = max(memory_peak, memory_end)
        else:
            memory_end = 0.0

        if track_gc:
            gc_end = gc.collect()
        else:
            gc_end = 0

        cpu_percent = process.cpu_percent()

        # 创建性能指标
        metrics = PerformanceMetrics(
            function_name=function_name,
            execution_time_seconds=execution_time,
            memory_start_mb=memory_start,
            memory_peak_mb=memory_peak,
            memory_end_mb=memory_end,
            cpu_percent=cpu_percent,
            gc_collections=abs(gc_end - gc_start),
            last_called=datetime.now(),
        )

        # 更新全局监控器
        _global_monitor.update_metrics(function_name, metrics)

        # 日志记录
        execution_time_ms = execution_time * 1000
        if log_calls and execution_time_ms >= min_execution_time_ms:
            logger.info(
                f"[PERF] {function_name} 执行完成:\n"
                f"  耗时: {execution_time_ms:.1f}ms\n"
                f"  内存: {memory_start:.1f}MB -> {memory_end:.1f}MB (峰值: {memory_peak:.1f}MB)\n"
                f"  CPU: {cpu_percent:.1f}%\n"
                f"  GC: {metrics.gc_collections} 次"
            )

        # 性能警告
        if execution_time_ms > 5000:  # 5秒警告阈值
            logger.warning(f"[PERF WARNING] {function_name} 执行时间过长: {execution_time_ms:.1f}ms")

        if track_memory and memory_peak > 1024:  # 1GB内存警告阈值
            logger.warning(f"[PERF WARNING] {function_name} 内存使用过高: {memory_peak:.1f}MB")

    # 注意：finally块中的return语句不会影响函数的返回值
    # 这里只是为了监控，实际的返回值在try块中已经返回


def monitor_dataframe_operations(min_rows: int = 1000):
    """
    DataFrame操作性能监控装饰器

    Args:
        min_rows: 最小行数阈值，低于此值不记录
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 检查是否有DataFrame参数
            df_info = _extract_dataframe_info(args, kwargs)

            if not df_info or df_info["rows"] < min_rows:
                return func(*args, **kwargs)

            function_name = f"{func.__module__}.{func.__name__}"
            start_time = time.time()

            result = func(*args, **kwargs)

            execution_time = time.time() - start_time
            rows = df_info["rows"]
            cols = df_info["columns"]
            rows_per_sec = rows / execution_time if execution_time > 0 else 0

            logger.info(
                f"[DF PERF] {function_name} DataFrame操作:\n"
                f"  数据量: {rows:,} 行 x {cols} 列\n"
                f"  耗时: {execution_time * 1000:.1f}ms\n"
                f"  处理速度: {rows_per_sec:.0f} 行/秒"
            )

            return result

        return wrapper

    return decorator


def monitor_memory_usage(threshold_mb: float = 100.0):
    """
    内存使用监控装饰器

    Args:
        threshold_mb: 内存使用阈值(MB)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            function_name = f"{func.__module__}.{func.__name__}"

            # 记录内存使用
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024

            try:
                result = func(*args, **kwargs)

                memory_after = process.memory_info().rss / 1024 / 1024
                memory_delta = memory_after - memory_before

                if abs(memory_delta) >= threshold_mb:
                    logger.info(
                        f"[MEMORY] {function_name} 内存变化: "
                        f"{memory_delta:+.1f}MB ({memory_before:.1f}MB -> {memory_after:.1f}MB)"
                    )

                return result

            finally:
                # 强制垃圾回收以释放内存
                gc.collect()

        return wrapper

    return decorator


@contextmanager
def performance_context(operation_name: str):
    """
    性能监控上下文管理器

    Args:
        operation_name: 操作名称
    """
    start_time = time.time()
    process = psutil.Process()
    memory_start = process.memory_info().rss / 1024 / 1024

    try:
        yield
    finally:
        execution_time = time.time() - start_time
        memory_end = process.memory_info().rss / 1024 / 1024
        memory_delta = memory_end - memory_start

        logger.info(
            f"[PERF CTX] {operation_name}:\n  耗时: {execution_time * 1000:.1f}ms\n  内存变化: {memory_delta:+.1f}MB"
        )


def _extract_dataframe_info(args: tuple, kwargs: dict) -> dict[str, Any] | None:
    """从参数中提取DataFrame信息"""
    # 检查位置参数
    for arg in args:
        if isinstance(arg, pd.DataFrame):
            return {
                "rows": len(arg),
                "columns": len(arg.columns),
                "memory_mb": arg.memory_usage(deep=True).sum() / 1024 / 1024,
            }

    # 检查关键字参数
    for value in kwargs.values():
        if isinstance(value, pd.DataFrame):
            return {
                "rows": len(value),
                "columns": len(value.columns),
                "memory_mb": value.memory_usage(deep=True).sum() / 1024 / 1024,
            }

    return None


# 便捷函数
def get_performance_stats() -> dict[str, Any]:
    """获取性能统计"""
    return _global_monitor.get_performance_summary()


def reset_performance_stats(function_name: str | None = None) -> None:
    """重置性能统计"""
    _global_monitor.reset_metrics(function_name)


def log_slow_functions(min_time_ms: float = 1000.0) -> None:
    """记录慢函数"""
    metrics = _global_monitor.get_all_metrics()

    slow_functions = [
        (name, metrics) for name, metrics in metrics.items() if metrics.avg_time_seconds * 1000 >= min_time_ms
    ]

    if slow_functions:
        logger.info("🐌 慢函数统计:")
        for name, metric in slow_functions:
            logger.info(
                f"  {name}: {metric.avg_time_seconds * 1000:.1f}ms "
                f"(调用 {metric.call_count} 次, 峰值内存 {metric.memory_peak_mb:.1f}MB)"
            )


def log_memory_intensive_functions(threshold_mb: float = 100.0) -> None:
    """记录内存密集函数"""
    metrics = _global_monitor.get_all_metrics()

    memory_intensive = [(name, metrics) for name, metrics in metrics.items() if metrics.memory_peak_mb >= threshold_mb]

    if memory_intensive:
        logger.info("💾 内存密集函数统计:")
        for name, metric in memory_intensive:
            logger.info(
                f"  {name}: {metric.memory_peak_mb:.1f}MB "
                f"(调用 {metric.call_count} 次, 平均耗时 {metric.avg_time_seconds * 1000:.1f}ms)"
            )
