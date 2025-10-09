
"""
缓存模块

提供Redis缓存功能，支持：
- Redis连接池管理
- 同步和异步操作
- 缓存Key命名规范
- TTL过期策略
"""


from typing import cast, Any, Optional, Union

from .redis_manager import CacheKeyManager, RedisManager

__all__ = ["RedisManager", "CacheKeyManager"]
