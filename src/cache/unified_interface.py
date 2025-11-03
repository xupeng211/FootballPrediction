"""
统一缓存接口
Unified Cache Interface

提供统一的缓存管理接口，整合TTL缓存、Redis缓存、缓存装饰器和一致性管理器。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass

from .ttl_cache_enhanced.ttl_cache import TTLCache
from .redis_enhanced import EnhancedRedisManager, RedisConfig
from .consistency_manager import get_consistency_manager
from .decorators import cached, cache_invalidate

logger = logging.getLogger(__name__)


class CacheBackend(Enum):
    """缓存后端类型"""

    MEMORY = "memory"
    REDIS = "redis"
    MULTI_LEVEL = "multi_level"


@dataclass
class UnifiedCacheConfig:
    """统一缓存配置"""

    backend: CacheBackend = CacheBackend.MEMORY
    memory_config: Optional[Dict[str, Any]] = None
    redis_config: Optional[RedisConfig] = None
    use_consistency_manager: bool = True
    enable_decorators: bool = True
    default_ttl: int = 3600


class CacheInterface(ABC):
    """缓存接口抽象基类"""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空缓存"""
        pass

    @abstractmethod
    def size(self) -> int:
        """获取缓存大小"""
        pass


class MemoryCacheAdapter(CacheInterface):
    """内存缓存适配器"""

    def __init__(self, config: Dict[str, Any] = None):
        default_config = {
            "max_size": 1000,
            "default_ttl": 3600,
            "cleanup_interval": 60.0,
        }
        final_config = {**default_config, **(config or {})}
        self._cache = TTLCache(**final_config)

    def get(self, key: str, default: Any = None) -> Any:
        return self._cache.get(key, default)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            self._cache.set(key, value, ttl)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        return self._cache.delete(key)

    def exists(self, key: str) -> bool:
        return self._cache.get(key) is not None

    def clear(self) -> None:
        self._cache.clear()

    def size(self) -> int:
        return self._cache.size()

    def get_stats(self) -> Dict[str, Any]:
        return self._cache.get_stats()


class RedisCacheAdapter(CacheInterface):
    """Redis缓存适配器"""

    def __init__(self, config: RedisConfig = None, use_mock: bool = None):
        self._manager = EnhancedRedisManager(config, use_mock)

    def _serialize_value(self, value: Any) -> str:
        """序列化值"""
        if isinstance(value, str):
            return value
        elif isinstance(value, (int, float, bool)):
            return str(value)
        elif isinstance(value, (dict, list)):
            import json

            return json.dumps(value, ensure_ascii=False)
        else:
            import pickle
            import base64

            return base64.b64encode(pickle.dumps(value)).decode()

    def _deserialize_value(self, value: str) -> Any:
        """反序列化值"""
        # 尝试解析为数字
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # 尝试解析为JSON
        try:
            import json

            return json.loads(value)
        except json.JSONDecodeError:
            pass

        # 尝试解析为pickle
        try:
            import pickle
            import base64

            return pickle.loads(base64.b64decode(value.encode()))
        except Exception:
            pass

        # 返回原始字符串
        return value

    def get(self, key: str, default: Any = None) -> Any:
        value = self._manager.get(key)
        if value is None:
            return default
        return self._deserialize_value(value)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            serialized = self._serialize_value(value)
            if ttl:
                return self._manager.set(key, serialized, ex=ttl)
            else:
                return self._manager.set(key, serialized)
        except Exception as e:
            logger.error(f"Redis设置失败: {e}")
            return False

    def delete(self, key: str) -> bool:
        return bool(self._manager.delete(key))

    def exists(self, key: str) -> bool:
        return self._manager.exists(key)

    def clear(self) -> None:
        self._manager.flushdb()

    def size(self) -> int:
        return len(self._manager.keys())

    def get_stats(self) -> Dict[str, Any]:
        return {"redis_info": self._manager.info(), "ping": self._manager.ping()}


