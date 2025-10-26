"""
APM集成模块
APM Integration Module

集成应用性能监控工具，提供分布式追踪、性能指标和错误监控。
"""

import logging
import time
import traceback
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager, contextmanager

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class APMIntegration:
    """APM集成管理器"""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.logger = logging.getLogger(__name__)

        # 尝试导入APM库
        self.apm_client = None
        self.init_apm_client()

    def init_apm_client(self):
        """初始化APM客户端"""
        if not self.enabled:
            return

        try:
            # 尝试导入和初始化OpenTelemetry
            try:
                from opentelemetry import trace, metrics
                from opentelemetry.exporter.prometheus import PrometheusMetricReader
                from opentelemetry.sdk.metrics import MeterProvider
                from opentelemetry.sdk.trace import TracerProvider
                from .trace.export import BatchSpanProcessor
                from .jaeger.thrift import JaegerExporter

                # 初始化追踪
                trace.set_tracer_provider(TracerProvider())
                tracer = trace.get_tracer(__name__)

                # 初始化指标
                reader = PrometheusMetricReader()
                metrics.set_meter_provider(MeterProvider(metric_readers=[reader]))

                self.tracer = tracer
                self.meter = metrics.get_meter(__name__)

                self.logger.info("OpenTelemetry APM initialized successfully")

            except ImportError as e:
                self.logger.warning(f"OpenTelemetry not available: {e}")

            # 尝试初始化Sentry (错误监控)
            try:
                import sentry_sdk
                from sentry_sdk.integrations.fastapi import FastApiIntegration
                from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
                from sentry_sdk.integrations.redis import RedisIntegration

                sentry_sdk.init(
                    dsn=self.get_sentry_dsn(),
                    integrations=[
                        FastApiIntegration(auto_enabling_integrations=False),
                        SqlalchemyIntegration(),
                        RedisIntegration(),
                    ],
                    traces_sample_rate=0.1,  # 10% 采样率
                    environment=self.get_environment(),
                )

                self.logger.info("Sentry APM initialized successfully")

            except ImportError as e:
                self.logger.warning(f"Sentry not available: {e}")
            except Exception as e:
                self.logger.warning(f"Sentry initialization failed: {e}")

        except Exception as e:
            self.logger.error(f"APM initialization failed: {e}")

    def get_sentry_dsn(self) -> Optional[str]:
        """获取Sentry DSN"""
        import os

        return os.getenv("SENTRY_DSN")

    def get_environment(self) -> str:
        """获取当前环境"""
        import os

        return os.getenv("ENVIRONMENT", "development")

    def create_span(self, name: str, **kwargs):
        """创建追踪span"""
        if not self.enabled or not hasattr(self, "tracer"):
            return _DummySpan()

        return self.tracer.start_span(name, **kwargs)

    def record_metric(self, name: str, value: float, unit: str = "", **kwargs):
        """记录指标"""
        if not self.enabled or not hasattr(self, "meter"):
            return

        try:
            counter = self.meter.create_counter(
                name=f"football_prediction_{name}", unit=unit, **kwargs
            )
            counter.add(value)
        except Exception as e:
            self.logger.warning(f"Failed to record metric {name}: {e}")

    def record_error(self, error: Exception, context: Optional[Dict] = None):
        """记录错误"""
        if not self.enabled:
            return

        try:
            import sentry_sdk

            sentry_sdk.capture_exception(error, extra=context)
        except Exception:
            # Sentry不可用时的fallback
            self.logger.error(f"Error recorded: {error}", exc_info=True)

    @contextmanager
    def trace_operation(self, operation_name: str):
        """追踪操作上下文管理器"""
        span = self.create_span(operation_name)
        try:
            yield span
        except Exception as e:
            self.record_error(e, {"operation": operation_name})
            raise
        finally:
            if hasattr(span, "end"):
                span.end()

    @asynccontextmanager
    async def trace_async_operation(self, operation_name: str):
        """追踪异步操作上下文管理器"""
        span = self.create_span(operation_name)
        try:
            yield span
        except Exception as e:
            self.record_error(e, {"operation": operation_name})
            raise
        finally:
            if hasattr(span, "end"):
                span.end()


class APMMiddleware(BaseHTTPMiddleware):
    """APM中间件"""

    def __init__(self, app, apm_integration: APMIntegration):
        super().__init__(app)
        self.apm = apm_integration

    async def dispatch(self, request: Request, call_next):
        """处理请求并记录APM数据"""
        if not self.apm.enabled:
            return await call_next(request)

        start_time = time.time()

        # 创建请求span
        with self.apm.trace_operation(
            f"HTTP {request.method} {request.url.path}"
        ) as span:
            try:
                # 记录请求开始
                self.apm.record_metric(
                    "http_requests_total",
                    1,
                    "count",
                    {
                        "method": request.method,
                        "path": request.url.path,
                    },
                )

                # 处理请求
                response = await call_next(request)

                # 计算响应时间
                process_time = time.time() - start_time

                # 记录响应时间指标
                self.apm.record_metric(
                    "http_request_duration",
                    process_time,
                    "seconds",
                    {
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": str(response.status_code),
                    },
                )

                # 记录状态码指标
                self.apm.record_metric(
                    "http_responses_total",
                    1,
                    "count",
                    {
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": str(response.status_code),
                    },
                )

                # 添加追踪信息到响应头
                response.headers["X-Trace-ID"] = getattr(span, "span_id", "unknown")
                response.headers["X-Process-Time"] = str(process_time)

                return response

            except Exception as e:
                # 记录错误
                self.apm.record_error(
                    e,
                    {
                        "method": request.method,
                        "path": request.url.path,
                        "query_params": dict(request.query_params),
                    },
                )

                # 记录错误指标
                self.apm.record_metric(
                    "http_errors_total",
                    1,
                    "count",
                    {
                        "method": request.method,
                        "path": request.url.path,
                        "error_type": type(e).__name__,
                    },
                )

                raise


class _DummySpan:
    """虚拟Span，用于APM不可用时的fallback"""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def set_attribute(self, key, value):
        pass

    def add_event(self, name, attributes=None):
        pass


# 全局APM实例
_global_apm = None


def get_apm() -> APMIntegration:
    """获取全局APM实例"""
    global _global_apm
    if _global_apm is None:
        _global_apm = APMIntegration()
    return _global_apm


def init_apm(enabled: bool = True) -> APMIntegration:
    """初始化APM"""
    global _global_apm
    _global_apm = APMIntegration(enabled)
    return _global_apm


# 便捷函数
def trace_operation(operation_name: str):
    """追踪操作装饰器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            apm = get_apm()
            with apm.trace_operation(operation_name):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def trace_async_operation(operation_name: str):
    """追踪异步操作装饰器"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            apm = get_apm()
            async with apm.trace_async_operation(operation_name):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def record_metric(name: str, value: float, unit: str = "", **kwargs):
    """记录指标的便捷函数"""
    get_apm().record_metric(name, value, unit, **kwargs)


def record_error(error: Exception, context: Optional[Dict] = None):
    """记录错误的便捷函数"""
    get_apm().record_error(error, context)
