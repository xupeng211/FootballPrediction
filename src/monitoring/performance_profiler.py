#!/usr/bin/env python3
"""
性能分析器
基于高覆盖率的性能监控和分析工具
"""

import asyncio
import functools
import json
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import psutil

try:
    import cProfile
    import pstats

    PROFILE_AVAILABLE = True
except ImportError:
    PROFILE_AVAILABLE = False
    print("Warning: cProfile not available")

from src.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""

    function_name: str
    execution_time: float
    memory_usage: float
    cpu_usage: float
    call_count: int
    timestamp: datetime
    metadata: dict[str, Any] = None


class PerformanceProfiler:
    """性能分析器"""

    def __init__(self):
        self.metrics: list[PerformanceMetrics] = []
        self._lock = threading.Lock()
        self._process = psutil.Process()

    def track_function(
        self,
        func: Callable = None,
        *,
        name: str | None = None,
        track_memory: bool = True,
        track_cpu: bool = True,
    ) -> Callable:
        """
        函数性能跟踪装饰器

        Args:
            func: 被装饰的函数
            name: 函数名称（用于记录）
            track_memory: 是否跟踪内存使用
            track_cpu: 是否跟踪CPU使用

        Returns:
            装饰后的函数
        """

        def decorator(f: Callable) -> Callable:
            func_name = name or f.__name__

            @functools.wraps(f)
            def sync_wrapper(*args, **kwargs):
                return self._measure_execution(
                    f, func_name, args, kwargs, track_memory, track_cpu, sync=True
                )

            @functools.wraps(f)
            async def async_wrapper(*args, **kwargs):
                return self._measure_execution(
                    f, func_name, args, kwargs, track_memory, track_cpu, sync=False
                )

            if asyncio.iscoroutinefunction(f):
                return async_wrapper
            else:
                return sync_wrapper

        if func is None:
            return decorator
        else:
            return decorator(func)

    def _measure_execution(
        self,
        func: Callable,
        name: str,
        args: tuple,
        kwargs: dict,
        track_memory: bool,
        track_cpu: bool,
        sync: bool = True,
    ) -> Any:
        """测量函数执行性能"""
        # 记录初始状态
        start_time = time.time()

        if track_memory:
            initial_memory = self._get_memory_usage()

        if track_cpu:
            initial_cpu = self._process.cpu_percent()

        try:
            # 执行函数
            if sync:
                result = func(*args, **kwargs)
            else:
                result = asyncio.run(func(*args, **kwargs))

        except Exception as e:
            logger.error(f"性能跟踪时函数 {name} 执行失败: {e}")
            raise

        # 记录结束状态
        end_time = time.time()
        execution_time = end_time - start_time

        if track_memory:
            final_memory = self._get_memory_usage()
            memory_usage = final_memory - initial_memory
        else:
            memory_usage = 0.0

        if track_cpu:
            final_cpu = self._process.cpu_percent()
            cpu_usage = final_cpu - initial_cpu if final_cpu > initial_cpu else 0.0
        else:
            cpu_usage = 0.0

        # 记录指标
        metrics = PerformanceMetrics(
            function_name=name,
            execution_time=execution_time,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            call_count=1,
            timestamp=datetime.now(),
            metadata={
                "args_count": len(args),
                "kwargs_count": len(kwargs),
                "is_async": not sync,
            },
        )

        with self._lock:
            self.metrics.append(metrics)

        # 记录慢执行
        if execution_time > 1.0:  # 超过1秒记录警告
            logger.warning(f"慢执行检测: {name} 耗时 {execution_time:.3f} 秒")

        return result

    def _get_memory_usage(self) -> float:
        """获取当前内存使用量（MB）"""
        try:
            return self._process.memory_info().rss / 1024 / 1024
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0

    def get_slow_functions(self, threshold: float = 1.0) -> list[PerformanceMetrics]:
        """获取执行缓慢的函数列表"""
        with self._lock:
            return [m for m in self.metrics if m.execution_time > threshold]

    def get_memory_intensive_functions(
        self, threshold: float = 50.0
    ) -> list[PerformanceMetrics]:
        """获取内存密集的函数列表"""
        with self._lock:
            return [m for m in self.metrics if m.memory_usage > threshold]

    def get_function_stats(self, function_name: str) -> dict[str, Any]:
        """获取特定函数的统计信息"""
        with self._lock:
            func_metrics = [m for m in self.metrics if m.function_name == function_name]

            if not func_metrics:
                return {}

            execution_times = [m.execution_time for m in func_metrics]
            memory_usages = [m.memory_usage for m in func_metrics]

            return {
                "function_name": function_name,
                "call_count": len(func_metrics),
                "avg_execution_time": sum(execution_times) / len(execution_times),
                "min_execution_time": min(execution_times),
                "max_execution_time": max(execution_times),
                "avg_memory_usage": sum(memory_usages) / len(memory_usages),
                "max_memory_usage": max(memory_usages),
                "total_execution_time": sum(execution_times),
                "last_called": max(m.timestamp for m in func_metrics).isoformat(),
            }

    def get_all_stats(self) -> dict[str, Any]:
        """获取所有函数的统计摘要"""
        with self._lock:
            if not self.metrics:
                return {"message": "没有性能数据"}

            function_names = list(set(m.function_name for m in self.metrics))
            all_stats = {}

            for name in function_names:
                all_stats[name] = self.get_function_stats(name)

            # 计算总体统计
            total_calls = len(self.metrics)
            total_time = sum(m.execution_time for m in self.metrics)
            avg_time = total_time / total_calls if total_calls > 0 else 0

            slow_functions = self.get_slow_functions(1.0)
            memory_intensive = self.get_memory_intensive_functions(50.0)

            return {
                "summary": {
                    "total_functions": len(function_names),
                    "total_calls": total_calls,
                    "total_execution_time": total_time,
                    "average_execution_time": avg_time,
                    "slow_functions_count": len(slow_functions),
                    "memory_intensive_count": len(memory_intensive),
                },
                "functions": all_stats,
                "slow_functions": [asdict(s) for s in slow_functions],
                "memory_intensive_functions": [asdict(m) for m in memory_intensive],
            }

    def clear_metrics(self):
        """清空性能指标"""
        with self._lock:
            self.metrics.clear()

    def export_metrics(self, file_path: str):
        """导出性能指标到文件"""
        try:
            stats = self.get_all_stats()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"性能指标已导出到: {file_path}")
        except Exception as e:
            logger.error(f"导出性能指标失败: {e}")


