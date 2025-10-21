# mypy: ignore-errors
"""
具体装饰器实现
Concrete Decorator Implementations

实现了各种用于功能增强和横切关注点的装饰器。
Implements various decorators for functionality enhancement and cross-cutting concerns.
"""

import asyncio
import time
import json
from typing import Any, Callable, Dict, List, Optional, Union, Type
from datetime import datetime, timedelta
import logging

from ..core.logging import get_logger
from ..core.exceptions import (
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    TimeoutError,
)

# 尝试导入可选依赖
try:
    from ..core.metrics import MetricsCollector
except ImportError:
    MetricsCollector = None

try:
    from ..core.cache import CacheManager
except ImportError:
    CacheManager = None

try:
    from ..core.auth import AuthService
except ImportError:
    AuthService = None

try:
    from ..core.validators import Validator
except ImportError:
    Validator = None
from .base import Decorator, DecoratorContext, decorator_registry


logger = get_logger(__name__)


class LoggingDecorator(Decorator):
    """日志装饰器，记录函数执行的前后信息"""

    def __init__(
        self,
        component,
        name: Optional[str] = None,
        level: str = "INFO",
        log_args: bool = True,
        log_result: bool = True,
        log_exception: bool = True,
        include_context: bool = False,
    ):
        super().__init__(component, name)
        self.level = level.upper()
        self.log_args = log_args
        self.log_result = log_result
        self.log_exception = log_exception
        self.include_context = include_context

    async def _execute(self, *args, **kwargs) -> Any:
        """执行日志装饰器"""
        func_name = self.component.get_name()
        logger_instance = logger

        # 记录函数开始执行
        log_data = {
            "event": "function_start",
            "function": func_name,
            "decorator": self.name,
        }

        if self.log_args:
            # 安全地记录参数（避免记录敏感信息）
            safe_args = self._sanitize_args(args)
            safe_kwargs = self._sanitize_kwargs(kwargs)
            log_data["args"] = safe_args
            log_data["kwargs"] = safe_kwargs

        if self.include_context and "context" in kwargs:
            context = kwargs["context"]
            if isinstance(context, DecoratorContext):
                log_data["trace_id"] = context.trace_id

        logger_instance.log(getattr(logging, self.level), json.dumps(log_data))

        try:
            # 执行被装饰的函数
            result = await self.component.execute(*args, **kwargs)

            # 记录函数执行成功
            if self.log_result:
                success_log = {
                    "event": "function_success",
                    "function": func_name,
                    "decorator": self.name,
                    "result": self._sanitize_result(result),
                }

                if self.include_context and "context" in kwargs:
                    context = kwargs["context"]
                    if isinstance(context, DecoratorContext):
                        success_log["execution_time"] = context.get_execution_time()
                        success_log["execution_path"] = context.execution_path

                logger_instance.log(
                    getattr(logging, self.level), json.dumps(success_log)
                )

            return result

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            # 记录函数执行失败
            if self.log_exception:
                error_log = {
                    "event": "function_error",
                    "function": func_name,
                    "decorator": self.name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }

                if self.include_context and "context" in kwargs:
                    context = kwargs["context"]
                    if isinstance(context, DecoratorContext):
                        error_log["execution_time"] = context.get_execution_time()

                logger_instance.error(json.dumps(error_log))

            raise

    def _sanitize_args(self, args: tuple) -> list:
        """清理参数，移除敏感信息"""
        sanitized = []

        for arg in args:
            if isinstance(arg, dict):
                sanitized.append(self._sanitize_dict(arg))
            elif isinstance(arg, (list, tuple)):
                sanitized.append(self._sanitize_sequence(arg))
            else:
                sanitized.append(str(arg)[:100])  # 限制长度

        return sanitized

    def _sanitize_kwargs(self, kwargs: dict) -> dict:
        """清理关键字参数，移除敏感信息"""
        return self._sanitize_dict(kwargs)

    def _sanitize_dict(self, data: dict) -> dict:
        """清理字典，移除敏感信息"""
        sensitive_keys = ["password", "token", "secret", "key", "auth"]
        sanitized = {}

        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, (list, tuple)):
                sanitized[key] = self._sanitize_sequence(value)
            else:
                sanitized[key] = str(value)[:100]

        return sanitized

    def _sanitize_sequence(self, seq: Union[list, tuple]) -> list:
        """清理序列，移除敏感信息"""
        sanitized = []

        for item in seq:
            if isinstance(item, dict):
                sanitized.append(self._sanitize_dict(item))
            elif isinstance(item, (list, tuple)):
                sanitized.append(self._sanitize_sequence(item))
            else:
                sanitized.append(str(item)[:100])

        return sanitized

    def _sanitize_result(self, result: Any) -> Any:
        """清理结果，移除敏感信息"""
        if isinstance(result, dict):
            return self._sanitize_dict(result)
        elif isinstance(result, (list, tuple)):
            return self._sanitize_sequence(result)
        else:
            return str(result)[:100]


