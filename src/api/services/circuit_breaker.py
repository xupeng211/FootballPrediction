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

from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import Any, Literal

logger = logging.getLogger(__name__)

# Circuit breaker state
CIRCUIT_BREAKER_LOG = Path("logs/circuit_breaker.log")
CIRCUIT_BREAKER_LOG.parent.mkdir(parents=True, exist_ok=True)


class CircuitBreaker:
    """V144.8: Circuit breaker for IP Hard Ban protection.

    Detects consecutive IP ban failures (39 bytes response) and
    triggers system shutdown to protect proxy pool reputation.

    Features:
        - Tracks consecutive failures across all proxy attempts
        - Triggers sys.exit(99) when threshold exceeded (3 consecutive bans)
        - Records detailed failure history
        - Protects proxy pool from being completely burned

    Attributes:
        threshold: Maximum consecutive failures before triggering (default: 3)
        consecutive_failures: Current count of consecutive IP bans
        failure_history: List of recent failure records

    Example:
        >>> breaker = CircuitBreaker(threshold=3)
        >>> breaker.record_failure("IP Hard Ban (39 bytes)", "proxy1:7890")
        >>> if breaker.is_triggered():
        ...     logger.critical("Circuit breaker triggered!")
    """

    # IP Hard Ban signature (39 bytes response)
    HARD_BAN_SIGNATURE = "IP Hard Ban (39 bytes)"
    HARD_BAN_LENGTH = 39

    def __init__(self, threshold: int = 3) -> None:
        """Initialize circuit breaker.

        Args:
            threshold: Maximum consecutive IP bans before triggering (default: 3)
        """
        self.threshold = threshold
        self.consecutive_failures = 0
        self.failure_history: list[dict] = []

    def is_hard_ban(self, content: str | bytes) -> bool:
        """Check if response indicates IP Hard Ban.

        Args:
            content: Response content (string or bytes)

        Returns:
            True if this is a 39-byte IP Hard Ban response
        """
        # Convert to string if needed
        if isinstance(content, bytes):
            content_str = content.decode("utf-8", errors="ignore")
        else:
            content_str = str(content)

        # Check length
        content_len = len(content_str)
        if content_len == self.HARD_BAN_LENGTH:
            logger.critical(f"[V144.8] 🚨 检测到 IP 硬封禁签名: {content_len} 字节")
            return True

        return False

    def record_failure(self, reason: str, proxy: str | None = None) -> None:
        """Record a failure and check if threshold is exceeded.

        Args:
            reason: Failure reason (e.g., "IP Hard Ban (39 bytes)")
            proxy: Proxy URL that failed (optional)

        Raises:
            SystemExit: If threshold exceeded (exit code 99)
        """
        # Check if this is a hard ban
        is_hard_ban = (
            self.HARD_BAN_SIGNATURE in reason
            or int(reason.split()[-1].replace(")", "")) == self.HARD_BAN_LENGTH
            if "bytes" in reason
            else False
        )

        if is_hard_ban:
            self.consecutive_failures += 1

            # Record failure
            failure_record = {
                "timestamp": datetime.now().isoformat(),
                "reason": reason,
                "proxy": proxy,
                "consecutive_count": self.consecutive_failures,
            }
            self.failure_history.append(failure_record)

            # Log to file
            self._log_failure(failure_record)

            # Critical log
            logger.critical(
                f"[V144.8] ⛔ IP 硬封禁计数: {self.consecutive_failures}/{self.threshold}"
            )

            # Check threshold
            if self.consecutive_failures >= self.threshold:
                self._trigger_shutdown()
        else:
            # Reset counter if not a hard ban
            self.consecutive_failures = 0
            logger.debug("[V144.8] 非 IP 硬封禁错误，重置计数器")

    def _log_failure(self, failure_record: dict) -> None:
        """Log failure to circuit breaker log file.

        Args:
            failure_record: Failure record dictionary
        """
        try:
            with open(CIRCUIT_BREAKER_LOG, "a") as f:
                f.write(f"{failure_record['timestamp']} | ")
                f.write(f"Proxy: {failure_record['proxy'] or 'Unknown'} | ")
                f.write(f"Reason: {failure_record['reason']} | ")
                f.write(f"Count: {failure_record['consecutive_count']}/{self.threshold}\n")
        except Exception as e:
            logger.exception(f"[V144.8] ❌ 写入熔断日志失败: {e}")

    def _trigger_shutdown(self) -> None:
        """Trigger immediate system shutdown.

        Logs critical error message and exits with code 99.
        This is intentional - prevents further damage to proxy pool.
        """
        # Critical log
        logger.critical("")
        logger.critical("=" * 80)
        logger.critical("[V144.8] 🛑 熔断器触发！立即关机保护代理池")
        logger.critical("=" * 80)
        logger.critical(f"原因: 连续 {self.consecutive_failures} 次检测到 IP 硬封禁")
        logger.critical(f"阈值: {self.threshold} 次")
        logger.critical("操作: 系统将执行 sys.exit(99) 强制关机")
        logger.critical("")
        logger.critical("失败历史:")
        for i, record in enumerate(reversed(self.failure_history[-5:]), 1):
            logger.critical(
                f"  {i}. {record['timestamp']} | {record['proxy']} | {record['reason']}"
            )
        logger.critical("=" * 80)
        logger.critical("")

        # Write final log entry
        try:
            with open(CIRCUIT_BREAKER_LOG, "a") as f:
                f.write("\n")
                f.write("=" * 80 + "\n")
                f.write("[V144.8] CIRCUIT BREAKER TRIGGERED - SHUTDOWN\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Consecutive Failures: {self.consecutive_failures}/{self.threshold}\n")
                f.write("Action: sys.exit(99)\n")
                f.write("=" * 80 + "\n\n")
        except Exception:
            pass

        # Force shutdown
        sys.exit(99)

    def is_triggered(self) -> bool:
        """Check if circuit breaker has been triggered.

        Returns:
            True if threshold exceeded (would have already exited)
        """
        return self.consecutive_failures >= self.threshold

    def reset(self) -> None:
        """Reset the circuit breaker (for testing/recovery).

        Warning: Only use this after cooldown period (6-24 hours).
        """
        old_count = self.consecutive_failures
        self.consecutive_failures = 0
        self.failure_history.clear()

        logger.info(f"[V144.8] 🔄 熔断器已重置 (之前计数: {old_count})")

    def get_status(self) -> dict[str, Any]:
        """Get current circuit breaker status.

        Returns:
            Dictionary with status information
        """
        return {
            "threshold": self.threshold,
            "consecutive_failures": self.consecutive_failures,
            "is_critical": self.consecutive_failures >= self.threshold,
            "recent_failures": len(self.failure_history),
        }


