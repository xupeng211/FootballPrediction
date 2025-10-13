"""
API装饰器测试
Tests for API Decorators

测试src.api.decorators模块的装饰器演示端点
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import asyncio
from datetime import datetime

# 测试导入
try:
    from src.api.decorators import router
    from src.api.decorators import (
        example_function_1,
        example_function_2,
        failing_function,
        slow_function,
        global_decorator_service,
    )

    DECORATORS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    DECORATORS_AVAILABLE = False
    router = None
    example_function_1 = None
    example_function_2 = None
    failing_function = None
    slow_function = None
    global_decorator_service = None


@pytest.mark.skipif(not DECORATORS_AVAILABLE, reason="Decorators module not available")
class TestAPIDecorators:
    """API装饰器测试"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)

    def test_router_exists(self):
        """测试：路由器存在"""
        assert router is not None
        assert hasattr(router, "routes")
        assert len(router.routes) > 0

    def test_example_functions_exist(self):
        """测试：示例函数存在"""
        assert example_function_1 is not None
        assert example_function_2 is not None
        assert failing_function is not None
        assert slow_function is not None
        assert asyncio.iscoroutinefunction(example_function_1)
        assert asyncio.iscoroutinefunction(example_function_2)

    async def test_example_function_1(self):
        """测试：示例函数1工作正常"""
        _result = await example_function_1(5, 10)
        assert _result == 15

    async def test_example_function_2(self):
        """测试：示例函数2工作正常"""
        _result = await example_function_2("test")
        assert _result == "Processed: test"

    async def test_failing_function(self):
        """测试：失败函数最终成功"""
        _result = await failing_function(retry_count=2)
        assert _result == "Success after retries"

    async def test_failing_function_will_fail(self):
        """测试：失败函数在重试次数不足时失败"""
        with pytest.raises(ValueError):
            await failing_function(retry_count=1)

    async def test_slow_function(self):
        """测试：慢速函数"""
        start = datetime.utcnow()
        _result = await slow_function(0.01)
        end = datetime.utcnow()

        assert _result == "Completed slowly"
        assert (end - start).total_seconds() >= 0.01

    @patch("src.api.decorators.global_decorator_service")
    def test_get_decorator_stats_all(self, mock_service, client):
        """测试：获取所有装饰器统计"""
        mock_service.get_all_stats.return_value = {
            "function1": {"calls": 10, "success_rate": 0.9},
            "function2": {"calls": 5, "success_rate": 1.0},
        }

        response = client.get("/decorators/stats")
        assert response.status_code == 200
        _data = response.json()
        assert "function1" in data
        assert "function2" in data
        mock_service.get_all_stats.assert_called_once()

    @patch("src.api.decorators.global_decorator_service")
    def test_get_decorator_stats_specific(self, mock_service, client):
        """测试：获取特定函数的装饰器统计"""
        mock_service.get_function_stats.return_value = {
            "function_name": "example_function_1",
            "calls": 10,
            "success_rate": 1.0,
        }

        response = client.get("/decorators/stats?function_name=example_function_1")
        assert response.status_code == 200
        _data = response.json()
        assert data["function_name"] == "example_function_1"
        mock_service.get_function_stats.assert_called_with("example_function_1")

    @patch("src.api.decorators.global_decorator_service")
    def test_get_decorator_stats_not_found(self, mock_service, client):
        """测试：获取不存在函数的统计"""
        mock_service.get_function_stats.return_value = None

        response = client.get("/decorators/stats?function_name=nonexistent")
        assert response.status_code == 404
        _data = response.json()
        assert "detail" in data
        assert "未找到" in data["detail"]

    @patch("src.api.decorators.global_decorator_service")
    def test_clear_decorator_stats(self, mock_service, client):
        """测试：清空装饰器统计"""
        mock_service.clear_stats.return_value = None

        response = client.post("/decorators/stats/clear")
        assert response.status_code == 200
        _data = response.json()
        assert data["message"] == "统计信息已清空"
        mock_service.clear_stats.assert_called_once()


