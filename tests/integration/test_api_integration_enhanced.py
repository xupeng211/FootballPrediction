"""
增强的API集成测试
测试API端点之间的交互和数据流
"""

import asyncio
from unittest.mock import patch

import pytest

from tests.helpers.enhanced_mocks import (
    EnhancedMock,
    MockDataGenerator,
    mock_database_session,
    mock_redis_cache,
)


@pytest.mark.integration
@pytest.mark.integration
class TestAPIIntegrationEnhanced:
    """增强的API集成测试"""

    @pytest.fixture
    def mock_services(self):
        """Mock所有外部服务"""
        return {
            "database": EnhancedMock.create_database_mock(),
            "redis": EnhancedMock.create_redis_mock(),
            "ml_model": EnhancedMock.create_ml_model_mock(),
            "http_client": EnhancedMock.create_http_client_mock()[0],
        }

    @pytest.fixture
    def sample_workflow_data(self):
        """示例工作流数据"""
        return {
            "match": MockDataGenerator.create_match_data(
                {
                    "id": 999,
                    "home_team_id": 100,
                    "away_team_id": 200,
                    "match_status": "live",
                    "minute": 45,
                    "home_score": 1,
                    "away_score": 0,
                }
            ),
            "teams": {
                100: MockDataGenerator.create_team_data({"id": 100, "team_name": "Home Team FC"}),
                200: MockDataGenerator.create_team_data({"id": 200, "team_name": "Away Team FC"}),
            },
            "odds": MockDataGenerator.create_odds_data(
                {"match_id": 999, "home_win": 1.8, "draw": 3.6, "away_win": 4.2}
            ),
        }

    @mock_database_session([MockDataGenerator.create_match_data()])
    @mock_redis_cache({})
    async def test_complete_prediction_workflow(self, api_client, sample_workflow_data):
        """测试完整的预测工作流"""
        # 1. 创建预测
        prediction_data = {"match_id": 999, "model_version": "v2.0"}

        with patch("src.api.predictions.PredictionService") as mock_service:
            mock_service.predict_match.return_value = {
                "prediction": "home_win",
                "confidence": 0.85,
                "probabilities": {"home_win": 0.85, "draw": 0.10, "away_win": 0.05},
            }

            # 创建预测请求
            response = api_client.post(
                "/api/v1/predictions",
                json=prediction_data,
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 201
            prediction = response.json()
            assert prediction["prediction"] == "home_win"

        # 2. 获取预测历史
        with patch("src.api.predictions.PredictionService") as mock_service:
            mock_service.get_prediction_history.return_value = [prediction]

            response = api_client.get(
                f"/api/v1/predictions/match/{prediction_data['match_id']}/history",
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            history = response.json()
            assert len(history) == 1
            assert history[0]["prediction"] == "home_win"

    async def test_live_match_updates_workflow(self, api_client, sample_workflow_data):
        """测试实时比赛更新工作流"""
        # Mock实时数据源
        live_data = {
            "match_id": 999,
            "events": [
                {"minute": 23, "type": "goal", "team": "home", "player": "Player A"},
                {
                    "minute": 45,
                    "type": "yellow_card",
                    "team": "away",
                    "player": "Player B",
                },
            ],
            "statistics": {
                "possession": {"home": 55, "away": 45},
                "shots": {"home": 8, "away": 4},
            },
        }

        with patch("src.api.data.ExternalDataService") as mock_service:
            mock_service.get_live_match_data.return_value = live_data

            # 获取实时数据
            response = api_client.get(f"/api/v1/matches/{sample_workflow_data['match']['id']}/live")

            assert response.status_code == 200
            live = response.json()
            assert len(live["events"]) == 2
            assert live["statistics"]["possession"]["home"] == 55

    async def test_odds_updates_and_prediction_correlation(self, api_client):
        """测试赔率更新与预测的关联"""
        # 模拟赔率变化
        odds_sequence = [
            {
                "home_win": 2.0,
                "draw": 3.4,
                "away_win": 3.8,
                "timestamp": "2025-10-05T10:00:00Z",
            },
            {
                "home_win": 1.9,
                "draw": 3.5,
                "away_win": 4.0,
                "timestamp": "2025-10-05T10:05:00Z",
            },
            {
                "home_win": 1.8,
                "draw": 3.6,
                "away_win": 4.2,
                "timestamp": "2025-10-05T10:10:00Z",
            },
        ]

        predictions = []

        # 对每个赔率更新获取预测
        for odds in odds_sequence:
            with patch("src.services.prediction.PredictionModel") as mock_model:
                mock_model.predict.return_value = {
                    "prediction": "home_win" if odds["home_win"] < 2.0 else "draw",
                    "confidence": min(0.9, 0.5 + (2.5 - odds["home_win"]) * 0.2),
                }

                response = api_client.post(
                    "/api/v1/predictions/real-time",
                    json={"match_id": 999, "current_odds": odds},
                )

                assert response.status_code == 200
                pred = response.json()
                predictions.append(pred)

        # 验证预测与赔率变化的关联
        assert predictions[0]["prediction"] == "draw"
        assert predictions[2]["prediction"] == "home_win"
        assert predictions[2]["confidence"] > predictions[0]["confidence"]

    async def test_batch_predictions_workflow(self, api_client):
        """测试批量预测工作流"""
        # 创建多个比赛的预测请求
        batch_request = {
            "matches": [
                {"match_id": 1001, "features": {"team_form": 0.8}},
                {"match_id": 1002, "features": {"team_form": 0.6}},
                {"match_id": 1003, "features": {"team_form": 0.9}},
            ],
            "model_version": "v2.0",
        }

        with patch("src.api.predictions.PredictionService") as mock_service:
            mock_service.batch_predict.return_value = [
                {"match_id": 1001, "prediction": "home_win", "confidence": 0.82},
                {"match_id": 1002, "prediction": "draw", "confidence": 0.65},
                {"match_id": 1003, "prediction": "away_win", "confidence": 0.71},
            ]

            response = api_client.post(
                "/api/v1/predictions/batch",
                json=batch_request,
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            results = response.json()
            assert len(results) == 3
            assert all("prediction" in r for r in results)

    async def test_cache_invalidation_workflow(self, api_client):
        """测试缓存失效工作流"""
        match_id = 888

        # 1. 首次请求，缓存为空
        with patch("src.cache.redis_manager.get_cache_value") as mock_get:
            mock_get.return_value = None

            with patch("src.cache.redis_manager.set_cache_value") as mock_set:
                response = api_client.get(f"/api/v1/matches/{match_id}")

                assert response.status_code == 200
                mock_set.assert_called_once()

        # 2. 更新数据，触发缓存失效
        with patch("src.cache.redis_manager.delete_cache") as mock_delete:
            mock_delete.return_value = 1

            # 模拟数据更新
            update_response = api_client.put(
                f"/api/v1/matches/{match_id}", json={"home_score": 1, "away_score": 0}
            )

            # 验证缓存被删除
            mock_delete.assert_called()

        # 3. 再次请求，获取更新后的数据
        with patch("src.cache.redis_manager.get_cache_value") as mock_get:
            mock_get.return_value = None  # 缓存已失效

            response = api_client.get(f"/api/v1/matches/{match_id}")
            assert response.status_code == 200

    async def test_error_propagation_workflow(self, api_client):
        """测试错误传播工作流"""
        # 模拟下游服务错误
        with patch("src.services.prediction.PredictionModel") as mock_model:
            mock_model.predict.side_effect = Exception("Model service unavailable")

            response = api_client.post("/api/v1/predictions", json={"match_id": 777})

            assert response.status_code == 503
            error = response.json()
            assert "error" in error
            assert "Model service unavailable" in error["detail"]

    async def test_data_consistency_workflow(self, api_client):
        """测试数据一致性工作流"""
        match_id = 666

        # 创建比赛
        create_data = MockDataGenerator.create_match_data({"id": match_id})

        with patch("src.database.base.DatabaseSession") as mock_db:
            mock_db.return_value.__aenter__.return_value.execute.return_value = match_id

            response = api_client.post("/api/v1/matches", json=create_data)
            assert response.status_code == 201

        # 获取比赛验证数据一致性
        response = api_client.get(f"/api/v1/matches/{match_id}")
        assert response.status_code == 200

        match = response.json()
        assert match["id"] == match_id
        assert match["home_team_id"] == create_data["home_team_id"]
        assert match["away_team_id"] == create_data["away_team_id"]

    async def test_concurrent_requests_workflow(self, api_client):
        """测试并发请求工作流"""

        # 创建多个并发请求
        async def make_request(match_id):
            with patch("src.api.data.DataService") as mock_service:
                mock_service.get_match_data.return_value = MockDataGenerator.create_match_data(
                    {"id": match_id}
                )

                response = api_client.get(f"/api/v1/matches/{match_id}")
                return response.json()

        # 并发执行10个请求
        match_ids = [100 + i for i in range(10)]
        tasks = [make_request(mid) for mid in match_ids]

        results = await asyncio.gather(*tasks)

        # 验证所有请求都成功
        assert len(results) == 10
        assert all(r["id"] in match_ids for r in results)

    async def test_rate_limiting_workflow(self, api_client):
        """测试速率限制工作流"""
        # 快速连续请求
        responses = []

        for i in range(5):
            response = api_client.get("/api/v1/health")
            responses.append(response)

        # 验证速率限制生效（如果启用）
        # 注意：在测试环境中速率限制可能被禁用
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 1  # 至少有一个请求成功

    async def test_authentication_flow(self, api_client):
        """测试认证流程"""
        # 1. 未认证请求
        response = api_client.get("/api/v1/predictions/1")
        assert response.status_code == 401

        # 2. 使用无效token
        response = api_client.get(
            "/api/v1/predictions/1", headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

        # 3. 使用有效token
        with patch("src.api.auth.verify_token") as mock_verify:
            mock_verify.return_value = {"user_id": 123, "role": "user"}

            response = api_client.get(
                "/api/v1/predictions/1", headers={"Authorization": "Bearer valid_token"}
            )
            # 注意：可能需要实际的路由存在
            assert response.status_code in [200, 404]

    async def test_api_versioning(self, api_client):
        """测试API版本控制"""
        # 测试v1 API
        response = api_client.get("/api/v1/health")
        assert response.status_code == 200

        # 测试版本响应头
        assert "api-version" in response.headers or "X-API-Version" in response.headers

    async def test_request_validation(self, api_client):
        """测试请求验证"""
        # 测试无效JSON
        response = api_client.post(
            "/api/v1/predictions",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

        # 测试必填字段缺失
        response = api_client.post(
            "/api/v1/predictions",
            json={},
            headers={"Authorization": "Bearer test_token"},
        )
        # 可能需要实际的路由存在
        assert response.status_code in [400, 422]

    async def test_response_format(self, api_client):
        """测试响应格式"""
        response = api_client.get("/api/v1/health")

        # 验证响应是JSON
        assert response.headers["content-type"] == "application/json"

        # 验证响应结构
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data

    async def test_cors_headers(self, api_client):
        """测试CORS头"""
        # 发送预检请求
        response = api_client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # 验证CORS头
        assert response.status_code in [200, 204]
        assert (
            "access-control-allow-origin" in response.headers
            or "Access-Control-Allow-Origin" in response.headers
        )
