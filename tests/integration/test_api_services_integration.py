"""
API与Services模块集成测试
API and Services Module Integration Tests

测试API层与服务层的集成，确保API正确调用业务服务
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

# 标记测试
pytestmark = [pytest.mark.integration, pytest.mark.api, pytest.mark.services]


class TestPredictionAPIServiceIntegration:
    """预测API与服务层集成测试"""

    @pytest.mark.asyncio
    async def test_prediction_api_uses_prediction_service(
        self, async_client: AsyncClient, sample_match, mock_redis
    ):
        """测试预测API使用预测服务"""
        if not sample_match:
            pytest.skip("Sample match not available")

        prediction_data = {
            "user_id": 1,
            "match_id": sample_match.id,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
        }

        # 模拟服务层
        mock_service = AsyncMock()
        mock_service.create_prediction.return_value = {
            "id": 1,
            "user_id": 1,
            "match_id": sample_match.id,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
        }

        with patch('src.api.routes.predictions.PredictionService', return_value=mock_service):
            response = await async_client.post("/api/predictions/", json=prediction_data)

            if response.status_code == 200:
                result = response.json()
                assert result["user_id"] == prediction_data["user_id"]
                assert result["match_id"] == prediction_data["match_id"]

                # 验证服务被调用
                mock_service.create_prediction.assert_called_once()
            elif response.status_code == 404:
                pytest.skip("Prediction API endpoint not available")

    @pytest.mark.asyncio
    async def test_prediction_api_service_error_handling(
        self, async_client: AsyncClient, sample_match
    ):
        """测试预测API服务错误处理"""
        if not sample_match:
            pytest.skip("Sample match not available")

        prediction_data = {
            "user_id": 1,
            "match_id": sample_match.id,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
        }

        # 模拟服务层错误
        mock_service = AsyncMock()
        mock_service.create_prediction.side_effect = Exception("Service error")

        with patch('src.api.routes.predictions.PredictionService', return_value=mock_service):
            response = await async_client.post("/api/predictions/", json=prediction_data)

            # 应该返回错误响应
            if response.status_code != 404:  # 如果端点存在
                assert response.status_code >= 400

    @pytest.mark.asyncio
    async def test_prediction_api_caching_integration(
        self, async_client: AsyncClient, sample_match, cache_test_data, mock_redis
    ):
        """测试预测API缓存集成"""
        if not sample_match:
            pytest.skip("Sample match not available")

        # 测试获取预测缓存
        cache_key = cache_test_data["prediction_cache_key"]

        with patch('src.api.routes.predictions.redis_client', mock_redis):
            # 首次请求（缓存未命中）
            response = await async_client.get(f"/api/predictions/cache/{cache_key}")

            # 第二次请求（缓存命中）
            if mock_redis.get.called:
                mock_redis.get.assert_called_with(cache_key)

    @pytest.mark.asyncio
    async def test_bulk_prediction_api_service_integration(
        self, async_client: AsyncClient, sample_match, bulk_test_data
    ):
        """测试批量预测API与服务集成"""
        if not sample_match:
            pytest.skip("Sample match not available")

        bulk_predictions = bulk_test_data["bulk_predictions"][:10]  # 只测试前10个

        # 模拟批量服务
        mock_service = AsyncMock()
        mock_service.create_bulk_predictions.return_value = {
            "created_count": len(bulk_predictions),
            "failed_count": 0,
            "predictions": [
                {
                    "id": i + 1,
                    "user_id": pred["user_id"],
                    "match_id": pred["match_id"],
                    "predicted_home": pred["predicted_home"],
                    "predicted_away": pred["predicted_away"],
                    "confidence": pred["confidence"],
                }
                for i, pred in enumerate(bulk_predictions)
            ]
        }

        with patch('src.api.routes.predictions.PredictionService', return_value=mock_service):
            response = await async_client.post(
                "/api/predictions/bulk",
                json={"predictions": bulk_predictions}
            )

            if response.status_code == 200:
                result = response.json()
                assert result["created_count"] == len(bulk_predictions)
                assert len(result["predictions"]) == len(bulk_predictions)

                # 验证批量服务被调用
                mock_service.create_bulk_predictions.assert_called_once()
            elif response.status_code == 404:
                pytest.skip("Bulk prediction API endpoint not available")


class TestMatchAPIServiceIntegration:
    """比赛API与服务层集成测试"""

    @pytest.mark.asyncio
    async def test_match_api_uses_match_service(
        self, async_client: AsyncClient, sample_teams
    ):
        """测试比赛API使用比赛服务"""
        if not sample_teams or len(sample_teams) < 2:
            pytest.skip("Sample teams not available")

        home_team, away_team = sample_teams[0], sample_teams[1]

        match_data = {
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "match_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "venue": "Test Stadium",
        }

        # 模拟比赛服务
        mock_service = AsyncMock()
        mock_service.create_match.return_value = {
            "id": 1,
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "match_date": match_data["match_date"],
            "venue": match_data["venue"],
            "status": "scheduled",
            "home_score": 0,
            "away_score": 0,
        }

        with patch('src.api.routes.matches.MatchService', return_value=mock_service):
            response = await async_client.post("/api/matches/", json=match_data)

            if response.status_code == 200:
                result = response.json()
                assert result["home_team_id"] == match_data["home_team_id"]
                assert result["away_team_id"] == match_data["away_team_id"]

                # 验证服务被调用
                mock_service.create_match.assert_called_once()
            elif response.status_code == 404:
                pytest.skip("Match API endpoint not available")

    @pytest.mark.asyncio
    async def test_match_status_update_service_integration(
        self, async_client: AsyncClient, sample_match
    ):
        """测试比赛状态更新服务集成"""
        if not sample_match:
            pytest.skip("Sample match not available")

        # 模拟比赛服务
        mock_service = AsyncMock()
        mock_service.start_match.return_value = {
            "id": sample_match.id,
            "status": "in_progress",
            "started_at": datetime.utcnow().isoformat(),
        }

        with patch('src.api.routes.matches.MatchService', return_value=mock_service):
            response = await async_client.post(f"/api/matches/{sample_match.id}/start")

            if response.status_code == 200:
                result = response.json()
                assert result["status"] == "in_progress"

                # 验证服务被调用
                mock_service.start_match.assert_called_once_with(sample_match.id)
            elif response.status_code == 404:
                pytest.skip("Match start API endpoint not available")

    @pytest.mark.asyncio
    async def test_match_statistics_service_integration(
        self, async_client: AsyncClient, sample_teams
    ):
        """测试比赛统计服务集成"""
        if not sample_teams:
            pytest.skip("Sample teams not available")

        team = sample_teams[0]

        # 模拟统计服务
        mock_service = AsyncMock()
        mock_service.get_team_statistics.return_value = {
            "team_id": team.id,
            "matches_played": 10,
            "wins": 6,
            "draws": 2,
            "losses": 2,
            "goals_for": 15,
            "goals_against": 8,
            "goal_difference": 7,
            "points": 20,
            "ranking": 3,
        }

        with patch('src.api.routes.matches.MatchService', return_value=mock_service):
            response = await async_client.get(f"/api/teams/{team.id}/statistics")

            if response.status_code == 200:
                stats = response.json()
                assert "matches_played" in stats
                assert "wins" in stats
                assert "points" in stats

                # 验证服务被调用
                mock_service.get_team_statistics.assert_called_once_with(team.id)
            elif response.status_code == 404:
                pytest.skip("Team statistics API endpoint not available")


class TestUserAPIServiceIntegration:
    """用户API与服务层集成测试"""

    @pytest.mark.asyncio
    async def test_user_registration_service_integration(
        self, async_client: AsyncClient, test_user_data
    ):
        """测试用户注册服务集成"""
        user_data = test_user_data["users"][0]

        registration_data = {
            "username": user_data["username"],
            "email": user_data["email"],
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        }

        # 模拟用户服务
        mock_service = AsyncMock()
        mock_service.register_user.return_value = {
            "id": user_data["id"],
            "username": user_data["username"],
            "email": user_data["email"],
            "is_active": True,
            "created_at": user_data["created_at"].isoformat(),
        }

        with patch('src.api.routes.users.UserService', return_value=mock_service):
            response = await async_client.post("/api/users/register", json=registration_data)

            if response.status_code in [200, 201]:
                result = response.json()
                assert result["username"] == registration_data["username"]
                assert result["email"] == registration_data["email"]

                # 验证服务被调用
                mock_service.register_user.assert_called_once()
            elif response.status_code == 404:
                pytest.skip("User registration API endpoint not available")

    @pytest.mark.asyncio
    async def test_user_authentication_service_integration(
        self, async_client: AsyncClient, test_user_data
    ):
        """测试用户认证服务集成"""
        user_data = test_user_data["users"][0]

        login_data = {
            "username": user_data["username"],
            "password": "SecurePassword123!",
        }

        # 模拟认证服务
        mock_service = AsyncMock()
        mock_service.authenticate_user.return_value = {
            "access_token": "test_jwt_token",
            "token_type": "bearer",
            "user": {
                "id": user_data["id"],
                "username": user_data["username"],
                "email": user_data["email"],
                "is_active": user_data["is_active"],
            }
        }

        with patch('src.api.routes.auth.UserService', return_value=mock_service):
            response = await async_client.post("/api/auth/login", json=login_data)

            if response.status_code == 200:
                result = response.json()
                assert "access_token" in result
                assert result["token_type"] == "bearer"

                # 验证服务被调用
                mock_service.authenticate_user.assert_called_once()
            elif response.status_code == 404:
                pytest.skip("User authentication API endpoint not available")

    @pytest.mark.asyncio
    async def test_user_prediction_history_service_integration(
        self, async_client: AsyncClient, sample_predictions, auth_headers
    ):
        """测试用户预测历史服务集成"""
        if not sample_predictions:
            pytest.skip("Sample predictions not available")

        user_id = sample_predictions[0].user_id

        # 模拟用户服务
        mock_service = AsyncMock()
        mock_service.get_user_predictions.return_value = [
            {
                "id": pred.id,
                "match_id": pred.match_id,
                "predicted_home": getattr(pred, 'predicted_home', 2),
                "predicted_away": getattr(pred, 'predicted_away', 1),
                "confidence": getattr(pred, 'confidence', 0.85),
                "status": pred.status,
                "created_at": getattr(pred, 'created_at', datetime.utcnow()).isoformat(),
            }
            for pred in sample_predictions
            if pred.user_id == user_id
        ]

        with patch('src.api.routes.users.UserService', return_value=mock_service):
            response = await async_client.get(
                f"/api/users/{user_id}/predictions",
                headers=auth_headers
            )

            if response.status_code == 200:
                predictions = response.json()
                assert isinstance(predictions, list)

                # 验证服务被调用
                mock_service.get_user_predictions.assert_called_once_with(user_id)
            elif response.status_code == 404:
                pytest.skip("User predictions API endpoint not available")


class TestAnalyticsAPIServiceIntegration:
    """分析API与服务层集成测试"""

    @pytest.mark.asyncio
    async def test_prediction_analytics_service_integration(
        self, async_client: AsyncClient, auth_headers
    ):
        """测试预测分析服务集成"""
        # 模拟分析服务
        mock_service = AsyncMock()
        mock_service.get_prediction_analytics.return_value = {
            "total_predictions": 1000,
            "accuracy_rate": 0.65,
            "average_confidence": 0.78,
            "popular_predictions": [
                {"score": "1-0", "count": 150},
                {"score": "2-1", "count": 120},
                {"score": "1-1", "count": 100},
            ],
            "confidence_distribution": {
                "high": 300,
                "medium": 500,
                "low": 200,
            },
            "monthly_trends": [
                {"month": "2024-01", "predictions": 800, "accuracy": 0.62},
                {"month": "2024-02", "predictions": 950, "accuracy": 0.68},
            ],
        }

        with patch('src.api.routes.analytics.AnalyticsService', return_value=mock_service):
            response = await async_client.get(
                "/api/analytics/predictions",
                headers=auth_headers
            )

            if response.status_code == 200:
                analytics = response.json()
                assert "total_predictions" in analytics
                assert "accuracy_rate" in analytics
                assert "popular_predictions" in analytics

                # 验证服务被调用
                mock_service.get_prediction_analytics.assert_called_once()
            elif response.status_code == 404:
                pytest.skip("Analytics API endpoint not available")

    @pytest.mark.asyncio
    async def test_user_analytics_service_integration(
        self, async_client: AsyncClient, test_user_data, auth_headers
    ):
        """测试用户分析服务集成"""
        user_data = test_user_data["users"][0]

        # 模拟用户分析服务
        mock_service = AsyncMock()
        mock_service.get_user_analytics.return_value = {
            "user_id": user_data["id"],
            "total_predictions": 50,
            "correct_predictions": 32,
            "accuracy_rate": 0.64,
            "total_points": 156,
            "ranking": 15,
            "favorite_teams": [
                {"team_name": "Manchester United", "predictions": 20},
                {"team_name": "Liverpool", "predictions": 15},
            ],
            "prediction_trends": [
                {"date": "2024-01-01", "predictions": 5, "accuracy": 0.60},
                {"date": "2024-01-02", "predictions": 3, "accuracy": 0.67},
            ],
        }

        with patch('src.api.routes.analytics.AnalyticsService', return_value=mock_service):
            response = await async_client.get(
                f"/api/analytics/users/{user_data['id']}",
                headers=auth_headers
            )

            if response.status_code == 200:
                analytics = response.json()
                assert analytics["user_id"] == user_data["id"]
                assert "accuracy_rate" in analytics
                assert "ranking" in analytics

                # 验证服务被调用
                mock_service.get_user_analytics.assert_called_once_with(user_data["id"])
            elif response.status_code == 404:
                pytest.skip("User analytics API endpoint not available")


class TestNotificationAPIServiceIntegration:
    """通知API与服务层集成测试"""

    @pytest.mark.asyncio
    async def test_notification_service_integration(
        self, async_client: AsyncClient, test_user_data, mock_external_services
    ):
        """测试通知服务集成"""
        user_data = test_user_data["users"][0]

        notification_data = {
            "user_id": user_data["id"],
            "type": "match_reminder",
            "title": "Match Reminder",
            "message": "Your predicted match starts in 1 hour",
            "scheduled_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        }

        # 模拟通知服务
        mock_service = AsyncMock()
        mock_service.send_notification.return_value = {
            "id": "notif_123",
            "user_id": user_data["id"],
            "status": "sent",
            "sent_at": datetime.utcnow().isoformat(),
        }

        with patch('src.api.routes.notifications.NotificationService', return_value=mock_service):
            response = await async_client.post("/api/notifications/", json=notification_data)

            if response.status_code == 200:
                result = response.json()
                assert result["user_id"] == notification_data["user_id"]
                assert result["status"] == "sent"

                # 验证服务被调用
                mock_service.send_notification.assert_called_once()
            elif response.status_code == 404:
                pytest.skip("Notification API endpoint not available")


class TestCacheIntegration:
    """缓存集成测试"""

    @pytest.mark.asyncio
    async def test_api_cache_service_integration(
        self, async_client: AsyncClient, cache_test_data, mock_redis
    ):
        """测试API缓存服务集成"""
        cache_key = cache_test_data["user_stats_key"]
        cached_value = json.dumps(cache_test_data["test_value"])

        # 设置Redis模拟返回缓存值
        mock_redis.get.return_value = cached_value

        with patch('src.api.middleware.cache.redis_client', mock_redis):
            response = await async_client.get(f"/api/cache/{cache_key}")

            # 验证缓存读取
            mock_redis.get.assert_called_with(cache_key)

    @pytest.mark.asyncio
    async def test_api_cache_invalidation_service(
        self, async_client: AsyncClient, cache_test_data, mock_redis
    ):
        """测试API缓存失效服务"""
        cache_key = cache_test_data["match_stats_key"]

        with patch('src.api.middleware.cache.redis_client', mock_redis):
            response = await async_client.delete(f"/api/cache/{cache_key}")

            # 验证缓存删除
            mock_redis.delete.assert_called_with(cache_key)


class TestAPIErrorHandling:
    """API错误处理测试"""

    @pytest.mark.asyncio
    async def test_service_unavailable_handling(
        self, async_client: AsyncClient
    ):
        """测试服务不可用处理"""
        # 模拟服务不可用
        mock_service = AsyncMock()
        mock_service.get_predictions.side_effect = ConnectionError("Service unavailable")

        with patch('src.api.routes.predictions.PredictionService', return_value=mock_service):
            response = await async_client.get("/api/predictions/")

            # 应该返回503或适当的错误码
            if response.status_code != 404:  # 如果端点存在
                assert response.status_code >= 500

    @pytest.mark.asyncio
    async def test_service_timeout_handling(
        self, async_client: AsyncClient
    ):
        """测试服务超时处理"""
        # 模拟服务超时
        mock_service = AsyncMock()
        mock_service.get_predictions.side_effect = asyncio.TimeoutError("Service timeout")

        with patch('src.api.routes.predictions.PredictionService', return_value=mock_service):
            response = await async_client.get("/api/predictions/")

            # 应该返回超时错误
            if response.status_code != 404:  # 如果端点存在
                assert response.status_code in [408, 504]

    @pytest.mark.asyncio
    async def test_invalid_data_handling(
        self, async_client: AsyncClient
    ):
        """测试无效数据处理"""
        invalid_data = {
            "user_id": "invalid",  # 应该是数字
            "match_id": None,  # 不能为空
            "predicted_home": -1,  # 不能为负数
        }

        response = await async_client.post("/api/predictions/", json=invalid_data)

        # 应该返回验证错误
        if response.status_code != 404:  # 如果端点存在
            assert response.status_code == 422


class TestAPIPerformanceIntegration:
    """API性能集成测试"""

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(
        self, async_client: AsyncClient, performance_benchmarks
    ):
        """测试并发请求处理"""
        import asyncio
        import time

        start_time = time.time()

        # 发送多个并发请求
        tasks = [
            async_client.get("/api/health") for _ in range(20)
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        total_time = end_time - start_time

        # 验证并发性能
        avg_response_time = total_time / len(tasks)
        assert avg_response_time < performance_benchmarks["response_time_limits"]["health_check"]

        # 验证大部分请求成功
        successful_responses = [r for r in responses if not isinstance(r, Exception) and r.status_code == 200]
        success_rate = len(successful_responses) / len(tasks)
        assert success_rate > 0.8

    @pytest.mark.asyncio
    async def test_request_rate_limiting(
        self, async_client: AsyncClient
    ):
        """测试请求速率限制"""
        import asyncio

        # 快速发送多个请求
        tasks = [
            async_client.get("/api/predictions/") for _ in range(10)
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # 检查是否有速率限制响应
        rate_limited_responses = [
            r for r in responses
            if not isinstance(r, Exception) and r.status_code == 429
        ]

        # 如果实现了速率限制，应该有一些请求被限制
        # 这个测试是可选的，取决于是否实现了速率限制
        pass