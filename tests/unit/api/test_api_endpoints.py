"""
API端点测试
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException, Depends
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

# 使用try-except导入，如果模块不存在则跳过测试
try:
    from src.api.app import app
    from src.api.predictions import router as prediction_router
    from src.api.data_router import router as data_router
    from src.api.health import router as health_router
    from src.api.predictions.models import PredictionRequest, PredictionResponse

    # 从 schemas 或其他地方导入基本模型
    try:
        from src.api.schemas import (
            MatchSchema,
            TeamSchema,
            PredictionSchema,
            UserSchema,
        )
    except ImportError:
        # 创建简单的模型类用于测试
        from pydantic import BaseModel

        class MatchSchema(BaseModel):
            id: int
            name: str

        class TeamSchema(BaseModel):
            id: int
            name: str

        class PredictionSchema(BaseModel):
            id: int
            match_id: int

        class UserSchema(BaseModel):
            id: int
            username: str

    API_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    API_AVAILABLE = False

TEST_SKIP_REASON = "API module not available"


@pytest.mark.skipif(not API_AVAILABLE, reason=TEST_SKIP_REASON)
class TestHealthEndpoint:
    """健康检查端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200

        _data = response.json()
        assert "status" in _data

        assert "timestamp" in _data

        assert "version" in _data

    def test_health_check_with_details(self, client):
        """测试带详情的健康检查"""
        response = client.get("/health?detailed=true")
        assert response.status_code == 200

        _data = response.json()
        assert "status" in _data

        assert "checks" in _data

        assert "database" in _data["checks"]
        assert "redis" in _data["checks"]

    def test_liveness_probe(self, client):
        """测试存活探针"""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"

    def test_readiness_probe(self, client):
        """测试就绪探针"""
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    @patch("src.api.health.check_database_health")
    def test_health_check_database_failure(self, mock_db_check, client):
        """测试数据库健康检查失败"""
        mock_db_check.return_value = {"status": "unhealthy"}

        response = client.get("/health")
        assert response.status_code == 503

        _data = response.json()
        assert _data["status"] == "unhealthy"


