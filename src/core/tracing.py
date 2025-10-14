"""
分布式追踪配置模块
使用OpenTelemetry进行分布式追踪
"""

import os
import time
from typing import Any,  Dict[str, Any], Any, Optional, List[Any]
from functools import wraps
from contextlib import contextmanager

from opentelemetry import trace, baggage, context
from opentelemetry import propagate
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.zipkin.json import ZipkinExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.util import types

from .logging import get_logger

logger = get_logger(__name__)


class TracingConfig:
    """追踪配置类"""

    def __init__(
        self,
        service_name: str = None,
        service_version: str = None,
        environment: str = None,
        jaeger_endpoint: str = None,
        zipkin_endpoint: str = None,
        otlp_endpoint: str = None,
        sample_rate: float = None,
        enabled: bool = True
    ):
        self.service_name = service_name or os.getenv('SERVICE_NAME', 'football-prediction')
        self.service_version = service_version or os.getenv('APP_VERSION', '1.0.0')
        self.environment = environment or os.getenv('ENVIRONMENT', 'development')
        self.jaeger_endpoint = jaeger_endpoint or os.getenv('JAEGER_ENDPOINT', 'http://localhost:14268/api/traces')
        self.zipkin_endpoint = zipkin_endpoint or os.getenv('ZIPKIN_ENDPOINT', 'http://localhost:9411/api/v2/spans')
        self.otlp_endpoint = otlp_endpoint or os.getenv('OTLP_ENDPOINT', 'http://localhost:4317')
        self.sample_rate = sample_rate or float(os.getenv('TRACE_SAMPLE_RATE', '0.1'))
        self.enabled = enabled and os.getenv('TRACING_ENABLED', 'true').lower() == 'true'

        self._tracer: Optional[trace.Tracer] = None
        self._provider: Optional[TracerProvider] = None

    def initialize(self) -> None:
        """初始化追踪系统"""
        if not self.enabled:
            logger.info("分布式追踪已禁用")
            return

        logger.info("初始化分布式追踪系统", service=self.service_name)

        # 设置追踪提供者
        self._provider = TracerProvider(
            sampler=TraceIdRatioBased(self.sample_rate),
            resource=self._create_resource()
        )

        trace.set_tracer_provider(self._provider)

        # 添加导出器
        self._setup_exporters()

        # 获取追踪器
        self._tracer = trace.get_tracer(self.service_name)

        # 自动插桩
        self._setup_auto_instrumentation()

        logger.info("分布式追踪系统初始化成功", sample_rate=self.sample_rate)

    def _create_resource(self) -> trace.Resource:
        """创建资源属性"""
        from opentelemetry.sdk.resources import Resource

        attributes = {
            "service.name": self.service_name,
            "service.version": self.service_version,
            "service.namespace": "football-prediction",
            "environment": self.environment,
            "telemetry.sdk.name": "opentelemetry",
            "telemetry.sdk.language": "python",
            "telemetry.sdk.version": "1.21.0"
        }

        # 添加主机信息
        try:
            import socket
            attributes["host.name"] = socket.gethostname()
        except Exception:
            pass

        # 添加容器信息
        if os.path.exists('/proc/self/cgroup'):
            attributes["container.id"] = os.uname()[1][:12]

        return Resource(attributes=attributes)

    def _setup_exporters(self) -> None:
        """设置追踪导出器"""
        exporters: List[SpanExporter] = []

        # Jaeger导出器
        if os.getenv('JAEGER_ENABLED', 'true').lower() == 'true':
            jaeger_exporter = JaegerExporter(
                endpoint=self.jaeger_endpoint,
                collector_endpoint=self.jaeger_endpoint,
            )
            exporters.append(jaeger_exporter)
            logger.info("Jaeger导出器已配置", endpoint=self.jaeger_endpoint)

        # Zipkin导出器
        if os.getenv('ZIPKIN_ENABLED', 'false').lower() == 'true':
            zipkin_exporter = ZipkinExporter(
                endpoint=self.zipkin_endpoint,
            )
            exporters.append(zipkin_exporter)
            logger.info("Zipkin导出器已配置", endpoint=self.zipkin_endpoint)

        # OTLP导出器
        if os.getenv('OTLP_ENABLED', 'true').lower() == 'true':
            otlp_exporter = OTLPSpanExporter(
                endpoint=self.otlp_endpoint,
                insecure=True
            )
            exporters.append(otlp_exporter)
            logger.info("OTLP导出器已配置", endpoint=self.otlp_endpoint)

        # 添加批处理器
        for exporter in exporters:
            span_processor = BatchSpanProcessor(exporter)
            self._provider.add_span_processor(span_processor)

    def _setup_auto_instrumentation(self) -> None:
        """设置自动插桩"""
        try:
            # FastAPI自动插桩
            if os.getenv('OTEL_INSTRUMENT_FASTAPI', 'true').lower() == 'true':
                FastAPIInstrumentor.instrument()
                logger.info("FastAPI自动插桩已启用")
        except ImportError:
            logger.warning("FastAPI未安装，跳过FastAPI自动插桩")

        try:
            # SQLAlchemy自动插桩
            if os.getenv('OTEL_INSTRUMENT_SQLALCHEMY', 'true').lower() == 'true':
                SQLAlchemyInstrumentor.instrument()
                logger.info("SQLAlchemy自动插桩已启用")
        except ImportError:
            logger.warning("SQLAlchemy未安装，跳过SQLAlchemy自动插桩")

        try:
            # Redis自动插桩
            if os.getenv('OTEL_INSTRUMENT_REDIS', 'true').lower() == 'true':
                RedisInstrumentor.instrument()
                logger.info("Redis自动插桩已启用")
        except ImportError:
            logger.warning("Redis未安装，跳过Redis自动插桩")

        try:
            # HTTPX自动插桩
            if os.getenv('OTEL_INSTRUMENT_HTTPX', 'true').lower() == 'true':
                HTTPXClientInstrumentor.instrument()
                logger.info("HTTPX自动插桩已启用")
        except ImportError:
            logger.warning("HTTPX未安装，跳过HTTPX自动插桩")

        try:
            # Celery自动插桩
            if os.getenv('OTEL_INSTRUMENT_CELERY', 'true').lower() == 'true':
                CeleryInstrumentor.instrument()
                logger.info("Celery自动插桩已启用")
        except ImportError:
            logger.warning("Celery未安装，跳过Celery自动插桩")

    def get_tracer(self, name: str = None) -> trace.Tracer:
        """获取追踪器"""
        if self._tracer is None:
            self.initialize()
        return trace.get_tracer(name or self.service_name)

    @property
    def tracer(self) -> trace.Tracer:
        """获取默认追踪器"""
        return self.get_tracer()

    def shutdown(self) -> None:
        """关闭追踪系统"""
        if self._provider:
            self._provider.shutdown()
            logger.info("分布式追踪系统已关闭")


