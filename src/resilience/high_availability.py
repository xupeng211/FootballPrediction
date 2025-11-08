"""
系统容错模块 - 高可用性和负载均衡
实现故障转移、负载均衡、服务降级等高可用特性
"""

import asyncio
import hashlib
import logging
import random
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class LoadBalanceStrategy(Enum):
    """负载均衡策略"""

    ROUND_ROBIN = "round_robin"  # 轮询
    WEIGHTED_ROUND_ROBIN = "weighted_rr"  # 加权轮询
    LEAST_CONNECTIONS = "least_conn"  # 最少连接
    RANDOM = "random"  # 随机
    CONSISTENT_HASH = "consistent_hash"  # 一致性哈希
    HEALTH_AWARE = "health_aware"  # 健康感知


class ServiceState(Enum):
    """服务状态"""

    HEALTHY = "healthy"  # 健康
    DEGRADED = "degraded"  # 降级
    UNHEALTHY = "unhealthy"  # 不健康
    MAINTENANCE = "maintenance"  # 维护模式
    DRAINING = "draining"  # 流量排空


@dataclass
class ServiceEndpoint:
    """服务端点"""

    endpoint_id: str
    host: str
    port: int
    weight: int = 1
    state: ServiceState = ServiceState.HEALTHY
    connections: int = 0
    max_connections: int = 1000
    response_time: float = 0.0
    success_rate: float = 100.0
    last_health_check: datetime | None = None
    failure_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def url(self) -> str:
        return f"{self.host}:{self.port}"

    def is_available(self) -> bool:
        """检查端点是否可用"""
        return (
            self.state in [ServiceState.HEALTHY, ServiceState.DEGRADED]
            and self.connections < self.max_connections
        )


@dataclass
class ServiceGroup:
    """服务组"""

    service_name: str
    endpoints: list[ServiceEndpoint] = field(default_factory=list)
    strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN
    current_index: int = 0
    circuit_breaker_enabled: bool = True
    health_check_enabled: bool = True
    last_failover: datetime | None = None
    total_failovers: int = 0

    def get_available_endpoints(self) -> list[ServiceEndpoint]:
        """获取可用端点"""
        return [ep for ep in self.endpoints if ep.is_available()]

    def get_healthy_endpoints(self) -> list[ServiceEndpoint]:
        """获取健康端点"""
        return [ep for ep in self.endpoints if ep.state == ServiceState.HEALTHY]


@dataclass
class FailoverConfig:
    """故障转移配置"""

    enabled: bool = True
    detection_timeout: float = 30.0  # 故障检测超时
    failover_timeout: float = 10.0  # 故障转移超时
    max_failover_attempts: int = 3  # 最大故障转移尝试次数
    recovery_check_interval: float = 60.0  # 恢复检查间隔
    auto_recovery: bool = True  # 自动恢复


@dataclass
class CircuitBreakerConfig:
    """断路器配置"""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3
    monitoring_window: int = 100  # 监控窗口大小


