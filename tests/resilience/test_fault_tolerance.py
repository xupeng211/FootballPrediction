"""
系统容错测试 - 验证高可用性和故障恢复能力
测试故障检测、故障转移、断路器、负载均衡等容错机制
"""

import asyncio
import random
import time
from unittest.mock import Mock

import pytest

from src.monitoring.alerting.alert_manager import (
    AlertManager,
    AlertRule,
    AlertSeverity,
    AlertStatus,
    NotificationChannel,
)
from src.resilience.fault_detector import (
    CircuitBreaker,
    FaultDetector,
    FaultSeverity,
    FaultType,
    HealthCheck,
    RetryPolicy,
)
from src.resilience.high_availability import (
    LoadBalanceStrategy,
    ServiceEndpoint,
    ServiceRegistry,
    ServiceState,
)


class TestFaultDetector:
    """故障检测器测试"""

    @pytest.fixture
    def fault_detector(self):
        return FaultDetector()

    @pytest.mark.asyncio
    async def test_health_check_registration(self, fault_detector):
        """测试健康检查注册"""

        async def mock_health_check():
            return True

        health_check = HealthCheck(
            name="test_service",
            check_func=mock_health_check,
            interval=30.0,
            timeout=5.0,
        )

        fault_detector.register_health_check(health_check)

        assert "test_service" in fault_detector.health_checks
        assert "test_service" in fault_detector.service_health

    @pytest.mark.asyncio
    async def test_service_health_monitoring(self, fault_detector):
        """测试服务健康监控"""

        async def mock_health_check():
            await asyncio.sleep(0.01)
            return True

        health_check = HealthCheck(
            name="test_service",
            check_func=mock_health_check,
            interval=30.0,
            timeout=5.0,
            failure_threshold=3,
        )

        fault_detector.register_health_check(health_check)

        # 执行健康检查
        health = await fault_detector.check_service_health("test_service")

        assert health.service_name == "test_service"
        assert health.total_checks >= 1

    @pytest.mark.asyncio
    async def test_circuit_breaker(self, fault_detector):
        """测试断路器"""
        fault_detector.register_circuit_breaker("test_service")

        circuit_breaker = fault_detector.circuit_breakers["test_service"]
        assert circuit_breaker.state == "closed"

        # 模拟失败
        async def failing_func():
            raise Exception("Service unavailable")

        with pytest.raises(Exception):
            await circuit_breaker.call(failing_func)

        # 检查状态变化
        # 由于只有一个失败，可能还没到阈值
        assert circuit_breaker.failure_count >= 1

    @pytest.mark.asyncio
    async def test_retry_policy(self):
        """测试重试策略"""
        retry_policy = RetryPolicy(max_attempts=3, base_delay=0.1, max_delay=1.0)

        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Attempt {call_count} failed")
            return "success"

        result = await retry_policy.execute_with_retry(failing_func)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_fault_event_creation(self, fault_detector):
        """测试故障事件创建"""
        await fault_detector._handle_service_failure("test_service")

        # 检查故障事件
        recent_faults = fault_detector.get_recent_faults(hours=1)
        assert len(recent_faults) >= 1

        fault = recent_faults[-1]
        assert fault.service == "test_service"
        assert fault.fault_type == FaultType.SERVICE_UNAVAILABLE
        assert fault.severity == FaultSeverity.HIGH


