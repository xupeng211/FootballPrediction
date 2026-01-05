#!/usr/bin/env python3
"""V105.0 熔断器模式实现 (Circuit Breaker Pattern).

实现工业级熔断器，用于保护系统免受级联故障影响：
1. **CLOSED 状态**: 正常运行，请求正常通过
2. **OPEN 状态**: 熔断开启，快速失败，阻止请求
3. **HALF_OPEN 状态**: 半开状态，允许部分请求探测服务是否恢复

Usage:
    >>> from src.core.circuit_breaker import CircuitBreaker
    >>> breaker = CircuitBreaker(
    ...     failure_threshold=3,
    ...     recovery_timeout=60,
    ...     expected_exception=Exception
    ... )
    >>> with breaker:
    ...     result = make_request()  # 如果失败次数过多，将被阻止
"""

import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """熔断器状态枚举"""

    CLOSED = "CLOSED"  # 正常状态
    OPEN = "OPEN"  # 熔断开启
    HALF_OPEN = "HALF_OPEN"  # 半开状态（探测中）


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""

    failure_threshold: int = 5  # 失败阈值（连续失败多少次后熔断）
    recovery_timeout: int = 60  # 恢复超时（秒）- 熔断后等待多久尝试恢复
    expected_exception: type[Exception] = Exception  # 预期的异常类型
    success_threshold: int = 2  # 半开状态下成功多少次后恢复
    timeout: float = 30.0  # 请求超时时间
    name: str = "default"  # 熔断器名称（用于日志）


@dataclass
class CircuitBreakerState:
    """熔断器当前状态"""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: datetime | None = None
    last_success_time: datetime | None = None
    opened_at: datetime | None = None

    def reset(self) -> None:
        """重置状态"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.opened_at = None


class CircuitBreakerError(Exception):
    """熔断器异常基类"""



class CircuitBreakerOpenError(CircuitBreakerError):
    """熔断器已开启异常"""

    def __init__(self, name: str, recovery_timeout: int) -> None:
        self.name = name
        self.recovery_timeout = recovery_timeout
        super().__init__(
            f"熔断器 '{name}' 已开启。将在 {recovery_timeout} 秒后尝试恢复。"
        )


class CircuitBreaker:
    """熔断器实现.

    保护系统免受级联故障影响，当检测到故障时自动熔断。

    Attributes:
        config: 熔断器配置
        state: 当前状态
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] = Exception,
        success_threshold: int = 2,
        timeout: float = 30.0,
        name: str = "default"
    ):
        """初始化熔断器.

        Args:
            failure_threshold: 失败阈值（默认 5 次）
            recovery_timeout: 恢复超时时间（默认 60 秒）
            expected_exception: 预期的异常类型
            success_threshold: 半开状态成功阈值（默认 2 次）
            timeout: 请求超时时间（默认 30 秒）
            name: 熔断器名称
        """
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            success_threshold=success_threshold,
            timeout=timeout,
            name=name
        )
        self.state = CircuitBreakerState()
        self._lock = asyncio.Lock()

    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置熔断器"""
        if self.state.opened_at is None:
            return False

        elapsed = (datetime.now() - self.state.opened_at).total_seconds()
        return elapsed >= self.config.recovery_timeout

    def _record_success(self) -> None:
        """记录成功"""
        self.state.success_count += 1
        self.state.failure_count = 0
        self.state.last_success_time = datetime.now()

        if self.state.state == CircuitState.HALF_OPEN:
            if self.state.success_count >= self.config.success_threshold:
                self.state.state = CircuitState.CLOSED
                logger.info(
                    f"🔧 熔断器 '{self.config.name}' 已恢复到 CLOSED 状态"
                )

    def _record_failure(self) -> None:
        """记录失败"""
        self.state.failure_count += 1
        self.state.last_failure_time = datetime.now()

        if self.state.state == CircuitState.HALF_OPEN:
            # 半开状态下失败，重新开启熔断
            self.state.state = CircuitState.OPEN
            self.state.opened_at = datetime.now()
            logger.warning(
                f"⚠️ 熔断器 '{self.config.name}' 在 HALF_OPEN 状态下失败，重新开启"
            )
        elif self.state.failure_count >= self.config.failure_threshold:
            # 达到失败阈值，开启熔断
            self.state.state = CircuitState.OPEN
            self.state.opened_at = datetime.now()
            logger.error(
                f"🔴 熔断器 '{self.config.name}' 已开启 "
                f"(连续失败 {self.state.failure_count} 次)"
            )

    @contextmanager
    def __call__(self):
        """上下文管理器 - 同步版本"""
        self._ensure_closed()
        try:
            yield self
            self._record_success()
        except self.config.expected_exception:
            self._record_failure()
            raise

    @asynccontextmanager
    async def __aenter__(self):
        """异步上下文管理器"""
        await self._ensure_closed_async()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if exc_type is not None and issubclass(exc_type, self.config.expected_exception):
            self._record_failure()
        else:
            self._record_success()

    def _ensure_closed(self) -> None:
        """确保熔断器关闭（同步版本）"""
        if self.state.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(
                    f"🔧 熔断器 '{self.config.name}' 尝试恢复到 HALF_OPEN 状态"
                )
                self.state.state = CircuitState.HALF_OPEN
                self.state.success_count = 0
            else:
                raise CircuitBreakerOpenError(
                    self.config.name,
                    self.config.recovery_timeout
                )

    async def _ensure_closed_async(self) -> None:
        """确保熔断器关闭（异步版本）"""
        async with self._lock:
            self._ensure_closed()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """同步调用包装函数.

        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数执行结果

        Raises:
            CircuitBreakerOpenError: 熔断器已开启
            Exception: 函数执行异常
        """
        self._ensure_closed()
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.config.expected_exception:
            self._record_failure()
            raise

    async def acall(self, coro: Callable, *args, **kwargs) -> Any:
        """异步调用包装协程.

        Args:
            coro: 要执行的协程函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            协程执行结果

        Raises:
            CircuitBreakerOpenError: 熔断器已开启
            Exception: 协程执行异常
        """
        async with self._lock:
            self._ensure_closed()

        try:
            result = await asyncio.wait_for(
                coro(*args, **kwargs),
                timeout=self.config.timeout
            )
            self._record_success()
            return result
        except TimeoutError:
            self._record_failure()
            raise
        except self.config.expected_exception:
            self._record_failure()
            raise

    def reset(self) -> None:
        """手动重置熔断器"""
        self.state.reset()
        logger.info(f"🔄 熔断器 '{self.config.name}' 已手动重置")

    def get_state(self) -> dict:
        """获取熔断器当前状态（用于监控）"""
        return {
            "name": self.config.name,
            "state": self.state.state.value,
            "failure_count": self.state.failure_count,
            "success_count": self.state.success_count,
            "last_failure_time": self.state.last_failure_time.isoformat() if self.state.last_failure_time else None,
            "last_success_time": self.state.last_success_time.isoformat() if self.state.last_success_time else None,
            "opened_at": self.state.opened_at.isoformat() if self.state.opened_at else None,
        }


# ============================================================================
# 预配置的熔断器实例
# ============================================================================

# 网络请求熔断器
network_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=300,  # 5 分钟
    expected_exception=(ConnectionError, TimeoutError),
    name="network_requests"
)

# API 请求熔断器
api_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,  # 1 分钟
    expected_exception=Exception,
    name="api_requests"
)

# 数据库熔断器
database_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=120,  # 2 分钟
    expected_exception=Exception,
    name="database_operations"
)
