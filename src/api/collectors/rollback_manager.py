#!/usr/bin/env python3
"""V150.0 Rollback Manager - Emergency Stop Protocol.

This module provides emergency rollback functionality for collection operations.
When IP bans are detected (403/429), it immediately stops all operations
and sets a cooling period.

Author: 高级自动化测试工程师 (SDET)
Version: V150.0
Date: 2026-01-07
"""

from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RollbackManager:
    """V150.0: Emergency rollback manager for collection operations.

    This manager monitors collection operations and triggers emergency rollback
    when IP bans are detected.

    Example:
        >>> manager = RollbackManager(max_failures=1)  # Stop on first 403
        >>> if manager.should_rollback(error_type="403"):
        ...     manager.execute_rollback()
        ...     raise EmergencyStopException("IP ban detected")
    """

    def __init__(self, max_failures: int = 1, cooling_hours: int = 12):
        """Initialize the rollback manager.

        Args:
            max_failures: Maximum number of ban errors before rollback (default: 1)
            cooling_hours: Cooling period duration in hours (default: 12)
        """
        self.max_failures = max_failures
        self.cooling_hours = cooling_hours
        self.ban_errors = {"403", "429", "503", "ConnectionRefusedError"}
        self.failure_count = 0
        self.is_stopped = False
        self.stop_reason: str | None = None
        self.stop_time: datetime | None = None

    def should_rollback(self, error_type: str | None = None) -> bool:
        """Check if rollback should be triggered.

        Args:
            error_type: Type of error (e.g., "403", "429", "timeout")

        Returns:
            True if rollback should be triggered
        """
        # Check if already stopped
        if self.is_stopped:
            return True

        # Check if error type indicates ban
        if error_type and error_type in self.ban_errors:
            self.failure_count += 1
            logger.critical(
                f"🚨 BAN ERROR DETECTED: {error_type} "
                f"(failure {self.failure_count}/{self.max_failures})"
            )

            if self.failure_count >= self.max_failures:
                return True

        return False

    def execute_rollback(self, reason: str = "IP ban detected") -> None:
        """Execute emergency rollback.

        This:
        1. Sets a cooling period in environment variable
        2. Logs the rollback event
        3. Marks the manager as stopped

        Args:
            reason: Reason for rollback
        """
        # Calculate cooling end time
        cooling_end = datetime.now() + timedelta(hours=self.cooling_hours)

        # Set environment variable
        os.environ["COLLECTION_PAUSE_UNTIL"] = cooling_end.isoformat()

        # Mark as stopped
        self.is_stopped = True
        self.stop_reason = reason
        self.stop_time = datetime.now()

        # Log critical event
        logger.critical("=" * 70)
        logger.critical("🛑 EMERGENCY ROLLBACK TRIGGERED")
        logger.critical("=" * 70)
        logger.critical(f"Reason: {reason}")
        logger.critical(f"Cooling period: {self.cooling_hours} hours")
        logger.critical(f"Cooling ends: {cooling_end.isoformat()}")
        logger.critical("=" * 70)

        # Save rollback event to file
        self._save_rollback_event(reason, cooling_end)

    def _save_rollback_event(self, reason: str, cooling_end: datetime) -> None:
        """Save rollback event to log file."""
        try:
            rollback_log = Path("logs/rollback_events.log")
            rollback_log.parent.mkdir(parents=True, exist_ok=True)

            with open(rollback_log, "a") as f:
                f.write(f"\n{'=' * 70}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Reason: {reason}\n")
                f.write(f"Cooling ends: {cooling_end.isoformat()}\n")
                f.write(f"{'=' * 70}\n")
        except Exception as e:
            logger.exception(f"Failed to save rollback event: {e}")

    def is_emergency_stopped(self) -> bool:
        """Check if emergency stop has been triggered.

        Returns:
            True if operations should stop
        """
        return self.is_stopped

    def get_status(self) -> dict[str, Any]:
        """Get current rollback manager status.

        Returns:
            Dictionary with status information
        """
        return {
            "is_stopped": self.is_stopped,
            "stop_reason": self.stop_reason,
            "stop_time": self.stop_time.isoformat() if self.stop_time else None,
            "failure_count": self.failure_count,
            "max_failures": self.max_failures,
            "cooling_hours": self.cooling_hours,
        }


class EmergencyStopException(Exception):
    """Exception raised when emergency stop is triggered."""

