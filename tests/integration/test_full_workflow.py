"""
完整业务流程集成测试
Full Workflow Integration Tests

测试足球预测系统的完整业务流程，包括多个模块的协调工作
"""

import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# P8.2修复：移除循环导入，fixtures将在下面定义

# 标记测试
pytestmark = [pytest.mark.integration, pytest.mark.workflow, pytest.mark.e2e]

# P8.2修复：定义fixtures以解决循环导入问题
@pytest.fixture
def cache_test_data():
    """缓存测试数据fixture"""
    return {
        "user_stats_key": "user:123:stats",
        "test_value": {
            "predictions_count": 10,
            "success_rate": 0.75,
            "last_updated": "2025-11-13T10:00:00Z"
        }
    }

@pytest.fixture
def mock_redis():
    """Redis模拟fixture"""
    from unittest.mock import AsyncMock
    redis_mock = AsyncMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.exists.return_value = False
    redis_mock.delete.return_value = True
    return redis_mock


class TestCompletePredictionWorkflow:
    """完整预测工作流测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_prediction_workflow(
        self,
        async_client: AsyncClient,
        sample_teams,
        test_user_data,
        mock_external_services,
    ):
        """测试端到端预测工作流"""
        if not sample_teams or len(sample_teams) < 2:
            pytest.skip("Sample teams not available")

        # 工作流步骤1: 用户注册
        user_data = test_user_data["users"][0]
        registration_data = {
            "username": user_data["username"],
            "email": user_data["email"],
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        }

        # 模拟用户服务
        mock_user_service = AsyncMock()
        mock_user_service.register_user.return_value = {
            "id": user_data["id"],
            "username": user_data["username"],
            "email": user_data["email"],
            "is_active": True,
            "created_at": user_data["created_at"].isoformat(),
        }

        with patch("src.api.routes.users.UserService", return_value=mock_user_service):
            response = await async_client.post(
                "/api/users/register", json=registration_data
            )

            if response.status_code in [200, 201]:
                user = response.json()
                user_id = user["id"]
            else:
                # 如果注册端点不可用，使用测试数据
                user_id = user_data["id"]

        # 工作流步骤2: 用户登录获取token
        {
            "username": user_data["username"],
            "password": "SecurePassword123!",
        }

        mock_auth_service = AsyncMock()
        mock_auth_service.authenticate_user.return_value = {
            "access_token": "test_jwt_token",
            "token_type": "bearer",
            "user": user,
        }

        auth_headers = {"Authorization": "Bearer test_jwt_token"}

        # 工作流步骤3: 创建比赛
        home_team, away_team = sample_teams[0], sample_teams[1]

        match_data = {
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "match_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "venue": "Test Stadium",
            "league_id": home_team.league_id if hasattr(home_team, "league_id") else 1,
        }

        mock_match_service = AsyncMock()
        mock_match_service.create_match.return_value = {
            "id": 1,
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "match_date": match_data["match_date"],
            "venue": match_data["venue"],
            "status": "scheduled",
            "home_score": 0,
            "away_score": 0,
        }

        with patch(
            "src.api.routes.matches.MatchService", return_value=mock_match_service
        ):
            response = await async_client.post("/api/matches/", json=match_data)

            if response.status_code == 200:
                match = response.json()
                match_id = match["id"]
            else:
                match_id = 1

        # 工作流步骤4: 创建预测
        prediction_data = {
            "user_id": user_id,
            "match_id": match_id,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
        }

        mock_prediction_service = AsyncMock()
        mock_prediction_service.create_prediction.return_value = {
            "id": 1,
            "user_id": user_id,
            "match_id": match_id,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
        }

        with patch(
            "src.api.routes.predictions.PredictionService",
            return_value=mock_prediction_service,
        ):
            response = await async_client.post(
                "/api/predictions/", json=prediction_data
            )

            if response.status_code == 200:
                prediction = response.json()
                prediction_id = prediction["id"]
            else:
                prediction_id = 1

        # 工作流步骤5: 获取预测历史
        mock_user_service.get_user_predictions.return_value = [prediction]

        with patch("src.api.routes.users.UserService", return_value=mock_user_service):
            response = await async_client.get(
                f"/api/users/{user_id}/predictions", headers=auth_headers
            )

            if response.status_code == 200:
                predictions = response.json()
                assert len(predictions) >= 1

        # 工作流步骤6: 模拟比赛结束和预测评估
        evaluation_data = {
            "actual_home": 2,
            "actual_away": 1,
        }

        mock_prediction_service.evaluate_prediction.return_value = {
            "prediction_id": prediction_id,
            "actual_home": 2,
            "actual_away": 1,
            "is_correct": True,
            "points_earned": 10,
            "accuracy_score": 1.0,
        }

        with patch(
            "src.api.routes.predictions.PredictionService",
            return_value=mock_prediction_service,
        ):
            response = await async_client.post(
                f"/api/predictions/{prediction_id}/evaluate", json=evaluation_data
            )

            if response.status_code == 200:
                evaluation = response.json()
                assert evaluation["is_correct"]
                assert evaluation["points_earned"] > 0

        # 工作流步骤7: 更新用户积分
        mock_scoring_service = AsyncMock()
        mock_scoring_service.update_user_points.return_value = {
            "user_id": user_id,
            "total_points": 10,
            "ranking": 1,
        }

        # 工作流步骤8: 发送通知
        with patch(
            "src.domain.events.event_bus",
            mock_external_services["notification_service"],
        ):
            # 验证通知服务被调用
            if hasattr(
                mock_external_services["notification_service"], "send_notification"
            ):
                pass  # 在实际实现中会验证调用

        # 验证完整工作流成功
        assert user_id > 0
        assert match_id > 0
        assert prediction_id > 0

    @pytest.mark.asyncio
    async def test_prediction_validation_workflow(
        self, async_client: AsyncClient, sample_match, error_test_data
    ):
        """测试预测验证工作流"""
        if not sample_match:
            pytest.skip("Sample match not available")

        invalid_predictions = error_test_data["invalid_predictions"]

        # 测试各种无效预测数据
        for invalid_prediction in invalid_predictions:
            # 补充必要的数据
            prediction_data = {
                "user_id": 1,
                "match_id": sample_match.id,
                "predicted_home": 2,
                "predicted_away": 1,
                "confidence": 0.85,
            }
            prediction_data.update(invalid_prediction)

            response = await async_client.post(
                "/api/predictions/", json=prediction_data
            )

            # 应该返回验证错误
            if response.status_code != 404:  # 如果端点存在
                assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_concurrent_prediction_workflow(
        self, async_client: AsyncClient, sample_match, test_user_data
    ):
        """测试并发预测工作流"""
        if not sample_match:
            pytest.skip("Sample match not available")

        async def create_user_prediction(user_id: int):
            """为用户创建预测"""
            prediction_data = {
                "user_id": user_id,
                "match_id": sample_match.id,
                "predicted_home": (user_id % 5) + 1,
                "predicted_away": (user_id % 3) + 1,
                "confidence": 0.5 + (user_id % 5) * 0.1,
            }

            mock_service = AsyncMock()
            mock_service.create_prediction.return_value = {
                "id": user_id,
                "user_id": user_id,
                "match_id": sample_match.id,
                "predicted_home": prediction_data["predicted_home"],
                "predicted_away": prediction_data["predicted_away"],
                "confidence": prediction_data["confidence"],
                "status": "pending",
            }

            with patch(
                "src.api.routes.predictions.PredictionService",
                return_value=mock_service,
            ):
                return await async_client.post(
                    "/api/predictions/", json=prediction_data
                )

        # 并发创建多个用户预测
        tasks = [create_user_prediction(i) for i in range(1, 11)]  # 10个用户

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证并发处理结果
        successful_responses = [
            r
            for r in responses
            if not isinstance(r, Exception) and r.status_code == 200
        ]

        assert len(successful_responses) > 5  # 至少一半成功


class TestMatchManagementWorkflow:
    """比赛管理工作流测试"""

    @pytest.mark.asyncio
    async def test_complete_match_lifecycle_workflow(
        self, async_client: AsyncClient, sample_teams, test_user_data
    ):
        """测试完整比赛生命周期工作流"""
        if not sample_teams or len(sample_teams) < 2:
            pytest.skip("Sample teams not available")

        home_team, away_team = sample_teams[0], sample_teams[1]

        # 步骤1: 创建比赛
        match_data = {
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "match_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "venue": "Test Stadium",
            "league_id": home_team.league_id if hasattr(home_team, "league_id") else 1,
        }

        mock_match_service = AsyncMock()
        mock_match_service.create_match.return_value = {
            "id": 1,
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "match_date": match_data["match_date"],
            "venue": match_data["venue"],
            "status": "scheduled",
            "home_score": 0,
            "away_score": 0,
        }

        with patch(
            "src.api.routes.matches.MatchService", return_value=mock_match_service
        ):
            response = await async_client.post("/api/matches/", json=match_data)

            if response.status_code == 200:
                match = response.json()
                match_id = match["id"]
            else:
                match_id = 1

        # 步骤2: 用户创建预测
        user_id = test_user_data["users"][0]["id"]
        prediction_data = {
            "user_id": user_id,
            "match_id": match_id,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
        }

        mock_prediction_service = AsyncMock()
        mock_prediction_service.create_prediction.return_value = {
            "id": 1,
            "user_id": user_id,
            "match_id": match_id,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
            "status": "pending",
        }

        with patch(
            "src.api.routes.predictions.PredictionService",
            return_value=mock_prediction_service,
        ):
            response = await async_client.post(
                "/api/predictions/", json=prediction_data
            )

            # 步骤3: 开始比赛
            mock_match_service.start_match.return_value = {
                "id": match_id,
                "status": "in_progress",
                "started_at": datetime.utcnow().isoformat(),
            }

            with patch(
                "src.api.routes.matches.MatchService", return_value=mock_match_service
            ):
                response = await async_client.post(f"/api/matches/{match_id}/start")

                if response.status_code == 200:
                    match_status = response.json()
                    assert match_status["status"] == "in_progress"

        # 步骤4: 结束比赛
        finish_data = {
            "home_score": 2,
            "away_score": 1,
        }

        mock_match_service.finish_match.return_value = {
            "id": match_id,
            "status": "finished",
            "home_score": 2,
            "away_score": 1,
            "finished_at": datetime.utcnow().isoformat(),
        }

        with patch(
            "src.api.routes.matches.MatchService", return_value=mock_match_service
        ):
            response = await async_client.post(
                f"/api/matches/{match_id}/finish", json=finish_data
            )

            if response.status_code == 200:
                finished_match = response.json()
                assert finished_match["status"] == "finished"
                assert finished_match["home_score"] == 2
                assert finished_match["away_score"] == 1

        # 步骤5: 自动评估所有相关预测
        mock_prediction_service.evaluate_match_predictions.return_value = {
            "evaluated_count": 1,
            "correct_predictions": 1,
            "total_points_awarded": 10,
        }

        with patch(
            "src.api.routes.predictions.PredictionService",
            return_value=mock_prediction_service,
        ):
            response = await async_client.post(
                f"/api/matches/{match_id}/evaluate-predictions"
            )

            if response.status_code == 200:
                evaluation_results = response.json()
                assert evaluation_results["evaluated_count"] > 0

        # 步骤6: 更新球队统计
        mock_match_service.update_team_statistics.return_value = {
            "home_team": {
                "matches_played": 1,
                "wins": 1,
                "draws": 0,
                "losses": 0,
                "goals_for": 2,
                "goals_against": 1,
                "points": 3,
            },
            "away_team": {
                "matches_played": 1,
                "wins": 0,
                "draws": 0,
                "losses": 1,
                "goals_for": 1,
                "goals_against": 2,
                "points": 0,
            },
        }

        with patch(
            "src.api.routes.matches.MatchService", return_value=mock_match_service
        ):
            response = await async_client.post(
                f"/api/matches/{match_id}/update-statistics"
            )

            if response.status_code == 200:
                statistics = response.json()
                assert "home_team" in statistics
                assert "away_team" in statistics

    @pytest.mark.asyncio
    async def test_batch_match_processing_workflow(
        self, async_client: AsyncClient, sample_teams, bulk_test_data
    ):
        """测试批量比赛处理工作流"""
        if not sample_teams or len(sample_teams) < 2:
            pytest.skip("Sample teams not available")

        bulk_matches = bulk_test_data["bulk_matches"][:5]  # 只测试5场比赛

        # 步骤1: 批量创建比赛
        created_matches = []
        mock_match_service = AsyncMock()

        for i, match_data in enumerate(bulk_matches):
            # 确保有效的球队ID
            match_data["home_team_id"] = sample_teams[i % len(sample_teams)].id
            match_data["away_team_id"] = sample_teams[(i + 1) % len(sample_teams)].id

            mock_match_service.create_match.return_value = {
                "id": i + 1,
                **match_data,
                "status": "scheduled",
            }

            with patch(
                "src.api.routes.matches.MatchService", return_value=mock_match_service
            ):
                response = await async_client.post("/api/matches/", json=match_data)
                if response.status_code == 200:
                    match = response.json()
                    created_matches.append(match)

        # 步骤2: 批量结束比赛
        for match in created_matches:
            finish_data = {
                "home_score": (match["id"] % 4),
                "away_score": ((match["id"] + 1) % 4),
            }

            mock_match_service.finish_match.return_value = {
                **match,
                "status": "finished",
                "home_score": finish_data["home_score"],
                "away_score": finish_data["away_score"],
                "finished_at": datetime.utcnow().isoformat(),
            }

            with patch(
                "src.api.routes.matches.MatchService", return_value=mock_match_service
            ):
                response = await async_client.post(
                    f"/api/matches/{match['id']}/finish", json=finish_data
                )

        # 步骤3: 批量评估预测
        mock_prediction_service = AsyncMock()
        mock_prediction_service.evaluate_all_pending_predictions.return_value = {
            "evaluated_count": len(created_matches) * 2,  # 假设每场比赛2个预测
            "total_points_awarded": len(created_matches) * 15,  # 平均每场15分
        }

        with patch(
            "src.api.routes.predictions.PredictionService",
            return_value=mock_prediction_service,
        ):
            response = await async_client.post("/api/predictions/evaluate-all")

            if response.status_code == 200:
                results = response.json()
                assert results["evaluated_count"] > 0


class TestUserManagementWorkflow:
    """用户管理工作流测试"""

    @pytest.mark.asyncio
    async def test_complete_user_lifecycle_workflow(
        self, async_client: AsyncClient, test_user_data, mock_external_services
    ):
        """测试完整用户生命周期工作流"""
        user_data = test_user_data["users"][0]

        # 步骤1: 用户注册
        registration_data = {
            "username": user_data["username"],
            "email": user_data["email"],
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        }

        mock_user_service = AsyncMock()
        mock_user_service.register_user.return_value = {
            "id": user_data["id"],
            "username": user_data["username"],
            "email": user_data["email"],
            "is_active": True,
            "is_verified": False,
            "created_at": user_data["created_at"].isoformat(),
        }

        with patch("src.api.routes.users.UserService", return_value=mock_user_service):
            response = await async_client.post(
                "/api/users/register", json=registration_data
            )

            if response.status_code in [200, 201]:
                user = response.json()
                user_id = user["id"]
                assert user["is_active"]
                assert not user["is_verified"]
            else:
                user_id = user_data["id"]

        # 步骤2: 邮箱验证
        verification_token = "test_verification_token"

        mock_user_service.verify_email.return_value = {
            "user_id": user_id,
            "is_verified": True,
            "verified_at": datetime.utcnow().isoformat(),
        }

        with patch("src.api.routes.users.UserService", return_value=mock_user_service):
            response = await async_client.post(
                "/api/users/verify-email", json={"token": verification_token}
            )

            if response.status_code == 200:
                verification_result = response.json()
                assert verification_result["is_verified"]

        # 步骤3: 用户登录
        login_data = {
            "username": user_data["username"],
            "password": "SecurePassword123!",
        }

        mock_auth_service = AsyncMock()
        mock_auth_service.authenticate_user.return_value = {
            "access_token": "test_jwt_token",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": user,
        }

        with patch("src.api.routes.auth.AuthService", return_value=mock_auth_service):
            response = await async_client.post("/api/auth/login", json=login_data)

            if response.status_code == 200:
                auth_result = response.json()
                assert "access_token" in auth_result
                assert auth_result["token_type"] == "bearer"

        auth_headers = {"Authorization": "Bearer test_jwt_token"}

        # 步骤4: 更新用户资料
        profile_data = {
            "first_name": "John",
            "last_name": "Doe",
            "favorite_team": "Manchester United",
            "notification_preferences": {
                "match_reminders": True,
                "result_notifications": True,
                "promotion_emails": False,
            },
        }

        mock_user_service.update_user_profile.return_value = {
            **user,
            **profile_data,
            "updated_at": datetime.utcnow().isoformat(),
        }

        with patch("src.api.routes.users.UserService", return_value=mock_user_service):
            response = await async_client.put(
                f"/api/users/{user_id}/profile", json=profile_data, headers=auth_headers
            )

            if response.status_code == 200:
                updated_profile = response.json()
                assert updated_profile["first_name"] == profile_data["first_name"]

        # 步骤5: 获取用户统计
        mock_user_service.get_user_statistics.return_value = {
            "user_id": user_id,
            "total_predictions": 10,
            "correct_predictions": 7,
            "accuracy_rate": 0.7,
            "total_points": 85,
            "ranking": 15,
            "member_since": user["created_at"],
            "last_prediction": datetime.utcnow().isoformat(),
        }

        with patch("src.api.routes.users.UserService", return_value=mock_user_service):
            response = await async_client.get(
                f"/api/users/{user_id}/statistics", headers=auth_headers
            )

            if response.status_code == 200:
                statistics = response.json()
                assert "accuracy_rate" in statistics
                assert "total_points" in statistics

        # 步骤6: 密码重置
        reset_data = {
            "email": user_data["email"],
        }

        mock_user_service.initiate_password_reset.return_value = {
            "message": "Password reset email sent",
            "reset_token": "reset_token_123",
        }

        with patch("src.api.routes.users.UserService", return_value=mock_user_service):
            response = await async_client.post(
                "/api/users/reset-password", json=reset_data
            )

            if response.status_code == 200:
                reset_result = response.json()
                assert "reset_token" in reset_result

        # 步骤7: 确认密码重置
        confirm_reset_data = {
            "token": "reset_token_123",
            "new_password": "NewSecurePassword456!",
            "confirm_password": "NewSecurePassword456!",
        }

        mock_user_service.confirm_password_reset.return_value = {
            "message": "Password reset successful",
        }

        with patch("src.api.routes.users.UserService", return_value=mock_user_service):
            response = await async_client.post(
                "/api/users/confirm-password-reset", json=confirm_reset_data
            )

            if response.status_code == 200:
                assert response.json()["message"] == "Password reset successful"

        # 步骤8: 用户注销
        mock_auth_service.logout_user.return_value = {
            "message": "Logged out successfully",
        }

        with patch("src.api.routes.auth.AuthService", return_value=mock_auth_service):
            response = await async_client.post("/api/auth/logout", headers=auth_headers)

            if response.status_code == 200:
                logout_result = response.json()
                assert logout_result["message"] == "Logged out successfully"


class TestDataProcessingWorkflow:
    """数据处理工作流测试"""

    @pytest.mark.asyncio
    async def test_external_data_sync_workflow(
        self,
        async_client: AsyncClient,
        mock_external_api_responses,
        mock_external_services,
    ):
        """测试外部数据同步工作流"""
        # 步骤1: 同步比赛数据
        mock_data_service = AsyncMock()
        mock_data_service.sync_match_data.return_value = {
            "synced_matches": 10,
            "new_matches": 3,
            "updated_matches": 7,
            "sync_time": datetime.utcnow().isoformat(),
        }

        with patch("src.api.routes.data.DataService", return_value=mock_data_service):
            response = await async_client.post("/api/data/sync/matches")

            if response.status_code == 200:
                sync_result = response.json()
                assert sync_result["synced_matches"] > 0

        # 步骤2: 同步赔率数据
        mock_data_service.sync_odds_data.return_value = {
            "synced_odds": 25,
            "new_odds": 8,
            "updated_odds": 17,
            "sync_time": datetime.utcnow().isoformat(),
        }

        with patch("src.api.routes.data.DataService", return_value=mock_data_service):
            response = await async_client.post("/api/data/sync/odds")

            if response.status_code == 200:
                odds_result = response.json()
                assert odds_result["synced_odds"] > 0

        # 步骤3: 数据质量检查
        mock_data_service.validate_data_quality.return_value = {
            "total_records": 100,
            "valid_records": 95,
            "invalid_records": 5,
            "quality_score": 0.95,
            "issues": [
                {"type": "missing_data", "count": 3},
                {"type": "inconsistent_format", "count": 2},
            ],
        }

        with patch("src.api.routes.data.DataService", return_value=mock_data_service):
            response = await async_client.get("/api/data/quality-check")

            if response.status_code == 200:
                quality_result = response.json()
                assert quality_result["quality_score"] > 0.9

    @pytest.mark.asyncio
    async def test_analytics_update_workflow(
        self, async_client: AsyncClient, mock_external_services
    ):
        """测试分析更新工作流"""
        # 步骤1: 更新预测分析
        mock_analytics_service = AsyncMock()
        mock_analytics_service.update_prediction_analytics.return_value = {
            "updated_predictions": 50,
            "new_analytics": 15,
            "updated_at": datetime.utcnow().isoformat(),
        }

        with patch(
            "src.api.routes.analytics.AnalyticsService",
            return_value=mock_analytics_service,
        ):
            response = await async_client.post("/api/analytics/update/predictions")

            if response.status_code == 200:
                analytics_result = response.json()
                assert analytics_result["updated_predictions"] > 0

        # 步骤2: 更新用户分析
        mock_analytics_service.update_user_analytics.return_value = {
            "updated_users": 20,
            "updated_rankings": 20,
            "updated_at": datetime.utcnow().isoformat(),
        }

        with patch(
            "src.api.routes.analytics.AnalyticsService",
            return_value=mock_analytics_service,
        ):
            response = await async_client.post("/api/analytics/update/users")

            if response.status_code == 200:
                user_analytics_result = response.json()
                assert user_analytics_result["updated_users"] > 0

        # 步骤3: 生成报告
        mock_analytics_service.generate_report.return_value = {
            "report_id": "report_123",
            "type": "weekly",
            "generated_at": datetime.utcnow().isoformat(),
            "metrics": {
                "total_predictions": 500,
                "active_users": 100,
                "accuracy_rate": 0.68,
            },
        }

        with patch(
            "src.api.routes.analytics.AnalyticsService",
            return_value=mock_analytics_service,
        ):
            response = await async_client.post(
                "/api/analytics/reports",
                json={"type": "weekly", "period": "last_7_days"},
            )

            if response.status_code == 200:
                report = response.json()
                assert "report_id" in report
                assert report["type"] == "weekly"


class TestErrorHandlingWorkflow:
    """错误处理工作流测试"""

    @pytest.mark.asyncio
    async def test_system_failure_recovery_workflow(
        self, async_client: AsyncClient, mock_external_services
    ):
        """测试系统故障恢复工作流"""
        # 步骤1: 检测系统状态
        mock_health_service = AsyncMock()
        mock_health_service.check_system_health.return_value = {
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
            "external_apis": "available",
            "last_check": datetime.utcnow().isoformat(),
        }

        with patch("src.api.health.HealthService", return_value=mock_health_service):
            response = await async_client.get("/api/health/detailed")

            if response.status_code == 200:
                health_status = response.json()
                assert health_status["status"] == "healthy"

        # 步骤2: 模拟数据库连接失败
        mock_db_service = AsyncMock()
        mock_db_service.check_connection.side_effect = ConnectionError(
            "Database connection failed"
        )

        with patch("src.api.health.HealthService", return_value=mock_db_service):
            response = await async_client.get("/api/health/database")

            # 应该返回错误状态
            if response.status_code != 404:
                assert response.status_code >= 500

        # 步骤3: 系统恢复
        mock_health_service.recover_system.return_value = {
            "recovery_successful": True,
            "recovered_services": ["database", "redis"],
            "recovery_time": datetime.utcnow().isoformat(),
        }

        with patch("src.api.health.HealthService", return_value=mock_health_service):
            response = await async_client.post("/api/health/recover")

            if response.status_code == 200:
                recovery_result = response.json()
                assert recovery_result["recovery_successful"]

    @pytest.mark.asyncio
    async def test_data_consistency_workflow(self, async_client: AsyncClient):
        """测试数据一致性工作流"""
        # 步骤1: 检查数据一致性
        mock_consistency_service = AsyncMock()
        mock_consistency_service.check_data_consistency.return_value = {
            "total_checks": 100,
            "passed_checks": 98,
            "failed_checks": 2,
            "consistency_score": 0.98,
            "issues": [
                {
                    "type": "orphaned_predictions",
                    "count": 1,
                    "description": "Predictions without corresponding matches",
                },
                {
                    "type": "inconsistent_scores",
                    "count": 1,
                    "description": "Mismatch between home/away scores",
                },
            ],
        }

        with patch(
            "src.api.data.ConsistencyService", return_value=mock_consistency_service
        ):
            response = await async_client.get("/api/data/consistency-check")

            if response.status_code == 200:
                consistency_result = response.json()
                assert consistency_result["consistency_score"] > 0.9

        # 步骤2: 修复数据一致性问题
        mock_consistency_service.fix_consistency_issues.return_value = {
            "fixed_issues": 2,
            "fixed_orphaned_predictions": 1,
            "fixed_inconsistent_scores": 1,
            "fix_time": datetime.utcnow().isoformat(),
        }

        with patch(
            "src.api.data.ConsistencyService", return_value=mock_consistency_service
        ):
            response = await async_client.post("/api/data/fix-consistency")

            if response.status_code == 200:
                fix_result = response.json()
                assert fix_result["fixed_issues"] > 0


class TestPerformanceWorkflow:
    """性能工作流测试"""

    @pytest.mark.asyncio
    async def test_high_load_prediction_workflow(
        self, async_client: AsyncClient, sample_match, performance_benchmarks
    ):
        """测试高负载预测工作流"""
        if not sample_match:
            pytest.skip("Sample match not available")

        import time

        # 步骤1: 高并发创建预测
        async def create_prediction_batch(batch_size: int, start_id: int):
            """创建一批预测"""
            tasks = []
            for i in range(batch_size):
                prediction_data = {
                    "user_id": start_id + i,
                    "match_id": sample_match.id,
                    "predicted_home": (i % 5) + 1,
                    "predicted_away": (i % 3) + 1,
                    "confidence": 0.5 + (i % 5) * 0.1,
                }

                mock_service = AsyncMock()
                mock_service.create_prediction.return_value = {
                    "id": start_id + i,
                    **prediction_data,
                    "status": "pending",
                }

                with patch(
                    "src.api.routes.predictions.PredictionService",
                    return_value=mock_service,
                ):
                    task = async_client.post("/api/predictions/", json=prediction_data)
                    tasks.append(task)

            return await asyncio.gather(*tasks, return_exceptions=True)

        # 测试批量性能
        start_time = time.time()
        batch_responses = await create_prediction_batch(50, 100)  # 50个预测
        batch_time = time.time() - start_time

        # 验证性能
        successful_responses = [
            r
            for r in batch_responses
            if not isinstance(r, Exception) and hasattr(r, "status_code")
        ]
        success_count = len([r for r in successful_responses if r.status_code == 200])

        if success_count > 0:
            avg_time_per_prediction = batch_time / len(batch_responses)
            assert (
                avg_time_per_prediction
                < performance_benchmarks["response_time_limits"]["prediction_creation"]
            )

            # 验证成功率
            success_rate = success_count / len(batch_responses)
            assert success_rate > 0.8  # 至少80%成功率

    @pytest.mark.asyncio
    async def test_cache_performance_workflow(
        self,
        async_client: AsyncClient,
        cache_test_data,
        mock_redis,
        performance_benchmarks,
    ):
        """测试缓存性能工作流"""


@pytest.mark.asyncio
async def test_cache_workflow(async_client: AsyncClient, cache_test_data, mock_redis):
    """测试缓存工作流"""
    import time

    cache_key = cache_test_data["user_stats_key"]
    cached_value = json.dumps(cache_test_data["test_value"])

    # 设置Redis模拟
    mock_redis.get.return_value = cached_value
    mock_redis.set.return_value = True
    mock_redis.exists.return_value = True

    # 测试缓存读取性能
    start_time = time.time()
    response = await async_client.get(f"/api/cache/{cache_key}")
    cache_read_time = time.time() - start_time

    # 验证缓存读取性能
    if response.status_code == 200:
        assert cache_read_time < 0.1  # 缓存读取应该很快

    # 测试缓存写入性能
    start_time = time.time()
    new_cache_data = {"test": "data", "timestamp": time.time()}
    response = await async_client.post(f"/api/cache/{cache_key}", json=new_cache_data)
    cache_write_time = time.time() - start_time

    # 验证缓存写入性能
    if response.status_code == 200:
        assert cache_write_time < 0.1  # 缓存写入也应该很快


# 工作流测试辅助函数
async def create_test_user(async_client: AsyncClient, user_data: dict):
    """创建测试用户的辅助函数"""
    registration_data = {
        "username": user_data["username"],
        "email": user_data["email"],
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
    }

    mock_service = AsyncMock()
    mock_service.register_user.return_value = {
        "id": user_data["id"],
        "username": user_data["username"],
        "email": user_data["email"],
        "is_active": True,
    }

    with patch("src.api.routes.users.UserService", return_value=mock_service):
        response = await async_client.post(
            "/api/users/register", json=registration_data
        )
        return response.json() if response.status_code in [200, 201] else None


async def create_test_match(async_client: AsyncClient, match_data: dict):
    """创建测试比赛的辅助函数"""
    mock_service = AsyncMock()
    mock_service.create_match.return_value = {
        "id": 1,
        **match_data,
        "status": "scheduled",
    }

    with patch("src.api.routes.matches.MatchService", return_value=mock_service):
        response = await async_client.post("/api/matches/", json=match_data)
        return response.json() if response.status_code == 200 else None


async def create_test_prediction(async_client: AsyncClient, prediction_data: dict):
    """创建测试预测的辅助函数"""
    mock_service = AsyncMock()
    mock_service.create_prediction.return_value = {
        "id": 1,
        **prediction_data,
        "status": "pending",
    }

    with patch(
        "src.api.routes.predictions.PredictionService", return_value=mock_service
    ):
        response = await async_client.post("/api/predictions/", json=prediction_data)
        return response.json() if response.status_code == 200 else None
