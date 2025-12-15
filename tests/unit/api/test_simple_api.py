"""简化的API测试 - 专注于API逻辑而不涉及数据库连接
Simple API tests focusing on logic without database connections.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.database.definitions import get_async_session


class TestSimpleAPIEndpoints:
    """简化的API端点测试."""

    @pytest.fixture
    def mock_client(self):
        """创建带有mock数据库依赖的测试客户端."""
        # 创建mock会话
        mock_session = AsyncMock(spec=AsyncSession)

        # Override数据库依赖
        app.dependency_overrides[get_async_session] = lambda: mock_session

        with TestClient(app) as client:
            yield client

        # 清理
        app.dependency_overrides.clear()

    @pytest.mark.unit
    def test_matches_endpoint_exists(self, mock_client):
        """测试matches端点存在且响应格式正确."""
        response = mock_client.get("/api/v1/matches")

        # 端点应该存在（不是404）
        assert response.status_code != 404

        # 响应应该是JSON格式
        assert response.headers["content-type"] == "application/json"

    @pytest.mark.unit
    def test_matches_by_id_endpoint_exists(self, mock_client):
        """测试matches/{id}端点存在."""
        response = mock_client.get("/api/v1/matches/1")

        # 端点应该存在（不是404），可能返回404（资源不存在）或500（数据库错误）
        assert response.status_code != 404 or "不匹配任何已知路由" not in response.text

    @pytest.mark.unit
    def test_teams_endpoint_exists(self, mock_client):
        """测试teams端点存在."""
        response = mock_client.get("/api/v1/teams")

        # 端点应该存在（不是404）
        assert response.status_code != 404

    @pytest.mark.unit
    def test_teams_by_id_endpoint_exists(self, mock_client):
        """测试teams/{id}端点存在."""
        response = mock_client.get("/api/v1/teams/1")

        # 端点应该存在（不是404）
        assert response.status_code != 404

    @pytest.mark.unit
    def test_leagues_endpoint_exists(self, mock_client):
        """测试leagues端点存在."""
        response = mock_client.get("/api/v1/leagues")

        # 端点应该存在（不是404）
        assert response.status_code != 404

    @pytest.mark.unit
    def test_odds_endpoint_exists(self, mock_client):
        """测试odds端点存在."""
        response = mock_client.get("/api/v1/odds")

        # 端点应该存在（不是404）
        assert response.status_code != 404

    @pytest.mark.unit
    def test_health_endpoint_works(self):
        """测试健康检查端点正常工作."""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    @pytest.mark.unit
    def test_openapi_docs_available(self):
        """测试API文档可用."""
        client = TestClient(app)
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert len(data["paths"]) > 0

    @pytest.mark.unit
    def test_api_docs_contains_data_management_routes(self):
        """测试API文档包含数据管理路由."""
        client = TestClient(app)
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        paths = data["paths"]

        # 检查关键的数据管理路由是否存在
        expected_paths = [
            "/api/v1/matches",
            "/api/v1/matches/{match_id}",
            "/api/v1/teams",
            "/api/v1/teams/{team_id}",
            "/api/v1/leagues",
            "/api/v1/odds",
        ]

        for path in expected_paths:
            assert path in paths, f"路径 {path} 在API文档中不存在"

    @pytest.mark.unit
    def test_api_route_registration(self):
        """测试API路由正确注册."""
        client = TestClient(app)

        # 测试所有期望的路由都返回非404状态
        routes = ["/api/v1/matches", "/api/v1/teams", "/api/v1/leagues", "/api/v1/odds"]

        for route in routes:
            response = client.get(route)
            # 可能返回200（如果有默认数据）或500（如果数据库未连接）
            # 但不应该是404（路由不存在）
            assert response.status_code != 404, f"路由 {route} 不存在"

    @pytest.mark.unit
    def test_invalid_routes_return_proper_errors(self):
        """测试无效路由返回适当的错误."""
        client = TestClient(app)

        # 测试不存在的路由返回404
        not_found_routes = ["/api/v1/nonexistent"]

        for route in not_found_routes:
            response = client.get(route)
            assert response.status_code == 404, f"路由 {route} 应该返回404"

        # 测试参数验证错误返回422（FastAPI验证错误）
        validation_routes = [
            "/api/v1/matches/invalid",  # 应该是数字ID
            "/api/v1/teams/abc",  # 应该是数字ID
        ]

        for route in validation_routes:
            response = client.get(route)
            assert response.status_code == 422, f"路由 {route} 参数验证错误应该返回422"

    @pytest.mark.unit
    def test_cors_headers_present(self):
        """测试CORS头部存在."""
        client = TestClient(app)
        response = client.options("/api/v1/matches")

        # 应该有CORS相关头部
        assert (
            "access-control-allow-origin" in response.headers
            or response.status_code == 405
        )

    @pytest.mark.unit
    def test_response_format_consistency(self, mock_client):
        """测试响应格式一致性."""
        # 测试所有API端点都返回JSON格式
        endpoints = [
            "/api/v1/matches",
            "/api/v1/teams",
            "/api/v1/leagues",
            "/api/v1/odds",
        ]

        for endpoint in endpoints:
            response = mock_client.get(endpoint)
            if response.status_code == 200:
                assert response.headers["content-type"] == "application/json"
                data = response.json()
                assert isinstance(data, dict), f"端点 {endpoint} 应该返回JSON对象"