@pytest.mark.skipif(not API_AVAILABLE, reason=TEST_SKIP_REASON)
class TestPredictionEndpoints:
    """预测端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def mock_prediction_service(self):
        """模拟预测服务"""
        service = AsyncMock()
        service.predict = AsyncMock(
            return_value={
                "match_id": 123,
                "prediction": {"home_win": 0.6, "draw": 0.25, "away_win": 0.15},
                "confidence": 0.85,
                "model_version": "v2.0.0",
            }
        )
        return service

    @patch("src.api.predictions.get_prediction_service")
    def test_create_prediction(self, mock_get_service, client, mock_prediction_service):
        """测试创建预测"""
        mock_get_service.return_value = mock_prediction_service

        request_data = {"match_id": 123, "user_id": 456, "algorithm": "ensemble"}

        response = client.post("/api/v1/predictions", json=request_data)
        assert response.status_code == 201

        _data = response.json()
        assert _data["match_id"] == 123
        assert "prediction" in _data

        assert "confidence" in _data

    def test_create_prediction_invalid_data(self, client):
        """测试创建预测 - 无效数据"""
        request_data = {
            "match_id": "invalid",  # 应该是数字
            "user_id": 456,
        }

        response = client.post("/api/v1/predictions", json=request_data)
        assert response.status_code == 422

    @patch("src.api.predictions.get_prediction_service")
    def test_get_prediction(self, mock_get_service, client):
        """测试获取预测"""
        service = AsyncMock()
        service.get_prediction = AsyncMock(
            return_value={
                "id": 1,
                "match_id": 123,
                "user_id": 456,
                "prediction": {"home_win": 0.6},
                "created_at": datetime.now(),
            }
        )
        mock_get_service.return_value = service

        response = client.get("/api/v1/predictions/1")
        assert response.status_code == 200

        _data = response.json()
        assert _data["id"] == 1
        assert _data["match_id"] == 123

    def test_get_prediction_not_found(self, client):
        """测试获取不存在的预测"""
        with patch("src.api.predictions.get_prediction_service") as mock_get:
            service = AsyncMock()
            service.get_prediction = AsyncMock(return_value=None)
            mock_get.return_value = service

            response = client.get("/api/v1/predictions/999")
            assert response.status_code == 404

    @patch("src.api.predictions.get_prediction_service")
    def test_list_predictions(self, mock_get_service, client):
        """测试获取预测列表"""
        service = AsyncMock()
        service.get_user_predictions = AsyncMock(
            return_value=[{"id": 1, "match_id": 123}, {"id": 2, "match_id": 124}]
        )
        mock_get_service.return_value = service

        response = client.get("/api/v1/predictions?user_id=456&limit=10")
        assert response.status_code == 200

        _data = response.json()
        assert len(data) == 2
        assert _data[0]["match_id"] == 123

    @patch("src.api.predictions.get_prediction_service")
    def test_update_prediction(self, mock_get_service, client):
        """测试更新预测"""
        service = AsyncMock()
        service.update_prediction = AsyncMock(
            return_value={"id": 1, "status": "updated"}
        )
        mock_get_service.return_value = service

        update_data = {"algorithm": "neural_network"}

        response = client.put("/api/v1/predictions/1", json=update_data)
        assert response.status_code == 200

    @patch("src.api.predictions.get_prediction_service")
    def test_delete_prediction(self, mock_get_service, client):
        """测试删除预测"""
        service = AsyncMock()
        service.delete_prediction = AsyncMock(return_value=True)
        mock_get_service.return_value = service

        response = client.delete("/api/v1/predictions/1")
        assert response.status_code == 204

    @patch("src.api.predictions.get_prediction_service")
    def test_batch_predictions(self, mock_get_service, client):
        """测试批量预测"""
        service = AsyncMock()
        service.batch_predict = AsyncMock(
            return_value=[
                {"match_id": 123, "prediction": {"home_win": 0.6}},
                {"match_id": 124, "prediction": {"home_win": 0.4}},
            ]
        )
        mock_get_service.return_value = service

        request_data = {
            "matches": [
                {"match_id": 123, "home_team": 1, "away_team": 2},
                {"match_id": 124, "home_team": 3, "away_team": 4},
            ]
        }

        response = client.post("/api/v1/predictions/batch", json=request_data)
        assert response.status_code == 200

        _data = response.json()
        assert len(_data["predictions"]) == 2


@pytest.mark.skipif(not API_AVAILABLE, reason=TEST_SKIP_REASON)
class TestDataEndpoints:
    """数据端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @patch("src.api.data.get_match_service")
    def test_get_matches(self, mock_get_service, client):
        """测试获取比赛列表"""
        service = AsyncMock()
        service.get_matches = AsyncMock(
            return_value=[
                {"id": 123, "home_team": "Team A", "away_team": "Team B"},
                {"id": 124, "home_team": "Team C", "away_team": "Team D"},
            ]
        )
        mock_get_service.return_value = service

        response = client.get("/api/v1/matches?limit=10&offset=0")
        assert response.status_code == 200

        _data = response.json()
        assert "matches" in _data

        assert "total" in _data

        assert len(_data["matches"]) == 2

    @patch("src.api.data.get_match_service")
    def test_get_match(self, mock_get_service, client):
        """测试获取单个比赛"""
        service = AsyncMock()
        service.get_match = AsyncMock(
            return_value={
                "id": 123,
                "home_team": {"id": 1, "name": "Team A"},
                "away_team": {"id": 2, "name": "Team B"},
                "league": {"id": 10, "name": "Premier League"},
                "kickoff_time": datetime.now() + timedelta(days=1),
            }
        )
        mock_get_service.return_value = service

        response = client.get("/api/v1/matches/123")
        assert response.status_code == 200

        _data = response.json()
        assert _data["id"] == 123
        assert _data["home_team"]["name"] == "Team A"

    @patch("src.api.data.get_team_service")
    def test_get_teams(self, mock_get_service, client):
        """测试获取球队列表"""
        service = AsyncMock()
        service.get_teams = AsyncMock(
            return_value=[
                {"id": 1, "name": "Team A", "league": 10},
                {"id": 2, "name": "Team B", "league": 10},
            ]
        )
        mock_get_service.return_value = service

        response = client.get("/api/v1/teams?league_id=10")
        assert response.status_code == 200

        _data = response.json()
        assert len(data) == 2

    @patch("src.api.data.get_team_service")
    def test_get_team_statistics(self, mock_get_service, client):
        """测试获取球队统计"""
        service = AsyncMock()
        service.get_team_stats = AsyncMock(
            return_value={
                "team_id": 1,
                "matches_played": 38,
                "wins": 20,
                "draws": 10,
                "losses": 8,
                "goals_for": 60,
                "goals_against": 35,
                "points": 70,
            }
        )
        mock_get_service.return_value = service

        response = client.get("/api/v1/teams/1/statistics")
        assert response.status_code == 200

        _data = response.json()
        assert _data["team_id"] == 1
        assert _data["wins"] == 20

    @patch("src.api.data.get_league_service")
    def test_get_league_standings(self, mock_get_service, client):
        """测试获取联赛排名"""
        service = AsyncMock()
        service.get_standings = AsyncMock(
            return_value=[
                {"position": 1, "team": "Team A", "points": 70, "played": 38},
                {"position": 2, "team": "Team B", "points": 65, "played": 38},
            ]
        )
        mock_get_service.return_value = service

        response = client.get("/api/v1/leagues/10/standings")
        assert response.status_code == 200

        _data = response.json()
        assert len(data) == 2
        assert _data[0]["position"] == 1

    @patch("src.api.data.get_data_sync_service")
    def test_sync_data(self, mock_get_service, client):
        """测试数据同步"""
        service = AsyncMock()
        service.sync_all = AsyncMock(
            return_value={
                "status": "success",
                "synced_matches": 100,
                "synced_teams": 20,
                "duration": 30.5,
            }
        )
        mock_get_service.return_value = service

        response = client.post("/api/v1/data/sync")
        assert response.status_code == 200

        _data = response.json()
        assert _data["status"] == "success"
        assert _data["synced_matches"] == 100


