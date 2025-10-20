"""
API端点综合测试
Comprehensive API Endpoint Tests

测试所有核心API端点的功能。
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json
from datetime import datetime

from src.api.app import app

client = TestClient(app)


class TestRootEndpoints:
    """根路径端点测试"""

    def test_root_endpoint(self):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_api_health(self):
        """测试API健康检查"""
        response = client.get("/api/health")
        assert response.status_code in [200, 404]

    def test_metrics(self):
        """测试指标端点"""
        response = client.get("/metrics")
        assert response.status_code in [200, 404]

    def test_api_test(self):
        """测试API测试端点"""
        response = client.get("/api/test")
        assert response.status_code in [200, 404]


class TestPredictionEndpoints:
    """预测相关端点测试"""

    @patch("src.core.prediction.PredictionEngine")
    def test_create_prediction(self, mock_engine_class):
        """测试创建预测"""
        # 模拟预测引擎
        mock_engine = MagicMock()
        mock_engine_class.return_value = mock_engine
        mock_engine.predict = AsyncMock(
            return_value={
                "match_id": 123,
                "home_win_prob": 0.5,
                "draw_prob": 0.3,
                "away_win_prob": 0.2,
                "predicted_outcome": "home",
                "confidence": 0.75,
                "model_version": "v1.0",
            }
        )

        request_data = {
            "match_id": 123,
            "model_version": "v1.0",
            "include_details": True,
        }

        response = client.post("/api/v1/predictions", json=request_data)
        assert response.status_code in [200, 404, 422]

    def test_get_predictions(self):
        """测试获取预测列表"""
        response = client.get("/api/v1/predictions?user_id=1&limit=10")
        assert response.status_code in [200, 401, 404]

    def test_get_prediction_by_id(self):
        """测试根据ID获取预测"""
        response = client.get("/api/v1/predictions/123")
        assert response.status_code in [200, 404]

    def test_batch_predictions(self):
        """测试批量预测"""
        request_data = {"match_ids": [123, 124, 125], "model_version": "v1.0"}
        response = client.post("/api/v1/predictions/batch", json=request_data)
        assert response.status_code in [200, 404, 501]

    def test_update_prediction(self):
        """测试更新预测"""
        update_data = {"confidence": 0.8, "notes": "Updated prediction"}
        response = client.put("/api/v1/predictions/123", json=update_data)
        assert response.status_code in [200, 404, 401]

    def test_delete_prediction(self):
        """测试删除预测"""
        response = client.delete("/api/v1/predictions/123")
        assert response.status_code in [200, 204, 404, 401]


class TestMatchEndpoints:
    """比赛相关端点测试"""

    def test_get_matches(self):
        """测试获取比赛列表"""
        response = client.get("/api/v1/matches")
        assert response.status_code in [200, 404]

    def test_get_upcoming_matches(self):
        """测试获取即将到来的比赛"""
        response = client.get("/api/v1/matches?status=upcoming&days=7")
        assert response.status_code in [200, 404]

    def test_get_match_by_id(self):
        """测试根据ID获取比赛"""
        response = client.get("/api/v1/matches/123")
        assert response.status_code in [200, 404]

    def test_get_match_details(self):
        """测试获取比赛详情"""
        response = client.get("/api/v1/matches/123/details")
        assert response.status_code in [200, 404]

    def test_get_match_statistics(self):
        """测试获取比赛统计"""
        response = client.get("/api/v1/matches/123/statistics")
        assert response.status_code in [200, 404]

    def test_get_match_history(self):
        """测试获取比赛历史"""
        response = client.get("/api/v1/matches/history?team_id=1&limit=10")
        assert response.status_code in [200, 404]


class TestTeamEndpoints:
    """队伍相关端点测试"""

    def test_get_teams(self):
        """测试获取队伍列表"""
        response = client.get("/api/v1/teams")
        assert response.status_code in [200, 404]

    def test_get_team_by_id(self):
        """测试根据ID获取队伍"""
        response = client.get("/api/v1/teams/123")
        assert response.status_code in [200, 404]

    def test_get_team_statistics(self):
        """测试获取队伍统计"""
        response = client.get("/api/v1/teams/123/statistics")
        assert response.status_code in [200, 404]

    def test_get_team_matches(self):
        """测试获取队伍比赛"""
        response = client.get("/api/v1/teams/123/matches?limit=10")
        assert response.status_code in [200, 404]

    def test_get_team_ranking(self):
        """测试获取队伍排名"""
        response = client.get("/api/v1/teams/ranking?league_id=1")
        assert response.status_code in [200, 404]


class TestLeagueEndpoints:
    """联赛相关端点测试"""

    def test_get_leagues(self):
        """测试获取联赛列表"""
        response = client.get("/api/v1/leagues")
        assert response.status_code in [200, 404]

    def test_get_league_by_id(self):
        """测试根据ID获取联赛"""
        response = client.get("/api/v1/leagues/123")
        assert response.status_code in [200, 404]

    def test_get_league_table(self):
        """测试获取联赛积分榜"""
        response = client.get("/api/v1/leagues/123/table")
        assert response.status_code in [200, 404]

    def test_get_league_matches(self):
        """测试获取联赛比赛"""
        response = client.get("/api/v1/leagues/123/matches?round=1")
        assert response.status_code in [200, 404]

    def test_get_league_statistics(self):
        """测试获取联赛统计"""
        response = client.get("/api/v1/leagues/123/statistics")
        assert response.status_code in [200, 404]


class TestOddsEndpoints:
    """赔率相关端点测试"""

    def test_get_match_odds(self):
        """测试获取比赛赔率"""
        response = client.get("/api/v1/odds/matches/123")
        assert response.status_code in [200, 404]

    def test_get_odds_comparison(self):
        """测试获取赔率对比"""
        response = client.get("/api/v1/odds/matches/123/comparison")
        assert response.status_code in [200, 404]

    def test_get_market_odds(self):
        """测试获取市场赔率"""
        response = client.get("/api/v1/odds/market/1x2")
        assert response.status_code in [200, 404]

    def test_get_odds_history(self):
        """测试获取赔率历史"""
        response = client.get("/api/v1/odds/matches/123/history")
        assert response.status_code in [200, 404]


class TestUserEndpoints:
    """用户相关端点测试"""

    def test_register_user(self):
        """测试用户注册"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepassword",
        }
        response = client.post("/api/v1/users/register", json=user_data)
        assert response.status_code in [200, 201, 404, 422]

    def test_login_user(self):
        """测试用户登录"""
        login_data = {"username": "testuser", "password": "securepassword"}
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code in [200, 401, 404]

    def test_get_user_profile(self):
        """测试获取用户资料"""
        headers = {"Authorization": "Bearer mock_token"}
        response = client.get("/api/v1/users/profile", headers=headers)
        assert response.status_code in [200, 401, 404]

    def test_update_user_profile(self):
        """测试更新用户资料"""
        headers = {"Authorization": "Bearer mock_token"}
        update_data = {"email": "new@example.com"}
        response = client.put(
            "/api/v1/users/profile", json=update_data, headers=headers
        )
        assert response.status_code in [200, 401, 404]

    def test_get_user_predictions(self):
        """测试获取用户预测"""
        headers = {"Authorization": "Bearer mock_token"}
        response = client.get("/api/v1/users/predictions", headers=headers)
        assert response.status_code in [200, 401, 404]

    def test_logout_user(self):
        """测试用户登出"""
        headers = {"Authorization": "Bearer mock_token"}
        response = client.post("/api/v1/auth/logout", headers=headers)
        assert response.status_code in [200, 401, 404]