# 全局追踪配置实例
tracing_config = TracingConfig()


def init_tracing(**kwargs) -> None:
    """初始化分布式追踪"""
    global tracing_config
    tracing_config = TracingConfig(**kwargs)
    tracing_config.initialize()


def get_tracer(name: str = None) -> trace.Tracer:
    """获取追踪器"""
    return tracing_config.get_tracer(name)


def trace_span(
    name: str = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: Dict[str, types.AttributeValue] = None
):
    """装饰器：创建追踪span"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            span_name = name or f"{func.__module__".{func.__name__}"

            with tracer.start_as_current_span(span_name, kind=kind) as span:
                # 添加属性
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                # 添加函数信息
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("function.success", True)
                    return result
                except Exception as e:
                    span.set_attribute("function.success", False)
                    span.set_attribute("error.message", str(e))
                    span.set_status(trace.Status(
                        trace.StatusCode.ERROR,
                        description=str(e)
                    ))
                    raise
        return wrapper
    return decorator


def trace_async_span(
    name: str = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: Dict[str, types.AttributeValue] = None
):
    """装饰器：创建异步追踪span"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            span_name = name or f"{func.__module__".{func.__name__}"

            with tracer.start_as_current_span(span_name, kind=kind) as span:
                # 添加属性
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                # 添加函数信息
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                span.set_attribute("function.async", True)

                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("function.success", True)
                    return result
                except Exception as e:
                    span.set_attribute("function.success", False)
                    span.set_attribute("error.message", str(e))
                    span.set_status(trace.Status(
                        trace.StatusCode.ERROR,
                        description=str(e)
                    ))
                    raise
        return wrapper
    return decorator


@contextmanager
def trace_context(
    name: str,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    attributes: Dict[str, types.AttributeValue] = None
):
    """上下文管理器：创建追踪span"""
    tracer = get_tracer()
    with tracer.start_as_current_span(name, kind=kind) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span


def add_span_attribute(key: str, value: types.AttributeValue) -> None:
    """添加属性到当前span"""
    span = trace.get_current_span()
    if span:
        span.set_attribute(key, value)


def add_span_event(name: str, attributes: Dict[str, types.AttributeValue] = None) -> None:
    """添加事件到当前span"""
    span = trace.get_current_span()
    if span:
        span.add_event(name, attributes or {})


def set_span_error(exception: Exception) -> None:
    """设置当前span为错误状态"""
    span = trace.get_current_span()
    if span:
        span.set_status(
            trace.Status(
                trace.StatusCode.ERROR,
                description=str(exception)
            )
        )
        span.set_attribute("error.type", type(exception).__name__)
        span.set_attribute("error.message", str(exception))


def get_trace_id() -> Optional[str]:
    """获取当前追踪ID"""
    span = trace.get_current_span()
    if span and span.get_span_context():
        return format(span.get_span_context().trace_id, "032x")
    return None


def get_span_id() -> Optional[str]:
    """获取当前span ID"""
    span = trace.get_current_span()
    if span and span.get_span_context():
        return format(span.get_span_context().span_id, "016x")
    return None


def set_baggage(key: str, value: str) -> None:
    """设置baggage项"""
    ctx = baggage.set_baggage(key, value)
    context.attach(ctx)


def get_baggage(key: str) -> Optional[str]:
    """获取baggage项"""
    return baggage.get_baggage(key)


# 性能追踪装饰器
def trace_performance(operation_name: str = None):
    """性能追踪装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__".{func.__name__}"
            start_time = time.time()

            with trace_context(f"performance.{op_name}", attributes={
                "operation.name": op_name,
                "operation.type": "performance"
            }) as span:
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time

                    # 记录性能指标
                    span.set_attribute("performance.duration_ms", duration * 1000)
                    span.set_attribute("performance.success", True)

                    # 如果超过阈值，记录警告
                    threshold = float(os.getenv('PERFORMANCE_WARNING_THRESHOLD', '1.0'))
                    if duration > threshold:
                        span.set_attribute("performance.slow", True)
                        logger.warning(
                            "Slow operation detected",
                            operation=op_name,
                            duration=duration,
                            threshold=threshold
                        )

                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    span.set_attribute("performance.duration_ms", duration * 1000)
                    span.set_attribute("performance.success", False)
                    raise
        return wrapper
    return decorator


# 数据库追踪装饰器
def trace_database_operation(operation: str, table: str = None):
    """数据库操作追踪装饰器"""
    return trace_span(
        name=f"database.{operation}",
        kind=trace.SpanKind.CLIENT,
        attributes={
            "db.operation": operation,
            "db.system": "postgresql",
            "db.name": os.getenv('DB_NAME', 'football_prediction'),
            "db.table": table or "unknown"
        }
    )


# HTTP客户端追踪装饰器
def trace_http_request(method: str, url: str = None):
    """HTTP请求追踪装饰器"""
    return trace_span(
        name=f"http.{method.lower()}",
        kind=trace.SpanKind.CLIENT,
        attributes={
            "http.method": method,
            "http.url": url or "unknown"
        }
    )


# 消息队列追踪装饰器
def trace_message_publish(queue: str, message_type: str = None):
    """消息发布追踪装饰器"""
    return trace_span(
        name="message.publish",
        kind=trace.SpanKind.PRODUCER,
        attributes={
            "messaging.system": "celery",
            "messaging.destination": queue,
            "messaging.message_type": message_type or "unknown"
        }
    )


def trace_message_process(queue: str, message_type: str = None):
    """消息处理追踪装饰器"""
    return trace_span(
        name="message.process",
        kind=trace.SpanKind.CONSUMER,
        attributes={
            "messaging.system": "celery",
            "messaging.destination": queue,
            "messaging.message_type": message_type or "unknown"
        }
    )