class RetryDecorator(Decorator):
    """重试装饰器，在函数执行失败时自动重试"""

    def __init__(
        self,
        component,
        name: Optional[str] = None,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        exceptions: tuple = (Exception,),
        jitter: bool = True,
    ):
        super().__init__(component, name)
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.exceptions = exceptions
        self.jitter = jitter

    async def _execute(self, *args, **kwargs) -> Any:
        """执行重试装饰器"""
        last_exception = None
        current_delay = self.delay

        for attempt in range(1, self.max_attempts + 1):
            try:
                return await self.component.execute(*args, **kwargs)

            except self.exceptions as e:
                last_exception = e

                if attempt == self.max_attempts:
                    # 最后一次尝试失败，抛出异常
                    logger.error(
                        f"Function {self.component.get_name()} failed after "
                        f"{self.max_attempts} attempts. Last error: {str(e)}"
                    )
                    raise

                # 计算下一次重试的延迟
                if self.jitter:
                    # 添加随机抖动，避免雷群效应
                    jitter_delay = current_delay * (0.5 + 0.5 * time.time() % 1)
                else:
                    jitter_delay = current_delay

                logger.warning(
                    f"Function {self.component.get_name()} failed on attempt "
                    f"{attempt}/{self.max_attempts}. "
                    f"Retrying in {jitter_delay:.2f} seconds. Error: {str(e)}"
                )

                await asyncio.sleep(jitter_delay)

                # 更新延迟时间
                current_delay = min(current_delay * self.backoff_factor, self.max_delay)

        # 这行代码实际上不会执行，但为了类型检查器
        raise last_exception


class MetricsDecorator(Decorator):
    """指标收集装饰器，收集函数执行的性能指标"""

    def __init__(
        self,
        component,
        name: Optional[str] = None,
        metrics_collector=None,
        metric_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        track_args: bool = False,
    ):
        super().__init__(component, name)
        self.metrics_collector = metrics_collector or (
            MetricsCollector() if MetricsCollector else None
        )
        self.metric_name = metric_name or f"function.{self.component.get_name()}"
        self.tags = tags or {}
        self.track_args = track_args

    async def _execute(self, *args, **kwargs) -> Any:
        """执行指标收集装饰器"""
        start_time = time.time()
        success = False
        error_type = None

        try:
            # 执行被装饰的函数
            result = await self.component.execute(*args, **kwargs)
            success = True
            return result

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            error_type = type(e).__name__
            raise

        finally:
            # 记录执行时间
            execution_time = time.time() - start_time

            # 构建指标标签
            metric_tags = {
                "function": self.component.get_name(),
                "decorator": self.name,
                "success": str(success),
                **self.tags,
            }

            if error_type:
                metric_tags["error_type"] = error_type

            if self.track_args and args:
                # 可以根据参数类型添加标签
                if hasattr(args[0], "__class__"):
                    metric_tags["arg_type"] = args[0].__class__.__name__

            # 记录指标
            if self.metrics_collector:
                self.metrics_collector.histogram(
                    name=f"{self.metric_name}.duration",
                    value=execution_time,
                    tags=metric_tags,
                )

                self.metrics_collector.counter(
                    name=f"{self.metric_name}.calls",
                    value=1,
                    tags=metric_tags,
                )

                # 记录成功/失败状态
                if success:
                    self.metrics_collector.counter(
                        name=f"{self.metric_name}.success",
                        value=1,
                        tags=metric_tags,
                    )
                else:
                    self.metrics_collector.counter(
                        name=f"{self.metric_name}.error",
                        value=1,
                        tags=metric_tags,
                    )


