"""
系统容错模块 - 故障检测和恢复系统
实现实时故障检测、自动故障恢复和高可用性保障
"""

import asyncio
import json
import logging
import statistics
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

# from src.core.config_di import get_config  # 暂时注释掉，后续需要时再实现

logger = logging.getLogger(__name__)


class FaultSeverity(Enum):
    """故障严重程度"""

    LOW = "low"  # 低级别故障，影响较小
    MEDIUM = "medium"  # 中等故障，影响部分功能
    HIGH = "high"  # 高级别故障，影响核心功能
    CRITICAL = "critical"  # 严重故障，系统不可用


class FaultType(Enum):
    """故障类型"""

    DATABASE_CONNECTION = "database_connection"  # 数据库连接故障
    CACHE_SERVICE = "cache_service"  # 缓存服务故障
    EXTERNAL_API = "external_api"  # 外部API故障
    MEMORY_PRESSURE = "memory_pressure"  # 内存压力
    CPU_OVERLOAD = "cpu_overload"  # CPU过载
    DISK_SPACE = "disk_space"  # 磁盘空间不足
    NETWORK_PARTITION = "network_partition"  # 网络分区
    SERVICE_UNAVAILABLE = "service_unavailable"  # 服务不可用
    RATE_LIMIT = "rate_limit"  # 频率限制
    TIMEOUT = "timeout"  # 超时


class RecoveryAction(Enum):
    """恢复动作"""

    RETRY = "retry"  # 重试
    CIRCUIT_BREAKER = "circuit_breaker"  # 断路器
    FAILOVER = "failover"  # 故障转移
    DEGRADE = "degrade"  # 服务降级
    RESTART = "restart"  # 服务重启
    SCALE_UP = "scale_up"  # 扩容
    SCALE_DOWN = "scale_down"  # 缩容
    NOTIFY = "notify"  # 告警通知


@dataclass
class FaultEvent:
    """故障事件"""

    fault_id: str
    fault_type: FaultType
    severity: FaultSeverity
    service: str
    description: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_time: datetime | None = None
    resolution_action: RecoveryAction | None = None


@dataclass
class HealthCheck:
    """健康检查配置"""

    name: str
    check_func: Callable
    interval: float = 30.0  # 检查间隔(秒)
    timeout: float = 5.0  # 超时时间(秒)
    failure_threshold: int = 3  # 连续失败阈值
    recovery_threshold: int = 2  # 恢复阈值
    enabled: bool = True


@dataclass
class ServiceHealth:
    """服务健康状态"""

    service_name: str
    status: str  # healthy, degraded, unhealthy, unknown
    last_check: datetime
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_checks: int = 0
    success_rate: float = 0.0
    last_failure: datetime | None = None
    last_recovery: datetime | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


