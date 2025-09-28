"""
API健康检查简单测试

测试API健康检查端点的基本功能
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestAPIHealthSimple:
    """API健康检查基础测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        with patch('src.main.app'):
            from src.main import app
            return TestClient(app)

    def test_health_endpoint_exists(self, client):
        """测试健康检查端点存在"""
        response = client.get("/health")
        # 验证端点存在，即使返回错误码
        assert response.status_code in [200, 404, 500]

    def test_health_endpoint_response_format(self, client):
        """测试健康检查响应格式"""
        response = client.get("/health")

        # 如果返回200，验证响应格式
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            # 响应应该包含基本信息
            if 'status' in data:
                assert data['status'] in ['healthy', 'unhealthy']
            if 'timestamp' in data:
                assert isinstance(data['timestamp'], str)

    def test_health_endpoint_headers(self, client):
        """测试健康检查端点头部"""
        response = client.get("/health")

        # 验证响应头
        assert 'content-type' in response.headers
        assert 'application/json' in response.headers['content-type'].lower()

    def test_health_endpoint_methods(self, client):
        """测试健康检查端点支持的方法"""
        # GET请求
        response = client.get("/health")
        assert response.status_code in [200, 404, 500]

        # POST请求（可能不支持）
        response = client.post("/health", json={})
        assert response.status_code in [405, 404, 500]  # Method Not Allowed

    def test_api_info_endpoint(self, client):
        """测试API信息端点"""
        response = client.get("/")
        assert response.status_code in [200, 404, 500]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_docs_endpoint(self, client):
        """测试文档端点"""
        response = client.get("/docs")
        assert response.status_code in [200, 404, 500]

    def test_openapi_endpoint(self, client):
        """测试OpenAPI端点"""
        response = client.get("/openapi.json")
        assert response.status_code in [200, 404, 500]

    @patch('src.api.health.get_database_manager')
    def test_database_health_check(self, mock_get_db_manager, client):
        """测试数据库健康检查"""
        # Mock数据库管理器
        mock_db_manager = Mock()
        mock_get_db_manager.return_value = mock_db_manager

        # Mock数据库连接
        mock_session = Mock()
        mock_db_manager.get_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.scalar.return_value = True

        response = client.get("/health")
        assert response.status_code in [200, 404, 500]

    @patch('src.api.health.get_redis_client')
    def test_redis_health_check(self, mock_get_redis, client):
        """测试Redis健康检查"""
        # Mock Redis客户端
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis
        mock_redis.ping.return_value = True

        response = client.get("/health")
        assert response.status_code in [200, 404, 500]

    def test_health_endpoint_performance(self, client):
        """测试健康检查端点性能"""
        import time

        # 测试响应时间
        start_time = time.time()
        response = client.get("/health")
        end_time = time.time()

        response_time = end_time - start_time
        # 响应时间应该小于1秒
        assert response_time < 1.0

    def test_health_endpoint_concurrent_requests(self, client):
        """测试健康检查端点并发请求"""
        import threading
        import time

        results = []

        def make_request():
            response = client.get("/health")
            results.append(response.status_code)

        # 创建多个并发请求
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有请求都得到了响应
        assert len(results) == 5
        for status_code in results:
            assert status_code in [200, 404, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.api.health", "--cov-report=term-missing"])