class ValidationDecorator(Decorator):
    """验证装饰器，验证函数的输入和输出"""

    def __init__(
        self,
        component,
        name: Optional[str] = None,
        input_validators: Optional[List[Validator]] = None,
        output_validators: Optional[List[Validator]] = None,
        validate_args: bool = True,
        validate_kwargs: bool = True,
        validate_result: bool = True,
    ):
        super().__init__(component, name)
        self.input_validators = input_validators or []
        self.output_validators = output_validators or []
        self.validate_args = validate_args
        self.validate_kwargs = validate_kwargs
        self.validate_result = validate_result

        # 如果没有Validator类，禁用验证
        if Validator is None:
            self.input_validators = []
            self.output_validators = []

    async def _execute(self, *args, **kwargs) -> Any:
        """执行验证装饰器"""
        # 验证输入参数
        if self.input_validators and Validator:
            for i, validator in enumerate(self.input_validators):
                if i < len(args):
                    if not validator.validate(args[i]):
                        raise ValidationError(
                            f"Argument {i} validation failed: {validator.get_error_message()}"
                        )

        if self.validate_kwargs and self.input_validators and Validator:
            for key, value in kwargs.items():
                for validator in self.input_validators:
                    if not validator.validate(value):
                        raise ValidationError(
                            f"Argument '{key}' validation failed: {validator.get_error_message()}"
                        )

        # 执行被装饰的函数
        result = await self.component.execute(*args, **kwargs)

        # 验证输出结果
        if self.validate_result and self.output_validators and Validator:
            for validator in self.output_validators:
                if not validator.validate(result):
                    raise ValidationError(
                        f"Result validation failed: {validator.get_error_message()}"
                    )

        return result


class CacheDecorator(Decorator):
    """缓存装饰器，缓存函数的执行结果"""

    def __init__(
        self,
        component,
        name: Optional[str] = None,
        cache_manager=None,
        ttl: Optional[int] = None,
        key_generator: Optional[Callable] = None,
        cache_empty: bool = False,
    ):
        super().__init__(component, name)
        self.cache_manager = cache_manager or (CacheManager() if CacheManager else None)
        self.ttl = ttl
        self.key_generator = key_generator or self._default_key_generator
        self.cache_empty = cache_empty

    async def _execute(self, *args, **kwargs) -> Any:
        """执行缓存装饰器"""
        if not self.cache_manager:
            # 如果没有缓存管理器，直接执行
            return await self.component.execute(*args, **kwargs)

        # 生成缓存键
        cache_key = self.key_generator(*args, **kwargs)

        # 尝试从缓存获取
        cached_result = await self.cache_manager.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for key: {cache_key}")
            return cached_result

        # 缓存未命中，执行函数
        result = await self.component.execute(*args, **kwargs)

        # 缓存结果
        if result is not None or self.cache_empty:
            await self.cache_manager.set(cache_key, result, ttl=self.ttl)
            logger.debug(f"Cached result for key: {cache_key}")

        return result

    def _default_key_generator(self, *args, **kwargs) -> str:
        """默认的缓存键生成器"""
        import hashlib
        import pickle

        # 创建一个包含函数名和参数的字符串
        key_data = {
            "function": self.component.get_name(),
            "args": args,
            "kwargs": sorted(kwargs.items()),
        }

        # 序列化并哈希
        serialized = pickle.dumps(key_data, protocol=pickle.HIGHEST_PROTOCOL)
        hash_digest = hashlib.md5(serialized).hexdigest()

        return f"{self.component.get_name()}:{hash_digest}"


