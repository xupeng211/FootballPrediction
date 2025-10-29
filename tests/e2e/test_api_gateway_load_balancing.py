from typing import List
from typing import Optional
from typing import Any
"""
Phase 4A Week 3 - API网关和负载均衡测试

API Gateway and Load Balancing Test Suite

这个测试文件提供API网关和负载均衡的综合测试，包括：
- API网关路由测试
- 负载均衡算法测试
- 服务发现和健康检查
- 熔断和降级机制
- 限流和防护机制

测试覆盖率目标：>=95%
"""

import asyncio
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict

import pytest

# 导入Phase 4A Mock工厂
try:
    from tests.unit.mocks.mock_factory_phase4a import Phase4AMockFactory
except ImportError:

    class Phase4AMockFactory:
        @staticmethod
        def create_mock_gateway_service():
            return Mock()

        @staticmethod
        def create_mock_load_balancer():
            return Mock()


class LoadBalancingStrategy(Enum):
    """负载均衡策略"""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RANDOM = "random"


class RoutingRule(Enum):
    """路由规则类型"""

    PATH_BASED = "path_based"
    HEADER_BASED = "header_based"
    METHOD_BASED = "method_based"
    HOST_BASED = "host_based"


@dataclass
class ServiceInstance:
    """服务实例"""

    id: str
    host: str
    port: int
    weight: int = 1
    health_status: str = "healthy"
    connection_count: int = 0
    response_time: float = 0.0
    last_health_check: datetime = None

    def __post_init__(self):
        if self.last_health_check is None:
            self.last_health_check = datetime.now()

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass
class GatewayMetrics:
    """网关指标"""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    circuit_breaker_activations: int = 0
    rate_limit_hits: int = 0

    @property
    def success_rate(self) -> float:
        total = self.successful_requests + self.failed_requests
        return self.successful_requests / total if total > 0 else 0

    @property
    def error_rate(self) -> float:
        return 1.0 - self.success_rate


class MockAPIService:
    """Mock API服务"""

    def __init__(self, service_id: str, response_delay: float = 0.01, failure_rate: float = 0.0):
        self.service_id = service_id
        self.response_delay = response_delay
        self.failure_rate = failure_rate
        self.request_count = 0

    async def handle_request(self, path: str, method: str = "GET", headers: Dict[str, str] = None):
        """处理请求"""
        self.request_count += 1

        # 模拟网络延迟
        await asyncio.sleep(self.response_delay)

        # 模拟失败
        import random

        if random.random() < self.failure_rate:
            raise Exception(f"Service {self.service_id} temporarily unavailable")

        # 根据路径返回不同响应
        if path == "/health":
            return {
                "service_id": self.service_id,
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
            }
        elif path.startswith("/api/v1/predictions"):
            return {
                "predictions": [
                    {
                        "id": str(uuid.uuid4()),
                        "match_id": 1,
                        "prediction": "home_win",
                        "confidence": 0.75,
                    }
                ],
                "service_id": self.service_id,
            }
        elif path.startswith("/api/v1/matches"):
            return {
                "matches": [
                    {
                        "id": 1,
                        "home_team": "Manchester United",
                        "away_team": "Liverpool",
                        "date": "2025-10-26T15:00:00Z",
                    }
                ],
                "service_id": self.service_id,
            }
        else:
            return {"message": "Not Found", "service_id": self.service_id}


class MockLoadBalancer:
    """Mock负载均衡器"""

    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.current_index = 0
        self.services: List[ServiceInstance] = []

    def add_service(self, service: ServiceInstance):
        """添加服务实例"""
        self.services.append(service)

    def remove_service(self, service_id: str):
        """移除服务实例"""
        self.services = [s for s in self.services if s.id != service_id]

    async def select_service(self) -> Optional[ServiceInstance]:
        """选择服务实例"""
        if not self.services:
            return None

        # 过滤健康的服务
        healthy_services = [s for s in self.services if s.health_status == "healthy"]
        if not healthy_services:
            return None

        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(healthy_services)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(healthy_services)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_select(healthy_services)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return self._random_select(healthy_services)

        return healthy_services[0]

    def _round_robin_select(self, services: List[ServiceInstance]) -> ServiceInstance:
        """轮询选择"""
        service = services[self.current_index % len(services)]
        self.current_index += 1
        return service

    def _least_connections_select(self, services: List[ServiceInstance]) -> ServiceInstance:
        """最少连接数选择"""
        return min(services, key=lambda s: s.connection_count)

    def _weighted_round_robin_select(self, services: List[ServiceInstance]) -> ServiceInstance:
        """加权轮询选择"""
        # 创建权重列表
        weighted_services = []
        for service in services:
            weighted_services.extend([service] * service.weight)

        return weighted_services[self.current_index % len(weighted_services)]

    def _random_select(self, services: List[ServiceInstance]) -> ServiceInstance:
        """随机选择"""
        import random

        return random.choice(services)


