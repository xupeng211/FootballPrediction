"""缓存一致性管理器
Cache Consistency Manager.

提供企业级缓存一致性解决方案，支持多种一致性算法、分布式事务和最终一致性保证。
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ConsistencyLevel(Enum):
    """一致性级别."""

    STRONG = "strong"  # 强一致性
    EVENTUAL = "eventual"  # 最终一致性
    SESSION = "session"  # 会话一致性
    MONOTONIC_READ = "monotonic_read"  # 单调读一致性
    MONOTONIC_WRITE = "monotonic_write"  # 单调写一致性
    CAUSAL = "causal"  # 因果一致性


class ConflictResolutionStrategy(Enum):
    """冲突解决策略."""

    LAST_WRITE_WINS = "last_write_wins"  # 最后写入获胜
    FIRST_WRITE_WINS = "first_write_wins"  # 首次写入获胜
    TIMESTAMP_ORDER = "timestamp_order"  # 时间戳顺序
    VECTOR_CLOCK = "vector_clock"  # 向量时钟
    MERGE = "merge"  # 合并策略
    CUSTOM = "custom"  # 自定义策略


class InvalidationStrategy(Enum):
    """失效策略."""

    IMMEDIATE = "immediate"  # 立即失效
    DELAYED = "delayed"  # 延迟失效
    BROADCAST = "broadcast"  # 广播失效
    PUBLISHER_SUBSCRIBER = "pub_sub"  # 发布订阅模式
    TTL_BASED = "ttl_based"  # 基于TTL失效


class CacheEvent:
    """缓存事件."""

    def __init__(
        self,
        event_type: str,
        key: str,
        data: Any = None,
        timestamp: datetime | None = None,
        source_node: str | None = None,
        correlation_id: str | None = None,
    ):
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.key = key
        self.data = data
        self.timestamp = timestamp or datetime.utcnow()
        self.source_node = source_node
        self.correlation_id = correlation_id
        self.processed = False
        self.retry_count = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "key": self.key,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source_node": self.source_node,
            "correlation_id": self.correlation_id,
            "processed": self.processed,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheEvent":
        """从字典创建事件."""
        event = cls(
            event_type=data["event_type"],
            key=data["key"],
            data=data.get("data"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source_node=data.get("source_node"),
            correlation_id=data.get("correlation_id"),
        )
        event.event_id = data["event_id"]
        event.processed = data.get("processed", False)
        event.retry_count = data.get("retry_count", 0)
        return event


class VectorClock:
    """向量时钟实现."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.clock: dict[str, int] = defaultdict(int)
        self.clock[node_id] = 1

    def increment(self) -> "VectorClock":
        """递增本地时钟."""
        self.clock[self.node_id] += 1
        return self

    def update(self, other: "VectorClock") -> "VectorClock":
        """更新时钟（合并操作）."""
        for node_id, timestamp in other.clock.items():
            self.clock[node_id] = max(self.clock[node_id], timestamp)
        return self

    def happens_before(self, other: "VectorClock") -> bool:
        """检查是否先于另一个事件发生."""
        # 如果所有分量都小于等于对方，且至少有一个严格小于
        all_less_equal = all(
            self.clock[node] <= other.clock[node]
            for node in self.clock.keys() | other.clock.keys()
        )
        any_strict_less = any(
            self.clock[node] < other.clock[node]
            for node in self.clock.keys() | other.clock.keys()
        )
        return all_less_equal and any_strict_less

    def is_concurrent(self, other: "VectorClock") -> bool:
        """检查是否并发."""
        return not (self.happens_before(other) or other.happens_before(self))

    def to_dict(self) -> dict[str, int]:
        """转换为字典."""
        return dict(self.clock)

    @classmethod
    def from_dict(cls, node_id: str, data: dict[str, int]) -> "VectorClock":
        """从字典创建向量时钟."""
        clock = cls(node_id)
        clock.clock.update(data)
        return clock


