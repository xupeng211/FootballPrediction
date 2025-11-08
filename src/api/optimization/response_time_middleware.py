"""
API优化中间件 - 响应时间监控和优化
实现实时响应时间监控、自动优化和性能告警
"""

import logging
import statistics
import time
from collections import defaultdict
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.ux_optimization.api_optimizer import APIResponseOptimizer, get_api_optimizer

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ResponseTimeAlert:
    """响应时间告警"""

    endpoint: str
    method: str
    current_avg: float
    threshold: float
    level: AlertLevel
    message: str
    timestamp: datetime
    sample_count: int


@dataclass
class PerformanceThreshold:
    """性能阈值配置"""

    warning_avg_ms: float = 300.0  # 平均响应时间警告阈值
    critical_avg_ms: float = 500.0  # 平均响应时间严重阈值
    warning_p95_ms: float = 400.0  # P95响应时间警告阈值
    critical_p95_ms: float = 600.0  # P95响应时间严重阈值
    min_sample_size: int = 50  # 最小样本数
    alert_cooldown: int = 300  # 告警冷却时间(秒)


class ResponseTimeMiddleware(BaseHTTPMiddleware):
    """响应时间监控中间件"""

    def __init__(
        self,
        app,
        optimizer: APIResponseOptimizer | None = None,
        threshold: PerformanceThreshold | None = None,
    ):
        super().__init__(app)
        self.optimizer = optimizer or get_api_optimizer()
        self.threshold = threshold or PerformanceThreshold()

        # 响应时间数据存储
        self.response_times: dict[str, list[float]] = defaultdict(list)
        self.last_alerts: dict[str, datetime] = {}

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "total_response_time": 0.0,
            "alerts_triggered": 0,
            "optimizations_triggered": 0,
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理HTTP请求"""
        start_time = time.time()
        endpoint = self._get_endpoint_key(request)
        method = request.method

        try:
            # 记录请求开始
            request_start = datetime.now()

            # 处理请求
            response = await call_next(request)

            # 计算响应时间
            response_time = (time.time() - start_time) * 1000

            # 更新统计信息
            self._update_stats(endpoint, method, response_time, response.status_code)

            # 添加响应头
            response.headers["X-Response-Time"] = f"{response_time:.1f}ms"
            response.headers["X-Request-ID"] = getattr(request.state, "request_id", "")

            # 记录到优化器
            await self.optimizer._record_metric(
                endpoint=endpoint,
                method=method,
                response_time=response_time,
                status_code=response.status_code,
                user_id=getattr(request.state, "user_id", None),
            )

            # 检查性能告警
            await self._check_performance_alerts(endpoint, method)

            return response

        except Exception as e:
            # 计算错误响应时间
            response_time = (time.time() - start_time) * 1000
            status_code = getattr(e, "status_code", 500)

            # 更新统计信息
            self._update_stats(endpoint, method, response_time, status_code)

            # 记录错误
            logger.error(f"Request error: {method} {endpoint} - {str(e)}")

            raise

    def _get_endpoint_key(self, request: Request) -> str:
        """获取端点键"""
        # 移除查询参数
        path = request.url.path
        # 替换路径参数为通用模式
        import re

        # 替换数字ID为通用模式
        path = re.sub(r"/\d+", "/{id}", path)
        # 替换UUID为通用模式
        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "/{uuid}",
            path,
        )

        return path

    def _update_stats(
        self, endpoint: str, method: str, response_time: float, status_code: int
    ) -> None:
        """更新统计信息"""
        key = f"{method}:{endpoint}"

        # 记录响应时间
        self.response_times[key].append(response_time)

        # 限制数据量
        if len(self.response_times[key]) > 1000:
            self.response_times[key] = self.response_times[key][-1000:]

        # 更新全局统计
        self.stats["total_requests"] += 1
        self.stats["total_response_time"] += response_time

    async def _check_performance_alerts(self, endpoint: str, method: str) -> None:
        """检查性能告警"""
        key = f"{method}:{endpoint}"
        response_times = self.response_times[key]

        if len(response_times) < self.threshold.min_sample_size:
            return

        # 计算性能指标
        avg_time = statistics.mean(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile

        # 检查是否需要告警
        current_time = datetime.now()
        last_alert_time = self.last_alerts.get(key)

        # 检查告警冷却时间
        if (
            last_alert_time
            and (current_time - last_alert_time).total_seconds()
            < self.threshold.alert_cooldown
        ):
            return

        alerts = []

        # 检查平均响应时间
        if avg_time > self.threshold.critical_avg_ms:
            alerts.append(
                ResponseTimeAlert(
                    endpoint=endpoint,
                    method=method,
                    current_avg=avg_time,
                    threshold=self.threshold.critical_avg_ms,
                    level=AlertLevel.CRITICAL,
                    message=f"平均响应时间严重超阈值: {avg_time:.1f}ms > {self.threshold.critical_avg_ms}ms",
                    timestamp=current_time,
                    sample_count=len(response_times),
                )
            )
        elif avg_time > self.threshold.warning_avg_ms:
            alerts.append(
                ResponseTimeAlert(
                    endpoint=endpoint,
                    method=method,
                    current_avg=avg_time,
                    threshold=self.threshold.warning_avg_ms,
                    level=AlertLevel.WARNING,
                    message=f"平均响应时间警告: {avg_time:.1f}ms > {self.threshold.warning_avg_ms}ms",
                    timestamp=current_time,
                    sample_count=len(response_times),
                )
            )

        # 检查P95响应时间
        if p95_time > self.threshold.critical_p95_ms:
            alerts.append(
                ResponseTimeAlert(
                    endpoint=endpoint,
                    method=method,
                    current_avg=p95_time,
                    threshold=self.threshold.critical_p95_ms,
                    level=AlertLevel.CRITICAL,
                    message=f"P95响应时间严重超阈值: {p95_time:.1f}ms > {self.threshold.critical_p95_ms}ms",
                    timestamp=current_time,
                    sample_count=len(response_times),
                )
            )
        elif p95_time > self.threshold.warning_p95_ms:
            alerts.append(
                ResponseTimeAlert(
                    endpoint=endpoint,
                    method=method,
                    current_avg=p95_time,
                    threshold=self.threshold.warning_p95_ms,
                    level=AlertLevel.WARNING,
                    message=f"P95响应时间警告: {p95_time:.1f}ms > {self.threshold.warning_p95_ms}ms",
                    timestamp=current_time,
                    sample_count=len(response_times),
                )
            )

        # 处理告警
        if alerts:
            await self._handle_alerts(key, alerts)

    async def _handle_alerts(self, key: str, alerts: list[ResponseTimeAlert]) -> None:
        """处理告警"""
        for alert in alerts:
            # 记录告警
            await self._log_alert(alert)

            # 触发自动优化
            if alert.level in [AlertLevel.ERROR, AlertLevel.CRITICAL]:
                await self._trigger_auto_optimization(alert)

        # 更新告警时间
        self.last_alerts[key] = datetime.now()
        self.stats["alerts_triggered"] += len(alerts)

    async def _log_alert(self, alert: ResponseTimeAlert) -> None:
        """记录告警"""
        log_message = (
            f"[{alert.level.value.upper()}] {alert.method} {alert.endpoint} - "
            f"{alert.message} (样本数: {alert.sample_count})"
        )

        if alert.level == AlertLevel.CRITICAL:
            logger.critical(log_message)
        elif alert.level == AlertLevel.ERROR:
            logger.error(log_message)
        elif alert.level == AlertLevel.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # 这里可以发送到外部监控系统
        await self._send_to_monitoring_system(alert)

    async def _send_to_monitoring_system(self, alert: ResponseTimeAlert) -> None:
        """发送到监控系统"""
        try:
            # 集成到现有监控系统
            pass
        except Exception as e:
            logger.warning(f"Failed to send alert to monitoring system: {e}")

    async def _trigger_auto_optimization(self, alert: ResponseTimeAlert) -> None:
        """触发自动优化"""
        try:
            logger.info(
                f"Triggering auto optimization for {alert.method} {alert.endpoint}"
            )

            # 调用API优化器进行优化
            await self.optimizer._optimize_endpoint(
                alert.endpoint, alert.method, []  # 这里可以传递相关指标
            )

            self.stats["optimizations_triggered"] += 1
            logger.info(
                f"Auto optimization triggered for {alert.method} {alert.endpoint}"
            )

        except Exception as e:
            logger.error(f"Auto optimization failed: {e}")

    @asynccontextmanager
    async def measure_request_time(self, endpoint: str, method: str = "GET"):
        """测量请求时间的上下文管理器"""
        start_time = time.time()
        try:
            yield
        finally:
            response_time = (time.time() - start_time) * 1000
            self._update_stats(endpoint, method, response_time, 200)

    def get_performance_summary(self) -> dict[str, Any]:
        """获取性能摘要"""
        summary = {"global_stats": self.stats.copy(), "endpoints": {}}

        # 计算全局平均响应时间
        if self.stats["total_requests"] > 0:
            summary["global_stats"]["avg_response_time"] = (
                self.stats["total_response_time"] / self.stats["total_requests"]
            )
        else:
            summary["global_stats"]["avg_response_time"] = 0.0

        # 计算各端点性能
        for key, response_times in self.response_times.items():
            if response_times:
                method, endpoint = key.split(":", 1)
                summary["endpoints"][key] = {
                    "method": method,
                    "endpoint": endpoint,
                    "request_count": len(response_times),
                    "avg_response_time": statistics.mean(response_times),
                    "min_response_time": min(response_times),
                    "max_response_time": max(response_times),
                    "p95_response_time": statistics.quantiles(response_times, n=20)[18],
                    "p99_response_time": statistics.quantiles(response_times, n=100)[
                        98
                    ],
                }

        return summary

    def get_slow_endpoints(self, threshold_ms: float = 300.0) -> list[dict[str, Any]]:
        """获取慢端点列表"""
        slow_endpoints = []

        for key, response_times in self.response_times.items():
            if len(response_times) >= self.threshold.min_sample_size:
                avg_time = statistics.mean(response_times)
                if avg_time > threshold_ms:
                    method, endpoint = key.split(":", 1)
                    slow_endpoints.append(
                        {
                            "method": method,
                            "endpoint": endpoint,
                            "avg_response_time": avg_time,
                            "request_count": len(response_times),
                            "severity": "high" if avg_time > 500 else "medium",
                        }
                    )

        # 按响应时间排序
        slow_endpoints.sort(key=lambda x: x["avg_response_time"], reverse=True)
        return slow_endpoints

    def get_recent_alerts(self, hours: int = 24) -> list[dict[str, Any]]:
        """获取最近的告警"""
        # 这里应该从告警存储中获取
        # 简化实现
        return []

    def reset_stats(self) -> None:
        """重置统计信息"""
        self.response_times.clear()
        self.last_alerts.clear()
        self.stats = {
            "total_requests": 0,
            "total_response_time": 0.0,
            "alerts_triggered": 0,
            "optimizations_triggered": 0,
        }
        logger.info("Response time middleware stats reset")


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """请求大小监控中间件"""

    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):  # 10MB
        super().__init__(app)
        self.max_request_size = max_request_size
        self.stats = {
            "total_requests": 0,
            "total_request_size": 0,
            "oversized_requests": 0,
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求大小检查"""
        # 检查请求大小
        content_length = request.headers.get("content-length")
        if content_length:
            size = int(content_length)
            self.stats["total_request_size"] += size
            self.stats["total_requests"] += 1

            if size > self.max_request_size:
                self.stats["oversized_requests"] += 1
                logger.warning(
                    f"Oversized request: {size} bytes (limit: {self.max_request_size})"
                )
                raise HTTPException(
                    status_code=413,
                    detail=f"Request entity too large (max: {self.max_request_size} bytes)",
                )

        return await call_next(request)

    def get_size_stats(self) -> dict[str, Any]:
        """获取请求大小统计"""
        avg_size = (
            self.stats["total_request_size"] / self.stats["total_requests"]
            if self.stats["total_requests"] > 0
            else 0
        )

        return {
            **self.stats,
            "avg_request_size": avg_size,
            "oversized_rate": (
                self.stats["oversized_requests"] / self.stats["total_requests"] * 100
                if self.stats["total_requests"] > 0
                else 0
            ),
        }


# 工厂函数
def create_response_time_middleware(
    app,
    optimizer: APIResponseOptimizer | None = None,
    threshold: PerformanceThreshold | None = None,
) -> ResponseTimeMiddleware:
    """创建响应时间监控中间件"""
    return ResponseTimeMiddleware(app, optimizer, threshold)


def create_request_size_middleware(
    app, max_request_size: int = 10 * 1024 * 1024
) -> RequestSizeMiddleware:
    """创建请求大小监控中间件"""
    return RequestSizeMiddleware(app, max_request_size)
