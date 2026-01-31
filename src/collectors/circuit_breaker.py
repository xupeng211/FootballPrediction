#!/usr/bin/env python3
"""
爬虫熔断器 (Circuit Breaker)
============================
功能:
1. 记录连续请求失败次数
2. 达到阈值后触发熔断，暂停请求
3. 冷却时间后进入半开状态，尝试恢复
4. 完整的状态管理和告警日志

Author: Security Hardening Officer
Version: 1.0.0
Date: 2025-12-30

状态机设计:
  CLOSED (正常) ──────► OPEN (熔断) ──────► HALF_OPEN (探测)
    │                         ▲                     │
    │ 5次连续失败              │ 10分钟冷却          │
    │                         │                     │
    └─────────────────────────┴─────────────────────┘
              成功后恢复              探测成功
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import time
from typing import Any

from src.ops.alert_manager import AlertSeverity, send_alert_sync

logger = logging.getLogger(__name__)


# ============================================
# 熔断器状态枚举
# ============================================


class CircuitState(Enum):
    """熔断器状态"""

    CLOSED = "closed"  # 正常状态，允许请求通过
    OPEN = "open"  # 熔断状态，拒绝请求
    HALF_OPEN = "half_open"  # 探测状态，允许少量请求测试


# ============================================
# 熔断器异常
# ============================================


class CircuitBreakerOpenError(Exception):
    """熔断器已打开异常"""

    def __init__(self, cooldown_remaining: float):
        self.cooldown_remaining = cooldown_remaining
        super().__init__(f"熔断器已打开，剩余冷却时间: {cooldown_remaining:.0f} 秒")


class CircuitBreakerError(Exception):
    """熔断器基础异常"""


# ============================================
# 熔断器配置
# ============================================


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""

    # 连续失败阈值
    failure_threshold: int = 5

    # 冷却时间（秒）
    cooldown_seconds: int = 600  # 默认 10 分钟

    # 半开状态最大探测次数
    half_open_max_calls: int = 3

    # 成功计数阈值（半开状态下连续成功多少次才恢复）
    success_threshold: int = 2

    # 超时时间（秒）
    timeout_seconds: int = 30

    # 需要熔断的 HTTP 状态码
    critical_http_codes: set[int] = field(default_factory=lambda: {403, 429, 500, 502, 503, 504})

    # 需要熔断的异常类型
    critical_exceptions: tuple = field(default_factory=lambda: (TimeoutError, ConnectionError))


# ============================================
# 熔断器统计
# ============================================


@dataclass
class CircuitBreakerStats:
    """熔断器统计数据"""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0  # 因熔断被拒绝的请求数

    consecutive_failures: int = 0
    consecutive_successes: int = 0

    last_failure_time: float | None = None
    last_success_time: float | None = None

    state_transitions: dict[str, int] = field(
        default_factory=lambda: {
            "closed_to_open": 0,
            "open_to_half_open": 0,
            "half_open_to_closed": 0,
            "half_open_to_open": 0,
        }
    )

    current_state: CircuitState = CircuitState.CLOSED

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "rejected_requests": self.rejected_requests,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "state_transitions": self.state_transitions,
            "current_state": self.current_state.value,
        }


# ============================================
# 熔断器实现
# ============================================


class CircuitBreaker:
    """
    爬虫熔断器

    用于防止级联故障，当外部服务不可用时快速失败

    使用示例:
    >>> breaker = CircuitBreaker(name="fotmob_api")
    >>> async with breaker:
    >>>     response = await fetch_data()
    >>>     return response
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ):
        """
        初始化熔断器

        Args:
            name: 熔断器名称（用于日志区分）
            config: 熔断器配置
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()

        # 当前状态
        self._state = CircuitState.CLOSED
        self._state_since = time.time()

        # 统计数据
        self._stats = CircuitBreakerStats()

        logger.info(
            f"熔断器初始化: {self.name} (阈值: {self.config.failure_threshold}, 冷却: {self.config.cooldown_seconds}s)"
        )

    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        return self._state

    @property
    def stats(self) -> CircuitBreakerStats:
        """获取统计数据"""
        return self._stats

    def _transition_to(self, new_state: CircuitState) -> None:
        """状态转换"""
        old_state = self._state

        if old_state == new_state:
            return

        # 记录转换次数
        transition_key = f"{old_state.value}_to_{new_state.value}"
        if transition_key in self._stats.state_transitions:
            self._stats.state_transitions[transition_key] += 1

        # 更新状态
        self._state = new_state
        self._state_since = time.time()
        self._stats.current_state = new_state

        # 记录日志
        emoji = {"closed": "🟢", "open": "🔴", "half_open": "🟡"}[new_state.value]
        logger.warning(
            f"{emoji} 熔断器 [{self.name}] 状态转换: {old_state.value.upper()} -> {new_state.value.upper()}"
        )

        # P0 安全加固: 发送告警 (CLOSED -> OPEN)
        if new_state == CircuitState.OPEN:
            send_alert_sync(
                title=f"熔断器触发: {self.name}",
                message=f"熔断器 [{self.name}] 已触发，连续失败 {self._stats.consecutive_failures} 次",
                severity=AlertSeverity.CRITICAL,
                alert_type=f"circuit_breaker_open_{self.name}",
                metadata={
                    "breaker_name": self.name,
                    "failure_threshold": self.config.failure_threshold,
                    "consecutive_failures": self._stats.consecutive_failures,
                    "cooldown_seconds": self.config.cooldown_seconds,
                    "total_failures": self._stats.failed_requests,
                },
            )

    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置（从 OPEN 到 HALF_OPEN）"""
        if self._state != CircuitState.OPEN:
            return False

        elapsed = time.time() - self._state_since
        return elapsed >= self.config.cooldown_seconds

    def _record_success(self) -> None:
        """记录成功"""
        self._stats.total_requests += 1
        self._stats.successful_requests += 1
        self._stats.consecutive_successes += 1
        self._stats.consecutive_failures = 0
        self._stats.last_success_time = time.time()

        # 半开状态下，连续成功达到阈值则恢复
        if (
            self._state == CircuitState.HALF_OPEN
            and self._stats.consecutive_successes >= self.config.success_threshold
        ):
            self._transition_to(CircuitState.CLOSED)
            logger.info(f"熔断器 [{self.name}] 已恢复到正常状态")

    def _record_failure(self, exception: Exception | None = None) -> None:
        """记录失败（内部方法）"""
        self._stats.total_requests += 1
        self._stats.failed_requests += 1
        self._stats.consecutive_successes = 0
        self._stats.last_failure_time = time.time()

        # 判断是否是严重错误
        is_critical = self._is_critical_error(exception)

        # 只有严重错误才计入连续失败次数
        if is_critical:
            self._stats.consecutive_failures += 1
            logger.warning(
                f"熔断器 [{self.name}] 记录严重错误: {type(exception).__name__ if exception else 'Unknown'} "
                f"(连续失败: {self._stats.consecutive_failures}/{self.config.failure_threshold})"
            )

            # 连续失败达到阈值，打开熔断器
            if self._stats.consecutive_failures >= self.config.failure_threshold:
                if self._state != CircuitState.OPEN:
                    self._transition_to(CircuitState.OPEN)
                    logger.error(
                        f"🔴 熔断器 [{self.name}] 已触发! "
                        f"连续失败 {self._stats.consecutive_failures} 次，"
                        f"冷却 {self.config.cooldown_seconds} 秒..."
                    )
        else:
            # 非关键错误不计入连续失败，但仍记录为失败请求
            logger.debug(
                f"熔断器 [{self.name}] 记录非关键错误: {type(exception).__name__ if exception else 'Unknown'} "
                f"(不计入熔断阈值)"
            )

    def record_failure(self, reason: str | None = None, is_critical: bool = True) -> None:
        """V149.0: 公开方法 - 手动记录失败（用于外部熔断触发）

        这是 HarvesterService 用来"硬接线"熔断器的公开接口。
        当检测到 IP 硬封（如 39 字节错误）时，直接调用此方法触发熔断。

        Args:
            reason: 失败原因描述（如 "IP Hard Ban: 39 bytes"）
            is_critical: 是否为严重错误（默认 True，计入连续失败阈值）

        Example:
            >>> breaker = CircuitBreaker("oddsportal")
            >>> breaker.record_failure("IP Hard Ban: 39 bytes", is_critical=True)
            >>> if breaker.state == CircuitState.OPEN:
            >>>     print("熔断器已触发，进入冷却期")
        """
        self._stats.total_requests += 1
        self._stats.failed_requests += 1
        self._stats.consecutive_successes = 0
        self._stats.last_failure_time = time.time()

        if is_critical:
            self._stats.consecutive_failures += 1
            logger.warning(
                f"🔴 熔断器 [{self.name}] 手动记录关键失败: {reason} "
                f"(连续失败: {self._stats.consecutive_failures}/{self.config.failure_threshold})"
            )

            # 连续失败达到阈值，打开熔断器
            if self._stats.consecutive_failures >= self.config.failure_threshold:
                if self._state != CircuitState.OPEN:
                    self._transition_to(CircuitState.OPEN)
                    logger.error(
                        f"🔴 熔断器 [{self.name}] 已触发! "
                        f"连续失败 {self._stats.consecutive_failures} 次，"
                        f"冷却 {self.config.cooldown_seconds} 秒..."
                    )
                    # V149.0: 自动退出 EXIT 99
                    logger.critical("⛔ CIRCUIT_BREAKER: IP Hard Ban Detected - EXIT 99")
                    import sys

                    sys.exit(99)
        else:
            logger.debug(f"熔断器 [{self.name}] 手动记录非关键失败: {reason} (不计入熔断阈值)")

    def _is_critical_error(self, exception: Exception | None) -> bool:
        """判断是否是严重错误"""
        if exception is None:
            return False

        # 检查是否是关键异常类型
        if isinstance(exception, self.config.critical_exceptions):
            return True

        # 检查 HTTP 错误
        if hasattr(exception, "status"):
            # aiohttp ClientResponse
            if exception.status in self.config.critical_http_codes:
                return True

        # 检查特殊的错误属性
        if hasattr(exception, "http_status"):
            if exception.http_status in self.config.critical_http_codes:
                return True

        return False

    def can_proceed(self) -> bool:
        """
        检查是否可以继续执行请求

        Returns:
            True 可以继续，False 应该拒绝
        """
        # 如果是 OPEN 状态，检查是否可以转换到 HALF_OPEN
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            return False

        return True

    def get_cooldown_remaining(self) -> float:
        """
        获取剩余冷却时间

        Returns:
            剩余秒数，如果不在冷却期则返回 0
        """
        if self._state != CircuitState.OPEN:
            return 0

        elapsed = time.time() - self._state_since
        remaining = self.config.cooldown_seconds - elapsed
        return max(0, remaining)

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        通过熔断器调用函数

        Args:
            func: 要调用的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数返回值

        Raises:
            CircuitBreakerOpenError: 熔断器已打开
            Exception: 函数执行异常
        """
        # 检查是否可以继续
        if not self.can_proceed():
            remaining = self.get_cooldown_remaining()
            self._stats.rejected_requests += 1
            raise CircuitBreakerOpenError(remaining)

        try:
            # 调用函数
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout_seconds,
                )
            else:
                result = func(*args, **kwargs)

            # 记录成功
            self._record_success()
            return result

        except TimeoutError as e:
            self._record_failure(e)
            raise

        except Exception as e:
            self._record_failure(e)
            raise

    def __enter__(self) -> "CircuitBreaker":
        """上下文管理器入口"""
        if not self.can_proceed():
            remaining = self.get_cooldown_remaining()
            self._stats.rejected_requests += 1
            raise CircuitBreakerOpenError(remaining)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """上下文管理器出口"""
        if exc_type is None:
            self._record_success()
        else:
            self._record_failure(exc_val)

    async def __aenter__(self) -> "CircuitBreaker":
        """异步上下文管理器入口"""
        if not self.can_proceed():
            remaining = self.get_cooldown_remaining()
            self._stats.rejected_requests += 1
            raise CircuitBreakerOpenError(remaining)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """异步上下文管理器出口"""
        if exc_type is None:
            self._record_success()
        else:
            self._record_failure(exc_val)

    def reset(self) -> None:
        """重置熔断器状态（用于测试或手动恢复）"""
        self._state = CircuitState.CLOSED
        self._state_since = time.time()
        self._stats = CircuitBreakerStats()
        logger.info(f"熔断器 [{self.name}] 已手动重置")

    def get_status(self) -> dict:
        """
        获取熔断器状态

        Returns:
            状态字典
        """
        return {
            "name": self.name,
            "state": self._state.value,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "cooldown_seconds": self.config.cooldown_seconds,
                "half_open_max_calls": self.config.half_open_max_calls,
                "success_threshold": self.config.success_threshold,
            },
            "stats": self._stats.to_dict(),
            "cooldown_remaining": self.get_cooldown_remaining(),
        }


# ============================================
# 熔断器管理器（单例模式）
# ============================================


class CircuitBreakerManager:
    """
    熔断器管理器

    用于管理多个熔断器实例
    """

    _instance = None
    _breakers: dict[str, CircuitBreaker] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_breaker(
        cls,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> CircuitBreaker:
        """
        获取或创建熔断器

        Args:
            name: 熔断器名称
            config: 熔断器配置

        Returns:
            CircuitBreaker 实例
        """
        if name not in cls._breakers:
            cls._breakers[name] = CircuitBreaker(name, config)
        return cls._breakers[name]

    @classmethod
    def reset_all(cls) -> None:
        """重置所有熔断器"""
        for breaker in cls._breakers.values():
            breaker.reset()
        logger.info("所有熔断器已重置")

    @classmethod
    def get_all_status(cls) -> dict[str, dict]:
        """获取所有熔断器状态"""
        return {name: breaker.get_status() for name, breaker in cls._breakers.items()}


# ============================================
# 便捷装饰器
# ============================================


def with_circuit_breaker(
    breaker_name: str | None = None,
    config: CircuitBreakerConfig | None = None,
):
    """
    熔断器装饰器

    使用示例:
    >>> @with_circuit_breaker("api_call")
    >>> async def fetch_data():
    >>>     ...
    """

    def decorator(func: Callable) -> Callable:
        name = breaker_name or func.__name__

        async def async_wrapper(*args, **kwargs):
            breaker = CircuitBreakerManager.get_breaker(name, config)
            return await breaker.call(func, *args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            breaker = CircuitBreakerManager.get_breaker(name, config)
            return breaker.call(func, *args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ============================================
# 使用示例
# ============================================


if __name__ == "__main__":
    import random

    async def demo():
        """熔断器演示"""
        logging.basicConfig(level=logging.INFO)

        # 创建熔断器
        config = CircuitBreakerConfig(
            failure_threshold=3,
            cooldown_seconds=10,
            half_open_max_calls=2,
        )
        breaker = CircuitBreaker("demo_api", config)

        async def unreliable_api():
            """模拟不可靠的 API"""
            if random.random() < 0.5:
                # 模拟 429 错误
                class TooManyRequestsError(Exception):
                    status = 429

                raise TooManyRequestsError("Too many requests")
            return {"data": "success"}

        # 模拟多次调用
        for _i in range(15):
            try:
                await breaker.call(unreliable_api)
            except CircuitBreakerOpenError:
                pass
            except Exception:
                pass

            await asyncio.sleep(0.5)

    asyncio.run(demo())
