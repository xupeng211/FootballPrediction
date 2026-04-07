#!/usr/bin/env python3
"""V144.8 Circuit Breaker - IP Ban Protection (39 bytes).

Implements automatic circuit breaker for IP Hard Ban detection:
- Tracks consecutive IP ban failures (39 bytes)
- Triggers sys.exit(99) when threshold exceeded
- Protects proxy pool reputation
- Records critical errors to logs

Author: V144.8 SRE Team
Version: 1.0.0
Date: 2026-01-06
"""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
import logging
from pathlib import Path
import sys
from typing import Any, Literal, TypedDict

logger = logging.getLogger(__name__)

CIRCUIT_BREAKER_LOG = Path("logs/circuit_breaker.log")
CIRCUIT_BREAKER_LOG.parent.mkdir(parents=True, exist_ok=True)
DEFAULT_THRESHOLD = 3
LOG_TAIL_SIZE = 5


class FailureRecord(TypedDict):
    """熔断失败记录。"""

    timestamp: str
    reason: str
    proxy: str | None
    consecutive_count: int


def _utc_now_iso() -> str:
    """返回 UTC ISO 时间戳。"""
    return datetime.now(UTC).isoformat()


class CircuitBreaker:
    """V144.8: Circuit breaker for IP Hard Ban protection."""

    HARD_BAN_SIGNATURE = "IP Hard Ban (39 bytes)"
    HARD_BAN_LENGTH = 39

    def __init__(self, threshold: int = DEFAULT_THRESHOLD) -> None:
        self.threshold = threshold
        self.consecutive_failures = 0
        self.failure_history: list[FailureRecord] = []

    def is_hard_ban(self, content: str | bytes) -> bool:
        """检查响应内容是否命中硬封禁签名。"""
        content_str = (
            content.decode("utf-8", errors="ignore") if isinstance(content, bytes) else str(content)
        )
        content_len = len(content_str)
        if content_len == self.HARD_BAN_LENGTH:
            logger.critical("[V144.8] 检测到 IP 硬封禁签名: %s 字节", content_len)
            return True
        return False

    def record_failure(self, reason: str, proxy: str | None = None) -> None:
        """记录失败并在达到阈值时触发熔断。"""
        if not self._reason_is_hard_ban(reason):
            self.consecutive_failures = 0
            logger.debug("[V144.8] 非 IP 硬封禁错误, 重置计数器")
            return

        self.consecutive_failures += 1
        failure_record: FailureRecord = {
            "timestamp": _utc_now_iso(),
            "reason": reason,
            "proxy": proxy,
            "consecutive_count": self.consecutive_failures,
        }
        self.failure_history.append(failure_record)
        self._log_failure(failure_record)

        logger.critical(
            "[V144.8] IP 硬封禁计数: %s/%s",
            self.consecutive_failures,
            self.threshold,
        )

        if self.consecutive_failures >= self.threshold:
            self._trigger_shutdown()

    def is_triggered(self) -> bool:
        """返回熔断器是否已经到达阈值。"""
        return self.consecutive_failures >= self.threshold

    def reset(self) -> None:
        """重置熔断器状态。"""
        old_count = self.consecutive_failures
        self.consecutive_failures = 0
        self.failure_history.clear()
        logger.info("[V144.8] 熔断器已重置 (之前计数: %s)", old_count)

    def get_status(self) -> dict[str, Any]:
        """返回当前熔断器状态。"""
        return {
            "threshold": self.threshold,
            "consecutive_failures": self.consecutive_failures,
            "is_critical": self.is_triggered(),
            "recent_failures": len(self.failure_history),
        }

    def _reason_is_hard_ban(self, reason: str) -> bool:
        """根据错误原因判断是否为硬封禁。"""
        if self.HARD_BAN_SIGNATURE in reason:
            return True

        if "bytes" not in reason:
            return False

        try:
            last_token = reason.split()[-1].rstrip(")")
            return int(last_token) == self.HARD_BAN_LENGTH
        except (IndexError, ValueError):
            return False

    def _log_failure(self, failure_record: FailureRecord) -> None:
        """将失败信息写入本地日志。"""
        try:
            with CIRCUIT_BREAKER_LOG.open("a", encoding="utf-8") as file_obj:
                file_obj.write(f"{failure_record['timestamp']} | ")
                file_obj.write(f"Proxy: {failure_record['proxy'] or 'Unknown'} | ")
                file_obj.write(f"Reason: {failure_record['reason']} | ")
                file_obj.write(f"Count: {failure_record['consecutive_count']}/{self.threshold}\n")
        except OSError:
            logger.exception("[V144.8] 写入熔断日志失败")

    def _trigger_shutdown(self) -> None:
        """触发关机保护。"""
        logger.critical("")
        logger.critical("%s", "=" * 80)
        logger.critical("[V144.8] 熔断器触发! 立即关机保护代理池")
        logger.critical("%s", "=" * 80)
        logger.critical("原因: 连续 %s 次检测到 IP 硬封禁", self.consecutive_failures)
        logger.critical("阈值: %s 次", self.threshold)
        logger.critical("操作: 系统将执行 sys.exit(99) 强制关机")
        logger.critical("")
        logger.critical("失败历史:")

        for index, record in enumerate(reversed(self.failure_history[-LOG_TAIL_SIZE:]), start=1):
            logger.critical(
                "  %s. %s | %s | %s",
                index,
                record["timestamp"],
                record["proxy"],
                record["reason"],
            )

        logger.critical("%s", "=" * 80)
        logger.critical("")

        try:
            with CIRCUIT_BREAKER_LOG.open("a", encoding="utf-8") as file_obj:
                file_obj.write("\n")
                file_obj.write("=" * 80 + "\n")
                file_obj.write("[V144.8] CIRCUIT BREAKER TRIGGERED - SHUTDOWN\n")
                file_obj.write(f"Timestamp: {_utc_now_iso()}\n")
                file_obj.write(
                    f"Consecutive Failures: {self.consecutive_failures}/{self.threshold}\n"
                )
                file_obj.write("Action: sys.exit(99)\n")
                file_obj.write("=" * 80 + "\n\n")
        except OSError:
            logger.exception("[V144.8] 写入最终熔断日志失败")

        sys.exit(99)


@lru_cache(maxsize=1)
def get_circuit_breaker(threshold: int = DEFAULT_THRESHOLD) -> CircuitBreaker:
    """获取全局熔断器实例。"""
    logger.info("[V144.8] 熔断器已初始化 (阈值: %s)", threshold)
    return CircuitBreaker(threshold=threshold)


def check_hard_ban_and_trip(
    content: str | bytes,
    proxy: str | None = None,
) -> Literal["continue", "trip"]:
    """检测硬封禁并在需要时触发熔断。"""
    breaker = get_circuit_breaker()
    if breaker.is_hard_ban(content):
        breaker.record_failure(breaker.HARD_BAN_SIGNATURE, proxy)
        return "trip"

    breaker.consecutive_failures = 0
    return "continue"
