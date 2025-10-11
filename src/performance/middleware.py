"""
性能监控中间件
Performance Monitoring Middleware

提供FastAPI应用的性能监控：
- 请求响应时间跟踪
- 内存使用监控
- 并发请求统计
- 错误率监控
- 端点性能分析
"""

import time
from typing import Callable, Dict, List, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.performance.profiler import get_profiler, APIEndpointProfiler
from src.core.logging import get_logger

logger = get_logger(__name__)


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""

    def __init__(
        self,
        app,
        track_memory: bool = True,
        track_concurrency: bool = True,
        sample_rate: float = 1.0,
    ):
        """
        初始化性能监控中间件

        Args:
            app: FastAPI应用实例
            track_memory: 是否跟踪内存使用
            track_concurrency: 是否跟踪并发请求
            sample_rate: 采样率（0-1），1.0表示100%采样
        """
        super().__init__(app)
        self.track_memory = track_memory
        self.track_concurrency = track_concurrency
        self.sample_rate = sample_rate

        # 初始化组件
        self.profiler = get_profiler()
        self.api_profiler = APIEndpointProfiler(self.profiler)

        # 并发请求跟踪
        self.active_requests: Dict[str, float] = {}
        self.max_concurrent_requests = 0
        self.total_requests = 0
        self.request_times: List[float] = []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并收集性能指标"""
        # 采样检查
        import random

        if random.random() > self.sample_rate:
            return await call_next(request)  # type: ignore

        # 生成请求ID
        request_id = f"{request.method}_{hash(str(request.url))}_{time.time()}"

        # 记录请求开始
        start_time = time.perf_counter()
        start_memory = None

        if self.track_memory:
            import psutil

            process = psutil.Process()
            start_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 跟踪并发请求
        if self.track_concurrency:
            self.active_requests[request_id] = start_time
            current_concurrent = len(self.active_requests)
            if current_concurrent > self.max_concurrent_requests:
                self.max_concurrent_requests = current_concurrent

        # 获取请求大小
        request_size = 0
        try:
            body = await request.body()
            request_size = len(body)
        except (ValueError, RuntimeError, TimeoutError):
            pass

        try:
            # 执行请求
            response = await call_next(request)

            # 计算响应时间
            end_time = time.perf_counter()
            duration = end_time - start_time

            # 记录响应大小
            response_size = 0
            if hasattr(response, "body"):
                try:
                    response_size = len(response.body)
                except (ValueError, RuntimeError, TimeoutError):
                    pass

            # 记录端点性能
            self.api_profiler.record_endpoint_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration=duration,
                request_size=request_size,
                response_size=response_size,
            )

            # 更新统计
            self.total_requests += 1
            self.request_times.append(duration)
            # 保留最近1000个请求的时间
            if len(self.request_times) > 1000:
                self.request_times = self.request_times[-1000:]

            # 添加性能头部
            response.headers["X-Process-Time"] = f"{duration:.4f}"
            response.headers["X-Request-ID"] = request_id

            if self.track_memory and start_memory:
                import psutil

                process = psutil.Process()
                end_memory = process.memory_info().rss / 1024 / 1024
                memory_delta = end_memory - start_memory
                response.headers["X-Memory-Delta"] = f"{memory_delta:.2f}MB"

            # 记录慢请求
            if duration > 1.0:  # 超过1秒的请求
                logger.warning(
                    f"Slow request detected: {request.method} {request.url.path} "
                    f"took {duration:.4f}s"
                )

            # 记录错误请求
            if response.status_code >= 400:
                logger.warning(
                    f"Error request: {request.method} {request.url.path} "
                    f"returned {response.status_code} in {duration:.4f}s"
                )

            return response  # type: ignore

        except (ValueError, RuntimeError, TimeoutError) as e:
            # 记录异常
            end_time = time.perf_counter()
            duration = end_time - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"after {duration:.4f}s - {str(e)}"
            )
            raise

        finally:
            # 清理并发请求跟踪
            if self.track_concurrency and request_id in self.active_requests:
                del self.active_requests[request_id]

    def get_performance_stats(self) -> Dict:
        """获取性能统计信息"""
        stats = {
            "total_requests": self.total_requests,
            "current_concurrent_requests": len(self.active_requests),
            "max_concurrent_requests": self.max_concurrent_requests,
            "endpoint_stats": self.api_profiler.get_endpoint_stats(),
        }

        # 计算响应时间统计
        if self.request_times:
            stats["response_time"] = {
                "average": sum(self.request_times) / len(self.request_times),
                "min": min(self.request_times),
                "max": max(self.request_times),
                "p50": self._percentile(self.request_times, 50),
                "p95": self._percentile(self.request_times, 95),
                "p99": self._percentile(self.request_times, 99),
            }

        # 获取慢端点
        slow_endpoints = self.api_profiler.get_slow_endpoints(threshold=0.5)
        stats["slow_endpoints"] = slow_endpoints[:10]  # 前10个最慢的端点

        return stats

    def _percentile(self, data: List[float], percentile: float) -> float:
        """计算百分位数"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def reset_stats(self):
        """重置统计信息"""
        self.total_requests = 0
        self.max_concurrent_requests = 0
        self.request_times.clear()
        self.api_profiler.endpoint_stats.clear()


