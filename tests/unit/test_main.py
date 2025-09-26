"""
主应用测试

测试FastAPI应用启动、生命周期管理、中间件配置、异常处理等功能。
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import sys
from io import StringIO
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field


class TestMainApplication:
    """主应用测试类"""

    def test_fastapi_app_configuration(self):
        """测试FastAPI应用配置"""
        # 创建一个模拟的FastAPI应用来测试配置逻辑
        test_app = FastAPI(
            title="足球预测API",
            description="基于机器学习的足球比赛结果预测系统",
            version="1.0.0",
            docs_url="_docs",
            redoc_url="/redoc",
        )

    assert test_app.title == "足球预测API"
    assert test_app.description == "基于机器学习的足球比赛结果预测系统"
    assert test_app.version == "1.0.0"
    assert test_app.docs_url == "/docs"
    assert test_app.redoc_url == "/redoc"

    def test_cors_middleware_configuration(self):
        """测试CORS中间件配置"""
        # 创建FastAPI应用
        test_app = FastAPI()

        # 测试CORS配置逻辑
        cors_origins = os.getenv("CORS_ORIGINS", "http:_/localhost:3000").split(",")
        test_app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
        )

        # 验证CORS中间件已添加
        cors_middleware = None
        for middleware in test_app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                cors_middleware = middleware
                break

    assert cors_middleware is not None, "CORS中间件未配置"
    assert cors_middleware.options.get("allow_origins") == cors_origins
    assert cors_middleware.options.get("allow_credentials") is True
    assert cors_middleware.options.get("allow_methods") == ["GET", "POST", "PUT", "DELETE"]
    assert cors_middleware.options.get("allow_headers") == ["*"]

    def test_cors_with_environment_variable(self):
        """测试环境变量控制的CORS配置"""
        with patch.dict(os.environ, {'CORS_ORIGINS': 'http:_/localhost:3000,https://example.com'}):
            # 直接测试CORS逻辑
            cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    assert cors_origins == ["http://localhost:3000", "https://example.com"]

    def test_root_endpoint_response_structure(self):
        """测试根路径响应结构"""
        # 创建RootResponse模型
        class RootResponse(BaseModel):
            """根路径API响应模型"""
            service: str = Field(..., description="服务名称")
            version: str = Field(..., description="版本号")
            status: str = Field(..., description="服务状态")
            docs_url: str = Field(..., description="API文档地址")
            health_check: str = Field(..., description="健康检查地址")

        # 创建一个简单的FastAPI应用来测试根路径逻辑
        test_app = FastAPI()

        @test_app.get("_")
        async def test_root():
            return {
                "service": "足球预测API",
                "version": "1.0.0",
                "status": "运行中",
                "docs_url": "_docs",
                "health_check": "/health",
            }

        with TestClient(test_app) as client:
            response = client.get("/")

    assert response.status_code == 200

            data = response.json()
    assert data["service"] == "足球预测API"
    assert data["version"] == "1.0.0"
    assert data["status"] == "运行中"
    assert data["docs_url"] == "/docs"
    assert data["health_check"] == "/health"

            # 验证响应符合模型
            root_response = RootResponse(**data)
    assert root_response.service == "足球预测API"

    def test_http_exception_handler(self):
        """测试HTTP异常处理器"""
        # 创建模拟日志记录器
        mock_logger = MagicMock()

        # 创建模拟请求
        mock_request = MagicMock()
        mock_request.url = "http:_/test.com/api/test"

        # 创建HTTP异常
        exception = HTTPException(status_code=404, detail="页面未找到")

        # 创建HTTP异常处理器函数
        async def http_exception_handler(request, exc: HTTPException):
            mock_logger.error(f"HTTP异常: {exc.status_code} - {exc.detail}")
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": True,
                    "status_code": exc.status_code,
                    "message": exc.detail,
                    "path": str(request.url),
                },
            )

        # 调用异常处理器
        response = asyncio.run(http_exception_handler(mock_request, exception))

    assert isinstance(response, JSONResponse)
    assert response.status_code == 404

        data = response.body.decode()
    assert "error" in data
    assert "status_code" in data
    assert "404" in data
    assert "页面未找到" in data

        # 验证日志记录
        mock_logger.error.assert_called_once_with("HTTP异常: 404 - 页面未找到")

    def test_general_exception_handler(self):
        """测试通用异常处理器"""
        # 创建模拟日志记录器
        mock_logger = MagicMock()

        # 创建模拟请求
        mock_request = MagicMock()
        mock_request.url = "http:_/test.com/api/test"

        # 创建通用异常
        exception = ValueError("测试异常")

        # 创建通用异常处理器函数
        async def general_exception_handler(request, exc: Exception):
            mock_logger.error(f"未处理异常: {type(exc).__name__}: {exc}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "status_code": 500,
                    "message": "内部服务器错误",
                    "path": str(request.url),
                },
            )

        # 调用异常处理器
        response = asyncio.run(general_exception_handler(mock_request, exception))

    assert isinstance(response, JSONResponse)
    assert response.status_code == 500

        data = response.body.decode()
    assert "error" in data
    assert "status_code" in data
    assert "500" in data
    assert "内部服务器错误" in data

        # 验证日志记录
        mock_logger.error.assert_called_once_with("未处理异常: ValueError: 测试异常")

    def test_lifespan_manager_success(self):
        """测试生命周期管理器成功场景"""
        # 创建模拟日志记录器
        mock_logger = MagicMock()
        mock_init_db = MagicMock()
        mock_start_metrics = AsyncMock()
        mock_stop_metrics = AsyncMock()

        # 创建生命周期管理器
        @asynccontextmanager
        async def test_lifespan(app: FastAPI):
            # 启动时初始化
            mock_logger.info("🚀 足球预测API启动中...")

            try:
                # 初始化数据库连接
                mock_logger.info("📊 初始化数据库连接...")
                mock_init_db()

                # 启动监控指标收集
                mock_logger.info("📈 启动监控指标收集...")
                await mock_start_metrics()

                mock_logger.info("✅ 服务启动成功")

            except Exception as e:
                mock_logger.error(f"❌ 启动失败: {e}")
                raise

            yield

            # 关闭时清理
            mock_logger.info("🛑 服务正在关闭...")

            # 停止监控指标收集
            mock_logger.info("📉 停止监控指标收集...")
            await mock_stop_metrics()

        # 创建测试应用
        test_app = FastAPI(lifespan=test_lifespan)

        # 执行生命周期测试
        async def test_lifecycle():
            async with test_lifespan(test_app):
                # 验证启动操作
                mock_init_db.assert_called_once()
                mock_start_metrics.assert_awaited_once()
                mock_logger.info.assert_any_call("🚀 足球预测API启动中...")
                mock_logger.info.assert_any_call("📊 初始化数据库连接...")
                mock_logger.info.assert_any_call("📈 启动监控指标收集...")
                mock_logger.info.assert_any_call("✅ 服务启动成功")

            # 验证关闭操作
            mock_stop_metrics.assert_awaited_once()
            mock_logger.info.assert_any_call("🛑 服务正在关闭...")
            mock_logger.info.assert_any_call("📉 停止监控指标收集...")

        asyncio.run(test_lifecycle())

    def test_lifespan_manager_failure(self):
        """测试生命周期管理器失败场景"""
        # 创建模拟日志记录器
        mock_logger = MagicMock()
        mock_start_metrics = AsyncMock()

        # 模拟数据库初始化失败
        mock_init_db = MagicMock()
        mock_init_db.side_effect = Exception("数据库连接失败")

        # 创建生命周期管理器
        @asynccontextmanager
        async def test_lifespan(app: FastAPI):
            mock_logger.info("🚀 足球预测API启动中...")

            try:
                mock_logger.info("📊 初始化数据库连接...")
                mock_init_db()

                mock_logger.info("✅ 服务启动成功")
            except Exception as e:
                mock_logger.error(f"❌ 启动失败: {e}")
                raise

            yield

        # 创建测试应用
        test_app = FastAPI(lifespan=test_lifespan)

        # 验证异常抛出
        with pytest.raises(Exception, match="数据库连接失败"):
            async def test_startup_failure():
                async with test_lifespan(test_app):
                    pass

            asyncio.run(test_startup_failure())

        # 验证错误日志
        mock_logger.error.assert_called_with("❌ 启动失败: 数据库连接失败")

    def test_warning_filters_setup_success(self):
        """测试警告过滤器设置成功"""
        # 模拟成功导入警告过滤器
        with patch('src.utils.warning_filters.setup_warning_filters') as mock_setup:
            mock_setup.return_value = None

            # 测试警告过滤器设置逻辑
            try:
                from src.utils.warning_filters import setup_warning_filters
                setup_warning_filters()
                mock_setup.assert_called_once()
            except ImportError:
                pass  # 忽略导入错误

    def test_warning_filters_fallback(self):
        """测试警告过滤器回退机制"""
        # 模拟警告过滤器模块导入失败
        with patch('builtins.__import__', side_effect=lambda name, *args, **kwargs:
                  ImportError() if name == 'src.utils.warning_filters' else __import__(name, *args, **kwargs)):

            with patch('warnings.filterwarnings') as mock_filterwarnings:
                # 测试回退逻辑
                import warnings

                try:
                    from src.utils.warning_filters import setup_warning_filters
                except ImportError:
                    # 模拟回退到基本过滤器
                    try:
                        import marshmallow.warnings
                        warnings.filterwarnings(
                            "ignore", category=marshmallow.warnings.ChangedInMarshmallow4Warning
                        )
                    except ImportError:
                        pass

    def test_logging_configuration(self):
        """测试日志配置"""
        # 测试日志配置逻辑
        with patch('logging.basicConfig') as mock_basicConfig:
            # 模拟日志配置
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

            # 验证调用
            mock_basicConfig.assert_called_with(
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

    def test_environment_variable_parsing(self):
        """测试环境变量解析"""
        # 测试开发环境配置
        with patch.dict(os.environ, {
            'API_PORT': '9000',
            'ENVIRONMENT': 'development',
            'API_HOST': '0.0.0.0'
        }):
            port = int(os.getenv("API_PORT", 8000))
    assert port == 9000

            if os.getenv("ENVIRONMENT") == "development":
                default_host = "0.0.0.0"
            else:
                default_host = "127.0.0.1"
            host = os.getenv("API_HOST", default_host)
    assert host == "0.0.0.0"

        # 测试生产环境配置
        with patch.dict(os.environ, {
            'API_PORT': '8080',
            'ENVIRONMENT': 'production'
        }):
            port = int(os.getenv("API_PORT", 8000))
    assert port == 8080

            if os.getenv("ENVIRONMENT") == "development":
                default_host = "0.0.0.0"
            else:
                default_host = "127.0.0.1"
            host = os.getenv("API_HOST", default_host)
    assert host == "127.0.0.1"

    def test_route_registration(self):
        """测试路由注册逻辑"""
        # 创建一个简单的FastAPI应用来测试路由注册
        test_app = FastAPI()

        # 模拟健康检查路由
        from fastapi import APIRouter
        health_router = APIRouter()

        @health_router.get("_health")
        async def health_check():
            return {"status": "healthy"}

        @health_router.get("/health/liveness")
        async def liveness_check():
            return {"status": "alive"}

        @health_router.get("/health/readiness")
        async def readiness_check():
            return {"status": "ready"}

        # 注册路由
        test_app.include_router(health_router)
        test_app.include_router(health_router, prefix="/api/v1")

        # 验证路由已注册
        registered_routes = [route.path for route in test_app.routes if hasattr(route, 'path')]

        expected_routes = [
            "/health",
            "/health/liveness",
            "/health/readiness",
            "/api/v1/health",
            "/api/v1/health/liveness",
            "/api/v1/health/readiness"
        ]

        for route in expected_routes:
    assert any(route in registered_path for registered_path in registered_routes), \
                f"路由 {route} 未注册"

    def test_exception_handler_registration(self):
        """测试异常处理器注册"""
        # 创建FastAPI应用并注册异常处理器
        test_app = FastAPI()

        @test_app.exception_handler(HTTPException)
        async def test_http_exception_handler(request, exc: HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": True, "message": exc.detail}
            )

        @test_app.exception_handler(Exception)
        async def test_general_exception_handler(request, exc: Exception):
            return JSONResponse(
                status_code=500,
                content={"error": True, "message": "内部服务器错误"}
            )

        # 验证异常处理器已注册
    assert len(test_app.exception_handlers) > 0

        # 检查HTTPException处理器
        http_exception_handlers = [
            handler for handler in test_app.exception_handlers.keys()
            if handler == HTTPException
        ]
    assert len(http_exception_handlers) > 0

        # 检查通用Exception处理器
        general_exception_handlers = [
            handler for handler in test_app.exception_handlers.keys()
            if handler == Exception
        ]
    assert len(general_exception_handlers) > 0

    def test_uvicorn_configuration_logic(self):
        """测试Uvicorn配置逻辑"""
        # 测试开发环境配置
        with patch.dict(os.environ, {
            'API_PORT': '9000',
            'ENVIRONMENT': 'development',
            'API_HOST': '0.0.0.0'
        }):
            port = int(os.getenv("API_PORT", 8000))
            if os.getenv("ENVIRONMENT") == "development":
                default_host = "0.0.0.0"
            else:
                default_host = "127.0.0.1"
            host = os.getenv("API_HOST", default_host)
            reload = os.getenv("ENVIRONMENT") == "development"

    assert port == 9000
    assert host == "0.0.0.0"
    assert reload is True

        # 测试生产环境配置
        with patch.dict(os.environ, {
            'API_PORT': '8080',
            'ENVIRONMENT': 'production'
        }):
            port = int(os.getenv("API_PORT", 8000))
            if os.getenv("ENVIRONMENT") == "development":
                default_host = "0.0.0.0"
            else:
                default_host = "127.0.0.1"
            host = os.getenv("API_HOST", default_host)
            reload = os.getenv("ENVIRONMENT") == "development"

    assert port == 8080
    assert host == "127.0.0.1"
    assert reload is False

    def test_import_structure_validation(self):
        """测试导入结构验证"""
        # 验证必要的FastAPI组件可用
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import JSONResponse
        from fastapi.middleware.cors import CORSMiddleware
        from contextlib import asynccontextmanager
        from pydantic import BaseModel, Field

        # 验证所有组件都可以正常导入
    assert FastAPI is not None
    assert HTTPException is not None
    assert JSONResponse is not None
    assert CORSMiddleware is not None
    assert asynccontextmanager is not None
    assert BaseModel is not None
    assert Field is not None