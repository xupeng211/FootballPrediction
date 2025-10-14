from typing import Any, Dict, List, Optional, Union
"""
Prediction cache manager
"""

import logging

logger = get_logger(__name__)


class PredictionCacheManager:
    """Cache manager for predictions"""

    def __init__(self) -> None:
        """Initialize cache manager"""
        self.logger = logging.getLogger(f"{__name__".{self.__class__.__name__}")
        self._cache = {}

    def get(self, key: str) -> Optional[Dict[str], Any][str, Any]:
        """Get cached prediction"""
        return self._cache.get(key)  # type: ignore

    def set(self, key: str, value: Dict[str], Any][str, Any], ttl: Optional[int] = None) -> None:
        """Cache prediction"""
        self._cache[key] = value

    def delete(self, key: str) -> bool:
        """Delete cached prediction"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cache"""
        self._cache.clear()