class LoadBalancer:
    """负载均衡器"""

    def __init__(self, service_group: ServiceGroup):
        self.service_group = service_group
        self.request_counter = 0
        self.consistent_hash_ring = {}
        self._initialize_consistent_hash()

    async def select_endpoint(
        self, request_key: str | None = None
    ) -> ServiceEndpoint | None:
        """选择端点"""
        available_endpoints = self.service_group.get_available_endpoints()
        if not available_endpoints:
            logger.warning(
                f"No available endpoints for {self.service_group.service_name}"
            )
            return None

        strategy = self.service_group.strategy

        if strategy == LoadBalanceStrategy.ROUND_ROBIN:
            endpoint = self._round_robin(available_endpoints)
        elif strategy == LoadBalanceStrategy.WEIGHTED_ROUND_ROBIN:
            endpoint = self._weighted_round_robin(available_endpoints)
        elif strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            endpoint = self._least_connections(available_endpoints)
        elif strategy == LoadBalanceStrategy.RANDOM:
            endpoint = self._random(available_endpoints)
        elif strategy == LoadBalanceStrategy.CONSISTENT_HASH:
            endpoint = self._consistent_hash(request_key, available_endpoints)
        elif strategy == LoadBalanceStrategy.HEALTH_AWARE:
            endpoint = self._health_aware(available_endpoints)
        else:
            endpoint = self._round_robin(available_endpoints)

        return endpoint

    def _round_robin(self, endpoints: list[ServiceEndpoint]) -> ServiceEndpoint:
        """轮询选择"""
        endpoint = endpoints[self.service_group.current_index % len(endpoints)]
        self.service_group.current_index += 1
        return endpoint

    def _weighted_round_robin(
        self, endpoints: list[ServiceEndpoint]
    ) -> ServiceEndpoint:
        """加权轮询选择"""
        total_weight = sum(ep.weight for ep in endpoints)
        if total_weight == 0:
            return random.choice(endpoints)

        # 构建加权列表
        weighted_endpoints = []
        for ep in endpoints:
            weighted_endpoints.extend([ep] * ep.weight)

        endpoint = weighted_endpoints[
            self.service_group.current_index % len(weighted_endpoints)
        ]
        self.service_group.current_index += 1
        return endpoint

    def _least_connections(self, endpoints: list[ServiceEndpoint]) -> ServiceEndpoint:
        """最少连接选择"""
        return min(endpoints, key=lambda ep: ep.connections)

    def _random(self, endpoints: list[ServiceEndpoint]) -> ServiceEndpoint:
        """随机选择"""
        return random.choice(endpoints)

    def _consistent_hash(
        self, request_key: str | None, endpoints: list[ServiceEndpoint]
    ) -> ServiceEndpoint:
        """一致性哈希选择"""
        if not request_key:
            return self._round_robin(endpoints)

        hash_key = int(hashlib.md5(request_key.encode()).hexdigest(), 16)
        endpoint_ids = [ep.endpoint_id for ep in endpoints]

        if not endpoint_ids:
            return self._round_robin(endpoints)

        # 简单的一致性哈希实现
        index = hash_key % len(endpoint_ids)
        endpoint_id = endpoint_ids[index]

        for ep in endpoints:
            if ep.endpoint_id == endpoint_id:
                return ep

        return self._round_robin(endpoints)

    def _health_aware(self, endpoints: list[ServiceEndpoint]) -> ServiceEndpoint:
        """健康感知选择"""
        # 优先选择健康端点
        healthy_endpoints = [ep for ep in endpoints if ep.state == ServiceState.HEALTHY]
        if healthy_endpoints:
            return min(healthy_endpoints, key=lambda ep: ep.response_time)

        # 如果没有健康端点，选择降级端点
        degraded_endpoints = [
            ep for ep in endpoints if ep.state == ServiceState.DEGRADED
        ]
        if degraded_endpoints:
            return min(degraded_endpoints, key=lambda ep: ep.response_time)

        # 最后选择任何可用端点
        return self._least_connections(endpoints)

    def _initialize_consistent_hash(self):
        """初始化一致性哈希环"""
        for endpoint in self.service_group.endpoints:
            self.consistent_hash_ring[endpoint.endpoint_id] = endpoint


