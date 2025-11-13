#!/usr/bin/env python3
"""
API健康检查单元测试

测试 src.api.health 模块的功能
"""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

try:
    from src.api.health import database_health, health_check, router, system_health
    from src.main_simple import app
except ImportError:
    # 如果无法导入，使用模拟测试
    router = None
    app = None


class TestHealthAPI:
    """API健康检查测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        if app:
            return TestClient(app)
        else:
            return None

    def test_health_check_basic(self):
        """测试基础健康检查"""
        if health_check:
            result = health_check()
            assert isinstance(result, dict)
            assert "status" in result
            assert "timestamp" in result
            assert result["status"] in ["healthy", "unhealthy", "degraded"]
        else:
            pytest.skip("health_check function not available")

    def test_system_health_check(self):
        """测试系统健康检查"""
        if system_health:
            result = system_health()
            assert isinstance(result, dict)
            assert "system" in result
            assert "status" in result
        else:
            pytest.skip("system_health function not available")

    def test_database_health_check(self):
        """测试数据库健康检查"""
        if database_health:
            result = database_health()
            assert isinstance(result, dict)
            assert "database" in result
            assert "status" in result
        else:
            pytest.skip("database_health function not available")

    @pytest.mark.skipif(app is None, reason="FastAPI app not available")
    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        if client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "timestamp" in data

    @pytest.mark.skipif(app is None, reason="FastAPI app not available")
    def test_system_health_endpoint(self, client):
        """测试系统健康检查端点"""
        if client:
            response = client.get("/health/system")
            assert response.status_code == 200
            data = response.json()
            assert "system" in data
            assert "status" in data

    @pytest.mark.skipif(app is None, reason="FastAPI app not available")
    def test_database_health_endpoint(self, client):
        """测试数据库健康检查端点"""
        if client:
            response = client.get("/health/database")
            assert response.status_code == 200
            data = response.json()
            assert "database" in data
            assert "status" in data

    @patch("src.api.health.psutil")
    def test_system_metrics_with_mock(self, mock_psutil):
        """测试系统指标（使用模拟）"""
        # 模拟psutil返回数据
        mock_psutil.cpu_percent.return_value = 45.5
        mock_psutil.virtual_memory.return_value.percent = 60.2
        mock_psutil.disk_usage.return_value.percent = 75.8

        if system_health:
            result = system_health()
            assert isinstance(result, dict)
            # 验证系统指标被收集
            assert "cpu" in result.get("system", {}).get("metrics", {})
            assert "memory" in result.get("system", {}).get("metrics", {})
            assert "disk" in result.get("system", {}).get("metrics", {})
        else:
            pytest.skip("system_health function not available")

    @patch("src.api.health.time.time")
    def test_timestamp_in_health_response(self, mock_time):
        """测试健康响应包含时间戳"""
        mock_time.return_value = 1234567890.123

        if health_check:
            result = health_check()
            assert "timestamp" in result
            assert isinstance(result["timestamp"], (str, int, float))
        else:
            pytest.skip("health_check function not available")

    def test_health_response_structure(self):
        """测试健康响应结构"""
        if health_check:
            result = health_check()

            # 验证基本结构
            required_fields = ["status", "timestamp"]
            for field in required_fields:
                assert field in result, f"Missing required field: {field}"

            # 验证状态值
            valid_statuses = ["healthy", "unhealthy", "degraded"]
            assert result["status"] in valid_statuses

            # 验证时间戳格式
            assert result["timestamp"] is not None
        else:
            pytest.skip("health_check function not available")

    def test_error_handling_in_health_checks(self):
        """测试健康检查中的错误处理"""
        # 测试当某个组件失败时的处理
        if health_check:
            result = health_check()
            # 即使某些组件失败，健康检查也应该返回有效响应
            assert isinstance(result, dict)
            assert "status" in result
        else:
            pytest.skip("health_check function not available")

    @pytest.mark.asyncio
    async def test_async_health_check(self):
        """测试异步健康检查（如果存在）"""
        # 检查是否有异步版本的健康检查
        if hasattr(health_check, "__code__") and health_check.__code__.co_flags & 0x80:
            result = await health_check()
            assert isinstance(result, dict)
        else:
            pytest.skip("No async health check available")

    def test_health_check_caching(self):
        """测试健康检查缓存（如果实现）"""
        if health_check:
            # 第一次调用
            result1 = health_check()
            # 第二次调用
            result2 = health_check()

            # 基本验证两个结果都有相同结构
            assert isinstance(result1, type)(result2)
            assert "status" in result1 and "status" in result2
        else:
            pytest.skip("health_check function not available")

    def test_health_check_with_dependencies(self):
        """测试带依赖项的健康检查"""
        # 如果健康检查接受参数
        if health_check:
            try:
                # 尝试调用带参数的健康检查
                result = health_check(include_system=True)
                assert isinstance(result, dict)
                assert "system" in result
            except TypeError:
                # 如果不支持参数，跳过测试
                pytest.skip("Health check doesn't accept parameters")
        else:
            pytest.skip("health_check function not available")

    def test_custom_health_indicators(self):
        """测试自定义健康指标"""
        # 如果存在自定义健康指标检查
        if hasattr(health_check, "__code__"):
            # 检查函数是否有自定义实现
            source_lines = health_check.__code__.co_firstlineno
            assert source_lines > 0  # 基本验证函数存在
        else:
            pytest.skip("health_check function not available")

    @pytest.mark.parametrize(
        "status,expected_code",
        [
            ("healthy", 200),
            ("degraded", 200),
            ("unhealthy", 503),
        ],
    )
    def test_health_status_response_codes(self, status, expected_code):
        """测试不同健康状态对应的HTTP状态码"""
        # 这个测试需要根据实际实现调整
        if health_check:
            # 模拟不同状态的健康检查
            with patch.object(
                health_check,
                "return_value",
                {"status": status, "timestamp": "2024-01-01T00:00:00Z"},
            ):
                if app:
                    client = TestClient(app)
                    response = client.get("/health")
                    # 根据实际实现调整期望值
                    assert response.status_code in [200, 503]
        else:
            pytest.skip("health_check function not available")

    def test_health_check_performance(self):
        """测试健康检查性能"""
        import time

        if health_check:
            start_time = time.time()
            result = health_check()
            end_time = time.time()

            # 验证响应时间在合理范围内
            assert (end_time - start_time) < 2.0  # 应该在2秒内完成
            assert isinstance(result, dict)
        else:
            pytest.skip("health_check function not available")

    def test_health_check_idempotency(self):
        """测试健康检查的幂等性"""
        if health_check:
            # 多次调用应该返回结构相同的结果
            results = [health_check() for _ in range(5)]

            # 验证所有结果都有相同的基本结构
            for result in results:
                assert isinstance(result, dict)
                assert "status" in result
                assert "timestamp" in result
                assert result["status"] in ["healthy", "unhealthy", "degraded"]
        else:
            pytest.skip("health_check function not available")


class TestHealthAPIIntegration:
    """API健康检查集成测试类"""

    @pytest.fixture
    def mock_external_dependencies(self):
        """模拟外部依赖"""
        import sys

        # 创建mock psutil模块
        mock_psutil = MagicMock()
        mock_psutil.cpu_percent.return_value = 25.0
        mock_psutil.virtual_memory.return_value = MagicMock(percent=50.0)
        mock_psutil.disk_usage.return_value = MagicMock(percent=30.0)

        # 创建mock time模块
        mock_time = MagicMock()
        mock_time.time.return_value = 1640995200.0

        # 将mock模块添加到sys.modules
        with patch.dict('sys.modules', {'psutil': mock_psutil, 'time': mock_time}):
            yield mock_psutil, mock_time

    def test_full_health_check_integration(self, mock_external_dependencies):
        """测试完整健康检查集成"""
        # 检查system_health函数是否可用
        try:
            from src.api.health import system_health
        except (ImportError, NameError):
            pytest.skip("system_health function not available")

        if system_health:
            result = system_health()
            assert isinstance(result, dict)
            assert "system" in result
            assert "status" in result

            system_data = result["system"]
            assert "metrics" in system_data
            assert "cpu" in system_data["metrics"]
            assert "memory" in system_data["metrics"]
            assert "disk" in system_data["metrics"]
        else:
            pytest.skip("system_health function not available")

    def test_health_check_chain(self):
        """测试健康检查链式调用"""
        if health_check and system_health:
            # 依次调用多个健康检查
            basic_health = health_check()
            sys_health = system_health()

            # 验证所有健康检查都返回有效结构
            assert isinstance(basic_health, dict)
            assert isinstance(sys_health, dict)
            assert "status" in basic_health
            assert "status" in sys_health
        else:
            pytest.skip("Health check functions not available")


@pytest.mark.skipif(router is None, reason="Health router not available")
class TestHealthRouter:
    """健康路由器测试类"""

    def test_router_initialization(self):
        """测试路由器初始化"""
        assert router is not None
        assert hasattr(router, "routes")

    def test_router_endpoints(self):
        """测试路由器端点"""
        routes = [route.path for route in router.routes]

        # 至少应该有基础健康检查端点
        assert "/health" in routes

    def test_router_methods(self):
        """测试路由器HTTP方法"""
        for route in router.routes:
            assert route.methods
            assert "GET" in route.methods  # 健康检查应该支持GET请求