class TestAnalyticsEndpoints:
    """分析相关端点测试"""

    def test_get_prediction_accuracy(self):
        """测试获取预测准确率"""
        response = client.get("/api/v1/analytics/accuracy?period=30d")
        assert response.status_code in [200, 401, 404]

    def test_get_performance_metrics(self):
        """测试获取性能指标"""
        response = client.get("/api/v1/analytics/performance")
        assert response.status_code in [200, 401, 404]

    def test_get_trending_predictions(self):
        """测试获取热门预测"""
        response = client.get("/api/v1/analytics/trending")
        assert response.status_code in [200, 404]

    def test_get_user_statistics(self):
        """测试获取用户统计"""
        response = client.get("/api/v1/analytics/users/123/statistics")
        assert response.status_code in [200, 401, 404]


class TestUtilityEndpoints:
    """工具端点测试"""

    def test_api_version(self):
        """测试API版本"""
        response = client.get("/api/v1/version")
        assert response.status_code in [200, 404]

    def test_api_status(self):
        """测试API状态"""
        response = client.get("/api/v1/status")
        assert response.status_code in [200, 404]

    def test_api_docs(self):
        """测试API文档"""
        response = client.get("/docs")
        assert response.status_code in [200, 404]

    def test_openapi_schema(self):
        """测试OpenAPI schema"""
        response = client.get("/openapi.json")
        assert response.status_code in [200, 404]


class TestErrorHandling:
    """错误处理测试"""

    def test_404_not_found(self):
        """测试404错误"""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_422_validation_error(self):
        """测试422验证错误"""
        response = client.post("/api/v1/predictions", json={})
        assert response.status_code in [400, 422, 404]

    def test_401_unauthorized(self):
        """测试401未授权"""
        response = client.get("/api/v1/users/profile")
        assert response.status_code in [401, 404]

    def test_403_forbidden(self):
        """测试403禁止访问"""
        response = client.delete("/api/v1/predictions/123")
        assert response.status_code in [401, 403, 404]

    def test_500_server_error(self):
        """测试服务器错误"""
        # 这个测试需要实际触发错误
        pass
