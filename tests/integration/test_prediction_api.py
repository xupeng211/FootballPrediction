#!/usr/bin/env python3
"""
M5模块: 预测API集成测试

严格遵循TDD原则，在实现API之前编写集成测试。
验证FastAPI服务的完整功能和HTTP接口规范。

测试覆盖:
1. 单场比赛预测API (GET /predict/match/{match_id})
2. 批量预测API (POST /predict/batch)
3. 健康检查API (GET /predict/health)
4. 统计信息API (GET /predict/stats)
5. 错误处理和边界条件
6. 性能和延迟测试

设计原则:
- TDD驱动: 先写测试，后写实现
- 端到端测试: 测试完整的API调用链
- Mock隔离: 使用Mock对象隔离外部依赖
- HTTP标准: 验证HTTP状态码和响应格式
- 性能验证: 确保响应时间和并发处理能力
"""

import pytest
import asyncio
import json
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

import httpx
from fastapi.testclient import TestClient
import pandas as pd
import numpy as np

# 导入待测试的API模块
from src.api.predictions.predict_router import router, PredictionResult, BatchPredictionRequest
from src.services.inference_service import InferenceService, InferenceConfig

# 导入依赖模块
from src.ml.models.xgboost_classifier import XGBoostClassifier, XGBoostModelConfig
from src.features.schemas import MatchFeatureSet, TeamFormFeatures, XGFeatures, OddsFeatures


