# Caching Implementation Design

## Overview

This document describes the caching implementation for the Football Prediction System, focusing on adding TTL (Time-To-Live) support to the prediction service.

## Current State

The prediction service currently has a basic model caching mechanism:
- Models are cached in `self.model_cache` dictionary
- Model metadata is cached in `self.model_metadata_cache` dictionary
- No TTL mechanism - cached items never expire
- No cache size limits

## Proposed Implementation

### 1. Cache Entry with TTL

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

@dataclass
class CacheEntry:
    """Cache entry with TTL support"""
    value: Any
    created_at: datetime
    ttl: Optional[timedelta] = None

    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        if self.ttl is None:
            return False
        return datetime.now() > (self.created_at + self.ttl)

    def get_remaining_ttl(self) -> Optional[timedelta]:
        """Get remaining TTL for cache entry"""
        if self.ttl is None:
            return None
        expiration_time = self.created_at + self.ttl
        remaining = expiration_time - datetime.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)
```

### 2. TTL Cache Manager

```python
import asyncio
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TTLCache:
    """TTL-based cache manager"""

    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    logger.debug(f"Cache hit for key: {key}")
                    return entry.value
                else:
                    logger.debug(f"Cache expired for key: {key}")
                    del self._cache[key]
            logger.debug(f"Cache miss for key: {key}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> None:
        """Set value in cache with TTL"""
        async with self._lock:
            # Check if we need to evict items
            if len(self._cache) >= self._max_size:
                await self._evict_expired()
                if len(self._cache) >= self._max_size:
                    await self._evict_lru()

            self._cache[key] = CacheEntry(
                value=value,
                created_at=datetime.now(),
                ttl=ttl
            )
            logger.debug(f"Cache set for key: {key} with TTL: {ttl}")

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache deleted for key: {key}")
                return True
            return False

    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
            logger.debug("Cache cleared")

    async def _evict_expired(self) -> None:
        """Evict expired entries"""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del self._cache[key]
        logger.debug(f"Evicted {len(expired_keys)} expired entries")

    async def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if self._cache:
            # Find oldest entry
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].created_at
            )
            del self._cache[oldest_key]
            logger.debug(f"Evicted LRU entry: {oldest_key}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        async with self._lock:
            total_entries = len(self._cache)
            expired_entries = sum(1 for entry in self._cache.values() if entry.is_expired())
            active_entries = total_entries - expired_entries

            return {
                "total_entries": total_entries,
                "active_entries": active_entries,
                "expired_entries": expired_entries,
                "max_size": self._max_size
            }
```

### 3. Integration with Prediction Service

```python
class PredictionService:
    """Enhanced prediction service with TTL caching"""

    def __init__(self, mlflow_tracking_uri: str = "http://localhost:5002"):
        # ... existing initialization ...

        # Initialize TTL cache
        self.model_cache = TTLCache(max_size=10)  # Max 10 models
        self.prediction_cache = TTLCache(max_size=1000)  # Max 1000 predictions

        # Cache TTL configuration
        self.model_cache_ttl = timedelta(hours=1)  # Models cached for 1 hour
        self.prediction_cache_ttl = timedelta(minutes=30)  # Predictions cached for 30 minutes

    async def get_production_model(
        self, model_name: str = "football_baseline_model"
    ) -> Tuple[Any, str]:
        """Get production model with TTL caching"""
        # Create cache key
        cache_key = f"model:{model_name}"

        # Try to get from cache
        cached_result = await self.model_cache.get(cache_key)
        if cached_result:
            model, version = cached_result
            logger.debug(f"Using cached model {model_name} version {version}")
            return model, version

        # Load model from MLflow (existing logic)
        # ... existing model loading code ...

        # Cache the result
        await self.model_cache.set(
            cache_key,
            (model, version),
            ttl=self.model_cache_ttl
        )

        return model, version

    async def predict_match(self, match_id: int) -> PredictionResult:
        """Predict match result with TTL caching"""
        # Create cache key
        cache_key = f"prediction:{match_id}"

        # Try to get from cache
        cached_result = await self.prediction_cache.get(cache_key)
        if cached_result:
            logger.debug(f"Using cached prediction for match {match_id}")
            return cached_result

        # Generate prediction (existing logic)
        # ... existing prediction code ...

        # Cache the result
        await self.prediction_cache.set(
            cache_key,
            result,
            ttl=self.prediction_cache_ttl
        )

        return result
```

## Benefits

1. **Automatic Expiration**: Cache entries automatically expire after TTL
2. **Memory Management**: Cache size limits prevent memory exhaustion
3. **Improved Performance**: Cached predictions reduce computation time
4. **Freshness Control**: Configurable TTL ensures data freshness
5. **Thread Safety**: Async lock ensures thread-safe cache operations

## Configuration

Environment variables for cache configuration:
- `MODEL_CACHE_TTL_HOURS`: Model cache TTL in hours (default: 1)
- `PREDICTION_CACHE_TTL_MINUTES`: Prediction cache TTL in minutes (default: 30)
- `MODEL_CACHE_MAX_SIZE`: Maximum number of models in cache (default: 10)
- `PREDICTION_CACHE_MAX_SIZE`: Maximum number of predictions in cache (default: 1000)
