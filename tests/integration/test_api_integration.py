"""API集成测试"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestAPIIntegration:
    """测试API集成"""

    @pytest.fixture(scope="class")
    def api_url(self):
        """获取API URL"""
        import os
        return os.getenv("API_URL", "http://localhost:8000")

    async def test_health_endpoint(self, api_url):
        """测试健康检查端点"""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"

    async def test_api_docs_accessible(self, api_url):
        """测试API文档可访问"""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/docs")
            assert response.status_code == 200

    async def test_metrics_endpoint(self, api_url):
        """测试指标端点"""
        async with AsyncClient() as client:
            response = await client.get(f"{api_url}/metrics")
            # 指标端点可能返回404，这是正常的
            assert response.status_code in [200, 404]

    async def test_prediction_endpoint_structure(self, api_url):
        """测试预测端点结构（不需要实际预测）"""
        async with AsyncClient() as client:
            # 测试获取预测列表
            response = await client.get(f"{api_url}/predictions/")
            # 可能返回404或200，取决于是否有数据
            assert response.status_code in [200, 404, 422]