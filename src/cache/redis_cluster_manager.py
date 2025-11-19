"""Redis集群管理器
Redis Cluster Manager.

提供企业级Redis集群管理、分布式缓存、一致性算法和高可用性支持。
"""

import asyncio
import bisect
import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

try:
    import redis.asyncio as aioredis

    # from redis.cluster import RedisCluster  # 暂时注释，未使用
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    aioredis = None

# 始终导入MockRedisManager以供测试使用

logger = logging.getLogger(__name__)


class CacheConsistencyStrategy(Enum):
    """缓存一致性策略."""

    EVENTUAL_CONSISTENCY = "eventual"  # 最终一致性
    STRONG_CONSISTENCY = "strong"  # 强一致性
    READ_YOUR_WRITES = "ryw"  # 读己之写
    SESSION_CONSISTENCY = "session"  # 会话一致性


class NodeStatus(Enum):
    """节点状态."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    RECOVERING = "recovering"
    FAILED = "failed"


class ReplicationStrategy(Enum):
    """复制策略."""

    MASTER_SLAVE = "master_slave"  # 主从复制
    MULTI_MASTER = "multi_master"  # 多主复制
    CONSISTENT_HASHING = "hashing"  # 一致性哈希
    QUORUM = "quorum"  # 法定人数


@dataclass
class ClusterNode:
    """集群节点配置."""

    node_id: str
    host: str
    port: int
    password: str | None = None
    db: int = 0
    weight: int = 1
    is_master: bool = False
    status: NodeStatus = NodeStatus.HEALTHY
    last_health_check: datetime | None = None
    failure_count: int = 0
    max_failures: int = 3
    connection: Any | None = None

    def __post_init__(self):
        if self.last_health_check is None:
            self.last_health_check = datetime.utcnow()


@dataclass
class ClusterMetrics:
    """集群指标."""

    total_nodes: int = 0
    healthy_nodes: int = 0
    failed_nodes: int = 0
    total_connections: int = 0
    active_connections: int = 0
    cache_hit_rate: float = 0.0
    avg_response_time: float = 0.0
    total_operations: int = 0
    failed_operations: int = 0
    memory_usage: int = 0
    key_count: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CacheEntry:
    """缓存条目."""

    key: str
    value: Any
    ttl: int | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    version: int = 1
    checksum: str = ""

    def __post_init__(self):
        if not self.checksum:
            self.checksum = self._calculate_checksum()

    def _calculate_checksum(self) -> str:
        """计算校验和."""
        data = f"{self.key}{self.value}{self.version}{self.created_at}"
        return hashlib.md5(data.encode()).hexdigest()

    def is_valid(self) -> bool:
        """验证缓存条目有效性."""
        if (
            self.ttl
            and (datetime.utcnow() - self.created_at).total_seconds() > self.ttl
        ):
            return False
        return self.checksum == self._calculate_checksum()

    def is_expired(self) -> bool:
        """检查缓存是否过期."""
        if self.ttl is None:
            return False
        return (datetime.utcnow() - self.created_at).total_seconds() > self.ttl

    def access(self):
        """访问缓存条目，更新访问统计."""
        self.accessed_at = datetime.utcnow()
        self.access_count += 1
        return self.value


class ConsistentHashRing:
    """一致性哈希环."""

    def __init__(self, replicas: int = 150):
        self.replicas = replicas
        self.ring: dict[int, str] = {}
        self.sorted_keys: list[int] = []
        self.nodes: dict[str, ClusterNode] = {}

    def add_node(self, node: ClusterNode):
        """添加节点到哈希环."""
        self.nodes[node.node_id] = node

        # 为每个节点创建多个虚拟节点
        for i in range(self.replicas):
            virtual_key = f"{node.node_id}:{i}"
            hash_value = self._hash(virtual_key)
            self.ring[hash_value] = node.node_id
            bisect.insort(self.sorted_keys, hash_value)

    def remove_node(self, node_id: str):
        """从哈希环移除节点."""
        if node_id not in self.nodes:
            return

        del self.nodes[node_id]

        # 移除所有虚拟节点
        keys_to_remove = []
        for i in range(self.replicas):
            virtual_key = f"{node_id}:{i}"
            hash_value = self._hash(virtual_key)
            if hash_value in self.ring:
                keys_to_remove.append(hash_value)

        for key in keys_to_remove:
            del self.ring[key]
            self.sorted_keys.remove(key)

    def get_node(self, key: str) -> ClusterNode | None:
        """根据键获取对应的节点."""
        if not self.ring:
            return None

        hash_value = self._hash(key)
        idx = bisect.bisect_left(self.sorted_keys, hash_value)

        # 如果超出范围，回到环的起点
        if idx == len(self.sorted_keys):
            idx = 0

        node_id = self.ring[self.sorted_keys[idx]]
        return self.nodes.get(node_id)

    def get_nodes_for_key(self, key: str, count: int = 1) -> list[ClusterNode]:
        """获取键对应的多个节点（用于复制）."""
        if not self.ring:
            return []

        hash_value = self._hash(key)
        idx = bisect.bisect_left(self.sorted_keys, hash_value)

        nodes = []
        visited = set()

        while len(nodes) < count and len(visited) < len(self.nodes):
            if idx >= len(self.sorted_keys):
                idx = 0

            node_id = self.ring[self.sorted_keys[idx]]
            if node_id not in visited:
                node = self.nodes[node_id]
                if node.status == NodeStatus.HEALTHY:
                    nodes.append(node)
                visited.add(node_id)

            idx += 1

        return nodes

    def _hash(self, key: str) -> int:
        """计算哈希值."""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)


class RedisClusterManager:
    """Redis集群管理器."""

    def __init__(
        self,
        consistency_strategy: CacheConsistencyStrategy = CacheConsistencyStrategy.EVENTUAL_CONSISTENCY,
        replication_strategy: ReplicationStrategy = ReplicationStrategy.CONSISTENT_HASHING,
        replication_factor: int = 2,
        health_check_interval: int = 30,
        connection_timeout: int = 5,
        max_retries: int = 3,
    ):
        self.consistency_strategy = consistency_strategy
        self.replication_strategy = replication_strategy
        self.replication_factor = replication_factor
        self.health_check_interval = health_check_interval
        self.connection_timeout = connection_timeout
        self.max_retries = max_retries

        self.nodes: dict[str, ClusterNode] = {}
        self.hash_ring = ConsistentHashRing()
        self.metrics = ClusterMetrics()
        self.is_monitoring = False
        self.monitoring_task: asyncio.Task | None = None

        # 会话一致性支持
        self.session_cache: dict[str, dict[str, Any]] = {}

        # 读写分离
        self.master_nodes: set[str] = set()
        self.slave_nodes: set[str] = set()

        # 缓存统计
        self.operation_stats: dict[str, int] = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
            "retries": 0,
        }

        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using mock implementation")

    async def add_node(self, node_config: dict[str, Any]) -> bool:
        """添加集群节点."""
        try:
            node = ClusterNode(
                node_id=node_config.get(
                    "node_id", f"{node_config['host']}:{node_config['port']}"
                ),
                host=node_config["host"],
                port=node_config["port"],
                password=node_config.get("password"),
                db=node_config.get("db", 0),
                weight=node_config.get("weight", 1),
                is_master=node_config.get("is_master", False),
            )

            # 尝试连接节点
            await self._connect_node(node)

            # 添加到集群
            self.nodes[node.node_id] = node

            if self.replication_strategy == ReplicationStrategy.CONSISTENT_HASHING:
                self.hash_ring.add_node(node)

            # 更新主从节点集合
            if node.is_master:
                self.master_nodes.add(node.node_id)
            else:
                self.slave_nodes.add(node.node_id)

            logger.info(f"Added Redis node: {node.node_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add Redis node: {e}")
            return False

    async def remove_node(self, node_id: str) -> bool:
        """移除集群节点."""
        if node_id not in self.nodes:
            return False

        try:
            node = self.nodes[node_id]

            # 关闭连接
            await self._disconnect_node(node)

            # 从集群移除
            del self.nodes[node_id]

            if self.replication_strategy == ReplicationStrategy.CONSISTENT_HASHING:
                self.hash_ring.remove_node(node_id)

            # 更新主从节点集合
            self.master_nodes.discard(node_id)
            self.slave_nodes.discard(node_id)

            logger.info(f"Removed Redis node: {node_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove Redis node {node_id}: {e}")
            return False

    async def _connect_node(self, node: ClusterNode):
        """连接到Redis节点."""
        if not REDIS_AVAILABLE:
            # 使用Mock Redis
            from .mock_redis import MockRedisManager

            node.connection = MockRedisManager()
            node.status = NodeStatus.HEALTHY
            return

        try:
            if hasattr(aioredis, "from_url"):
                connection = aioredis.from_url(
                    f"redis://{node.host}:{node.port}/{node.db}",
                    password=node.password,
                    socket_timeout=self.connection_timeout,
                    socket_connect_timeout=self.connection_timeout,
                    retry_on_timeout=True,
                    max_connections=10,
                )

                # 测试连接
                await connection.ping()
                node.connection = connection
                node.status = NodeStatus.HEALTHY
                node.last_health_check = datetime.utcnow()
                node.failure_count = 0

            else:
                raise Exception("Redis connection not available")

        except Exception as e:
            logger.error(f"Failed to connect to Redis node {node.node_id}: {e}")
            node.status = NodeStatus.UNHEALTHY
            node.failure_count += 1
            raise

    async def _disconnect_node(self, node: ClusterNode):
        """断开Redis节点连接."""
        if node.connection and hasattr(node.connection, "close"):
            try:
                await node.connection.close()
            except Exception as e:
                logger.error(f"Error closing connection to {node.node_id}: {e}")

    async def get(self, key: str, session_id: str | None = None) -> Any | None:
        """获取缓存值."""
        start_time = time.time()

        try:
            # 会话一致性检查
            if (
                self.consistency_strategy
                == CacheConsistencyStrategy.SESSION_CONSISTENCY
                and session_id
                and session_id in self.session_cache
            ):
                session_data = self.session_cache[session_id]
                if key in session_data:
                    self.operation_stats["hits"] += 1
                    return session_data[key]

            # 选择节点
            nodes = await self._select_nodes_for_read(key)

            for node in nodes:
                try:
                    value = await self._get_from_node(node, key)
                    if value is not None:
                        self.operation_stats["hits"] += 1

                        # 更新会话缓存
                        if (
                            self.consistency_strategy
                            == CacheConsistencyStrategy.SESSION_CONSISTENCY
                            and session_id
                        ):
                            if session_id not in self.session_cache:
                                self.session_cache[session_id] = {}
                            self.session_cache[session_id][key] = value

                        # 更新访问统计
                        await self._update_access_stats(node, key)
                        return value

                except Exception as e:
                    logger.warning(
                        f"Failed to get key {key} from node {node.node_id}: {e}"
                    )
                    await self._handle_node_error(node)
                    continue

            self.operation_stats["misses"] += 1
            return None

        except Exception as e:
            logger.error(f"Error getting key {key}: {e}")
            self.operation_stats["errors"] += 1
            return None

        finally:
            # 更新响应时间
            response_time = time.time() - start_time
            self._update_avg_response_time(response_time)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        session_id: str | None = None,
    ) -> bool:
        """设置缓存值."""
        start_time = time.time()

        try:
            # 创建缓存条目
            cache_entry = CacheEntry(key=key, value=value, ttl=ttl)

            # 选择节点
            nodes = await self._select_nodes_for_write(key)

            success_count = 0
            for node in nodes:
                try:
                    if await self._set_to_node(node, cache_entry):
                        success_count += 1

                except Exception as e:
                    logger.warning(
                        f"Failed to set key {key} to node {node.node_id}: {e}"
                    )
                    await self._handle_node_error(node)

            # 强一致性要求所有节点都成功
            min_success = (
                1
                if self.consistency_strategy
                != CacheConsistencyStrategy.STRONG_CONSISTENCY
                else len(nodes)
            )

            if success_count >= min_success:
                self.operation_stats["sets"] += 1

                # 更新会话缓存
                if (
                    self.consistency_strategy
                    == CacheConsistencyStrategy.SESSION_CONSISTENCY
                    and session_id
                ):
                    if session_id not in self.session_cache:
                        self.session_cache[session_id] = {}
                    self.session_cache[session_id][key] = value

                return True
            else:
                self.operation_stats["errors"] += 1
                return False

        except Exception as e:
            logger.error(f"Error setting key {key}: {e}")
            self.operation_stats["errors"] += 1
            return False

        finally:
            # 更新响应时间
            response_time = time.time() - start_time
            self._update_avg_response_time(response_time)

    async def delete(self, key: str) -> bool:
        """删除缓存值."""
        try:
            # 选择所有可能包含该键的节点
            nodes = await self._select_nodes_for_key(key)

            success_count = 0
            for node in nodes:
                try:
                    if await self._delete_from_node(node, key):
                        success_count += 1

                except Exception as e:
                    logger.warning(
                        f"Failed to delete key {key} from node {node.node_id}: {e}"
                    )
                    await self._handle_node_error(node)

            if success_count > 0:
                self.operation_stats["deletes"] += 1
                return True
            else:
                self.operation_stats["errors"] += 1
                return False

        except Exception as e:
            logger.error(f"Error deleting key {key}: {e}")
            self.operation_stats["errors"] += 1
            return False

    async def _select_nodes_for_read(self, key: str) -> list[ClusterNode]:
        """选择读操作节点."""
        if (
            self.replication_strategy == ReplicationStrategy.MASTER_SLAVE
            and self.slave_nodes
        ):
            # 优先选择从节点读
            healthy_slaves = [
                self.nodes[node_id]
                for node_id in self.slave_nodes
                if self.nodes[node_id].status == NodeStatus.HEALTHY
            ]
            if healthy_slaves:
                return [random.choice(healthy_slaves)]

        # 使用一致性哈希或默认策略
        node = self.hash_ring.get_node(key)
        if node and node.status == NodeStatus.HEALTHY:
            return [node]

        # 如果首选节点不可用，选择其他健康节点
        healthy_nodes = [
            n for n in self.nodes.values() if n.status == NodeStatus.HEALTHY
        ]
        return [random.choice(healthy_nodes)] if healthy_nodes else []

    async def _select_nodes_for_write(self, key: str) -> list[ClusterNode]:
        """选择写操作节点."""
        if self.replication_strategy == ReplicationStrategy.CONSISTENT_HASHING:
            return self.hash_ring.get_nodes_for_key(key, self.replication_factor)

        elif self.replication_strategy == ReplicationStrategy.MASTER_SLAVE:
            # 写主节点
            masters = [
                self.nodes[node_id]
                for node_id in self.master_nodes
                if self.nodes[node_id].status == NodeStatus.HEALTHY
            ]
            if masters:
                return masters

        # 默认策略：选择健康节点
        healthy_nodes = [
            n for n in self.nodes.values() if n.status == NodeStatus.HEALTHY
        ]
        return healthy_nodes[: self.replication_factor] if healthy_nodes else []

    async def _select_nodes_for_key(self, key: str) -> list[ClusterNode]:
        """选择所有可能包含该键的节点."""
        nodes = []

        if self.replication_strategy == ReplicationStrategy.CONSISTENT_HASHING:
            nodes = self.hash_ring.get_nodes_for_key(key, len(self.nodes))
        else:
            nodes = list(self.nodes.values())

        return [node for node in nodes if node.status != NodeStatus.FAILED]

    async def _get_from_node(self, node: ClusterNode, key: str) -> Any | None:
        """从特定节点获取值."""
        if not node.connection:
            return None

        try:
            # 尝试获取缓存条目
            data = await node.connection.get(f"cache:{key}")
            if data:
                cache_entry = json.loads(data)
                entry = CacheEntry(**cache_entry)

                if entry.is_valid():
                    entry.accessed_at = datetime.utcnow()
                    entry.access_count += 1
                    return entry.value
                else:
                    # 过期或无效，删除
                    await self._delete_from_node(node, key)

            return None

        except Exception as e:
            logger.error(f"Error getting from node {node.node_id}: {e}")
            raise

    async def _set_to_node(self, node: ClusterNode, cache_entry: CacheEntry) -> bool:
        """向特定节点设置值."""
        if not node.connection:
            return False

        try:
            data = json.dumps(
                {
                    "key": cache_entry.key,
                    "value": cache_entry.value,
                    "ttl": cache_entry.ttl,
                    "created_at": cache_entry.created_at.isoformat(),
                    "accessed_at": cache_entry.accessed_at.isoformat(),
                    "access_count": cache_entry.access_count,
                    "version": cache_entry.version,
                    "checksum": cache_entry.checksum,
                },
                default=str,
            )

            cache_key = f"cache:{cache_entry.key}"

            if cache_entry.ttl:
                success = await node.connection.setex(cache_key, cache_entry.ttl, data)
            else:
                success = await node.connection.set(cache_key, data)

            return success

        except Exception as e:
            logger.error(f"Error setting to node {node.node_id}: {e}")
            raise

    async def _delete_from_node(self, node: ClusterNode, key: str) -> bool:
        """从特定节点删除值."""
        if not node.connection:
            return False

        try:
            result = await node.connection.delete(f"cache:{key}")
            return result > 0

        except Exception as e:
            logger.error(f"Error deleting from node {node.node_id}: {e}")
            raise

    async def _update_access_stats(self, node: ClusterNode, key: str):
        """更新访问统计."""
        # 这里可以实现访问频率统计
        pass

    async def _handle_node_error(self, node: ClusterNode):
        """处理节点错误."""
        node.failure_count += 1
        node.last_health_check = datetime.utcnow()

        if node.failure_count >= node.max_failures:
            node.status = NodeStatus.FAILED
            logger.warning(
                f"Node {node.node_id} marked as failed after {node.failure_count} failures"
            )
        else:
            node.status = NodeStatus.UNHEALTHY
            logger.warning(f"Node {node.node_id} marked as unhealthy")

    def _update_avg_response_time(self, response_time: float):
        """更新平均响应时间."""
        total_ops = (
            self.operation_stats["hits"]
            + self.operation_stats["misses"]
            + self.operation_stats["sets"]
        )
        if total_ops > 0:
            self.metrics.avg_response_time = (
                self.metrics.avg_response_time * (total_ops - 1) + response_time
            ) / total_ops

    async def start_health_monitoring(self):
        """开始健康监控."""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._health_monitoring_loop())
        logger.info("Redis cluster health monitoring started")

    async def stop_health_monitoring(self):
        """停止健康监控."""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Redis cluster health monitoring stopped")

    async def _health_monitoring_loop(self):
        """健康监控循环."""
        while self.is_monitoring:
            try:
                await self._check_all_nodes_health()
                await self._update_metrics()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(5)

    async def _check_all_nodes_health(self):
        """检查所有节点健康状态."""
        for node in self.nodes.values():
            try:
                await self._check_node_health(node)
            except Exception as e:
                logger.error(f"Error checking health of node {node.node_id}: {e}")

    async def _check_node_health(self, node: ClusterNode):
        """检查单个节点健康状态."""
        try:
            if not node.connection:
                await self._connect_node(node)
                return

            # 执行ping测试
            await asyncio.wait_for(
                node.connection.ping(), timeout=self.connection_timeout
            )

            # 更新健康状态
            if node.status in [NodeStatus.UNHEALTHY, NodeStatus.FAILED]:
                node.status = NodeStatus.RECOVERING
                logger.info(f"Node {node.node_id} is recovering")

            node.status = NodeStatus.HEALTHY
            node.last_health_check = datetime.utcnow()
            node.failure_count = 0

        except Exception as e:
            await self._handle_node_error(node)
            logger.warning(f"Health check failed for node {node.node_id}: {e}")

    async def _update_metrics(self):
        """更新集群指标."""
        self.metrics.total_nodes = len(self.nodes)
        self.metrics.healthy_nodes = len(
            [n for n in self.nodes.values() if n.status == NodeStatus.HEALTHY]
        )
        self.metrics.failed_nodes = len(
            [n for n in self.nodes.values() if n.status == NodeStatus.FAILED]
        )

        # 计算缓存命中率
        total_requests = self.operation_stats["hits"] + self.operation_stats["misses"]
        if total_requests > 0:
            self.metrics.cache_hit_rate = (
                self.operation_stats["hits"] / total_requests
            ) * 100

        self.metrics.total_operations = sum(self.operation_stats.values())
        self.metrics.failed_operations = self.operation_stats["errors"]
        self.metrics.last_updated = datetime.utcnow()

    async def get_cluster_status(self) -> dict[str, Any]:
        """获取集群状态."""
        await self._update_metrics()

        return {
            "cluster_info": {
                "total_nodes": self.metrics.total_nodes,
                "healthy_nodes": self.metrics.healthy_nodes,
                "failed_nodes": self.metrics.failed_nodes,
                "replication_strategy": self.replication_strategy.value,
                "consistency_strategy": self.consistency_strategy.value,
                "replication_factor": self.replication_factor,
            },
            "nodes": {
                node_id: {
                    "host": node.host,
                    "port": node.port,
                    "status": node.status.value,
                    "is_master": node.is_master,
                    "weight": node.weight,
                    "failure_count": node.failure_count,
                    "last_health_check": (
                        node.last_health_check.isoformat()
                        if node.last_health_check
                        else None
                    ),
                }
                for node_id, node in self.nodes.items()
            },
            "metrics": {
                "cache_hit_rate": round(self.metrics.cache_hit_rate, 2),
                "avg_response_time": round(self.metrics.avg_response_time, 4),
                "total_operations": self.metrics.total_operations,
                "failed_operations": self.metrics.failed_operations,
                "operation_stats": self.operation_stats.copy(),
                "last_updated": self.metrics.last_updated.isoformat(),
            },
            "health_monitoring": {
                "active": self.is_monitoring,
                "check_interval": self.health_check_interval,
            },
        }

    async def cleanup_session_cache(self, session_id: str):
        """清理会话缓存."""
        if session_id in self.session_cache:
            del self.session_cache[session_id]

    async def invalidate_key(self, key: str):
        """使键失效（用于缓存更新）."""
        await self.delete(key)

        # 清理会话缓存中的对应键
        for session_data in self.session_cache.values():
            if key in session_data:
                del session_data[key]


# 全局Redis集群管理器实例
_cluster_manager: RedisClusterManager | None = None


def get_redis_cluster_manager() -> RedisClusterManager | None:
    """获取全局Redis集群管理器实例."""
    global _cluster_manager
    return _cluster_manager


async def initialize_redis_cluster(config: dict[str, Any]) -> RedisClusterManager:
    """初始化Redis集群管理器."""
    global _cluster_manager

    consistency_strategy = CacheConsistencyStrategy(
        config.get("consistency_strategy", "eventual")
    )
    replication_strategy = ReplicationStrategy(
        config.get("replication_strategy", "hashing")
    )

    _cluster_manager = RedisClusterManager(
        consistency_strategy=consistency_strategy,
        replication_strategy=replication_strategy,
        replication_factor=config.get("replication_factor", 2),
        health_check_interval=config.get("health_check_interval", 30),
        connection_timeout=config.get("connection_timeout", 5),
        max_retries=config.get("max_retries", 3),
    )

    # 添加节点
    nodes = config.get("nodes", [])
    for node_config in nodes:
        await _cluster_manager.add_node(node_config)

    # 启动健康监控
    await _cluster_manager.start_health_monitoring()

    logger.info(f"Redis cluster initialized with {len(nodes)} nodes")
    return _cluster_manager