class CacheVersion:
    """缓存版本信息."""

    def __init__(
        self,
        key: str = "",
        version: int = 1,
        timestamp: datetime | None = None,
        node_id: str = "",
        data: Any = None,
        vector_clock: VectorClock | None = None,
        checksum: str = "",
        metadata: dict[str, Any] | None = None,
        **kwargs,
    ):
        self.key = key
        self.version = version
        self.timestamp = timestamp or datetime.utcnow()
        self.node_id = node_id or kwargs.get("node_id", "")
        self.data = data
        self.vector_clock = vector_clock
        self.metadata = metadata or {}
        self.checksum = checksum or self._calculate_checksum()

    def _calculate_checksum(self) -> str:
        """计算校验和."""
        data = f"{self.key}{self.version}{self.timestamp}{self.node_id}"
        if hasattr(self, "data") and self.data:
            data += str(self.data)
        if self.vector_clock:
            data += json.dumps(self.vector_clock.to_dict(), sort_keys=True)
        return hashlib.md5(data.encode()).hexdigest()

    def is_valid(self) -> bool:
        """检查版本有效性."""
        return self.checksum == self._calculate_checksum()


class ConsistencyAlgorithm(ABC):
    """一致性算法抽象类."""

    @abstractmethod
    async def read(self, key: str, node_id: str) -> Any:
        """读取操作."""
        pass

    @abstractmethod
    async def write(self, key: str, value: Any, node_id: str) -> bool:
        """写入操作."""
        pass

    @abstractmethod
    async def invalidate(self, key: str, node_id: str) -> bool:
        """失效操作."""
        pass

    @abstractmethod
    async def resolve_conflict(
        self, key: str, versions: list[CacheVersion]
    ) -> CacheVersion:
        """解决冲突."""
        pass


class StrongConsistencyAlgorithm(ConsistencyAlgorithm):
    """强一致性算法."""

    def __init__(self, quorum_size: int, node_count: int):
        self.quorum_size = quorum_size
        self.node_count = node_count
        self.lock_manager = DistributedLockManager()

    async def read(self, key: str, node_id: str) -> Any:
        """强一致性读取（需要读仲裁）."""
        # 获取读锁
        lock_key = f"read_lock:{key}"
        lock_acquired = await self.lock_manager.acquire(lock_key, node_id, timeout=5.0)

        if not lock_acquired:
            raise Exception(f"Failed to acquire read lock for key {key}")

        try:
            # 从多个节点读取
            responses = []
            tasks = []

            for i in range(self.node_count):
                other_node_id = f"node_{i}"
                if other_node_id != node_id:
                    task = asyncio.create_task(self._read_from_node(key, other_node_id))
                    tasks.append(task)

            # 等待足够多的响应
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )

            # 收集响应
            for task in done:
                try:
                    result = await task
                    if result is not None:
                        responses.append(result)
                except Exception as e:
                    logger.warning(f"Read error from node: {e}")

            # 仲裁读取
            if len(responses) >= self.quorum_size:
                # 选择最新版本
                latest_version = max(responses, key=lambda v: v.timestamp)
                return latest_version.data
            else:
                raise Exception("Read quorum not achieved")

        finally:
            await self.lock_manager.release(lock_key, node_id)

    async def write(self, key: str, value: Any, node_id: str) -> bool:
        """强一致性写入（需要写仲裁）."""
        # 获取写锁
        lock_key = f"write_lock:{key}"
        lock_acquired = await self.lock_manager.acquire(lock_key, node_id, timeout=5.0)

        if not lock_acquired:
            raise Exception(f"Failed to acquire write lock for key {key}")

        try:
            # 创建新版本
            version = CacheVersion(
                key=key,
                version=int(time.time() * 1000000),  # 微秒时间戳
                timestamp=datetime.utcnow(),
                node_id=node_id,
                data=value,
            )

            # 写入多个节点
            success_count = 0
            tasks = []

            for i in range(self.node_count):
                target_node_id = f"node_{i}"
                task = asyncio.create_task(
                    self._write_to_node(key, version, target_node_id)
                )
                tasks.append(task)

            # 等待写入完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, bool) and result:
                    success_count += 1
                elif isinstance(result, Exception):
                    logger.warning(f"Write error: {result}")

            # 仲裁写入
            return success_count >= self.quorum_size

        finally:
            await self.lock_manager.release(lock_key, node_id)

    async def invalidate(self, key: str, node_id: str) -> bool:
        """强一致性失效."""
        # 获取锁并失效所有节点
        lock_key = f"invalidate_lock:{key}"
        lock_acquired = await self.lock_manager.acquire(lock_key, node_id, timeout=5.0)

        if not lock_acquired:
            return False

        try:
            success_count = 0
            tasks = []

            for i in range(self.node_count):
                target_node_id = f"node_{i}"
                task = asyncio.create_task(self._invalidate_node(key, target_node_id))
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, bool) and result:
                    success_count += 1

            return success_count >= self.quorum_size

        finally:
            await self.lock_manager.release(lock_key, node_id)

    async def resolve_conflict(
        self, key: str, versions: list[CacheVersion]
    ) -> CacheVersion:
        """解决冲突（强一致性使用最新时间戳）."""
        if not versions:
            raise ValueError("No versions to resolve")

        # 选择时间戳最新的版本
        return max(versions, key=lambda v: v.timestamp)

    async def _read_from_node(self, key: str, node_id: str) -> CacheVersion | None:
        """从特定节点读取."""
        # 这里实现具体的节点读取逻辑
        pass

    async def _write_to_node(
        self, key: str, version: CacheVersion, node_id: str
    ) -> bool:
        """写入特定节点."""
        # 这里实现具体的节点写入逻辑
        pass

    async def _invalidate_node(self, key: str, node_id: str) -> bool:
        """失效特定节点."""
        # 这里实现具体的节点失效逻辑
        pass


