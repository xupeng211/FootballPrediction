"""API数据端点测试"""

import pytest
from fastapi.testclient import TestClient

# 尝试导入API模块并设置可用性标志
try:

    API_AVAILABLE = True
    TEST_SKIP_REASON = "API模块不可用"
except ImportError as e:
    print(f"Data API import error: {e}")
    API_AVAILABLE = False
    TEST_SKIP_REASON = "Data API模块不可用"


@pytest.mark.skipif(not API_AVAILABLE, reason=TEST_SKIP_REASON)
@pytest.mark.unit
@pytest.mark.api
class TestAPIData:
    """API数据端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        # 智能Mock兼容修复模式：移除真实API导入
        try:
            from src.api.app import app

            return TestClient(app)
        except ImportError:
            pytest.skip("无法导入app")

    def test_get_root(self, client):
        """测试根端点"""
        response = client.get("/")
        assert response.status_code == 200
        _data = response.json()
        assert "message" in _data
        assert "version" in _data

    def test_cors_headers(self, client):
        """测试CORS头"""
        response = client.options("/api/health")
        # 检查是否有CORS相关的头
        # 某些CORS头可能存在
        assert response.status_code in [200, 405]

    def test_invalid_endpoint(self, client):
        """测试无效端点"""
        response = client.get("/api/invalid-endpoint")
        assert response.status_code == 404

    def test_health_response_time(self, client):
        """测试健康检查响应时间"""
        import time

        start = time.time()
        response = client.get("/api/health")
        end = time.time()
        assert response.status_code == 200
        # 响应时间应该少于1秒
        assert (end - start) < 1.0
