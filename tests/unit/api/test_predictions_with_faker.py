"""
使用Faker的预测API测试
Prediction API Tests with Faker

使用Faker生成动态测试数据来测试预测API。
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from src.api.app import app
from src.api.predictions.router import (
    PredictionRequest,
    PredictionResult,
    BatchPredictionRequest,
)

client = TestClient(app)


@pytest.mark.unit
@pytest.mark.fast
class TestPredictionsWithFaker:
    """使用Faker测试预测API"""

    def test_create_prediction_with_fake_data(self, fake_prediction):
        """使用假数据测试创建预测"""
        # 准备请求数据
        request_data = {
            "match_id": fake_prediction["match_id"],
            "model_version": fake_prediction["model_version"],
            "include_details": True,
        }

        # 发送请求
        response = client.post("/predictions", json=request_data)

        # 验证响应
        assert response.status_code == 201
        data = response.json()

        # 验证响应结构
        assert "match_id" in data
        assert "home_win_prob" in data
        assert "draw_prob" in data
        assert "away_win_prob" in data
        assert "predicted_outcome" in data
        assert "confidence" in data
        assert "model_version" in data
        assert "predicted_at" in data

        # 验证数据类型和范围
        assert isinstance(data["home_win_prob"], (int, float))
        assert isinstance(data["draw_prob"], (int, float))
        assert isinstance(data["away_win_prob"], (int, float))
        assert data["predicted_outcome"] in ["home", "draw", "away"]
        assert 0 <= data["confidence"] <= 1

    def test_create_multiple_predictions(self, fake_batch_data):
        """测试批量创建预测"""
        # 获取批量假数据
        fake_predictions = fake_batch_data("predictions", 5)

        results = []
        for pred in fake_predictions:
            request_data = {
                "match_id": pred["match_id"],
                "model_version": pred["model_version"],
            }
            response = client.post("/predictions", json=request_data)
            assert response.status_code == 201
            results.append(response.json())

        # 验证所有预测都是唯一的
        match_ids = [r["match_id"] for r in results]
        assert len(match_ids) == len(set(match_ids))

    def test_batch_prediction_endpoint(self, fake_api_request):
        """测试批量预测端点"""
        # 生成批量请求
        request_data = fake_api_request("batch_prediction", match_count=5)

        response = client.post("/predictions/batch", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # 验证批量响应结构
        assert "predictions" in data
        assert "total" in data
        assert "success_count" in data
        assert "failed_count" in data
        assert "failed_match_ids" in data

        assert data["total"] == len(request_data["match_ids"])
        assert len(data["predictions"]) == data["success_count"]
        assert data["success_count"] + data["failed_count"] == data["total"]

    def test_get_prediction_with_fake_id(self, fake_match):
        """使用假ID测试获取预测"""
        match_id = fake_match["match_id"]

        response = client.get(f"/predictions/{match_id}")

        # 可能返回200（如果有缓存）或404（如果没有）
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert data["match_id"] == match_id
            assert "predicted_outcome" in data

    def test_verify_prediction_with_fake_data(self, fake_prediction):
        """使用假数据测试预测验证"""
        match_id = fake_prediction["match_id"]
        actual_result = fake_prediction["predicted_outcome"]  # 使用相同的预测结果

        response = client.post(
            f"/predictions/{match_id}/verify", params={"actual_result": actual_result}
        )

        assert response.status_code == 200
        data = response.json()

        # 验证验证响应结构
        assert "match_id" in data
        assert "prediction" in data
        assert "actual_result" in data
        assert "is_correct" in data
        assert "accuracy_score" in data

        assert data["match_id"] == match_id
        assert data["actual_result"] == actual_result
        assert isinstance(data["is_correct"], bool)
        assert isinstance(data["accuracy_score"], (int, float))

    def test_prediction_history_with_fake_data(self, fake_match):
        """使用假数据测试预测历史"""
        match_id = fake_match["match_id"]
        limit = 5

        response = client.get(
            f"/predictions/history/{match_id}", params={"limit": limit}
        )

        assert response.status_code == 200
        data = response.json()

        # 验证历史响应结构
        assert "match_id" in data
        assert "predictions" in data
        assert "total_predictions" in data

        assert data["match_id"] == match_id
        assert len(data["predictions"]) <= limit
        assert data["total_predictions"] == len(data["predictions"])

    def test_recent_predictions_with_fake_data(self, fake_batch_data):
        """测试获取最近预测"""
        # 先创建一些预测
        fake_predictions = fake_batch_data("predictions", 10)
        for pred in fake_predictions[:3]:  # 只创建3个
            client.post(
                "/predictions",
                json={
                    "match_id": pred["match_id"],
                    "model_version": pred["model_version"],
                },
            )

        # 获取最近预测
        response = client.get("/predictions/recent", params={"limit": 5, "hours": 24})

        assert response.status_code == 200
        data = response.json()

        # 验证是列表格式
        assert isinstance(data, list)
        assert len(data) <= 5

        # 验证每个元素的结构
        if data:
            item = data[0]
            assert "id" in item
            assert "match_id" in item
            assert "home_team" in item
            assert "away_team" in item
            assert "prediction" in item
            assert "match_date" in item


@pytest.mark.unit
@pytest.mark.fast
class TestPredictionValidation:
    """测试预测验证功能"""

    def test_prediction_request_validation(self, fake_api_request):
        """测试预测请求验证"""
        # 测试有效请求
        valid_request = fake_api_request("prediction")
        response = client.post("/predictions", json=valid_request)
        assert response.status_code == 201

        # 测试无效的match_id
        invalid_request = {
            "match_id": "invalid",  # 应该是整数
            "model_version": "default",
        }
        response = client.post("/predictions", json=invalid_request)
        assert response.status_code == 422

        # 测试无效的model_version（太长）
        invalid_request = {
            "match_id": 123,
            "model_version": "x" * 101,  # 超过长度限制
        }
        response = client.post("/predictions", json=invalid_request)
        assert response.status_code == 422

    def test_batch_prediction_validation(self):
        """测试批量预测验证"""
        # 测试空列表
        response = client.post("/predictions/batch", json={"match_ids": []})
        assert response.status_code == 422

        # 测试超过限制的列表
        response = client.post(
            "/predictions/batch",
            json={
                "match_ids": list(range(101))  # 超过100个
            },
        )
        assert response.status_code == 422

        # 测试无效的match_id类型
        response = client.post(
            "/predictions/batch", json={"match_ids": ["invalid", "also_invalid"]}
        )
        assert response.status_code == 422

    def test_verification_validation(self):
        """测试验证请求验证"""
        # 测试无效的actual_result
        response = client.post(
            "/predictions/123/verify", params={"actual_result": "invalid"}
        )
        assert response.status_code == 422

        # 测试有效的actual_result
        for result in ["home", "draw", "away"]:
            response = client.post(
                "/predictions/123/verify", params={"actual_result": result}
            )
            # 可能返回200（成功）或404（预测不存在）
            assert response.status_code in [200, 404]


@pytest.mark.unit
@pytest.mark.fast
class TestPredictionErrorHandling:
    """测试预测错误处理"""

    def test_prediction_not_found(self):
        """测试获取不存在的预测"""
        # 使用一个不太可能存在的ID
        response = client.get("/predictions/999999")
        assert response.status_code == 200  # 端点返回模拟数据

    def test_batch_prediction_with_errors(self, fake_api_request):
        """测试批量预测中的错误处理"""
        # 混合有效和无效的ID
        request_data = {"match_ids": [123, 456, 789], "model_version": "default"}

        with patch("src.api.predictions.router.logger"):
            response = client.post("/predictions/batch", json=request_data)

            # 应该成功处理
            assert response.status_code == 200
            data = response.json()

            # 验证结构
            assert "failed_match_ids" in data
            assert isinstance(data["failed_match_ids"], list)

    def test_server_error_handling(self):
        """测试服务器错误处理"""
        # 模拟服务器错误
        with patch("src.api.predictions.router.datetime") as mock_datetime:
            mock_datetime.utcnow.side_effect = Exception("Server error")

            response = client.post(
                "/predictions", json={"match_id": 123, "model_version": "default"}
            )

            # 应该返回500错误
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Prediction failed" in data["detail"]