class MockCircuitBreaker:
    """Mock熔断器"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func, *args, **kwargs):
        """执行函数调用"""
        if self.state == "OPEN":
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"

            raise e


class TestAPIGatewayAndLoadBalancing:
    """API网关和负载均衡测试"""

    @pytest.fixture
    def mock_services(self):
        """Mock服务集合"""
        return [
            MockAPIService("service_1", response_delay=0.01, failure_rate=0.0),
            MockAPIService("service_2", response_delay=0.02, failure_rate=0.0),
            MockAPIService("service_3", response_delay=0.015, failure_rate=0.0),
        ]

    @pytest.fixture
    def load_balancer(self):
        """负载均衡器"""
        return MockLoadBalancer(LoadBalancingStrategy.ROUND_ROBIN)

    @pytest.fixture
    def circuit_breaker(self):
        """熔断器"""
        return MockCircuitBreaker(failure_threshold=3, recovery_timeout=30)

    @pytest.fixture
    def gateway_metrics(self):
        """网关指标"""
        return GatewayMetrics()

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_round_robin_load_balancing(self, mock_services, load_balancer, gateway_metrics):
        """测试轮询负载均衡"""
        print("🧪 测试轮询负载均衡策略")

        # 注册服务到负载均衡器
        service_instances = []
        for i, service in enumerate(mock_services):
            instance = ServiceInstance(
                id=service.service_id, host="localhost", port=8001 + i, weight=1
            )
            load_balancer.add_service(instance)
            service_instances.append(instance)

        # 测试负载均衡选择
        selected_services = []
        for _ in range(9):  # 3倍的服务数量
            service = await load_balancer.select_service()
            assert service is not None
            selected_services.append(service.service_id)

        # 验证轮询分布
        expected_distribution = {"service_1": 3, "service_2": 3, "service_3": 3}

        actual_distribution = {}
        for service_id in selected_services:
            actual_distribution[service_id] = actual_distribution.get(service_id, 0) + 1

        assert actual_distribution == expected_distribution
        gateway_metrics.successful_requests += 9

        print("✅ 轮询负载均衡测试通过")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_least_connections_load_balancing(self, mock_services, gateway_metrics):
        """测试最少连接数负载均衡"""
        print("🧪 测试最少连接数负载均衡策略")

        load_balancer = MockLoadBalancer(LoadBalancingStrategy.LEAST_CONNECTIONS)

        # 注册服务并设置初始连接数
        service_instances = [
            ServiceInstance("service_1", "localhost", 8001, connection_count=5),
            ServiceInstance("service_2", "localhost", 8002, connection_count=2),
            ServiceInstance("service_3", "localhost", 8003, connection_count=8),
        ]

        for instance in service_instances:
            load_balancer.add_service(instance)

        # 测试选择最少连接的服务
        selected_service = await load_balancer.select_service()
        assert selected_service.service_id == "service_2"  # 连接数最少

        # 更新连接数后再次测试
        service_2 = next(s for s in load_balancer.services if s.id == "service_2")
        service_2.connection_count = 10

        selected_service = await load_balancer.select_service()
        assert selected_service.service_id == "service_1"  # 现在连接数最少

        gateway_metrics.successful_requests += 2
        print("✅ 最少连接数负载均衡测试通过")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_weighted_round_robin_load_balancing(self, mock_services, gateway_metrics):
        """测试加权轮询负载均衡"""
        print("🧪 测试加权轮询负载均衡策略")

        load_balancer = MockLoadBalancer(LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN)

        # 注册不同权重的服务
        service_instances = [
            ServiceInstance("service_1", "localhost", 8001, weight=3),
            ServiceInstance("service_2", "localhost", 8002, weight=1),
            ServiceInstance("service_3", "localhost", 8003, weight=2),
        ]

        for instance in service_instances:
            load_balancer.add_service(instance)

        # 测试加权分布 (总权重=6)
        selected_services = []
        for _ in range(12):  # 2倍的总权重
            service = await load_balancer.select_service()
            selected_services.append(service.service_id)

        # 验证加权分布
        expected_distribution = {
            "service_1": 6,  # weight 3
            "service_2": 2,  # weight 1
            "service_3": 4,  # weight 2
        }

        actual_distribution = {}
        for service_id in selected_services:
            actual_distribution[service_id] = actual_distribution.get(service_id, 0) + 1

        assert actual_distribution == expected_distribution
        gateway_metrics.successful_requests += 12
        print("✅ 加权轮询负载均衡测试通过")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_service_health_check(self, mock_services, gateway_metrics):
        """测试服务健康检查"""
        print("🧪 测试服务健康检查")

        load_balancer = MockLoadBalancer()

        # 注册服务实例
        for service in mock_services:
            instance = ServiceInstance(
                id=service.service_id,
                host="localhost",
                port=8001,
                health_status="healthy",
            )
            load_balancer.add_service(instance)

        # 测试健康服务选择
        healthy_service = await load_balancer.select_service()
        assert healthy_service is not None
        assert healthy_service.health_status == "healthy"

        # 模拟一个服务不健康
        for service in load_balancer.services:
            if service.id == "service_2":
                service.health_status = "unhealthy"
                break

        # 测试只选择健康服务
        for _ in range(5):
            service = await load_balancer.select_service()
            assert service.health_status == "healthy"
            assert service.id != "service_2"

        gateway_metrics.successful_requests += 6
        print("✅ 服务健康检查测试通过")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_circuit_breaker_functionality(self, circuit_breaker, gateway_metrics):
        """测试熔断器功能"""
        print("🧪 测试熔断器功能")

        call_count = 0

        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise Exception("Simulated failure")
            return "success"

        # 测试正常状态
        assert circuit_breaker.state == "CLOSED"

        # 触发熔断
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_function)

        with pytest.raises(Exception):
            await circuit_breaker.call(failing_function)

        with pytest.raises(Exception):
            await circuit_breaker.call(failing_function)

        # 现在熔断器应该打开
        assert circuit_breaker.state == "OPEN"
        gateway_metrics.circuit_breaker_activations += 1

        # 熔断打开时应该立即失败
        with pytest.raises(Exception) as exc_info:
            await circuit_breaker.call(failing_function)
        assert "Circuit breaker is OPEN" in str(exc_info.value)

        # 模拟恢复时间
        circuit_breaker.last_failure_time = datetime.now() - timedelta(seconds=61)

        # 应该进入半开状态
        result = await circuit_breaker.call(failing_function)
        assert result == "success"
        assert circuit_breaker.state == "CLOSED"

        gateway_metrics.successful_requests += 1
        print("✅ 熔断器功能测试通过")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_services, gateway_metrics):
        """测试限流机制"""
        print("🧪 测试限流机制")

        rate_limiter = {
            "requests_per_minute": 10,
            "current_requests": 0,
            "request_times": [],
        }

        def is_rate_limited():
            now = datetime.now()
            # 清理1分钟前的请求记录
            rate_limiter["request_times"] = [
                req_time
                for req_time in rate_limiter["request_times"]
                if now - req_time < timedelta(minutes=1)
            ]

            if len(rate_limiter["request_times"]) >= rate_limiter["requests_per_minute"]:
                return True
            return False

        def record_request():
            rate_limiter["current_requests"] += 1
            rate_limiter["request_times"].append(datetime.now())

        # 测试正常请求
        for i in range(10):
            assert not is_rate_limited()
            record_request()

        # 下一个请求应该被限流
        assert is_rate_limited()
        gateway_metrics.rate_limit_hits += 1

        # 模拟时间过去
        rate_limiter["request_times"] = [datetime.now() - timedelta(minutes=2)]

        # 现在应该可以正常请求
        assert not is_rate_limited()
        record_request()

        gateway_metrics.successful_requests += 11
        print("✅ 限流机制测试通过")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_gateway_routing_rules(self, mock_services, gateway_metrics):
        """测试网关路由规则"""
        print("🧪 测试网关路由规则")

        routing_rules = {
            "/api/v1/predictions/*": {
                "service": "prediction_service",
                "method": ["GET", "POST"],
                "rate_limit": 100,
            },
            "/api/v1/matches/*": {
                "service": "match_service",
                "method": ["GET"],
                "rate_limit": 200,
            },
            "/health": {
                "service": "health_service",
                "method": ["GET"],
                "rate_limit": 1000,
            },
        }

        def find_routing_rule(path: str, method: str) -> Optional[Dict[str, Any]]:
            for pattern, rule in routing_rules.items():
                if path.startswith(pattern.rstrip("*")):
                    if method in rule["method"]:
                        return rule
            return None

        # 测试预测路由
        rule = find_routing_rule("/api/v1/predictions/123", "POST")
        assert rule is not None
        assert rule["service"] == "prediction_service"

        # 测试比赛路由
        rule = find_routing_rule("/api/v1/matches/upcoming", "GET")
        assert rule is not None
        assert rule["service"] == "match_service"

        # 测试健康检查路由
        rule = find_routing_rule("/health", "GET")
        assert rule is not None
        assert rule["service"] == "health_service"

        # 测试不匹配的路由
        rule = find_routing_rule("/unknown/path", "GET")
        assert rule is None

        gateway_metrics.successful_requests += 4
        print("✅ 网关路由规则测试通过")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, mock_services, load_balancer, gateway_metrics):
        """测试并发请求处理"""
        print("🧪 测试并发请求处理")

        # 注册服务
        for service in mock_services:
            instance = ServiceInstance(id=service.service_id, host="localhost", port=8001)
            load_balancer.add_service(instance)

        async def handle_request():
            service = await load_balancer.select_service()
            if service:
                service.connection_count += 1
                # 模拟处理时间
                await asyncio.sleep(0.01)
                service.connection_count -= 1
                return {"service": service.service_id, "status": "success"}
            return {"status": "no_service_available"}

        # 启动100个并发请求
        num_requests = 100
        tasks = [handle_request() for _ in range(num_requests)]
        start_time = time.time()

        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # 验证结果
        assert len(results) == num_requests
        success_count = sum(1 for r in results if r["status"] == "success")
        assert success_count == num_requests

        # 验证负载分布
        service_counts = {}
        for result in results:
            if result["status"] == "success":
                service_id = result["service"]
                service_counts[service_id] = service_counts.get(service_id, 0) + 1

        # 验证所有服务都被使用
        for service in mock_services:
            assert service.service_id in service_counts
            assert service_counts[service.service_id] > 0

        total_time = end_time - start_time
        avg_time_per_request = total_time / num_requests
        throughput = num_requests / total_time

        print("📊 并发测试结果:")
        print(f"   请求数量: {num_requests}")
        print(f"   总耗时: {total_time:.3f}s")
        print(f"   平均请求时间: {avg_time_per_request:.3f}s")
        print(f"   吞吐量: {throughput:.1f} req/s")
        print(f"   成功率: {success_count/num_requests:.1%}")

        gateway_metrics.total_requests = num_requests
        gateway_metrics.successful_requests = success_count
        gateway_metrics.avg_response_time = avg_time_per_request

        # 性能断言
        assert throughput > 50, f"吞吐量过低: {throughput:.1f} req/s"
        assert avg_time_per_request < 0.05, f"平均响应时间过长: {avg_time_per_request:.3f}s"

        print("✅ 并发请求处理测试通过")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_service_discovery_integration(self, mock_services, gateway_metrics):
        """测试服务发现集成"""
        print("🧪 测试服务发现集成")

        service_registry = {"services": {}}

        async def register_service(service_id: str, host: str, port: int):
            service_registry["services"][service_id] = {
                "id": service_id,
                "host": host,
                "port": port,
                "health": "healthy",
                "last_heartbeat": datetime.now().isoformat(),
                "metadata": {
                    "version": "1.0.0",
                    "capabilities": ["predictions", "matches"],
                },
            }

        async def discover_services(service_type: str = None) -> List[Dict[str, Any]]:
            services = []
            for service_id, info in service_registry["services"].items():
                if service_type is None or service_type in info["metadata"]["capabilities"]:
                    services.append(info)
            return services

        # 注册服务
        for i, service in enumerate(mock_services):
            await register_service(service.service_id, "localhost", 8001 + i)

        # 发现所有服务
        all_services = await discover_services()
        assert len(all_services) == len(mock_services)

        # 发现特定类型服务
        prediction_services = await discover_services("predictions")
        assert len(prediction_services) == len(mock_services)  # 所有服务都支持predictions

        # 验证服务信息
        for service_info in all_services:
            assert "id" in service_info
            assert "host" in service_info
            assert "port" in service_info
            assert "health" in service_info
            assert "last_heartbeat" in service_info

        gateway_metrics.successful_requests += len(mock_services) * 2
        print("✅ 服务发现集成测试通过")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_gateway_middleware_pipeline(self, mock_services, gateway_metrics):
        """测试网关中间件管道"""
        print("🧪 测试网关中间件管道")

        middleware_pipeline = []

        # 认证中间件
        async def auth_middleware(request, next_handler):
            start_time = time.time()

            # 模拟认证验证
            auth_header = request.get("headers", {}).get("Authorization")
            if not auth_header:
                return {"status": "unauthorized", "message": "Missing auth header"}

            result = await next_handler(request)

            processing_time = time.time() - start_time
            result["auth_processing_time"] = processing_time
            return result

        # 限流中间件
        async def rate_limit_middleware(request, next_handler):
            client_ip = request.get("client_ip", "unknown")
            # 简化的限流逻辑
            if client_ip in rate_limit_middleware.request_counts:
                rate_limit_middleware.request_counts[client_ip] += 1
            else:
                rate_limit_middleware.request_counts[client_ip] = 1

            if rate_limit_middleware.request_counts[client_ip] > 10:
                return {"status": "rate_limited", "message": "Too many requests"}

            result = await next_handler(request)
            result["rate_limit_remaining"] = 10 - rate_limit_middleware.request_counts[client_ip]
            return result

        rate_limit_middleware.request_counts = {}

        # 日志中间件
        async def logging_middleware(request, next_handler):
            start_time = time.time()
            method = request.get("method", "GET")
            path = request.get("path", "/")

            print(f"[LOG] {method} {path} - {start_time}")

            result = await next_handler(request)

            processing_time = time.time() - start_time
            print(
                f"[LOG] {method} {path} - {result.get('status', 'unknown')} ({processing_time:.3f}s)"
            )

            result["total_processing_time"] = processing_time
            return result

        # 构建中间件管道
        middleware_pipeline = [
            logging_middleware,
            auth_middleware,
            rate_limit_middleware,
        ]

        # 请求处理器
        async def request_handler(request):
            service = request.get("service", "unknown")
            return {
                "status": "success",
                "service": service,
                "data": {"message": "Request processed successfully"},
            }

        # 执行管道
        async def execute_pipeline(request):
            # 构建处理链
            handlers = [request_handler]
            for middleware in reversed(middleware_pipeline):
                current_handler = handlers[0]
                handlers.insert(0, lambda req, h=current_handler: middleware(req, h))

            return await handlers[0](request)

        # 测试正常请求
        valid_request = {
            "method": "GET",
            "path": "/api/v1/predictions",
            "headers": {"Authorization": "Bearer valid_token"},
            "client_ip": "192.168.1.100",
            "service": "prediction_service",
        }

        result = await execute_pipeline(valid_request)
        assert result["status"] == "success"
        assert "auth_processing_time" in result
        assert "rate_limit_remaining" in result
        assert "total_processing_time" in result

        # 测试未授权请求
        unauthorized_request = {
            "method": "GET",
            "path": "/api/v1/predictions",
            "client_ip": "192.168.1.101",
            "service": "prediction_service",
        }

        result = await execute_pipeline(unauthorized_request)
        assert result["status"] == "unauthorized"

        # 测试限流
        rate_limit_request = {
            "method": "GET",
            "path": "/api/v1/predictions",
            "headers": {"Authorization": "Bearer valid_token"},
            "client_ip": "192.168.1.102",
            "service": "prediction_service",
        }

        # 发送11个请求（超过限制）
        for i in range(11):
            result = await execute_pipeline(rate_limit_request)
            if i < 10:
                assert result["status"] == "success"
                assert result["rate_limit_remaining"] == 10 - (i + 1)
            else:
                assert result["status"] == "rate_limited"

        gateway_metrics.successful_requests += (
            12  # 1 valid + 1 unauthorized + 10 success + 1 rate_limited
        )
        gateway_metrics.failed_requests += 1  # 1 unauthorized

        print("✅ 网关中间件管道测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
