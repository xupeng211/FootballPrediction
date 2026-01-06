#!/usr/bin/env python3
"""
预测结果缓存管理器 (Prediction Cache Manager)

专职负责预测结果的缓存、TTL管理、清理逻辑。
遵循单一职责原则，只负责缓存生命周期管理。
"""

import asyncio
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
import hashlib
import logging
from threading import RLock
import time
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""

    result: dict[str, Any]
    timestamp: float
    ttl: float
    access_count: int = 0
    last_access: float = 0.0

    @property
    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        return time.time() > (self.timestamp + self.ttl)

    @property
    def age_seconds(self) -> float:
        """获取缓存年龄（秒）"""
        return time.time() - self.timestamp

    def update_access(self) -> None:
        """更新访问统计"""
        self.access_count += 1
        self.last_access = time.time()


@dataclass
class CacheStats:
    """缓存统计信息"""

    total_entries: int = 0
    expired_entries: int = 0
    hit_count: int = 0
    miss_count: int = 0
    total_requests: int = 0
    memory_usage_mb: float = 0.0
    cleanup_count: int = 0
    last_cleanup_time: datetime | None = None

    @property
    def hit_rate(self) -> float:
        """缓存命中率"""
        if self.total_requests == 0:
            return 0.0
        return self.hit_count / self.total_requests

    @property
    def miss_rate(self) -> float:
        """缓存未命中率"""
        return 1.0 - self.hit_rate


