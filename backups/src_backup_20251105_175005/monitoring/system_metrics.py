"""
系统指标收集器
System Metrics Collector

负责收集系统,数据库,缓存等各项指标.
"""

from datetime import datetime
from typing import Any

import psutil
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from src.cache.redis.core.connection_manager import RedisConnectionManager
from src.database.connection import DatabaseManager


class SystemMetricsCollector:
    """类文档字符串"""

    pass  # 添加pass语句
    """系统指标收集器"""

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        self.registry = registry or CollectorRegistry()
        self.db_manager: DatabaseManager | None = None
        self.redis_manager: RedisConnectionManager | None = None

        # 系统指标
        self.cpu_usage = Gauge(
            "system_cpu_usage_percent", "CPU usage percentage", registry=self.registry
        )

        self.memory_usage = Gauge(
            "system_memory_usage_bytes", "Memory usage in bytes", registry=self.registry
        )

        self.disk_usage = Gauge(
            "system_disk_usage_bytes",
            "Disk usage in bytes",
            ["mountpoint"],
            registry=self.registry,
        )

        # 数据库指标
        self.db_connections = Gauge(
            "database_connections_active",
            "Active database connections",
            registry=self.registry,
        )

        self.db_query_duration = Histogram(
            "database_query_duration_seconds",
            "Database query duration",
            ["operation", "table"],
            registry=self.registry,
        )

        # 缓存指标
        self.cache_operations = Counter(
            "cache_operations_total",
            "Total cache operations",
            ["operation", "cache_type", "result"],
            registry=self.registry,
        )

        self.cache_size = Gauge(
            "cache_size_bytes", "Cache size in bytes", registry=self.registry
        )

    def set_database_manager(self, db_manager: DatabaseManager) -> None:
        """设置数据库管理器"""
        self.db_manager = db_manager

    def set_redis_manager(self, redis_manager: RedisConnectionManager) -> None:
        """设置Redis管理器"""
        self.redis_manager = redis_manager

    async def collect_system_metrics(self) -> dict[str, Any]:
        """收集系统指标"""
        metrics = {}

        # CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        self.cpu_usage.set(cpu_percent)
        metrics["cpu_percent"] = cpu_percent

        # 内存使用率
        memory = psutil.virtual_memory()
        self.memory_usage.set(memory.used)
        metrics["memory"] = {
            "total": memory.total,
            "used": memory.used,
            "available": memory.available,
            "percent": memory.percent,
        }

        # 磁盘使用率
        disk_metrics = {}
        for partition in psutil.disk_partitions():
            if partition.mountpoint:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    self.disk_usage.labels(mountpoint=partition.mountpoint).set(
                        usage.used
                    )
                    disk_metrics[partition.mountpoint] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": (usage.used / usage.total) * 100,
                    }
                except PermissionError:
                    continue
        metrics["disk"] = disk_metrics

        # 网络IO
        net_io = psutil.net_io_counters()
        metrics["network"] = {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
        }

        # 进程信息
        process = psutil.Process()
        metrics["process"] = {
            "pid": process.pid,
            "cpu_percent": process.cpu_percent(),
            "memory_percent": process.memory_percent(),
            "memory_info": process.memory_info()._asdict(),
            "create_time": process.create_time(),
            "num_threads": process.num_threads(),
        }

        return metrics

    async def collect_database_metrics(self) -> dict[str, Any]:
        """收集数据库指标"""
        if not self.db_manager:
            return {"error": "Database manager not set"}

        metrics = {}

        try:
            # 连接池状态
            pool = self.db_manager.pool
            if pool:
                self.db_connections.set(pool.size)
                metrics["pool"] = {
                    "size": pool.size,
                    "checked_in": pool.checkedin,
                    "checked_out": pool.checkedout,
                    "overflow": pool.overflow,
                }

            # 执行测试查询
            start_time = datetime.utcnow()
            await self.db_manager.execute("SELECT 1")
            duration = (datetime.utcnow() - start_time).total_seconds()

            self.db_query_duration.labels(operation="test", table="system").observe(
                duration
            )
            metrics["response_time"] = duration

        except (ValueError, RuntimeError, TimeoutError) as e:
            metrics["error"] = str(e)

        return metrics

    async def collect_cache_metrics(self) -> dict[str, Any]:
        """收集缓存指标"""
        if not self.redis_manager:
            return {"error": "Redis manager not set"}

        metrics = {}

        try:
            # Redis 信息
            info = await self.redis_manager.redis.info()

            metrics["memory"] = {
                "used": info.get("used_memory", 0),
                "used_human": info.get("used_memory_human"),
                "peak": info.get("used_memory_peak", 0),
                "rss": info.get("used_memory_rss", 0),
            }

            metrics["clients"] = {
                "connected": info.get("connected_clients", 0),
                "blocked": info.get("blocked_clients", 0),
            }

            metrics["stats"] = {
                "total_commands_processed": info.get("total_commands_processed", 0),
                "total_connections_received": info.get("total_connections_received", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }

            # 计算命中率
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            if hits + misses > 0:
                hit_rate = (hits / (hits + misses)) * 100
                metrics["hit_rate"] = hit_rate

            # 缓存大小
            self.cache_size.set(info.get("used_memory", 0))

        except (ValueError, RuntimeError, TimeoutError) as e:
            metrics["error"] = str(e)

        return metrics

    async def collect_application_metrics(self) -> dict[str, Any]:
        """收集应用程序指标"""
        metrics = {}

        # 获取当前进程信息
        process = psutil.Process()

        # 内存详情
        mem_info = process.memory_info()
        metrics["memory"] = {
            "rss": mem_info.rss,
            "vms": mem_info.vms,
            "shared": mem_info.shared,
            "text": mem_info.text,
            "lib": mem_info.lib,
            "data": mem_info.data,
            "dirty": mem_info.dirty,
        }

        # 文件描述符
        try:
            num_fds = process.num_fds()
            metrics["file_descriptors"] = num_fds
        except (AttributeError, psutil.AccessDenied):
            metrics["file_descriptors"] = 0

        # 线程数
        metrics["threads"] = process.num_threads()

        # 子进程
        children = process.children(recursive=True)
        metrics["children"] = len(children)

        # 上下文切换
        try:
            ctx_switches = process.num_ctx_switches()
            metrics["context_switches"] = {
                "voluntary": ctx_switches.voluntary,
                "involuntary": ctx_switches.involuntary,
            }
        except (AttributeError, psutil.AccessDenied):
            pass

        return metrics