class FailoverManager:
    """故障转移管理器"""

    def __init__(self, config: FailoverConfig):
        self.config = config
        self.active_failovers: dict[str, datetime] = {}
        self.failover_history: deque = deque(maxlen=1000)

    async def initiate_failover(self, service_group: ServiceGroup) -> bool:
        """启动故障转移"""
        if not self.config.enabled:
            logger.warning("Failover is disabled")
            return False

        service_name = service_group.service_name
        available_endpoints = service_group.get_available_endpoints()

        if len(available_endpoints) <= 1:
            logger.warning(f"Insufficient endpoints for failover: {service_name}")
            return False

        logger.info(f"Initiating failover for {service_name}")
        start_time = datetime.now()

        # 记录故障转移开始
        self.active_failovers[service_name] = start_time
        service_group.last_failover = start_time
        service_group.total_failovers += 1

        try:
            # 执行故障转移逻辑
            success = await self._execute_failover(service_group)

            if success:
                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"Failover completed for {service_name} in {duration:.2f}s")

                # 记录故障转移历史
                self.failover_history.append(
                    {
                        "service": service_name,
                        "timestamp": start_time,
                        "duration": duration,
                        "success": True,
                    }
                )

                return True
            else:
                logger.error(f"Failover failed for {service_name}")
                return False

        except Exception as e:
            logger.error(f"Failover error for {service_name}: {e}")
            return False
        finally:
            # 清理活跃故障转移记录
            self.active_failovers.pop(service_name, None)

    async def _execute_failover(self, service_group: ServiceGroup) -> bool:
        """执行故障转移"""
        service_name = service_group.service_name

        # 标记故障端点
        for endpoint in service_group.endpoints:
            if endpoint.state != ServiceState.UNHEALTHY:
                # 找出问题端点并标记
                if not await self._is_endpoint_healthy(endpoint):
                    endpoint.state = ServiceState.UNHEALTHY
                    endpoint.failure_count += 1

        # 验证至少有一个可用端点
        available_endpoints = service_group.get_available_endpoints()
        if not available_endpoints:
            logger.error(f"No available endpoints after failover for {service_name}")
            return False

        return True

    async def _is_endpoint_healthy(self, endpoint: ServiceEndpoint) -> bool:
        """检查端点健康状态"""
        try:
            # 简单的健康检查（实际实现中应该根据服务类型定制）
            start_time = time.time()
            await asyncio.sleep(0.1)  # 模拟健康检查
            response_time = (time.time() - start_time) * 1000

            # 更新端点指标
            endpoint.response_time = response_time
            endpoint.last_health_check = datetime.now()

            # 根据响应时间判断健康状态
            return response_time < 1000  # 1秒超时

        except Exception as e:
            logger.warning(f"Health check failed for {endpoint.url}: {e}")
            return False

    async def check_recovery(
        self, service_group: ServiceGroup
    ) -> list[ServiceEndpoint]:
        """检查服务恢复情况"""
        recovered_endpoints = []

        for endpoint in service_group.endpoints:
            if endpoint.state == ServiceState.UNHEALTHY:
                # 检查是否应该尝试恢复
                if await self._should_attempt_recovery(endpoint):
                    if await self._is_endpoint_healthy(endpoint):
                        endpoint.state = ServiceState.HEALTHY
                        endpoint.failure_count = 0
                        recovered_endpoints.append(endpoint)
                        logger.info(f"Endpoint {endpoint.url} recovered")

        return recovered_endpoints

    async def _should_attempt_recovery(self, endpoint: ServiceEndpoint) -> bool:
        """检查是否应该尝试恢复"""
        if endpoint.last_health_check is None:
            return True

        time_since_last_check = (
            datetime.now() - endpoint.last_health_check
        ).total_seconds()

        return time_since_last_check >= self.config.recovery_check_interval

    def get_failover_stats(self) -> dict[str, Any]:
        """获取故障转移统计"""
        stats = {
            "active_failovers": len(self.active_failovers),
            "total_failovers": sum(
                sg.total_failovers for sg in self._get_all_service_groups()
            ),
            "recent_failovers": [],
            "failover_success_rate": 0.0,
        }

        # 最近的故障转移
        recent_failovers = [
            event
            for event in self.failover_history
            if (datetime.now() - event["timestamp"]).total_seconds() <= 24 * 3600
        ]
        stats["recent_failovers"] = recent_failovers

        # 计算成功率
        if self.failover_history:
            successful = sum(1 for event in self.failover_history if event["success"])
            stats["failover_success_rate"] = (
                successful / len(self.failover_history)
            ) * 100

        return stats

    def _get_all_service_groups(self) -> list[ServiceGroup]:
        """获取所有服务组（简化实现）"""
        return []


class CircuitBreakerManager:
    """断路器管理器"""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.circuit_breakers: dict[str, Any] = {}

    def get_circuit_breaker(self, service: str, endpoint_id: str) -> Any:
        """获取断路器"""
        key = f"{service}:{endpoint_id}"
        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = self._create_circuit_breaker()
        return self.circuit_breakers[key]

    def _create_circuit_breaker(self) -> Any:
        """创建断路器（简化实现）"""
        from src.resilience.fault_detector import CircuitBreaker

        return CircuitBreaker(
            failure_threshold=self.config.failure_threshold,
            recovery_timeout=self.config.recovery_timeout,
            half_open_max_calls=self.config.half_open_max_calls,
        )