class MultiLevelCacheAdapter(CacheInterface):
    """多级缓存适配器"""

    def __init__(
        self, memory_config: Dict[str, Any] = None, redis_config: RedisConfig = None
    ):
        self._l1_cache = MemoryCacheAdapter(memory_config)
        self._l2_cache = RedisCacheAdapter(redis_config, use_mock=True)

    def get(self, key: str, default: Any = None) -> Any:
        # 先查L1缓存
        value = self._l1_cache.get(key)
        if value is not None:
            return value

        # 查L2缓存
        value = self._l2_cache.get(key)
        if value is not None:
            # 回填到L1缓存
            self._l1_cache.set(key, value)
            return value

        return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        l1_success = self._l1_cache.set(key, value, ttl)
        l2_success = self._l2_cache.set(key, value, ttl)
        return l1_success and l2_success

    def delete(self, key: str) -> bool:
        l1_success = self._l1_cache.delete(key)
        l2_success = self._l2_cache.delete(key)
        return l1_success or l2_success

    def exists(self, key: str) -> bool:
        return self._l1_cache.exists(key) or self._l2_cache.exists(key)

    def clear(self) -> None:
        self._l1_cache.clear()
        self._l2_cache.clear()

    def size(self) -> int:
        # 返回L1缓存大小（实际缓存的数据量）
        return self._l1_cache.size()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "l1_stats": self._l1_cache.get_stats(),
            "l2_stats": self._l2_cache.get_stats(),
        }


