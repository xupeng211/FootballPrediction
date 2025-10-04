# Retry Mechanism Design

## Overview

This document describes the retry mechanism implementation for external services in the Football Prediction System, including database connections, MLflow service calls, and other external dependencies.

## Current State

The system currently has limited or no retry mechanisms for external service calls:

- Database connections may fail without retry
- MLflow service calls may fail without retry
- External API calls may fail without retry
- No exponential backoff
- No circuit breaker pattern

## Proposed Implementation

### 1. Retry Decorator

```python
import asyncio
import functools
import logging
import random
import time
from typing import Any, Callable, Optional, Type, TypeVar

T = TypeVar('T')

logger = logging.getLogger(__name__)

class RetryConfig:
    """Configuration for retry mechanism"""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions

def retry(
    config: RetryConfig,
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    Retry decorator with exponential backoff and jitter

    Args:
        config: Retry configuration
        on_retry: Optional callback function called on each retry
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e

                    # If this is the last attempt, re-raise
                    if attempt == config.max_attempts - 1:
                        logger.error(f"Max retry attempts reached for {func.__name__}: {e}")
                        raise

                    # Calculate delay
                    delay = config.base_delay * (config.exponential_base ** attempt)
                    if delay > config.max_delay:
                        delay = config.max_delay

                    # Add jitter
                    if config.jitter:
                        delay *= (0.5 + random.random() * 0.5)

                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )

                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt + 1, e)

                    # Wait before retry
                    await asyncio.sleep(delay)

            # This should never be reached due to the re-raise above
            raise last_exception

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e

                    # If this is the last attempt, re-raise
                    if attempt == config.max_attempts - 1:
                        logger.error(f"Max retry attempts reached for {func.__name__}: {e}")
                        raise

                    # Calculate delay
                    delay = config.base_delay * (config.exponential_base ** attempt)
                    if delay > config.max_delay:
                        delay = config.max_delay

                    # Add jitter
                    if config.jitter:
                        delay *= (0.5 + random.random() * 0.5)

                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )

                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt + 1, e)

                    # Wait before retry
                    time.sleep(delay)

            # This should never be reached due to the re-raise above
            raise last_exception

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
```

### 2. Circuit Breaker Pattern

```python
import asyncio
import time
from enum import Enum
from typing import Any, Callable, Optional

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker implementation"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        retry_timeout: float = 30.0
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.retry_timeout = retry_timeout

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with circuit breaker protection"""
        async with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise Exception("Circuit breaker is OPEN")

            try:
                result = await func(*args, **kwargs)
                await self._on_success()
                return result
            except Exception as e:
                await self._on_failure()
                raise

    async def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    async def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset"""
        if self.last_failure_time is None:
            return False

        time_since_failure = time.time() - self.last_failure_time
        timeout = self.retry_timeout if self.state == CircuitState.HALF_OPEN else self.recovery_timeout
        return time_since_failure >= timeout
```

### 3. Integration with Database Connection

```python
# src/database/connection.py
import asyncio
from typing import Optional

from .retry import retry, RetryConfig

# Database-specific retry configuration
DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    retryable_exceptions=(ConnectionError, TimeoutError, asyncio.TimeoutError)
)

class DatabaseManager:
    # ... existing code ...

    @retry(DATABASE_RETRY_CONFIG)
    async def get_match(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Get match with retry mechanism"""
        from src.database.models.match import Match

        async with self.get_async_session() as session:
            result = await session.execute(select(Match).where(Match.id == match_id))
            match = result.scalar_one_or_none()
            if match:
                return {c.name: getattr(match, c.name) for c in match.__table__.columns}
            return None

    @retry(DATABASE_RETRY_CONFIG)
    async def health_check_with_retry(self) -> bool:
        """Check database health with retry mechanism"""
        try:
            session = self.create_async_session()
            await session.execute(text("SELECT 1"))
            await session.close()
            return True
        except Exception:
            return False
```

### 4. Integration with MLflow Service

```python
# src/models/prediction_service.py
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException

from .retry import retry, RetryConfig

# MLflow-specific retry configuration
MLFLOW_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    retryable_exceptions=(MlflowException, ConnectionError, TimeoutError)
)

class PredictionService:
    # ... existing code ...

    @retry(MLFLOW_RETRY_CONFIG)
    async def get_production_model_with_retry(
        self, model_name: str = "football_baseline_model"
    ) -> Tuple[Any, str]:
        """Get production model with retry mechanism"""
        client = MlflowClient(tracking_uri=self.mlflow_tracking_uri)

        # Rest of the existing model loading logic
        # ... existing code ...
```

## Benefits

1. **Improved Reliability**: Automatic retry of failed operations
2. **Exponential Backoff**: Prevents overwhelming failing services
3. **Jitter**: Reduces thundering herd problem
4. **Circuit Breaker**: Prevents cascading failures
5. **Configurable**: Flexible retry policies for different services
6. **Monitoring**: Built-in logging and metrics

## Configuration

Environment variables for retry configuration:

- `DATABASE_RETRY_MAX_ATTEMPTS`: Database retry max attempts (default: 5)
- `DATABASE_RETRY_BASE_DELAY`: Database retry base delay in seconds (default: 1.0)
- `DATABASE_RETRY_MAX_DELAY`: Database retry max delay in seconds (default: 30.0)
- `MLFLOW_RETRY_MAX_ATTEMPTS`: MLflow retry max attempts (default: 3)
- `MLFLOW_RETRY_BASE_DELAY`: MLflow retry base delay in seconds (default: 2.0)
- `MLFLOW_RETRY_MAX_DELAY`: MLflow retry max delay in seconds (default: 30.0)