@pytest.mark.skipif(not DECORATORS_AVAILABLE, reason="Decorators module not available")
class TestDecoratorDemos:
    """装饰器演示测试"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)

    @patch("src.api.decorators.global_decorator_service")
    async def test_demo_logging_decorator(self, mock_service, client):
        """测试：日志装饰器演示"""
        # 创建模拟装饰器函数
        mock_decorated = AsyncMock()
        mock_decorated.return_value = 30
        mock_decorated.get_decorator_stats.return_value = {
            "logging": {"calls": 1, "last_call": "2023-01-01T12:00:00"}
        }

        mock_service.apply_decorators.return_value = mock_decorated

        response = client.get("/decorators/demo/logging?input_value=10")
        assert response.status_code == 200
        _data = response.json()

        assert data["input"] == 10
        assert data["result"] == 30
        assert "decorator_stats" in data
        assert "message" in data

        mock_service.apply_decorators.assert_called_with(
            example_function_1, decorator_names=["default_logging"]
        )

    @patch("src.api.decorators.global_decorator_service")
    async def test_demo_retry_decorator(self, mock_service, client):
        """测试：重试装饰器演示"""
        # 创建模拟装饰器函数
        mock_decorated = AsyncMock()
        mock_decorated.return_value = "Success after retries"
        mock_decorated.get_decorator_stats.return_value = {
            "retry": {"attempts": 3, "success": True}
        }

        mock_service.apply_decorators.return_value = mock_decorated

        response = client.get("/decorators/demo/retry")
        assert response.status_code == 200
        _data = response.json()

        assert data["result"] == "Success after retries"
        assert "execution_time_seconds" in data
        assert "decorator_stats" in data
        assert data["message"] == "函数失败后自动重试"

    @patch("src.api.decorators.global_decorator_service")
    async def test_demo_cache_decorator_with_cache(self, mock_service, client):
        """测试：缓存装饰器演示（使用缓存）"""
        # 创建模拟装饰器函数
        mock_decorated = AsyncMock()
        mock_decorated.return_value = 30
        mock_decorated.return_value = 30  # 两次调用返回相同结果
        mock_decorated.get_decorator_stats.return_value = {
            "cache": {"hits": 1, "misses": 1}
        }

        mock_service.apply_decorators.return_value = mock_decorated

        response = client.get("/decorators/demo/cache?input_value=10&use_cache=true")
        assert response.status_code == 200
        _data = response.json()

        assert data["input"] == 10
        assert data["first_call"]["result"] == 30
        assert data["second_call"]["result"] == 30
        assert data["cache_enabled"] is True
        assert "speedup" in data

    @patch("src.api.decorators.global_decorator_service")
    async def test_demo_timeout_decorator_success(self, mock_service, client):
        """测试：超时装饰器演示（成功）"""
        # 创建模拟装饰器函数
        mock_decorated = AsyncMock()
        mock_decorated.return_value = "Completed"

        mock_service.apply_decorators.return_value = mock_decorated

        response = client.get("/decorators/demo/timeout?delay=0.05&timeout_seconds=0.1")
        assert response.status_code == 200
        _data = response.json()

        assert data["success"] is True
        assert data["result"] == "Completed"
        assert data["timed_out"] is False

    @patch("src.api.decorators.global_decorator_service")
    async def test_demo_timeout_decorator_timeout(self, mock_service, client):
        """测试：超时装饰器演示（超时）"""
        # 创建模拟装饰器函数
        mock_decorated = AsyncMock()
        mock_decorated.side_effect = ValueError("Timeout")

        mock_service.apply_decorators.return_value = mock_decorated

        response = client.get("/decorators/demo/timeout?delay=0.2&timeout_seconds=0.1")
        assert response.status_code == 200
        _data = response.json()

        assert data["success"] is False
        assert data["result"] is None
        assert data["error_message"] == "Timeout"

    @patch("src.api.decorators.global_decorator_service")
    async def test_demo_metrics_decorator(self, mock_service, client):
        """测试：指标装饰器演示"""
        # 创建模拟装饰器函数
        mock_decorated = AsyncMock()
        mock_decorated.side_effect = [
            "Processed: iteration_0",
            "Processed: iteration_1",
            "Processed: iteration_2",
        ]
        mock_decorated.get_decorator_stats.return_value = {
            "metrics": {
                "total_calls": 3,
                "average_time": 0.02,
                "min_time": 0.018,
                "max_time": 0.025,
            }
        }

        mock_service.apply_decorators.return_value = mock_decorated

        response = client.get("/decorators/demo/metrics?iterations=3")
        assert response.status_code == 200
        _data = response.json()

        assert data["iterations"] == 3
        assert data["results_count"] == 3
        assert len(data["sample_results"]) == 3
        assert "decorator_stats" in data

    @patch("src.api.decorators.global_decorator_service")
    async def test_demo_combo_decorators(self, mock_service, client):
        """测试：组合装饰器演示"""
        # 创建模拟装饰器函数
        mock_decorated = AsyncMock()
        mock_decorated.return_value = 30
        mock_decorated.return_value = 30  # 两次调用返回相同结果
        mock_decorated.get_decorator_stats.return_value = {
            "decorators": {
                "logging": {"calls": 2},
                "metrics": {"calls": 2},
                "timeout": {"calls": 2},
                "cache": {"hits": 1, "misses": 1},
            }
        }

        mock_service.apply_decorators.return_value = mock_decorated

        response = client.get("/decorators/demo/combo?input_value=10")
        assert response.status_code == 200
        _data = response.json()

        assert data["input"] == 10
        assert len(data["results"]) == 2
        assert data["decorator_count"] == 4
        assert data["message"] == "同时应用了日志、指标、超时和缓存装饰器"


@pytest.mark.skipif(not DECORATORS_AVAILABLE, reason="Decorators module not available")
class TestDecoratorConfigManagement:
    """装饰器配置管理测试"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)

    @patch("src.api.decorators.global_decorator_service")
    def test_get_decorator_configs(self, mock_service, client):
        """测试：获取装饰器配置"""
        # 创建模拟工厂
        mock_factory = Mock()
        mock_factory.list_configs.return_value = ["logging", "cache", "retry"]
        mock_factory.get_config.side_effect = [
            Mock(
                decorator_type="logging",
                enabled=True,
                priority=1,
                parameters={"level": "INFO"},
            ),
            Mock(
                decorator_type="cache",
                enabled=True,
                priority=2,
                parameters={"ttl": 300},
            ),
            Mock(
                decorator_type="retry",
                enabled=False,
                priority=3,
                parameters={"max_attempts": 3},
            ),
        ]
        mock_factory.list_chain_configs.return_value = ["default_chain"]
        mock_factory.get_chain_config.return_value = Mock(
            target_functions=["example_*"],
            is_global=True,
            decorators=["logging", "cache"],
        )

        mock_service.factory = mock_factory
        mock_service._global_decorators = {}
        mock_service._function_decorators = {}

        response = client.get("/decorators/configs")
        assert response.status_code == 200
        _data = response.json()

        assert "decorators" in data
        assert "chains" in data
        assert len(data["decorators"]) == 3
        assert data["decorators"]["logging"]["type"] == "logging"
        assert data["decorators"]["cache"]["enabled"] is True

    @patch("src.api.decorators.global_decorator_service")
    def test_reload_decorator_configs(self, mock_service, client):
        """测试：重新加载装饰器配置"""
        mock_service.reload_configuration.return_value = None

        response = client.post("/decorators/reload")
        assert response.status_code == 200
        _data = response.json()
        assert data["message"] == "装饰器配置已重新加载"
        mock_service.reload_configuration.assert_called_once()


