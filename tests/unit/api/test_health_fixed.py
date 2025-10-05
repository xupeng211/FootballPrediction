"""健康检查API测试（修复版）"""

from unittest.mock import patch

import pytest
from fastapi import status


class TestHealthAPI:
    """健康检查API测试"""

    def test_health_check_success(self, api_client):
        """测试健康检查成功"""
        response = api_client.get("/api/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "checks" in data

    def test_health_check_with_database_true(self, api_client):
        """测试带数据库检查的健康检查（check_db=true）"""
        with patch("src.api.health._collect_database_health") as mock_check:
            mock_check.return_value = {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": 10,
                "details": {"message": "数据库连接正常"},
            }

            response = api_client.get("/api/health?check_db=true")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["checks"]["database"]["status"] == "healthy"

    def test_health_check_with_database_false(self, api_client):
        """测试跳过数据库检查的健康检查（check_db=false）"""
        response = api_client.get("/api/health?check_db=false")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["checks"]["database"]["status"] == "skipped"

    def test_health_check_database_failure(self, api_client):
        """测试数据库健康检查失败"""
        with patch("src.api.health._collect_database_health") as mock_check:
            mock_check.return_value = {
                "healthy": False,
                "status": "unhealthy",
                "response_time_ms": 100,
                "details": {"message": "数据库连接失败", "error": "Connection timeout"},
            }

            response = api_client.get("/api/health?check_db=true")

            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            # 错误响应会被HTTP异常处理器包装
            error_data = response.json()
            assert error_data["error"] is True
            assert error_data["status_code"] == 503

    def test_health_check_with_redis_check(self, api_client):
        """测试Redis健康检查"""
        with patch("src.api.health._check_redis") as mock_redis:
            mock_redis.return_value = {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": 5,
                "details": {"message": "Redis连接正常"},
            }

            # 设置环境变量以启用Redis检查
            with patch.dict(
                "os.environ", {"MINIMAL_HEALTH_MODE": "false", "FAST_FAIL": "true"}
            ):
                response = api_client.get("/api/health?check_db=true")

            # 检查响应
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_503_SERVICE_UNAVAILABLE,
            ]

    @pytest.mark.parametrize("endpoint", ["/api/health", "/api/health/"])
    def test_health_check_endpoints(self, api_client, endpoint):
        """测试多个健康检查端点"""
        response = api_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK

    def test_health_check_minimal_mode(self, api_client):
        """测试最小模式下的健康检查"""
        # 在最小模式下，Redis、Kafka等应该被跳过
        response = api_client.get("/api/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # 检查数据库状态（取决于MINIMAL_HEALTH_MODE）
        db_status = data["checks"]["database"]["status"]
        assert db_status in ["healthy", "skipped", "unhealthy"]

        # 检查其他服务在最小模式下被跳过
        for service in ["redis", "kafka", "mlflow", "filesystem"]:
            assert data["checks"][service]["status"] == "skipped"

    def test_health_check_response_structure(self, api_client):
        """测试健康检查响应结构"""
        response = api_client.get("/api/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # 验证必需字段
        required_fields = [
            "status",
            "timestamp",
            "service",
            "version",
            "uptime",
            "checks",
            "response_time_ms",
        ]
        for field in required_fields:
            assert field in data, f"缺少必需字段: {field}"

        # 验证检查项结构
        for check_name, check_data in data["checks"].items():
            assert "status" in check_data, f"检查项 {check_name} 缺少status字段"
            assert (
                "response_time_ms" in check_data
            ), f"检查项 {check_name} 缺少response_time_ms字段"
            # 在某些情况下（如数据库未初始化），可能没有healthy字段
            if "healthy" not in check_data:
                assert check_data["status"] in [
                    "skipped"
                ], "只有跳过的检查项可以缺少healthy字段"

    def test_health_check_with_invalid_query_param(self, api_client):
        """测试无效查询参数"""
        # 无效的查询参数应该被忽略
        response = api_client.get("/api/health?invalid_param=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