class DatabasePerformanceMiddleware:
    """数据库性能监控中间件"""

    def __init__(self):
        self.query_stats: Dict[str, Dict] = {}
        self.slow_queries: List[Dict] = []
        self.total_queries = 0

    async def track_query(
        self,
        query: str,
        duration: float,
        rows_affected: int = 0,
        error: Optional[str] = None,
    ):
        """跟踪数据库查询性能"""
        self.total_queries += 1

        # 提取查询类型
        query_type = query.strip().split()[0].upper() if query else "UNKNOWN"

        if query_type not in self.query_stats:
            self.query_stats[query_type] = {
                "count": 0,
                "total_time": 0,
                "rows_total": 0,
                "error_count": 0,
            }

        stats = self.query_stats[query_type]
        stats["count"] += 1
        stats["total_time"] += duration
        stats["rows_total"] += rows_affected

        if error:
            stats["error_count"] += 1

        # 记录慢查询（超过100ms）
        if duration > 0.1:
            self.slow_queries.append(
                {
                    "query": query[:200] + "..." if len(query) > 200 else query,
                    "duration": duration,
                    "rows_affected": rows_affected,
                    "timestamp": time.time(),
                }
            )

            # 保留最近100个慢查询
            if len(self.slow_queries) > 100:
                self.slow_queries = self.slow_queries[-100:]

    def get_query_stats(self) -> Dict:
        """获取查询统计信息"""
        stats = {"total_queries": self.total_queries, "query_types": {}}

        for query_type, data in self.query_stats.items():
            stats["query_types"][query_type] = {
                "count": data["count"],
                "average_time": data["total_time"] / data["count"]
                if data["count"] > 0
                else 0,
                "total_time": data["total_time"],
                "rows_total": data["rows_total"],
                "error_rate": data["error_count"] / data["count"]
                if data["count"] > 0
                else 0,
            }

        stats["slow_queries"] = self.slow_queries[-10:]  # 最近10个慢查询

        return stats


class CachePerformanceMiddleware:
    """缓存性能监控中间件"""

    def __init__(self):
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "hit_times": [],
            "set_times": [],
        }

    def record_cache_hit(self, duration: float):
        """记录缓存命中"""
        self.cache_stats["hits"] += 1
        self.cache_stats["hit_times"].append(duration)
        if len(self.cache_stats["hit_times"]) > 1000:
            self.cache_stats["hit_times"] = self.cache_stats["hit_times"][-1000:]

    def record_cache_miss(self):
        """记录缓存未命中"""
        self.cache_stats["misses"] += 1

    def record_cache_set(self, duration: float):
        """记录缓存设置"""
        self.cache_stats["sets"] += 1
        self.cache_stats["set_times"].append(duration)
        if len(self.cache_stats["set_times"]) > 1000:
            self.cache_stats["set_times"] = self.cache_stats["set_times"][-1000:]

    def record_cache_delete(self):
        """记录缓存删除"""
        self.cache_stats["deletes"] += 1

    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (
            self.cache_stats["hits"] / total_requests if total_requests > 0 else 0
        )

        stats = {
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "hits": self.cache_stats["hits"],
            "misses": self.cache_stats["misses"],
            "sets": self.cache_stats["sets"],
            "deletes": self.cache_stats["deletes"],
        }

        # 计算平均时间
        if self.cache_stats["hit_times"]:
            stats["average_hit_time"] = sum(self.cache_stats["hit_times"]) / len(
                self.cache_stats["hit_times"]
            )
        if self.cache_stats["set_times"]:
            stats["average_set_time"] = sum(self.cache_stats["set_times"]) / len(
                self.cache_stats["set_times"]
            )

        return stats


class BackgroundTaskPerformanceMonitor:
    """后台任务性能监控器"""

    def __init__(self):
        self.task_stats: Dict[str, Dict] = {}
        self.active_tasks: Dict[str, float] = {}
        self.failed_tasks: List[Dict] = []

    def start_task(self, task_id: str, task_name: str):
        """开始任务跟踪"""
        self.active_tasks[task_id] = {"name": task_name, "start_time": time.time()}  # type: ignore

    def end_task(self, task_id: str, success: bool = True, error: Optional[str] = None):
        """结束任务跟踪"""
        if task_id not in self.active_tasks:
            return

        task = self.active_tasks[task_id]
        duration = time.time() - task["start_time"]  # type: ignore
        task_name = task["name"]  # type: ignore

        # 更新任务统计
        if task_name not in self.task_stats:
            self.task_stats[task_name] = {
                "total_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "total_time": 0,
                "min_time": float("inf"),
                "max_time": 0,
            }

        stats = self.task_stats[task_name]
        stats["total_count"] += 1
        stats["total_time"] += duration
        stats["min_time"] = min(stats["min_time"], duration)
        stats["max_time"] = max(stats["max_time"], duration)

        if success:
            stats["success_count"] += 1
        else:
            stats["failure_count"] += 1
            self.failed_tasks.append(
                {
                    "task_id": task_id,
                    "task_name": task_name,
                    "duration": duration,
                    "error": error,
                    "timestamp": time.time(),
                }
            )
            # 保留最近100个失败任务
            if len(self.failed_tasks) > 100:
                self.failed_tasks = self.failed_tasks[-100:]

        del self.active_tasks[task_id]

    def get_task_stats(self) -> Dict:
        """获取任务统计信息"""
        stats = {"active_tasks": len(self.active_tasks), "task_types": {}}

        for task_name, data in self.task_stats.items():
            stats["task_types"][task_name] = {  # type: ignore
                "total_count": data["total_count"],
                "success_count": data["success_count"],
                "failure_count": data["failure_count"],
                "success_rate": data["success_count"] / data["total_count"]
                if data["total_count"] > 0
                else 0,
                "average_time": data["total_time"] / data["total_count"]
                if data["total_count"] > 0
                else 0,
                "min_time": data["min_time"] if data["min_time"] != float("inf") else 0,
                "max_time": data["max_time"],
            }

        stats["recent_failures"] = self.failed_tasks[-10:]

        return stats
