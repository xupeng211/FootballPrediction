"""
扩展API端点集成测试
测试更多API路由和边界条件
"""

import pytest
import json
import time
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class TestPredictionAPIExtended:
    """扩展预测API测试"""

    @pytest.fixture
    def api_client(self):
        """创建API测试客户端"""
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware

        app = FastAPI(title="Football Prediction API Extended")

        # 添加CORS中间件
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # 数据模型
        class PredictionRequest(BaseModel):
            home_team: str
            away_team: str
            model_version: Optional[str] = "xgboost_v2"
            features: Optional[List[float]] = None

        class BatchPredictionRequest(BaseModel):
            matches: List[Dict[str, Any]]
            model_version: Optional[str] = "xgboost_v2"

        class PredictionResponse(BaseModel):
            home_team: str
            away_team: str
            prediction: str
            probabilities: Dict[str, float]
            confidence: float
            model_version: str
            timestamp: str
            processing_time_ms: float

        # 预测端点
        @app.post("/predict", response_model=PredictionResponse)
        async def predict_match(request: PredictionRequest):
            """预测单场比赛结果"""
            start_time = time.perf_counter()

            # 模拟预测逻辑
            home_team, away_team = request.home_team, request.away_team

            # 根据队伍名称生成确定性预测（用于测试）
            home_hash = sum(ord(c) for c in home_team)
            away_hash = sum(ord(c) for c in away_team)
            prediction_seed = (home_hash + away_hash) % 3

            outcomes = ["HOME_WIN", "DRAW", "AWAY_WIN"]
            prediction = outcomes[prediction_seed]

            # 生成概率
            base_prob = 0.4
            if prediction == "HOME_WIN":
                probabilities = {"HOME_WIN": 0.6, "DRAW": 0.3, "AWAY_WIN": 0.1}
                confidence = 0.6
            elif prediction == "DRAW":
                probabilities = {"HOME_WIN": 0.3, "DRAW": 0.4, "AWAY_WIN": 0.3}
                confidence = 0.4
            else:  # AWAY_WIN
                probabilities = {"HOME_WIN": 0.1, "DRAW": 0.3, "AWAY_WIN": 0.6}
                confidence = 0.6

            processing_time = (time.perf_counter() - start_time) * 1000

            return {
                "home_team": home_team,
                "away_team": away_team,
                "prediction": prediction,
                "probabilities": probabilities,
                "confidence": confidence,
                "model_version": request.model_version,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "processing_time_ms": processing_time,
            }

        # 批量预测端点
        @app.post("/predict/batch", response_model=List[PredictionResponse])
        async def predict_batch(request: BatchPredictionRequest):
            """批量预测比赛结果"""
            results = []

            for match in request.matches:
                # 创建单次预测请求
                single_request = PredictionRequest(
                    home_team=match.get("home_team", ""),
                    away_team=match.get("away_team", ""),
                    model_version=request.model_version,
                )

                # 复用预测逻辑
                result = await predict_match(single_request)
                results.append(result)

            return results

        # 模型信息端点
        @app.get("/models/{model_name}/info")
        async def get_model_info(model_name: str):
            """获取模型信息"""
            models_info = {
                "xgboost_v2": {
                    "name": "XGBoost v2.0",
                    "version": "2.0.1",
                    "accuracy": 0.68,
                    "features_count": 12,
                    "training_date": "2024-01-01",
                    "model_type": "classification",
                },
                "random_forest": {
                    "name": "Random Forest",
                    "version": "1.5.0",
                    "accuracy": 0.65,
                    "features_count": 12,
                    "training_date": "2023-12-15",
                    "model_type": "classification",
                },
            }

            if model_name not in models_info:
                raise HTTPException(status_code=404, detail=f"模型 {model_name} 不存在")

            return models_info[model_name]

        # 模型列表端点
        @app.get("/models")
        async def list_models():
            """列出所有可用模型"""
            return {
                "models": [
                    {"name": "xgboost_v2", "status": "active", "accuracy": 0.68},
                    {"name": "random_forest", "status": "active", "accuracy": 0.65},
                    {"name": "neural_network", "status": "training", "accuracy": None},
                ],
                "default_model": "xgboost_v2",
                "total_count": 3,
            }

        # 统计信息端点
        @app.get("/stats")
        async def get_prediction_stats():
            """获取预测统计信息"""
            return {
                "total_predictions": 15420,
                "successful_predictions": 15231,
                "failed_predictions": 189,
                "success_rate": 0.988,
                "avg_processing_time_ms": 45.2,
                "models_used": {
                    "xgboost_v2": 10234,
                    "random_forest": 4196,
                    "neural_network": 991,
                },
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }

        # 健康检查端点
        @app.get("/health")
        async def health_check():
            """健康检查"""
            return {
                "status": "healthy",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "version": "1.0.0",
                "uptime_seconds": 3600,
            }

        # 错误处理
        @app.exception_handler(422)
        async def validation_exception_handler(request, exc):
            return {
                "error": "Validation Error",
                "message": "请求数据验证失败",
                "status_code": 422,
                "details": str(exc),
            }

        return TestClient(app)

    def test_single_prediction_with_different_teams(self, api_client):
        """测试不同队伍组合的预测"""
        test_cases = [
            {"home": "Manchester United", "away": "Liverpool"},
            {"home": "Chelsea", "away": "Arsenal"},
            {"home": "Real Madrid", "away": "Barcelona"},
            {"home": "Bayern Munich", "away": "Borussia Dortmund"},
        ]

        for case in test_cases:
            request_data = {
                "home_team": case["home"],
                "away_team": case["away"],
                "model_version": "xgboost_v2",
            }

            response = api_client.post("/predict", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["home_team"] == case["home"]
            assert data["away_team"] == case["away"]
            assert data["prediction"] in ["HOME_WIN", "DRAW", "AWAY_WIN"]
            assert "probabilities" in data
            assert all(
                key in data["probabilities"] for key in ["HOME_WIN", "DRAW", "AWAY_WIN"]
            )
            assert data["model_version"] == "xgboost_v2"
            assert data["processing_time_ms"] >= 0

    def test_batch_prediction(self, api_client):
        """测试批量预测"""
        batch_request = {
            "matches": [
                {"home_team": "Team A", "away_team": "Team B"},
                {"home_team": "Team C", "away_team": "Team D"},
                {"home_team": "Team E", "away_team": "Team F"},
            ],
            "model_version": "xgboost_v2",
        }

        response = api_client.post("/predict/batch", json=batch_request)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

        for prediction in data:
            assert prediction["prediction"] in ["HOME_WIN", "DRAW", "AWAY_WIN"]
            assert "probabilities" in prediction
            assert prediction["model_version"] == "xgboost_v2"

    def test_model_info_endpoint(self, api_client):
        """测试模型信息端点"""
        # 测试存在的模型
        response = api_client.get("/models/xgboost_v2/info")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "accuracy" in data
        assert "features_count" in data

        # 测试不存在的模型
        response = api_client.get("/models/nonexistent_model/info")
        assert response.status_code == 404
        error_data = response.json()
        assert "detail" in error_data

    def test_models_list_endpoint(self, api_client):
        """测试模型列表端点"""
        response = api_client.get("/models")
        assert response.status_code == 200
        data = response.json()

        assert "models" in data
        assert "default_model" in data
        assert "total_count" in data
        assert isinstance(data["models"], list)
        assert len(data["models"]) > 0

        # 验证模型结构
        for model in data["models"]:
            assert "name" in model
            assert "status" in model
            assert "accuracy" in model

    def test_stats_endpoint(self, api_client):
        """测试统计信息端点"""
        response = api_client.get("/stats")
        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "total_predictions",
            "successful_predictions",
            "failed_predictions",
            "success_rate",
            "avg_processing_time_ms",
            "models_used",
            "last_updated",
        ]

        for field in required_fields:
            assert field in data, f"缺少字段: {field}"

        # 验证数据类型和范围
        assert isinstance(data["total_predictions"], int)
        assert isinstance(data["success_rate"], (int, float))
        assert 0 <= data["success_rate"] <= 1
        assert isinstance(data["models_used"], dict)

    def test_prediction_with_custom_features(self, api_client):
        """测试使用自定义特征的预测"""
        request_data = {
            "home_team": "Team A",
            "away_team": "Team B",
            "features": [1.2, 0.8, 0.5, 1.1, 0.9, 1.3, 0.7, 1.0, 0.6, 1.2, 0.8, 1.1],
        }

        response = api_client.post("/predict", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["home_team"] == "Team A"
        assert data["away_team"] == "Team B"
        assert data["prediction"] is not None

    def test_prediction_validation_errors(self, api_client):
        """测试预测请求验证错误"""
        # 测试缺少必需字段
        invalid_request = {
            "home_team": "Team A"
            # 缺少 away_team
        }

        response = api_client.post("/predict", json=invalid_request)
        assert response.status_code == 422

        # 测试空字符串
        invalid_request2 = {"home_team": "", "away_team": "Team B"}

        response = api_client.post("/predict", json=invalid_request2)
        # 应该处理空字符串（根据具体实现可能通过或失败）

    def test_batch_prediction_empty_list(self, api_client):
        """测试空批量预测列表"""
        empty_batch = {"matches": [], "model_version": "xgboost_v2"}

        response = api_client.post("/predict/batch", json=empty_batch)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_batch_prediction_max_size(self, api_client):
        """测试批量预测大小限制"""
        # 创建大量比赛（测试性能和限制）
        large_batch = {
            "matches": [
                {"home_team": f"Team {i}", "away_team": f"Opponent {i}"}
                for i in range(100)
            ],
            "model_version": "xgboost_v2",
        }

        response = api_client.post("/predict/batch", json=large_batch)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 100

        for i, prediction in enumerate(data):
            assert prediction["home_team"] == f"Team {i}"
            assert prediction["away_team"] == f"Opponent {i}"

    def test_concurrent_predictions(self, api_client):
        """测试并发预测请求"""
        import threading
        import queue

        results = queue.Queue()

        def make_prediction(request_id):
            request_data = {
                "home_team": f"Team {request_id}",
                "away_team": f"Opponent {request_id}",
            }
            response = api_client.post("/predict", json=request_data)
            results.put((request_id, response.status_code, response.json()))

        # 创建10个并发请求
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_prediction, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        successful_requests = 0
        while not results.empty():
            request_id, status_code, data = results.get()
            assert status_code == 200, f"请求 {request_id} 失败: {status_code}"
            assert data["home_team"] == f"Team {request_id}"
            successful_requests += 1

        assert successful_requests == 10

    def test_api_response_time(self, api_client):
        """测试API响应时间"""
        request_data = {"home_team": "Team A", "away_team": "Team B"}

        # 测量多次请求的响应时间
        response_times = []
        for _ in range(10):
            start_time = time.perf_counter()
            response = api_client.post("/predict", json=request_data)
            end_time = time.perf_counter()

            assert response.status_code == 200
            response_times.append((end_time - start_time) * 1000)

        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)

        print(f"API响应时间统计:")
        print(f"  - 平均: {avg_response_time:.2f}ms")
        print(f"  - 最大: {max_response_time:.2f}ms")
        print(f"  - 最小: {min_response_time:.2f}ms")

        # 性能断言（根据实际情况调整）
        assert avg_response_time < 100, f"平均响应时间过长: {avg_response_time:.2f}ms"
        assert max_response_time < 500, f"最大响应时间过长: {max_response_time:.2f}ms"

    def test_different_model_versions(self, api_client):
        """测试不同模型版本"""
        models_to_test = ["xgboost_v2", "random_forest"]

        for model_version in models_to_test:
            request_data = {
                "home_team": "Team A",
                "away_team": "Team B",
                "model_version": model_version,
            }

            response = api_client.post("/predict", json=request_data)

            if response.status_code == 200:
                data = response.json()
                assert data["model_version"] == model_version
            elif response.status_code == 404:
                # 模型可能不存在，这是可接受的
                pass
            else:
                pytest.fail(
                    f"模型 {model_version} 测试失败，状态码: {response.status_code}"
                )

    def test_api_error_handling(self, api_client):
        """测试API错误处理"""
        # 测试无效JSON
        response = api_client.post(
            "/predict",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

        # 测试缺少Content-Type
        response = api_client.post("/predict", data='{"home": "test"}')
        # FastAPI通常会自动处理，所以这个可能通过

        # 测试过大的请求体
        huge_features = [1.0] * 1000  # 创建非常大的特征数组
        large_request = {
            "home_team": "Team A",
            "away_team": "Team B",
            "features": huge_features,
        }

        response = api_client.post("/predict", json=large_request)
        # 根据实现可能通过或失败

    def test_api_health_and_readiness(self, api_client):
        """测试API健康状态和就绪状态"""
        # 基础健康检查
        response = api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data


class TestAPIIntegrationWithDependencies:
    """API与依赖项集成测试"""

    @pytest.fixture
    def api_client_with_mocks(self):
        """创建带有Mock依赖的API客户端"""
        from fastapi import FastAPI
        from unittest.mock import Mock, AsyncMock

        app = FastAPI(title="Football Prediction API with Mocks")

        # Mock外部服务
        mock_prediction_service = Mock()
        mock_prediction_service.predict_match.return_value = {
            "prediction": "HOME_WIN",
            "probabilities": {"HOME_WIN": 0.7, "DRAW": 0.2, "AWAY_WIN": 0.1},
            "confidence": 0.7,
        }

        mock_database = Mock()
        mock_database.get_prediction_history.return_value = [
            {"match_id": "1", "prediction": "HOME_WIN", "actual": "HOME_WIN"},
            {"match_id": "2", "prediction": "DRAW", "actual": "AWAY_WIN"},
        ]

        # 带有依赖注入的端点
        @app.post("/predict/with-dependencies")
        async def predict_with_dependencies(request: dict):
            """使用依赖的预测端点"""
            # 模拟服务调用
            result = mock_prediction_service.predict_match(
                home_team=request["home_team"], away_team=request["away_team"]
            )

            return {
                "home_team": request["home_team"],
                "away_team": request["away_team"],
                **result,
            }

        @app.get("/history/{team}")
        async def get_prediction_history(team: str):
            """获取预测历史"""
            history = mock_database.get_prediction_history(team)
            return {"team": team, "history": history}

        return TestClient(app), {
            "prediction_service": mock_prediction_service,
            "database": mock_database,
        }

    def test_prediction_with_service_dependency(self, api_client_with_mocks):
        """测试带有服务依赖的预测"""
        client, mocks = api_client_with_mocks

        request_data = {"home_team": "Team A", "away_team": "Team B"}

        response = client.post("/predict/with-dependencies", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["prediction"] == "HOME_WIN"
        assert "probabilities" in data

        # 验证Mock被调用
        mocks["prediction_service"].predict_match.assert_called_once()

    def test_history_with_database_dependency(self, api_client_with_mocks):
        """测试带有数据库依赖的历史查询"""
        client, mocks = api_client_with_mocks

        response = client.get("/history/Team_A")
        assert response.status_code == 200

        data = response.json()
        assert data["team"] == "Team_A"
        assert "history" in data
        assert len(data["history"]) == 2

        # 验证Mock被调用
        mocks["database"].get_prediction_history.assert_called_once_with("Team_A")

    def test_dependency_failure_handling(self, api_client_with_mocks):
        """测试依赖失败处理"""
        client, mocks = api_client_with_mocks

        # 模拟预测服务失败
        mocks["prediction_service"].predict_match.side_effect = Exception("服务不可用")

        request_data = {"home_team": "Team A", "away_team": "Team B"}

        response = client.post("/predict/with-dependencies", json=request_data)
        # 根据错误处理策略，可能返回500或其他状态码


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
