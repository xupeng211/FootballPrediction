"""测试预测API模块"""

import pytest
from src.api.predictions import router


@pytest.mark.api
class TestPredictionsModule:
    """预测模块测试"""

    def test_import_router(self):
        """测试路由器导入"""
        assert router is not None
        assert hasattr(router, 'routes')

    def test_router_attributes(self):
        """测试路由器属性"""
        assert hasattr(router, 'prefix')
        assert hasattr(router, 'tags')

    def test_module_exports(self):
        """测试模块导出"""
        from src.api.predictions import __all__
        assert 'router' in __all__
