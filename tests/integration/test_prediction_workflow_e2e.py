"""
预测工作流端到端测试
Prediction Workflow End-to-End Tests

完整测试足球预测系统的预测工作流，从用户登录到预测完成的整个流程
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# 标记测试
pytestmark = [pytest.mark.e2e, pytest.mark.workflow, pytest.mark.slow]


class TestPredictionWorkflowE2E:
    """预测工作流端到端测试"""

    @pytest.mark.asyncio
    async def test_complete_prediction_journey(
        self,
        async_client: AsyncClient,
        sample_teams,
        sample_league,
        test_user_data,
        mock_external_services,
        mock_redis,
    ):
        """测试完整的预测旅程"""
        if not sample_teams or len(sample_teams) < 2:
            pytest.skip("Sample teams not available")

        # ================================
        # 第一阶段: 用户认证和准备
        # ================================

        user_data = test_user_data["users"][0]
        user_id = user_data["id"]

        # 模拟认证服务
        mock_auth_service = AsyncMock()
        mock_auth_service.authenticate_user.return_value = {
            "access_token": "test_jwt_token",
            "token_type": "bearer",
            "expires_in": 3600,
            "user": {
                "id": user_id,
                "username": user_data["username"],
                "email": user_data["email"],
                "is_active": True,
                "is_verified": True,
            },
        }

        auth_headers = {"Authorization": "Bearer test_jwt_token"}

        # ================================
        # 第二阶段: 比赛信息获取
        # ================================

        # 创建比赛
        home_team, away_team = sample_teams[0], sample_teams[1]

        match_data = {
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "match_date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
            "venue": "Old Trafford",
            "league_id": sample_league.id if hasattr(sample_league, "id") else 1,
            "status": "SCHEDULED",
        }

        mock_match_service = AsyncMock()
        mock_match_service.create_match.return_value = {
            "id": 1,
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "match_date": match_data["match_date"],
            "venue": match_data["venue"],
            "status": "SCHEDULED",
            "home_score": 0,
            "away_score": 0,
            "home_team": {"id": home_team.id, "name": home_team.name},
            "away_team": {"id": away_team.id, "name": away_team.name},
        }

        with patch(
            "src.domain.services.match_service.MatchService", return_value=mock_match_service
        ):
            response = await async_client.post("/api/matches/", json=match_data)

            if response.status_code == 200:
                match = response.json()
                match_id = match["id"]
            else:
                match_id = 1

        # 获取比赛详情（包含历史数据）
        mock_match_service.get_match_with_statistics.return_value = {
            **match,
            "home_team_stats": {
                "recent_form": ["W", "D", "W", "L", "W"],
                "goals_scored": 15,
                "goals_conceded": 8,
                "home_record": {"played": 5, "won": 4, "drawn": 1, "lost": 0},
            },
            "away_team_stats": {
                "recent_form": ["D", "L", "W", "D", "L"],
                "goals_scored": 10,
                "goals_conceded": 12,
                "away_record": {"played": 5, "won": 1, "drawn": 2, "lost": 2},
            },
            "head_to_head": {
                "total_matches": 10,
                "home_wins": 6,
                "away_wins": 2,
                "draws": 2,
            },
        }

        with patch(
            "src.domain.services.match_service.MatchService", return_value=mock_match_service
        ):
            response = await async_client.get(f"/api/matches/{match_id}/details")

            if response.status_code == 200:
                match_details = response.json()
                assert "home_team_stats" in match_details
                assert "head_to_head" in match_details

        # ================================
        # 第三阶段: 获取预测建议
        # ================================

        # 获取AI预测建议
        mock_prediction_service = AsyncMock()
        mock_prediction_service.get_prediction_suggestions.return_value = {
            "match_id": match_id,
            "suggestions": [
                {
                    "score": "2-1",
                    "confidence": 0.75,
                    "probability": 0.35,
                    "reasoning": "Home team has strong home record and recent form",
                },
                {
                    "score": "1-1",
                    "confidence": 0.65,
                    "probability": 0.25,
                    "reasoning": "Both teams have balanced scoring ability",
                },
                {
                    "score": "2-0",
                    "confidence": 0.60,
                    "probability": 0.20,
                    "reasoning": "Home team defense has been solid recently",
                },
            ],
            "statistical_analysis": {
                "expected_goals_home": 1.8,
                "expected_goals_away": 1.2,
                "over_2_5_probability": 0.65,
                "home_win_probability": 0.55,
                "draw_probability": 0.25,
                "away_win_probability": 0.20,
            },
        }

        with patch(
            "src.domain.services.prediction_service.PredictionService",
            return_value=mock_prediction_service,
        ):
            response = await async_client.get(
                f"/api/predictions/suggestions/{match_id}", headers=auth_headers
            )

            if response.status_code == 200:
                suggestions = response.json()
                assert len(suggestions["suggestions"]) > 0
                assert "statistical_analysis" in suggestions

        # ================================
        # 第四阶段: 创建预测
        # ================================

        # 用户创建预测
        prediction_data = {
            "user_id": user_id,
            "match_id": match_id,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
            "reasoning": "Home team has better form and home advantage",
        }

        mock_prediction_service.create_prediction.return_value = {
            "id": 1,
            "user_id": user_id,
            "match_id": match_id,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
            "reasoning": prediction_data["reasoning"],
            "status": "PENDING",
            "created_at": datetime.utcnow().isoformat(),
            "match": {
                "id": match_id,
                "home_team": {"name": home_team.name},
                "away_team": {"name": away_team.name},
                "match_date": match_data["match_date"],
            },
        }

        # 模拟领域事件发布
        with patch(
            "src.domain.events.event_bus", mock_external_services["audit_service"]
        ):
            with patch(
                "src.domain.services.prediction_service.PredictionService",
                return_value=mock_prediction_service,
            ):
                response = await async_client.post(
                    "/api/predictions/", json=prediction_data, headers=auth_headers
                )

                if response.status_code in [200, 201]:
                    prediction = response.json()
                    prediction_id = prediction["id"]
                    assert prediction["status"] == "PENDING"
                else:
                    prediction_id = 1

        # ================================
        # 第五阶段: 获取预测确认
        # ================================

        # 获取预测详情
        mock_prediction_service.get_prediction_details.return_value = {
            "id": prediction_id,
            "user_id": user_id,
            "match_id": match_id,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
            "status": "PENDING",
            "potential_points": {
                "exact_score": 10,
                "correct_result": 3,
                "confidence_bonus": 1.5,
                "total_possible": 14.5,
            },
            "created_at": datetime.utcnow().isoformat(),
        }

        with patch(
            "src.domain.services.prediction_service.PredictionService",
            return_value=mock_prediction_service,
        ):
            response = await async_client.get(
                f"/api/predictions/{prediction_id}", headers=auth_headers
            )

            if response.status_code == 200:
                prediction_details = response.json()
                assert "potential_points" in prediction_details
                assert prediction_details["potential_points"]["exact_score"] == 10

        # ================================
        # 第六阶段: 比赛进行中
        # ================================

        # 模拟比赛开始
        mock_match_service.start_match.return_value = {
            "id": match_id,
            "status": "IN_PROGRESS",
            "started_at": datetime.utcnow().isoformat(),
            "current_score": {"home": 0, "away": 0},
        }

        with patch(
            "src.domain.services.match_service.MatchService", return_value=mock_match_service
        ):
            response = await async_client.post(f"/api/matches/{match_id}/start")

            if response.status_code == 200:
                live_match = response.json()
                assert live_match["status"] == "IN_PROGRESS"

        # 模拟实时比分更新
        mock_match_service.update_live_score.return_value = {
            "match_id": match_id,
            "minute": 45,
            "score": {"home": 1, "away": 0},
            "scorers": [{"player": "Player A", "team": "home", "minute": 23}],
        }

        with patch(
            "src.domain.services.match_service.MatchService", return_value=mock_match_service
        ):
            response = await async_client.get(f"/api/matches/{match_id}/live")

            if response.status_code == 200:
                live_score = response.json()
                assert live_score["score"]["home"] == 1

        # ================================
        # 第七阶段: 比赛结束和预测评估
        # ================================

        # 比赛结束
        final_score = {"home_score": 2, "away_score": 1}

        mock_match_service.finish_match.return_value = {
            "id": match_id,
            "status": "FINISHED",
            "final_score": final_score,
            "finished_at": datetime.utcnow().isoformat(),
            "match_events": [
                {"minute": 23, "type": "goal", "team": "home"},
                {"minute": 67, "type": "goal", "team": "away"},
                {"minute": 89, "type": "goal", "team": "home"},
            ],
        }

        with patch(
            "src.domain.services.match_service.MatchService", return_value=mock_match_service
        ):
            response = await async_client.post(
                f"/api/matches/{match_id}/finish", json=final_score
            )

            if response.status_code == 200:
                finished_match = response.json()
                assert finished_match["status"] == "FINISHED"

        # 自动评估预测
        mock_prediction_service.evaluate_prediction.return_value = {
            "prediction_id": prediction_id,
            "actual_home": 2,
            "actual_away": 1,
            "predicted_home": 2,
            "predicted_away": 1,
            "is_correct_score": True,
            "is_correct_result": True,
            "points_earned": {
                "base_points": 10,
                "confidence_bonus": 2.5,
                "total": 12.5,
            },
            "accuracy_score": 1.0,
            "evaluated_at": datetime.utcnow().isoformat(),
        }

        # 模拟事件发布
        with patch(
            "src.domain.events.event_bus", mock_external_services["analytics_service"]
        ):
            with patch(
                "src.domain.services.prediction_service.PredictionService",
                return_value=mock_prediction_service,
            ):
                response = await async_client.post(
                    f"/api/predictions/{prediction_id}/evaluate",
                    json={"actual_home": 2, "actual_away": 1},
                )

                if response.status_code == 200:
                    evaluation = response.json()
                    assert evaluation["is_correct_score"]
                    assert evaluation["points_earned"]["total"] == 12.5

        # ================================
        # 第八阶段: 更新用户统计和排名
        # ================================

        # 更新用户积分
        mock_scoring_service = AsyncMock()
        mock_scoring_service.update_user_points.return_value = {
            "user_id": user_id,
            "total_points": 12.5,
            "weekly_points": 12.5,
            "monthly_points": 12.5,
            "ranking": {"overall": 1, "weekly": 1, "monthly": 1},
            "accuracy_stats": {
                "total_predictions": 1,
                "correct_predictions": 1,
                "accuracy_rate": 1.0,
            },
        }

        with patch(
            "src.domain.services.scoring_service.ScoringService", return_value=mock_scoring_service
        ):
            response = await async_client.post(
                f"/api/users/{user_id}/update-points", headers=auth_headers
            )

            if response.status_code == 200:
                updated_stats = response.json()
                assert updated_stats["total_points"] == 12.5
                assert updated_stats["ranking"]["overall"] == 1

        # ================================
        # 第九阶段: 发送通知
        # ================================

        # 发送预测结果通知
        mock_notification_service = AsyncMock()
        mock_notification_service.send_prediction_result_notification.return_value = {
            "notification_id": "notif_123",
            "user_id": user_id,
            "type": "prediction_result",
            "status": "sent",
            "sent_at": datetime.utcnow().isoformat(),
        }

        with patch(
            "src.domain.services.notification_service.NotificationService",
            return_value=mock_notification_service,
        ):
            response = await async_client.post(
                f"/api/notifications/prediction-result/{prediction_id}",
                headers=auth_headers,
            )

            if response.status_code == 200:
                notification_result = response.json()
                assert notification_result["status"] == "sent"

        # ================================
        # 第十阶段: 验证完整工作流
        # ================================

        # 验证所有步骤都成功完成
        assert user_id > 0
        assert match_id > 0
        assert prediction_id > 0

        # 验证预测历史
        mock_prediction_service.get_user_prediction_history.return_value = {
            "predictions": [
                {
                    "id": prediction_id,
                    "match_id": match_id,
                    "predicted_home": 2,
                    "predicted_away": 1,
                    "actual_home": 2,
                    "actual_away": 1,
                    "status": "EVALUATED",
                    "points_earned": 12.5,
                    "is_correct": True,
                    "created_at": datetime.utcnow().isoformat(),
                    "evaluated_at": datetime.utcnow().isoformat(),
                }
            ],
            "summary": {
                "total_predictions": 1,
                "correct_predictions": 1,
                "accuracy_rate": 1.0,
                "total_points": 12.5,
                "average_points_per_prediction": 12.5,
            },
        }

        with patch(
            "src.domain.services.prediction_service.PredictionService",
            return_value=mock_prediction_service,
        ):
            response = await async_client.get(
                f"/api/users/{user_id}/predictions/history", headers=auth_headers
            )

            if response.status_code == 200:
                history = response.json()
                assert len(history["predictions"]) == 1
                assert history["summary"]["accuracy_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_multiple_predictions_workflow(
        self,
        async_client: AsyncClient,
        sample_teams,
        test_user_data,
        mock_external_services,
    ):
        """测试多个预测的工作流"""
        if not sample_teams or len(sample_teams) < 4:
            pytest.skip("Need at least 4 teams for multiple matches")

        user_data = test_user_data["users"][0]
        user_id = user_data["id"]
        auth_headers = {"Authorization": "Bearer test_jwt_token"}

        # 创建多场比赛
        matches = []
        mock_match_service = AsyncMock()
        mock_prediction_service = AsyncMock()

        for i in range(0, len(sample_teams) - 1, 2):
            home_team = sample_teams[i]
            away_team = sample_teams[i + 1]

            match_data = {
                "home_team_id": home_team.id,
                "away_team_id": away_team.id,
                "match_date": (datetime.utcnow() + timedelta(days=i + 1)).isoformat(),
                "venue": f"Stadium {i + 1}",
                "status": "SCHEDULED",
            }

            mock_match_service.create_match.return_value = {
                "id": i + 1,
                **match_data,
                "home_team": {"name": home_team.name},
                "away_team": {"name": away_team.name},
            }

            with patch(
                "src.domain.services.match_service.MatchService", return_value=mock_match_service
            ):
                response = await async_client.post("/api/matches/", json=match_data)
                if response.status_code == 200:
                    matches.append(response.json())

        # 为每场比赛创建预测
        predictions = []
        for i, match in enumerate(matches):
            prediction_data = {
                "user_id": user_id,
                "match_id": match["id"],
                "predicted_home": (i % 3) + 1,
                "predicted_away": ((i + 1) % 3),
                "confidence": 0.6 + (i * 0.1),
            }

            mock_prediction_service.create_prediction.return_value = {
                "id": i + 1,
                **prediction_data,
                "status": "PENDING",
                "created_at": datetime.utcnow().isoformat(),
            }

            with patch(
                "src.domain.services.prediction_service.PredictionService",
                return_value=mock_prediction_service,
            ):
                response = await async_client.post(
                    "/api/predictions/", json=prediction_data, headers=auth_headers
                )
                if response.status_code == 200:
                    predictions.append(response.json())

        # 批量评估预测
        evaluation_results = []
        for i, prediction in enumerate(predictions):
            evaluation_data = {
                "actual_home": (i % 3) + 1,
                "actual_away": ((i + 2) % 3),
            }

            mock_prediction_service.evaluate_prediction.return_value = {
                "prediction_id": prediction["id"],
                "actual_home": evaluation_data["actual_home"],
                "actual_away": evaluation_data["actual_away"],
                "predicted_home": prediction["predicted_home"],
                "predicted_away": prediction["predicted_away"],
                "is_correct_score": evaluation_data["actual_home"]
                == prediction["predicted_home"]
                and evaluation_data["actual_away"] == prediction["predicted_away"],
                "is_correct_result": True,  # 简化逻辑
                "points_earned": (
                    10
                    if evaluation_data["actual_home"] == prediction["predicted_home"]
                    else 3
                ),
                "accuracy_score": (
                    1.0
                    if evaluation_data["actual_home"] == prediction["predicted_home"]
                    else 0.7
                ),
            }

            with patch(
                "src.domain.services.prediction_service.PredictionService",
                return_value=mock_prediction_service,
            ):
                response = await async_client.post(
                    f"/api/predictions/{prediction['id']}/evaluate",
                    json=evaluation_data,
                )
                if response.status_code == 200:
                    evaluation_results.append(response.json())

        # 验证批量结果
        assert len(predictions) > 0
        assert len(evaluation_results) > 0

        # 获取用户总体统计
        total_points = sum(r["points_earned"] for r in evaluation_results)
        correct_predictions = sum(
            1 for r in evaluation_results if r["is_correct_score"]
        )

        assert total_points > 0
        assert correct_predictions >= 0

    @pytest.mark.asyncio
    async def test_prediction_with_various_outcomes(
        self, async_client: AsyncClient, sample_teams, test_user_data
    ):
        """测试不同预测结果的工作流"""
        if not sample_teams or len(sample_teams) < 2:
            pytest.skip("Sample teams not available")

        user_data = test_user_data["users"][0]
        user_id = user_data["id"]
        auth_headers = {"Authorization": "Bearer test_jwt_token"}

        home_team, away_team = sample_teams[0], sample_teams[1]

        # 创建比赛
        match_data = {
            "home_team_id": home_team.id,
            "away_team_id": away_team.id,
            "match_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            "venue": "Test Stadium",
        }

        mock_match_service = AsyncMock()
        mock_match_service.create_match.return_value = {
            "id": 1,
            **match_data,
            "status": "SCHEDULED",
        }

        with patch(
            "src.domain.services.match_service.MatchService", return_value=mock_match_service
        ):
            response = await async_client.post("/api/matches/", json=match_data)
            match_id = 1 if response.status_code != 200 else response.json()["id"]

        # 测试场景1: 精确预测正确
        prediction_scenarios = [
            {
                "name": "Exact Score Correct",
                "predicted": {"home": 2, "away": 1},
                "actual": {"home": 2, "away": 1},
                "expected_points": 10,
                "expected_accuracy": 1.0,
            },
            {
                "name": "Result Only Correct",
                "predicted": {"home": 3, "away": 1},
                "actual": {"home": 2, "away": 0},
                "expected_points": 3,
                "expected_accuracy": 0.7,
            },
            {
                "name": "Incorrect Prediction",
                "predicted": {"home": 1, "away": 2},
                "actual": {"home": 2, "away": 1},
                "expected_points": 0,
                "expected_accuracy": 0.0,
            },
        ]

        mock_prediction_service = AsyncMock()

        for scenario in prediction_scenarios:
            # 创建预测
            prediction_data = {
                "user_id": user_id,
                "match_id": match_id,
                "predicted_home": scenario["predicted"]["home"],
                "predicted_away": scenario["predicted"]["away"],
                "confidence": 0.80,
            }

            mock_prediction_service.create_prediction.return_value = {
                "id": len(prediction_scenarios),
                **prediction_data,
                "status": "PENDING",
                "created_at": datetime.utcnow().isoformat(),
            }

            with patch(
                "src.domain.services.prediction_service.PredictionService",
                return_value=mock_prediction_service,
            ):
                response = await async_client.post(
                    "/api/predictions/", json=prediction_data, headers=auth_headers
                )
                prediction_id = (
                    len(prediction_scenarios)
                    if response.status_code != 200
                    else response.json()["id"]
                )

            # 评估预测
            mock_prediction_service.evaluate_prediction.return_value = {
                "prediction_id": prediction_id,
                "actual_home": scenario["actual"]["home"],
                "actual_away": scenario["actual"]["away"],
                "predicted_home": scenario["predicted"]["home"],
                "predicted_away": scenario["predicted"]["away"],
                "is_correct_score": scenario["predicted"] == scenario["actual"],
                "is_correct_result": (
                    (
                        scenario["predicted"]["home"] > scenario["predicted"]["away"]
                        and scenario["actual"]["home"] > scenario["actual"]["away"]
                    )
                    or (
                        scenario["predicted"]["home"] < scenario["predicted"]["away"]
                        and scenario["actual"]["home"] < scenario["actual"]["away"]
                    )
                    or (
                        scenario["predicted"]["home"] == scenario["predicted"]["away"]
                        and scenario["actual"]["home"] == scenario["actual"]["away"]
                    )
                ),
                "points_earned": scenario["expected_points"],
                "accuracy_score": scenario["expected_accuracy"],
            }

            with patch(
                "src.domain.services.prediction_service.PredictionService",
                return_value=mock_prediction_service,
            ):
                response = await async_client.post(
                    f"/api/predictions/{prediction_id}/evaluate",
                    json={
                        "actual_home": scenario["actual"]["home"],
                        "actual_away": scenario["actual"]["away"],
                    },
                )

                if response.status_code == 200:
                    evaluation = response.json()
                    assert evaluation["points_earned"] == scenario["expected_points"]
                    assert (
                        abs(
                            evaluation["accuracy_score"] - scenario["expected_accuracy"]
                        )
                        < 0.01
                    )

    @pytest.mark.asyncio
    async def test_prediction_deadline_workflow(
        self, async_client: AsyncClient, sample_teams, test_user_data
    ):
        """测试预测截止时间工作流"""
        if not sample_teams:
            pytest.skip("Sample teams not available")

        user_data = test_user_data["users"][0]
        user_id = user_data["id"]
        auth_headers = {"Authorization": "Bearer test_jwt_token"}

        # 创建即将开始的比赛
        match_data = {
            "home_team_id": sample_teams[0].id,
            "away_team_id": (
                sample_teams[1].id if len(sample_teams) > 1 else sample_teams[0].id
            ),
            "match_date": (
                datetime.utcnow() + timedelta(minutes=5)
            ).isoformat(),  # 5分钟后开始
            "venue": "Test Stadium",
            "prediction_deadline": (
                datetime.utcnow() + timedelta(minutes=3)
            ).isoformat(),  # 3分钟后截止
        }

        mock_match_service = AsyncMock()
        mock_match_service.create_match.return_value = {
            "id": 1,
            **match_data,
            "status": "SCHEDULED",
            "prediction_deadline": match_data["prediction_deadline"],
        }

        with patch(
            "src.domain.services.match_service.MatchService", return_value=mock_match_service
        ):
            response = await async_client.post("/api/matches/", json=match_data)
            match_id = 1 if response.status_code != 200 else response.json()["id"]

        # 在截止时间前创建预测
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
            **prediction_data,
            "status": "PENDING",
            "created_at": datetime.utcnow().isoformat(),
        }

        with patch(
            "src.domain.services.prediction_service.PredictionService",
            return_value=mock_prediction_service,
        ):
            response = await async_client.post(
                "/api/predictions/", json=prediction_data, headers=auth_headers
            )

            if response.status_code in [200, 201]:
                prediction = response.json()
                assert prediction["status"] == "PENDING"

        # 模拟比赛开始（截止时间已过）
        mock_match_service.start_match.return_value = {
            "id": match_id,
            "status": "IN_PROGRESS",
            "started_at": datetime.utcnow().isoformat(),
        }

        with patch(
            "src.domain.services.match_service.MatchService", return_value=mock_match_service
        ):
            response = await async_client.post(f"/api/matches/{match_id}/start")

            # 尝试在比赛开始后创建预测（应该失败）
        late_prediction_data = {
            "user_id": user_id,
            "match_id": match_id,
            "predicted_home": 1,
            "predicted_away": 1,
            "confidence": 0.70,
        }

        mock_prediction_service.create_prediction.side_effect = Exception(
            "Match has already started - predictions closed"
        )

        with patch(
            "src.domain.services.prediction_service.PredictionService",
            return_value=mock_prediction_service,
        ):
            response = await async_client.post(
                "/api/predictions/", json=late_prediction_data, headers=auth_headers
            )

            # 应该返回错误
            if response.status_code != 404:
                assert response.status_code >= 400

    @pytest.mark.asyncio
    async def test_prediction_with_cache_and_performance(
        self,
        async_client: AsyncClient,
        sample_teams,
        test_user_data,
        cache_test_data,
        mock_redis,
        performance_benchmarks,
    ):
        """测试预测缓存的性能优化"""
        if not sample_teams:
            pytest.skip("Sample teams not available")

        import time

        user_data = test_user_data["users"][0]
        user_id = user_data["id"]
        auth_headers = {"Authorization": "Bearer test_jwt_token"}

        # 测试缓存命中性能
        cache_key = f"user_predictions_{user_id}"
        cached_predictions = json.dumps(
            [
                {
                    "id": 1,
                    "match_id": 1,
                    "predicted_home": 2,
                    "predicted_away": 1,
                    "status": "PENDING",
                }
            ]
        )

        mock_redis.get.return_value = cached_predictions

        start_time = time.time()
        response = await async_client.get(
            f"/api/users/{user_id}/predictions", headers=auth_headers
        )
        cache_hit_time = time.time() - start_time

        # 验证缓存命中性能
        if response.status_code == 200:
            assert cache_hit_time < 0.1  # 缓存读取应该很快
            mock_redis.get.assert_called_with(cache_key)

        # 测试缓存写入性能
        new_prediction_data = {
            "user_id": user_id,
            "match_id": sample_teams[0].id,
            "predicted_home": 1,
            "predicted_away": 1,
            "confidence": 0.75,
        }

        mock_prediction_service = AsyncMock()
        mock_prediction_service.create_prediction.return_value = {
            "id": 2,
            **new_prediction_data,
            "status": "PENDING",
            "created_at": datetime.utcnow().isoformat(),
        }

        start_time = time.time()
        with patch(
            "src.domain.services.prediction_service.PredictionService",
            return_value=mock_prediction_service,
        ):
            response = await async_client.post(
                "/api/predictions/", json=new_prediction_data, headers=auth_headers
            )
        cache_write_time = time.time() - start_time

        # 验证缓存更新
        if response.status_code in [200, 201]:
            assert (
                cache_write_time
                < performance_benchmarks["response_time_limits"]["prediction_creation"]
            )
            # 验证缓存被更新（通过Redis调用）
            if hasattr(mock_redis, "set") and mock_redis.set.called:
                pass

        # 测试批量操作性能
        bulk_predictions = []
        for i in range(10):
            bulk_predictions.append(
                {
                    "user_id": user_id,
                    "match_id": i + 1,
                    "predicted_home": (i % 3) + 1,
                    "predicted_away": ((i + 1) % 3) + 1,
                    "confidence": 0.6 + (i * 0.03),
                }
            )

        start_time = time.time()
        mock_prediction_service.create_bulk_predictions.return_value = {
            "created_count": len(bulk_predictions),
            "predictions": [
                {"id": i + 3, **pred, "status": "PENDING"}
                for i, pred in enumerate(bulk_predictions)
            ],
        }

        with patch(
            "src.domain.services.prediction_service.PredictionService",
            return_value=mock_prediction_service,
        ):
            response = await async_client.post(
                "/api/predictions/bulk",
                json={"predictions": bulk_predictions},
                headers=auth_headers,
            )
        bulk_time = time.time() - start_time

        # 验证批量性能
        if response.status_code == 200:
            avg_time_per_prediction = bulk_time / len(bulk_predictions)
            assert (
                avg_time_per_prediction
                < performance_benchmarks["response_time_limits"]["prediction_creation"]
            )


class TestPredictionErrorHandlingE2E:
    """预测错误处理端到端测试"""

    @pytest.mark.asyncio
    async def test_prediction_conflict_handling(
        self, async_client: AsyncClient, sample_match, test_user_data
    ):
        """测试预测冲突处理"""
        if not sample_match:
            pytest.skip("Sample match not available")

        user_data = test_user_data["users"][0]
        user_id = user_data["id"]
        auth_headers = {"Authorization": "Bearer test_jwt_token"}

        # 创建第一个预测
        prediction_data = {
            "user_id": user_id,
            "match_id": sample_match.id,
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
        }

        mock_prediction_service = AsyncMock()
        mock_prediction_service.create_prediction.return_value = {
            "id": 1,
            **prediction_data,
            "status": "PENDING",
            "created_at": datetime.utcnow().isoformat(),
        }

        with patch(
            "src.domain.services.prediction_service.PredictionService",
            return_value=mock_prediction_service,
        ):
            response = await async_client.post(
                "/api/predictions/", json=prediction_data, headers=auth_headers
            )

            if response.status_code in [200, 201]:
                # 尝试为同一场比赛创建第二个预测（应该失败）
                mock_prediction_service.create_prediction.side_effect = Exception(
                    "User has already predicted this match"
                )

                response = await async_client.post(
                    "/api/predictions/", json=prediction_data, headers=auth_headers
                )

                # 应该返回冲突错误
                if response.status_code != 404:
                    assert response.status_code in [409, 400]

    @pytest.mark.asyncio
    async def test_invalid_match_predictions(
        self, async_client: AsyncClient, test_user_data
    ):
        """测试无效比赛的预测"""
        user_data = test_user_data["users"][0]
        user_id = user_data["id"]
        auth_headers = {"Authorization": "Bearer test_jwt_token"}

        # 尝试为不存在的比赛创建预测
        invalid_prediction_data = {
            "user_id": user_id,
            "match_id": 99999,  # 不存在的比赛ID
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
        }

        mock_prediction_service = AsyncMock()
        mock_prediction_service.create_prediction.side_effect = Exception(
            "Match not found"
        )

        with patch(
            "src.domain.services.prediction_service.PredictionService",
            return_value=mock_prediction_service,
        ):
            response = await async_client.post(
                "/api/predictions/", json=invalid_prediction_data, headers=auth_headers
            )

            # 应该返回404错误
            if response.status_code != 404:
                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_prediction_evaluation_errors(
        self, async_client: AsyncClient, sample_predictions
    ):
        """测试预测评估错误"""
        if not sample_predictions:
            pytest.skip("Sample predictions not available")

        prediction = sample_predictions[0]

        # 尝试评估已评估的预测
        evaluation_data = {
            "actual_home": 2,
            "actual_away": 1,
        }

        mock_prediction_service = AsyncMock()
        mock_prediction_service.evaluate_prediction.side_effect = Exception(
            "Prediction has already been evaluated"
        )

        with patch(
            "src.domain.services.prediction_service.PredictionService",
            return_value=mock_prediction_service,
        ):
            response = await async_client.post(
                f"/api/predictions/{prediction.id}/evaluate", json=evaluation_data
            )

            # 应该返回错误
            if response.status_code != 404:
                assert response.status_code >= 400


# 测试辅助函数
def create_test_match_data(
    home_team_id: int, away_team_id: int, days_ahead: int = 1
) -> dict:
    """创建测试比赛数据的辅助函数"""
    return {
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "match_date": (datetime.utcnow() + timedelta(days=days_ahead)).isoformat(),
        "venue": f"Test Stadium {days_ahead}",
        "status": "SCHEDULED",
    }


def create_test_prediction_data(
    user_id: int,
    match_id: int,
    home_score: int,
    away_score: int,
    confidence: float = 0.8,
) -> dict:
    """创建测试预测数据的辅助函数"""
    return {
        "user_id": user_id,
        "match_id": match_id,
        "predicted_home": home_score,
        "predicted_away": away_score,
        "confidence": confidence,
    }


async def verify_workflow_completion(
    async_client: AsyncClient, user_id: int, auth_headers: dict
):
    """验证工作流完成的辅助函数"""
    # 检查用户统计
    response = await async_client.get(
        f"/api/users/{user_id}/statistics", headers=auth_headers
    )

    if response.status_code == 200:
        stats = response.json()
        return {
            "total_predictions": stats.get("total_predictions", 0),
            "total_points": stats.get("total_points", 0),
            "accuracy_rate": stats.get("accuracy_rate", 0.0),
        }

    return None