class UnifiedCacheManager:
    """统一缓存管理器"""

    def __init__(self, config: UnifiedCacheConfig = None):
        self.config = config or UnifiedCacheConfig()
        self._adapter = self._create_adapter()
        self._consistency_manager = None

        if self.config.use_consistency_manager:
            self._consistency_manager = get_consistency_manager()

        logger.info(f"统一缓存管理器初始化完成，后端: {self.config.backend.value}")

    def _create_adapter(self) -> CacheInterface:
        """创建缓存适配器"""
        if self.config.backend == CacheBackend.MEMORY:
            return MemoryCacheAdapter(self.config.memory_config)
        elif self.config.backend == CacheBackend.REDIS:
            return RedisCacheAdapter(self.config.redis_config)
        elif self.config.backend == CacheBackend.MULTI_LEVEL:
            return MultiLevelCacheAdapter(
                self.config.memory_config, self.config.redis_config
            )
        else:
            raise ValueError(f"不支持的缓存后端: {self.config.backend}")

    # 基础操作
    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        return self._adapter.get(key, default)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        success = self._adapter.set(key, value, ttl)

        if success and self._consistency_manager:
            # 通知一致性管理器（使用线程安全的方式）
            try:
                loop = asyncio.get_running_loop()
                # 如果有运行的事件循环，创建任务
                loop.create_task(
                    self._consistency_manager.set_cache_entry(
                        key, value, ttl or self.config.default_ttl
                    )
                )
            except RuntimeError:
                # 没有运行的事件循环，创建新的事件循环
                try:
                    asyncio.run(
                        self._consistency_manager.set_cache_entry(
                            key, value, ttl or self.config.default_ttl
                        )
                    )
                except Exception as e:
                    logger.warning(f"一致性管理器通知失败: {e}")

        return success

    def delete(self, key: str) -> bool:
        """删除缓存项"""
        success = self._adapter.delete(key)

        if success and self._consistency_manager:
            # 通知一致性管理器（使用线程安全的方式）
            try:
                loop = asyncio.get_running_loop()
                # 如果有运行的事件循环，创建任务
                loop.create_task(self._consistency_manager.invalidate_cache([key]))
            except RuntimeError:
                # 没有运行的事件循环，创建新的事件循环
                try:
                    asyncio.run(self._consistency_manager.invalidate_cache([key]))
                except Exception as e:
                    logger.warning(f"一致性管理器失效通知失败: {e}")

        return success

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return self._adapter.exists(key)

    def clear(self) -> None:
        """清空缓存"""
        self._adapter.clear()

        if self._consistency_manager:
            # 清空一致性管理器中的所有缓存
            asyncio.create_task(
                self._consistency_manager.invalidate_cache(
                    self._adapter.keys() if hasattr(self._adapter, "keys") else []
                )
            )

    def size(self) -> int:
        """获取缓存大小"""
        return self._adapter.size()

    # 批量操作
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取缓存值"""
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """批量设置缓存值"""
        success_count = 0
        for key, value in mapping.items():
            if self.set(key, value, ttl):
                success_count += 1
        return success_count == len(mapping)

    def delete_many(self, keys: List[str]) -> int:
        """批量删除缓存项"""
        success_count = 0
        for key in keys:
            if self.delete(key):
                success_count += 1
        return success_count

    # 高级操作
    def incr(self, key: str, amount: int = 1) -> int:
        """递增数值"""
        current = self.get(key, 0)
        if not isinstance(current, (int, float)):
            current = 0
        new_value = current + amount
        self.set(key, new_value)
        return new_value

    def decr(self, key: str, amount: int = 1) -> int:
        """递减数值"""
        return self.incr(key, -amount)

    def ttl(self, key: str) -> int:
        """获取键的TTL"""
        if hasattr(self._adapter, "_cache") and hasattr(self._adapter._cache, "ttl"):
            return self._adapter._cache.ttl(key)
        elif hasattr(self._adapter, "_manager"):
            return self._adapter._manager.ttl(key)
        else:
            return -1

    def expire(self, key: str, seconds: int) -> bool:
        """设置键的过期时间"""
        value = self.get(key)
        if value is not None:
            return self.set(key, value, seconds)
        return False

    # 装饰器支持
    def cached(self, ttl: int = None, key_prefix: str = "cache", **kwargs):
        """缓存装饰器"""
        if ttl is None:
            ttl = self.config.default_ttl

        def decorator(func):
            if not self.config.enable_decorators:
                return func

            # 使用统一的缓存设置
            @cached(
                ttl=ttl, key_prefix=key_prefix, use_consistency_manager=False, **kwargs
            )
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def cache_invalidate(self, pattern: str = None, keys: List[str] = None):
        """缓存失效装饰器"""

        def decorator(func):
            if not self.config.enable_decorators:
                return func

            @cache_invalidate(pattern=pattern, keys=keys)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator

    # 统计和监控
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        stats = {
            "backend": self.config.backend.value,
            "size": self.size(),
            "config": {
                "default_ttl": self.config.default_ttl,
                "use_consistency_manager": self.config.use_consistency_manager,
                "enable_decorators": self.config.enable_decorators,
            },
        }

        if hasattr(self._adapter, "get_stats"):
            stats["adapter_stats"] = self._adapter.get_stats()

        if self._consistency_manager:
            # 获取一致性管理器统计信息（同步版本）
            try:
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果已经在事件循环中，创建任务
                        asyncio.create_task(self._consistency_manager.get_statistics())
                        stats["consistency_stats"] = {"task_created": True}
                    else:
                        # 如果没有运行的事件循环，直接运行
                        stats["consistency_stats"] = loop.run_until_complete(
                            self._consistency_manager.get_statistics()
                        )
                except RuntimeError:
                    # 没有事件循环，创建新的
                    stats["consistency_stats"] = asyncio.run(
                        self._consistency_manager.get_statistics()
                    )
            except Exception as e:
                logger.warning(f"获取一致性管理器统计信息失败: {e}")

        return stats

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health = {
            "status": "healthy",
            "backend": self.config.backend.value,
            "adapter_healthy": True,
            "consistency_healthy": True,
        }

        # 检查适配器健康状态
        try:
            test_key = "__health_check__"
            self.set(test_key, "test", 1)
            value = self.get(test_key)
            self.delete(test_key)
            if value != "test":
                health["adapter_healthy"] = False
        except Exception as e:
            health["adapter_healthy"] = False
            health["adapter_error"] = str(e)

        # 检查一致性管理器健康状态
        if self._consistency_manager:
            try:
                if not self._consistency_manager._running:
                    health["consistency_healthy"] = False
            except Exception as e:
                health["consistency_healthy"] = False
                health["consistency_error"] = str(e)

        # 总体健康状态
        if not health["adapter_healthy"] or not health["consistency_healthy"]:
            health["status"] = "unhealthy"

        return health


# 全局实例
_global_cache_manager: Optional[UnifiedCacheManager] = None


def get_cache_manager(config: UnifiedCacheConfig = None) -> UnifiedCacheManager:
    """获取全局缓存管理器实例"""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = UnifiedCacheManager(config)
    return _global_cache_manager


def reset_cache_manager():
    """重置全局缓存管理器"""
    global _global_cache_manager
    _global_cache_manager = None


# 便捷函数
def cache_get(key: str, default: Any = None) -> Any:
    """便捷获取缓存"""
    return get_cache_manager().get(key, default)


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """便捷设置缓存"""
    return get_cache_manager().set(key, value, ttl)


def cache_delete(key: str) -> bool:
    """便捷删除缓存"""
    return get_cache_manager().delete(key)


def cache_exists(key: str) -> bool:
    """便捷检查缓存是否存在"""
    return get_cache_manager().exists(key)


def cache_clear() -> None:
    """便捷清空缓存"""
    get_cache_manager().clear()


def cache_get_many(keys: List[str]) -> Dict[str, Any]:
    """便捷批量获取缓存"""
    return get_cache_manager().get_many(keys)


def cache_set_many(mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
    """便捷批量设置缓存"""
    return get_cache_manager().set_many(mapping, ttl)


# 导出所有便捷函数
__all__ = [
    "UnifiedCacheManager",
    "UnifiedCacheConfig",
    "CacheBackend",
    "get_cache_manager",
    "reset_cache_manager",
    "cache_get",
    "cache_set",
    "cache_delete",
    "cache_exists",
    "cache_clear",
    "cache_get_many",
    "cache_set_many",
]
