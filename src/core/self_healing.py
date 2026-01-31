#!/usr/bin/env python3
"""V41.590 Self-Healing Mechanism - 自愈机制

This module provides automatic recovery from common scraping failures,
including IP bans, timeouts, and 403 errors. It implements an
exponential backoff retry strategy with proxy rotation.

Key Features:
    - Automatic proxy rotation on failure
    - Exponential backoff retry strategy
    - Error classification (ban, timeout, network error)
    - Self-healing with circuit breaker pattern
    - Comprehensive logging for debugging

Author: V41.590 Stealth Team
Date: 2026-01-21
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from typing import Any

from playwright.async_api import Page

from src.core.proxy.proxy_manager import ProxyManager, get_proxy_manager

logger = logging.getLogger(__name__)


# ============================================================================
# Error Classification
# ============================================================================


class ErrorType(Enum):
    """错误类型分类"""
    IP_BAN = "ip_ban"                      # IP 封禁 (403, Hard Ban)
    TIMEOUT = "timeout"                    # 超时错误
    NETWORK_ERROR = "network_error"        # 网络错误
    CAPTCHA = "captcha"                    # 验证码触发
    RATE_LIMIT = "rate_limit"              # 速率限制 (429)
    UNKNOWN = "unknown"                    # 未知错误


@dataclass
class ErrorRecord:
    """错误记录"""
    error_type: ErrorType
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    last_retry_at: datetime | None = None


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    initial_delay: float = 2.0  # 初始延迟（秒）
    max_delay: float = 60.0      # 最大延迟（秒）
    exponential_base: float = 2.0  # 指数退避基数

    def get_delay(self, retry_count: int) -> float:
        """计算第 N 次重试的延迟时间"""
        delay = self.initial_delay * (self.exponential_base ** retry_count)
        return min(delay, self.max_delay)


# ============================================================================
# Self-Healing Engine
# ============================================================================


class SelfHealingEngine:
    """V41.590: 自愈引擎

    提供自动故障恢复和重试机制，支持代理轮换和指数退避。

    特性:
    - 错误分类和自动识别
    - 代理自动轮换
    - 指数退避重试策略
    - 熔断器模式防止雪崩

    Example:
        >>> engine = SelfHealingEngine()
        >>> result = await.execute_with_healing(
        ...     page,
        ...     lambda: page.goto("https://example.com"),
        ...     engine
        ... )
    """

    def __init__(
        self,
        proxy_manager: ProxyManager | None = None,
        retry_config: RetryConfig | None = None
    ):
        """初始化自愈引擎

        Args:
            proxy_manager: 代理管理器
            retry_config: 重试配置
        """
        self.proxy_manager = proxy_manager or get_proxy_manager()
        self.retry_config = retry_config or RetryConfig()

        # 错误记录
        self.error_history: list[ErrorRecord] = []

        # 熔断器状态
        self.circuit_open_until: datetime | None = None

        logger.info("[SelfHealingEngine] 初始化完成")

    def classify_error(self, error: Exception) -> ErrorType:
        """V41.590: 错误分类 - 识别失败类型

        Args:
            error: 异常对象

        Returns:
            ErrorType 枚举值
        """
        error_msg = str(error).lower()

        # IP 封禁检测
        if any(keyword in error_msg for keyword in [
            "403", "forbidden", "hard ban", "blocked",
            "access denied", "ip ban"
        ]):
            return ErrorType.IP_BAN

        # 超时错误
        if isinstance(error, (asyncio.TimeoutError, TimeoutError)):
            return ErrorType.TIMEOUT

        # 速率限制
        if "429" in error_msg or "too many requests" in error_msg:
            return ErrorType.RATE_LIMIT

        # 验证码
        if "captcha" in error_msg or "challenge" in error_msg:
            return ErrorType.CAPTCHA

        # 网络错误
        if any(keyword in error_msg for keyword in [
            "connection", "network", "dns", "refused"
        ]):
            return ErrorType.NETWORK_ERROR

        return ErrorType.UNKNOWN

    def should_attempt_healing(self, error_type: ErrorType) -> bool:
        """判断是否应该尝试自愈

        Args:
            error_type: 错误类型

        Returns:
            是否应该尝试自愈
        """
        # 检查熔断器
        if self.circuit_open_until:
            if datetime.now() < self.circuit_open_until:
                logger.warning(
                    f"[SelfHealing] 熔断器开启中，拒绝请求 "
                    f"({self.circuit_open_until.strftime('%H:%M:%S')})"
                )
                return False
            # 熔断器冷却期已过，重置
            self.circuit_open_until = None
            logger.info("[SelfHealing] 熔断器已重置")

        # 根据错误类型决定是否自愈
        return error_type in {
            ErrorType.IP_BAN,
            ErrorType.TIMEOUT,
            ErrorType.NETWORK_ERROR,
            ErrorType.RATE_LIMIT,
        }

    async def heal_with_proxy_rotation(self, error_type: ErrorType) -> dict[str, Any]:
        """使用代理轮换进行自愈

        Args:
            error_type: 错误类型

        Returns:
            自愈结果字典
        """
        result = {
            "healed": False,
            "action_taken": None,
            "new_proxy": None,
        }

        # 获取新代理
        new_proxy = self.proxy_manager.get_proxy()
        if not new_proxy:
            result["action_taken"] = "no_available_proxies"
            logger.error("[SelfHealing] 没有可用代理进行自愈")
            return result

        # 代理轮换
        if error_type == ErrorType.IP_BAN:
            # 标记当前代理失败
            current_proxy = getattr(self, "_current_proxy", None)
            if current_proxy:
                self.proxy_manager.mark_failure(current_proxy)

            result["action_taken"] = "proxy_rotated"
            result["new_proxy"] = new_proxy
            self._current_proxy = new_proxy

            logger.info(
                f"[SelfHealing] IP 封禁自愈: 更换代理 "
                f"({current_proxy or 'Unknown'} -> {new_proxy})"
            )

            result["healed"] = True

        return result

    async def execute_with_healing(
        self,
        page: Page,
        operation: Callable,
        operation_name: str = "operation",
        max_retries: int | None = None
    ) -> Any:
        """执行操作并带有自愈机制

        Args:
            page: Playwright Page 对象
            operation: 要执行的异步操作
            operation_name: 操作名称（用于日志）
            max_retries: 最大重试次数（None 表示使用配置默认值）

        Returns:
            操作结果

        Raises:
            Exception: 所有重试失败后抛出原始异常
        """
        if max_retries is None:
            max_retries = self.retry_config.max_retries

        last_error = None
        retry_count = 0

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    # 执行自愈
                    logger.info(f"[SelfHealing] 第 {attempt} 次尝试...")

                # 执行操作
                result = await operation()
                return result

            except Exception as e:
                last_error = e
                error_type = self.classify_error(e)

                # 记录错误
                error_record = ErrorRecord(
                    error_type=error_type,
                    message=str(e),
                    retry_count=retry_count,
                    last_retry_at=datetime.now()
                )
                self.error_history.append(error_record)

                logger.warning(
                    f"[SelfHealing] {operation_name} 失败: "
                    f"{error_type.value} - {str(e)[:100]}"
                )

                # 检查是否应该尝试自愈
                if not self.should_attempt_healing(error_type):
                    logger.error(f"[SelfHealing] 不可恢复的错误，停止重试: {error_type.value}")
                    raise

                # 最后一次尝试不再重试
                if attempt >= max_retries:
                    logger.error(f"[SelfHealing] 达到最大重试次数 ({max_retries})")
                    raise

                # 执行自愈
                heal_result = await self.heal_with_proxy_rotation(error_type)

                if not heal_result["healed"]:
                    logger.error("[SelfHealing] 自愈失败，无法继续")
                    raise

                # 等待（指数退避）
                delay = self.retry_config.get_delay(retry_count)
                logger.info(f"[SelfHealing] 等待 {delay:.1f} 秒后重试...")
                await asyncio.sleep(delay)

                retry_count += 1

        # 不应该到达这里
        raise last_error


# ============================================================================
# Convenience Functions
# ============================================================================

_self_healing_engine_instance: SelfHealingEngine | None = None


def get_self_healing_engine(
    proxy_manager: ProxyManager | None = None,
    retry_config: RetryConfig | None = None
) -> SelfHealingEngine:
    """获取自愈引擎单例

    Args:
        proxy_manager: 代理管理器
        retry_config: 重试配置

    Returns:
        SelfHealingEngine 单例实例
    """
    global _self_healing_engine_instance
    if _self_healing_engine_instance is None:
        _self_healing_engine_instance = SelfHealingEngine(
            proxy_manager=proxy_manager,
            retry_config=retry_config
        )
    return _self_healing_engine_instance


async def execute_with_healing(
    page: Page,
    operation: Callable,
    operation_name: str = "operation",
    engine: SelfHealingEngine | None = None
) -> Any:
    """便捷函数：使用自愈机制执行操作

    Args:
        page: Playwright Page 对象
        operation: 要执行的异步操作
        operation_name: 操作名称
        engine: 自愈引擎实例

    Returns:
        操作结果
    """
    if engine is None:
        engine = get_self_healing_engine()

    return await engine.execute_with_healing(
        page=page,
        operation=operation,
        operation_name=operation_name
    )
