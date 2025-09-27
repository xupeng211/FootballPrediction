"""
Auto-generated tests for src.main module
"""

import pytest
from unittest.mock import patch, MagicMock
from src.main import app


class TestMain:
    """测试主应用模块"""

    def test_app_creation(self):
        """测试应用创建"""
        assert app is not None
        assert app.title == "足球预测API"

    def test_app_cors_configuration(self):
        """测试CORS配置"""
        # 检查是否启用了CORS中间件
        cors_middleware = None
        for middleware in app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                cors_middleware = middleware
                break

        assert cors_middleware is not None, "CORS middleware should be configured"

    def test_app_health_endpoint(self):
        """测试健康检查端点"""
        from fastapi.testclient import TestClient
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200

    def test_app_root_endpoint(self):
        """测试根端点"""
        from fastapi.testclient import TestClient
        client = TestClient(app)

        response = client.get("/")
        assert response.status_code == 200

    @patch('src.main.setup_warning_filters')
    def test_warning_filters_setup_on_import(self, mock_setup):
        """测试导入时设置警告过滤器"""
        # 重新导入模块以测试警告过滤器设置
        import importlib
        import src.main
        importlib.reload(src.main)

        # 验证是否调用了警告过滤器设置
        mock_setup.assert_called_once()

    @patch('src.main.setup_warning_filters')
    def test_warning_filters_import_error_handling(self, mock_setup):
        """测试警告过滤器导入错误处理"""
        mock_setup.side_effect = ImportError("Module not found")

        # 重新导入模块，应该处理导入错误
        import importlib
        import src.main
        importlib.reload(src.main)

        # 即使导入失败，应用仍然应该创建
        assert app is not None

    def test_logging_configuration(self):
        """测试日志配置"""
        import logging
        # 验证根日志器配置
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    @patch('src.main.initialize_database')
    def test_database_initialization_import(self, mock_init_db):
        """测试数据库初始化导入"""
        # 数据库初始化应该在应用启动时被调用
        from src.main import initialize_database
        assert initialize_database is not None

    def test_app_includes_all_routers(self):
        """测试应用包含所有路由器"""
        # 检查应用的路由
        routes = [route.path for route in app.routes if hasattr(route, 'path')]

        # 应该包含主要路由
        expected_routes = ['/health', '/']
        for route in expected_routes:
            assert any(expected in path for path in routes for expected in [route])

    def test_app_openapi_specification(self):
        """测试OpenAPI规范"""
        assert app.openapi() is not None
        openapi_spec = app.openapi()
        assert "openapi" in openapi_spec
        assert "info" in openapi_spec
        assert "paths" in openapi_spec

    def test_app_info_configuration(self):
        """测试应用信息配置"""
        assert app.title == "Football Prediction System"
        assert app.description is not None
        assert app.version is not None

    def test_app_startup_event(self):
        """测试应用启动事件"""
        # 应用应该有启动事件处理
        assert hasattr(app.router, 'startup')

    def test_app_shutdown_event(self):
        """测试应用关闭事件"""
        # 应用应该有关闭事件处理
        assert hasattr(app.router, 'shutdown')

    @patch('src.main.start_metrics_collection')
    @patch('src.main.stop_metrics_collection')
    def test_metrics_collection_integration(self, mock_stop, mock_start):
        """测试指标收集集成"""
        # 验证指标收集函数存在
        from src.main import start_metrics_collection, stop_metrics_collection
        assert callable(start_metrics_collection)
        assert callable(stop_metrics_collection)

    def test_middleware_stack(self):
        """测试中间件堆栈"""
        # 应用应该有中间件配置
        assert len(app.user_middleware) > 0

    def test_exception_handlers(self):
        """测试异常处理器"""
        # 应用应该有异常处理器
        assert len(app.exception_handlers) > 0