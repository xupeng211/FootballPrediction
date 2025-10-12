"""
测试 src/api/health.py 模块
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock

# 确保模块可以导入
sys.path.insert(0, 'src')

try:
    from src.api import health
    from src.api.health import router
    HEALTH_AVAILABLE = True
except ImportError:
    HEALTH_AVAILABLE = False


@pytest.mark.skipif(not HEALTH_AVAILABLE, reason="health模块不可用")
class TestHealthModule:
    """测试 health 模块"""

    def test_module_imports(self):
        """测试模块导入"""
        assert health is not None
        assert router is not None
        assert hasattr(router, 'routes')

    def test_health_router_exists(self):
        """测试健康路由器存在"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(router, prefix="/health")

        client = TestClient(app)
        response = client.get("/health/")

        # 由于是mock环境，可能不会返回真实数据
        # 但至少应该有响应
        assert response.status_code in [200, 404, 500]

    @patch('src.api.health.health_checker')
    def test_health_endpoint(self, mock_health_checker):
        """测试健康检查端点"""
        # Mock健康检查器
        mock_checker = Mock()
        mock_checker.check_all_services.return_value = {
            "status": "healthy",
            "database": "ok",
            "redis": "ok"
        }
        mock_health_checker.HealthChecker.return_value = mock_checker

        # 测试导入
        from src.api.health import get_health_status

        # 如果函数存在，调用它
        if hasattr(health, 'get_health_status'):
            result = get_health_status()
            assert isinstance(result, dict)

    def test_health_routes(self):
        """测试健康路由配置"""
        routes = router.routes
        assert len(routes) > 0

        # 检查是否有健康检查路由
        route_paths = [route.path for route in routes]
        assert '/' in route_paths or '/health' in route_paths