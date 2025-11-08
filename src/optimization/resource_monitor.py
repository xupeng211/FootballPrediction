#!/usr/bin/env python3
"""
资源监控和优化系统
提供实时资源监控、性能分析、自动调优和资源池管理功能
"""

import asyncio
import statistics
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from src.core.logger import get_logger

logger = get_logger(__name__)


class AlertLevel(Enum):
    """告警级别"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ResourceType(Enum):
    """资源类型"""

    CPU = "cpu"
    MEMORY = "memory"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    DATABASE_CONNECTIONS = "database_connections"
    CACHE_USAGE = "cache_usage"
    API_REQUESTS = "api_requests"
    BACKGROUND_TASKS = "background_tasks"


@dataclass
class ResourceMetric:
    """资源指标"""

    resource_type: ResourceType
    name: str
    current_value: float
    unit: str
    threshold_warning: float
    threshold_critical: float
    timestamp: datetime
    tags: dict[str, str] = None

    @property
    def is_warning(self) -> bool:
        """是否达到警告级别"""
        return self.current_value >= self.threshold_warning

    @property
    def is_critical(self) -> bool:
        """是否达到严重级别"""
        return self.current_value >= self.threshold_critical

    @property
    def alert_level(self) -> AlertLevel:
        """告警级别"""
        if self.is_critical:
            return AlertLevel.CRITICAL
        elif self.is_warning:
            return AlertLevel.WARNING
        else:
            return AlertLevel.INFO


@dataclass
class ResourceAlert:
    """资源告警"""

    resource_type: ResourceType
    metric_name: str
    alert_level: AlertLevel
    message: str
    current_value: float
    threshold: float
    timestamp: datetime
    resolved: bool = False
    resolved_at: datetime | None = None
    tags: dict[str, str] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "resource_type": self.resource_type.value,
            "metric_name": self.metric_name,
            "alert_level": self.alert_level.value,
            "message": self.message,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "tags": self.tags or {},
        }


@dataclass
class OptimizationAction:
    """优化动作"""

    action_id: str
    resource_type: ResourceType
    action_type: str  # scale_up, scale_down, optimize_config, restart_service
    description: str
    parameters: dict[str, Any]
    expected_impact: str
    risk_level: str  # low, medium, high
    cooldown_period: int  # 冷却时间（秒）
    last_applied: datetime | None = None

    def can_apply(self) -> bool:
        """是否可以应用此动作"""
        if not self.last_applied:
            return True

        cooldown_elapsed = datetime.now() - self.last_applied
        return cooldown_elapsed.total_seconds() >= self.cooldown_period


class ResourceMonitor:
    """资源监控器"""

    def __init__(self, config: dict | None = None):
        self.config = config or self._get_default_config()
        self.metrics_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.active_alerts: dict[str, ResourceAlert] = {}
        self.optimization_actions: dict[str, OptimizationAction] = {}
        self.monitoring_active = False
        self.auto_optimization_enabled = self.config.get("auto_optimization", False)

        # 性能基线
        self.performance_baseline = {}
        self.baseline_established = False

        # 初始化优化动作
        self._initialize_optimization_actions()

        logger.info("资源监控器初始化完成")

    def _get_default_config(self) -> dict:
        """获取默认配置"""
        return {
            "monitoring_interval": 60,  # 监控间隔（秒）
            "metrics_retention_hours": 24,  # 指标保留时间
            "alert_cooldown_minutes": 15,  # 告警冷却时间
            "auto_optimization": True,  # 自动优化
            "optimization_threshold": 0.8,  # 优化阈值
            "performance_window_minutes": 30,  # 性能评估窗口
            "max_concurrent_optimizations": 3,  # 最大并发优化数
            "risk_tolerance": "medium",  # 风险容忍度
        }

    def _initialize_optimization_actions(self) -> None:
        """初始化优化动作"""
        actions = [
            # CPU优化动作
            OptimizationAction(
                action_id="cpu_scale_up",
                resource_type=ResourceType.CPU,
                action_type="scale_up",
                description="增加CPU资源",
                parameters={"increment": 1, "max_vcpus": 16},
                expected_impact="CPU使用率下降15-25%",
                risk_level="low",
                cooldown_period=300,  # 5分钟
            ),
            OptimizationAction(
                action_id="cpu_scale_down",
                resource_type=ResourceType.CPU,
                action_type="scale_down",
                description="减少CPU资源",
                parameters={"decrement": 1, "min_vcpus": 2},
                expected_impact="节省成本10-20%",
                risk_level="medium",
                cooldown_period=600,  # 10分钟
            ),
            # 内存优化动作
            OptimizationAction(
                action_id="memory_scale_up",
                resource_type=ResourceType.MEMORY,
                action_type="scale_up",
                description="增加内存资源",
                parameters={"increment_gb": 2, "max_memory_gb": 64},
                expected_impact="内存压力缓解，性能提升20-30%",
                risk_level="low",
                cooldown_period=300,
            ),
            OptimizationAction(
                action_id="memory_scale_down",
                resource_type=ResourceType.MEMORY,
                action_type="scale_down",
                description="减少内存资源",
                parameters={"decrement_gb": 2, "min_memory_gb": 4},
                expected_impact="节省成本15-25%",
                risk_level="medium",
                cooldown_period=600,
            ),
            # 数据库优化动作
            OptimizationAction(
                action_id="db_connections_optimize",
                resource_type=ResourceType.DATABASE_CONNECTIONS,
                action_type="optimize_config",
                description="优化数据库连接池",
                parameters={"max_connections": 100, "min_connections": 10},
                expected_impact="连接效率提升，响应时间减少10-20%",
                risk_level="low",
                cooldown_period=180,
            ),
            # 缓存优化动作
            OptimizationAction(
                action_id="cache_cleanup",
                resource_type=ResourceType.CACHE_USAGE,
                action_type="optimize_config",
                description="清理过期缓存数据",
                parameters={"cleanup_expired": True, "compress_data": True},
                expected_impact="内存使用减少15-30%",
                risk_level="low",
                cooldown_period=900,  # 15分钟
            ),
            OptimizationAction(
                action_id="cache_scale_up",
                resource_type=ResourceType.CACHE_USAGE,
                action_type="scale_up",
                description="扩展缓存容量",
                parameters={"increment_gb": 1, "max_memory_gb": 16},
                expected_impact="缓存命中率提升，性能提升10-20%",
                risk_level="medium",
                cooldown_period=600,
            ),
        ]

        for action in actions:
            self.optimization_actions[action.action_id] = action

    async def start_monitoring(self) -> None:
        """启动监控"""
        if self.monitoring_active:
            logger.warning("资源监控已在运行中")
            return

        self.monitoring_active = True
        logger.info("启动资源监控...")

        monitoring_task = asyncio.create_task(self._monitoring_loop())

        try:
            await monitoring_task
        except asyncio.CancelledError:
            logger.info("资源监控已停止")
            self.monitoring_active = False
        except Exception as e:
            logger.error(f"资源监控异常: {e}")
            self.monitoring_active = False
            raise

    async def stop_monitoring(self) -> None:
        """停止监控"""
        self.monitoring_active = False
        logger.info("停止资源监控...")

    async def _monitoring_loop(self) -> None:
        """监控循环"""
        while self.monitoring_active:
            try:
                # 收集所有资源指标
                metrics = await self._collect_all_metrics()

                # 处理指标并检测告警
                await self._process_metrics(metrics)

                # 执行自动优化
                if self.auto_optimization_enabled:
                    await self._auto_optimize()

                # 清理过期数据
                await self._cleanup_expired_data()

                logger.debug("监控周期完成")

            except Exception as e:
                logger.error(f"监控周期异常: {e}")

            # 等待下一个监控周期
            await asyncio.sleep(self.config["monitoring_interval"])

    async def _collect_all_metrics(self) -> list[ResourceMetric]:
        """收集所有资源指标"""
        metrics = []

        # 收集各种资源指标
        metric_collectors = [
            self._collect_cpu_metrics,
            self._collect_memory_metrics,
            self._collect_disk_io_metrics,
            self._collect_network_metrics,
            self._collect_database_metrics,
            self._collect_cache_metrics,
            self._collect_api_metrics,
            self._collect_background_task_metrics,
        ]

        for collector in metric_collectors:
            try:
                collector_metrics = await collector()
                metrics.extend(collector_metrics)
            except Exception as e:
                logger.warning(f"指标收集失败 {collector.__name__}: {e}")

        return metrics

    async def _collect_cpu_metrics(self) -> list[ResourceMetric]:
        """收集CPU指标"""
        try:
            import psutil

            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)

            # 每核心CPU使用率
            cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)

            # CPU负载
            load_avg = psutil.getloadavg()

            metrics = [
                ResourceMetric(
                    resource_type=ResourceType.CPU,
                    name="cpu_usage_percent",
                    current_value=cpu_percent,
                    unit="percent",
                    threshold_warning=70.0,
                    threshold_critical=90.0,
                    timestamp=datetime.now(),
                    tags={"component": "system"},
                ),
                ResourceMetric(
                    resource_type=ResourceType.CPU,
                    name="load_average_1m",
                    current_value=load_avg[0],
                    unit="count",
                    threshold_warning=psutil.cpu_count() * 0.7,
                    threshold_critical=psutil.cpu_count() * 0.9,
                    timestamp=datetime.now(),
                    tags={"component": "system"},
                ),
            ]

            # 添加每核心CPU指标
            for i, core_usage in enumerate(cpu_per_core):
                metrics.append(
                    ResourceMetric(
                        resource_type=ResourceType.CPU,
                        name=f"cpu_core_{i}_usage",
                        current_value=core_usage,
                        unit="percent",
                        threshold_warning=80.0,
                        threshold_critical=95.0,
                        timestamp=datetime.now(),
                        tags={"component": "system", "core": str(i)},
                    )
                )

            return metrics

        except Exception as e:
            logger.warning(f"收集CPU指标失败: {e}")
            return []

    async def _collect_memory_metrics(self) -> list[ResourceMetric]:
        """收集内存指标"""
        try:
            import psutil

            virtual_memory = psutil.virtual_memory()
            swap_memory = psutil.swap_memory()

            metrics = [
                ResourceMetric(
                    resource_type=ResourceType.MEMORY,
                    name="memory_usage_percent",
                    current_value=virtual_memory.percent,
                    unit="percent",
                    threshold_warning=80.0,
                    threshold_critical=95.0,
                    timestamp=datetime.now(),
                    tags={"component": "system"},
                ),
                ResourceMetric(
                    resource_type=ResourceType.MEMORY,
                    name="memory_available_gb",
                    current_value=virtual_memory.available / (1024**3),
                    unit="GB",
                    threshold_warning=2.0,
                    threshold_critical=1.0,
                    timestamp=datetime.now(),
                    tags={"component": "system"},
                ),
                ResourceMetric(
                    resource_type=ResourceType.MEMORY,
                    name="swap_usage_percent",
                    current_value=swap_memory.percent,
                    unit="percent",
                    threshold_warning=50.0,
                    threshold_critical=80.0,
                    timestamp=datetime.now(),
                    tags={"component": "system"},
                ),
            ]

            return metrics

        except Exception as e:
            logger.warning(f"收集内存指标失败: {e}")
            return []

    async def _collect_disk_io_metrics(self) -> list[ResourceMetric]:
        """收集磁盘IO指标"""
        try:
            import psutil

            disk_io = psutil.disk_io_counters()
            disk_usage = psutil.disk_usage("/")

            # 计算IO速率（需要历史数据）
            metrics = []

            if disk_io:
                metrics.append(
                    ResourceMetric(
                        resource_type=ResourceType.DISK_IO,
                        name="disk_read_bytes_per_sec",
                        current_value=disk_io.read_bytes,  # 实际应该计算速率
                        unit="bytes/sec",
                        threshold_warning=100 * 1024 * 1024,  # 100MB/s
                        threshold_critical=200 * 1024 * 1024,  # 200MB/s
                        timestamp=datetime.now(),
                        tags={"component": "storage"},
                    )
                )

                metrics.append(
                    ResourceMetric(
                        resource_type=ResourceType.DISK_IO,
                        name="disk_write_bytes_per_sec",
                        current_value=disk_io.write_bytes,  # 实际应该计算速率
                        unit="bytes/sec",
                        threshold_warning=100 * 1024 * 1024,
                        threshold_critical=200 * 1024 * 1024,
                        timestamp=datetime.now(),
                        tags={"component": "storage"},
                    )
                )

            # 磁盘使用率
            usage_percent = (disk_usage.used / disk_usage.total) * 100
            metrics.append(
                ResourceMetric(
                    resource_type=ResourceType.DISK_IO,
                    name="disk_usage_percent",
                    current_value=usage_percent,
                    unit="percent",
                    threshold_warning=80.0,
                    threshold_critical=95.0,
                    timestamp=datetime.now(),
                    tags={"component": "storage"},
                )
            )

            return metrics

        except Exception as e:
            logger.warning(f"收集磁盘IO指标失败: {e}")
            return []

    async def _collect_network_metrics(self) -> list[ResourceMetric]:
        """收集网络指标"""
        try:
            import psutil

            network_io = psutil.net_io_counters()

            metrics = []

            if network_io:
                # 网络IO速率
                metrics.append(
                    ResourceMetric(
                        resource_type=ResourceType.NETWORK_IO,
                        name="network_bytes_sent_per_sec",
                        current_value=network_io.bytes_sent,  # 实际应该计算速率
                        unit="bytes/sec",
                        threshold_warning=100 * 1024 * 1024,  # 100MB/s
                        threshold_critical=500 * 1024 * 1024,  # 500MB/s
                        timestamp=datetime.now(),
                        tags={"component": "network"},
                    )
                )

                metrics.append(
                    ResourceMetric(
                        resource_type=ResourceType.NETWORK_IO,
                        name="network_bytes_recv_per_sec",
                        current_value=network_io.bytes_recv,  # 实际应该计算速率
                        unit="bytes/sec",
                        threshold_warning=100 * 1024 * 1024,
                        threshold_critical=500 * 1024 * 1024,
                        timestamp=datetime.now(),
                        tags={"component": "network"},
                    )
                )

            return metrics

        except Exception as e:
            logger.warning(f"收集网络指标失败: {e}")
            return []

    async def _collect_database_metrics(self) -> list[ResourceMetric]:
        """收集数据库指标"""
        # 模拟数据库指标收集
        # 实际实现需要连接到具体数据库

        try:
            # 模拟连接数
            active_connections = 25
            max_connections = 100

            # 模拟查询性能
            avg_query_time = 85  # ms
            slow_queries = 5

            metrics = [
                ResourceMetric(
                    resource_type=ResourceType.DATABASE_CONNECTIONS,
                    name="active_connections",
                    current_value=active_connections,
                    unit="count",
                    threshold_warning=max_connections * 0.8,
                    threshold_critical=max_connections * 0.95,
                    timestamp=datetime.now(),
                    tags={"component": "database"},
                ),
                ResourceMetric(
                    resource_type=ResourceType.DATABASE_CONNECTIONS,
                    name="connection_usage_percent",
                    current_value=(active_connections / max_connections) * 100,
                    unit="percent",
                    threshold_warning=80.0,
                    threshold_critical=95.0,
                    timestamp=datetime.now(),
                    tags={"component": "database"},
                ),
                ResourceMetric(
                    resource_type=ResourceType.DATABASE_CONNECTIONS,
                    name="avg_query_time_ms",
                    current_value=avg_query_time,
                    unit="ms",
                    threshold_warning=200.0,
                    threshold_critical=1000.0,
                    timestamp=datetime.now(),
                    tags={"component": "database"},
                ),
                ResourceMetric(
                    resource_type=ResourceType.DATABASE_CONNECTIONS,
                    name="slow_queries_count",
                    current_value=slow_queries,
                    unit="count",
                    threshold_warning=10.0,
                    threshold_critical=50.0,
                    timestamp=datetime.now(),
                    tags={"component": "database"},
                ),
            ]

            return metrics

        except Exception as e:
            logger.warning(f"收集数据库指标失败: {e}")
            return []

    async def _collect_cache_metrics(self) -> list[ResourceMetric]:
        """收集缓存指标"""
        try:
            # 模拟Redis指标
            cache_memory = 1.5  # GB
            cache_memory_limit = 4.0  # GB
            hit_rate = 0.82  # 82%
            keys_count = 150000

            metrics = [
                ResourceMetric(
                    resource_type=ResourceType.CACHE_USAGE,
                    name="memory_usage_percent",
                    current_value=(cache_memory / cache_memory_limit) * 100,
                    unit="percent",
                    threshold_warning=80.0,
                    threshold_critical=95.0,
                    timestamp=datetime.now(),
                    tags={"component": "cache"},
                ),
                ResourceMetric(
                    resource_type=ResourceType.CACHE_USAGE,
                    name="hit_rate_percent",
                    current_value=hit_rate * 100,
                    unit="percent",
                    threshold_warning=70.0,
                    threshold_critical=50.0,  # 命中率低是问题
                    timestamp=datetime.now(),
                    tags={"component": "cache"},
                ),
                ResourceMetric(
                    resource_type=ResourceType.CACHE_USAGE,
                    name="keys_count",
                    current_value=keys_count,
                    unit="count",
                    threshold_warning=1000000,  # 100万键
                    threshold_critical=2000000,  # 200万键
                    timestamp=datetime.now(),
                    tags={"component": "cache"},
                ),
            ]

            return metrics

        except Exception as e:
            logger.warning(f"收集缓存指标失败: {e}")
            return []

    async def _collect_api_metrics(self) -> list[ResourceMetric]:
        """收集API指标"""
        try:
            # 模拟API指标
            requests_per_minute = 850
            avg_response_time = 120  # ms
            error_rate = 0.02  # 2%

            metrics = [
                ResourceMetric(
                    resource_type=ResourceType.API_REQUESTS,
                    name="requests_per_minute",
                    current_value=requests_per_minute,
                    unit="req/min",
                    threshold_warning=1000.0,
                    threshold_critical=2000.0,
                    timestamp=datetime.now(),
                    tags={"component": "api"},
                ),
                ResourceMetric(
                    resource_type=ResourceType.API_REQUESTS,
                    name="avg_response_time_ms",
                    current_value=avg_response_time,
                    unit="ms",
                    threshold_warning=500.0,
                    threshold_critical=2000.0,
                    timestamp=datetime.now(),
                    tags={"component": "api"},
                ),
                ResourceMetric(
                    resource_type=ResourceType.API_REQUESTS,
                    name="error_rate_percent",
                    current_value=error_rate * 100,
                    unit="percent",
                    threshold_warning=5.0,
                    threshold_critical=15.0,
                    timestamp=datetime.now(),
                    tags={"component": "api"},
                ),
            ]

            return metrics

        except Exception as e:
            logger.warning(f"收集API指标失败: {e}")
            return []

    async def _collect_background_task_metrics(self) -> list[ResourceMetric]:
        """收集后台任务指标"""
        try:
            # 模拟后台任务指标
            active_tasks = 15
            pending_tasks = 8
            failed_tasks_24h = 3

            metrics = [
                ResourceMetric(
                    resource_type=ResourceType.BACKGROUND_TASKS,
                    name="active_tasks_count",
                    current_value=active_tasks,
                    unit="count",
                    threshold_warning=50.0,
                    threshold_critical=100.0,
                    timestamp=datetime.now(),
                    tags={"component": "tasks"},
                ),
                ResourceMetric(
                    resource_type=ResourceType.BACKGROUND_TASKS,
                    name="pending_tasks_count",
                    current_value=pending_tasks,
                    unit="count",
                    threshold_warning=20.0,
                    threshold_critical=50.0,
                    timestamp=datetime.now(),
                    tags={"component": "tasks"},
                ),
                ResourceMetric(
                    resource_type=ResourceType.BACKGROUND_TASKS,
                    name="failed_tasks_24h",
                    current_value=failed_tasks_24h,
                    unit="count",
                    threshold_warning=10.0,
                    threshold_critical=50.0,
                    timestamp=datetime.now(),
                    tags={"component": "tasks"},
                ),
            ]

            return metrics

        except Exception as e:
            logger.warning(f"收集后台任务指标失败: {e}")
            return []

    async def _process_metrics(self, metrics: list[ResourceMetric]) -> None:
        """处理指标"""
        current_time = datetime.now()

        for metric in metrics:
            # 存储指标历史
            key = f"{metric.resource_type.value}_{metric.name}"
            self.metrics_history[key].append(metric)

            # 检查告警条件
            await self._check_alerts(metric)

        # 更新性能基线
        if not self.baseline_established:
            await self._establish_baseline()

    async def _check_alerts(self, metric: ResourceMetric) -> None:
        """检查告警"""
        if not (metric.is_warning or metric.is_critical):
            # 检查是否需要解决现有告警
            await self._resolve_alerts_if_needed(metric)
            return

        # 创建告警key
        alert_key = f"{metric.resource_type.value}_{metric.name}"

        # 检查是否已有活跃告警
        if alert_key in self.active_alerts:
            existing_alert = self.active_alerts[alert_key]

            # 更新告警级别（如果升级）
            if metric.alert_level.value > existing_alert.alert_level.value:
                existing_alert.alert_level = metric.alert_level
                existing_alert.current_value = metric.current_value
                existing_alert.timestamp = metric.timestamp
                logger.info(f"告警升级: {alert_key} -> {metric.alert_level.value}")

        else:
            # 创建新告警
            alert = ResourceAlert(
                resource_type=metric.resource_type,
                metric_name=metric.name,
                alert_level=metric.alert_level,
                message=f"{metric.resource_type.value} {metric.name} 达到 {metric.alert_level.value} 级别: {metric.current_value} {metric.unit}",
                current_value=metric.current_value,
                threshold=(
                    metric.threshold_critical
                    if metric.is_critical
                    else metric.threshold_warning
                ),
                timestamp=metric.timestamp,
                tags=metric.tags,
            )

            self.active_alerts[alert_key] = alert

            # 发送告警通知
            await self._send_alert(alert)

            logger.warning(f"新告警: {alert.message}")

    async def _resolve_alerts_if_needed(self, metric: ResourceMetric) -> None:
        """如果条件允许，解决告警"""
        alert_key = f"{metric.resource_type.value}_{metric.name}"

        if alert_key in self.active_alerts:
            # 检查是否已恢复到正常水平
            if not metric.is_warning:
                alert = self.active_alerts[alert_key]
                alert.resolved = True
                alert.resolved_at = datetime.now()

                logger.info(f"告警已解决: {alert.message}")

                # 发送解决通知
                await self._send_alert_resolved(alert)

                # 从活跃告警中移除
                del self.active_alerts[alert_key]

    async def _send_alert(self, alert: ResourceAlert) -> None:
        """发送告警通知"""
        # 这里可以集成实际的告警系统
        # 如邮件、Slack、企业微信、钉钉等

        message = f"🚨 [{alert.alert_level.value.upper()}] {alert.message}"
        message += f"\n当前值: {alert.current_value}"
        message += f"\n阈值: {alert.threshold}"
        message += f"\n时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

        if alert.tags:
            message += f"\n标签: {', '.join(f'{k}={v}' for k, v in alert.tags.items())}"

        logger.warning(f"告警通知: {message}")

        # 实际实现中，这里会调用通知服务
        # await self.notification_service.send_alert(message, alert.alert_level)

    async def _send_alert_resolved(self, alert: ResourceAlert) -> None:
        """发送告警解决通知"""
        message = f"✅ 告警已解决: {alert.message}"
        message += f"\n解决时间: {alert.resolved_at.strftime('%Y-%m-%d %H:%M:%S')}"

        logger.info(f"告警解决通知: {message}")

        # 实际实现中，这里会调用通知服务
        # await self.notification_service.send_alert_resolved(message)

    async def _establish_baseline(self) -> None:
        """建立性能基线"""
        if len(self.metrics_history) < 10:  # 需要足够的数据点
            return

        try:
            baseline_data = {}

            for key, metrics in self.metrics_history.items():
                if len(metrics) >= 5:
                    values = [m.current_value for m in metrics]
                    baseline_data[key] = {
                        "mean": statistics.mean(values),
                        "median": statistics.median(values),
                        "stddev": statistics.stdev(values) if len(values) > 1 else 0,
                        "min": min(values),
                        "max": max(values),
                    }

            if baseline_data:
                self.performance_baseline = baseline_data
                self.baseline_established = True
                logger.info("性能基线建立完成")

        except Exception as e:
            logger.warning(f"建立性能基线失败: {e}")

    async def _auto_optimize(self) -> None:
        """自动优化"""
        if not self.active_alerts:
            return

        # 收集需要优化的资源类型
        resource_types_with_alerts = set()
        for alert in self.active_alerts.values():
            if not alert.resolved and alert.alert_level in [
                AlertLevel.WARNING,
                AlertLevel.CRITICAL,
            ]:
                resource_types_with_alerts.add(alert.resource_type)

        # 为每种资源类型寻找优化动作
        optimization_candidates = []

        for resource_type in resource_types_with_alerts:
            candidates = await self._find_optimization_candidates(resource_type)
            optimization_candidates.extend(candidates)

        # 按优先级排序
        optimization_candidates.sort(
            key=lambda x: self._get_optimization_priority(x), reverse=True
        )

        # 执行优化（限制并发数量）
        max_concurrent = self.config["max_concurrent_optimizations"]
        executed_count = 0

        for action in optimization_candidates:
            if executed_count >= max_concurrent:
                break

            if action.can_apply():
                success = await self._execute_optimization_action(action)
                if success:
                    executed_count += 1
                    action.last_applied = datetime.now()

    async def _find_optimization_candidates(
        self, resource_type: ResourceType
    ) -> list[OptimizationAction]:
        """为资源类型寻找优化候选"""
        candidates = []

        # 获取该资源类型的活跃告警
        alerts = [
            alert
            for alert in self.active_alerts.values()
            if alert.resource_type == resource_type and not alert.resolved
        ]

        if not alerts:
            return candidates

        # 根据告警类型和严重程度选择合适的优化动作
        for action in self.optimization_actions.values():
            if action.resource_type != resource_type:
                continue

            # 根据告警级别选择动作
            if any(alert.alert_level == AlertLevel.CRITICAL for alert in alerts):
                # 严重告警，选择扩容动作
                if (
                    "scale_up" in action.action_id
                    or "optimize_config" in action.action_id
                ):
                    candidates.append(action)
            elif any(alert.alert_level == AlertLevel.WARNING for alert in alerts):
                # 警告告警，可以选择缩容或优化配置
                if (
                    self.config["risk_tolerance"] == "aggressive"
                    and "scale_down" in action.action_id
                ):
                    candidates.append(action)
                elif "optimize_config" in action.action_id:
                    candidates.append(action)

        return candidates

    def _get_optimization_priority(self, action: OptimizationAction) -> float:
        """获取优化优先级分数"""
        base_score = 0

        # 根据风险容忍度调整
        if self.config["risk_tolerance"] == "aggressive":
            if action.risk_level == "high":
                base_score += 3
            elif action.risk_level == "medium":
                base_score += 2
            else:
                base_score += 1
        elif self.config["risk_tolerance"] == "conservative":
            if action.risk_level == "low":
                base_score += 3
            elif action.risk_level == "medium":
                base_score += 1
        else:  # medium
            if action.risk_level == "medium":
                base_score += 3
            elif action.risk_level == "low":
                base_score += 2
            else:
                base_score += 1

        # 根据动作类型调整
        if "optimize_config" in action.action_type:
            base_score += 2  # 配置优化优先级高
        elif "scale_up" in action.action_type:
            base_score += 1  # 扩容次之
        elif "scale_down" in action.action_type:
            base_score += 0  # 缩容优先级最低

        return base_score

    async def _execute_optimization_action(self, action: OptimizationAction) -> bool:
        """执行优化动作"""
        logger.info(f"执行优化动作: {action.description}")

        try:
            if action.action_type == "scale_up":
                return await self._scale_up_resource(action)
            elif action.action_type == "scale_down":
                return await self._scale_down_resource(action)
            elif action.action_type == "optimize_config":
                return await self._optimize_resource_config(action)
            elif action.action_type == "restart_service":
                return await self._restart_service(action)
            else:
                logger.warning(f"不支持的优化动作类型: {action.action_type}")
                return False

        except Exception as e:
            logger.error(f"执行优化动作失败: {action.description}, 错误: {e}")
            return False

    async def _scale_up_resource(self, action: OptimizationAction) -> bool:
        """扩容资源"""
        # 实际实现中，这里会调用云服务API进行扩容
        logger.info(f"扩容资源: {action.resource_type.value}")
        await asyncio.sleep(1)  # 模拟API调用延迟
        return True

    async def _scale_down_resource(self, action: OptimizationAction) -> bool:
        """缩容资源"""
        # 实际实现中，这里会调用云服务API进行缩容
        logger.info(f"缩容资源: {action.resource_type.value}")
        await asyncio.sleep(1)  # 模拟API调用延迟
        return True

    async def _optimize_resource_config(self, action: OptimizationAction) -> bool:
        """优化资源配置"""
        # 实际实现中，这里会修改配置文件或调用配置API
        logger.info(f"优化资源配置: {action.resource_type.value}")
        await asyncio.sleep(0.5)  # 模拟配置更新
        return True

    async def _restart_service(self, action: OptimizationAction) -> bool:
        """重启服务"""
        # 实际实现中，这里会重启相关服务
        logger.info(f"重启服务: {action.resource_type.value}")
        await asyncio.sleep(2)  # 模拟服务重启时间
        return True

    async def _cleanup_expired_data(self) -> None:
        """清理过期数据"""
        cutoff_time = datetime.now() - timedelta(
            hours=self.config["metrics_retention_hours"]
        )

        # 清理过期指标
        for key in list(self.metrics_history.keys()):
            metrics = self.metrics_history[key]
            while metrics and metrics[0].timestamp < cutoff_time:
                metrics.popleft()

        # 清理已解决的告警（保留24小时）
        alert_cutoff = datetime.now() - timedelta(hours=24)
        resolved_alerts = [
            alert
            for alert in self.active_alerts.values()
            if alert.resolved and alert.resolved_at and alert.resolved_at < alert_cutoff
        ]

        for alert in resolved_alerts:
            alert_key = f"{alert.resource_type.value}_{alert.metric_name}"
            if (
                alert_key in self.active_alerts
                and self.active_alerts[alert_key].resolved
            ):
                del self.active_alerts[alert_key]

    def get_monitoring_status(self) -> dict:
        """获取监控状态"""
        return {
            "monitoring_active": self.monitoring_active,
            "auto_optimization_enabled": self.auto_optimization_enabled,
            "total_metrics_collected": sum(
                len(metrics) for metrics in self.metrics_history.values()
            ),
            "active_alerts_count": len(self.active_alerts),
            "baseline_established": self.baseline_established,
            "optimization_actions_count": len(self.optimization_actions),
            "last_update": datetime.now().isoformat(),
        }

    def get_resource_summary(self) -> dict:
        """获取资源状态摘要"""
        summary = {
            "resource_types": {},
            "active_alerts": [],
            "performance_baseline": self.baseline_established,
        }

        # 按资源类型汇总指标
        for resource_type in ResourceType:
            type_metrics = []
            for key, metrics in self.metrics_history.items():
                if key.startswith(resource_type.value):
                    if metrics:  # 如果有数据
                        latest_metric = metrics[-1]
                        type_metrics.append(latest_metric)

            if type_metrics:
                summary["resource_types"][resource_type.value] = {
                    "metrics_count": len(type_metrics),
                    "last_update": max(m.timestamp for m in type_metrics).isoformat(),
                    "warning_count": sum(1 for m in type_metrics if m.is_warning),
                    "critical_count": sum(1 for m in type_metrics if m.is_critical),
                    "metrics": [asdict(m) for m in type_metrics[-5:]],  # 最近5个指标
                }

        # 活跃告警
        summary["active_alerts"] = [
            alert.to_dict() for alert in self.active_alerts.values()
        ]

        return summary

    def get_optimization_recommendations(self) -> list[dict]:
        """获取优化建议"""
        recommendations = []

        for alert in self.active_alerts.values():
            if alert.resolved:
                continue

            # 根据告警类型生成建议
            if alert.resource_type == ResourceType.CPU:
                if alert.alert_level == AlertLevel.CRITICAL:
                    recommendations.append(
                        {
                            "resource_type": alert.resource_type.value,
                            "priority": "high",
                            "action": "increase_cpu_resources",
                            "description": "CPU使用率严重过高，建议立即增加CPU资源或优化代码性能",
                            "estimated_impact": "性能提升30-50%",
                        }
                    )
                elif alert.alert_level == AlertLevel.WARNING:
                    recommendations.append(
                        {
                            "resource_type": alert.resource_type.value,
                            "priority": "medium",
                            "action": "optimize_cpu_usage",
                            "description": "CPU使用率较高，建议检查CPU密集型任务并进行优化",
                            "estimated_impact": "性能提升15-25%",
                        }
                    )

            elif alert.resource_type == ResourceType.MEMORY:
                if alert.alert_level == AlertLevel.CRITICAL:
                    recommendations.append(
                        {
                            "resource_type": alert.resource_type.value,
                            "priority": "high",
                            "action": "increase_memory",
                            "description": "内存使用率严重过高，建议增加内存或优化内存使用",
                            "estimated_impact": "稳定性显著提升",
                        }
                    )
                elif alert.alert_level == AlertLevel.WARNING:
                    recommendations.append(
                        {
                            "resource_type": alert.resource_type.value,
                            "priority": "medium",
                            "action": "optimize_memory_usage",
                            "description": "内存使用率较高，建议检查内存泄漏并优化数据结构",
                            "estimated_impact": "稳定性提升20-30%",
                        }
                    )

            elif alert.resource_type == ResourceType.DATABASE_CONNECTIONS:
                recommendations.append(
                    {
                        "resource_type": alert.resource_type.value,
                        "priority": "high",
                        "action": "optimize_database_connections",
                        "description": "数据库连接数过高，建议优化连接池配置或增加数据库实例",
                        "estimated_impact": "响应时间减少20-40%",
                    }
                )

            elif alert.resource_type == ResourceType.CACHE_USAGE:
                if "hit_rate" in alert.metric_name:
                    recommendations.append(
                        {
                            "resource_type": alert.resource_type.value,
                            "priority": "medium",
                            "action": "optimize_cache_strategy",
                            "description": "缓存命中率过低，建议调整缓存策略或增加缓存容量",
                            "estimated_impact": "性能提升15-30%",
                        }
                    )

        # 按优先级排序
        priority_order = {"high": 3, "medium": 2, "low": 1}
        recommendations.sort(
            key=lambda x: priority_order.get(x["priority"], 0), reverse=True
        )

        return recommendations


async def demo_resource_monitor():
    """演示资源监控功能"""
    print("🔍 演示企业级资源监控系统")
    print("=" * 50)

    # 初始化资源监控器
    monitor = ResourceMonitor()

    print("\n📊 收集资源指标...")
    metrics = await monitor._collect_all_metrics()

    print(f"收集到 {len(metrics)} 个指标:")
    for metric in metrics[:10]:  # 显示前10个
        status = "🚨" if metric.is_critical else "⚠️" if metric.is_warning else "✅"
        print(
            f"  {status} {metric.resource_type.value}.{metric.name}: "
            f"{metric.current_value:.2f} {metric.unit}"
        )

    print("\n🚨 检查告警...")
    for metric in metrics:
        await monitor._check_alerts(metric)

    active_alerts = len(monitor.active_alerts)
    print(f"当前活跃告警: {active_alerts}")

    if monitor.active_alerts:
        print("\n告警详情:")
        for alert_key, alert in monitor.active_alerts.items():
            print(f"  [{alert.alert_level.value.upper()}] {alert.message}")

    print("\n💡 生成优化建议...")
    recommendations = monitor.get_optimization_recommendations()

    if recommendations:
        print(f"找到 {len(recommendations)} 条优化建议:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. [{rec['priority'].upper()}] {rec['description']}")
            print(f"     建议: {rec['action']}")
            print(f"     预期影响: {rec['estimated_impact']}")
    else:
        print("暂无优化建议")

    print("\n📈 监控状态:")
    status = monitor.get_monitoring_status()
    print(f"  监控状态: {'运行中' if status['monitoring_active'] else '已停止'}")
    print(f"  自动优化: {'启用' if status['auto_optimization_enabled'] else '禁用'}")
    print(f"  总指标数: {status['total_metrics_collected']}")
    print(f"  活跃告警: {status['active_alerts_count']}")
    print(f"  基线建立: {'是' if status['baseline_established'] else '否'}")

    print("\n🔧 演示自动优化...")
    if monitor.auto_optimization_enabled and monitor.active_alerts:
        await monitor._auto_optimize()
        print("自动优化完成")
    else:
        print("跳过自动优化（无告警或未启用）")

    print("\n✅ 资源监控演示完成")


if __name__ == "__main__":
    asyncio.run(demo_resource_monitor())