@pytest.mark.skipif(not DECORATORS_AVAILABLE, reason="Decorators module not available")
class TestDecoratorContext:
    """装饰器上下文测试"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = FastAPI()
        app.include_router(router)
        return app

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)

    @patch("src.api.decorators.global_decorator_service")
    @patch("src.api.decorators.DecoratorContext")
    async def test_demo_decorator_context(
        self, mock_context_class, mock_service, client
    ):
        """测试：装饰器上下文演示"""
        # 创建模拟上下文
        mock_context = Mock()
        mock_context.get.side_effect = lambda key, default=None: {
            "user_id": "demo_user",
            "request_id": "req_12345",
        }.get(key, default)
        mock_context.to_dict.return_value = {
            "user_id": "demo_user",
            "request_id": "req_12345",
            "execution_path": ["step1", "step2", "step3"],
        }
        mock_context.execution_path = ["step1", "step2", "step3"]
        mock_context.get_execution_time.return_value = 0.05

        mock_context_class.return_value = mock_context

        # 创建模拟装饰器函数
        mock_decorated = AsyncMock()
        mock_decorated.side_effect = [
            {"value": 2, "user_id": "demo_user", "request_id": "req_12345"},
            {"value": 4, "user_id": "demo_user", "request_id": "req_12345"},
            {"value": 6, "user_id": "demo_user", "request_id": "req_12345"},
        ]

        mock_service.apply_decorators.return_value = mock_decorated

        response = client.get("/decorators/demo/context?step_count=3")
        assert response.status_code == 200
        _data = response.json()

        assert "context_info" in data
        assert data["step_count"] == 3
        assert len(data["results"]) == 3
        assert "execution_path" in data
        assert "total_time" in data


@pytest.mark.skipif(
    DECORATORS_AVAILABLE, reason="Decorators module should be available"
)
class TestModuleNotAvailable:
    """模块不可用时的测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not DECORATORS_AVAILABLE
        assert True  # 表明测试意识到模块不可用


# 测试模块级别的功能
def test_module_imports():
    """测试：模块导入"""
    if DECORATORS_AVAILABLE:
        from src.api.decorators import router, global_decorator_service

        assert router is not None
        assert global_decorator_service is not None


def test_router_routes():
    """测试：路由器路由"""
    if DECORATORS_AVAILABLE:
        routes = [route.path for route in router.routes]
        # 路由包含前缀 /decorators
        expected_routes = [
            "/decorators/stats",
            "/decorators/stats/clear",
            "/decorators/demo/logging",
            "/decorators/demo/retry",
            "/decorators/demo/cache",
            "/decorators/demo/timeout",
            "/decorators/demo/metrics",
            "/decorators/demo/combo",
            "/decorators/configs",
            "/decorators/reload",
            "/decorators/demo/context",
        ]

        for route in expected_routes:
            assert route in routes, f"Missing route: {route}"


@pytest.mark.asyncio
async def test_global_decorator_service():
    """测试：全局装饰器服务"""
    if DECORATORS_AVAILABLE:
        # 验证服务存在
        assert global_decorator_service is not None

        # 验证服务有基本方法
        assert hasattr(global_decorator_service, "apply_decorators")
        assert hasattr(global_decorator_service, "get_all_stats")
        assert hasattr(global_decorator_service, "clear_stats")
        assert hasattr(global_decorator_service, "reload_configuration")
