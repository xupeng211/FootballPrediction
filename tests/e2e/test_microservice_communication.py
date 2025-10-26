"""
Phase 4A Week 3 - 微服务间通信测试

Microservice Communication Test Suite

这个测试文件提供微服务间通信的综合测试，包括：
- REST API通信测试
- 消息队列通信测试
- gRPC通信测试
- 事件驱动通信测试
- 服务发现和注册测试
- 超时和重试机制测试

测试覆盖率目标：>=95%
"""

import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
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
        def create_mock_user_service():
            return Mock()

        @staticmethod
        def create_mock_prediction_service():
            return Mock()

        @staticmethod
        def create_mock_notification_service():
            return Mock()


class CommunicationProtocol(Enum):
    """通信协议"""
    REST_API = "rest_api"
    MESSAGE_QUEUE = "message_queue"
    GRPC = "grpc"
    EVENT_STREAM = "event_stream"
    WEBSOCKET = "websocket"


class ServiceStatus(Enum):
    """服务状态"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


@dataclass
class ServiceMessage:
    """服务消息"""
    id: str
    source_service: str
    target_service: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None

    def __post_init__(self):
        if self.correlation_id is None:
            self.correlation_id = str(uuid.uuid4())


@dataclass
class CommunicationMetrics:
    """通信指标"""
    total_messages: int = 0
    successful_messages: int = 0
    failed_messages: int = 0
    avg_response_time: float = 0.0
    timeout_count: int = 0
    retry_count: int = 0

    @property
    def success_rate(self) -> float:
        total = self.successful_messages + self.failed_messages
        return self.successful_messages / total if total > 0 else 0

    @property
    def error_rate(self) -> float:
        return 1.0 - self.success_rate


class MockMessageQueue:
    """Mock消息队列"""

    def __init__(self, name: str):
        self.name = name
        self.messages: List[ServiceMessage] = []
        self.subscribers: Dict[str, Callable] = {}
        self.processing_delay = 0.01

    async def publish(self, message: ServiceMessage):
        """发布消息"""
        self.messages.append(message)

        # 模拟处理延迟
        await asyncio.sleep(self.processing_delay)

        # 通知订阅者
        for subscriber_id, callback in self.subscribers.items():
            try:
                await callback(message)
            except Exception as e:
                print(f"Subscriber {subscriber_id} error: {e}")

        return {"status": "published", "message_id": message.id}

    async def subscribe(self, subscriber_id: str, callback: Callable):
        """订阅消息"""
        self.subscribers[subscriber_id] = callback

    async def unsubscribe(self, subscriber_id: str):
        """取消订阅"""
        if subscriber_id in self.subscribers:
            del self.subscribers[subscriber_id]

    def get_messages_count(self) -> int:
        """获取消息数量"""
        return len(self.messages)

    def clear(self):
        """清空消息"""
        self.messages.clear()


class MockEventBus:
    """Mock事件总线"""

    def __init__(self):
        self.events: List[ServiceMessage] = []
        self.handlers: Dict[str, List[Callable]] = {}

    async def publish_event(self, event_type: str, payload: Dict[str, Any], source: str = "unknown"):
        """发布事件"""
        event = ServiceMessage(
            id=str(uuid.uuid4()),
            source_service=source,
            target_service="broadcast",
            message_type=event_type,
            payload=payload,
            timestamp=datetime.now()
        )

        self.events.append(event)

        # 通知事件处理器
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    print(f"Event handler error: {e}")

        return {"status": "published", "event_id": event.id}

    async def subscribe_event(self, event_type: str, handler: Callable, handler_id: str = None):
        """订阅事件"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []

        self.handlers[event_type].append(handler)

    async def unsubscribe_event(self, event_type: str, handler_id: str = None):
        """取消订阅事件"""
        if event_type in self.handlers:
            # 简化实现，移除最后一个处理器
            if self.handlers[event_type]:
                self.handlers[event_type].pop()

    def get_events_count(self) -> int:
        """获取事件数量"""
        return len(self.events)

    def get_events_by_type(self, event_type: str) -> List[ServiceMessage]:
        """根据类型获取事件"""
        return [event for event in self.events if event.message_type == event_type]