@pytest.mark.skipif(not API_AVAILABLE, reason=TEST_SKIP_REASON)
class TestAuthentication:
    """认证测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_login_success(self, client):
        """测试成功登录"""
        with patch("src.api.auth.authenticate_user") as mock_auth:
            mock_auth.return_value = {
                "user_id": 123,
                "username": "testuser",
                "token": "jwt_token_here",
            }

            login_data = {"username": "testuser", "password": "password123"}

            response = client.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == 200

            _data = response.json()
            assert "token" in _data

            assert _data["username"] == "testuser"

    def test_login_invalid_credentials(self, client):
        """测试无效凭据登录"""
        with patch("src.api.auth.authenticate_user") as mock_auth:
            mock_auth.return_value = None

            login_data = {"username": "testuser", "password": "wrongpassword"}

            response = client.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == 401

    def test_protected_endpoint_without_token(self, client):
        """测试无令牌访问受保护端点"""
        response = client.get("/api/v1/users/profile")
        assert response.status_code == 401

    def test_protected_endpoint_with_valid_token(self, client):
        """测试有效令牌访问受保护端点"""
        with patch("src.api.auth.verify_token") as mock_verify:
            mock_verify.return_value = {"user_id": 123, "username": "testuser"}

            headers = {"Authorization": "Bearer valid_jwt_token"}
            response = client.get("/api/v1/users/profile", headers=headers)
            assert response.status_code == 200

    def test_protected_endpoint_with_invalid_token(self, client):
        """测试无效令牌访问受保护端点"""
        with patch("src.api.auth.verify_token") as mock_verify:
            mock_verify.return_value = None

            headers = {"Authorization": "Bearer invalid_token"}
            response = client.get("/api/v1/users/profile", headers=headers)
            assert response.status_code == 401


@pytest.mark.skipif(not API_AVAILABLE, reason=TEST_SKIP_REASON)
class TestRateLimiting:
    """速率限制测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @patch("src.api.middleware.check_rate_limit")
    def test_rate_limit_within_limit(self, mock_check, client):
        """测试速率限制内请求"""
        mock_check.return_value = True

        for _ in range(5):
            response = client.get("/api/v1/matches")
            assert response.status_code == 200

    @patch("src.api.middleware.check_rate_limit")
    def test_rate_limit_exceeded(self, mock_check, client):
        """测试超出速率限制"""
        mock_check.return_value = False

        response = client.get("/api/v1/matches")
        assert response.status_code == 429

        _data = response.json()
        assert "error" in _data

        assert "rate limit" in _data["error"].lower()

    def test_rate_limit_headers(self, client):
        """测试速率限制头部"""
        response = client.get("/api/v1/matches")

        # 检查是否有速率限制头部
        assert response.headers.get("X-RateLimit-Limit") is not None
        assert response.headers.get("X-RateLimit-Remaining") is not None
        assert response.headers.get("X-RateLimit-Reset") is not None


