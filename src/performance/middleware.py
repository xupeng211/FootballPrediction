"""
性能监控中间件 - 简化版本
"""

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class PerformanceMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""

    def __init__(self, app, dispatch: Callable = None):
        super().__init__(app, dispatch)
        self.request_times = []
        self.active_requests = {}
        self.max_concurrent_requests = 0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并记录性能指标"""
        start_time = time.perf_counter()
        request_id = id(request)

        # 记录请求开始
        self.active_requests[request_id] = start_time
        current_concurrent = len(self.active_requests)
        self.max_concurrent_requests = max(
            self.max_concurrent_requests, current_concurrent
        )

        try:
            # 获取请求大小
            try:
                body = await request.body()
                len(body)
            except (ValueError, RuntimeError, TimeoutError):
                pass

            # 执行请求
            response = await call_next(request)

            # 计算响应时间
            end_time = time.perf_counter()
            duration = end_time - start_time

            # 记录响应大小
            try:
                len(response.body) if hasattr(response, "body") else 0
            except (ValueError, RuntimeError, TimeoutError):
                pass

            # 记录性能数据
            self.request_times.append(duration)
            if len(self.request_times) > 1000:
                self.request_times = self.request_times[-1000:]

            # 添加性能头部
            response.headers["X-Process-Time"] = f"{duration:.4f}"
            response.headers["X-Concurrent-Requests"] = str(current_concurrent)

            return response

        finally:
            # 清理活动请求记录
            self.active_requests.pop(request_id, None)

    def get_performance_stats(self) -> dict:
        """获取性能统计信息"""
        if not self.request_times:
            return {
                "avg_response_time": 0,
                "max_concurrent_requests": self.max_concurrent_requests,
                "current_concurrent": len(self.active_requests),
                "total_requests": 0,
            }

        return {
            "avg_response_time": sum(self.request_times) / len(self.request_times),
            "max_response_time": max(self.request_times),
            "min_response_time": min(self.request_times),
            "max_concurrent_requests": self.max_concurrent_requests,
            "current_concurrent": len(self.active_requests),
            "total_requests": len(self.request_times),
        }


class BackgroundTaskPerformanceMonitor:
    """后台任务性能监控器"""

    def __init__(self):
        self.task_stats = {}

    def start_task(self, task_name: str):
        """开始任务监控"""
        self.task_stats[task_name] = {"start_time": time.time()}

    def end_task(self, task_name: str):
        """结束任务监控"""
        if task_name in self.task_stats:
            self.task_stats[task_name]["end_time"] = time.time()

    def get_stats(self) -> dict:
        """获取任务统计"""
        return self.task_stats


class CachePerformanceMiddleware:
    """缓存性能中间件"""

    def __init__(self):
        self.cache_hits = 0
        self.cache_misses = 0

    def record_hit(self):
        """记录缓存命中"""
        self.cache_hits += 1

    def record_miss(self):
        """记录缓存未命中"""
        self.cache_misses += 1

    def get_hit_rate(self) -> float:
        """获取缓存命中率"""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0


class DatabasePerformanceMiddleware:
    """数据库性能中间件"""

    def __init__(self):
        self.query_times = []
        self.slow_queries = []

    def record_query(self, duration: float, query: str = ""):
        """记录查询性能"""
        self.query_times.append(duration)
        if duration > 0.1:  # 慢查询阈值
            self.slow_queries.append({"duration": duration, "query": query})

    def get_avg_query_time(self) -> float:
        """获取平均查询时间"""
        return (
            sum(self.query_times) / len(self.query_times) if self.query_times else 0.0
        )


# 为了向后兼容，提供别名
PerformanceMonitoringMiddleware = PerformanceMiddleware
