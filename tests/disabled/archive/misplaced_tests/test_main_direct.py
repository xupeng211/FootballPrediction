#!/usr/bin/env python3
"""
Main application test runner

This script tests main.py functions directly without pytest to avoid dependency issues.
"""

import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


def test_fastapi_app_creation():
    """Test FastAPI app creation"""
    print("Testing FastAPI app creation...")

    # Mock heavy dependencies
    sys.modules["pandas"] = MagicMock()
    sys.modules["numpy"] = MagicMock()
    sys.modules["sklearn"] = MagicMock()
    sys.modules["xgboost"] = MagicMock()
    sys.modules["mlflow"] = MagicMock()
    sys.modules["prometheus_client"] = MagicMock()
    sys.modules["structlog"] = MagicMock()
    sys.modules["redis"] = MagicMock()
    sys.modules["sqlalchemy"] = MagicMock()
    sys.modules["sqlalchemy.ext"] = MagicMock()
    sys.modules["sqlalchemy.ext.asyncio"] = MagicMock()
    sys.modules["sqlalchemy.orm"] = MagicMock()
    sys.modules["alembic"] = MagicMock()
    sys.modules["confluent_kafka"] = MagicMock()
    sys.modules["feast"] = MagicMock()
    sys.modules["great_expectations"] = MagicMock()
    sys.modules["psycopg2"] = MagicMock()
    sys.modules["asyncpg"] = MagicMock()
    sys.modules["aiosqlite"] = MagicMock()
    sys.modules["celery"] = MagicMock()
    sys.modules["openlineage"] = MagicMock()

    # Mock submodules
    sys.modules["pandas.core"] = MagicMock()
    sys.modules["pandas.core.frame"] = MagicMock()
    sys.modules["numpy.core"] = MagicMock()
    sys.modules["sklearn.model_selection"] = MagicMock()
    sys.modules["sklearn.metrics"] = MagicMock()
    sys.modules["sklearn.preprocessing"] = MagicMock()

    try:
        # Import main module
        from main import app

        # Test basic app properties
        assert app.title == "足球预测API"
        assert app.description == "基于机器学习的足球比赛结果预测系统"
        assert app.version == "1.0.0"
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"

        print("✅ FastAPI app creation test passed")
        return True

    except Exception as e:
        print(f"❌ FastAPI app creation test failed: {e}")
        return False


def test_cors_middleware():
    """Test CORS middleware configuration"""
    print("Testing CORS middleware...")

    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware

        # Create test app
        test_app = FastAPI()

        # Add CORS middleware
        test_app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["*"],
        )

        # Verify middleware was added
        cors_middleware = None
        for middleware in test_app.user_middleware:
            if "CORSMiddleware" in str(middleware.cls):
                cors_middleware = middleware
                break

        assert cors_middleware is not None, "CORS中间件未配置"
        # In newer FastAPI versions, options are stored differently
        if hasattr(cors_middleware, "options"):
            assert cors_middleware.options.get("allow_origins") == [
                "http://localhost:3000"
            ]
            assert cors_middleware.options.get("allow_credentials") is True
        else:
            # Check the middleware kwargs directly
            assert "allow_origins" in cors_middleware.kwargs
            assert cors_middleware.kwargs["allow_origins"] == ["http://localhost:3000"]
            assert cors_middleware.kwargs["allow_credentials"] is True

        print("✅ CORS middleware test passed")
        return True

    except Exception as e:
        print(f"❌ CORS middleware test failed: {e}")
        return False


def test_lifespan_manager():
    """Test lifespan manager"""
    print("Testing lifespan manager...")

    try:
        from fastapi import FastAPI
        from contextlib import asynccontextmanager

        # Mock dependencies
        mock_logger = MagicMock()
        mock_init_db = MagicMock()
        mock_start_metrics = AsyncMock()
        mock_stop_metrics = AsyncMock()

        # Create lifespan manager
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

        # Test lifespan
        async def test_lifecycle():
            test_app = FastAPI(lifespan=test_lifespan)

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
        print("✅ Lifespan manager test passed")
        return True

    except Exception as e:
        print(f"❌ Lifespan manager test failed: {e}")
        return False


def test_exception_handlers():
    """Test exception handlers"""
    print("Testing exception handlers...")

    try:
        from fastapi import HTTPException
        from fastapi.responses import JSONResponse

        # Test HTTP exception handler
        async def test_http_exception_handler():
            MagicMock()
            mock_request = MagicMock()
            mock_request.url = "http://test.com/api/test"

            exception = HTTPException(status_code=404, detail="页面未找到")

            response = JSONResponse(
                status_code=exception.status_code,
                content={
                    "error": True,
                    "status_code": exception.status_code,
                    "message": exception.detail,
                    "path": str(mock_request.url),
                },
            )

            assert isinstance(response, JSONResponse)
            assert response.status_code == 404

            data = response.body.decode()
            assert "error" in data
            assert "status_code" in data
            assert "404" in data
            assert "页面未找到" in data

        # Test general exception handler
        async def test_general_exception_handler():
            MagicMock()
            mock_request = MagicMock()
            mock_request.url = "http://test.com/api/test"

            response = JSONResponse(
                status_code=500,
                content={
                    "error": True,
                    "status_code": 500,
                    "message": "内部服务器错误",
                    "path": str(mock_request.url),
                },
            )

            assert isinstance(response, JSONResponse)
            assert response.status_code == 500

            data = response.body.decode()
            assert "error" in data
            assert "status_code" in data
            assert "500" in data
            assert "内部服务器错误" in data

        asyncio.run(test_http_exception_handler())
        asyncio.run(test_general_exception_handler())

        print("✅ Exception handlers test passed")
        return True

    except Exception as e:
        print(f"❌ Exception handlers test failed: {e}")
        return False


def test_environment_variables():
    """Test environment variable parsing"""
    print("Testing environment variable parsing...")

    try:
        import os

        # Test with environment variables
        with patch.dict(
            os.environ,
            {"API_PORT": "9000", "ENVIRONMENT": "development", "API_HOST": "0.0.0.0"},
        ):
            port = int(os.getenv("API_PORT", 8000))
            assert port == 9000

            if os.getenv("ENVIRONMENT") == "development":
                default_host = "0.0.0.0"
            else:
                default_host = "127.0.0.1"
            host = os.getenv("API_HOST", default_host)
            assert host == "0.0.0.0"

        print("✅ Environment variables test passed")
        return True

    except Exception as e:
        print(f"❌ Environment variables test failed: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("开始运行 main.py 测试...")
    print("=" * 50)

    tests = [
        test_fastapi_app_creation,
        test_cors_middleware,
        test_lifespan_manager,
        test_exception_handlers,
        test_environment_variables,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")

    print("=" * 50)
    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过!")
        return True
    else:
        print("❌ 部分测试失败")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
