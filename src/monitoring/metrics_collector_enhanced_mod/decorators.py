"""
性能跟踪装饰器 / Performance Tracking Decorators

提供用于跟踪函数性能的装饰器。
"""

import time
import functools
from typing import Callable, Any, Optional


# 延迟导入以避免循环依赖
def _get_collector():
    """延迟获取metrics collector"""
    from .collector import get_metrics_collector

    return get_metrics_collector()


def track_prediction_performance(
    model_version_param: str = "model_version",
    confidence_param: str = "confidence_score",
):
    """
    跟踪预测性能的装饰器

    Args:
        model_version_param: 模型版本参数名
        confidence_param: 置信度参数名

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            """异步函数包装器"""
            start_time = time.time()
            success = True
            result = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                collector = _get_collector()

                # 提取模型版本
                model_version = kwargs.get(model_version_param, "unknown")
                if model_version == "unknown" and args:
                    # 尝试从位置参数获取
                    if len(args) > 1:
                        model_version = str(args[1])

                # 提取置信度
                confidence = 0.0
                if confidence_param in kwargs:
                    confidence = float(kwargs.get(confidence_param, 0.0))
                elif hasattr(result, confidence_param):
                    confidence = float(getattr(result, confidence_param, 0.0))

                # 提取预测结果
                predicted_result = "unknown"
                if hasattr(result, "predicted_result"):
                    predicted_result = str(getattr(result, "predicted_result"))
                elif isinstance(result, dict) and "predicted_result" in result:
                    predicted_result = str(result["predicted_result"])

                # 记录指标
                collector.record_prediction(
                    model_version=model_version,
                    predicted_result=predicted_result,
                    confidence=confidence,
                    duration=duration,
                    success=success,
                )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            """同步函数包装器"""
            start_time = time.time()
            success = True
            result = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                collector = _get_collector()

                # 提取参数
                model_version = kwargs.get(model_version_param, "unknown")
                confidence = float(kwargs.get(confidence_param, 0.0))
                predicted_result = "unknown"

                if hasattr(result, "predicted_result"):
                    predicted_result = str(getattr(result, "predicted_result"))

                # 记录指标
                collector.record_prediction(
                    model_version=model_version,
                    predicted_result=predicted_result,
                    confidence=confidence,
                    duration=duration,
                    success=success,
                )

        # 根据函数类型返回相应的包装器
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def track_cache_performance(
    cache_type_param: str = "cache_type",
    operation_name: Optional[str] = None,
):
    """
    跟踪缓存性能的装饰器

    Args:
        cache_type_param: 缓存类型参数名
        operation_name: 操作名称，如果为None则使用函数名

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            hit = False
            result = None

            try:
                result = func(*args, **kwargs)

                # 根据返回结果判断是否命中
                # 如果结果不为None且不是False，则认为是命中
                hit = result is not None and result is not False

                return result
            finally:
                duration = time.time() - start_time
                collector = _get_collector()

                # 提取缓存类型
                cache_type = kwargs.get(cache_type_param, "default")

                # 确定操作名称
                op_name = operation_name or func.__name__

                # 记录指标
                collector.record_cache_operation(
                    cache_type=cache_type,
                    operation=op_name,
                    hit=hit,
                    duration=duration,
                )

        return wrapper

    return decorator


def track_database_performance(
    operation_type: str = "query",
    connection_pool_param: Optional[str] = None,
):
    """
    跟踪数据库性能的装饰器

    Args:
        operation_type: 操作类型（query/insert/update/delete）
        connection_pool_param: 连接池参数名

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            """异步函数包装器"""
            start_time = time.time()
            success = True

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                collector = _get_collector()

                # 如果提供了连接池，尝试获取连接信息
                if connection_pool_param and connection_pool_param in kwargs:
                    pool = kwargs[connection_pool_param]
                    if hasattr(pool, "size"):
                        collector.record_database_metrics(
                            pool_size=pool.size(),
                            active_connections=getattr(pool, "active", 0),
                            idle_connections=getattr(pool, "idle", 0),
                            query_duration=duration,
                        )

                # 记录错误
                if not success:
                    collector.record_error(
                        error_type="database_error",
                        component=f"db_{operation_type}",
                        severity="high",
                    )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            """同步函数包装器"""
            start_time = time.time()
            success = True

            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                collector = _get_collector()

                # 记录查询指标
                metric = {
                    "name": "database_operation_duration",
                    "value": duration,
                    "labels": {"operation": operation_type},
                    "unit": "seconds",
                }
                # 这里需要导入MetricPoint，但为了避免循环导入，
                # 我们直接通过collector记录
                collector.aggregator.add_metric(metric)

                # 记录错误
                if not success:
                    collector.record_error(
                        error_type="database_error",
                        component=f"db_{operation_type}",
                        severity="high",
                    )

        # 根据函数类型返回相应的包装器
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def track_performance(
    metric_name: str,
    labels: Optional[dict] = None,
    track_success: bool = True,
):
    """
    通用性能跟踪装饰器

    Args:
        metric_name: 指标名称
        labels: 标签字典
        track_success: 是否跟踪成功/失败

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True

            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                collector = _get_collector()

                # 更新Prometheus指标
                final_labels = labels or {}
                final_labels.update(
                    {
                        "function": func.__name__,
                        "module": func.__module__,
                    }
                )

                if track_success:
                    final_labels["success"] = str(success)

                # 使用 request_duration 直方图
                histogram = collector.prometheus.request_duration
                histogram.labels(
                    endpoint=f"{func.__module__}.{func.__name__}", method="function"
                ).observe(duration)

                # 记录到聚合器
                from .metric_types import MetricPoint

                metric = MetricPoint(
                    name=metric_name,
                    value=duration,
                    labels=final_labels,
                    unit="seconds",
                )
                collector.aggregator.add_metric(metric)

        return wrapper

    return decorator