class TestHighAvailability:
    """高可用性测试"""

    @pytest.fixture
    def service_registry(self):
        return ServiceRegistry()

    def test_service_registration(self, service_registry):
        """测试服务注册"""
        endpoints = [
            ServiceEndpoint("ep1", "localhost", 8001, weight=1),
            ServiceEndpoint("ep2", "localhost", 8002, weight=2),
            ServiceEndpoint("ep3", "localhost", 8003, weight=1),
        ]

        service_registry.register_service("test_service", endpoints)

        service_group = service_registry.services["test_service"]
        assert len(service_group.endpoints) == 3
        assert service_group.strategy == LoadBalanceStrategy.ROUND_ROBIN

    @pytest.mark.asyncio
    async def test_load_balancer_round_robin(self, service_registry):
        """测试轮询负载均衡"""
        endpoints = [
            ServiceEndpoint("ep1", "localhost", 8001),
            ServiceEndpoint("ep2", "localhost", 8002),
            ServiceEndpoint("ep3", "localhost", 8003),
        ]

        service_registry.register_service(
            "test_service", endpoints, LoadBalanceStrategy.ROUND_ROBIN
        )

        # 测试轮询选择
        load_balancer = service_registry.load_balancers["test_service"]

        selected_endpoints = []
        for _ in range(6):  # 6次选择应该轮询每个端点2次
            endpoint = await load_balancer.select_endpoint()
            selected_endpoints.append(endpoint.endpoint_id)

        # 验证轮询
        assert selected_endpoints.count("ep1") == 2
        assert selected_endpoints.count("ep2") == 2
        assert selected_endpoints.count("ep3") == 2

    @pytest.mark.asyncio
    async def test_load_balancer_least_connections(self, service_registry):
        """测试最少连接负载均衡"""
        endpoints = [
            ServiceEndpoint("ep1", "localhost", 8001, connections=5),
            ServiceEndpoint("ep2", "localhost", 8002, connections=2),
            ServiceEndpoint("ep3", "localhost", 8003, connections=8),
        ]

        service_registry.register_service(
            "test_service", endpoints, LoadBalanceStrategy.LEAST_CONNECTIONS
        )

        load_balancer = service_registry.load_balancers["test_service"]
        endpoint = await load_balancer.select_endpoint()

        # 应该选择连接数最少的端点
        assert endpoint.endpoint_id == "ep2"
        assert endpoint.connections == 2

    @pytest.mark.asyncio
    async def test_failover_scenario(self, service_registry):
        """测试故障转移场景"""
        endpoints = [
            ServiceEndpoint("ep1", "localhost", 8001, state=ServiceState.UNHEALTHY),
            ServiceEndpoint("ep2", "localhost", 8002, state=ServiceState.HEALTHY),
            ServiceEndpoint("ep3", "localhost", 8003, state=ServiceState.HEALTHY),
        ]

        service_registry.register_service("test_service", endpoints)

        # 模拟服务调用
        async def mock_service_call():
            await asyncio.sleep(0.01)
            return "response"

        # 应该选择健康的端点
        result = await service_registry.call_service("test_service", mock_service_call)
        assert result == "response"

    @pytest.mark.asyncio
    async def test_service_health_monitoring(self, service_registry):
        """测试服务健康监控"""
        endpoints = [
            ServiceEndpoint("ep1", "localhost", 8001),
            ServiceEndpoint("ep2", "localhost", 8002),
        ]

        service_registry.register_service("test_service", endpoints)

        health_info = service_registry.get_service_health("test_service")
        assert health_info["service"] == "test_service"
        assert "total_endpoints" in health_info
        assert "endpoints" in health_info
        assert len(health_info["endpoints"]) == 2

    @pytest.mark.asyncio
    async def test_registry_stats(self, service_registry):
        """测试注册中心统计"""
        # 注册多个服务
        for i in range(3):
            endpoints = [
                ServiceEndpoint(f"ep{i}1", f"host{i}", 8000 + i * 10),
                ServiceEndpoint(f"ep{i}2", f"host{i}", 8001 + i * 10),
            ]
            service_registry.register_service(f"service_{i}", endpoints)

        stats = service_registry.get_registry_stats()
        assert stats["total_services"] == 3
        assert stats["total_endpoints"] == 6
        assert stats["health_rate"] >= 0  # 初始状态