class BenchmarkRunner:
    """基准测试运行器"""

    def __init__(self):
        self.profiler = PerformanceProfiler()

    async def run_api_benchmark(self, iterations: int = 100):
        """运行API基准测试"""
        logger.info(f"开始API基准测试，迭代次数: {iterations}")

        @self.profiler.track_function
        async def simulate_api_call(endpoint: str):
            """模拟API调用"""
            # 模拟不同的响应时间
            await asyncio.sleep(0.01 if endpoint == "/health" else 0.05)
            return {"endpoint": endpoint, "status": "ok"}

        endpoints = [
            "/health",
            "/api/v1/predictions",
            "/api/v1/matches",
            "/api/v1/users/me",
        ]

        for i in range(iterations):
            for endpoint in endpoints:
                await simulate_api_call(endpoint)

        logger.info("API基准测试完成")

    def run_utils_benchmark(self, iterations: int = 1000):
        """运行工具函数基准测试"""
        logger.info(f"开始工具函数基准测试，迭代次数: {iterations}")

        @self.profiler.track_function
        def test_string_operations():
            """测试字符串操作"""
            s = "Hello World"
            for _ in range(10):
                _ = s.upper()
                _ = s.lower()
                _ = s.replace(" ", "_")
                _ = len(s)

        @self.profiler.track_function
        def test_format_operations():
            """测试格式化操作"""
            for i in range(10):
                _ = f"Number: {i:04d}"
                _ = f"Float: {i * 1.234:.2f}"
                _ = f"Percent: {i / 100:.1%}"

        for i in range(iterations // 100):
            test_string_operations()
            test_format_operations()

        logger.info("工具函数基准测试完成")

    def run_benchmark_suite(self):
        """运行完整的基准测试套件"""
        logger.info("开始完整基准测试套件")

        # 同步测试
        self.run_utils_benchmark()

        # 异步测试
        asyncio.run(self.run_api_benchmark())

        # 生成报告
        stats = self.profiler.get_all_stats()

        logger.info("基准测试套件完成")
        return stats


# 全局性能分析器实例
global_profiler = PerformanceProfiler()


def performance_track(name: str | None = None, **kwargs):
    """全局性能跟踪装饰器"""
    return global_profiler.track_function(name=name, **kwargs)


# 便捷函数
def get_performance_stats() -> dict[str, Any]:
    """获取全局性能统计"""
    return global_profiler.get_all_stats()


def export_performance_stats(file_path: str):
    """导出全局性能统计"""
    global_profiler.export_metrics(file_path)


def clear_performance_stats():
    """清空全局性能统计"""
    global_profiler.clear_metrics()


if __name__ == "__main__":
    # 运行基准测试
    runner = BenchmarkRunner()
    stats = runner.run_benchmark_suite()

    # 输出结果
    print("\n=== 性能基准测试结果 ===")
    print(json.dumps(stats, ensure_ascii=False, indent=2, default=str))

    # 导出结果
    export_performance_stats("performance_benchmark_results.json")