class EventualConsistencyAlgorithm(ConsistencyAlgorithm):
    """最终一致性算法."""

    def __init__(self, node_id: str, conflict_strategy: ConflictResolutionStrategy):
        self.node_id = node_id
        self.conflict_strategy = conflict_strategy
        self.event_queue = deque()
        self.processing = False
        self.vector_clock = VectorClock(node_id)

    async def read(self, key: str, node_id: str) -> Any:
        """最终一致性读取."""
        # 直接读取本地数据
        return await self._read_local(key)

    async def write(self, key: str, value: Any, node_id: str) -> bool:
        """最终一致性写入."""
        # 更新向量时钟
        self.vector_clock.increment()

        # 创建版本
        version = CacheVersion(
            key=key,
            version=int(time.time() * 1000000),
            timestamp=datetime.utcnow(),
            node_id=node_id,
            vector_clock=self.vector_clock,
            data=value,
        )

        # 写入本地
        success = await self._write_local(key, version)

        if success:
            # 异步传播到其他节点
            asyncio.create_task(self._propagate_write(key, version))

        return success

    async def invalidate(self, key: str, node_id: str) -> bool:
        """最终一致性失效."""
        # 创建失效事件
        event = CacheEvent(event_type="invalidate", key=key, source_node=node_id)

        # 本地失效
        success = await self._invalidate_local(key)

        if success:
            # 异步传播失效事件
            asyncio.create_task(self._propagate_event(event))

        return success

    async def resolve_conflict(
        self, key: str, versions: list[CacheVersion]
    ) -> CacheVersion:
        """解决冲突."""
        if not versions:
            raise ValueError("No versions to resolve")

        if self.conflict_strategy == ConflictResolutionStrategy.LAST_WRITE_WINS:
            return max(versions, key=lambda v: v.timestamp)

        elif self.conflict_strategy == ConflictResolutionStrategy.VECTOR_CLOCK:
            # 使用向量时钟解决并发冲突
            latest = versions[0]
            for version in versions[1:]:
                if version.vector_clock and latest.vector_clock:
                    if version.vector_clock.happens_before(latest.vector_clock):
                        latest = version
                    elif not latest.vector_clock.happens_before(version.vector_clock):
                        # 并发冲突，选择时间戳更新的
                        if version.timestamp > latest.timestamp:
                            latest = version
                elif version.timestamp > latest.timestamp:
                    latest = version
            return latest

        elif self.conflict_strategy == ConflictResolutionStrategy.MERGE:
            # 合并策略（对于可合并的数据）
            return await self._merge_versions(key, versions)

        else:
            # 默认使用时间戳
            return max(versions, key=lambda v: v.timestamp)

    async def _read_local(self, key: str) -> Any:
        """读取本地数据."""
        # 实现本地读取逻辑
        pass

    async def _write_local(self, key: str, version: CacheVersion) -> bool:
        """写入本地数据."""
        # 实现本地写入逻辑
        pass

    async def _invalidate_local(self, key: str) -> bool:
        """本地失效."""
        # 实现本地失效逻辑
        pass

    async def _propagate_write(self, key: str, version: CacheVersion):
        """传播写入事件."""
        event = CacheEvent(
            event_type="write",
            key=key,
            data=version.to_dict(),
            source_node=self.node_id,
        )
        await self._propagate_event(event)

    async def _propagate_event(self, event: CacheEvent):
        """传播事件到其他节点."""
        # 实现事件传播逻辑
        pass

    async def _merge_versions(
        self, key: str, versions: list[CacheVersion]
    ) -> CacheVersion:
        """合并版本."""
        # 实现版本合并逻辑
        pass


