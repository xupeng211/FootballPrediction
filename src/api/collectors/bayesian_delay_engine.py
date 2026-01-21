#!/usr/bin/env python3
"""V150.0 Bayesian Adaptive Delay Engine.

This module implements a delay strategy that adapts based on historical success rates.
Unlike fixed delay intervals, this engine uses Bayesian inference to dynamically
adjust the delay between requests, reducing detection risk.

Key Features:
    - Bayesian updating: Delay increases on failures, decreases on successes
    - Exponential backoff: Failures trigger 2-5 minute "long thinking" delays
    - Convergence: Gradually returns to baseline after stable success
    - Fallback: Never goes below minimum safe delay

Author: 高级爬虫逆向专家
Version: V150.0
Date: 2026-01-07
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import logging
import random
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DelayHistory:
    """Single delay event record."""

    timestamp: datetime
    delay_seconds: float
    success: bool
    error_type: str | None = None


@dataclass
class BayesianState:
    """Bayesian inference state for delay calculation."""

    # Prior beliefs (Beta distribution parameters)
    alpha: float = 2.0  # Success count prior
    beta: float = 1.0  # Failure count prior

    # Current estimates
    success_probability: float = 0.6667  # Initial estimate
    confidence: float = 0.5  # How confident we are in the estimate

    # History for debugging
    history: list[DelayHistory] = field(default_factory=list)

    def update(self, success: bool) -> None:
        """Update Bayesian belief after observing an outcome."""
        # Update Beta distribution parameters
        if success:
            self.alpha += 1
        else:
            self.beta += 1

        # Calculate posterior mean
        self.success_probability = self.alpha / (self.alpha + self.beta)

        # Confidence increases with more data
        total_observations = self.alpha + self.beta - 3  # Subtract priors
        self.confidence = min(total_observations / 20, 1.0)


class BayesianDelayEngine:
    """V150.0: Bayesian adaptive delay engine.

    This engine calculates optimal delays between requests based on:
    1. Historical success rate (Bayesian inference)
    2. Recent failure pattern (exponential backoff)
    3. Random jitter (to avoid predictable patterns)

    The delay follows these principles:
    - High success rate → gradual decrease to baseline (30s)
    - Failure → exponential increase (2-5 minutes)
    - Stable success → maintain current level
    - Never below 15s minimum safe delay

    Example:
        >>> engine = BayesianDelayEngine()
        >>> delay = engine.calculate_delay(last_success=True)
        >>> await asyncio.sleep(delay)
        >>> engine.record_result(delay, success=True)
    """

    def __init__(
        self,
        base_delay: float = 30.0,
        min_delay: float = 15.0,
        max_delay: float = 300.0,
        backoff_multiplier: float = 2.0,
        recovery_rate: float = 0.8,
    ):
        """Initialize the Bayesian delay engine.

        Args:
            base_delay: Target baseline delay in seconds (default: 30s)
            min_delay: Minimum safe delay (default: 15s)
            max_delay: Maximum delay cap (default: 300s = 5 minutes)
            backoff_multiplier: Exponential backoff factor (default: 2.0)
            recovery_rate: Speed of returning to baseline (default: 0.8)
        """
        self.base_delay = base_delay
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.recovery_rate = recovery_rate

        # Bayesian inference state
        self.state = BayesianState()

        # Current delay level
        self.current_delay = base_delay

        # Consecutive failure counter for exponential backoff
        self.consecutive_failures = 0

        # Long thinking mode (triggered by failures)
        self.in_long_thinking = False

        logger.info(
            f"🧠 V150.0 BayesianDelayEngine initialized: "
            f"base={base_delay}s, min={min_delay}s, max={max_delay}s"
        )

    def calculate_delay(
        self,
        last_success: bool | None = None,
        force_long_thinking: bool = False,
    ) -> float:
        """Calculate the next delay based on historical performance.

        Args:
            last_success: Whether the last request succeeded (None if unknown)
            force_long_thinking: Force 2-5 minute long thinking delay

        Returns:
            Delay duration in seconds

        Example:
            >>> delay = engine.calculate_delay(last_success=True)
            >>> print(f"Next delay: {delay:.1f}s")
        """
        # If forced long thinking, generate 2-5 minute delay
        if force_long_thinking or self.in_long_thinking:
            delay = random.uniform(120, 300)
            logger.info(f"🧠 Long thinking mode: {delay:.1f}s")
            self.in_long_thinking = False  # Reset flag
            return delay

        # Update Bayesian state if we have a result
        if last_success is not None:
            self.state.update(last_success)

            # Handle failure case
            if not last_success:
                self.consecutive_failures += 1

                # Trigger exponential backoff
                backoff_delay = self.base_delay * (
                    self.backoff_multiplier**self.consecutive_failures
                )
                self.current_delay = min(backoff_delay, self.max_delay)

                # If backoff is severe, enter long thinking mode next time
                if self.current_delay >= 120:
                    self.in_long_thinking = True

                logger.warning(
                    f"⚠️  Failure detected: consecutive={self.consecutive_failures}, "
                    f"delay={self.current_delay:.1f}s"
                )
            else:
                # Success case: gradual recovery
                self.consecutive_failures = 0

                # Bayesian weighted delay
                # High success probability → move toward base_delay
                target_delay = (
                    self.base_delay * self.state.success_probability
                    + self.current_delay * (1 - self.state.success_probability)
                )

                # Apply recovery rate
                self.current_delay = target_delay * self.recovery_rate + self.current_delay * (
                    1 - self.recovery_rate
                )

                logger.debug(
                    f"✓ Success: p(success)={self.state.success_probability:.3f}, "
                    f"delay={self.current_delay:.1f}s"
                )

        # Ensure delay is within bounds
        self.current_delay = max(self.min_delay, min(self.current_delay, self.max_delay))

        # Add random jitter (±20%) to avoid patterns
        jitter = random.uniform(0.8, 1.2)
        final_delay = self.current_delay * jitter

        # Final bounds check
        return max(self.min_delay, min(final_delay, self.max_delay))


    def record_result(
        self,
        delay: float,
        success: bool,
        error_type: str | None = None,
    ) -> None:
        """Record the result of a request with its delay.

        This maintains history for debugging and analysis.

        Args:
            delay: The delay that was used
            success: Whether the request succeeded
            error_type: Type of error if failed (e.g., "403", "429", "timeout")

        Example:
            >>> engine.record_result(delay=30.0, success=True)
            >>> engine.record_result(delay=180.0, success=False, error_type="429")
        """
        record = DelayHistory(
            timestamp=datetime.now(),
            delay_seconds=delay,
            success=success,
            error_type=error_type,
        )
        self.state.history.append(record)

        # Keep only last 100 records to avoid memory bloat
        if len(self.state.history) > 100:
            self.state.history = self.state.history[-100:]

        logger.debug(
            f"📊 Result recorded: delay={delay:.1f}s, success={success}, error={error_type}"
        )

    def get_statistics(self) -> dict[str, Any]:
        """Get current engine statistics.

        Returns:
            Dictionary with statistics including success rate, delay info, etc.

        Example:
            >>> stats = engine.get_statistics()
            >>> print(f"Success rate: {stats['success_rate']:.1%}")
        """
        history = self.state.history
        if not history:
            return {
                "total_requests": 0,
                "success_rate": 0.0,
                "current_delay": self.current_delay,
                "consecutive_failures": self.consecutive_failures,
            }

        total = len(history)
        successes = sum(1 for h in history if h.success)

        return {
            "total_requests": total,
            "successes": successes,
            "failures": total - successes,
            "success_rate": successes / total if total > 0 else 0.0,
            "current_delay": self.current_delay,
            "base_delay": self.base_delay,
            "consecutive_failures": self.consecutive_failures,
            "in_long_thinking": self.in_long_thinking,
            "bayesian_success_prob": self.state.success_probability,
            "bayesian_confidence": self.state.confidence,
        }

    def reset(self) -> None:
        """Reset the engine to initial state.

        This is useful when switching to a completely different data source
        or proxy pool.

        Example:
            >>> engine.reset()
        """
        self.state = BayesianState()
        self.current_delay = self.base_delay
        self.consecutive_failures = 0
        self.in_long_thinking = False
        logger.info("🔄 BayesianDelayEngine reset to initial state")


# ============================================================================
# Convenience Functions
# ============================================================================


async def wait_with_bayesian_delay(
    engine: BayesianDelayEngine,
    last_success: bool | None = None,
) -> float:
    """Wait using Bayesian delay engine.

    Args:
        engine: BayesianDelayEngine instance
        last_success: Whether the last request succeeded

    Returns:
        The delay that was used

    Example:
        >>> delay = await wait_with_bayesian_delay(engine, last_success=True)
    """
    delay = engine.calculate_delay(last_success=last_success)
    logger.info(f"⏳ Bayesian delay: {delay:.1f}s")
    await asyncio.sleep(delay)
    return delay


# Create singleton instance for convenient access
_default_engine: BayesianDelayEngine | None = None


def get_default_engine() -> BayesianDelayEngine:
    """Get the default singleton BayesianDelayEngine instance."""
    global _default_engine
    if _default_engine is None:
        _default_engine = BayesianDelayEngine()
    return _default_engine


# ============================================================================
# CLI for Testing
# ============================================================================

if __name__ == "__main__":
    import asyncio

    async def demo():
        """Demonstrate the Bayesian delay engine."""
        engine = BayesianDelayEngine()


        # Simulate a sequence of requests
        results = [
            True,  # Success
            True,  # Success
            False,  # Failure (trigger backoff)
            True,  # Success (recovery starts)
            True,  # Success
            True,  # Success
            True,  # Success
        ]

        for _i, success in enumerate(results, 1):
            delay = engine.calculate_delay(last_success=success)
            engine.record_result(delay, success)


            await asyncio.sleep(0.1)  # Small sleep for demo

        stats = engine.get_statistics()
        for value in stats.values():
            if isinstance(value, float):
                pass
            else:
                pass

    asyncio.run(demo())