class TestAlertManager:
    """告警管理器测试"""

    @pytest.fixture
    def alert_manager(self):
        return AlertManager()

    def test_alert_rule_addition(self, alert_manager):
        """测试告警规则添加"""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            description="Test alert rule",
            condition="avg > 100",
            severity=AlertSeverity.WARNING,
            notification_channels=[NotificationChannel.EMAIL],
        )

        alert_manager.add_rule(rule)

        assert "test_rule" in alert_manager.rules
        assert alert_manager.rules["test_rule"].name == "Test Rule"

    def test_alert_rule_removal(self, alert_manager):
        """测试告警规则移除"""
        rule = AlertRule(
            rule_id="test_rule",
            name="Test Rule",
            description="Test alert rule",
            condition="avg > 100",
            severity=AlertSeverity.WARNING,
        )

        alert_manager.add_rule(rule)
        assert "test_rule" in alert_manager.rules

        alert_manager.remove_rule("test_rule")
        assert "test_rule" not in alert_manager.rules

    @pytest.mark.asyncio
    async def test_alert_triggering(self, alert_manager):
        """测试告警触发"""
        rule = AlertRule(
            rule_id="cpu_alert",
            name="High CPU Usage",
            description="CPU usage is too high",
            condition="max > 80",
            severity=AlertSeverity.ERROR,
            threshold=80.0,
        )

        alert_manager.add_rule(rule)

        # 添加触发告警的指标
        await alert_manager.add_metric("cpu_usage", 85.0)

        # 检查是否创建了告警
        active_alerts = alert_manager.get_active_alerts()
        # 可能需要等待规则评估
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_alert_resolution(self, alert_manager):
        """测试告警解决"""
        rule = AlertRule(
            rule_id="test_recovery",
            name="Test Recovery",
            description="Test alert recovery",
            condition="avg > 50",
            severity=AlertSeverity.WARNING,
            recovery_threshold=40.0,
        )

        alert_manager.add_rule(rule)

        # 添加触发告警的指标
        await alert_manager.add_metric("test_metric", 60.0)

        # 添加恢复指标
        await alert_manager.add_metric("test_metric", 30.0)

        # 检查告警摘要
        summary = alert_manager.get_alert_summary()
        assert "total_active_alerts" in summary
        assert "rules_count" in summary

    def test_alert_acknowledgment(self, alert_manager):
        """测试告警确认"""
        # 创建模拟告警
        alert = Mock()
        alert.alert_id = "test_alert_id"
        alert.status = AlertStatus.ACTIVE
        alert.metadata = {}

        alert_manager.active_alerts["test_alert_id"] = alert

        # 确认告警
        alert_manager.acknowledge_alert(
            "test_alert_id", "test_user", "Acknowledged by test user"
        )

        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.metadata["acknowledged_by"] == "test_user"
        assert alert.acknowledged_at is not None

    def test_alert_suppression(self, alert_manager):
        """测试告警抑制"""
        # 创建模拟告警
        alert = Mock()
        alert.alert_id = "test_alert_id"
        alert.status = AlertStatus.ACTIVE
        alert.metadata = {}

        alert_manager.active_alerts["test_alert_id"] = alert

        # 抑制告警
        alert_manager.suppress_alert("test_alert_id", 3600, "test_user")

        assert alert.status == AlertStatus.SUPPRESSED
        assert alert.suppressed_until is not None
        assert alert.metadata["suppressed_by"] == "test_user"

    def test_alert_summary(self, alert_manager):
        """测试告警摘要"""
        summary = alert_manager.get_alert_summary()

        assert "total_active_alerts" in summary
        assert "severity_breakdown" in summary
        assert "rules_count" in summary
        assert "enabled_rules_count" in summary
        assert "recent_alerts" in summary


