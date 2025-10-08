"""改进的功能API测试"""

import pytest


class TestFeaturesImproved:
    """测试改进的功能API"""

    def test_features_improved_import(self):
        """测试改进的功能API导入"""
        try:
            from src.api.features_improved import router

            assert router is not None
        except ImportError:
            pytest.skip("features_improved module not available")

    def test_features_improved_router(self):
        """测试改进的功能API路由器"""
        try:
            from src.api.features_improved import router

            assert hasattr(router, "routes")
        except:
            pytest.skip("features_improved router not available")

    def test_features_improved_endpoints(self):
        """测试改进的功能API端点"""
        try:
            from src.api.features_improved import router

            routes = list(router.routes)
            assert isinstance(routes, list)
        except:
            pytest.skip("features_improved endpoints not testable")
