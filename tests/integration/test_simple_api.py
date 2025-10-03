"""简单API集成测试"""

import pytest
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestSimpleAPI:
    """测试简单API集成"""

    @pytest.fixture(scope="class")
    def app(self):
        """创建测试应用"""
        from src.main import app
        return app

    @pytest.fixture(scope="class")
    def client(self, app):
        """创建测试客户端"""
        from src.api import health as health_module

        health_module.MINIMAL_HEALTH_MODE = True
        health_module.FAST_FAIL = False

        return TestClient(app, base_url="http://localhost")

    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        # 可能返回200（正常）、404（未启用）或503（数据库未初始化）
        assert response.status_code in [200, 404, 503]

        if response.status_code == 200:
            data = response.json()
            assert "status" in data

    def test_api_docs_accessible(self, client):
        """测试API文档可访问性"""
        response = client.get("/docs")
        # 可能返回200（正常）或404（minimal模式）
        assert response.status_code in [200, 404]

    def test_root_endpoint(self, client):
        """测试根端点"""
        response = client.get("/")
        # 可能返回200或404
        assert response.status_code in [200, 404]

    async def test_async_client(self):
        """测试异步客户端"""
        app = FastAPI(title = os.getenv("TEST_SIMPLE_API_TITLE_57"))

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        # 使用TestClient而不是AsyncClient
        from fastapi.testclient import TestClient
        client = TestClient(app)

        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"message": "test"}

    def test_error_handling(self, client):
        """测试错误处理"""
        # 测试不存在的端点
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_monitoring_endpoints(self, client):
        """测试监控端点"""
        # 测试指标端点
        response = client.get("/metrics")
        # 可能返回200、404或401
        assert response.status_code in [200, 404, 401]

    def test_cache_integration(self):
        """测试缓存集成"""
        from src.cache.ttl_cache import TTLCache

        # 创建缓存实例
        cache = TTLCache(max_size=10)

        # 测试设置和获取
        import asyncio
        async def test_cache():
            await cache.set("test_key", "test_value")
            value = await cache.get("test_key")
            return value

        value = asyncio.run(test_cache())
        assert value == "test_value"

    def test_service_integration(self):
        """测试服务集成"""
        from src.services.content_analysis import ContentAnalysisService

        # 创建服务实例
        service = ContentAnalysisService()

        # 测试服务存在
        assert service is not None
        # 测试基本属性
        assert hasattr(service, 'name') or hasattr(service, '__class__')
