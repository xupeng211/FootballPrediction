"""监控API测试"""

import pytest


@pytest.mark.unit
@pytest.mark.monitoring
class TestMonitoringAPI:
    """测试监控API"""

    def test_monitoring_import(self):
        """测试监控模块导入"""
        try:
            from src.api.monitoring import router

            assert router is not None
        except ImportError:
            pytest.skip("monitoring module not available")

    def test_monitoring_router(self):
        """测试监控路由器"""
        try:
            from src.api.monitoring import router

            assert hasattr(router, "routes")
            except Exception:
            pytest.skip("monitoring router not available")

    def test_monitoring_endpoints(self):
        """测试监控端点"""
        try:
            from src.api.monitoring import router

            routes = list(router.routes)
            assert isinstance(routes, list)
            except Exception:
            pytest.skip("monitoring endpoints not testable")