class CircuitBreaker:
    """断路器模式实现"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
        self.half_open_calls = 0

    async def call(self, func: Callable, *args, **kwargs):
        """通过断路器调用函数"""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half_open"
                self.half_open_calls = 0
            else:
                raise Exception("Circuit breaker is open")

        if self.state == "half_open":
            if self.half_open_calls >= self.half_open_max_calls:
                raise Exception("Circuit breaker half-open limit exceeded")

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            self._on_success()
            return result

        except Exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置断路器"""
        return (
            self.last_failure_time
            and (datetime.now() - self.last_failure_time).total_seconds()
            > self.recovery_timeout
        )

    def _on_success(self):
        """成功时调用"""
        if self.state == "half_open":
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self._reset()
        else:
            self.failure_count = 0

    def _on_failure(self):
        """失败时调用"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"

    def _reset(self):
        """重置断路器"""
        self.failure_count = 0
        self.state = "closed"
        self.half_open_calls = 0
        self.last_failure_time = None


class RetryPolicy:
    """重试策略"""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    async def execute_with_retry(self, func: Callable, *args, **kwargs):
        """带重试执行函数"""
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            except Exception as e:
                last_exception = e
                if attempt == self.max_attempts - 1:
                    break

                delay = self._calculate_delay(attempt)
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}"
                )
                await asyncio.sleep(delay)

        raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        delay = self.base_delay * (self.exponential_base**attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            import random

            delay *= 0.5 + random.random() * 0.5

        return delay


class FaultDetector:
    """故障检测器"""

    def __init__(self):
        self.health_checks: dict[str, HealthCheck] = {}
        self.service_health: dict[str, ServiceHealth] = {}
        self.circuit_breakers: dict[str, CircuitBreaker] = {}
        self.fault_events: deque[FaultEvent] = deque(maxlen=1000)
        self.metrics = defaultdict(list)
        self.recovery_actions: dict[FaultType, list[RecoveryAction]] = {
            FaultType.DATABASE_CONNECTION: [
                RecoveryAction.RETRY,
                RecoveryAction.FAILOVER,
            ],
            FaultType.CACHE_SERVICE: [RecoveryAction.DEGRADE, RecoveryAction.RESTART],
            FaultType.EXTERNAL_API: [
                RecoveryAction.RETRY,
                RecoveryAction.CIRCUIT_BREAKER,
            ],
            FaultType.MEMORY_PRESSURE: [RecoveryAction.SCALE_UP, RecoveryAction.NOTIFY],
            FaultType.CPU_OVERLOAD: [RecoveryAction.SCALE_UP, RecoveryAction.DEGRADE],
            FaultType.SERVICE_UNAVAILABLE: [
                RecoveryAction.FAILOVER,
                RecoveryAction.NOTIFY,
            ],
        }

        # 后台监控任务将在需要时启动
        self._monitoring_started = False

    def register_health_check(self, health_check: HealthCheck):
        """注册健康检查"""
        self.health_checks[health_check.name] = health_check
        self.service_health[health_check.name] = ServiceHealth(
            service_name=health_check.name, status="unknown", last_check=datetime.now()
        )
        logger.info(f"Registered health check: {health_check.name}")

    def register_circuit_breaker(self, service: str, **kwargs):
        """注册断路器"""
        self.circuit_breakers[service] = CircuitBreaker(**kwargs)
        logger.info(f"Registered circuit breaker for service: {service}")

    async def check_service_health(self, service_name: str) -> ServiceHealth:
        """检查服务健康状态"""
        if service_name not in self.health_checks:
            return ServiceHealth(
                service_name=service_name, status="unknown", last_check=datetime.now()
            )

        health_check = self.health_checks[service_name]
        service_health = self.service_health[service_name]

        if not health_check.enabled:
            service_health.status = "disabled"
            return service_health

        try:
            # 执行健康检查
            if asyncio.iscoroutinefunction(health_check.check_func):
                is_healthy = await asyncio.wait_for(
                    health_check.check_func(), timeout=health_check.timeout
                )
            else:
                is_healthy = health_check.check_func()

            service_health.total_checks += 1

            if is_healthy:
                service_health.consecutive_successes += 1
                service_health.consecutive_failures = 0
                service_health.status = "healthy"
                service_health.last_recovery = datetime.now()
            else:
                service_health.consecutive_failures += 1
                service_health.consecutive_successes = 0

                if (
                    service_health.consecutive_failures
                    >= health_check.failure_threshold
                ):
                    service_health.status = "unhealthy"
                    await self._handle_service_failure(service_name)

            # 计算成功率
            service_health.success_rate = (
                service_health.consecutive_successes
                / max(1, service_health.total_checks)
            ) * 100

        except TimeoutError:
            service_health.consecutive_failures += 1
            service_health.consecutive_successes = 0
            service_health.status = "unhealthy"
            service_health.last_failure = datetime.now()

            if service_health.consecutive_failures >= health_check.failure_threshold:
                await self._handle_service_failure(service_name)

        except Exception as e:
            logger.error(f"Health check error for {service_name}: {e}")
            service_health.consecutive_failures += 1
            service_health.status = "degraded"

        service_health.last_check = datetime.now()
        return service_health

    async def _handle_service_failure(self, service_name: str):
        """处理服务故障"""
        logger.error(f"Service failure detected: {service_name}")

        # 创建故障事件
        fault_event = FaultEvent(
            fault_id=f"fault_{service_name}_{int(time.time())}",
            fault_type=FaultType.SERVICE_UNAVAILABLE,
            severity=FaultSeverity.HIGH,
            service=service_name,
            description=f"Service {service_name} is unhealthy",
            timestamp=datetime.now(),
        )

        self.fault_events.append(fault_event)

        # 执行恢复动作
        await self._execute_recovery_actions(fault_event)

    async def _execute_recovery_actions(self, fault_event: FaultEvent):
        """执行恢复动作"""
        actions = self.recovery_actions.get(fault_event.fault_type, [])

        for action in actions:
            try:
                await self._execute_action(action, fault_event)
                logger.info(
                    f"Executed recovery action {action.value} for {fault_event.service}"
                )
            except Exception as e:
                logger.error(f"Failed to execute recovery action {action.value}: {e}")

    async def _execute_action(self, action: RecoveryAction, fault_event: FaultEvent):
        """执行具体恢复动作"""
        if action == RecoveryAction.RETRY:
            logger.info(f"Initiating retry for {fault_event.service}")

        elif action == RecoveryAction.NOTIFY:
            await self._send_alert(fault_event)

        elif action == RecoveryAction.FAILOVER:
            logger.info(f"Initiating failover for {fault_event.service}")

        elif action == RecoveryAction.DEGRADE:
            logger.info(f"Degrading service {fault_event.service}")

        elif action == RecoveryAction.SCALE_UP:
            logger.info(f"Scaling up service {fault_event.service}")

    async def _send_alert(self, fault_event: FaultEvent):
        """发送告警通知"""
        alert_data = {
            "fault_id": fault_event.fault_id,
            "service": fault_event.service,
            "severity": fault_event.severity.value,
            "type": fault_event.fault_type.value,
            "description": fault_event.description,
            "timestamp": fault_event.timestamp.isoformat(),
        }

        logger.warning(f"ALERT: {json.dumps(alert_data, indent=2)}")
        # 这里可以集成实际的告警系统

    def get_service_health_summary(self) -> dict[str, Any]:
        """获取服务健康状态摘要"""
        summary = {
            "total_services": len(self.service_health),
            "healthy": 0,
            "degraded": 0,
            "unhealthy": 0,
            "unknown": 0,
            "services": {},
        }

        for service_name, health in self.service_health.items():
            status = health.status
            summary["services"][service_name] = {
                "status": status,
                "last_check": health.last_check.isoformat(),
                "success_rate": health.success_rate,
                "consecutive_failures": health.consecutive_failures,
            }
            summary[status] += 1

        return summary

    def get_recent_faults(self, hours: int = 24) -> list[FaultEvent]:
        """获取最近的故障事件"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [event for event in self.fault_events if event.timestamp > cutoff_time]

    async def call_with_resilience(
        self,
        service: str,
        func: Callable,
        retry_policy: RetryPolicy | None = None,
        *args,
        **kwargs,
    ):
        """带容错机制调用服务"""
        retry_policy = retry_policy or RetryPolicy()

        # 检查断路器状态
        if service in self.circuit_breakers:
            return await self.circuit_breakers[service].call(
                retry_policy.execute_with_retry, func, *args, **kwargs
            )
        else:
            return await retry_policy.execute_with_retry(func, *args, **kwargs)

    def _start_monitoring_tasks(self):
        """启动后台监控任务"""
        if not self._monitoring_started:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._health_check_loop())
                loop.create_task(self._metrics_collection_loop())
                self._monitoring_started = True
            except RuntimeError:
                # 没有运行中的事件循环，跳过后台任务
                logger.debug("No event loop running, skipping background tasks")

    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(30)  # 每30秒检查一次

                for health_check in self.health_checks.values():
                    if health_check.enabled:
                        await self.check_service_health(health_check.name)

            except Exception as e:
                logger.error(f"Health check loop error: {e}")

    async def _metrics_collection_loop(self):
        """指标收集循环"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟收集一次指标

                # 收集系统指标
                self._collect_system_metrics()
                self._collect_service_metrics()

            except Exception as e:
                logger.error(f"Metrics collection loop error: {e}")

    def _collect_system_metrics(self):
        """收集系统指标"""
        # 内存使用情况
        try:
            import psutil

            memory = psutil.virtual_memory()
            self.metrics["memory_usage"].append(
                {
                    "timestamp": datetime.now(),
                    "percent": memory.percent,
                    "available_gb": memory.available / (1024**3),
                }
            )

            # CPU使用情况
            cpu = psutil.cpu_percent(interval=1)
            self.metrics["cpu_usage"].append(
                {"timestamp": datetime.now(), "percent": cpu}
            )

            # 磁盘使用情况
            disk = psutil.disk_usage("/")
            self.metrics["disk_usage"].append(
                {
                    "timestamp": datetime.now(),
                    "percent": (disk.used / disk.total) * 100,
                    "free_gb": disk.free / (1024**3),
                }
            )

            # 保持最近100个数据点
            for metric_type in self.metrics:
                if len(self.metrics[metric_type]) > 100:
                    self.metrics[metric_type] = self.metrics[metric_type][-100:]

        except ImportError:
            logger.warning("psutil not available for system metrics")
        except Exception as e:
            logger.error(f"System metrics collection error: {e}")

    def _collect_service_metrics(self):
        """收集服务指标"""
        for service_name, health in self.service_health.items():
            self.metrics[f"service_{service_name}"].append(
                {
                    "timestamp": datetime.now(),
                    "status": health.status,
                    "success_rate": health.success_rate,
                }
            )

    async def add_metric(
        self, metric_name: str, value: float, tags: dict[str, Any] = None
    ):
        """添加指标数据 - 兼容AlertManager接口"""
        self.metrics[metric_name].append(
            {"value": value, "timestamp": datetime.now(), "tags": tags or {}}
        )

    def get_metrics_summary(self) -> dict[str, Any]:
        """获取指标摘要"""
        summary = {}

        for metric_type, data_points in self.metrics.items():
            if not data_points:
                continue

            latest = data_points[-1]
            if "percent" in latest:
                summary[metric_type] = {
                    "current": latest["percent"],
                    "avg": statistics.mean(dp["percent"] for dp in data_points),
                    "max": max(dp["percent"] for dp in data_points),
                    "min": min(dp["percent"] for dp in data_points),
                }

        return summary


# 全局故障检测器实例
_fault_detector: FaultDetector | None = None


def get_fault_detector() -> FaultDetector:
    """获取全局故障检测器实例"""
    global _fault_detector
    if _fault_detector is None:
        _fault_detector = FaultDetector()
    return _fault_detector


def initialize_fault_detector() -> FaultDetector:
    """初始化全局故障检测器"""
    global _fault_detector
    _fault_detector = FaultDetector()
    return _fault_detector