class DistributedLockManager:
    """分布式锁管理器."""

    def __init__(self):
        self.locks: dict[str, dict[str, Any]] = {}
        self.lock_timeout = 30.0

    async def acquire(self, lock_key: str, node_id: str, timeout: float = 10.0) -> bool:
        """获取分布式锁."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if lock_key not in self.locks:
                self.locks[lock_key] = {
                    "owner": node_id,
                    "acquired_at": time.time(),
                    "expires_at": time.time() + self.lock_timeout,
                }
                return True

            # 检查锁是否过期
            lock_info = self.locks[lock_key]
            if time.time() > lock_info["expires_at"]:
                # 锁已过期，可以获取
                self.locks[lock_key] = {
                    "owner": node_id,
                    "acquired_at": time.time(),
                    "expires_at": time.time() + self.lock_timeout,
                }
                return True

            # 等待一段时间后重试
            await asyncio.sleep(0.1)

        return False

    async def release(self, lock_key: str, node_id: str) -> bool:
        """释放分布式锁."""
        if lock_key in self.locks and self.locks[lock_key]["owner"] == node_id:
            del self.locks[lock_key]
            return True
        return False

    async def is_locked(self, lock_key: str) -> bool:
        """检查锁状态."""
        if lock_key not in self.locks:
            return False

        lock_info = self.locks[lock_key]
        if time.time() > lock_info["expires_at"]:
            del self.locks[lock_key]
            return False

        return True


class CacheConsistencyManager:
    """缓存一致性管理器."""

    def __init__(
        self,
        node_id: str,
        consistency_level: ConsistencyLevel,
        conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS,
    ):
        self.node_id = node_id
        self.consistency_level = consistency_level
        self.conflict_strategy = conflict_strategy

        # 选择一致性算法
        self.algorithm = self._create_consistency_algorithm()

        # 事件系统
        self.event_handlers: dict[str, list[Callable]] = defaultdict(list)
        self.event_queue = asyncio.Queue()
        self.event_processor_running = False

        # 版本管理
        self.version_manager = VersionManager()

        # 会话一致性支持
        self.session_context: dict[str, dict[str, Any]] = {}

        # 统计信息
        self.stats = {
            "reads": 0,
            "writes": 0,
            "invalidations": 0,
            "conflicts": 0,
            "resolutions": 0,
            "errors": 0,
        }

    def _create_consistency_algorithm(self) -> ConsistencyAlgorithm:
        """创建一致性算法."""
        if self.consistency_level == ConsistencyLevel.STRONG:
            # 强一致性需要集群配置
            return StrongConsistencyAlgorithm(quorum_size=2, node_count=3)
        elif self.consistency_level == ConsistencyLevel.EVENTUAL:
            return EventualConsistencyAlgorithm(self.node_id, self.conflict_strategy)
        else:
            # 其他一致性级别的实现
            return EventualConsistencyAlgorithm(self.node_id, self.conflict_strategy)

    async def read(self, key: str, session_id: str | None = None) -> Any:
        """读取操作."""
        try:
            # 会话一致性检查
            if (
                self.consistency_level == ConsistencyLevel.SESSION
                and session_id
                and session_id in self.session_context
            ):
                session_data = self.session_context[session_id]
                if key in session_data:
                    return session_data[key]

            # 执行读取
            result = await self.algorithm.read(key, self.node_id)
            self.stats["reads"] += 1

            # 更新会话上下文
            if (
                self.consistency_level == ConsistencyLevel.SESSION
                and session_id
                and result is not None
            ):
                if session_id not in self.session_context:
                    self.session_context[session_id] = {}
                self.session_context[session_id][key] = result

            # 触发读取事件
            await self._trigger_event("read", {"key": key, "result": result})

            return result

        except Exception as e:
            logger.error(f"Read error for key {key}: {e}")
            self.stats["errors"] += 1
            return None

    async def write(self, key: str, value: Any, session_id: str | None = None) -> bool:
        """写入操作."""
        try:
            # 执行写入
            success = await self.algorithm.write(key, value, self.node_id)
            self.stats["writes"] += 1

            if success:
                # 更新会话上下文
                if self.consistency_level == ConsistencyLevel.SESSION and session_id:
                    if session_id not in self.session_context:
                        self.session_context[session_id] = {}
                    self.session_context[session_id][key] = value

                # 触发写入事件
                await self._trigger_event("write", {"key": key, "value": value})

            return success

        except Exception as e:
            logger.error(f"Write error for key {key}: {e}")
            self.stats["errors"] += 1
            return False

    async def invalidate(self, key: str) -> bool:
        """失效操作."""
        try:
            success = await self.algorithm.invalidate(key, self.node_id)
            self.stats["invalidations"] += 1

            if success:
                # 清理会话上下文
                for session_data in self.session_context.values():
                    if key in session_data:
                        del session_data[key]

                # 触发失效事件
                await self._trigger_event("invalidate", {"key": key})

            return success

        except Exception as e:
            logger.error(f"Invalidate error for key {key}: {e}")
            self.stats["errors"] += 1
            return False

    async def resolve_conflict(
        self, key: str, versions: list[CacheVersion]
    ) -> CacheVersion:
        """解决冲突."""
        try:
            self.stats["conflicts"] += 1
            resolved = await self.algorithm.resolve_conflict(key, versions)
            self.stats["resolutions"] += 1

            logger.info(
                f"Resolved conflict for key {key}: selected version from {resolved.node_id}"
            )
            return resolved

        except Exception as e:
            logger.error(f"Conflict resolution error for key {key}: {e}")
            self.stats["errors"] += 1
            # 返回第一个版本作为默认
            return versions[0]

    async def start_event_processor(self):
        """启动事件处理器."""
        if self.event_processor_running:
            return

        self.event_processor_running = True
        asyncio.create_task(self._event_processor_loop())

    async def stop_event_processor(self):
        """停止事件处理器."""
        self.event_processor_running = False

    async def _event_processor_loop(self):
        """事件处理循环."""
        while self.event_processor_running:
            try:
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                await self._process_event(event)
            except TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Event processing error: {e}")

    async def _process_event(self, event: CacheEvent):
        """处理事件."""
        try:
            if event.event_type == "write":
                # 处理写入事件
                version_data = event.data
                version = CacheVersion.from_dict(version_data)
                await self._handle_remote_write(event.key, version)

            elif event.event_type == "invalidate":
                # 处理失效事件
                await self._handle_remote_invalidation(event.key)

        except Exception as e:
            logger.error(f"Error processing event {event.event_id}: {e}")

    async def _handle_remote_write(self, key: str, version: CacheVersion):
        """处理远程写入."""
        # 检查是否存在冲突
        current_version = await self.version_manager.get_version(key)
        if current_version and current_version.version != version.version:
            # 存在冲突，需要解决
            versions = [current_version, version]
            resolved = await self.resolve_conflict(key, versions)
            await self.version_manager.set_version(key, resolved)
        else:
            # 无冲突，直接设置
            await self.version_manager.set_version(key, version)

    async def _handle_remote_invalidation(self, key: str):
        """处理远程失效."""
        await self.version_manager.remove_version(key)

    async def _trigger_event(self, event_name: str, data: dict[str, Any]):
        """触发事件."""
        if event_name in self.event_handlers:
            for handler in self.event_handlers[event_name]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_name}: {e}")

    def add_event_handler(self, event_name: str, handler: Callable):
        """添加事件处理器."""
        self.event_handlers[event_name].append(handler)

    async def cleanup_session(self, session_id: str):
        """清理会话数据."""
        if session_id in self.session_context:
            del self.session_context[session_id]

    async def get_statistics(self) -> dict[str, Any]:
        """获取统计信息."""
        total_operations = sum(self.stats.values())
        error_rate = (
            (self.stats["errors"] / total_operations * 100)
            if total_operations > 0
            else 0
        )
        conflict_rate = (
            (self.stats["conflicts"] / self.stats["writes"] * 100)
            if self.stats["writes"] > 0
            else 0
        )

        return {
            "consistency_level": self.consistency_level.value,
            "conflict_strategy": self.conflict_strategy.value,
            "statistics": self.stats.copy(),
            "total_operations": total_operations,
            "error_rate": round(error_rate, 2),
            "conflict_rate": round(conflict_rate, 2),
            "active_sessions": len(self.session_context),
            "event_processor_running": self.event_processor_running,
        }


class VersionManager:
    """版本管理器."""

    def __init__(self):
        self.versions: dict[str, CacheVersion] = {}
        self.lock = asyncio.Lock()

    async def get_version(self, key: str) -> CacheVersion | None:
        """获取版本."""
        async with self.lock:
            return self.versions.get(key)

    async def set_version(self, key: str, version: CacheVersion):
        """设置版本."""
        async with self.lock:
            self.versions[key] = version

    async def remove_version(self, key: str):
        """移除版本."""
        async with self.lock:
            if key in self.versions:
                del self.versions[key]

    async def get_all_versions(self) -> dict[str, CacheVersion]:
        """获取所有版本."""
        async with self.lock:
            return self.versions.copy()


# 全局缓存一致性管理器实例
_consistency_manager: CacheConsistencyManager | None = None


def get_cache_consistency_manager() -> CacheConsistencyManager | None:
    """获取全局缓存一致性管理器实例."""
    global _consistency_manager
    return _consistency_manager


async def initialize_cache_consistency(
    node_id: str,
    consistency_level: ConsistencyLevel = ConsistencyLevel.EVENTUAL,
    conflict_strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.LAST_WRITE_WINS,
) -> CacheConsistencyManager:
    """初始化缓存一致性管理器."""
    global _consistency_manager

    _consistency_manager = CacheConsistencyManager(
        node_id=node_id,
        consistency_level=consistency_level,
        conflict_strategy=conflict_strategy,
    )

    # 启动事件处理器
    await _consistency_manager.start_event_processor()

    logger.info(
        f"Cache consistency manager initialized with {consistency_level.value} consistency"
    )
    return _consistency_manager
