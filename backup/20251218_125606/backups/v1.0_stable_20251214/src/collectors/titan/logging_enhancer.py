"""
Titan007 采集器日志增强器
Titan007 Collector Logging Enhancer

为 Titan007 采集器提供结构化日志，包含完整的业务上下文信息。
确保生产环境排错的高效性。

使用示例:
    from src.collectors.titan.logging_enhancer import get_titan_logger

    logger = get_titan_logger("TitanEuroCollector")
    logger.info("开始采集欧赔数据", extra={
        "match_id": match_id,
        "company_id": company_id,
        "company_name": company_name
    })
"""

import logging
from typing import Any, Dict, Optional
from functools import wraps


class TitanLoggingAdapter(logging.LoggerAdapter):
    """Titan007 日志适配器"""

    def process(self, msg: str, kwargs: Any) -> tuple[str, Any]:
        """处理日志消息，添加 Titan007 上下文信息"""
        # 确保有 extra 字典
        extra = kwargs.get("extra", {})

        # 添加 Titan007 特定上下文
        titan_context = {
            "service": "titan007_collector",
            "component": self.extra.get("component", "unknown"),
            **self.extra,
        }

        # 合并上下文
        extra.update(titan_context)
        kwargs["extra"] = extra

        return msg, kwargs


def get_titan_logger(
    component: str, base_logger: Optional[logging.Logger] = None
) -> TitanLoggingAdapter:
    """获取 Titan007 增强日志器"""
    if base_logger is None:
        base_logger = logging.getLogger(f"src.collectors.titan.{component}")

    return TitanLoggingAdapter(base_logger, {"component": component})


def log_with_context(component_name: str):
    """装饰器：为方法添加日志上下文"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_titan_logger(component_name)

            # 从参数中提取上下文信息
            context = {}

            # 提取 match_id
            if args:
                # 通常是 self, match_id, ...
                if len(args) >= 2 and isinstance(args[1], str):
                    context["match_id"] = args[1]

            # 提取 company_id
            if "company_id" in kwargs:
                context["company_id"] = kwargs["company_id"]
            elif "dto" in kwargs and hasattr(kwargs["dto"], "companyid"):
                context["company_id"] = kwargs["dto"].companyid
                context["company_name"] = getattr(kwargs["dto"], "companyname", None)

            # 记录方法开始
            logger.info(f"开始执行 {func.__name__}", extra=context)

            try:
                result = await func(*args, **kwargs)

                # 记录方法成功
                logger.info(
                    f"成功完成 {func.__name__}",
                    extra={
                        **context,
                        "result_type": type(result).__name__ if result else "None",
                    },
                )

                return result

            except Exception as e:
                # 记录方法失败
                logger.error(
                    f"执行失败 {func.__name__}",
                    extra={
                        **context,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                )
                raise

        return wrapper

    return decorator


class TitanOperationLogger:
    """Titan007 操作日志器"""

    def __init__(self, component: str):
        self.logger = get_titan_logger(component)
        self.component = component

    def log_api_request(self, endpoint: str, params: Dict[str, Any], **context):
        """记录API请求"""
        self.logger.info(
            f"API请求: {endpoint}",
            extra={
                "operation": "api_request",
                "endpoint": endpoint,
                "params": params,
                **context,
            },
        )

    def log_api_success(self, endpoint: str, response_size: int, **context):
        """记录API成功响应"""
        self.logger.info(
            f"API成功: {endpoint}",
            extra={
                "operation": "api_success",
                "endpoint": endpoint,
                "response_size": response_size,
                **context,
            },
        )

    def log_api_error(self, endpoint: str, error: Exception, **context):
        """记录API错误"""
        self.logger.error(
            f"API失败: {endpoint}",
            extra={
                "operation": "api_error",
                "endpoint": endpoint,
                "error_type": type(error).__name__,
                "error_message": str(error),
                **context,
            },
        )

    def log_database_operation(self, operation: str, table: str, **context):
        """记录数据库操作"""
        self.logger.info(
            f"数据库操作: {operation} on {table}",
            extra={
                "operation": "database",
                "database_operation": operation,
                "table": table,
                **context,
            },
        )

    def log_rate_limit_hit(self, wait_time: float, **context):
        """记录限流触发"""
        self.logger.warning(
            "触发限流",
            extra={"operation": "rate_limit", "wait_time": wait_time, **context},
        )