@pytest.mark.skipif(not API_AVAILABLE, reason=TEST_SKIP_REASON)
class TestValidation:
    """输入验证测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_prediction_request_validation(self, client):
        """测试预测请求验证"""
        # 测试有效请求
        valid_request = {"match_id": 123, "user_id": 456, "algorithm": "ensemble"}

        with patch("src.api.predictions.get_prediction_service") as mock_get:
            service = AsyncMock()
            service.predict = AsyncMock(return_value={"prediction": {}})
            mock_get.return_value = service

            response = client.post("/api/v1/predictions", json=valid_request)
            assert response.status_code == 201

        # 测试无效请求 - 缺少必需字段
        invalid_request = {
            "match_id": 123
            # 缺少 user_id
        }

        response = client.post("/api/v1/predictions", json=invalid_request)
        assert response.status_code == 422

        # 测试无效请求 - 错误的数据类型
        invalid_request2 = {"match_id": "not_a_number", "user_id": 456}

        response = client.post("/api/v1/predictions", json=invalid_request2)
        assert response.status_code == 422

    def test_match_filter_validation(self, client):
        """测试比赛过滤器验证"""
        # 测试有效的过滤器
        response = client.get("/api/v1/matches?limit=10&offset=0")
        assert response.status_code == 200

        # 测试无效的limit
        response = client.get("/api/v1/matches?limit=-1")
        assert response.status_code == 422

        # 测试过大的limit
        response = client.get("/api/v1/matches?limit=1000")
        assert response.status_code == 422

    def test_date_validation(self, client):
        """测试日期验证"""
        # 测试有效日期格式
        response = client.get("/api/v1/matches?date_from=2024-01-01&date_to=2024-01-31")
        # 可能返回200或404，取决于是否有数据
        assert response.status_code in [200, 404]

        # 测试无效日期格式
        response = client.get("/api/v1/matches?date_from=invalid-date")
        assert response.status_code == 422


@pytest.mark.skipif(not API_AVAILABLE, reason=TEST_SKIP_REASON)
class TestErrorHandling:
    """错误处理测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_404_error(self, client):
        """测试404错误"""
        response = client.get("/api/v1/nonexistent-endpoint")
        assert response.status_code == 404

        _data = response.json()
        assert "error" in _data

        assert "Not Found" in _data["error"]["message"]

    def test_500_error(self, client):
        """测试500错误"""
        with patch("src.api.predictions.get_prediction_service") as mock_get:
            service = AsyncMock()
            service.predict = AsyncMock(side_effect=Exception("Database error"))
            mock_get.return_value = service

            request_data = {"match_id": 123, "user_id": 456}

            response = client.post("/api/v1/predictions", json=request_data)
            assert response.status_code == 500

            _data = response.json()
            assert "error" in _data

    def test_validation_error_format(self, client):
        """测试验证错误格式"""
        request_data = {"invalid_field": "value"}

        response = client.post("/api/v1/predictions", json=request_data)
        assert response.status_code == 422

        _data = response.json()
        assert "detail" in _data

        assert isinstance(_data["detail"], list)

    def test_cors_headers(self, client):
        """测试CORS头部"""
        response = client.options("/api/v1/matches")

        assert response.headers.get("Access-Control-Allow-Origin") is not None
        assert response.headers.get("Access-Control-Allow-Methods") is not None
        assert response.headers.get("Access-Control-Allow-Headers") is not None


