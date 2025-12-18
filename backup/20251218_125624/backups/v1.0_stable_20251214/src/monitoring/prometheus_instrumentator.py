"""P4-1: Prometheus 监控模块
为 FastAPI 应用集成 Prometheus 指标收集。
"""

import time
from collections.abc import Callable
from functools import wraps

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator

logger = __name__

# 核心业务指标
HTTP_REQUESTS_TOTAL = Counter(
    "football_prediction_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=None,
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "football_prediction_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=None,
)

# 业务特定指标
PREDICTION_REQUESTS_TOTAL = Counter(
    "football_prediction_requests_total",
    "Total prediction requests",
    ["prediction_type", "status"],
    registry=None,
)

PREDICTION_REQUEST_DURATION_SECONDS = Histogram(
    "football_prediction_request_duration_seconds",
    "Prediction request duration in seconds",
    ["prediction_type"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0],
    registry=None,
)

DATABASE_OPERATIONS_TOTAL = Counter(
    "football_prediction_db_operations_total",
    "Total database operations",
    ["operation", "table", "status"],
    registry=None,
)

DATABASE_OPERATION_DURATION_SECONDS = Histogram(
    "football_prediction_db_operation_duration_seconds",
    "Database operation duration in seconds",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=None,
)

REDIS_OPERATIONS_TOTAL = Counter(
    "football_prediction_redis_operations_total",
    "Total Redis operations",
    ["operation", "status"],
    registry=None,
)

ACTIVE_CONNECTIONS = Gauge(
    "football_prediction_active_connections",
    "Number of active connections",
    ["connection_type"],
    registry=None,
)

ML_MODEL_INFERENCE_TOTAL = Counter(
    "football_prediction_ml_inference_total",
    "Total ML model inference requests",
    ["model_name", "status"],
    registry=None,
)

ML_MODEL_INFERENCE_DURATION_SECONDS = Histogram(
    "football_prediction_ml_inference_duration_seconds",
    "ML model inference duration in seconds",
    ["model_name"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
    registry=None,
)

# 数据收集指标
DATA_COLLECTION_REQUESTS_TOTAL = Counter(
    "football_prediction_data_collection_requests_total",
    "Total data collection requests",
    ["source", "status"],
    registry=None,
)

DATA_COLLECTED_RECORDS = Counter(
    "football_prediction_data_collected_records_total",
    "Total records collected",
    ["source", "table"],
    registry=None,
)


def create_instrumentator() -> Instrumentator:
    """创建 Prometheus 仪表化器"""

    # 自定义指标处理
    def instrumentation_callback(request, response, labels, metrics):
        """
        自定义指标收集回调
        """
        method = request.method
        endpoint = request.url.path
        status_code = str(response.status_code)

        # 更新 HTTP 指标
        HTTP_REQUESTS_TOTAL.labels(
            method=method, endpoint=endpoint, status_code=status_code
        ).inc()

        # 如果是预测请求，额外记录预测指标
        if "/predictions" in endpoint:
            prediction_type = "unknown"
            if endpoint.endswith("/predictions"):
                prediction_type = "list"
            elif endpoint.endswith("/generate"):
                prediction_type = "generate"
            elif "/batch" in endpoint:
                prediction_type = "batch"

            status = "success" if response.status_code < 400 else "error"
            PREDICTION_REQUESTS_TOTAL.labels(
                prediction_type=prediction_type, status=status
            ).inc()

    # 创建仪表化器
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=False,
        should_group_untemplated=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics"],
        env_var_name="PROMETHEUS_FASTAPI_INSTRUMENTATOR",
        inprogress_name="football_prediction_http_requests_inprogress",
        inprogress_labels=True,
    )

    # 添加自定义指标
    instrumentator.add(instrumentation_callback)

    return instrumentator


def instrument_database_operation(operation: str, table: str):
    """装饰器：数据库操作监控"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                logger.error(f"Database operation {operation} on {table} failed: {e}")
                raise
            finally:
                duration = time.time() - start_time
                DATABASE_OPERATIONS_TOTAL.labels(
                    operation=operation, table=table, status=status
                ).inc()
                DATABASE_OPERATION_DURATION_SECONDS.labels(
                    operation=operation, table=table
                ).observe(duration)

        return wrapper

    return decorator


def instrument_redis_operation(operation: str):
    """装饰器：Redis 操作监控"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                logger.error(f"Redis operation {operation} failed: {e}")
                raise
            finally:
                REDIS_OPERATIONS_TOTAL.labels(operation=operation, status=status).inc()

        return wrapper

    return decorator


def instrument_ml_inference(model_name: str):
    """装饰器：ML 模型推理监控"""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                logger.error(f"ML inference {model_name} failed: {e}")
                raise
            finally:
                duration = time.time() - start_time
                ML_MODEL_INFERENCE_TOTAL.labels(
                    model_name=model_name, status=status
                ).inc()
                ML_MODEL_INFERENCE_DURATION_SECONDS.labels(
                    model_name=model_name
                ).observe(duration)

        return wrapper

    return decorator


def update_active_connections(connection_type: str, count: int):
    """更新活跃连接数指标"""
    ACTIVE_CONNECTIONS.labels(connection_type=connection_type).set(count)


def record_data_collection(
    source: str, status: str, records_count: int = 0, table: str = "unknown"
):
    """记录数据收集指标"""
    DATA_COLLECTION_REQUESTS_TOTAL.labels(source=source, status=status).inc()
    if records_count > 0:
        DATA_COLLECTED_RECORDS.labels(source=source, table=table).inc(records_count)


# 导出指标以便在路由中使用
__all__ = [
    "HTTP_REQUESTS_TOTAL",
    "HTTP_REQUEST_DURATION_SECONDS",
    "PREDICTION_REQUESTS_TOTAL",
    "PREDICTION_REQUEST_DURATION_SECONDS",
    "DATABASE_OPERATIONS_TOTAL",
    "DATABASE_OPERATION_DURATION_SECONDS",
    "REDIS_OPERATIONS_TOTAL",
    "ACTIVE_CONNECTIONS",
    "ML_MODEL_INFERENCE_TOTAL",
    "ML_MODEL_INFERENCE_DURATION_SECONDS",
    "DATA_COLLECTION_REQUESTS_TOTAL",
    "DATA_COLLECTED_RECORDS",
    "create_instrumentator",
    "instrument_database_operation",
    "instrument_redis_operation",
    "instrument_ml_inference",
    "update_active_connections",
    "record_data_collection",
    "generate_latest",
]
