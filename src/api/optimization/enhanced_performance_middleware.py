"""增强性能监控中间件
Enhanced Performance Monitoring Middleware.

提供智能性能监控、自动优化建议和实时性能指标收集。
"""

import asyncio
import logging
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """性能指标收集器."""

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.request_history: deque = deque(maxlen=max_history)
        self.endpoint_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "total_time": 0.0,
                "min_time": float("inf"),
                "max_time": 0.0,
                "error_count": 0,
                "recent_times": deque(maxlen=100),
            }
        )
        self.global_stats = {
            "total_requests": 0,
            "total_time": 0.0,
            "error_count": 0,
            "start_time": time.time(),
        }

    def record_request(
        self,
        method: str,
        url: str,
        status_code: int,
        process_time: float,
        endpoint: str,
    ):
        """记录请求指标."""
        self.global_stats["total_requests"] += 1
        self.global_stats["total_time"] += process_time

        if status_code >= 400:
            self.global_stats["error_count"] += 1

        # 更新端点统计
        stats = self.endpoint_stats[endpoint]
        stats["count"] += 1
        stats["total_time"] += process_time
        stats["min_time"] = min(stats["min_time"], process_time)
        stats["max_time"] = max(stats["max_time"], process_time)
        stats["recent_times"].append(process_time)

        if status_code >= 400:
            stats["error_count"] += 1

        # 记录历史
        self.request_history.append(
            {
                "timestamp": time.time(),
                "method": method,
                "url": url,
                "endpoint": endpoint,
                "status_code": status_code,
                "process_time": process_time,
            }
        )

    def get_endpoint_stats(self, endpoint: str) -> dict[str, Any]:
        """获取端点统计信息."""
        stats = self.endpoint_stats[endpoint]
        if stats["count"] == 0:
            return {}

        recent_times = list(stats["recent_times"])
        recent_times.sort()

        return {
            "endpoint": endpoint,
            "request_count": stats["count"],
            "avg_response_time": stats["total_time"] / stats["count"],
            "min_response_time": stats["min_time"],
            "max_response_time": stats["max_time"],
            "p50_response_time": (
                recent_times[len(recent_times) // 2] if recent_times else 0
            ),
            "p95_response_time": (
                recent_times[int(len(recent_times) * 0.95)] if recent_times else 0
            ),
            "p99_response_time": (
                recent_times[int(len(recent_times) * 0.99)] if recent_times else 0
            ),
            "error_rate": (stats["error_count"] / stats["count"]) * 100,
            "error_count": stats["error_count"],
        }

    def get_global_stats(self) -> dict[str, Any]:
        """获取全局统计信息."""
        uptime = time.time() - self.global_stats["start_time"]
        total_requests = self.global_stats["total_requests"]

        return {
            "total_requests": total_requests,
            "total_errors": self.global_stats["error_count"],
            "error_rate": (
                (self.global_stats["error_count"] / total_requests * 100)
                if total_requests > 0
                else 0
            ),
            "avg_response_time": (
                (self.global_stats["total_time"] / total_requests)
                if total_requests > 0
                else 0
            ),
            "requests_per_second": total_requests / uptime if uptime > 0 else 0,
            "uptime_seconds": uptime,
            "top_slow_endpoints": self._get_slow_endpoints(),
            "top_error_endpoints": self._get_error_endpoints(),
        }

    def _get_slow_endpoints(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取最慢的端点."""
        endpoints = []
        for endpoint, stats in self.endpoint_stats.items():
            if stats["count"] > 0:
                avg_time = stats["total_time"] / stats["count"]
                endpoints.append(
                    {
                        "endpoint": endpoint,
                        "avg_response_time": avg_time,
                        "request_count": stats["count"],
                    }
                )

        return sorted(endpoints, key=lambda x: x["avg_response_time"], reverse=True)[
            :limit
        ]

    def _get_error_endpoints(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取错误率最高的端点."""
        endpoints = []
        for endpoint, stats in self.endpoint_stats.items():
            if stats["count"] > 0:
                error_rate = (stats["error_count"] / stats["count"]) * 100
                if error_rate > 0:
                    endpoints.append(
                        {
                            "endpoint": endpoint,
                            "error_rate": error_rate,
                            "error_count": stats["error_count"],
                            "request_count": stats["count"],
                        }
                    )

        return sorted(endpoints, key=lambda x: x["error_rate"], reverse=True)[:limit]


class PerformanceOptimizer:
    """性能优化器."""

    def __init__(self):
        self.optimization_suggestions: list[dict[str, Any]] = []

    def analyze_performance(self, metrics: PerformanceMetrics) -> list[dict[str, Any]]:
        """分析性能并提供优化建议."""
        suggestions = []
        global_stats = metrics.get_global_stats()

        # 检查平均响应时间
        if global_stats["avg_response_time"] > 0.5:  # 500ms
            suggestions.append(
                {
                    "type": "response_time",
                    "severity": "high",
                    "message": f"平均响应时间过高 ({global_stats['avg_response_time']:.2f}s)，建议优化数据库查询和缓存策略",
                    "current_value": global_stats["avg_response_time"],
                    "target_value": 0.2,
                    "recommendations": [
                        "实现查询优化器",
                        "增加缓存层",
                        "优化数据库索引",
                        "考虑异步处理",
                    ],
                }
            )

        # 检查错误率
        if global_stats["error_rate"] > 5:  # 5%
            suggestions.append(
                {
                    "type": "error_rate",
                    "severity": "critical",
                    "message": f"错误率过高 ({global_stats['error_rate']:.2f}%)，需要立即处理",
                    "current_value": global_stats["error_rate"],
                    "target_value": 2.0,
                    "recommendations": [
                        "检查异常处理逻辑",
                        "增加输入验证",
                        "优化错误日志记录",
                        "实现健康检查",
                    ],
                }
            )

        # 检查慢端点
        slow_endpoints = global_stats["top_slow_endpoints"][:3]
        for endpoint in slow_endpoints:
            if endpoint["avg_response_time"] > 1.0:  # 1秒
                suggestions.append(
                    {
                        "type": "slow_endpoint",
                        "severity": "high",
                        "message": f"端点 {endpoint['endpoint']} 响应时间过慢 ({endpoint['avg_response_time']:.2f}s)",
                        "endpoint": endpoint["endpoint"],
                        "current_value": endpoint["avg_response_time"],
                        "target_value": 0.3,
                        "recommendations": [
                            "分析数据库查询",
                            "实现缓存策略",
                            "优化算法逻辑",
                            "考虑分页或懒加载",
                        ],
                    }
                )

        # 检查错误端点
        error_endpoints = global_stats["top_error_endpoints"][:3]
        for endpoint in error_endpoints:
            if endpoint["error_rate"] > 10:  # 10%
                suggestions.append(
                    {
                        "type": "error_endpoint",
                        "severity": "critical",
                        "message": f"端点 {endpoint['endpoint']} 错误率过高 ({endpoint['error_rate']:.2f}%)",
                        "endpoint": endpoint["endpoint"],
                        "current_value": endpoint["error_rate"],
                        "target_value": 5.0,
                        "recommendations": [
                            "检查输入参数验证",
                            "改进错误处理",
                            "增加日志记录",
                            "实现重试机制",
                        ],
                    }
                )

        self.optimization_suggestions = suggestions
        return suggestions


class EnhancedPerformanceMiddleware(BaseHTTPMiddleware):
    """增强性能监控中间件."""

    def __init__(self, app, enabled: bool = True, detailed_logging: bool = False):
        super().__init__(app)
        self.enabled = enabled
        self.detailed_logging = detailed_logging
        self.metrics = PerformanceMetrics()
        self.optimizer = PerformanceOptimizer()
        self.last_optimization_check = time.time()
        self.optimization_interval = 300  # 5分钟检查一次

    async def dispatch(self, request: Request, call_next) -> Response:
        """处理请求并记录性能指标."""
        if not self.enabled:
            return await call_next(request)

        start_time = time.time()

        # 提取端点信息
        method = request.method
        url_path = request.url.path
        endpoint = self._extract_endpoint(request)

        # 处理请求
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            if self.detailed_logging:
                logger.error(f"Request failed: {method} {url_path} - {str(e)}")
            raise

        # 计算处理时间
        process_time = time.time() - start_time

        # 记录性能指标
        self.metrics.record_request(
            method, url_path, status_code, process_time, endpoint
        )

        # 添加性能相关响应头
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        response.headers["X-Performance-Monitor"] = "enabled"

        # 记录慢请求日志
        if process_time > 1.0:  # 超过1秒的请求
            logger.warning(
                f"Slow request detected: {method} {url_path} - {process_time:.3f}s"
            )

        # 记录错误请求日志
        if status_code >= 400 and self.detailed_logging:
            logger.warning(
                f"Error request: {method} {url_path} - {status_code} - {process_time:.3f}s"
            )

        # 定期检查性能优化建议
        current_time = time.time()
        if current_time - self.last_optimization_check > self.optimization_interval:
            self.last_optimization_check = current_time
            asyncio.create_task(self._check_performance_optimizations())

        return response

    def _extract_endpoint(self, request: Request) -> str:
        """提取端点标识."""
        path = request.url.path

        # 简化端点路径，提取主要模式
        if path.startswith("/api/v1/"):
            # 提取主要端点模式
            parts = path.split("/")
            if len(parts) >= 4:
                return f"/api/v1/{parts[3]}"

        return path

    async def _check_performance_optimizations(self):
        """检查性能优化建议."""
        try:
            suggestions = self.optimizer.analyze_performance(self.metrics)
            if suggestions:
                # 记录优化建议
                for suggestion in suggestions:
                    if suggestion["severity"] in ["critical", "high"]:
                        logger.warning(
                            f"Performance optimization suggestion: {suggestion['message']}"
                        )
        except Exception as e:
            logger.error(f"Error checking performance optimizations: {str(e)}")

    def get_performance_report(self) -> dict[str, Any]:
        """获取性能报告."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "global_stats": self.metrics.get_global_stats(),
            "optimization_suggestions": self.optimizer.optimization_suggestions,
            "endpoint_count": len(self.metrics.endpoint_stats),
            "uptime_hours": (time.time() - self.metrics.global_stats["start_time"])
            / 3600,
        }

    def get_endpoint_report(self, endpoint: str) -> dict[str, Any]:
        """获取特定端点的性能报告."""
        return self.metrics.get_endpoint_stats(endpoint)


# 全局性能中间件实例
_performance_middleware: EnhancedPerformanceMiddleware | None = None


def get_performance_middleware() -> EnhancedPerformanceMiddleware | None:
    """获取全局性能中间件实例."""
    return _performance_middleware


def set_performance_middleware(middleware: EnhancedPerformanceMiddleware):
    """设置全局性能中间件实例."""
    global _performance_middleware
    _performance_middleware = middleware


def create_performance_middleware(
    app, enabled: bool = True, detailed_logging: bool = False
) -> EnhancedPerformanceMiddleware:
    """创建性能中间件实例."""
    middleware = EnhancedPerformanceMiddleware(app, enabled, detailed_logging)
    set_performance_middleware(middleware)
    return middleware
