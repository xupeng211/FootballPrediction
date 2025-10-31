"""
缓存一致性管理器
Cache Consistency Manager

提供企业级缓存一致性管理功能，支持多种一致性级别和失效策略。
"""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class ConsistencyLevel(Enum):
    """缓存一致性级别"""
    EVENTUAL = "eventual"     # 最终一致性
    STRONG = "strong"          # 强一致性
    WEAK = "weak"             # 弱一致性


class CacheEvent:
    """缓存事件"""

    def __init__(self, event_type: str, key: str, data: Optional[Dict[str, Any]] = None):
        self.event_type = event_type
        self.key = key
        self.data = data or {}
        self.timestamp = datetime.utcnow()
        self.event_id = f"{event_type}_{int(self.timestamp.timestamp())}"


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    ttl: int
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0


class CacheConsistencyManager:
    """缓存一致性管理器"""

    def __init__(self, consistency_level: ConsistencyLevel = ConsistencyLevel.EVENTUAL):
        """
        初始化缓存一致性管理器

        Args:
            consistency_level: 一致性级别
        """
        self.consistency_level = consistency_level
        self._lock = threading.RLock()
        self._cache_stores: Dict[str, Any] = {}  # 存储后端注册
        self._invalidation_queue = asyncio.Queue()
        self._subscriptions: Dict[str, Set[Callable]] = {}
        self._event_listeners: List[Callable[[CacheEvent], None]] = []
        self._running = False
        self._background_task = None

        logger.info(f"缓存一致性管理器初始化完成，一致性级别: {consistency_level.value}")

    async def start(self) -> None:
        """启动一致性管理器"""
        with self._lock:
            if self._running:
                return

            self._running = True
            self._background_task = asyncio.create_task(self._process_invalidation_queue())
            logger.info("缓存一致性管理器已启动")

    async def stop(self) -> None:
        """停止一致性管理器"""
        with self._lock:
            if not self._running:
                return

            self._running = False

            if self._background_task:
                self._background_task.cancel()
                try:
                    await self._background_task
                except asyncio.CancelledError:
                    pass

            logger.info("缓存一致性管理器已停止")

    def register_cache_store(self, name: str, store: Any) -> None:
        """注册缓存存储后端"""
        with self._lock:
            self._cache_stores[name] = store
            logger.info(f"注册缓存存储: {name}")

    def unregister_cache_store(self, name: str) -> None:
        """注销缓存存储后端"""
        with self._lock:
            if name in self._cache_stores:
                del self._cache_stores[name]
                logger.info(f"注销缓存存储: {name}")

    async def invalidate_cache(self, keys: List[str], reason: str = "manual") -> None:
        """
        缓存失效处理

        Args:
            keys: 要失效的缓存键列表
            reason: 失效原因
        """
        if not keys:
            return

        event = CacheEvent(
            event_type="invalidate",
            keys=keys,
            data={"reason": reason, "count": len(keys)}
        )

        # 根据一致性级别处理失效
        if self.consistency_level == ConsistencyLevel.STRONG:
            # 强一致性：立即失效
            await self._perform_invalidation(keys, event)
        else:
            # 最终一致性：加入队列异步处理
            await self._invalidation_queue.put((keys, event))

        # 通知订阅者
        await self._notify_subscribers(keys, event)

        # 记录事件监听器
        await self._notify_event_listeners(event)

    async def invalidate_pattern(self, pattern: str, reason: str = "pattern") -> None:
        """
        按模式失效缓存

        Args:
            pattern: 缓存键模式
            reason: 失效原因
        """
        # 根据一致性级别处理模式失效
        if self.consistency_level == ConsistencyLevel.STRONG:
            # 强一致性：立即匹配和失效
            keys_to_invalidate = []
            with self._lock:
                for store_name, store in self._cache_stores.items():
                    if hasattr(store, 'get_keys_by_pattern'):
                        try:
                            keys = await store.get_keys_by_pattern(pattern)
                            keys_to_invalidate.extend(keys)
                        except Exception as e:
                            logger.error(f"从存储 {store_name} 获取模式键失败: {e}")

            if keys_to_invalidate:
                await self.invalidate_cache(list(set(keys_to_invalidate)), reason)
        else:
            # 最终一致性：加入模式失效队列
            event = CacheEvent(
                event_type="invalidate_pattern",
                pattern=pattern,
                data={"reason": reason}
            )
            await self._invalidation_queue.put((pattern, event))

    async def get_cache_entry(self, key: str, store_name: str = "default") -> Optional[CacheEntry]:
        """
        获取缓存条目

        Args:
            key: 缓存键
            store_name: 存储名称

        Returns:
            缓存条目或None
        """
        store = self._cache_stores.get(store_name)
        if not store:
            logger.warning(f"存储 {store_name} 未注册")
            return None

        try:
            if hasattr(store, 'get'):
                value = await store.get(key)
                if value is not None:
                    # 更新访问信息
                    await self._update_access_info(key, store_name)
                    return CacheEntry(
                        key=key,
                        value=value,
                        ttl=self._get_ttl(key, store_name),
                        created_at=datetime.utcnow(),
                        last_accessed=datetime.utcnow(),
                        access_count=1
                    )
        except Exception as e:
            logger.error(f"从存储 {store_name} 获取缓存 {key} 失败: {e}")

        return None

    async def set_cache_entry(self, key: str, value: Any, ttl: int, store_name: str = "default") -> bool:
        """
        设置缓存条目

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒）
            store_name: 存储名称

        Returns:
            是否设置成功
        """
        store = self._cache_stores.get(store_name)
        if not store:
            logger.warning(f"存储 {store_name} 未注册")
            return False

        try:
            if hasattr(store, 'set'):
                await store.set(key, value, ttl)

                # 记录设置事件
                event = CacheEvent(
                    event_type="set",
                    key=key,
                    data={"ttl": ttl, "store": store_name}
                )
                await self._notify_event_listeners(event)

                return True
        except Exception as e:
            logger.error(f"向存储 {store_name} 设置缓存 {key} 失败: {e}")

        return False

    def subscribe(self, key: str, callback: Callable[[str], None]) -> None:
        """
        订阅缓存键变化

        Args:
            key: 缓存键
            callback: 回调函数
        """
        with self._lock:
            if key not in self._subscriptions:
                self._subscriptions[key] = set()
            self._subscriptions[key].add(callback)
            logger.info(f"订阅缓存键变化: {key}")

    def unsubscribe(self, key: str, callback: Callable[[str], None]) -> None:
        """
        取消订阅缓存键变化

        Args:
            key: 缓存键
            callback: 回调函数
        """
        with self._lock:
            if key in self._subscriptions and callback in self._subscriptions[key]:
                self._subscriptions[key].remove(callback)
                if not self._subscriptions[key]:
                    del self._subscriptions[key]
                logger.info(f"取消订阅缓存键变化: {key}")

    def add_event_listener(self, listener: Callable[[CacheEvent], None]) -> None:
        """
        添加事件监听器

        Args:
            listener: 事件监听器函数
        """
        self._event_listeners.append(listener)
        logger.info("添加缓存事件监听器")

    def remove_event_listener(self, listener: Callable[[CacheEvent], None]) -> None:
        """
        移除事件监听器

        Args:
            listener: 事件监听器函数
        """
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)
            logger.info("移除缓存事件监听器")

    async def get_statistics(self) -> Dict[str, Any]:
        """
        获取一致性管理器统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            stats = {
                "consistency_level": self.consistency_level.value,
                "registered_stores": list(self._cache_stores.keys()),
                "subscriptions_count": sum(len(subs) for subs in self._subscriptions.values()),
                "event_listeners_count": len(self._event_listeners),
                "queue_size": self._invalidation_queue.qsize(),
                "is_running": self._running
            }

        # 获取存储后端统计
        store_stats = {}
        for name, store in self._cache_stores.items():
            if hasattr(store, 'get_statistics'):
                try:
                    store_stats[name] = await store.get_statistics()
                except Exception as e:
                    logger.error(f"获取存储 {name} 统计信息失败: {e}")

        if store_stats:
            stats["store_statistics"] = store_stats

        return stats

    async def _process_invalidation_queue(self) -> None:
        """处理失效队列"""
        while self._running:
            try:
                # 等待失效任务，设置超时避免阻塞
                task = await asyncio.wait_for(
                    self._invalidation_queue.get(),
                    timeout=1.0
                )

                if task:
                    keys_or_pattern, event = task
                    await self._perform_invalidation(keys_or_pattern, event)

            except asyncio.TimeoutError:
                # 超时是正常的，继续循环
                continue
            except asyncio.CancelledError:
                logger.info("失效队列处理任务被取消")
                break
            except Exception as e:
                logger.error(f"处理失效队列时发生错误: {e}")

    async def _perform_invalidation(self, keys_or_pattern: Any, event: CacheEvent) -> None:
        """执行失效操作"""
        if isinstance(keys_or_pattern, list):
            # 具体键失效
            for store_name, store in self._cache_stores.items():
                for key in keys_or_pattern:
                    try:
                        if hasattr(store, 'delete'):
                            await store.delete(key)
                    except Exception as e:
                        logger.error(f"从存储 {store_name} 删除缓存 {key} 失败: {e}")
        else:
            # 模式失效
            pattern = keys_or_pattern
            for store_name, store in self._cache_stores.items():
                if hasattr(store, 'delete_by_pattern'):
                    try:
                        await store.delete_by_pattern(pattern)
                    except Exception as e:
                        logger.error(f"从存储 {store_name} 模式删除失败: {e}")

    async def _notify_subscribers(self, keys: List[str], event: CacheEvent) -> None:
        """通知订阅者"""
        for key in keys:
            with self._lock:
                if key in self._subscriptions:
                    for callback in self._subscriptions[key]:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(key)
                            else:
                                callback(key)
                        except Exception as e:
                            logger.error(f"通知订阅者 {key} 时发生错误: {e}")

    async def _notify_event_listeners(self, event: CacheEvent) -> None:
        """通知事件监听器"""
        for listener in self._event_listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    listener(event)
            except Exception as e:
                logger.error(f"事件监听器处理失败: {e}")

    async def _update_access_info(self, key: str, store_name: str) -> None:
        """更新访问信息"""
        store = self._cache_stores.get(store_name)
        if store and hasattr(store, 'update_access_info'):
            try:
                await store.update_access_info(key)
            except Exception as e:
                logger.error(f"更新访问信息失败: {e}")

    def _get_ttl(self, key: str, store_name: str) -> int:
        """获取TTL"""
        store = self._cache_stores.get(store_name)
        if store and hasattr(store, 'get_ttl'):
            try:
                return store.get_ttl(key)
            except Exception:
                pass
        return 3600  # 默认TTL


# 全局一致性管理器实例
_global_consistency_manager: Optional[CacheConsistencyManager] = None


def get_consistency_manager() -> CacheConsistencyManager:
    """获取全局一致性管理器实例"""
    global _global_consistency_manager
    if _global_consistency_manager is None:
        _global_consistency_manager = CacheConsistencyManager()
    return _global_consistency_manager


async def start_consistency_manager() -> CacheConsistencyManager:
    """启动全局一致性管理器"""
    manager = get_consistency_manager()
    await manager.start()
    return manager


async def stop_consistency_manager() -> None:
    """停止全局一致性管理器"""
    manager = get_consistency_manager()
    await manager.stop()


# 便捷函数 - 向后兼容
async def invalidate_entity_cache(entity_type: str, entity_id: str = None) -> None:
    """
    实体缓存失效

    Args:
        entity_type: 实体类型
        entity_id: 实体ID（可选）
    """
    manager = get_consistency_manager()

    if entity_id:
        keys = [f"{entity_type}:{entity_id}"]
    else:
        keys = [f"{entity_type}:*"]

    await manager.invalidate_cache(keys, f"entity_{entity_type}_change")


async def sync_entity_cache(entity_type: str, entity_id: str = None, data: Any = None, ttl: int = 3600) -> None:
    """
    同步实体缓存

    Args:
        entity_type: 实体类型
        entity_id: 实体ID（可选）
        data: 缓存数据
        ttl: 生存时间（秒）
    """
    manager = get_consistency_manager()

    if entity_id and data is not None:
        key = f"{entity_type}:{entity_id}"
        await manager.set_cache_entry(key, data, ttl)
        logger.info(f"同步实体缓存: {key}")