@pytest.mark.skipif(not API_AVAILABLE, reason=TEST_SKIP_REASON)
class TestPagination:
    """分页测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @patch("src.api.data.get_match_service")
    def test_pagination_first_page(self, mock_get_service, client):
        """测试第一页分页"""
        service = AsyncMock()
        service.get_matches = AsyncMock(
            return_value={
                "matches": [{"id": i} for i in range(1, 11)],
                "total": 100,
                "limit": 10,
                "offset": 0,
            }
        )
        mock_get_service.return_value = service

        response = client.get("/api/v1/matches?limit=10&offset=0")
        assert response.status_code == 200

        _data = response.json()
        assert len(_data["matches"]) == 10
        assert _data["total"] == 100

    @patch("src.api.data.get_match_service")
    def test_pagination_last_page(self, mock_get_service, client):
        """测试最后一页分页"""
        service = AsyncMock()
        service.get_matches = AsyncMock(
            return_value={
                "matches": [{"id": i} for i in range(91, 101)],
                "total": 100,
                "limit": 10,
                "offset": 90,
            }
        )
        mock_get_service.return_value = service

        response = client.get("/api/v1/matches?limit=10&offset=90")
        assert response.status_code == 200

        _data = response.json()
        assert len(_data["matches"]) == 10
        assert _data["matches"][0]["id"] == 91

    @patch("src.api.data.get_match_service")
    def test_pagination_exceeded(self, mock_get_service, client):
        """测试超出范围的分页"""
        service = AsyncMock()
        service.get_matches = AsyncMock(
            return_value={"matches": [], "total": 100, "limit": 10, "offset": 100}
        )
        mock_get_service.return_value = service

        response = client.get("/api/v1/matches?limit=10&offset=100")
        assert response.status_code == 200

        _data = response.json()
        assert len(_data["matches"]) == 0

    def test_pagination_links(self, client):
        """测试分页链接"""
        with patch("src.api.data.get_match_service") as mock_get:
            service = AsyncMock()
            service.get_matches = AsyncMock(
                return_value={
                    "matches": [{"id": i} for i in range(1, 11)],
                    "total": 100,
                    "limit": 10,
                    "offset": 10,
                }
            )
            mock_get.return_value = service

            response = client.get("/api/v1/matches?limit=10&offset=10")
            assert response.status_code == 200

            # 检查响应头中的分页链接
            links = response.headers.get("Link")
            if links:
                assert 'rel="first"' in links
                assert 'rel="prev"' in links
                assert 'rel="next"' in links
                assert 'rel="last"' in links


@pytest.mark.skipif(not API_AVAILABLE, reason=TEST_SKIP_REASON)
class TestCaching:
    """缓存测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @patch("src.api.middleware.get_from_cache")
    def test_cache_hit(self, mock_get_cache, client):
        """测试缓存命中"""
        mock_get_cache.return_value = {"id": 123, "data": "cached_data"}

        response = client.get("/api/v1/matches/123")
        assert response.status_code == 200

        # 验证缓存头部
        assert response.headers.get("X-Cache") == "HIT"

    @patch("src.api.middleware.get_from_cache")
    @patch("src.api.middleware.set_cache")
    def test_cache_miss(self, mock_set_cache, mock_get_cache, client):
        """测试缓存未命中"""
        mock_get_cache.return_value = None

        with patch("src.api.data.get_match_service") as mock_get:
            service = AsyncMock()
            service.get_match = AsyncMock(
                return_value={"id": 123, "data": "fresh_data"}
            )
            mock_get.return_value = service

            response = client.get("/api/v1/matches/123")
            assert response.status_code == 200

            # 验证缓存头部
            assert response.headers.get("X-Cache") == "MISS"

            # 验证缓存设置被调用
            mock_set_cache.assert_called_once()

    def test_cache_control_headers(self, client):
        """测试缓存控制头部"""
        response = client.get("/api/v1/matches")

        # 检查缓存控制头部
        cache_control = response.headers.get("Cache-Control")
        if cache_control:
            assert "max-age" in cache_control or "no-cache" in cache_control

    def test_etag_header(self, client):
        """测试ETag头部"""
        with patch("src.api.data.get_match_service") as mock_get:
            service = AsyncMock()
            service.get_match = AsyncMock(return_value={"id": 123, "version": 1})
            mock_get.return_value = service

            response = client.get("/api/v1/matches/123")
            assert response.status_code == 200

            # 检查ETag头部
            etag = response.headers.get("ETag")
            if etag:
                assert etag.startswith('"')
                assert etag.endswith('"')
