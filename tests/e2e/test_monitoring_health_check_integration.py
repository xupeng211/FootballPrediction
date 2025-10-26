"""
Phase 4A Week 3 - 监控和健康检查集成测试

Monitoring and Health Check Integration Test Suite

这个测试文件提供监控和健康检查的集成测试，包括：
- 健康检查端点测试
- 监控指标收集测试
- 日志聚合和分析测试
- 告警机制测试
- 系统性能监控测试
- 分布式追踪测试

测试覆盖率目标：>=95%
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from unittest.mock import Mock, AsyncMock, patch
import uuid

# 导入Phase 4A Mock工厂
try:
    from tests.unit.mocks.mock_factory_phase4a import Phase4AMockFactory
except ImportError:
    class Phase4AMockFactory:
        @staticmethod
        def create_mock_monitoring_service():
            return Mock()

        @staticmethod
        def create_mock_health_checker():
            return Mock()


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    service_id: str
    status: HealthStatus
    response_time: float
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class MetricPoint:
    """指标点"""
    name: str
    value: Union[int, float]
    metric_type: MetricType
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None


@dataclass
class Alert:
    """告警"""
    id: str
    level: AlertLevel
    title: str
    message: str
    service_id: str
    metric_name: Optional[str] = None
    threshold: Optional[Union[int, float]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class LogEntry:
    """日志条目"""
    id: str
    timestamp: datetime
    level: str
    service: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None


class MockMetricsCollector:
    """Mock指标收集器"""

    def __init__(self):
        self.metrics: Dict[str, List[MetricPoint]] = {}
        self.alerts: List[Alert] = []
        self.alert_rules: Dict[str, Dict[str, Any]] = {}

    def add_metric(self, name: str, value: Union[int, float], metric_type: MetricType = MetricType.GAUGE, tags: Dict[str, str] = None, unit: str = None):
        """添加指标点"""
        if name not in self.metrics:
            self.metrics[name] = []

        metric_point = MetricPoint(
            name=name,
            value=value,
            metric_type=metric_type,
            timestamp=datetime.now(),
            tags=tags or {},
            unit=unit
        )
        self.metrics[name].append(metric_point)

    def get_metric(self, name: str, last_n: int = 1) -> List[MetricPoint]:
        """获取指标"""
        if name not in self.metrics:
            return []
        return self.metrics[name][-last_n:]

    def set_alert_rule(self, metric_name: str, condition: str, threshold: Union[int, float], level: AlertLevel):
        """设置告警规则"""
        self.alert_rules[metric_name] = {
            "condition": condition,
            "threshold": threshold,
            "level": level
        }

    def check_alerts(self, service_id: str = None):
        """检查告警条件"""
        new_alerts = []

        for metric_name, points in self.metrics.items():
            if not points:
                continue

            if metric_name in self.alert_rules:
                rule = self.alert_rules[metric_name]
                latest_point = points[-1]
                threshold = rule["threshold"]
                condition = rule["condition"]

                if condition == "greater_than" and latest_point.value > threshold:
                    alert = Alert(
                        id=str(uuid.uuid4()),
                        level=rule["level"],
                        title=f"{metric_name} exceeds threshold",
                        message=f"{metric_name} value {latest_point.value} > threshold {threshold}",
                        service_id=service_id or "unknown",
                        metric_name=metric_name,
                        threshold=threshold
                    )
                    new_alerts.append(alert)

                elif condition == "less_than" and latest_point.value < threshold:
                    alert = Alert(
                        id=str(uuid.uuid4()),
                        level=rule["level"],
                        title=f"{metric_name} below threshold",
                        message=f"{metric_name} value {latest_point.value} < threshold {threshold}",
                        service_id=service_id or "unknown",
                        metric_name=metric_name,
                        threshold=threshold
                    )
                    new_alerts.append(alert)

        self.alerts.extend(new_alerts)
        return new_alerts


class MockLogAggregator:
    """Mock日志聚合器"""

    def __init__(self):
        self.logs: List[LogEntry] = []
        self.indexed_logs: Dict[str, List[LogEntry]] = {}  # 按服务索引
        self.trace_logs: Dict[str, List[LogEntry]] = {}  # 按追踪ID索引

    def add_log(self, level: str, service: str, message: str, metadata: Dict[str, Any] = None, trace_id: str = None):
        """添加日志"""
        log_entry = LogEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            level=level,
            service=service,
            message=message,
            metadata=metadata or {},
            trace_id=trace_id
        )

        self.logs.append(log_entry)

        # 按服务索引
        if service not in self.indexed_logs:
            self.indexed_logs[service] = []
        self.indexed_logs[service].append(log_entry)

        # 按追踪ID索引
        if trace_id:
            if trace_id not in self.trace_logs:
                self.trace_logs[trace_id] = []
            self.trace_logs[trace_id].append(log_entry)

    def get_logs_by_service(self, service: str, last_n: int = 100) -> List[LogEntry]:
        """根据服务获取日志"""
        if service not in self.indexed_logs:
            return []
        return self.indexed_logs[service][-last_n:]

    def get_logs_by_level(self, level: str, last_n: int = 100) -> List[LogEntry]:
        """根据级别获取日志"""
        filtered_logs = [log for log in self.logs if log.level == level]
        return filtered_logs[-last_n:]

    def get_trace_logs(self, trace_id: str) -> List[LogEntry]:
        """根据追踪ID获取日志"""
        return self.trace_logs.get(trace_id, [])

    def get_error_logs(self, last_n: int = 50) -> List[LogEntry]:
        """获取错误日志"""
        return self.get_logs_by_level("ERROR", last_n)

    def get_warning_logs(self, last_n: int = 50) -> List[LogEntry]:
        """获取警告日志"""
        return self.get_logs_by_level("WARNING", last_n)


class MockHealthChecker:
    """Mock健康检查器"""

    def __init__(self):
        self.check_history: List[HealthCheckResult] = []
        self.service_configs: Dict[str, Dict[str, Any]] = {}

    def configure_service(self, service_id: str, config: Dict[str, Any]):
        """配置服务健康检查"""
        self.service_configs[service_id] = config

    async def check_service_health(self, service_id: str) -> HealthCheckResult:
        """检查单个服务健康状态"""
        if service_id not in self.service_configs:
            return HealthCheckResult(
                service_id=service_id,
                status=HealthStatus.UNKNOWN,
                response_time=0.0,
                timestamp=datetime.now(),
                error="Service not configured"
            )

        config = self.service_configs[service_id]
        start_time = time.time()

        # 模拟健康检查逻辑
        await asyncio.sleep(config.get("check_delay", 0.01))

        # 模拟不同的健康状态
        if config.get("always_fail"):
            status = HealthStatus.UNHEALTHY
            error = "Service intentionally failing for testing"
        elif config.get("always_degraded"):
            status = HealthStatus.DEGRADED
            details = {"reason": "High latency", "response_time": config.get("response_time", 0.5)}
        else:
            status = HealthStatus.HEALTHY
            error = None
            details = {"response_time": config.get("response_time", 0.01)}

        response_time = time.time() - start_time

        result = HealthCheckResult(
            service_id=service_id,
            status=status,
            response_time=response_time,
            timestamp=datetime.now(),
            details=details,
            error=error
        )

        self.check_history.append(result)
        return result

    async def check_all_services(self) -> List[HealthCheckResult]:
        """检查所有服务健康状态"""
        tasks = []
        for service_id in self.service_configs.keys():
            tasks.append(self.check_service_health(service_id))

        return await asyncio.gather(*tasks)

    def get_service_health_history(self, service_id: str, last_n: int = 10) -> List[HealthCheckResult]:
        """获取服务健康检查历史"""
        return [
            check for check in self.check_history
            if check.service_id == service_id
        ][-last_n]


class MockDistributedTracer:
    """Mock分布式追踪器"""

    def __init__(self):
        self.traces: Dict[str, Dict[str, Any]] = {}

    def start_trace(self, operation_name: str, service: str, metadata: Dict[str, Any] = None) -> str:
        """开始追踪"""
        trace_id = str(uuid.uuid4())
        self.traces[trace_id] = {
            "operation_name": operation_name,
            "service": service,
            "start_time": datetime.now(),
            "spans": [],
            "metadata": metadata or {}
        }
        return trace_id

    def end_trace(self, trace_id: str, status: str = "success", error: str = None):
        """结束追踪"""
        if trace_id not in self.traces:
            return None

        self.traces[trace_id]["end_time"] = datetime.now()
        self.traces[trace_id]["status"] = status
        if error:
            self.traces[trace_id]["error"] = error

        return self.traces[trace_id]

    def add_span(self, trace_id: str, span_name: str, start_time: float = None, end_time: float = None):
        """添加span"""
        if trace_id not in self.traces:
            return None

        span = {
            "span_name": span_name,
            "start_time": start_time or time.time()
        }

        if end_time is not None:
            span["end_time"] = end_time
            span["duration"] = end_time - span["start_time"]

        self.traces[trace_id]["spans"].append(span)

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """获取追踪信息"""
        return self.traces.get(trace_id)


class TestMonitoringAndHealthCheckIntegration:
    """监控和健康检查集成测试"""

    @pytest.fixture
    def metrics_collector(self):
        """指标收集器"""
        return MockMetricsCollector()

    @pytest.fixture
    def log_aggregator(self):
        """日志聚合器"""
        return MockLogAggregator()

    @pytest.fixture
    def health_checker(self):
        """健康检查器"""
        return MockHealthChecker()

    @pytest.fixture
    def distributed_tracer(self):
        """分布式追踪器"""
        return MockDistributedTracer()

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_health_check_endpoints(self, health_checker):
        """测试健康检查端点"""
        print("🧪 测试健康检查端点")

        # 配置服务
        services = [
            {
                "service_id": "user_service",
                "check_delay": 0.01,
                "response_time": 0.02
            },
            {
                "service_id": "prediction_service",
                "check_delay": 0.015,
                "response_time": 0.03
            },
            {
                "service_id": "failing_service",
                "always_fail": True,
                "check_delay": 0.005
            }
        ]

        for service in services:
            health_checker.configure_service(service["service_id"], service)

        # 检查单个服务
        user_result = await health_checker.check_service_health("user_service")
        prediction_result = await health_checker.check_service_health("prediction_service")
        failing_result = await health_checker.check_service_health("failing_service")

        # 验证健康服务结果
        assert user_result.status == HealthStatus.HEALTHY
        assert user_result.response_time < 0.1
        assert "response_time" in user_result.details

        assert prediction_result.status == HealthStatus.HEALTHY
        assert prediction_result.response_time < 0.1
        assert "response_time" in prediction_result.details

        # 验证失败服务结果
        assert failing_result.status == HealthStatus.UNHEALTHY
        assert failing_result.error is not None
        assert failing_result.error == "Service intentionally failing for testing"

        print("✅ 单个服务健康检查通过")

        # 检查所有服务
        all_results = await health_checker.check_all_services()
        assert len(all_results) == len(services)

        healthy_count = sum(1 for result in all_results if result.status == HealthStatus.HEALTHY)
        assert healthy_count == 2  # user_service + prediction_service

        print(f"✅ 所有服务健康检查通过 (健康服务: {healthy_count}/{len(services)})")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_metrics_collection_and_alerting(self, metrics_collector):
        """测试指标收集和告警"""
        print("🧪 测试指标收集和告警")

        # 配置告警规则
        metrics_collector.set_alert_rule("cpu_usage", "greater_than", 80, AlertLevel.WARNING)
        metrics_collector.set_alert_rule("memory_usage", "greater_than", 90, AlertLevel.ERROR)
        metrics_collector.set_alert_rule("error_rate", "greater_than", 0.05, AlertLevel.CRITICAL)

        # 添加正常指标
        metrics_collector.add_metric("cpu_usage", 45.5, MetricType.GAUGE, unit="%")
        metrics_collector.add_metric("memory_usage", 65.2, MetricType.GAUGE, unit="%")
        metrics_collector.add_metric("request_count", 1000, MetricType.COUNTER)
        metrics_collector.add_metric("response_time", 0.045, MetricType.TIMER, unit="s")

        # 添加触发告警的指标
        metrics_collector.add_metric("cpu_usage", 85.0, MetricType.GAUGE, unit="%")
        metrics_collector.add_metric("memory_usage", 95.0, MetricType.GAUGE, unit="%")

        # 检查告警
        alerts = metrics_collector.check_alerts()

        # 验证告警数量
        assert len(alerts) == 2  # cpu_usage 和 memory_usage 触发告警
        cpu_alerts = [alert for alert in alerts if alert.metric_name == "cpu_usage"]
        memory_alerts = [alert for alert in alerts if alert.metric_name == "memory_usage"]

        assert len(cpu_alerts) == 1
        assert cpu_alerts[0].level == AlertLevel.WARNING
        assert "exceeds threshold" in cpu_alerts[0].title
        assert cpu_alerts[0].threshold == 80

        assert len(memory_alerts) == 1
        assert memory_alerts[0].level == AlertLevel.ERROR
        assert "below threshold" in memory_alerts[0].title
        assert memory_alerts[0].threshold == 90

        # 验证指标存储
        cpu_metrics = metrics_collector.get_metric("cpu_usage", 2)
        memory_metrics = metrics_collector.get_metric("memory_usage", 2)

        assert len(cpu_metrics) == 2
        assert cpu_metrics[-1].value == 85.0
        assert cpu_metrics[-1].unit == "%"

        assert len(memory_metrics) == 2
        assert memory_metrics[-1].value == 95.0
        assert memory_metrics[-1].unit == "%"

        print(f"✅ 指标收集和告警测试通过 ({len(alerts)} 个告警)")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_log_aggregation_and_analysis(self, log_aggregator):
        """测试日志聚合和分析"""
        print("🧪 测试日志聚合和分析")

        trace_id = str(uuid.uuid4())

        # 添加不同级别的日志
        logs_to_add = [
            ("INFO", "user_service", "User login successful", {"user_id": "user_123"}, trace_id),
            ("WARNING", "prediction_service", "High prediction confidence threshold reached", {"confidence": 0.9}, trace_id),
            ("ERROR", "database_service", "Database connection failed", {"retry_count": 3}, trace_id),
            ("INFO", "user_service", "Prediction created successfully", {"prediction_id": "pred_456"}, trace_id),
            ("CRITICAL", "notification_service", "Notification service down", {"error": "connection_timeout"}, trace_id),
        ]

        for level, service, message, metadata, trace in logs_to_add:
            log_aggregator.add_log(level, service, message, metadata, trace)

        # 验证日志总数
        assert len(log_aggregator.logs) == len(logs_to_add)

        # 验证按服务索引
        user_service_logs = log_aggregator.get_logs_by_service("user_service")
        assert len(user_service_logs) == 2

        prediction_service_logs = log_aggregator.get_logs_by_service("prediction_service")
        assert len(prediction_service_logs) == 1

        database_service_logs = log_aggregator.get_logs_by_service("database_service")
        assert len(database_service_logs) == 1

        # 验证按级别索引
        error_logs = log_aggregator.get_error_logs()
        assert len(error_logs) == 2  # ERROR + CRITICAL

        warning_logs = log_aggregator.get_warning_logs()
        assert len(warning_logs) == 1

        # 验证追踪日志
        trace_logs = log_aggregator.get_trace_logs(trace_id)
        assert len(trace_logs) == 4

        # 验证追踪日志内容
        trace_messages = [log.message for log in trace_logs]
        assert "User login successful" in trace_messages
        assert "Database connection failed" in trace_messages
        assert "Prediction created successfully" in trace_messages
        assert "Notification service down" in trace_messages

        print(f"✅ 日志聚合和分析测试通过 ({len(log_aggregator.logs)} 条日志)")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_distributed_tracing(self, distributed_tracer):
        """测试分布式追踪"""
        print("🧪 测试分布式追踪")

        # 开始追踪
        trace_id = distributed_tracer.start_trace(
            "user_prediction",
            "user_service",
            {"user_id": "user_123", "request_id": "req_789"}
        )

        # 添加多个span
        spans = [
            ("validate_user", time.time()),
            ("fetch_predictions", time.time()),
            ("create_prediction", time.time())
        ]

        for span_name, start_time in spans:
            distributed_tracer.add_span(trace_id, span_name, start_time)

        # 结束span
        time.sleep(0.01)
        distributed_tracer.add_span(trace_id, "validate_user", time.time())
        distributed_tracer.add_span(trace_id, "fetch_predictions", time.time())

        time.sleep(0.02)
        distributed_tracer.add_span(trace_id, "create_prediction", time.time())

        # 结束追踪
        trace = distributed_tracer.end_trace(trace_id)

        # 验证追踪信息
        assert trace is not None
        assert trace["operation_name"] == "user_prediction"
        assert trace["service"] == "user_service"
        assert trace["status"] == "success"
        assert "start_time" in trace
        assert "end_time" in trace
        assert "user_id" in trace["metadata"]

        # 验证spans
        assert len(trace["spans"]) == 3
        span_names = [span["span_name"] for span in trace["spans"]]
        assert "validate_user" in span_names
        assert "fetch_predictions" in span_names
        assert "create_prediction" in span_names

        # 验证span持续时间
        for span in trace["spans"]:
            assert "duration" in span
            assert span["duration"] >= 0

        print("✅ 分布式追踪测试通过")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_system_performance_monitoring(self, metrics_collector):
        """测试系统性能监控"""
        print("🧪 测试系统性能监控")

        # 模拟实时性能数据收集
        performance_data = [
            {"timestamp": datetime.now() - timedelta(seconds=300), "cpu": 45.2, "memory": 60.5, "disk_io": 25.1},
            {"timestamp": datetime.now() - timedelta(seconds=240), "cpu": 48.5, "memory": 62.1, "disk_io": 23.8},
            {"timestamp": datetime.now() - timedelta(seconds=180), "cpu": 52.1, "memory": 65.8, "disk_io": 28.9},
            {"timestamp": datetime.now() - timedelta(seconds=120), "cpu": 58.7, "memory": 68.2, "disk_io": 31.5},
            {"timestamp": datetime.now() - timedelta(seconds=60), "cpu": 62.3, "memory": 71.5, "disk_io": 35.2},
        ]

        # 添加性能指标
        for data in performance_data:
            metrics_collector.add_metric("cpu_usage", data["cpu"], MetricType.GAUGE, tags={"host": "server1"})
            metrics_collector.add_metric("memory_usage", data["memory"], MetricType.GAUGE, tags={"host": "server1"})
            metrics_collector.add_metric("disk_io", data["disk_io"], MetricType.GAUGE, tags={"host": "server1"})

        # 模拟响应时间指标
        response_times = [0.023, 0.045, 0.012, 0.067, 0.034, 0.089, 0.018, 0.025, 0.041]
        for rt in response_times:
            metrics_collector.add_metric("response_time", rt, MetricType.HISTOGRAM, tags={"endpoint": "/api/v1/predictions"})

        # 分析性能趋势
        cpu_metrics = metrics_collector.get_metric("cpu_usage")
        memory_metrics = metrics_collector.get_metric("memory_usage")
        response_time_metrics = metrics_collector.get_metric("response_time")

        # 计算性能统计
        avg_cpu = sum(point.value for point in cpu_metrics[-5:]) / len(cpu_metrics[-5:])
        max_cpu = max(point.value for point in cpu_metrics[-5:])
        avg_memory = sum(point.value for point in memory_metrics[-5:]) / len(memory_metrics[-5:])
        max_memory = max(point.value for point in memory_metrics[-5:])

        avg_response_time = sum(point.value for point in response_time[-10:]) / len(response_time[-10:])
        p95_response_time = sorted(response_time[-10:])[int(len(response_time[-10:]) * 0.95)]  # 95th percentile

        # 性能断言
        assert avg_cpu < 70, f"Average CPU usage too high: {avg_cpu}%"
        assert max_cpu < 80, f"Maximum CPU usage too high: {max_cpu}%"
        assert avg_memory < 75, f"Average memory usage too high: {avg_memory}%"
        assert max_memory < 85, f"Maximum memory usage too high: {max_memory}%"

        assert avg_response_time < 0.1, f"Average response time too high: {avg_response_time}s"
        assert p95_response_time < 0.15, f"P95 response time too high: {p95_response_time}s"

        print("📊 系统性能监控结果:")
        print(f"   CPU使用率: 平均 {avg_cpu:.1f}%, 最大 {max_cpu:.1f}%")
        print(f"   内存使用率: 平均 {avg_memory:.1f}%, 最大 {max_memory:.1f}%")
        print(f"   响应时间: 平均 {avg_response_time:.3f}s, P95 {p95_response_time:.3f}s")

        print("✅ 系统性能监控测试通过")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_monitoring_dashboard_integration(self, metrics_collector, log_aggregator, health_checker):
        """测试监控仪表板集成"""
        print("🧪 测试监控仪表板集成")

        # 配置健康检查
        health_checker.configure_service("user_service", {"check_delay": 0.01})
        health_checker.configure_service("prediction_service", {"check_delay": 0.015})

        # 执行健康检查
        health_results = await health_checker.check_all_services()
        healthy_count = sum(1 for result in health_results if result.status == HealthStatus.HEALTHY)
        total_count = len(health_results)

        # 生成监控数据
        health_status = {
            "healthy_services": healthy_count,
            "total_services": total_count,
            "overall_status": "healthy" if healthy_count == total_count else "degraded",
            "last_check": datetime.now().isoformat()
        }

        # 生成性能指标
        for _ in range(10):
            metrics_collector.add_metric("requests_per_second", 150 + _ * 10, MetricType.GAUGE)
            metrics_collector.add_metric("error_rate", 0.01 + _ * 0.005, MetricType.GAUGE)

        performance_metrics = {
            "requests_per_second": {
                "current": 240,  # 最后一个值
                "average": 195,  # 平均值
                "trend": "increasing"
            },
            "error_rate": {
                "current": 0.055,
                "average": 0.0375,
                "trend": "increasing"
            }
        }

        # 模拟日志数据
        for i in range(5):
            log_aggregator.add_log("INFO", "system", f"Monitoring data collected batch {i+1}")
        error_count = 2
        for i in range(error_count):
            log_aggregator.add_log("ERROR", "system", f"Service {i+1} temporarily unavailable")

        log_metrics = {
            "total_logs": log_aggregator.get_logs_count(),
            "error_count": error_count,
            "last_error": datetime.now().isoformat()
        }

        # 组装仪表板数据
        dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "health_status": health_status,
            "performance_metrics": performance_metrics,
            "log_metrics": log_metrics,
            "alerts": []
        }

        # 验证仪表板数据结构
        assert "health_status" in dashboard_data
        assert "performance_metrics" in dashboard_data
        assert "log_metrics" in dashboard_data
        assert "timestamp" in dashboard_data

        assert dashboard_data["health_status"]["healthy_services"] == total_count
        assert dashboard_data["health_status"]["overall_status"] == "healthy"
        assert dashboard_data["performance_metrics"]["requests_per_second"]["current"] == 240
        assert dashboard_data["log_metrics"]["total_logs"] == 7
        assert dashboard_data["log_metrics"]["error_count"] == 2

        print("✅ 监控仪表板集成测试通过")
        print(f"   健康服务: {dashboard_data['health_status']['healthy_services']}/{dashboard_data['health_status']['total_services']}")
        print(f"   当前QPS: {dashboard_data['performance_metrics']['requests_per_second']['current']}")
        print(f"   错误率: {dashboard_data['performance_metrics']['error_rate']['current']:.1%}")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_alert_management(self, metrics_collector):
        """测试告警管理"""
        print("🧪 测试告警管理")

        # 配置告警规则
        metrics_collector.set_alert_rule("high_error_rate", "greater_than", 0.1, AlertLevel.ERROR)
        metrics_collector.set_alert_rule("service_down", "equals", 1, AlertLevel.CRITICAL)

        # 添加正常指标
        for i in range(10):
            metrics_collector.add_metric("error_rate", 0.05, MetricType.GAUGE)
            metrics_collector.add_metric("service_availability", 1, MetricType.GAUGE)

        # 触发高错误率告警
        metrics_collector.add_metric("error_rate", 0.12, MetricType.GAUGE)
        alerts = metrics_collector.check_alerts("test_service")

        # 验证高错误率告警
        assert len(alerts) == 1
        error_alert = alerts[0]
        assert error_alert.level == AlertLevel.ERROR
        assert error_alert.metric_name == "high_error_rate"
        assert error_alert.threshold == 0.1

        # 触发服务宕机告警
        metrics_collector.add_metric("service_availability", 0, MetricType.GAUGE)
        service_down_alerts = metrics_collector.check_alerts("test_service")

        assert len(service_down_alerts) == 1
        down_alert = service_down_alerts[0]
        assert down_alert.level == AlertLevel.CRITICAL
        assert down_alert.metric_name == "service_down"
        assert down_alert.threshold == 1

        # 验证告警属性
        for alert in alerts:
            assert alert.id is not None
            assert alert.title is not None
            assert alert.message is not None
            assert alert.service_id == "test_service"
            assert alert.resolved is False
            assert alert.resolved_at is None

        print(f"✅ 告警管理测试通过 ({len(alerts)} 个告警)")
        print(f"   告警级别: {[alert.level.value for alert in alerts]}")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_monitoring_system_resilience(self, health_checker, metrics_collector):
        """测试监控系统弹性"""
        print("🧪 测试监控系统弹性")

        # 配置弹性健康检查
        health_checker.configure_service("resilient_service", {
            "check_delay": 0.01,
            "response_time": 0.02
        })

        health_checker.configure_service("flaky_service", {
            "check_delay": 0.005,
            "always_degraded": True,
            "response_time": 0.5
        })

        # 模拟系统压力下的健康检查
        stress_test_results = []

        for i in range(20):  # 模拟20次健康检查
            results = await health_checker.check_all_services()
            stress_test_results.append(results)

            # 添加性能指标
            resilient_healthy = any(r.status == HealthStatus.HEALTHY for r in results if r.service_id == "resilient_service")
            flaky_status = any(r.status == HealthStatus.DEGRADED for r in results if r.service_id == "flaky_service")

            metrics_collector.add_metric("resilient_service_healthy", 1 if resilient_healthy else 0, MetricType.GAUGE)
            metrics_collector.add_metric("flaky_service_degraded", 1 if flaky_status else 0, MetricType.GAUGE)

            # 短暂延迟以模拟真实环境
            await asyncio.sleep(0.001)

        # 分析弹性测试结果
        resilient_healthy_count = sum(1 for result in stress_test_results[-10:] for r in result if r.service_id == "resilient_service" and r.status == HealthStatus.HEALTHY)
        flaky_degraded_count = sum(1 for result in stress_test_results[-10:] for r in result if r.service_id == "flaky_service" and r.status == HealthStatus.DEGRADED)

        # 验证弹性表现
        assert resilient_healthy_count >= 8, f"Resilient service healthy rate too low: {resilient_healthy_count}/10"
        assert flaky_degraded_count >= 8, f"Flaky service degraded rate too low: {flaky_degraded_count}/10"

        # 验证响应时间
        resilient_results = [r for r in stress_test_results[-10:] for r in r.service_id == "resilient_service"]
        resilient_response_times = [r.response_time for r in resilient_results]
        avg_resilient_response = sum(resilient_response_times) / len(resilient_response_times)

        assert avg_resilient_response < 0.05, f"Resilient service response time too high: {avg_resilient_response:.3f}s"

        print("✅ 监控系统弹性测试通过")
        print(f"   弹性服务健康率: {resilient_healthy_count}/10")
        print(f"   不稳定服务降级率: {flaky_degraded_count}/10")
        print(f"   平均响应时间: {avg_resilient_response:.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])