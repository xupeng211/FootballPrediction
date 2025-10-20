"""
改进的预测API测试
Improved Prediction API Tests

遵循最佳实践：
- 使用精确的patch而不是全局mock
- 明确的断言和错误验证
- 统一的测试命名约定
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../src"))

from src.api.app import app
from src.api.predictions.router import PredictionRequest, PredictionResult

client = TestClient(app)


@pytest.mark.unit
@pytest.mark.api
class TestPredictionsAPI:
    """预测API测试类"""

    @patch("src.api.predictions.router.datetime")
    def test_create_prediction_with_valid_data_returns_201(self, mock_datetime):
        """测试：使用有效数据创建预测返回201状态码"""
        # 设置模拟时间
        mock_datetime.utcnow.return_value.isoformat.return_value = "2023-01-01T15:00:00"

        # 准备请求数据
        request_data = {
            "match_id": 123,
            "model_version": "v1.0",
            "include_details": True,
        }

        # 发送请求
        response = client.post("/predictions", json=request_data)

        # 明确的断言
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        data = response.json()

        # 验证响应结构
        required_fields = [
            "match_id",
            "home_win_prob",
            "draw_prob",
            "away_win_prob",
            "predicted_outcome",
            "confidence",
            "model_version",
            "predicted_at",
        ]
        for field in required_fields:
            assert field in data, f"Missing field in response: {field}"

        # 验证数据类型和范围
        assert isinstance(data["home_win_prob"], (int, float))
        assert isinstance(data["draw_prob"], (int, float))
        assert isinstance(data["away_win_prob"], (int, float))
        assert data["predicted_outcome"] in ["home", "draw", "away"]
        assert 0 <= data["confidence"] <= 1
        assert data["match_id"] == request_data["match_id"]

    def test_create_prediction_with_invalid_match_id_returns_422(self):
        """测试：使用无效的match_id创建预测返回422状态码"""
        request_data = {
            "match_id": "invalid",  # 错误：应该是整数
            "model_version": "v1.0",
        }

        response = client.post("/predictions", json=request_data)

        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

        # 验证错误详情
        error_detail = response.json()
        assert "detail" in error_detail
        assert any("match_id" in str(err) for err in error_detail["detail"])

    def test_create_prediction_with_invalid_model_version_returns_422(self):
        """测试：使用过长的model_version返回422状态码"""
        request_data = {
            "match_id": 123,
            "model_version": "x" * 101,  # 超过100字符限制
        }

        response = client.post("/predictions", json=request_data)

        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    @patch("src.api.predictions.router.datetime")
    def test_get_existing_prediction_returns_200(self, mock_datetime):
        """测试：获取存在的预测返回200状态码"""
        mock_datetime.utcnow.return_value.isoformat.return_value = "2023-01-01T15:00:00"

        match_id = 123
        response = client.get(f"/predictions/{match_id}")

        # 当前实现总是返回200（模拟数据）
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert data["match_id"] == match_id
        assert "predicted_outcome" in data

    def test_batch_prediction_with_valid_data_returns_200(self):
        """测试：批量预测有效数据返回200状态码"""
        request_data = {"match_ids": [123, 456, 789], "model_version": "v1.0"}

        response = client.post("/predictions/batch", json=request_data)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()

        # 验证批量响应结构
        required_fields = ["predictions", "total", "success_count", "failed_count"]
        for field in required_fields:
            assert field in data, f"Missing field in batch response: {field}"

        # 验证数据一致性
        assert data["total"] == len(request_data["match_ids"])
        assert data["success_count"] + data["failed_count"] == data["total"]
        assert len(data["predictions"]) == data["success_count"]

    def test_batch_prediction_with_empty_list_returns_422(self):
        """测试：批量预测空列表返回422状态码"""
        request_data = {
            "match_ids": [],  # 空：不允许
            "model_version": "v1.0",
        }

        response = client.post("/predictions/batch", json=request_data)

        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    def test_batch_prediction_with_too_many_matches_returns_422(self):
        """测试：批量预测超过限制数量返回422状态码"""
        request_data = {
            "match_ids": list(range(101)),  # 超过100个限制
            "model_version": "v1.0",
        }

        response = client.post("/predictions/batch", json=request_data)

        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    @pytest.mark.parametrize("actual_result", ["home", "draw", "away"])
    def test_verify_prediction_with_valid_result_returns_200(self, actual_result):
        """测试：使用有效结果验证预测返回200状态码"""
        match_id = 123

        response = client.post(
            f"/predictions/{match_id}/verify", params={"actual_result": actual_result}
        )

        # 当前实现总是返回200（模拟数据）
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert data["match_id"] == match_id
        assert data["actual_result"] == actual_result
        assert "is_correct" in data
        assert "accuracy_score" in data

    def test_verify_prediction_with_invalid_result_returns_422(self):
        """测试：使用无效结果验证预测返回422状态码"""
        response = client.post(
            "/predictions/123/verify", params={"actual_result": "invalid"}
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    @patch("src.api.predictions.router.datetime")
    def test_prediction_history_with_valid_limit_returns_200(self, mock_datetime):
        """测试：使用有效限制获取预测历史返回200状态码"""
        mock_datetime.utcnow.return_value = mock_datetime.utcnow.return_value

        match_id = 123
        limit = 5

        response = client.get(
            f"/predictions/history/{match_id}", params={"limit": limit}
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert data["match_id"] == match_id
        assert "predictions" in data
        assert "total_predictions" in data
        assert len(data["predictions"]) <= limit

    def test_prediction_history_with_invalid_limit_returns_422(self):
        """测试：使用无效限制获取预测历史返回422状态码"""
        response = client.get(
            "/predictions/123/history",
            params={"limit": 0},  # 低于最小值1
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    @patch("src.api.predictions.router.datetime")
    def test_recent_predictions_with_valid_params_returns_200(self, mock_datetime):
        """测试：使用有效参数获取最近预测返回200状态码"""
        mock_datetime.utcnow.return_value.isoformat.return_value = "2023-01-01T15:00:00"

        response = client.get("/predictions/recent", params={"limit": 10, "hours": 24})

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    def test_health_check_returns_200(self):
        """测试：健康检查返回200状态码"""
        response = client.get("/predictions/health")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert "status" in data
        assert "service" in data
        assert data["service"] == "predictions"


@pytest.mark.unit
@pytest.mark.api
class TestPredictionAPIErrors:
    """预测API错误处理测试类"""

    @patch("src.api.predictions.router.datetime")
    def test_prediction_endpoint_handles_server_error(self, mock_datetime):
        """测试：预测端点处理服务器错误"""
        # 模拟内部服务器错误
        mock_datetime.utcnow.side_effect = Exception("Database connection failed")

        response = client.post(
            "/predictions", json={"match_id": 123, "model_version": "v1.0"}
        )

        assert response.status_code == 500, f"Expected 500, got {response.status_code}"

        data = response.json()
        assert "detail" in data
        assert "Prediction failed" in data["detail"]

    def test_missing_request_body_returns_422(self):
        """测试：缺少请求体返回422状态码"""
        response = client.post("/predictions")

        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    def test_invalid_json_returns_422(self):
        """测试：无效JSON返回422状态码"""
        response = client.post(
            "/predictions",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422, f"Expected 422, got {response.status_code}"


@pytest.mark.unit
@pytest.mark.api
class TestPredictionAPIEdgeCases:
    """预测API边界情况测试类"""

    def test_prediction_with_minimal_data(self):
        """测试：使用最小必需数据创建预测"""
        request_data = {
            "match_id": 1  # 只提供必需字段
        }

        response = client.post("/predictions", json=request_data)

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        data = response.json()
        assert data["match_id"] == 1
        assert data["model_version"] == "default"  # 默认值
        assert data["features"] is None  # 默认值

    def test_prediction_with_maximal_data(self):
        """测试：使用完整数据创建预测"""
        request_data = {
            "match_id": 999999,
            "model_version": "v" * 100,  # 最大长度
            "include_details": True,
        }

        response = client.post("/predictions", json=request_data)

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

    def test_batch_prediction_edge_case_max_items(self):
        """测试：批量预测边界情况-最大项目数"""
        request_data = {
            "match_ids": list(range(100)),  # 刚好100个
            "model_version": "v1.0",
        }

        response = client.post("/predictions/batch", json=request_data)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert data["total"] == 100

    def test_get_prediction_with_extreme_match_id(self):
        """测试：使用极端match_id获取预测"""
        extreme_ids = [0, 1, 999999999, -1]

        for match_id in extreme_ids:
            response = client.get(f"/predictions/{match_id}")
            # 当前实现总是返回200（模拟数据）
            assert response.status_code == 200, f"Failed for match_id: {match_id}"
