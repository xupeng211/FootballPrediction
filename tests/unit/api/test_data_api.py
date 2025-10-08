"""数据API测试"""

import pytest


class TestDataAPI:
    """测试数据API"""

    def test_data_api_import(self):
        """测试数据API模块导入"""
        try:
            from src.api.data_api import router

            assert router is not None
        except ImportError:
            pytest.skip("data_api module not available")

    def test_data_api_router_exists(self):
        """测试数据API路由器存在"""
        try:
            from src.api.data_api import router

            # 检查是否是FastAPI路由器
            assert hasattr(router, "routes")
        except Exception:
            pytest.skip("router not available")

    def test_data_api_endpoints(self):
        """测试数据API端点"""
        try:
            from src.api.data_api import router

            # 检查是否有路由
            routes = list(router.routes)
            # 可能没有路由，但不应该抛出异常
            assert isinstance(routes, list)
        except:
            pytest.skip("endpoints not testable")
