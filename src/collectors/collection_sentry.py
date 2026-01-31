#!/usr/bin/env python3
"""
V26.5 自动巡航哨兵 (Cruise Sentry) - 自动停机保护
==================================================

核心功能：
    1. 滑动窗口统计（最近 N 个结果）
    2. 成功率监控（低于阈值触发停机）
    3. 连续失败监控（超过阈值触发停机）
    4. 强制设置 COLLECTION_PAUSE_UNTIL
    5. 抛出 SentryInterrupt 异常终止程序

设计原则：
    - 安全第一：宁可误停，不可不停
    - 透明监控：实时健康度可查询
    - 自动恢复：12 小时冷却后自动解除

Author: TDD Expert & DevOps Architect
Version: V26.5
Date: 2026-01-06
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
import logging
import os
from typing import Any

from src.collectors.base_extractor import SecurityInterrupt

logger = logging.getLogger(__name__)


# ============================================================================
# 自动巡航哨兵
# ============================================================================


class CollectionSentry:
    """
    V26.5 自动巡航哨兵 - 采集健康监控与自动停机保护

    功能：
        1. 实时监控采集成功率
        2. 检测连续失败
        3. 触发停机保护
        4. 强制冷却期

    使用示例：
        >>> sentry = CollectionSentry(
        ...     window_size=100,
        ...     success_rate_threshold=0.7,
        ...     consecutive_failure_threshold=5,
        ... )
        >>> for match in matches:
        ...     success = harvest(match)
        ...     sentry.record_result(success)
        ...     sentry.check_health_or_stop()  # 不健康会抛出异常
    """

    def __init__(
        self,
        window_size: int = 100,
        success_rate_threshold: float = 0.7,
        consecutive_failure_threshold: int = 5,
        pause_duration_hours: int = 12,
    ):
        """
        初始化自动巡航哨兵

        Args:
            window_size: 滑动窗口大小（最近 N 个结果）
            success_rate_threshold: 成功率阈值（低于此值触发停机）
            consecutive_failure_threshold: 连续失败阈值（超过此值触发停机）
            pause_duration_hours: 强制冷却期时长（小时）
        """
        self.window_size = window_size
        self.success_rate_threshold = success_rate_threshold
        self.consecutive_failure_threshold = consecutive_failure_threshold
        self.pause_duration = timedelta(hours=pause_duration_hours)

        # 滑动窗口（使用 deque 实现自动裁剪）
        self.result_history: deque[bool] = deque(maxlen=window_size)

        # 连续失败计数
        self._consecutive_failures = 0

        logger.info(
            f"🤖 CollectionSentry 初始化: "
            f"窗口={window_size}, "
            f"成功率阈值={success_rate_threshold:.0%}, "
            f"连续失败阈值={consecutive_failure_threshold}"
        )

    # ========================================
    # 核心监控方法
    # ========================================

    def record_result(self, success: bool) -> None:
        """
        记录采集结果

        Args:
            success: True 表示成功，False 表示失败
        """
        self.result_history.append(success)

        # 更新连续失败计数
        if success:
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1

        logger.debug(
            f"📊 记录结果: {'✅' if success else '❌'} | "
            f"成功率={self.get_success_rate():.1%} | "
            f"连续失败={self._consecutive_failures}"
        )

    def check_health(self) -> bool:
        """
        检查健康状态（不抛出异常）

        Returns:
            True 表示健康，False 表示不健康

        停机条件（两个都满足才停机）：
            1. 成功率低于阈值
            2. 连续失败超过阈值
        """
        # 检查 1: 成功率是否低于阈值
        success_rate = self.get_success_rate()
        rate_below_threshold = success_rate < self.success_rate_threshold

        # 检查 2: 连续失败是否超过阈值
        # 注意：连续失败 >= 6 才算超过 5（即 > 5）
        consecutive_failures_above_threshold = (
            self._consecutive_failures > self.consecutive_failure_threshold
        )

        # 只有两个条件都满足时才认为不健康
        is_unhealthy = rate_below_threshold and consecutive_failures_above_threshold

        if is_unhealthy:
            logger.warning(
                f"⚠️ 哨兵报警: 成功率={success_rate:.1%} < {self.success_rate_threshold:.1%}, "
                f"连续失败={self._consecutive_failures} >= {self.consecutive_failure_threshold}"
            )

        return not is_unhealthy

    def check_health_or_stop(self) -> None:
        """
        检查健康状态，不健康时触发停机保护

        Raises:
            SecurityInterrupt: 当健康度不达标时，强制停机

        停机保护措施：
            1. 设置 COLLECTION_PAUSE_UNTIL 环境变量
            2. 抛出 SecurityInterrupt 异常
            3. 记录详细日志
        """
        if not self.check_health():
            # 触发停机保护
            self._trigger_emergency_stop()

    # ========================================
    # 停机保护逻辑
    # ========================================

    def _trigger_emergency_stop(self) -> None:
        """
        触发紧急停机保护

        停机措施：
            1. 设置 COLLECTION_PAUSE_UNTIL 环境变量（12 小时后）
            2. 抛出 SecurityInterrupt 异常
            3. 记录详细日志
        """
        # 计算冷却截止时间
        pause_until = datetime.now() + self.pause_duration
        pause_until_str = pause_until.isoformat()

        # 设置环境变量
        os.environ["COLLECTION_PAUSE_UNTIL"] = pause_until_str

        # 获取失败原因
        success_rate = self.get_success_rate()
        failure_reason = []
        if success_rate < self.success_rate_threshold:
            failure_reason.append(
                f"成功率低于阈值 ({success_rate:.1%} < {self.success_rate_threshold:.1%})"
            )
        if self._consecutive_failures >= self.consecutive_failure_threshold:
            failure_reason.append(
                f"连续失败 {self._consecutive_failures} 次（阈值: {self.consecutive_failure_threshold}）"
            )

        # 构造异常消息
        error_message = (
            f"🛑 自动巡航哨兵触发停机保护\n"
            f"⏰ 停机时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"⏳ 冷却截止: {pause_until_str}\n"
            f"📊 停机原因:\n"
        )
        for i, reason in enumerate(failure_reason, 1):
            error_message += f"   {i}. {reason}\n"

        error_message += (
            "\n"
            "💡 系统将在冷却期结束后自动恢复。\n"
            "💡 如需立即恢复，请手动清除 COLLECTION_PAUSE_UNTIL 环境变量。"
        )

        # 记录日志
        logger.error("=" * 80)
        logger.error("🛑 自动巡航哨兵 - 触发停机保护")
        logger.error(error_message)
        logger.error("=" * 80)

        # 抛出异常
        raise SecurityInterrupt(error_message)

    # ========================================
    # 统计查询方法
    # ========================================

    def get_success_rate(self) -> float:
        """
        获取当前成功率

        Returns:
            成功率（0.0 - 1.0），如果无历史记录返回 0
        """
        if not self.result_history:
            return 0.0

        success_count = sum(1 for result in self.result_history if result)
        return success_count / len(self.result_history)

    def get_consecutive_failures(self) -> int:
        """
        获取当前连续失败次数

        Returns:
            连续失败次数
        """
        return self._consecutive_failures

    def get_summary(self) -> dict[str, Any]:
        """
        获取哨兵状态摘要

        Returns:
            状态摘要字典
        """
        total_requests = len(self.result_history)
        successful_requests = sum(1 for result in self.result_history if result)
        failed_requests = total_requests - successful_requests

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": self.get_success_rate(),
            "consecutive_failures": self._consecutive_failures,
            "is_healthy": self.check_health(),
            "threshold": {
                "success_rate": self.success_rate_threshold,
                "consecutive_failures": self.consecutive_failure_threshold,
            },
        }

    def reset(self) -> None:
        """
        重置哨兵状态

        用于新批次或手动恢复
        """
        self.result_history.clear()
        self._consecutive_failures = 0

        logger.info("🔄 CollectionSentry 状态已重置")


# ============================================================================
# 便捷函数
# ============================================================================


def create_collection_sentry(
    window_size: int = 100,
    success_rate_threshold: float = 0.7,
    consecutive_failure_threshold: int = 5,
    pause_duration_hours: int = 12,
) -> CollectionSentry:
    """
    创建自动巡航哨兵（工厂函数）

    Args:
        window_size: 滑动窗口大小
        success_rate_threshold: 成功率阈值
        consecutive_failure_threshold: 连续失败阈值
        pause_duration_hours: 冷却期时长

    Returns:
        CollectionSentry 实例
    """
    return CollectionSentry(
        window_size=window_size,
        success_rate_threshold=success_rate_threshold,
        consecutive_failure_threshold=consecutive_failure_threshold,
        pause_duration_hours=pause_duration_hours,
    )