class PredictionCache:
    """
    预测结果缓存管理器

    主要职责：
    1. 预测结果的缓存存储和检索
    2. TTL（生存时间）管理
    3. 自动过期清理
    4. LRU（最近最少使用）策略
    5. 缓存统计和监控

    设计原则：线程安全、高效、可配置
    """

    def __init__(
        self,
        default_ttl: int = 3600,
        max_size: int = 10000,
        cleanup_interval: int = 300,
        enable_auto_cleanup: bool = True,
    ):
        """
        初始化缓存管理器

        Args:
            default_ttl: 默认TTL（秒），默认1小时
            max_size: 最大缓存条目数，默认10000
            cleanup_interval: 清理间隔（秒），默认5分钟
            enable_auto_cleanup: 是否启用自动清理
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.cleanup_interval = cleanup_interval
        self.enable_auto_cleanup = enable_auto_cleanup

        # 线程安全的缓存存储
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = RLock()

        # 统计信息
        self._stats = CacheStats()

        # 后台清理任务
        self._cleanup_task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

        logger.info(
            f"预测缓存初始化完成: TTL={default_ttl}s, maxSize={max_size}, "
            f"cleanupInterval={cleanup_interval}s, autoCleanup={enable_auto_cleanup}"
        )

        if self.enable_auto_cleanup:
            self._start_cleanup_task()

    def _generate_cache_key(
        self,
        features_hash: str,
        model_name: str,
        additional_params: dict | None = None,
    ) -> str:
        """
        生成缓存键

        Args:
            features_hash: 特征数据的哈希值
            model_name: 模型名称
            additional_params: 额外参数

        Returns:
            str: 缓存键
        """
        key_parts = [model_name, features_hash]

        # 添加额外参数到键中
        if additional_params:
            sorted_params = sorted(additional_params.items())
            params_hash = hashlib.sha256(str(sorted_params).encode(), usedforsecurity=False).hexdigest()[:8]
            key_parts.append(params_hash)

        return ":".join(key_parts)

    def _hash_features(self, features: list[float]) -> str:
        """
        计算特征数据的哈希值

        Args:
            features: 特征数据列表

        Returns:
            str: 特征哈希值
        """
        # 转换为字符串以确保一致性
        features_str = ",".join(map(str, features))
        return hashlib.sha256(features_str.encode(), usedforsecurity=False).hexdigest()

    def get(
        self,
        features: list[float],
        model_name: str,
        additional_params: dict | None = None,
    ) -> dict[str, Any] | None:
        """
        获取缓存结果

        Args:
            features: 特征数据
            model_name: 模型名称
            additional_params: 额外参数

        Returns:
            Optional[Dict[str, Any]]: 缓存的预测结果，如果未找到或已过期则返回None
        """
        with self._lock:
            self._stats.total_requests += 1

            try:
                features_hash = self._hash_features(features)
                cache_key = self._generate_cache_key(features_hash, model_name, additional_params)

                if cache_key not in self._cache:
                    self._stats.miss_count += 1
                    return None

                cache_entry = self._cache[cache_key]

                # 检查是否过期
                if cache_entry.is_expired:
                    # 移除过期条目
                    del self._cache[cache_key]
                    self._stats.expired_entries += 1
                    self._stats.miss_count += 1
                    return None

                # 更新访问统计（LRU）
                cache_entry.update_access()
                self._cache.move_to_end(cache_key)  # 移动到末尾（最近使用）
                self._stats.hit_count += 1

                return cache_entry.result.copy()

            except Exception as e:
                logger.error(f"缓存获取异常: {e}")
                self._stats.miss_count += 1
                return None

    def set(
        self,
        features: list[float],
        model_name: str,
        result: dict[str, Any],
        ttl: int | None = None,
        additional_params: dict | None = None,
    ) -> bool:
        """
        设置缓存结果

        Args:
            features: 特征数据
            model_name: 模型名称
            result: 预测结果
            ttl: 生存时间（秒），如果为None则使用默认TTL
            additional_params: 额外参数

        Returns:
            bool: 设置成功返回True
        """
        with self._lock:
            try:
                features_hash = self._hash_features(features)
                cache_key = self._generate_cache_key(features_hash, model_name, additional_params)

                # 检查缓存大小限制
                if len(self._cache) >= self.max_size:
                    # 移除最久未使用的条目
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]

                # 创建缓存条目
                cache_entry = CacheEntry(
                    result=result.copy(),
                    timestamp=time.time(),
                    ttl=ttl if ttl is not None else self.default_ttl,
                    access_count=1,
                    last_access=time.time(),
                )

                # 存储到缓存
                self._cache[cache_key] = cache_entry
                self._stats.total_entries = len(self._cache)

                return True

            except Exception as e:
                logger.error(f"缓存设置异常: {e}")
                return False

    def delete(
        self,
        features: list[float],
        model_name: str,
        additional_params: dict | None = None,
    ) -> bool:
        """
        删除特定缓存条目

        Args:
            features: 特征数据
            model_name: 模型名称
            additional_params: 额外参数

        Returns:
            bool: 删除成功返回True
        """
        with self._lock:
            try:
                features_hash = self._hash_features(features)
                cache_key = self._generate_cache_key(features_hash, model_name, additional_params)

                if cache_key in self._cache:
                    del self._cache[cache_key]
                    self._stats.total_entries = len(self._cache)
                    return True

                return False

            except Exception as e:
                logger.error(f"缓存删除异常: {e}")
                return False

    def clear(self, pattern: str | None = None) -> int:
        """
        清空缓存

        Args:
            pattern: 模式匹配，如果提供则只删除匹配的条目

        Returns:
            int: 删除的条目数量
        """
        with self._lock:
            try:
                if pattern is None:
                    # 清空所有缓存
                    deleted_count = len(self._cache)
                    self._cache.clear()
                    logger.info(f"所有缓存已清空，共清理 {deleted_count} 个条目")
                else:
                    # 按模式清理
                    keys_to_delete = [key for key in self._cache.keys() if pattern in key]
                    for key in keys_to_delete:
                        del self._cache[key]
                    deleted_count = len(keys_to_delete)
                    logger.info(f"按模式 '{pattern}' 清理缓存，共删除 {deleted_count} 个条目")

                self._stats.total_entries = len(self._cache)
                return deleted_count

            except Exception as e:
                logger.error(f"缓存清理异常: {e}")
                return 0

    def cleanup_expired(self) -> int:
        """
        清理过期的缓存条目

        Returns:
            int: 清理的过期条目数量
        """
        with self._lock:
            try:
                expired_keys = []

                for key, entry in self._cache.items():
                    if entry.is_expired:
                        expired_keys.append(key)

                for key in expired_keys:
                    del self._cache[key]

                self._stats.expired_entries += len(expired_keys)
                self._stats.total_entries = len(self._cache)
                self._stats.cleanup_count += 1
                self._stats.last_cleanup_time = datetime.now()

                if expired_keys:
                    logger.info(f"过期缓存清理完成，共清理 {len(expired_keys)} 个条目")

                return len(expired_keys)

            except Exception as e:
                logger.error(f"过期缓存清理异常: {e}")
                return 0

    def _start_cleanup_task(self) -> None:
        """启动后台清理任务"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("缓存自动清理任务已启动")

    async def _cleanup_loop(self) -> None:
        """后台清理循环"""
        while not self._stop_event.is_set():
            try:
                # 使用可中断的等待
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self.cleanup_interval)
                    break  # 收到停止信号
                except TimeoutError:
                    pass  # 正常超时，继续执行清理

                # 执行清理
                cleaned_count = self.cleanup_expired()
                if cleaned_count > 0:
                    logger.debug(f"清理了 {cleaned_count} 个过期缓存项")

            except Exception as e:
                logger.error(f"后台清理任务异常: {e}")

        logger.info("缓存自动清理任务已停止")

    async def shutdown(self) -> None:
        """优雅关闭缓存管理器"""
        logger.info("开始关闭缓存管理器...")

        # 停止清理任务
        if self._cleanup_task and not self._cleanup_task.done():
            self._stop_event.set()
            try:
                await asyncio.wait_for(self._cleanup_task, timeout=5.0)
            except TimeoutError:
                self._cleanup_task.cancel()
                logger.warning("清理任务强制停止")

        # 清空缓存
        with self._lock:
            entry_count = len(self._cache)
            self._cache.clear()
            logger.info(f"缓存已清空，共清理 {entry_count} 个条目")

        logger.info("缓存管理器已关闭")

    def get_stats(self) -> CacheStats:
        """
        获取缓存统计信息

        Returns:
            CacheStats: 缓存统计信息
        """
        with self._lock:
            # 更新内存使用估算
            total_size = 0
            for entry in self._cache.values():
                # 粗略估算每个条目的内存使用
                total_size += len(str(entry.result))

            self._stats.memory_usage_mb = total_size / (1024 * 1024)
            self._stats.total_entries = len(self._cache)

            return self._stats

    def get_cache_keys(self, pattern: str | None = None) -> list[str]:
        """
        获取缓存键列表

        Args:
            pattern: 模式匹配过滤器

        Returns:
            List[str]: 缓存键列表
        """
        with self._lock:
            keys = list(self._cache.keys())
            if pattern:
                keys = [key for key in keys if pattern in key]
            return keys

    def get_cache_info(self) -> dict[str, Any]:
        """
        获取缓存详细信息

        Returns:
            Dict[str, Any]: 缓存详细信息
        """
        stats = self.get_stats()
        with self._lock:
            return {
                "configuration": {
                    "default_ttl": self.default_ttl,
                    "max_size": self.max_size,
                    "cleanup_interval": self.cleanup_interval,
                    "auto_cleanup_enabled": self.enable_auto_cleanup,
                },
                "status": {
                    "current_size": len(self._cache),
                    "max_size": self.max_size,
                    "utilization_rate": (len(self._cache) / self.max_size if self.max_size > 0 else 0),
                },
                "performance": {
                    "hit_rate": stats.hit_rate,
                    "miss_rate": stats.miss_rate,
                    "total_requests": stats.total_requests,
                    "hit_count": stats.hit_count,
                    "miss_count": stats.miss_count,
                },
                "maintenance": {
                    "expired_entries": stats.expired_entries,
                    "cleanup_count": stats.cleanup_count,
                    "last_cleanup_time": (stats.last_cleanup_time.isoformat() if stats.last_cleanup_time else None),
                },
                "memory": {
                    "estimated_usage_mb": stats.memory_usage_mb,
                    "average_entry_size_kb": (
                        (stats.memory_usage_mb * 1024 / len(self._cache)) if len(self._cache) > 0 else 0
                    ),
                },
            }

    def __len__(self) -> int:
        """返回缓存条目数量"""
        with self._lock:
            return len(self._cache)

    def __contains__(self, cache_key: str) -> bool:
        """检查缓存键是否存在且未过期"""
        with self._lock:
            if cache_key not in self._cache:
                return False
            return not self._cache[cache_key].is_expired

    def is_expired(self, cache_key: str) -> bool:
        """检查特定缓存键是否过期"""
        with self._lock:
            if cache_key not in self._cache:
                return True
            return self._cache[cache_key].is_expired

    # 注意：get_cache_info 方法已在该类的其他位置定义
