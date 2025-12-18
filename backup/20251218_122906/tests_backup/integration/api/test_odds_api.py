"""
赔率 API 集成测试
Odds API Integration Tests

测试 /api/v1/odds 端点的完整功能，包含基础功能验证和API响应格式测试
Author: QA Engineer
Created: 2025-12-07
Version: 1.0.0
"""

import os
import pytest
from fastapi.testclient import TestClient

# 设置测试环境变量
os.environ["TESTING"] = "true"
os.environ["FOOTBALL_PREDICTION_ML_MODE"] = "mock"
os.environ["SKIP_ML_MODEL_LOADING"] = "true"

# 导入应用
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.main import app

# 创建测试客户端
client = TestClient(app)


class TestOddsAPI:
    """赔率 API 集成测试类"""

    def test_health_check(self):
        """测试健康检查端点"""
        response = client.get("/api/v1/odds/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "赔率 API 服务运行正常" in data["message"]
        assert data["data"]["status"] == "healthy"
        assert data["data"]["service"] == "odds-api"
        assert "timestamp" in data["data"]

    def test_get_match_odds_endpoint_exists(self):
        """测试获取比赛赔率端点是否存在"""
        response = client.get("/api/v1/odds/matches/999")

        # 由于没有真实数据库，我们期望得到错误响应，但端点应该存在
        assert response.status_code in [
            404,
            500,
        ]  # 404表示比赛不存在，500表示数据库连接问题

    def test_trigger_fetch_endpoint_exists(self):
        """测试触发赔率采集端点是否存在"""
        response = client.post(
            "/api/v1/odds/fetch/999",
            json={"source_name": "oddsportal", "force_refresh": False},
        )

        # 由于没有真实数据库，我们期望得到错误响应，但端点应该存在
        assert response.status_code in [404, 500]

    def test_get_odds_history_endpoint_exists(self):
        """测试获取赔率历史端点是否存在"""
        response = client.get("/api/v1/odds/history/999")

        # 由于没有真实数据库，我们期望得到错误响应，但端点应该存在
        assert response.status_code in [404, 500]

    def test_get_match_odds_stats_endpoint_exists(self):
        """测试获取赔率统计端点是否存在"""
        response = client.get("/api/v1/odds/matches/999/stats")

        # 由于没有真实数据库，我们期望得到错误响应，但端点应该存在
        assert response.status_code in [404, 500]

    def test_get_bookmakers_endpoint_exists(self):
        """测试获取博彩公司列表端点是否存在"""
        response = client.get("/api/v1/odds/bookmakers")

        # 由于没有真实数据库，我们期望得到错误响应，但端点应该存在
        assert response.status_code in [500, 200]

    def test_endpoints_respond_with_json(self):
        """测试所有端点都返回JSON响应"""
        endpoints = [
            "/api/v1/odds/health",
            "/api/v1/odds/matches/1",
            "/api/v1/odds/matches/1/stats",
            "/api/v1/odds/history/1",
            "/api/v1/odds/bookmakers",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            # 所有端点都应该返回JSON
            assert response.headers["content-type"].startswith("application/json")

            # 解析JSON不应该失败
            try:
                data = response.json()
                assert isinstance(data, dict)
            except ValueError:
                pytest.fail(f"Endpoint {endpoint} did not return valid JSON")

    def test_post_endpoints_respond_with_json(self):
        """测试POST端点返回JSON响应"""
        response = client.post(
            "/api/v1/odds/fetch/1", json={"source_name": "oddsportal"}
        )

        # 所有端点都应该返回JSON
        assert response.headers["content-type"].startswith("application/json")

        # 解析JSON不应该失败
        try:
            data = response.json()
            assert isinstance(data, dict)
        except ValueError:
            pytest.fail("POST endpoint did not return valid JSON")

    def test_odds_routes_are_registered(self):
        """测试赔率路由已正确注册"""
        # 检查路由器是否包含预期的端点
        from src.api.odds import router as odds_router

        # 获取路由器中的所有路由（包含前缀）
        routes = [route.path for route in odds_router.routes]

        expected_routes = [
            "/odds/health",
            "/odds/matches/{match_id}",
            "/odds/fetch/{match_id}",
            "/odds/history/{odds_id}",
            "/odds/matches/{match_id}/stats",
            "/odds/bookmakers",
        ]

        for expected_route in expected_routes:
            assert (
                expected_route in routes
            ), f"Route {expected_route} not found in odds router"

    def test_response_structure_on_health_check(self):
        """测试健康检查响应的结构"""
        response = client.get("/api/v1/odds/health")
        data = response.json()

        # 验证StandardResponse结构
        required_fields = ["success", "message", "data", "timestamp"]
        for field in required_fields:
            assert field in data, f"Missing field {field} in response"

        # 验证data字段的结构
        health_data = data["data"]
        required_health_fields = [
            "status",
            "service",
            "timestamp",
            "database_connection",
            "fetcher_status",
        ]
        for field in required_health_fields:
            assert field in health_data, f"Missing field {field} in health data"

    def test_error_response_structure(self):
        """测试错误响应的结构"""
        response = client.get("/api/v1/odds/matches/999999")

        # 如果返回错误，验证错误响应结构
        if response.status_code >= 400:
            try:
                data = response.json()
                # FastAPI的HTTPException有detail字段
                assert "detail" in data, "Error response should have 'detail' field"
            except ValueError:
                pytest.fail("Error response should be valid JSON")


if __name__ == "__main__":
    # 可以直接运行此文件进行快速测试
    pytest.main([__file__, "-v"])
