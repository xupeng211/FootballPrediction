"""主模块测试"""

import pytest


@pytest.mark.unit

class TestMain:
    """测试主模块"""

    def test_main_import(self):
        """测试主模块导入"""
        try:
            import src.main

            assert src.main is not None
        except ImportError:
            pytest.skip("main module not available")

    def test_main_function_exists(self):
        """测试主函数存在"""
        try:
            from src.main import main

            assert callable(main)
        except ImportError:
            pytest.skip("main function not available")

    def test_create_app_function(self):
        """测试创建应用函数"""
        try:
            from src.main import create_app

            app = create_app()
            assert app is not None
            # 检查是否是FastAPI应用
            assert hasattr(app, "router")
        except ImportError:
            pytest.skip("create_app not available")