class MockInferenceService:
    """Mock推理服务，用于测试"""

    def __init__(self):
        self.is_initialized = True
        self.stats = {
            'total_requests': 0,
            'successful_predictions': 0,
            'cache_hits': 0,
            'fallback_used': 0,
            'errors': 0,
            'avg_response_time_ms': 0.0,
            'cache_size': 0
        }
        self.call_count = 0

    async def predict(self, match_id: str) -> Dict[str, Any]:
        """模拟预测方法"""
        self.call_count += 1
        self.stats['total_requests'] += 1

        # 模拟不同比赛ID的不同结果
        if match_id == "nonexistent_match":
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"比赛不存在: {match_id}")

        if match_id == "insufficient_features_match":
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="特征质量不足: 完整性=0.5")

        # 模拟正常预测结果
        import random
        random.seed(hash(match_id) % 1000)  # 基于match_id的确定性随机

        home_proba = random.uniform(0.3, 0.7)
        draw_proba = random.uniform(0.1, 0.3)
        away_proba = max(0.1, 1.0 - home_proba - draw_proba)

        # 归一化
        total = home_proba + draw_proba + away_proba
        home_proba /= total
        draw_proba /= total
        away_proba /= total

        # 确定预测类别
        probs = [away_proba, draw_proba, home_proba]
        max_idx = np.argmax(probs)
        class_mapping = {0: 'AWAY_WIN', 1: 'DRAW', 2: 'HOME_WIN'}

        self.stats['successful_predictions'] += 1

        return {
            'match_id': match_id,
            'HOME_WIN_PROBA': float(home_proba),
            'DRAW_PROBA': float(draw_proba),
            'AWAY_WIN_PROBA': float(away_proba),
            'predicted_class': class_mapping[max_idx],
            'confidence': float(max(probs)),
            'model_version': '1.0.0',
            'feature_completeness': 0.95,
            'data_quality': 'HIGH',
            'processed_at': datetime.now().isoformat()
        }

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'InferenceService',
            'model_loaded': True,
            'total_predictions': self.stats['successful_predictions'],
            'avg_response_time_ms': 45.2
        }

    def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计"""
        return {
            **self.stats,
            'cache_size': 0,
            'is_initialized': self.is_initialized
        }

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            'model_name': 'football_1x2_classifier',
            'model_version': '1.0.0',
            'is_trained': True,
            'n_features': 13,
            'classes': [0, 1, 2]
        }


@pytest.fixture
def mock_inference_service():
    """创建Mock推理服务"""
    return MockInferenceService()


@pytest.fixture
def app_with_mock(mock_inference_service):
    """创建带有Mock服务的FastAPI应用"""
    from fastapi import FastAPI
    from fastapi.dependencies import get_inference_service

    app = FastAPI()
    app.include_router(router)

    # 覆盖依赖注入
    async def override_get_inference_service():
        return mock_inference_service

    app.dependency_overrides[get_inference_service] = override_get_inference_service

    return app


@pytest.fixture
def client(app_with_mock):
    """创建测试客户端"""
    return TestClient(app_with_mock)


@pytest.fixture
def async_client(app_with_mock):
    """创建异步测试客户端"""
    return httpx.AsyncClient(app=app_with_mock, base_url="http://test")


class TestSingleMatchPrediction:
    """测试单场比赛预测API"""

    def test_predict_match_success(self, client: TestClient):
        """测试正常预测请求"""
        response = client.get("/predict/match/match_12345")

        # 验证响应状态
        assert response.status_code == 200

        # 验证响应数据
        data = response.json()

        # 验证必需字段
        required_fields = [
            'match_id', 'HOME_WIN_PROBA', 'DRAW_PROBA', 'AWAY_WIN_PROBA',
            'predicted_class', 'confidence', 'model_version', 'processed_at'
        ]
        for field in required_fields:
            assert field in data, f"缺少字段: {field}"

        # 验证数据类型和值
        assert data['match_id'] == "match_12345"
        assert isinstance(data['HOME_WIN_PROBA'], float)
        assert isinstance(data['DRAW_PROBA'], float)
        assert isinstance(data['AWAY_WIN_PROBA'], float)
        assert isinstance(data['confidence'], float)

        # 验证概率范围
        assert 0.0 <= data['HOME_WIN_PROBA'] <= 1.0
        assert 0.0 <= data['DRAW_PROBA'] <= 1.0
        assert 0.0 <= data['AWAY_WIN_PROBA'] <= 1.0

        # 验证概率总和（允许小的浮点误差）
        prob_sum = data['HOME_WIN_PROBA'] + data['DRAW_PROBA'] + data['AWAY_WIN_PROBA']
        assert abs(prob_sum - 1.0) < 1e-6, f"概率总和不为1: {prob_sum}"

        # 验证预测类别
        assert data['predicted_class'] in ['HOME_WIN', 'DRAW', 'AWAY_WIN']

        # 验证置信度
        assert 0.0 <= data['confidence'] <= 1.0

    def test_predict_match_not_found(self, client: TestClient):
        """测试不存在的比赛ID"""
        response = client.get("/predict/match/nonexistent_match")

        # 验证响应状态
        assert response.status_code == 404

        # 验证错误响应格式
        data = response.json()
        assert "error" in data
        assert "nonexistent_match" in data["error"]

    def test_predict_match_insufficient_features(self, client: TestClient):
        """测试特征数据不足的比赛"""
        response = client.get("/predict/match/insufficient_features_match")

        # 验证响应状态
        assert response.status_code == 400

        # 验证错误响应格式
        data = response.json()
        assert "error" in data
        assert "特征质量不足" in data["error"]

    def test_predict_match_with_query_params(self, client: TestClient):
        """测试带查询参数的预测请求"""
        response = client.get(
            "/predict/match/match_12345?include_features=true&include_metadata=true"
        )

        assert response.status_code == 200

        data = response.json()

        # 验证额外字段
        if 'feature_completeness' in data:
            assert isinstance(data['feature_completeness'], float)
            assert 0.0 <= data['feature_completeness'] <= 1.0

        if 'data_quality' in data:
            assert data['data_quality'] in ['HIGH', 'MEDIUM', 'LOW', 'FALLBACK']

    def test_predict_match_invalid_match_id(self, client: TestClient):
        """测试无效的比赛ID"""
        # 测试空ID
        response = client.get("/predict/match/")
        assert response.status_code == 404  # FastAPI路由匹配失败

        # 测试过长的ID
        long_id = "x" * 101
        response = client.get(f"/predict/match/{long_id}")
        # 这个测试可能需要根据实际验证逻辑调整

    def test_predict_match_response_headers(self, client: TestClient):
        """测试响应头"""
        response = client.get("/predict/match/match_12345")

        assert response.status_code == 200
        assert "content-type" in response.headers
        assert "application/json" in response.headers["content-type"]


class TestBatchPrediction:
    """测试批量预测API"""

    def test_batch_prediction_success(self, client: TestClient):
        """测试正常批量预测请求"""
        request_data = {
            "match_ids": ["match_1", "match_2", "match_3"],
            "include_features": False,
            "include_metadata": True
        }

        response = client.post("/predict/batch", json=request_data)

        # 验证响应状态
        assert response.status_code == 200

        # 验证响应数据
        data = response.json()

        # 验证必需字段
        required_fields = ['results', 'total_count', 'successful_count', 'failed_count', 'processed_at']
        for field in required_fields:
            assert field in data, f"缺少字段: {field}"

        # 验证统计信息
        assert data['total_count'] == 3
        assert data['successful_count'] == 3
        assert data['failed_count'] == 0
        assert len(data['results']) == 3

        # 验证每个预测结果
        for result in data['results']:
            PredictionResult.validate(result)

    def test_batch_prediction_with_errors(self, client: TestClient):
        """测试包含错误的批量预测"""
        request_data = {
            "match_ids": ["match_1", "nonexistent_match", "match_3"],
            "include_features": False,
            "include_metadata": True
        }

        response = client.post("/predict/batch", json=request_data)

        assert response.status_code == 200

        data = response.json()

        # 验证错误统计
        assert data['total_count'] == 3
        assert data['successful_count'] == 2
        assert data['failed_count'] == 1
        assert len(data['errors']) == 1
        assert len(data['results']) == 2

        # 验证错误信息
        error = data['errors'][0]
        assert error['match_id'] == "nonexistent_match"
        assert "error" in error

    def test_batch_prediction_empty_list(self, client: TestClient):
        """测试空的比赛ID列表"""
        request_data = {
            "match_ids": [],
            "include_features": False,
            "include_metadata": True
        }

        response = client.post("/predict/batch", json=request_data)
        assert response.status_code == 422  # Pydantic验证错误

    def test_batch_prediction_too_many_matches(self, client: TestClient):
        """测试过多的比赛ID"""
        request_data = {
            "match_ids": [f"match_{i}" for i in range(101)],  # 超过100个
            "include_features": False,
            "include_metadata": True
        }

        response = client.post("/predict/batch", json=request_data)
        assert response.status_code == 422  # Pydantic验证错误

    def test_batch_prediction_invalid_json(self, client: TestClient):
        """测试无效JSON请求"""
        response = client.post("/predict/batch", data="invalid json")
        assert response.status_code == 422

    def test_batch_prediction_duplicate_matches(self, client: TestClient):
        """测试重复的比赛ID"""
        request_data = {
            "match_ids": ["match_1", "match_1", "match_2"],
            "include_features": False,
            "include_metadata": True
        }

        response = client.post("/predict/batch", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data['total_count'] == 3
        assert data['successful_count'] == 3


class TestHealthAndStats:
    """测试健康检查和统计API"""

    def test_health_check_success(self, client: TestClient):
        """测试健康检查"""
        response = client.get("/predict/health")

        assert response.status_code == 200

        data = response.json()

        # 验证健康检查字段
        required_fields = ['status', 'timestamp', 'service']
        for field in required_fields:
            assert field in data, f"缺少字段: {field}"

        assert data['status'] == 'healthy'
        assert data['service'] == 'InferenceService'
        assert isinstance(data['timestamp'], str)

    def test_get_stats_success(self, client: TestClient):
        """测试获取统计信息"""
        response = client.get("/predict/stats")

        assert response.status_code == 200

        data = response.json()

        # 验证统计字段
        required_stats = [
            'total_requests', 'successful_predictions', 'cache_hits',
            'fallback_used', 'errors', 'avg_response_time_ms', 'is_initialized'
        ]
        for stat in required_stats:
            assert stat in data, f"缺少统计字段: {stat}"

        # 验证数据类型
        assert isinstance(data['total_requests'], int)
        assert isinstance(data['successful_predictions'], int)
        assert isinstance(data['avg_response_time_ms'], (int, float))
        assert isinstance(data['is_initialized'], bool)

    def test_get_model_info_success(self, client: TestClient):
        """测试获取模型信息"""
        response = client.get("/predict/model/info")

        assert response.status_code == 200

        data = response.json()

        # 验证模型信息字段
        required_fields = ['model_name', 'model_version', 'is_trained', 'n_features']
        for field in required_fields:
            assert field in data, f"缺少模型信息字段: {field}"

        assert data['model_name'] == 'football_1x2_classifier'
        assert isinstance(data['is_trained'], bool)
        assert isinstance(data['n_features'], int)

    def test_model_reload_success(self, client: TestClient):
        """测试模型重新加载"""
        response = client.post("/predict/model/reload")

        assert response.status_code == 200

        data = response.json()

        # 验证响应字段
        required_fields = ['success', 'message', 'reloaded_at']
        for field in required_fields:
            assert field in data, f"缺少字段: {field}"

        assert data['success'] is True
        assert "重新加载成功" in data['message']


class TestErrorHandling:
    """测试错误处理"""

    def test_service_unavailable(self, client: TestClient):
        """测试服务不可用的情况"""
        # 这个测试需要模拟推理服务初始化失败
        # 由于我们使用了Mock服务，这个测试需要在集成测试环境中实现
        pass

    def test_invalid_endpoints(self, client: TestClient):
        """测试无效端点"""
        # 测试不存在的端点
        response = client.get("/predict/invalid_endpoint")
        assert response.status_code == 404

    def test_invalid_methods(self, client: TestClient):
        """测试无效HTTP方法"""
        # 对GET端点使用POST方法
        response = client.post("/predict/match/match_12345")
        assert response.status_code == 405  # Method Not Allowed

    def test_cors_headers(self, client: TestClient):
        """测试CORS头"""
        response = client.options("/predict/match/match_12345")
        # 这个测试取决于CORS配置


class TestPerformance:
    """性能测试"""

    def test_single_prediction_response_time(self, client: TestClient):
        """测试单次预测响应时间"""
        start_time = time.time()
        response = client.get("/predict/match/match_12345")
        end_time = time.time()

        assert response.status_code == 200

        response_time_ms = (end_time - start_time) * 1000
        assert response_time_ms < 1000, f"响应时间过长: {response_time_ms:.2f}ms"

    @pytest.mark.asyncio
    async def test_concurrent_predictions(self, async_client: httpx.AsyncClient):
        """测试并发预测"""
        import asyncio

        # 准备并发请求
        match_ids = [f"match_{i}" for i in range(10)]
        tasks = []

        for match_id in match_ids:
            task = async_client.get(f"/predict/match/{match_id}")
            tasks.append(task)

        # 执行并发请求
        start_time = time.time()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # 验证所有响应
        successful_responses = [r for r in responses if not isinstance(r, Exception)]
        assert len(successful_responses) == 10

        for response in successful_responses:
            assert response.status_code == 200
            data = response.json()
            assert 'HOME_WIN_PROBA' in data

        # 验证并发性能
        total_time_ms = (end_time - start_time) * 1000
        avg_time_ms = total_time_ms / 10

        # 并发应该比串行更快
        assert avg_time_ms < 500, f"平均响应时间过长: {avg_time_ms:.2f}ms"

    def test_batch_prediction_performance(self, client: TestClient):
        """测试批量预测性能"""
        # 准大批量请求
        match_ids = [f"match_{i}" for i in range(50)]
        request_data = {
            "match_ids": match_ids,
            "include_features": False,
            "include_metadata": False
        }

        start_time = time.time()
        response = client.post("/predict/batch", json=request_data)
        end_time = time.time()

        assert response.status_code == 200

        response_time_ms = (end_time - start_time) * 1000
        avg_time_per_prediction = response_time_ms / 50

        # 批量预测应该比单次预测平均更快
        assert avg_time_per_prediction < 100, f"批量预测平均时间过长: {avg_time_per_prediction:.2f}ms"


class TestResponseValidation:
    """响应验证测试"""

    def test_probability_sum_validation(self, client: TestClient):
        """测试概率总和验证"""
        # 测试多个预测，确保概率总和总是1
        for i in range(10):
            response = client.get(f"/predict/match/test_match_{i}")
            assert response.status_code == 200

            data = response.json()
            prob_sum = data['HOME_WIN_PROBA'] + data['DRAW_PROBA'] + data['AWAY_WIN_PROBA']
            assert abs(prob_sum - 1.0) < 1e-6, f"概率总和不为1: {prob_sum} (match_{i})"

    def test_confidence_validation(self, client: TestClient):
        """测试置信度验证"""
        response = client.get("/predict/match/match_confidence_test")
        assert response.status_code == 200

        data = response.json()

        # 置信度应该等于最大概率
        max_prob = max(data['HOME_WIN_PROBA'], data['DRAW_PROBA'], data['AWAY_WIN_PROBA'])
        assert abs(data['confidence'] - max_prob) < 1e-6, "置信度应该等于最大概率"

    def test_datetime_format_validation(self, client: TestClient):
        """测试日期时间格式验证"""
        response = client.get("/predict/match/match_datetime_test")
        assert response.status_code == 200

        data = response.json()

        # 验证时间戳格式
        try:
            datetime.fromisoformat(data['processed_at'].replace('Z', '+00:00'))
        except ValueError:
            pytest.fail("processed_at 不是有效的ISO格式时间戳")


class TestIntegrationScenarios:
    """集成测试场景"""

    def test_end_to_end_prediction_workflow(self, client: TestClient):
        """端到端预测工作流测试"""
        # 1. 健康检查
        health_response = client.get("/predict/health")
        assert health_response.status_code == 200
        assert health_response.json()['status'] == 'healthy'

        # 2. 获取模型信息
        model_response = client.get("/predict/model/info")
        assert model_response.status_code == 200
        model_info = model_response.json()
        assert model_info['is_trained'] is True

        # 3. 单次预测
        predict_response = client.get("/predict/match/integration_match")
        assert predict_response.status_code == 200
        prediction = predict_response.json()
        assert prediction['predicted_class'] in ['HOME_WIN', 'DRAW', 'AWAY_WIN']

        # 4. 获取统计信息
        stats_response = client.get("/predict/stats")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats['total_requests'] > 0
        assert stats['successful_predictions'] > 0

    def test_prediction_consistency(self, client: TestClient):
        """测试预测一致性"""
        match_id = "consistency_test_match"

        # 多次预测同一场比赛
        results = []
        for _ in range(3):
            response = client.get(f"/predict/match/{match_id}")
            assert response.status_code == 200
            results.append(response.json())

        # 由于我们使用确定性Mock，结果应该一致
        first_result = results[0]
        for result in results[1:]:
            assert result['HOME_WIN_PROBA'] == first_result['HOME_WIN_PROBA']
            assert result['predicted_class'] == first_result['predicted_class']

    def test_error_recovery(self, client: TestClient):
        """测试错误恢复"""
        # 1. 请求不存在的比赛
        response = client.get("/predict/match/nonexistent_match")
        assert response.status_code == 404

        # 2. 请求正常比赛应该仍然成功
        response = client.get("/predict/match/normal_match")
        assert response.status_code == 200
        assert 'HOME_WIN_PROBA' in response.json()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])