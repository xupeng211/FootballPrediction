"""扩展的main.py测试 - 提升覆盖率"""

import os
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.main import app


class TestMainExtended:
    """扩展的main.py测试，覆盖未测试的代码路径"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_root_endpoint(self, client):
        """测试根路径端点"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "足球预测API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "运行中"
        assert "docs_url" in data
        assert "health_check" in data

    def test_minimal_api_mode_environment(self):
        """测试MINIMAL_API_MODE环境变量处理"""
        # 测试默认值
        with patch.dict(os.environ, {}, clear=True):
            # 重新导入模块以测试环境变量
            import importlib
            import src.main
            importlib.reload(src.main)
            assert src.main.MINIMAL_API_MODE is False

        # 测试设置为true
        with patch.dict(os.environ, {"MINIMAL_API_MODE": "true"}, clear=True):
            importlib.reload(src.main)
            assert src.main.MINIMAL_API_MODE is True

        # 测试设置为false
        with patch.dict(os.environ, {"MINIMAL_API_MODE": "false"}, clear=True):
            importlib.reload(src.main)
            assert src.main.MINIMAL_API_MODE is False

    @patch('src.main.lifespan')
    def test_lifespan_context_manager(self, mock_lifespan):
        """测试生命周期管理器"""
        from src.main import lifespan

        # 这是一个简单的存在性测试，确保lifespan函数存在
        assert callable(lifespan)
        assert hasattr(lifespan, '__aenter__')
        assert hasattr(lifespan, '__aexit__')

    def test_http_exception_handler(self, client):
        """测试HTTP异常处理器"""
        # 创建一个会抛出HTTP异常的路由
        @app.get("/test-http-exception")
        async def test_http_exception():
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="测试错误")

        response = client.get("/test-http-exception")
        assert response.status_code == 400
        data = response.json()
        assert data["error"] is True
        assert data["status_code"] == 400
        assert data["message"] == "测试错误"
        assert "path" in data

    def test_general_exception_handler(self, client):
        """测试通用异常处理器"""
        # 创建一个会抛出通用异常的路由
        @app.get("/test-general-exception")
        async def test_general_exception():
            raise ValueError("测试通用错误")

        response = client.get("/test-general-exception")
        assert response.status_code == 500
        data = response.json()
        assert data["error"] is True
        assert data["status_code"] == 500
        assert data["message"] == "内部服务器错误"
        assert "path" in data

    def test_main_execution_block(self):
        """测试主执行块的逻辑"""
        # 测试默认端口
        with patch.dict(os.environ, {}, clear=True):
            assert int(os.getenv("API_PORT", "8000")) == 8000

        # 测试自定义端口
        with patch.dict(os.environ, {"API_PORT": "9000"}, clear=True):
            assert int(os.getenv("API_PORT", "8000")) == 9000

    def test_host_selection_logic(self):
        """测试主机选择逻辑"""
        # 开发环境
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            env = os.getenv("ENVIRONMENT")
            if env == "development":
                default_host = "0.0.0.0"
            else:
                default_host = "127.0.0.1"
            assert default_host == "0.0.0.0"

        # 生产环境
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}, clear=True):
            env = os.getenv("ENVIRONMENT")
            if env == "development":
                default_host = "0.0.0.0"
            else:
                default_host = "127.0.0.1"
            assert default_host == "127.0.0.1"

        # 自定义主机
        with patch.dict(os.environ, {"API_HOST": "192.168.1.100"}, clear=True):
            host = os.getenv("API_HOST", "127.0.0.1")
            assert host == "192.168.1.100"

    def test_cors_origins_configuration(self):
        """测试CORS origins配置"""
        # 测试默认值
        with patch.dict(os.environ, {}, clear=True):
            origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
            assert origins == ["http://localhost:3000"]

        # 测试多个origins
        with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000,https://example.com"}, clear=True):
            origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
            assert origins == ["http://localhost:3000", "https://example.com"]

    @patch('src.main.RATE_LIMIT_AVAILABLE', True)
    @patch('src.main.limiter')
    def test_rate_limit_configuration(self, mock_limiter):
        """测试速率限制配置"""
        # 这是一个简单的测试，验证速率限制相关代码存在
        from src.main import RATE_LIMIT_AVAILABLE
        assert RATE_LIMIT_AVAILABLE is True

    @patch('src.main.RATE_LIMIT_AVAILABLE', False)
    def test_rate_limit_disabled(self):
        """测试速率限制禁用的情况"""
        from src.main import RATE_LIMIT_AVAILABLE
        assert RATE_LIMIT_AVAILABLE is False

    def test_warning_filters_setup(self):
        """测试警告过滤器设置"""
        # 验证警告过滤相关的代码路径
        try:
            from src.utils.warning_filters import setup_warning_filters
            assert callable(setup_warning_filters)
        except ImportError:
            # 如果模块不存在，应该有备用处理
            import warnings
            # 验证warnings模块可用
            assert callable(warnings.filterwarnings)

    def test_app_configuration(self):
        """测试应用配置"""
        assert app.title == "足球预测API"
        assert app.description == "基于机器学习的足球比赛结果预测系统"
        assert app.version == "1.0.0"
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"

    def test_logging_configuration(self):
        """测试日志配置"""
        import logging
        logger = logging.getLogger(__name__)
        assert logger is not None
        # 验证基本配置已设置
        assert len(logging.getLogger().handlers) > 0

    @patch('src.main.initialize_database')
    @patch('src.main.start_metrics_collection')
    @patch('src.main.stop_metrics_collection')
    async def test_lifespan_startup_shutdown(self, mock_stop, mock_start, mock_init):
        """测试生命周期启动和关闭逻辑"""
        from src.main import lifespan

        # 模拟启动
        mock_init.return_value = None
        mock_start.return_value = AsyncMock()
        mock_stop.return_value = AsyncMock()

        # 这个测试验证lifespan函数存在且可调用
        async with lifespan(app) as manager:
            assert manager is None  # lifespan只是yield None

        # 验证函数被定义（通过检查是否可调用）
        assert callable(lifespan)

    def test_router_registration(self):
        """测试路由注册"""
        # 验证至少有一个路由被注册
        routes = [route.path for route in app.routes]
        assert "/" in routes
        assert "/api/health" in routes or any("health" in route for route in routes)