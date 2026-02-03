#!/usr/bin/env python3
"""
Unified Circuit Breaker - V1.0.0 [Genesis.UnifiedEngine]
==========================================================

统一熔断器实现 - 整合项目中 7 个碎片化的 CircuitBreaker 实现。

整合前:
1. src/core/circuit_breaker.py - 核心熔断器
2. src/collectors/circuit_breaker.py - 采集器熔断器
3. src/api/services/circuit_breaker.py - API 熔断器
4. src/api/fotmob_client.py - FotMob 客户端熔断器
5. src/ml/fault_tolerance.py - ML 容错熔断器
6. src/services/collection_service.py - 收集服务熔断器
7. src/infrastructure/network/core/CircuitBreaker.js - NetworkShield 熔断器

整合后:
- 单一实现: UnifiedCircuitBreaker
- 与 NetworkShield 深度集成
- 支持 IP 级别和引擎级别的熔断
- 统一的配置和状态管理

Core Features:
- 状态机: CLOSED → OPEN → HALF_OPEN → CLOSED
- 与 NetworkShield 集成: 失败自动上报到 active_registry.json
- 双层熔断: IP 级别 + 引擎级别
- 事件系统: state_change, tripped, recovered
- 上下文管理器支持

Author: [Genesis.UnifiedEngine]
Version: V1.0.0
Date: 2026-02-03
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import time
from typing import Any, Dict, List, Optional, TypeVar

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# STATE ENUM
# ============================================================================


class CircuitBreakerState(Enum):
    """熔断器状态枚举"""
    CLOSED = "closed"       # 正常状态，允许请求通过
    OPEN = "open"           # 熔断状态，拒绝请求
    HALF_OPEN = "half_open" # 半开状态，允许测试请求


# ============================================================================
# CONFIGURATION
# ============================================================================


@dataclass
class CircuitBreakerConfig:
    """
    熔断器配置（统一标准）

    默认值基于 NetworkShield 标准:
    - failure_threshold: 2 次（与 NetworkShield 一致）
    - cooldown_minutes: 15 分钟（与 NetworkShield 一致）
    """
    # 失败阈值（连续失败多少次后熔断）
    failure_threshold: int = 2

    # 冷却时间（分钟）
    cooldown_minutes: int = 15

    # 半开状态最大测试请求数
    half_open_max_calls: int = 1

    # 成功阈值（半开状态下连续成功多少次才恢复）
    success_threshold: int = 1

    # 半开状态超时时间（毫秒）
    half_open_timeout_ms: int = 30000

    # 超时时间（秒）
    timeout_seconds: int = 30

    # 是否启用 NetworkShield 集成
    enable_network_shield_integration: bool = True

    # 需要熔断的 HTTP 状态码
    critical_http_codes: set[int] = field(
        default_factory=lambda: {403, 429, 500, 502, 503, 504}
    )

    # 需要熔断的异常类型
    critical_exceptions: tuple = field(
        default_factory=lambda: (TimeoutError, ConnectionError)
    )


# ============================================================================
# STATISTICS
# ============================================================================


@dataclass
class CircuitBreakerStatistics:
    """熔断器统计数据"""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    rejected_executions: int = 0

    consecutive_failures: int = 0
    consecutive_successes: int = 0

    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None

    cooldown_until: Optional[datetime] = None

    state_transitions: Dict[str, int] = field(
        default_factory=lambda: {
            "closed_to_open": 0,
            "open_to_half_open": 0,
            "half_open_to_closed": 0,
            "half_open_to_open": 0,
        }
    )

    current_state: CircuitBreakerState = CircuitBreakerState.CLOSED

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "rejected_executions": self.rejected_executions,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
            "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None,
            "state_transitions": self.state_transitions,
            "current_state": self.current_state.value,
            "success_rate": (
                self.successful_executions / self.total_executions
                if self.total_executions > 0 else 0
            ),
            "failure_rate": (
                self.failed_executions / self.total_executions
                if self.total_executions > 0 else 0
            )
        }


# ============================================================================
# EXCEPTIONS
# ============================================================================


class CircuitBreakerError(Exception):
    """熔断器异常基类"""
    pass


class CircuitBreakerOpenError(CircuitBreakerError):
    """熔断器已打开异常"""

    def __init__(
        self,
        name: str,
        cooldown_until: datetime,
        consecutive_failures: int
    ):
        self.name = name
        self.cooldown_until = cooldown_until
        self.consecutive_failures = consecutive_failures

        remaining = (cooldown_until - datetime.now()).total_seconds()

        super().__init__(
            f"CircuitBreaker '{name}' is OPEN. "
            f"{consecutive_failures} consecutive failures. "
            f"Cooldown until {cooldown_until.isoformat()} "
            f"({remaining:.0f} seconds remaining)"
        )


class CircuitBreakerTimeoutError(CircuitBreakerError):
    """熔断器超时异常"""
    pass


# ============================================================================
# EVENT CALLBACKS
# ============================================================================

T = TypeVar("T")


class EventBus:
    """事件总线（用于熔断器状态变更通知）"""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def on(self, event: str, callback: Callable) -> None:
        """注册事件监听器"""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)

    def emit(self, event: str, data: Any) -> None:
        """触发事件"""
        if event in self._listeners:
            for callback in self._listeners[event]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Event callback error: {e}")


# ============================================================================
# UNIFIED CIRCUIT BREAKER
# ============================================================================


class UnifiedCircuitBreaker:
    """
    统一熔断器 - 整合所有碎片化实现

    与 NetworkShield 深度集成：
    1. 失败时自动调用 mark_proxy_failed()
    2. 成功时自动调用 mark_proxy_success()
    3. 状态变更写入 active_registry.json

    使用示例:
        >>> from ..shared.network_guardian import NetworkGuardian
        >>>
        >>> guardian = await NetworkGuardian()
        >>> breaker = UnifiedCircuitBreaker("fotmob_engine", guardian)
        >>>
        >>> # 方式 1: 上下文管理器
        >>> async with breaker.execute(port=7891) as result:
        >>>     data = await fetch_data()
        >>>     return data
        >>>
        >>> # 方式 2: 手动调用
        >>> try:
        >>>     result = await breaker.call(fetch_data, port=7891)
        >>> except CircuitBreakerOpenError:
        >>>     # 熔断器打开，请求被拒绝
        >>>     pass
    """

    # 类级别配置（与 NetworkShield 同步）
    DEFAULT_CONFIG = CircuitBreakerConfig(
        failure_threshold=2,
        cooldown_minutes=15,
        half_open_max_calls=1,
        success_threshold=1
    )

    def __init__(
        self,
        name: str,
        network_guardian=None,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        初始化熔断器

        Args:
            name: 熔断器名称（用于日志和标识）
            network_guardian: NetworkGuardian 实例（可选）
            config: 熔断器配置（可选，使用默认配置如果为 None）
        """
        self.name = name
        self.config = config or self.DEFAULT_CONFIG
        self._network_guardian = network_guardian

        # 当前状态
        self._state = CircuitBreakerState.CLOSED
        self._state_since = datetime.now()

        # 统计数据
        self._stats = CircuitBreakerStatistics()

        # 事件总线
        self._events = EventBus()

        # 半开状态调用计数
        self._half_open_call_count = 0

        logger.info(
            f"[UnifiedCircuitBreaker] '{name}' initialized "
            f"(threshold: {self.config.failure_threshold}, "
            f"cooldown: {self.config.cooldown_minutes}min, "
            f"NetworkShield: {'enabled' if self._network_guardian else 'disabled'})"
        )

    # ========================================================================
    # PUBLIC PROPERTIES
    # ========================================================================

    @property
    def state(self) -> CircuitBreakerState:
        """获取当前状态"""
        return self._state

    @property
    def statistics(self) -> CircuitBreakerStatistics:
        """获取统计数据"""
        return self._stats

    @property
    def is_open(self) -> bool:
        """检查熔断器是否打开"""
        return self._state == CircuitBreakerState.OPEN

    @property
    def is_closed(self) -> bool:
        """检查熔断器是否关闭"""
        return self._state == CircuitBreakerState.CLOSED

    @property
    def is_half_open(self) -> bool:
        """检查熔断器是否半开"""
        return self._state == CircuitBreakerState.HALF_OPEN

    # ========================================================================
    # CORE METHODS
    # ========================================================================

    async def call(
        self,
        func: Callable[..., T],
        *args: Any,
        port: Optional[int] = None,
        **kwargs: Any
    ) -> T:
        """
        执行带熔断保护的函数调用

        Args:
            func: 要执行的异步函数
            *args: 函数参数
            port: 代理端口（用于 NetworkShield 状态上报）
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果

        Raises:
            CircuitBreakerOpenError: 熔断器打开
            CircuitBreakerTimeoutError: 执行超时
        """
        # 检查状态转换
        self._evaluate_state_transition()

        # 拒绝请求如果熔断器打开
        if self._state == CircuitBreakerState.OPEN:
            self._stats.rejected_executions += 1
            raise CircuitBreakerOpenError(
                self.name,
                self._stats.cooldown_until or datetime.now(),
                self._stats.consecutive_failures
            )

        # 执行请求
        self._stats.total_executions += 1

        try:
            # 超时执行
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout_seconds
            )

            # 记录成功
            self._record_success(port)
            self._stats.successful_executions += 1

            return result

        except asyncio.TimeoutError as e:
            # 超时视为失败
            self._record_failure(port, f"Timeout after {self.config.timeout_seconds}s")
            self._stats.failed_executions += 1
            raise CircuitBreakerTimeoutError(f"Execution timeout: {e}")

        except Exception as e:
            # 记录失败
            self._record_failure(port, str(e))
            self._stats.failed_executions += 1
            raise

    def execute(self, port: Optional[int] = None):
        """
        上下文管理器：执行带熔断保护的代码块

        Args:
            port: 代理端口（用于 NetworkShield 状态上报）

        Returns:
            上下文管理器

        使用示例:
            >>> async with breaker.execute(port=7891) as result:
            >>>     data = await fetch_data()
            >>>     result.set_value(data)
        """
        return _CircuitBreakerContext(self, port)

    # ========================================================================
    # STATE MANAGEMENT
    # ========================================================================

    def _evaluate_state_transition(self) -> None:
        """评估状态转换（基于时间和冷却期）"""
        now = datetime.now()

        # OPEN → HALF_OPEN
        if self._state == CircuitBreakerState.OPEN and self._stats.cooldown_until:
            if now >= self._stats.cooldown_until:
                self._transition_to(CircuitBreakerState.HALF_OPEN)
                self._events.emit("half_open", {
                    "name": self.name,
                    "timestamp": now.isoformat()
                })

        # HALF_OPEN → OPEN (超时)
        elif self._state == CircuitBreakerState.HALF_OPEN:
            elapsed_ms = (now - self._state_since).total_seconds() * 1000
            if elapsed_ms > self.config.half_open_timeout_ms:
                self._transition_to(CircuitBreakerState.OPEN)
                self._events.emit("half_open_timeout", {
                    "name": self.name,
                    "elapsed_ms": elapsed_ms
                })

    def _transition_to(self, new_state: CircuitBreakerState) -> None:
        """转换到新状态"""
        old_state = self._state
        self._state = new_state
        self._state_since = datetime.now()

        # 记录转换
        transition_key = f"{old_state.value}_to_{new_state.value}"
        self._stats.state_transitions[transition_key] = (
            self._stats.state_transitions.get(transition_key, 0) + 1
        )

        # 状态特定逻辑
        if new_state == CircuitBreakerState.OPEN:
            # 设置冷却期
            cooldown_until = datetime.now() + timedelta(minutes=self.config.cooldown_minutes)
            self._stats.cooldown_until = cooldown_until

            # 重置半开计数
            self._half_open_call_count = 0

        elif new_state == CircuitBreakerState.CLOSED:
            # 清除冷却期
            self._stats.cooldown_until = None
            self._half_open_call_count = 0

        # 触发事件
        self._events.emit("state_change", {
            "name": self.name,
            "old_state": old_state.value,
            "new_state": new_state.value,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(
            f"[CircuitBreaker.{self.name}] State transition: "
            f"{old_state.value} → {new_state.value}"
        )

    def _record_success(self, port: Optional[int] = None) -> None:
        """记录成功"""
        self._stats.consecutive_failures = 0
        self._stats.consecutive_successes += 1
        self._stats.last_success_time = datetime.now()

        # 上报到 NetworkShield
        if port and self._network_guardian:
            try:
                # 同步调用（mark_proxy_success 实际上是同步的）
                if asyncio.iscoroutinefunction(self._network_guardian.mark_proxy_success):
                    asyncio.create_task(self._network_guardian.mark_proxy_success(port))
                else:
                    self._network_guardian.mark_proxy_success(port)
            except Exception as e:
                logger.error(f"Failed to report success to NetworkShield: {e}")

        # HALF_OPEN → CLOSED
        if self._state == CircuitBreakerState.HALF_OPEN:
            if self._stats.consecutive_successes >= self.config.success_threshold:
                self._transition_to(CircuitBreakerState.CLOSED)
                self._events.emit("recovered", {
                    "name": self.name,
                    "consecutive_successes": self._stats.consecutive_successes
                })

    def _record_failure(self, port: Optional[int] = None, reason: str = "Unknown") -> None:
        """记录失败"""
        self._stats.consecutive_failures += 1
        self._stats.consecutive_successes = 0
        self._stats.last_failure_time = datetime.now()

        # 上报到 NetworkShield
        if port and self._network_guardian:
            try:
                if asyncio.iscoroutinefunction(self._network_guardian.mark_proxy_failed):
                    asyncio.create_task(self._network_guardian.mark_proxy_failed(port, reason))
                else:
                    self._network_guardian.mark_proxy_failed(port, reason)
            except Exception as e:
                logger.error(f"Failed to report failure to NetworkShield: {e}")

        # CLOSED → OPEN
        if self._state == CircuitBreakerState.CLOSED:
            if self._stats.consecutive_failures >= self.config.failure_threshold:
                self._transition_to(CircuitBreakerState.OPEN)
                self._events.emit("tripped", {
                    "name": self.name,
                    "consecutive_failures": self._stats.consecutive_failures,
                    "reason": reason
                })

        # HALF_OPEN → OPEN
        elif self._state == CircuitBreakerState.HALF_OPEN:
            self._transition_to(CircuitBreakerState.OPEN)

    # ========================================================================
    # MANUAL CONTROL
    # ========================================================================

    def reset(self) -> None:
        """手动重置熔断器"""
        self._transition_to(CircuitBreakerState.CLOSED)
        self._stats.consecutive_failures = 0
        self._stats.consecutive_successes = 0
        self._stats.cooldown_until = None
        self._half_open_call_count = 0

        logger.info(f"[CircuitBreaker.{self.name}] Manually reset")

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._statistics.to_dict()

    # ========================================================================
    # EVENT HANDLING
    # ========================================================================

    def on_state_change(self, callback: Callable) -> None:
        """注册状态变更监听器"""
        self._events.on("state_change", callback)

    def on_tripped(self, callback: Callable) -> None:
        """注册熔断监听器"""
        self._events.on("tripped", callback)

    def on_recovered(self, callback: Callable) -> None:
        """注册恢复监听器"""
        self._events.on("recovered", callback)

    def on_half_open(self, callback: Callable) -> None:
        """注册半开状态监听器"""
        self._events.on("half_open", callback)


# ============================================================================
# CONTEXT MANAGER
# ============================================================================


class _CircuitBreakerContext:
    """熔断器上下文管理器"""

    def __init__(self, breaker: UnifiedCircuitBreaker, port: Optional[int]):
        self._breaker = breaker
        self._port = port
        self._result = None
        self._exception = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # 成功
            self._breaker._record_success(self._port)
        else:
            # 失败
            self._breaker._record_failure(self._port, str(exc_val))

        return False  # 不抑制异常

    def set_value(self, value: Any) -> None:
        """设置返回值"""
        self._result = value


# ============================================================================
# FACTORY & REGISTRY
# ============================================================================

# 全局熔断器注册表
_circuit_breakers: Dict[str, UnifiedCircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    network_guardian=None,
    config: Optional[CircuitBreakerConfig] = None
) -> UnifiedCircuitBreaker:
    """
    获取或创建熔断器（工厂函数）

    Args:
        name: 熔断器名称
        network_guardian: NetworkGuardian 实例
        config: 熔断器配置

    Returns:
        UnifiedCircuitBreaker: 熔断器实例
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = UnifiedCircuitBreaker(
            name=name,
            network_guardian=network_guardian,
            config=config
        )
    return _circuit_breakers[name]


def reset_all_circuit_breakers() -> None:
    """重置所有熔断器"""
    for breaker in _circuit_breakers.values():
        breaker.reset()


def get_all_circuit_breaker_stats() -> Dict[str, Dict[str, Any]]:
    """获取所有熔断器的统计信息"""
    return {
        name: breaker.get_statistics()
        for name, breaker in _circuit_breakers.items()
    }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def execute_with_breaker(
    func: Callable[..., T],
    breaker_name: str,
    network_guardian=None,
    port: Optional[int] = None,
    *args: Any,
    **kwargs: Any
) -> T:
    """
    便捷函数：使用熔断器执行函数

    Args:
        func: 要执行的函数
        breaker_name: 熔断器名称
        network_guardian: NetworkGuardian 实例
        port: 代理端口
        *args, **kwargs: 函数参数

    Returns:
        函数执行结果
    """
    breaker = get_circuit_breaker(breaker_name, network_guardian)
    return await breaker.call(func, *args, port=port, **kwargs)