# ============================================================================
# Global Circuit Breaker Instance
# ============================================================================

# Global circuit breaker instance (module-level singleton)
_global_circuit_breaker: CircuitBreaker | None = None


def get_circuit_breaker(threshold: int = 3) -> CircuitBreaker:
    """Get the global circuit breaker instance.

    Args:
        threshold: Maximum consecutive failures (only used on first call)

    Returns:
        CircuitBreaker instance

    Example:
        >>> breaker = get_circuit_breaker()
        >>> breaker.record_failure("IP Hard Ban (39 bytes)", "proxy1:7890")
    """
    global _global_circuit_breaker

    if _global_circuit_breaker is None:
        _global_circuit_breaker = CircuitBreaker(threshold=threshold)
        logger.info(f"[V144.8] 🛡️ 熔断器已初始化 (阈值: {threshold})")

    return _global_circuit_breaker


def check_hard_ban_and_trip(
    content: str | bytes,
    proxy: str | None = None,
) -> Literal["continue", "trip"]:
    """V144.8: Check for IP Hard Ban and trigger circuit breaker if detected.

    This is a convenience function that combines detection and recording.

    Args:
        content: Response content to check
        proxy: Proxy URL that was used (optional)

    Returns:
        "continue" if content is OK (not a hard ban)
        "trip" if hard ban detected (circuit breaker will trigger)

    Note:
        If threshold is exceeded, this function will call sys.exit(99)
        and never return.

    Example:
        >>> result = check_hard_ban_and_trip(page_content, "proxy1:7890")
        >>> if result == "trip":
        ...     # Code won't reach here if threshold exceeded
        ...     logger.error("Hard ban detected!")
    """
    breaker = get_circuit_breaker()

    if breaker.is_hard_ban(content):
        breaker.record_failure(breaker.HARD_BAN_SIGNATURE, proxy)
        return "trip"

    # Reset counter if content is OK
    breaker.consecutive_failures = 0
    return "continue"