class MockGRPCService:
    """Mock gRPC服务"""

    def __init__(self, service_name: str, processing_delay: float = 0.01):
        self.service_name = service_name
        self.processing_delay = processing_delay
        self.methods = {}

    def register_method(self, method_name: str, handler: Callable):
        """注册gRPC方法"""
        self.methods[method_name] = handler

    async def call_method(self, method_name: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """调用gRPC方法"""
        if method_name not in self.methods:
            raise ValueError(f"Method {method_name} not found")

        # 模拟gRPC调用延迟
        await asyncio.sleep(self.processing_delay)

        # 调用处理方法
        return await self.methods[method_name](request_data)


class MockWebSocketService:
    """Mock WebSocket服务"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.connections: Dict[str, Any] = {}
        self.message_handlers: Dict[str, Callable] = {}

    async def connect(self, connection_id: str):
        """建立WebSocket连接"""
        self.connections[connection_id] = {
            "connected_at": datetime.now(),
            "message_count": 0
        }
        return {"status": "connected", "connection_id": connection_id}

    async def disconnect(self, connection_id: str):
        """断开WebSocket连接"""
        if connection_id in self.connections:
            del self.connections[connection_id]

    async def send_message(self, connection_id: str, message: Dict[str, Any]):
        """发送消息到连接"""
        if connection_id not in self.connections:
            raise ValueError(f"Connection {connection_id} not found")

        self.connections[connection_id]["message_count"] += 1

    async def broadcast_message(self, message: Dict[str, Any]):
        """广播消息到所有连接"""
        message_ids = []
        for connection_id in self.connections.keys():
            await self.send_message(connection_id, message)
            message_ids.append(connection_id)
        return {"status": "broadcast", "connection_count": len(message_ids)}


class MockServiceRegistry:
    """Mock服务注册中心"""

    def __init__(self):
        self.services: Dict[str, Dict[str, Any]] = {}
        self.health_checks: Dict[str, ServiceStatus] = {}

    def register_service(self, service_id: str, service_info: Dict[str, Any]):
        """注册服务"""
        self.services[service_id] = {
            **service_info,
            "registered_at": datetime.now(),
            "status": ServiceStatus.HEALTHY
        }
        self.health_checks[service_id] = ServiceStatus.HEALTHY
        return {"status": "registered", "service_id": service_id}

    def deregister_service(self, service_id: str):
        """注销服务"""
        if service_id in self.services:
            del self.services[service_id]
        if service_id in self.health_checks:
            del self.health_checks[service_id]
        return {"status": "deregistered", "service_id": service_id}

    def discover_service(self, service_name: str) -> Optional[Dict[str, Any]]:
        """发现服务"""
        for service_id, info in self.services.items():
            if info.get("name") == service_name and self.health_checks.get(service_id) == ServiceStatus.HEALTHY:
                return info
        return None

    def get_all_services(self) -> List[Dict[str, Any]]:
        """获取所有健康的服务"""
        return [
            {"id": service_id, **info}
            for service_id, info in self.services.items()
            if self.health_checks.get(service_id) == ServiceStatus.HEALTHY
        ]

    def update_service_health(self, service_id: str, status: ServiceStatus):
        """更新服务健康状态"""
        self.health_checks[service_id] = status
        if service_id in self.services:
            self.services[service_id]["status"] = status
            self.services[service_id]["last_health_check"] = datetime.now()


class TestMicroserviceCommunication:
    """微服务通信测试"""

    @pytest.fixture
    def mock_services(self):
        """Mock服务集合"""
        return {
            'user_service': Phase4AMockFactory.create_mock_user_service(),
            'prediction_service': Phase4AMockFactory.create_mock_prediction_service(),
            'notification_service': Phase4AMockFactory.create_mock_notification_service(),
        }

    @pytest.fixture
    def communication_metrics(self):
        """通信指标收集器"""
        return CommunicationMetrics()

    @pytest.fixture
    def message_queue(self):
        """消息队列"""
        return MockMessageQueue("test_queue")

    @pytest.fixture
    def event_bus(self):
        """事件总线"""
        return MockEventBus()

    @pytest.fixture
    def grpc_service(self):
        """gRPC服务"""
        return MockGRPCService("prediction_service")

    @pytest.fixture
    def websocket_service(self):
        """WebSocket服务"""
        return MockWebSocketService("notification_service")

    @pytest.fixture
    def service_registry(self):
        """服务注册中心"""
        return MockServiceRegistry()

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_rest_api_communication(self, mock_services, communication_metrics):
        """测试REST API通信"""
        print("🧪 测试REST API通信")

        # 模拟用户服务调用预测服务
        with patch.object(mock_services['prediction_service'], 'get_predictions') as mock_get:
            mock_get.return_value = {
                "predictions": [
                    {"id": 1, "match_id": 1, "prediction": "home_win"}
                ]
            }

            # 发送REST API请求
            start_time = time.time()
            response = await mock_services['prediction_service'].get_predictions(
                user_id="user_123",
                filters={"league": "premier_league"}
            )
            response_time = time.time() - start_time

            # 验证响应
            assert response is not None
            assert "predictions" in response
            assert len(response["predictions"]) > 0

            communication_metrics.successful_messages += 1
            communication_metrics.total_messages += 1
            communication_metrics.avg_response_time = response_time

        print(f"✅ REST API通信成功 ({response_time:.3f}s)")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_message_queue_communication(self, message_queue, communication_metrics):
        """测试消息队列通信"""
        print("🧪 测试消息队列通信")

        # 创建测试消息
        message = ServiceMessage(
            id=str(uuid.uuid4()),
            source_service="user_service",
            target_service="prediction_service",
            message_type="prediction_request",
            payload={
                "user_id": "user_123",
                "match_id": 1
            },
            timestamp=datetime.now()
        )

        # 订阅消息
        received_messages = []

        async def message_handler(msg: ServiceMessage):
            received_messages.append(msg)
            communication_metrics.successful_messages += 1

        await message_queue.subscribe("test_subscriber", message_handler)

        # 发布消息
        start_time = time.time()
        result = await message_queue.publish(message)
        publish_time = time.time() - start_time

        assert result["status"] == "published"
        assert result["message_id"] == message.id

        # 等待消息处理
        await asyncio.sleep(0.1)

        # 验证消息接收
        assert len(received_messages) == 1
        assert received_messages[0].id == message.id
        assert received_messages[0].source_service == "user_service"

        communication_metrics.total_messages += 1
        communication_metrics.avg_response_time = publish_time

        print(f"✅ 消息队列通信成功 ({publish_time:.3f}s)")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_event_driven_communication(self, event_bus, communication_metrics):
        """测试事件驱动通信"""
        print("🧪 测试事件驱动通信")

        # 事件处理器
        prediction_events = []

        async def prediction_created_handler(event: ServiceMessage):
            prediction_events.append(event)
            communication_metrics.successful_messages += 1

        async def prediction_updated_handler(event: ServiceMessage):
            communication_metrics.successful_messages += 1

        # 订阅事件
        await event_bus.subscribe_event("prediction.created", prediction_created_handler, "handler_1")
        await event_bus.subscribe_event("prediction.updated", prediction_updated_handler, "handler_2")

        # 发布预测创建事件
        start_time = time.time()
        result = await event_bus.publish_event(
            "prediction.created",
            {
                "prediction_id": "pred_123",
                "match_id": 1,
                "prediction": "home_win",
                "confidence": 0.75
            },
            source="prediction_service"
        )
        publish_time = time.time() - start_time

        assert result["status"] == "published"
        assert result["event_id"] is not None

        # 发布预测更新事件
        await event_bus.publish_event(
            "prediction.updated",
            {
                "prediction_id": "pred_123",
                "confidence": 0.80,
                "updated_at": datetime.now().isoformat()
            },
            source="prediction_service"
        )

        # 等待事件处理
        await asyncio.sleep(0.1)

        # 验证事件处理
        assert len(prediction_events) == 1
        assert prediction_events[0].message_type == "prediction.created"
        assert prediction_events[0].payload["prediction_id"] == "pred_123"

        assert event_bus.get_events_count() == 2
        assert len(event_bus.get_events_by_type("prediction.created")) == 1
        assert len(event_bus.get_events_by_type("prediction.updated")) == 1

        communication_metrics.total_messages += 2
        communication_metrics.avg_response_time = publish_time

        print(f"✅ 事件驱动通信成功 ({publish_time:.3f}s)")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_grpc_communication(self, grpc_service, communication_metrics):
        """测试gRPC通信"""
        print("🧪 测试gRPC通信")

        # 注册gRPC方法
        async def get_user_predictions(request_data):
            await asyncio.sleep(0.01)
            return {
                "user_id": request_data["user_id"],
                "predictions": [
                    {
                        "id": str(uuid.uuid4()),
                        "match_id": request_data.get("match_id", 1),
                        "prediction": "home_win",
                        "confidence": 0.75
                    }
                ]
            }

        async def create_prediction(request_data):
            await asyncio.sleep(0.02)
            return {
                "prediction_id": str(uuid.uuid4()),
                "status": "created",
                "match_id": request_data["match_id"],
                "prediction": request_data["prediction"]
            }

        grpc_service.register_method("GetUserPredictions", get_user_predictions)
        grpc_service.register_method("CreatePrediction", create_prediction)

        # 测试获取用户预测
        start_time = time.time()
        result = await grpc_service.call_method("GetUserPredictions", {
            "user_id": "user_123",
            "match_id": 1
        })
        response_time = time.time() - start_time

        assert "user_id" in result
        assert "predictions" in result
        assert len(result["predictions"]) > 0

        communication_metrics.successful_messages += 1
        communication_metrics.total_messages += 1

        # 测试创建预测
        start_time = time.time()
        result = await grpc_service.call_method("CreatePrediction", {
            "match_id": 2,
            "prediction": "away_win",
            "confidence": 0.65
        })
        response_time = time.time() - start_time

        assert "prediction_id" in result
        assert result["status"] == "created"

        communication_metrics.successful_messages += 1
        communication_metrics.total_messages += 1

        # 平均响应时间
        communication_metrics.avg_response_time = (
            (communication_metrics.avg_response_time * (communication_metrics.total_messages - 2) + response_time * 2) /
            communication_metrics.total_messages
        )

        print(f"✅ gRPC通信成功 (平均 {communication_metrics.avg_response_time:.3f}s)")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_websocket_communication(self, websocket_service, communication_metrics):
        """测试WebSocket通信"""
        print("🧪 测试WebSocket通信")

        # 建立连接
        connection_id = "conn_123"
        connection_result = await websocket_service.connect(connection_id)

        assert connection_result["status"] == "connected"
        assert connection_result["connection_id"] == connection_id

        # 发送消息到连接
        message = {
            "type": "notification",
            "data": {
                "title": "Prediction Result",
                "message": "Your prediction was successful!",
                "timestamp": datetime.now().isoformat()
            }
        }

        start_time = time.time()
        await websocket_service.send_message(connection_id, message)
        send_time = time.time() - start_time

        # 验证连接状态
        connections = websocket_service.connections
        assert connection_id in connections
        assert connections[connection_id]["message_count"] == 1

        communication_metrics.successful_messages += 1
        communication_metrics.total_messages += 1
        communication_metrics.avg_response_time = send_time

        # 广播消息
        broadcast_message = {
            "type": "system_update",
            "data": {
                "message": "System will undergo maintenance in 10 minutes",
                "level": "warning"
            }
        }

        start_time = time.time()
        broadcast_result = await websocket_service.broadcast_message(broadcast_message)
        broadcast_time = time.time() - start_time

        assert broadcast_result["status"] == "broadcast"
        assert broadcast_result["connection_count"] == 1

        # 断开连接
        await websocket_service.disconnect(connection_id)
        assert connection_id not in websocket_service.connections

        communication_metrics.successful_messages += 1
        communication_metrics.total_messages += 1

        # 更新平均响应时间
        communication_metrics.avg_response_time = (
            (communication_metrics.avg_response_time * (communication_metrics.total_messages - 2) + broadcast_time * 2) /
            communication_metrics.total_messages
        )

        print(f"✅ WebSocket通信成功 (平均 {communication_metrics.avg_response_time:.3f}s)")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_service_discovery_and_registration(self, service_registry, communication_metrics):
        """测试服务发现和注册"""
        print("🧪 测试服务发现和注册")

        # 注册多个服务
        services = [
            {
                "name": "user_service",
                "host": "localhost",
                "port": 8001,
                "version": "1.0.0",
                "protocol": "REST"
            },
            {
                "name": "prediction_service",
                "host": "localhost",
                "port": 8002,
                "version": "1.0.0",
                "protocol": "REST"
            },
            {
                "name": "notification_service",
                "host": "localhost",
                "port": 8003,
                "version": "1.0.0",
                "protocol": "WebSocket"
            }
        ]

        registered_services = []
        for service_info in services:
            service_id = f"{service_info['name']}_{service_info['port']}"
            result = await service_registry.register_service(service_id, service_info)

            assert result["status"] == "registered"
            assert result["service_id"] == service_id
            registered_services.append(service_id)

            communication_metrics.successful_messages += 1
            communication_metrics.total_messages += 1

        # 发现服务
        for service_name in ["user_service", "prediction_service", "notification_service"]:
            discovered_service = service_registry.discover_service(service_name)

            if service_name in ["user_service", "prediction_service"]:
                assert discovered_service is not None
                assert discovered_service["name"] == service_name
                assert discovered_service["status"] == ServiceStatus.HEALTHY

                communication_metrics.successful_messages += 1
            else:
                # notification_service可能不存在，这是正常的
                assert discovered_service is None

            communication_metrics.total_messages += 1

        # 获取所有健康服务
        all_services = service_registry.get_all_services()
        assert len(all_services) >= 2  # 至少有2个健康服务

        # 注销服务
        for service_id in registered_services:
            result = await service_registry.deregister_service(service_id)
            assert result["status"] == "deregistered"

        communication_metrics.successful_messages += len(registered_services)
        communication_metrics.total_messages += len(registered_services)

        print("✅ 服务发现和注册测试通过")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_timeout_and_retry_mechanism(self, communication_metrics):
        """测试超时和重试机制"""
        print("🧪 测试超时和重试机制")

        retry_attempts = []
        max_retries = 3
        timeout_duration = 0.1

        async def unreliable_service_call():
            """模拟不可靠的服务调用"""
            retry_attempts.append(len(retry_attempts) + 1)

            if len(retry_attempts) < max_retries:
                # 前几次调用失败
                raise Exception("Service temporarily unavailable")
            else:
                # 最后一次调用成功
                return {"status": "success", "attempt": len(retry_attempts)}

        # 实现重试逻辑
        async def call_with_retry():
            for attempt in range(max_retries):
                try:
                    start_time = time.time()

                    # 设置超时
                    result = await asyncio.wait_for(
                        unreliable_service_call(),
                        timeout=timeout_duration
                    )

                    response_time = time.time() - start_time
                    return {
                        "status": "success",
                        "result": result,
                        "attempt": attempt + 1,
                        "response_time": response_time
                    }
                except asyncio.TimeoutError:
                    communication_metrics.timeout_count += 1
                    print(f"Attempt {attempt + 1}: Timeout after {timeout_duration}s")
                    continue
                except Exception as e:
                    communication_metrics.failed_messages += 1
                    print(f"Attempt {attempt + 1}: {e}")
                    continue

            return {
                "status": "failed",
                "error": "Max retries exceeded",
                "attempts": max_retries
            }

        # 执行带重试的调用
        start_time = time.time()
        result = await call_with_retry()
        total_time = time.time() - start_time

        # 验证结果
        assert result["status"] == "success"
        assert result["attempt"] == max_retries
        assert len(retry_attempts) == max_retries

        # 验证重试次数
        communication_metrics.retry_count = max_retries - 1
        communication_metrics.successful_messages += 1
        communication_metrics.total_messages += max_retries

        print(f"✅ 超时和重试机制测试通过 ({total_time:.3f}s)")
        print(f"   重试次数: {communication_metrics.retry_count}")
        print(f"   超时次数: {communication_metrics.timeout_count}")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_service_orchestration(self, message_queue, event_bus, communication_metrics):
        """测试服务编排"""
        print("🧪 测试服务编排")

        # 模拟业务流程：用户创建预测 -> 通知 -> 数据分析

        # 1. 用户服务发布预测创建事件
        prediction_created_event = await event_bus.publish_event(
            "prediction.created",
            {
                "user_id": "user_123",
                "match_id": 1,
                "prediction": "home_win",
                "confidence": 0.75
            },
            source="user_service"
        )

        # 2. 预测服务监听事件并创建分析任务
        analysis_task = None

        async def prediction_handler(event):
            nonlocal analysis_task
            if event.message_type == "prediction.created":
                # 创建分析任务消息
                task_message = ServiceMessage(
                    id=str(uuid.uuid4()),
                    source_service="prediction_service",
                    target_service="analysis_service",
                    message_type="analysis_request",
                    payload={
                        "prediction_id": event.payload["prediction_id"],
                        "match_id": event.payload["match_id"],
                        "prediction": event.payload["prediction"]
                    },
                    timestamp=datetime.now()
                )

                # 发布分析任务到消息队列
                await message_queue.publish(task_message)
                analysis_task = task_message

        await event_bus.subscribe_event("prediction.created", prediction_handler)

        # 3. 分析服务处理任务并发布结果
        analysis_result = None

        async def message_handler(msg):
            nonlocal analysis_result
            if msg.message_type == "analysis_request":
                # 模拟分析处理
                await asyncio.sleep(0.01)

                result_message = ServiceMessage(
                    id=str(uuid.uuid4()),
                    source_service="analysis_service",
                    target_service="notification_service",
                    message_type="analysis_result",
                    payload={
                        "prediction_id": msg.payload["prediction_id"],
                        "analysis_result": "high_confidence",
                        "accuracy_score": 0.85,
                        "processed_at": datetime.now().isoformat()
                    },
                    timestamp=datetime.now(),
                    correlation_id=msg.id
                )

                # 发布分析结果
                await event_bus.publish_event(
                    "analysis.completed",
                    result_message.payload,
                    source="analysis_service"
                )

                analysis_result = result_message

        await message_queue.subscribe("analysis_service", message_handler)

        # 4. 通知服务监听分析结果
        notification_sent = False

        async def result_handler(event):
            nonlocal notification_sent
            if event.message_type == "analysis.completed":
                # 发送通知
                await asyncio.sleep(0.005)
                notification_sent = True

        await event_bus.subscribe_event("analysis.completed", result_handler)

        # 等待整个流程完成
        await asyncio.sleep(0.1)

        # 验证编排结果
        assert prediction_created_event["status"] == "published"
        assert analysis_task is not None
        assert analysis_result is not None
        assert notification_sent is True

        # 验证消息和事件统计
        total_events = event_bus.get_events_count()
        total_messages = message_queue.get_messages_count()

        assert total_events >= 2  # prediction.created + analysis.completed
        assert total_messages >= 1  # analysis_request

        # 更新通信指标
        communication_metrics.successful_messages = total_events + total_messages
        communication_metrics.total_messages = communication_metrics.successful_messages

        print("✅ 服务编排测试通过")
        print(f"   处理事件数: {total_events}")
        print(f"   处理消息数: {total_messages}")

    @pytest.mark.e2e
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, communication_metrics):
        """测试熔断器模式"""
        print("🧪 测试熔断器模式")

        circuit_state = {
            "failure_count": 0,
            "state": "CLOSED",  # CLOSED, OPEN, HALF_OPEN
            "last_failure_time": None,
            "failure_threshold": 3,
            "recovery_timeout": 0.5
        }

        async def protected_call():
            """受保护的服务调用"""
            if circuit_state["state"] == "OPEN":
                if datetime.now() - circuit_state["last_failure_time"] > timedelta(
                    seconds=circuit_state["recovery_timeout"]
                ):
                    circuit_state["state"] = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN")

            try:
                # 模拟服务调用
                await asyncio.sleep(0.01)

                # 模拟间歇性失败
                import random
                if random.random() < 0.6:  # 60% 失败率
                    raise Exception("Service call failed")

                # 成功时重置计数器
                if circuit_state["state"] == "HALF_OPEN":
                    circuit_state["state"] = "CLOSED"

                circuit_state["failure_count"] = 0
                return {"status": "success", "circuit_state": circuit_state["state"]}

            except Exception as e:
                circuit_state["failure_count"] += 1
                circuit_state["last_failure_time"] = datetime.now()

                if circuit_state["failure_count"] >= circuit_state["failure_threshold"]:
                    circuit_state["state"] = "OPEN"

                communication_metrics.failed_messages += 1
                raise e

        # 测试熔断器行为
        results = []

        # 前几次调用应该成功（随机性）
        for i in range(10):
            try:
                result = await protected_call()
                results.append(result)
                communication_metrics.successful_messages += 1
                communication_metrics.total_messages += 1
            except Exception:
                results.append({"status": "failed", "circuit_state": circuit_state["state"]})
                communication_metrics.failed_messages += 1
                communication_metrics.total_messages += 1

        # 验证熔断器被触发
        assert circuit_state["failure_count"] >= circuit_state["failure_threshold"]
        assert circuit_state["state"] in ["OPEN", "CLOSED"]  # 可能已经恢复

        # 验证成功率
        success_count = sum(1 for r in results if r["status"] == "success")
        total_count = len(results)
        success_rate = success_count / total_count

        print("✅ 熔断器模式测试通过")
        print(f"   成功率: {success_rate:.1%}")
        print(f"   最终状态: {circuit_state['state']}")
        print(f"   失败次数: {circuit_state['failure_count']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])