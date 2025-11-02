#!/usr/bin/env python3
"""
API健康检查测试
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from main import app
except ImportError:
    pytest.skip("主应用模块不可用", allow_module_level=True)


class TestHealthAPI:
    """API健康检查测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_health_endpoint_basic(self, client):
        """测试基础健康检查端点"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert data["status"] == "healthy"

    def test_health_endpoint_structure(self, client):
        """测试健康检查端点结构"""
        response = client.get("/health")
        data = response.json()

        # 验证必要字段存在
        required_fields = ["status", "version"]
        for field in required_fields:
            assert field in data, f"缺少必要字段: {field}"

        # 验证数据类型
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], str)

    def test_health_endpoint_database_status(self, client):
        """测试健康检查包含数据库状态"""
        response = client.get("/health")
        data = response.json()

        # 检查是否包含数据库状态信息
        if "database" in data:
            assert isinstance(data["database"], str)
            assert data["database"] in ["connected", "disconnected", "error"]

    @pytest.mark.critical
    def test_health_endpoint_response_time(self, client):
        """测试健康检查响应时间"""
        import time
        start_time = time.time()

        response = client.get("/health")

        response_time = time.time() - start_time
        assert response_time < 2.0, f"健康检查响应时间过长: {response_time:.2f}s"
        assert response.status_code == 200

    @pytest.mark.smoke
    def test_multiple_health_checks(self, client):
        """测试多次健康检查的一致性"""
        responses = []

        # 连续执行5次健康检查
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200
            responses.append(response.json())

        # 验证响应一致性
        first_response = responses[0]
        for response in responses[1:]:
            assert response["status"] == first_response["status"]
            assert response["version"] == first_response["version"]

    @pytest.mark.unit
    def test_health_endpoint_headers(self, client):
        """测试健康检查端点的响应头"""
        response = client.get("/health")

        # 验证内容类型
        assert "content-type" in response.headers
        assert "application/json" in response.headers["content-type"]


class TestHealthAPIErrorHandling:
    """健康检查API错误处理测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_invalid_method_not_allowed(self, client):
        """测试不支持的方法"""
        response = client.post("/health")
        assert response.status_code == 405

    def test_invalid_path_not_found(self, client):
        """测试不存在的路径"""
        response = client.get("/invalid-health")
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])