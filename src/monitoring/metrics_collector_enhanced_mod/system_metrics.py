"""
系统指标收集器 / System Metrics Collector

收集和管理系统相关的指标，如CPU、内存、连接数等。
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .metric_types import MetricPoint
from .prometheus_metrics import PrometheusMetricsManager
from .aggregator import MetricsAggregator

logger = logging.getLogger(__name__)


class SystemMetricsCollector:
    """系统指标收集器

    负责收集系统级别的各项指标。
    """

    def __init__(
        self, prometheus_manager: PrometheusMetricsManager, aggregator: MetricsAggregator
    ):
        """
        初始化系统指标收集器

        Args:
            prometheus_manager: Prometheus指标管理器
            aggregator: 指标聚合器
        """
        self.prometheus = prometheus_manager
        self.aggregator = aggregator

        # 错误计数
        self.error_counts: Dict[str, int] = {}

        # 缓存统计
        self.cache_stats: Dict[str, Dict[str, Any]] = {}

    def update_system_metrics(self):
        """更新系统指标"""
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())

            # 内存使用
            memory_info = process.memory_info()
            self.prometheus.set_gauge(
                "memory_usage",
                memory_info.rss,
                labels={"component": "rss"}
            )
            self.prometheus.set_gauge(
                "memory_usage",
                memory_info.vms,
                labels={"component": "vms"}
            )

            # 记录到聚合器
            rss_metric = MetricPoint(
                name="memory_rss",
                value=memory_info.rss,
                labels={"component": "app"},
                unit="bytes",
            )
            self.aggregator.add_metric(rss_metric)

            vms_metric = MetricPoint(
                name="memory_vms",
                value=memory_info.vms,
                labels={"component": "app"},
                unit="bytes",
            )
            self.aggregator.add_metric(vms_metric)

            # CPU使用率
            cpu_percent = process.cpu_percent(interval=0.1)
            self.prometheus.set_gauge(
                "cpu_usage",
                cpu_percent,
                labels={"component": "app"}
            )

            # 记录到聚合器
            cpu_metric = MetricPoint(
                name="cpu_usage",
                value=cpu_percent,
                labels={"component": "app"},
                unit="percent",
            )
            self.aggregator.add_metric(cpu_metric)

            # 系统负载
            load_avg = os.getloadavg()
            for i, period in enumerate(["1m", "5m", "15m"]):
                load_metric = MetricPoint(
                    name="system_load",
                    value=load_avg[i],
                    labels={"period": period},
                    unit="load",
                )
                self.aggregator.add_metric(load_metric)

            # 进程信息
            num_threads = process.num_threads()
            threads_metric = MetricPoint(
                name="process_threads",
                value=num_threads,
                labels={"component": "app"},
                unit="count",
            )
            self.aggregator.add_metric(threads_metric)

            # 文件描述符
            try:
                num_fds = process.num_fds()
                fds_metric = MetricPoint(
                    name="process_fds",
                    value=num_fds,
                    labels={"component": "app"},
                    unit="count",
                )
                self.aggregator.add_metric(fds_metric)
            except (AttributeError, OSError):
                # Windows系统不支持num_fds
                pass

        except ImportError:
            logger.warning("psutil not available, system metrics disabled")
        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")

    def record_error(self, error_type: str, component: str, severity: str = "medium"):
        """
        记录错误指标

        Args:
            error_type: 错误类型
            component: 组件名称
            severity: 严重程度
        """
        error_key = f"{component}:{error_type}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

        # 更新Prometheus
        self.prometheus.increment_counter(
            "error_rate",
            labels={"error_type": error_type}
        )

        # 记录到聚合器
        metric = MetricPoint(
            name="error_count",
            value=1,
            labels={
                "error_type": error_type,
                "component": component,
                "severity": severity,
            },
        )
        self.aggregator.add_metric(metric)

    def record_cache_operation(
        self,
        cache_type: str,
        operation: str,
        hit: Optional[bool] = None,
        size: Optional[int] = None,
        duration: Optional[float] = None,
    ):
        """
        记录缓存操作指标

        Args:
            cache_type: 缓存类型
            operation: 操作类型
            hit: 是否命中
            size: 缓存大小
            duration: 操作耗时
        """
        # 初始化缓存统计
        if cache_type not in self.cache_stats:
            self.cache_stats[cache_type] = {
                "hits": 0,
                "misses": 0,
                "total_ops": 0,
                "last_size": 0,
                "last_update": None,
            }

        stats = self.cache_stats[cache_type]
        stats["total_ops"] += 1

        if hit is not None:
            if hit:
                stats["hits"] += 1
            else:
                stats["misses"] += 1

            # 计算命中率
            hit_rate = stats["hits"] / stats["total_ops"]
            self.prometheus.cache_hit_rate.labels(cache_type=cache_type).set(hit_rate)

            # 记录到聚合器
            hit_rate_metric = MetricPoint(
                name="cache_hit_rate",
                value=hit_rate,
                labels={"cache_type": cache_type, "operation": operation},
                unit="ratio",
            )
            self.aggregator.add_metric(hit_rate_metric)

        if size is not None:
            stats["last_size"] = size
            size_metric = MetricPoint(
                name="cache_size",
                value=size,
                labels={"type": cache_type},
                unit="items",
            )
            self.aggregator.add_metric(size_metric)

        if duration is not None:
            duration_metric = MetricPoint(
                name="cache_operation_duration",
                value=duration,
                labels={"cache_type": cache_type, "operation": operation},
                unit="seconds",
            )
            self.aggregator.add_metric(duration_metric)

        stats["last_update"] = datetime.now()

    def update_connection_metrics(self, connection_counts: Dict[str, int]):
        """
        更新连接数指标

        Args:
            connection_counts: 连接数字典
        """
        for conn_type, count in connection_counts.items():
            self.prometheus.set_gauge(
                "active_connections",
                count,
                labels={"connection_type": conn_type}
            )

            # 记录到聚合器
            metric = MetricPoint(
                name="active_connections",
                value=count,
                labels={"connection_type": conn_type},
                unit="count",
            )
            self.aggregator.add_metric(metric)

    def record_database_metrics(
        self,
        pool_size: int,
        active_connections: int,
        idle_connections: int,
        query_duration: Optional[float] = None,
    ):
        """
        记录数据库连接池指标

        Args:
            pool_size: 连接池大小
            active_connections: 活跃连接数
            idle_connections: 空闲连接数
            query_duration: 查询耗时
        """
        # 更新连接池指标
        self.update_connection_metrics({
            "database_pool": pool_size,
            "database_active": active_connections,
            "database_idle": idle_connections,
        })

        # 记录查询耗时
        if query_duration is not None:
            metric = MetricPoint(
                name="database_query_duration",
                value=query_duration,
                labels={"component": "database"},
                unit="seconds",
            )
            self.aggregator.add_metric(metric)

    def get_system_summary(self) -> Dict[str, Any]:
        """
        获取系统指标摘要

        Returns:
            系统指标摘要字典
        """
        # 计算总错误数
        total_errors = sum(self.error_counts.values())

        # 计算各缓存类型的命中率
        cache_summaries = {}
        for cache_type, stats in self.cache_stats.items():
            if stats["total_ops"] > 0:
                hit_rate = stats["hits"] / stats["total_ops"]
                cache_summaries[cache_type] = {
                    "hit_rate": hit_rate,
                    "total_ops": stats["total_ops"],
                    "last_size": stats["last_size"],
                    "last_update": (
                        stats["last_update"].isoformat()
                        if stats["last_update"]
                        else None
                    ),
                }

        return {
            "errors": {
                "total": total_errors,
                "counts": dict(self.error_counts),
            },
            "cache": cache_summaries,
            "last_updated": datetime.now().isoformat(),
        }