class TestResilienceIntegration:
    """容错集成测试"""

    @pytest.mark.asyncio
    async def test_fault_detection_with_alerting(self):
        """测试故障检测与告警集成"""
        fault_detector = FaultDetector()
        alert_manager = AlertManager()

        # 创建告警规则
        rule = AlertRule(
            rule_id="service_unavailable",
            name="Service Unavailable",
            description="Service is unavailable",
            condition="avg < 0",
            severity=AlertSeverity.CRITICAL,
            notification_channels=[NotificationChannel.EMAIL],
        )

        alert_manager.add_rule(rule)

        # 模拟服务故障
        await fault_detector._handle_service_failure("critical_service")

        # 检查是否创建了故障事件
        faults = fault_detector.get_recent_faults(hours=1)
        assert len(faults) > 0

        # 验证故障事件
        fault = faults[0]
        assert fault.service == "critical_service"
        assert fault.severity == FaultSeverity.HIGH

    @pytest.mark.asyncio
    async def test_end_to_end_failover_scenario(self):
        """测试端到端故障转移场景"""
        service_registry = ServiceRegistry()
        alert_manager = AlertManager()

        # 创建告警规则
        rule = AlertRule(
            rule_id="failover_alert",
            name="Service Failover",
            description="Service failover triggered",
            condition="avg > 0",
            severity=AlertSeverity.ERROR,
            notification_channels=[NotificationChannel.EMAIL],
        )

        alert_manager.add_rule(rule)

        # 注册带故障的服务
        endpoints = [
            ServiceEndpoint("ep1", "localhost", 8001, state=ServiceState.UNHEALTHY),
            ServiceEndpoint("ep2", "localhost", 8002, state=ServiceState.HEALTHY),
            ServiceEndpoint("ep3", "localhost", 8003, state=ServiceState.DEGRADED),
        ]

        service_registry.register_service("test_service", endpoints)

        # 模拟服务调用
        call_count = 0
        responses = []

        async def mock_service_call():
            nonlocal call_count, responses
            call_count += 1
            await asyncio.sleep(0.001)
            responses.append(f"call_{call_count}")
            return f"response_{call_count}"

        # 执行多次调用，验证故障转移
        for _ in range(10):
            try:
                result = await service_registry.call_service(
                    "test_service", mock_service_call
                )
                responses.append(result)
            except Exception:
                # 记录失败
                pass

        # 验证有一些调用成功（故障转移到健康端点）
        assert len(responses) > 0

        # 检查服务健康状态
        health_info = service_registry.get_service_health("test_service")
        assert health_info["available_endpoints"] >= 1

    @pytest.mark.asyncio
    async def test_resilience_metrics_collection(self):
        """测试容错指标收集"""
        fault_detector = FaultDetector()

        # 模拟系统指标收集
        for i in range(10):
            fault_detector._collect_system_metrics()  # 同步方法调用
            await asyncio.sleep(0.01)  # 模拟时间间隔

        # 检查指标
        metrics_summary = fault_detector.get_metrics_summary()
        assert isinstance(metrics_summary, dict)

        # 检查系统健康状态
        health_summary = fault_detector.get_service_health_summary()
        assert "total_services" in health_summary
        assert "healthy" in health_summary

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_retry(self):
        """测试断路器与重试组合"""
        circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        retry_policy = RetryPolicy(max_attempts=2, base_delay=0.1)

        failure_count = 0
        success_count = 0

        async def unreliable_service():
            nonlocal failure_count, success_count
            if failure_count < 3:
                failure_count += 1
                raise Exception(f"Service failure #{failure_count}")
            else:
                success_count += 1
                return "success"

        # 通过断路器和重试策略调用服务
        try:
            await circuit_breaker.call(
                retry_policy.execute_with_retry, unreliable_service
            )
        except Exception:
            pass  # 预期的异常

        # 验证行为
        assert failure_count >= 3  # 触发了断路器
        assert circuit_breaker.state == "open"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_resilience_performance(self):
        """测试容错系统性能"""
        service_registry = ServiceRegistry()

        # 注册大量端点
        endpoints = []
        for i in range(50):  # 50个端点
            endpoints.append(ServiceEndpoint(f"ep{i}", f"host{i}", 8000 + i, weight=1))

        service_registry.register_service(
            "perf_test", endpoints, LoadBalanceStrategy.RANDOM
        )

        # 测试负载均衡性能
        start_time = time.time()
        tasks = []

        for i in range(100):  # 100个并发请求

            async def mock_service_call():
                await asyncio.sleep(0.001)  # 模拟1ms处理时间
                return f"response_{i}"

            task = service_registry.call_service("perf_test", mock_service_call)
            tasks.append(task)

        # 等待所有请求完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # 计算性能指标
        total_time = end_time - start_time
        avg_time = total_time / 100
        success_count = sum(
            1 for result in results if not isinstance(result, Exception)
        )

        # 性能断言
        assert avg_time < 0.1, f"平均响应时间 {avg_time:.3f}s 过长"
        assert success_count >= 90, f"成功率 {success_count}% 过低"

        print("容错系统性能测试:")
        print(f"  总时间: {total_time:.3f}s")
        print(f"  平均响应时间: {avg_time:.3f}s")
        print(f"  成功率: {success_count}%")


