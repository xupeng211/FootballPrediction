"""
Integration Tests for Prediction API
预测API端到端集成测试

测试完整的推理服务流程，包括预测、缓存、热更新等功能。
"""

import asyncio
import pytest
import time

import httpx

from src.inference import (
    get_predictor,
    get_model_loader,
    get_prediction_cache,
    get_hot_reload_manager,
)


class TestPredictionAPI:
    """预测API集成测试"""

    @pytest.fixture(scope="class")
    async def api_client(self):
        """创建API测试客户端"""
        base_url = "http://localhost:8000"

        async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
            yield client

    @pytest.fixture(scope="class", autouse=True)
    async def setup_test_environment(self):
        """设置测试环境"""
        try:
            # 初始化推理服务组件
            predictor = await get_predictor()
            model_loader = await get_model_loader()
            cache = await get_prediction_cache()
            hot_reload_manager = await get_hot_reload_manager()

            # 等待服务就绪
            await asyncio.sleep(2)

            yield {
                "predictor": predictor,
                "model_loader": model_loader,
                "cache": cache,
                "hot_reload_manager": hot_reload_manager,
            }

        except Exception as e:
            pytest.skip(f"Failed to setup test environment: {e}")

    @pytest.mark.asyncio
    async def test_health_check(self, api_client):
        """测试健康检查"""
        response = await api_client.get("/v1/predictions/health")

        assert response.status_code == 200

        health_data = response.json()
        assert "status" in health_data
        assert "model_loaded" in health_data
        assert "cache_status" in health_data

    @pytest.mark.asyncio
    async def test_single_prediction(self, api_client):
        """测试单场预测"""
        request_data = {
            "match_id": "test_match_001",
            "model_name": "xgboost_football_v1",
            "prediction_type": "probability",
            "features": {
                "home_goals": 2,
                "away_goals": 1,
                "home_possession": 60.5,
                "away_possession": 39.5,
                "home_shots": 15,
                "away_shots": 8,
            },
        }

        response = await api_client.post("/v1/predictions/predict", json=request_data)

        assert response.status_code == 200

        prediction_data = response.json()

        # 验证响应结构
        assert "request_id" in prediction_data
        assert "match_id" in prediction_data
        assert "home_win_prob" in prediction_data
        assert "draw_prob" in prediction_data
        assert "away_win_prob" in prediction_data
        assert "predicted_outcome" in prediction_data
        assert "confidence" in prediction_data
        assert "model_name" in prediction_data
        assert "model_version" in prediction_data
        assert "predicted_at" in prediction_data

        # 验证数据有效性
        assert prediction_data["match_id"] == request_data["match_id"]
        assert prediction_data["model_name"] == request_data["model_name"]

        # 概率应该为正数且和为1
        probs = [
            prediction_data["home_win_prob"],
            prediction_data["draw_prob"],
            prediction_data["away_win_prob"],
        ]
        for prob in probs:
            assert 0.0 <= prob <= 1.0

        assert abs(sum(probs) - 1.0) < 0.001  # 允许小的浮点误差

    @pytest.mark.asyncio
    async def test_batch_prediction(self, api_client):
        """测试批量预测"""
        request_data = {
            "requests": [
                {
                    "match_id": "test_match_002",
                    "model_name": "xgboost_football_v1",
                    "features": {
                        "home_goals": 3,
                        "away_goals": 1,
                        "home_possession": 65.0,
                        "away_possession": 35.0,
                    },
                },
                {
                    "match_id": "test_match_003",
                    "model_name": "xgboost_football_v1",
                    "features": {
                        "home_goals": 1,
                        "away_goals": 2,
                        "home_possession": 45.0,
                        "away_possession": 55.0,
                    },
                },
            ],
            "parallel": True,
        }

        response = await api_client.post(
            "/v1/predictions/predict/batch", json=request_data
        )

        assert response.status_code == 200

        batch_data = response.json()

        # 验证响应结构
        assert "batch_id" in batch_data
        assert "total_requests" in batch_data
        assert "successful_predictions" in batch_data
        assert "failed_predictions" in batch_data
        assert "predictions" in batch_data
        assert "batch_time_ms" in batch_data

        assert batch_data["total_requests"] == 2
        assert batch_data["successful_predictions"] >= 0
        assert len(batch_data["predictions"]) == batch_data["successful_predictions"]

        # 验证每个预测结果
        for prediction in batch_data["predictions"]:
            assert "match_id" in prediction
            assert "home_win_prob" in prediction
            assert "draw_prob" in prediction
            assert "away_win_prob" in prediction
            assert "predicted_outcome" in prediction

    @pytest.mark.asyncio
    async def test_prediction_caching(self, api_client):
        """测试预测缓存功能"""
        request_data = {
            "match_id": "test_match_cache_001",
            "model_name": "xgboost_football_v1",
            "features": {
                "home_goals": 2,
                "away_goals": 1,
                "home_possession": 55.0,
                "away_possession": 45.0,
            },
        }

        # 第一次请求（应该计算预测）
        start_time = time.time()
        response1 = await api_client.post("/v1/predictions/predict", json=request_data)
        first_request_time = time.time() - start_time

        assert response1.status_code == 200
        prediction1 = response1.json()
        assert not prediction1.get("cached", False)  # 第一次不应该来自缓存

        # 第二次请求（应该来自缓存）
        start_time = time.time()
        response2 = await api_client.post("/v1/predictions/predict", json=request_data)
        second_request_time = time.time() - start_time

        assert response2.status_code == 200
        prediction2 = response2.json()

        # 验证缓存命中
        assert prediction2.get("cached", False)  # 应该来自缓存
        assert second_request_time < first_request_time  # 缓存应该更快

        # 验证结果一致性
        assert prediction1["home_win_prob"] == prediction2["home_win_prob"]
        assert prediction1["draw_prob"] == prediction2["draw_prob"]
        assert prediction1["away_win_prob"] == prediction2["away_win_prob"]
        assert prediction1["predicted_outcome"] == prediction2["predicted_outcome"]

    @pytest.mark.asyncio
    async def test_model_list(self, api_client):
        """测试模型列表"""
        response = await api_client.get("/v1/predictions/models")

        assert response.status_code == 200

        models_data = response.json()
        assert "models" in models_data
        assert "total_models" in models_data
        assert "default_model" in models_data

        # 验证模型数据结构
        if models_data["models"]:
            for model in models_data["models"]:
                assert "model_name" in model
                assert "model_version" in model
                assert "model_type" in model
                assert "created_at" in model

    @pytest.mark.asyncio
    async def test_cache_management(self, api_client):
        """测试缓存管理"""
        # 首先进行一次预测以创建缓存
        request_data = {
            "match_id": "test_match_cache_mgmt_001",
            "model_name": "xgboost_football_v1",
            "features": {"home_goals": 1, "away_goals": 1},
        }

        await api_client.post("/v1/predictions/predict", json=request_data)

        # 获取缓存统计
        stats_response = await api_client.get("/v1/predictions/cache/stats")
        assert stats_response.status_code == 200

        stats_data = stats_response.json()
        assert "hits" in stats_data
        assert "misses" in stats_data
        assert "sets" in stats_data

        # 清除缓存
        clear_response = await api_client.delete("/v1/predictions/cache?pattern=*")
        assert clear_response.status_code == 200

        clear_data = clear_response.json()
        assert "status" in clear_data
        assert clear_data["status"] == "success"

    @pytest.mark.asyncio
    async def test_hot_reload_stats(self, api_client):
        """测试热更新统计"""
        response = await api_client.get("/v1/predictions/hot-reload/stats")

        assert response.status_code == 200

        stats_data = response.json()
        assert "total_reloads" in stats_data
        assert "successful_reloads" in stats_data
        assert "failed_reloads" in stats_data
        assert "is_monitoring" in stats_data

    @pytest.mark.asyncio
    async def test_prediction_stats(self, api_client):
        """测试预测统计"""
        response = await api_client.get("/v1/predictions/stats")

        assert response.status_code == 200

        stats_data = response.json()
        assert "total_predictions" in stats_data
        assert "successful_predictions" in stats_data
        assert "failed_predictions" in stats_data
        assert "cache_hit_rate" in stats_data

    @pytest.mark.asyncio
    async def test_error_handling(self, api_client):
        """测试错误处理"""
        # 测试无效模型
        invalid_request = {
            "match_id": "test_error_001",
            "model_name": "nonexistent_model",
            "features": {"home_goals": 1, "away_goals": 1},
        }

        response = await api_client.post(
            "/v1/predictions/predict", json=invalid_request
        )

        # 应该返回错误状态码
        assert response.status_code in [400, 404, 503]

        error_data = response.json()
        assert "error" in error_data
        assert "message" in error_data

        # 测试无效请求格式
        invalid_format = {
            "match_id": "",  # 空的match_id
            "model_name": "xgboost_football_v1",
            "features": {},
        }

        response = await api_client.post("/v1/predictions/predict", json=invalid_format)
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_concurrent_predictions(self, api_client):
        """测试并发预测"""
        request_data = {
            "match_id": "test_concurrent_001",
            "model_name": "xgboost_football_v1",
            "features": {"home_goals": 2, "away_goals": 1, "home_possession": 55.0},
        }

        # 创建多个并发请求
        tasks = []
        for i in range(10):
            request_copy = request_data.copy()
            request_copy["match_id"] = f"test_concurrent_{i:03d}"
            tasks.append(api_client.post("/v1/predictions/predict", json=request_copy))

        # 执行并发请求
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证结果
        successful_responses = 0
        for response in responses:
            if isinstance(response, Exception):
                print(f"Concurrent request failed: {response}")
                continue

            if response.status_code == 200:
                successful_responses += 1
                prediction_data = response.json()
                assert "home_win_prob" in prediction_data
                assert "match_id" in prediction_data

        # 至少应该有一些成功的请求
        assert successful_responses > 0
        print(f"Concurrent predictions: {successful_responses}/10 successful")

    @pytest.mark.asyncio
    async def test_feature_parity(self, api_client):
        """测试特征一致性（Feature Parity）"""
        # 使用相同的特征数据
        features = {
            "home_goals": 3,
            "away_goals": 1,
            "home_possession": 60.0,
            "away_possession": 40.0,
            "home_shots": 12,
            "away_shots": 8,
            "home_corners": 6,
            "away_corners": 3,
        }

        request_data = {
            "match_id": "test_feature_parity_001",
            "model_name": "xgboost_football_v1",
            "features": features,
        }

        # 进行多次预测，验证结果一致性
        responses = []
        for i in range(3):
            request_copy = request_data.copy()
            request_copy["match_id"] = f"test_parity_{i:03d}"
            request_copy["force_recalculate"] = True  # 强制重新计算

            response = await api_client.post(
                "/v1/predictions/predict", json=request_copy
            )
            assert response.status_code == 200

            prediction_data = response.json()
            responses.append(prediction_data)

        # 验证预测结果的一致性（忽略request_id和时间戳等）
        for response in responses[1:]:
            # 主概率应该相同（允许小的浮点误差）
            assert (
                abs(response["home_win_prob"] - responses[0]["home_win_prob"]) < 0.001
            )
            assert abs(response["draw_prob"] - responses[0]["draw_prob"]) < 0.001
            assert (
                abs(response["away_win_prob"] - responses[0]["away_win_prob"]) < 0.001
            )

            # 预测结果应该相同
            assert response["predicted_outcome"] == responses[0]["predicted_outcome"]
            assert abs(response["confidence"] - responses[0]["confidence"]) < 0.001

        print(f"Feature parity test passed: {len(responses)} consistent predictions")

    @pytest.mark.asyncio
    async def test_performance_requirements(self, api_client):
        """测试性能要求"""
        request_data = {
            "match_id": "test_performance_001",
            "model_name": "xgboost_football_v1",
            "features": {
                "home_goals": 2,
                "away_goals": 1,
                "home_possession": 55.0,
                "away_possession": 45.0,
            },
        }

        # 测试单次预测性能
        start_time = time.time()
        response = await api_client.post("/v1/predictions/predict", json=request_data)
        prediction_time = (time.time() - start_time) * 1000  # 转换为毫秒

        assert response.status_code == 200
        prediction_data = response.json()

        # API响应时间应该 < 1秒
        assert prediction_time < 1000, f"Prediction took too long: {prediction_time}ms"

        # 预测本身的时间应该合理（< 500ms）
        assert prediction_data.get("prediction_time_ms", 0) < 500

        print(
            f"Performance test passed: API={prediction_time:.2f}ms, Prediction={prediction_data.get('prediction_time_ms', 0)}ms"
        )

    @pytest.mark.asyncio
    async def test_api_response_format_consistency(self, api_client):
        """测试API响应格式一致性"""
        request_data = {
            "match_id": "test_format_001",
            "model_name": "xgboost_football_v1",
            "features": {"home_goals": 1, "away_goals": 1},
        }

        # 测试不同的端点
        endpoints = [
            "/v1/predictions/predict",
            "/v1/predictions/xgboost_football_v1/test_format_001",
        ]

        responses = []
        for endpoint in endpoints:
            try:
                response = await api_client.post(endpoint, json=request_data)
                if response.status_code == 200:
                    responses.append(response.json())
            except Exception as e:
                print(f"Endpoint {endpoint} failed: {e}")

        # 如果有多个成功响应，验证格式一致性
        if len(responses) > 1:
            first_response = responses[0]
            required_fields = [
                "request_id",
                "match_id",
                "predicted_at",
                "home_win_prob",
                "draw_prob",
                "away_win_prob",
                "predicted_outcome",
                "confidence",
                "model_name",
                "model_version",
                "model_type",
            ]

            for response in responses[1:]:
                for field in required_fields:
                    assert field in response, f"Missing field '{field}' in response"
                    assert type(response[field]) == type(
                        first_response[field]
                    ), f"Type mismatch for field '{field}'"

            print(
                f"Response format consistency test passed: {len(responses)} consistent responses"
            )


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