class AuthDecorator(Decorator):
    """认证装饰器，验证用户身份和权限"""

    def __init__(
        self,
        component,
        name: Optional[str] = None,
        auth_service=None,
        required_permissions: Optional[List[str]] = None,
        require_auth: bool = True,
        token_arg_name: str = "token",
        user_arg_name: str = "user",
    ):
        super().__init__(component, name)
        self.auth_service = auth_service or (AuthService() if AuthService else None)
        self.required_permissions = required_permissions or []
        self.require_auth = require_auth
        self.token_arg_name = token_arg_name
        self.user_arg_name = user_arg_name

    async def _execute(self, *args, **kwargs) -> Any:
        """执行认证装饰器"""
        if not self.require_auth:
            # 不需要认证，直接执行
            return await self.component.execute(*args, **kwargs)

        if not self.auth_service:
            # 如果没有认证服务，跳过认证
            return await self.component.execute(*args, **kwargs)

        # 获取token
        token = kwargs.get(self.token_arg_name)
        if not token:
            raise AuthenticationError("Authentication token is required")

        # 验证token
        _user = await self.auth_service.authenticate(token)
        if not user:
            raise AuthenticationError("Invalid authentication token")

        # 检查权限
        if self.required_permissions:
            for permission in self.required_permissions:
                if not await self.auth_service.check_permission(user, permission):
                    raise AuthorizationError(
                        f"User does not have required permission: {permission}"
                    )

        # 将用户信息添加到kwargs中
        kwargs[self.user_arg_name] = user

        # 执行被装饰的函数
        return await self.component.execute(*args, **kwargs)


class RateLimitDecorator(Decorator):
    """限流装饰器，限制函数的调用频率"""

    def __init__(
        self,
        component,
        name: Optional[str] = None,
        rate_limit: int = 100,
        time_window: int = 60,
        key_generator: Optional[Callable] = None,
        key_arg_name: str = "key",
    ):
        super().__init__(component, name)
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.key_generator = key_generator or self._default_key_generator
        self.key_arg_name = key_arg_name
        self._requests: Dict[str, List[datetime]] = {}

    async def _execute(self, *args, **kwargs) -> Any:
        """执行限流装饰器"""
        # 生成限流键
        key = self.key_generator(*args, **kwargs)

        # 清理过期的请求记录
        self._cleanup_expired_requests(key)

        # 检查是否超过限制
        current_time = datetime.utcnow()
        requests = self._requests.get(key, [])

        if len(requests) >= self.rate_limit:
            raise RateLimitError(
                f"Rate limit exceeded. Maximum {self.rate_limit} requests "
                f"per {self.time_window} seconds"
            )

        # 记录当前请求
        requests.append(current_time)
        self._requests[key] = requests

        # 执行被装饰的函数
        return await self.component.execute(*args, **kwargs)

    def _default_key_generator(self, *args, **kwargs) -> str:
        """默认的限流键生成器"""
        # 使用特定的参数作为键
        if self.key_arg_name in kwargs:
            return str(kwargs[self.key_arg_name])

        # 如果没有特定参数，使用第一个参数
        if args:
            return str(args[0])

        # 默认使用函数名
        return self.component.get_name()

    def _cleanup_expired_requests(self, key: str) -> None:
        """清理过期的请求记录"""
        if key not in self._requests:
            return

        current_time = datetime.utcnow()
        cutoff_time = current_time - timedelta(seconds=self.time_window)

        # 过滤出在时间窗口内的请求
        self._requests[key] = [
            request_time
            for request_time in self._requests[key]
            if request_time > cutoff_time
        ]


class TimeoutDecorator(Decorator):
    """超时装饰器，为函数执行设置超时限制"""

    def __init__(
        self,
        component,
        name: Optional[str] = None,
        timeout_seconds: float = 30.0,
        timeout_exception: Type[Exception] = TimeoutError,
    ):
        super().__init__(component, name)
        self.timeout_seconds = timeout_seconds
        self.timeout_exception = timeout_exception

    async def _execute(self, *args, **kwargs) -> Any:
        """执行超时装饰器"""
        try:
            # 使用asyncio.wait_for实现超时
            return await asyncio.wait_for(
                self.component.execute(*args, **kwargs),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            raise self.timeout_exception(
                f"Function {self.component.get_name()} timed out after "
                f"{self.timeout_seconds} seconds"
            )


# 注册所有装饰器
decorator_registry.register("logging", LoggingDecorator)
decorator_registry.register("retry", RetryDecorator)
decorator_registry.register("metrics", MetricsDecorator)
decorator_registry.register("validation", ValidationDecorator)
decorator_registry.register("cache", CacheDecorator)
decorator_registry.register("auth", AuthDecorator)
decorator_registry.register("rate_limit", RateLimitDecorator)
decorator_registry.register("timeout", TimeoutDecorator)