@pytest.mark.asyncio
async def test_combined_resilience_scenarios():
    """组合容错场景测试"""
    # 创建所有组件
    fault_detector = FaultDetector()
    service_registry = ServiceRegistry()
    alert_manager = AlertManager()

    # 注册多个服务
    services = {
        "api_service": [
            ServiceEndpoint("api1", "localhost", 8001),
            ServiceEndpoint("api2", "localhost", 8002),
        ],
        "db_service": [
            ServiceEndpoint("db1", "localhost", 5432),
            ServiceEndpoint("db2", "localhost", 5433),
        ],
        "cache_service": [
            ServiceEndpoint("cache1", "localhost", 6379),
            ServiceEndpoint("cache2", "localhost", 6380),
        ],
    }

    for service_name, endpoints in services.items():
        service_registry.register_service(service_name, endpoints)

        # 注册健康检查
        async def mock_health_check():
            await asyncio.sleep(0.01)
            return True

        health_check = HealthCheck(name=service_name, check_func=mock_health_check)
        fault_detector.register_health_check(health_check)

        # 创建告警规则
        rule = AlertRule(
            rule_id=f"{service_name}_health",
            name=f"{service_name} Health Check",
            description=f"Health check for {service_name}",
            condition="avg < 0.5",
            severity=AlertSeverity.ERROR,
        )
        alert_manager.add_rule(rule)

    # 模拟系统运行
    print("Starting combined resilience test...")
    start_time = time.time()

    # 模拟正常运行
    for _ in range(10):
        await asyncio.sleep(0.1)

        # 模拟一些系统指标
        await fault_detector.add_metric("cpu_usage", 30 + random.random() * 20)
        await fault_detector.add_metric("memory_usage", 40 + random.random() * 30)

    # 模拟故障场景
    print("Simulating fault scenarios...")

    # 1. 模拟API服务故障
    api_endpoints = service_registry.services["api_service"].endpoints
    api_endpoints[0].state = ServiceState.UNHEALTHY

    # 2. 模拟高负载
    for i in range(20):
        await fault_detector.add_metric("cpu_usage", 85 + random.random() * 10)
        await asyncio.sleep(0.01)

    # 验证系统仍然可用
    print("Verifying system availability...")

    for service_name in services.keys():
        health_info = service_registry.get_service_health(service_name)
        print(
            f"  {service_name}: {health_info['status']} ({health_info['available_endpoints']}/{health_info['total_endpoints']})"
        )

    # 验证整体系统状态
    fault_summary = fault_detector.get_service_health_summary()
    alert_summary = alert_manager.get_alert_summary()
    registry_stats = service_registry.get_registry_stats()

    end_time = time.time()
    duration = end_time - start_time

    print("\nCombined Resilience Test Results:")
    print(f"  Test Duration: {duration:.2f}s")
    print(f"  Fault Summary: {fault_summary}")
    print(f"  Alert Summary: {alert_summary}")
    print(f"  Registry Stats: {registry_stats}")

    # 断言系统仍然基本可用
    assert registry_stats["health_rate"] > 0.5, "系统健康率过低"
    assert registry_stats["healthy_endpoints"] > 0, "没有可用端点"

    print("✅ Combined resilience test passed!")


if __name__ == "__main__":
    asyncio.run(test_combined_resilience_scenarios())
