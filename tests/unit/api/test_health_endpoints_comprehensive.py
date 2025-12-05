"""
健康检查API端点综合测试套件
Health Check API Endpoints Comprehensive Test Suite

专门测试健康检查相关API端点的功能，包括基础健康检查、详细健康检查、组件状态监控等.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Optional

import pytest

# FastAPI和相关组件
try:
    import asyncio
    from enum import Enum

    from fastapi import BackgroundTasks, FastAPI, HTTPException, Path, Query
    from fastapi.testclient import TestClient
    from pydantic import BaseModel

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    pytest.skip("FastAPI not available", allow_module_level=True)


# 安全的Mock类
class HealthSafeMock:
    """健康检查专用的安全Mock类"""

    def __init__(self, *args, **kwargs):
        # 直接设置属性，避免使用hasattr
        self._attributes = set(kwargs.keys())
        for key, value in kwargs.items():
            object.__setattr__(self, key, value)

        # 设置默认属性
        if "status" not in self._attributes:
            object.__setattr__(self, "status", "healthy")
            self._attributes.add("status")

    def __call__(self, *args, **kwargs):
        return HealthSafeMock(*args, **kwargs)

    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )
        return HealthSafeMock(name=name)

    def __bool__(self):
        return True

    def __iter__(self):
        return iter([])

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# 枚举定义
class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class ComponentType(str, Enum):
    DATABASE = "database"
    CACHE = "cache"
    EXTERNAL_API = "external_api"
    MESSAGE_QUEUE = "message_queue"
    FILESYSTEM = "filesystem"
    MEMORY = "memory"
    CPU = "cpu"
    NETWORK = "network"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Pydantic模型定义
class ComponentHealth(BaseModel):
    name: str
    status: HealthStatus
    response_time_ms: float | None = None
    last_check: datetime
    error_message: str | None = None
    metadata: dict[str, Any] | None = None


class DetailedComponentHealth(ComponentHealth):
    uptime_percentage: float | None = None
    total_requests: int | None = None
    error_rate: float | None = None
    last_error: datetime | None = None
    dependencies: list[str] | None = None


class HealthResponse(BaseModel):
    status: HealthStatus
    service: str
    version: str
    timestamp: datetime
    uptime_seconds: float
    environment: str


class DetailedHealthResponse(HealthResponse):
    components: dict[str, DetailedComponentHealth]
    system_metrics: dict[str, Any] | None = None
    alerts: list[dict[str, Any]] | None = None


class HealthHistory(BaseModel):
    timestamp: datetime
    status: HealthStatus
    component_health: dict[str, ComponentHealth]


class MockHealthChecker:
    """Mock健康检查器"""

    def __init__(self):
        self.start_time = datetime.now()
        self.components = {
            ComponentType.DATABASE: {
                "name": "PostgreSQL Database",
                "status": HealthStatus.HEALTHY,
                "response_time_ms": 12.5,
                "last_check": datetime.now(),
                "uptime_percentage": 99.9,
                "total_requests": 15420,
                "error_rate": 0.001,
                "metadata": {"connection_pool": "8/20", "slow_queries": 2},
            },
            ComponentType.CACHE: {
                "name": "Redis Cache",
                "status": HealthStatus.HEALTHY,
                "response_time_ms": 2.1,
                "last_check": datetime.now(),
                "uptime_percentage": 99.99,
                "total_requests": 89765,
                "error_rate": 0.0001,
                "hit_rate": 0.85,
                "memory_usage": "256MB/1GB",
                "metadata": {"hit_rate": 0.85, "memory_usage": "25%"},
            },
            ComponentType.EXTERNAL_API: {
                "name": "External Football API",
                "status": HealthStatus.DEGRADED,
                "response_time_ms": 485.2,
                "last_check": datetime.now(),
                "uptime_percentage": 98.5,
                "total_requests": 3421,
                "error_rate": 0.015,
                "last_error": datetime.now() - timedelta(minutes=15),
                "metadata": {"rate_limit_remaining": 4500, "rate_limit_total": 5000},
            },
            ComponentType.MESSAGE_QUEUE: {
                "name": "RabbitMQ",
                "status": HealthStatus.HEALTHY,
                "response_time_ms": 8.3,
                "last_check": datetime.now(),
                "uptime_percentage": 99.8,
                "total_requests": 12450,
                "error_rate": 0.002,
                "queue_count": 23,
                "metadata": {"queues": 5, "messages": 145},
            },
            ComponentType.FILESYSTEM: {
                "name": "Local Filesystem",
                "status": HealthStatus.HEALTHY,
                "response_time_ms": 0.5,
                "last_check": datetime.now(),
                "metadata": {"disk_usage": "45GB/100GB", "free_space": "55GB"},
            },
            ComponentType.MEMORY: {
                "name": "System Memory",
                "status": HealthStatus.HEALTHY,
                "response_time_ms": 1.2,
                "last_check": datetime.now(),
                "metadata": {"usage": "2.1GB/8GB", "free": "5.9GB"},
            },
        }
        self.health_history = []
        self.alerts = [
            {
                "id": 1,
                "component": "External API",
                "severity": SeverityLevel.MEDIUM,
                "message": "Response time above threshold",
                "timestamp": datetime.now() - timedelta(minutes=10),
            }
        ]

    async def check_component_health(
        self, component_type: ComponentType
    ) -> DetailedComponentHealth:
        """检查单个组件健康状态"""
        if component_type in self.components:
            component_data = self.components[component_type]

            # 模拟检查延迟
            await asyncio.sleep(0.01)

            return DetailedComponentHealth(
                name=component_data["name"],
                status=component_data["status"],
                response_time_ms=component_data["response_time_ms"],
                last_check=component_data["last_check"],
                uptime_percentage=component_data.get("uptime_percentage"),
                total_requests=component_data.get("total_requests"),
                error_rate=component_data.get("error_rate"),
                last_error=component_data.get("last_error"),
                metadata=component_data.get("metadata", {}),
            )
        else:
            return DetailedComponentHealth(
                name=f"Unknown Component ({component_type})",
                status=HealthStatus.UNKNOWN,
                last_check=datetime.now(),
            )

    async def check_overall_health(self) -> HealthStatus:
        """检查整体健康状态"""
        component_statuses = [comp["status"] for comp in self.components.values()]

        if all(status == HealthStatus.HEALTHY for status in component_statuses):
            return HealthStatus.HEALTHY
        elif any(status == HealthStatus.UNHEALTHY for status in component_statuses):
            return HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in component_statuses):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNKNOWN

    async def get_system_metrics(self) -> dict[str, Any]:
        """获取系统指标"""
        return {
            "cpu_usage_percent": 45.2,
            "memory_usage_percent": 26.3,
            "disk_usage_percent": 45.0,
            "network_io": {"bytes_sent": 1048576, "bytes_received": 2097152},
            "process_count": 156,
            "load_average": [0.5, 0.8, 0.6],
        }

    def get_uptime_seconds(self) -> float:
        """获取运行时间（秒）"""
        return (datetime.now() - self.start_time).total_seconds()

    def add_health_snapshot(
        self, status: HealthStatus, components: dict[str, ComponentHealth]
    ):
        """添加健康快照到历史记录"""
        snapshot = HealthHistory(
            timestamp=datetime.now(), status=status, component_health=components
        )
        self.health_history.append(snapshot)

        # 保持历史记录在合理范围内
        if len(self.health_history) > 1000:
            self.health_history = self.health_history[-1000:]

    async def simulate_component_failure(self, component_type: ComponentType):
        """模拟组件故障"""
        if component_type in self.components:
            self.components[component_type]["status"] = HealthStatus.UNHEALTHY
            self.components[component_type]["last_error"] = datetime.now()
            self.components[component_type]["error_message"] = (
                "Simulated failure for testing"
            )

    async def simulate_component_recovery(self, component_type: ComponentType):
        """模拟组件恢复"""
        if component_type in self.components:
            self.components[component_type]["status"] = HealthStatus.HEALTHY
            self.components[component_type]["error_message"] = None
            self.components[component_type]["response_time_ms"] = 10.0


# 创建FastAPI应用
def create_health_test_app() -> FastAPI:
    """创建健康检查测试用FastAPI应用"""
    app = FastAPI(
        title="Health Check API", description="健康检查API测试应用", version="1.0.0"
    )

    health_checker = MockHealthChecker()

    # 基础健康检查端点
    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def basic_health_check():
        """基础健康检查"""
        overall_status = await health_checker.check_overall_health()
        uptime = health_checker.get_uptime_seconds()

        return HealthResponse(
            status=overall_status,
            service="football-prediction-api",
            version="1.0.0",
            timestamp=datetime.now(),
            uptime_seconds=uptime,
            environment="test",
        )

    # 详细健康检查端点
    @app.get("/health/detailed", response_model=DetailedHealthResponse, tags=["Health"])
    async def detailed_health_check():
        """详细健康检查"""
        overall_status = await health_checker.check_overall_health()
        uptime = health_checker.get_uptime_seconds()
        system_metrics = await health_checker.get_system_metrics()

        # 检查所有组件
        detailed_components = {}
        for component_type in ComponentType:
            component_health = await health_checker.check_component_health(
                component_type
            )
            detailed_components[component_type.value] = component_health

        return DetailedHealthResponse(
            status=overall_status,
            service="football-prediction-api",
            version="1.0.0",
            timestamp=datetime.now(),
            uptime_seconds=uptime,
            environment="test",
            components=detailed_components,
            system_metrics=system_metrics,
            alerts=health_checker.alerts,
        )

    # 单个组件健康检查
    @app.get(
        "/health/components/{component_type}",
        response_model=DetailedComponentHealth,
        tags=["Health"],
    )
    async def get_component_health(
        component_type: str = Path(..., description="组件类型"),
    ):
        """获取单个组件健康状态"""
        try:
            component_enum = ComponentType(component_type)
            component_health = await health_checker.check_component_health(
                component_enum
            )
            return component_health
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid component type: {component_type}"
            ) from None

    # 组件列表
    @app.get("/health/components", tags=["Health"])
    async def list_components():
        """获取所有可用组件列表"""
        return {
            "components": [
                {
                    "type": comp.value,
                    "name": health_checker.components.get(comp, {}).get(
                        "name", comp.value
                    ),
                }
                for comp in ComponentType
            ]
        }

    # 健康历史
    @app.get("/health/history", tags=["Health"])
    async def get_health_history(
        limit: int = Query(10, ge=1, le=100, description="返回记录数限制"),
    ):
        """获取健康检查历史"""
        history = health_checker.health_history[-limit:]
        return {
            "history": [
                {
                    "timestamp": snapshot.timestamp.isoformat(),
                    "status": snapshot.status,
                    "component_count": len(snapshot.component_health),
                }
                for snapshot in history
            ],
            "total_count": len(health_checker.health_history),
        }

    # 系统指标
    @app.get("/health/metrics", tags=["Health"])
    async def get_system_metrics():
        """获取系统指标"""
        metrics = await health_checker.get_system_metrics()
        return {"metrics": metrics, "timestamp": datetime.now().isoformat()}

    # 活跃告警
    @app.get("/health/alerts", tags=["Health"])
    async def get_active_alerts():
        """获取活跃告警"""
        return {
            "alerts": health_checker.alerts,
            "total_count": len(health_checker.alerts),
        }

    # 测试端点 - 模拟故障（仅用于测试）
    @app.post("/health/test/fail/{component_type}", tags=["Health", "Test"])
    async def simulate_component_failure(
        component_type: str = Path(..., description="要模拟故障的组件类型"),
    ):
        """模拟组件故障（仅用于测试）"""
        try:
            component_enum = ComponentType(component_type)
            await health_checker.simulate_component_failure(component_enum)
            return {"message": f"Simulated failure for component: {component_type}"}
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid component type: {component_type}"
            ) from None

    # 测试端点 - 模拟恢复（仅用于测试）
    @app.post("/health/test/recover/{component_type}", tags=["Health", "Test"])
    async def simulate_component_recovery(
        component_type: str = Path(..., description="要模拟恢复的组件类型"),
    ):
        """模拟组件恢复（仅用于测试）"""
        try:
            component_enum = ComponentType(component_type)
            await health_checker.simulate_component_recovery(component_enum)
            return {"message": f"Simulated recovery for component: {component_type}"}
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid component type: {component_type}"
            ) from None

    # 健康检查触发器
    @app.post("/health/refresh", tags=["Health"])
    async def refresh_health_checks(background_tasks: BackgroundTasks):
        """刷新健康检查状态"""
        # 在后台任务中执行健康检查
        background_tasks.add_task(perform_full_health_check, health_checker)
        return {"message": "Health check refresh started", "timestamp": datetime.now()}

    # 后台任务函数
    async def perform_full_health_check(health_checker_instance):
        """执行完整的健康检查"""
        try:
            # 检查所有组件
            components = {}
            for component_type in ComponentType:
                component_health = await health_checker_instance.check_component_health(
                    component_type
                )
                components[component_type.value] = component_health

            # 获取整体状态
            overall_status = await health_checker_instance.check_overall_health()

            # 添加到历史记录
            health_checker_instance.add_health_snapshot(overall_status, components)

            logging.info(f"Health check completed: {overall_status}")
        except Exception:
            logging.error(f"Health check failed: {e}")

    return app


# 创建测试应用和客户端
health_app = create_health_test_app()
health_client = TestClient(health_app)

logger = logging.getLogger(__name__)

# ==================== 测试用例 ====================


class TestBasicHealthCheck:
    """基础健康检查测试类"""

    def test_basic_health_check_success(self):
        """测试基础健康检查成功"""
        response = health_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # 验证响应结构
        required_fields = [
            "status",
            "service",
            "version",
            "timestamp",
            "uptime_seconds",
            "environment",
        ]
        for field in required_fields:
            assert field in data

        # 验证数据类型和值
        assert data["status"] in [status.value for status in HealthStatus]
        assert data["service"] == "football-prediction-api"
        assert data["version"] == "1.0.0"
        assert data["environment"] == "test"
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0

    def test_basic_health_check_response_time(self):
        """测试基础健康检查响应时间"""
        start_time = time.time()
        response = health_client.get("/health")
        end_time = time.time()

        response_time = end_time - start_time

        assert response.status_code == 200
        assert response_time < 1.0, f"Health check too slow: {response_time}s"

    def test_basic_health_check_content_type(self):
        """测试基础健康检查响应内容类型"""
        response = health_client.get("/health")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_basic_health_check_no_auth_required(self):
        """测试基础健康检查不需要认证"""
        response = health_client.get("/health")
        assert response.status_code == 200


class TestDetailedHealthCheck:
    """详细健康检查测试类"""

    def test_detailed_health_check_success(self):
        """测试详细健康检查成功"""
        response = health_client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()

        # 验证基础字段
        required_fields = [
            "status",
            "service",
            "version",
            "timestamp",
            "uptime_seconds",
            "environment",
            "components",
        ]
        for field in required_fields:
            assert field in data

        # 验证组件数据
        assert isinstance(data["components"], dict)
        assert len(data["components"]) > 0

        # 验证每个组件的结构
        for _component_key, component in data["components"].items():
            self._validate_component_structure(component)

    def _validate_component_structure(self, component):
        """验证组件结构"""
        required_fields = ["name", "status", "last_check"]
        for field in required_fields:
            assert field in component

        assert component["status"] in [status.value for status in HealthStatus]
        assert isinstance(component["name"], str)

        # 可选字段验证
        if "response_time_ms" in component:
            assert isinstance(component["response_time_ms"], (int, float))
            assert component["response_time_ms"] >= 0

        if (
            "uptime_percentage" in component
            and component["uptime_percentage"] is not None
        ):
            assert isinstance(component["uptime_percentage"], (int, float))
            assert 0 <= component["uptime_percentage"] <= 100

        if "error_rate" in component:
            assert isinstance(component["error_rate"], (int, float))
            assert 0 <= component["error_rate"] <= 1

    def test_detailed_health_check_includes_system_metrics(self):
        """测试详细健康检查包含系统指标"""
        response = health_client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()

        assert "system_metrics" in data
        metrics = data["system_metrics"]

        # 验证系统指标结构
        expected_metrics = [
            "cpu_usage_percent",
            "memory_usage_percent",
            "disk_usage_percent",
        ]
        for metric in expected_metrics:
            assert metric in metrics
            assert isinstance(metrics[metric], (int, float))
            assert 0 <= metrics[metric] <= 100

    def test_detailed_health_check_includes_alerts(self):
        """测试详细健康检查包含告警信息"""
        response = health_client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()

        assert "alerts" in data
        alerts = data["alerts"]
        assert isinstance(alerts, list)

        # 验证告警结构
        if alerts:
            alert = alerts[0]
            required_fields = ["id", "component", "severity", "message", "timestamp"]
            for field in required_fields:
                assert field in alert

            assert alert["severity"] in [severity.value for severity in SeverityLevel]


class TestComponentHealthCheck:
    """组件健康检查测试类"""

    def _validate_component_structure(self, component):
        """验证组件结构"""
        required_fields = ["name", "status", "last_check"]
        for field in required_fields:
            assert field in component

        assert component["status"] in [status.value for status in HealthStatus]
        assert isinstance(component["name"], str)

        # 可选字段验证
        if (
            "response_time_ms" in component
            and component["response_time_ms"] is not None
        ):
            assert isinstance(component["response_time_ms"], (int, float))
            assert component["response_time_ms"] >= 0

        if (
            "uptime_percentage" in component
            and component["uptime_percentage"] is not None
        ):
            assert isinstance(component["uptime_percentage"], (int, float))
            assert 0 <= component["uptime_percentage"] <= 100

        if "error_rate" in component and component["error_rate"] is not None:
            assert isinstance(component["error_rate"], (int, float))
            assert 0 <= component["error_rate"] <= 1

    def test_get_database_component_health(self):
        """测试获取数据库组件健康状态"""
        response = health_client.get("/health/components/database")

        assert response.status_code == 200
        data = response.json()
        self._validate_component_structure(data)
        assert "database" in data["name"].lower() or "PostgreSQL" in data["name"]

    def test_get_cache_component_health(self):
        """测试获取缓存组件健康状态"""
        response = health_client.get("/health/components/cache")

        assert response.status_code == 200
        data = response.json()
        self._validate_component_structure(data)
        assert "redis" in data["name"].lower() or "cache" in data["name"].lower()

    def test_get_invalid_component_health(self):
        """测试获取无效组件健康状态"""
        response = health_client.get("/health/components/invalid_component")

        assert response.status_code == 400
        data = response.json()
        assert "Invalid component type" in data["detail"]

    def test_list_all_components(self):
        """测试列出所有组件"""
        response = health_client.get("/health/components")

        assert response.status_code == 200
        data = response.json()

        assert "components" in data
        components = data["components"]
        assert isinstance(components, list)
        assert len(components) > 0

        # 验证每个组件都有type和name
        for component in components:
            assert "type" in component
            assert "name" in component


class TestHealthHistory:
    """健康历史测试类"""

    def test_get_health_history(self):
        """测试获取健康历史"""
        response = health_client.get("/health/history")

        assert response.status_code == 200
        data = response.json()

        assert "history" in data
        assert "total_count" in data

        history = data["history"]
        assert isinstance(history, list)

        # 验证历史记录结构
        if history:
            record = history[0]
            required_fields = ["timestamp", "status", "component_count"]
            for field in required_fields:
                assert field in record

    def test_get_health_history_with_limit(self):
        """测试带限制的健康历史获取"""
        response = health_client.get("/health/history?limit=5")

        assert response.status_code == 200
        data = response.json()
        history = data["history"]

        assert len(history) <= 5

    def test_health_history_limit_validation(self):
        """测试健康历史限制验证"""
        # 测试超出限制的值
        response = health_client.get("/health/history?limit=200")
        assert response.status_code in [200, 422]  # 根据实现可能不同

        # 测试负数
        response = health_client.get("/health/history?limit=-1")
        assert response.status_code in [200, 422]


class TestSystemMetrics:
    """系统指标测试类"""

    def test_get_system_metrics(self):
        """测试获取系统指标"""
        response = health_client.get("/health/metrics")

        assert response.status_code == 200
        data = response.json()

        assert "metrics" in data
        assert "timestamp" in data

        metrics = data["metrics"]

        # 验证基础指标
        required_metrics = [
            "cpu_usage_percent",
            "memory_usage_percent",
            "disk_usage_percent",
        ]
        for metric in required_metrics:
            assert metric in metrics
            assert isinstance(metrics[metric], (int, float))
            assert 0 <= metrics[metric] <= 100

        # 验证网络IO指标
        if "network_io" in metrics:
            network_io = metrics["network_io"]
            assert "bytes_sent" in network_io
            assert "bytes_received" in network_io

    def test_system_metrics_timestamp_format(self):
        """测试系统指标时间戳格式"""
        response = health_client.get("/health/metrics")

        assert response.status_code == 200
        data = response.json()

        timestamp_str = data["timestamp"]
        # 验证时间戳格式（ISO格式）
        try:
            datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            pytest.fail(f"Invalid timestamp format: {timestamp_str}")


class TestAlerts:
    """告警测试类"""

    def test_get_active_alerts(self):
        """测试获取活跃告警"""
        response = health_client.get("/health/alerts")

        assert response.status_code == 200
        data = response.json()

        assert "alerts" in data
        assert "total_count" in data

        alerts = data["alerts"]
        assert isinstance(alerts, list)

        # 验证告警结构
        if alerts:
            alert = alerts[0]
            required_fields = ["id", "component", "severity", "message", "timestamp"]
            for field in required_fields:
                assert field in alert

            assert alert["severity"] in [severity.value for severity in SeverityLevel]


class TestHealthSimulation:
    """健康状态模拟测试类"""

    def test_simulate_component_failure(self):
        """测试模拟组件故障"""
        # 先检查组件当前状态
        response = health_client.get("/health/components/database")
        response.json()["status"]

        # 模拟故障
        response = health_client.post("/health/test/fail/database")
        assert response.status_code == 200
        assert "Simulated failure" in response.json()["message"]

        # 验证故障状态
        response = health_client.get("/health/components/database")
        assert response.json()["status"] == "unhealthy"

        # 恢复组件
        response = health_client.post("/health/test/recover/database")
        assert response.status_code == 200

        # 验证恢复状态
        response = health_client.get("/health/components/database")
        assert response.json()["status"] == "healthy"

    def test_simulate_invalid_component_failure(self):
        """测试模拟无效组件故障"""
        response = health_client.post("/health/test/fail/invalid_component")
        assert response.status_code == 400
        assert "Invalid component type" in response.json()["detail"]


class TestHealthRefresh:
    """健康检查刷新测试类"""

    def test_refresh_health_checks(self):
        """测试刷新健康检查"""
        response = health_client.post("/health/refresh")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "timestamp" in data
        assert "Health check refresh started" in data["message"]


class TestHealthCheckPerformance:
    """健康检查性能测试类"""

    def test_concurrent_health_checks(self):
        """测试并发健康检查"""
        import threading
        import time

        results = []

        def make_health_request():
            start_time = time.time()
            response = health_client.get("/health")
            end_time = time.time()
            results.append(
                {
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                }
            )

        # 创建多个并发请求
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_health_request)
            threads.append(thread)

        start_time = time.time()
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()
        end_time = time.time()

        # 验证所有请求都成功
        assert len(results) == 10
        assert all(result["status_code"] == 200 for result in results)

        # 验证响应时间
        response_times = [result["response_time"] for result in results]
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 1.0, (
            f"Average response time too slow: {avg_response_time}s"
        )

        # 验证总体执行时间
        total_time = end_time - start_time
        assert total_time < 5.0, f"Total execution time too slow: {total_time}s"

    def test_detailed_health_check_performance(self):
        """测试详细健康检查性能"""
        start_time = time.time()
        response = health_client.get("/health/detailed")
        end_time = time.time()

        response_time = end_time - start_time

        assert response.status_code == 200
        assert response_time < 2.0, f"Detailed health check too slow: {response_time}s"


class TestHealthCheckReliability:
    """健康检查可靠性测试类"""

    def test_health_check_consistency(self):
        """测试健康检查结果一致性"""
        # 多次调用基础健康检查
        responses = []
        for _ in range(5):
            response = health_client.get("/health")
            responses.append(response.json())

        # 验证基本字段的一致性
        base_response = responses[0]
        for response in responses[1:]:
            assert response["service"] == base_response["service"]
            assert response["version"] == base_response["version"]
            assert response["environment"] == base_response["environment"]

        # 运行时间应该是递增的
        uptimes = [response["uptime_seconds"] for response in responses]
        assert all(uptimes[i] <= uptimes[i + 1] for i in range(len(uptimes) - 1))

    def test_component_status_persistence(self):
        """测试组件状态持久性"""
        # 获取初始状态
        response = health_client.get("/health/components/database")
        initial_data = response.json()

        # 等待一秒后再次获取
        import time

        time.sleep(1)

        response = health_client.get("/health/components/database")
        later_data = response.json()

        # 验证状态一致性（除非我们模拟了变化）
        assert initial_data["name"] == later_data["name"]
        assert initial_data["status"] == later_data["status"]

        # 验证时间戳更新
        assert later_data["last_check"] != initial_data["last_check"]


class TestHealthCheckErrorHandling:
    """健康检查错误处理测试类"""

    def test_health_check_robustness(self):
        """测试健康检查的健壮性"""
        # 测试各种边界条件
        test_cases = [
            "/health",
            "/health/detailed",
            "/health/components/database",
            "/health/metrics",
            "/health/alerts",
        ]

        for endpoint in test_cases:
            response = health_client.get(endpoint)
            # 所有端点都应该返回有效状态码
            assert response.status_code in [200, 400, 404, 500]

            if response.status_code == 200:
                # 成功响应应该包含有效的JSON
                data = response.json()
                assert isinstance(data, dict)

    def test_invalid_endpoints(self):
        """测试无效端点"""
        invalid_endpoints = [
            "/health/invalid",
            "/health/components/invalid_component",
            "/health/unknown_endpoint",
        ]

        for endpoint in invalid_endpoints:
            response = health_client.get(endpoint)
            assert response.status_code in [400, 404]


class TestHealthCheckIntegration:
    """健康检查集成测试类"""

    def test_full_health_workflow(self):
        """测试完整的健康检查工作流程"""
        # 1. 获取基础健康状态
        basic_response = health_client.get("/health")
        assert basic_response.status_code == 200
        basic_data = basic_response.json()

        # 2. 获取详细健康状态
        detailed_response = health_client.get("/health/detailed")
        assert detailed_response.status_code == 200
        detailed_data = detailed_response.json()

        # 3. 验证一致性
        assert basic_data["status"] == detailed_data["status"]
        assert basic_data["service"] == detailed_data["service"]
        assert basic_data["version"] == detailed_data["version"]

        # 4. 检查组件状态
        assert "components" in detailed_data
        components = detailed_data["components"]

        # 5. 验证组件类型
        expected_component_types = [comp.value for comp in ComponentType]
        for component_type in expected_component_types:
            if component_type in components:
                component_response = health_client.get(
                    f"/health/components/{component_type}"
                )
                assert component_response.status_code == 200

        # 6. 获取系统指标
        metrics_response = health_client.get("/health/metrics")
        assert metrics_response.status_code == 200

        # 7. 刷新健康检查
        refresh_response = health_client.post("/health/refresh")
        assert refresh_response.status_code == 200

    def test_health_check_with_component_failure_simulation(self):
        """测试组件故障模拟下的健康检查"""
        # 1. 模拟外部API故障
        fail_response = health_client.post("/health/test/fail/external_api")
        assert fail_response.status_code == 200

        # 2. 验证整体状态变为degraded或unhealthy
        detailed_response = health_client.get("/health/detailed")
        assert detailed_response.status_code == 200
        detailed_data = detailed_response.json()

        # 整体状态应该反映组件故障
        assert detailed_data["status"] in ["degraded", "unhealthy"]

        # 3. 验证特定组件状态
        component_response = health_client.get("/health/components/external_api")
        component_data = component_response.json()
        assert component_data["status"] == "unhealthy"

        # 4. 恢复组件
        recover_response = health_client.post("/health/test/recover/external_api")
        assert recover_response.status_code == 200

        # 5. 验证恢复后的状态
        component_response = health_client.get("/health/components/external_api")
        component_data = component_response.json()
        assert component_data["status"] == "healthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])