class ServiceRegistry:
    """服务注册中心"""

    def __init__(self):
        self.services: dict[str, ServiceGroup] = {}
        self.endpoints: dict[str, ServiceEndpoint] = {}
        self.load_balancers: dict[str, LoadBalancer] = {}
        self.failover_manager = FailoverManager(FailoverConfig())
        self.circuit_breaker_manager = CircuitBreakerManager(CircuitBreakerConfig())
        self._monitoring_task = None

    def register_service(
        self,
        service_name: str,
        endpoints: list[ServiceEndpoint],
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
    ):
        """注册服务"""
        service_group = ServiceGroup(
            service_name=service_name, endpoints=endpoints, strategy=strategy
        )

        self.services[service_name] = service_group
        self.load_balancers[service_name] = LoadBalancer(service_group)

        # 注册端点
        for endpoint in endpoints:
            self.endpoints[endpoint.endpoint_id] = endpoint

        logger.info(
            f"Registered service {service_name} with {len(endpoints)} endpoints"
        )

    def unregister_service(self, service_name: str):
        """注销服务"""
        if service_name in self.services:
            del self.services[service_name]
            del self.load_balancers[service_name]
            logger.info(f"Unregistered service {service_name}")

    async def call_service(
        self,
        service_name: str,
        func: Callable,
        *args,
        request_key: str | None = None,
        **kwargs,
    ):
        """调用服务"""
        if service_name not in self.services:
            raise ValueError(f"Service {service_name} not found")

        service_group = self.services[service_name]
        load_balancer = self.load_balancers[service_name]

        # 选择端点
        endpoint = await load_balancer.select_endpoint(request_key)
        if not endpoint:
            # 尝试故障转移
            failover_success = await self.failover_manager.initiate_failover(
                service_group
            )
            if failover_success:
                endpoint = await load_balancer.select_endpoint(request_key)
                if not endpoint:
                    raise Exception(
                        f"No available endpoints for {service_name} after failover"
                    )
            else:
                raise Exception(f"Failover failed for {service_name}")

        # 增加连接计数
        endpoint.connections += 1
        start_time = time.time()

        try:
            # 获取断路器
            circuit_breaker = self.circuit_breaker_manager.get_circuit_breaker(
                service_name, endpoint.endpoint_id
            )

            # 通过断路器调用
            result = await circuit_breaker.call(func, *args, **kwargs)

            # 更新成功指标
            response_time = (time.time() - start_time) * 1000
            endpoint.response_time = (
                endpoint.response_time * 0.7 + response_time * 0.3
            )  # 指数平滑
            endpoint.success_rate = endpoint.success_rate * 0.9 + 10  # 指数平滑

            return result

        except Exception as e:
            # 更新失败指标
            endpoint.failure_count += 1
            endpoint.state = ServiceState.UNHEALTHY
            logger.error(f"Service call failed: {service_name} -> {endpoint.url}: {e}")
            raise

        finally:
            # 减少连接计数
            endpoint.connections = max(0, endpoint.connections - 1)

    def get_service_health(self, service_name: str) -> dict[str, Any]:
        """获取服务健康状态"""
        if service_name not in self.services:
            return {"status": "not_found"}

        service_group = self.services[service_name]
        available_endpoints = len(service_group.get_available_endpoints())
        total_endpoints = len(service_group.endpoints)

        return {
            "service": service_name,
            "status": "healthy" if available_endpoints > 0 else "unhealthy",
            "total_endpoints": total_endpoints,
            "available_endpoints": available_endpoints,
            "strategy": service_group.strategy.value,
            "total_failovers": service_group.total_failovers,
            "last_failover": (
                service_group.last_failover.isoformat()
                if service_group.last_failover
                else None
            ),
            "endpoints": [
                {
                    "endpoint_id": ep.endpoint_id,
                    "url": ep.url,
                    "state": ep.state.value,
                    "connections": ep.connections,
                    "max_connections": ep.max_connections,
                    "response_time": ep.response_time,
                    "success_rate": ep.success_rate,
                    "weight": ep.weight,
                }
                for ep in service_group.endpoints
            ],
        }

    def get_registry_stats(self) -> dict[str, Any]:
        """获取注册中心统计"""
        total_services = len(self.services)
        total_endpoints = len(self.endpoints)
        healthy_endpoints = sum(
            1
            for ep in self.endpoints.values()
            if ep.state in [ServiceState.HEALTHY, ServiceState.DEGRADED]
        )

        return {
            "total_services": total_services,
            "total_endpoints": total_endpoints,
            "healthy_endpoints": healthy_endpoints,
            "health_rate": (healthy_endpoints / max(1, total_endpoints)) * 100,
            "failover_stats": self.failover_manager.get_failover_stats(),
            "services": {
                name: self.get_service_health(name) for name in self.services.keys()
            },
        }


# 全局服务注册中心实例
_service_registry: ServiceRegistry | None = None


def get_service_registry() -> ServiceRegistry:
    """获取全局服务注册中心实例"""
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry()
    return _service_registry


def initialize_service_registry() -> ServiceRegistry:
    """初始化全局服务注册中心"""
    global _service_registry
    _service_registry = ServiceRegistry()
    return _service_registry
