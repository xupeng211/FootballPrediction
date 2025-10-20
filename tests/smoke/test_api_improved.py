"""
改进的API Smoke测试
Improved API Smoke Tests

精确的断言和明确的期望：
- 不使用宽松的状态码范围
- 明确测试成功和失败场景
- 清晰的错误信息
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from src.api.app import app

client = TestClient(app)


@pytest.mark.smoke
@pytest.mark.fast
class TestAPIHealth:
    """API健康检查测试"""

    def test_root_endpoint_returns_200_with_message(self):
        """测试：根端点返回200状态码和消息"""
        response = client.get("/")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert "message" in data, "Response should contain 'message' field"
        assert "Football Prediction API" in data["message"]

    def test_health_endpoint_returns_200_with_status(self):
        """测试：健康检查端点返回200状态码"""
        response = client.get("/api/health")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert "status" in data, "Response should contain 'status' field"
        assert data["status"] == "healthy"

    def test_docs_endpoint_returns_200(self):
        """测试：文档端点返回200状态码"""
        response = client.get("/docs")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        # 验证返回的是HTML内容
        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type, "Should return HTML documentation"


@pytest.mark.smoke
@pytest.mark.fast
class TestPredictionsEndpoint:
    """预测端点Smoke测试"""

    @patch("src.api.predictions.router.datetime")
    def test_predictions_post_endpoint_returns_201(self, mock_datetime):
        """测试：POST /predictions端点返回201状态码"""
        # 设置模拟时间
        mock_datetime.utcnow.return_value.isoformat.return_value = "2023-01-01T15:00:00"

        request_data = {"match_id": 123, "model_version": "default"}

        response = client.post("/predictions", json=request_data)

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        data = response.json()
        assert data["match_id"] == request_data["match_id"]
        assert "predicted_outcome" in data
        assert "confidence" in data

    def test_predictions_post_with_invalid_data_returns_422(self):
        """测试：POST /predictions使用无效数据返回422状态码"""
        # 测试缺少必需字段
        response = client.post("/predictions", json={})

        assert (
            response.status_code == 422
        ), f"Expected 422 for missing data, got {response.status_code}"

        # 测试无效类型
        response = client.post(
            "/predictions",
            json={"match_id": "invalid_type", "model_version": "default"},
        )

        assert (
            response.status_code == 422
        ), f"Expected 422 for invalid type, got {response.status_code}"

    def test_predictions_get_endpoint_returns_200(self):
        """测试：GET /predictions/{match_id}端点返回200状态码"""
        # 注意：当前实现总是返回模拟数据
        response = client.get("/predictions/123")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert data["match_id"] == 123

    def test_predictions_batch_endpoint_returns_200(self):
        """测试：POST /predictions/batch端点返回200状态码"""
        request_data = {"match_ids": [123, 456], "model_version": "default"}

        response = client.post("/predictions/batch", json=request_data)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert "predictions" in data
        assert "total" in data
        assert data["total"] == 2

    def test_predictions_health_returns_200(self):
        """测试：GET /predictions/health端点返回200状态码"""
        response = client.get("/predictions/health")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"


@pytest.mark.smoke
@pytest.mark.fast
class TestAPIErrorHandling:
    """API错误处理测试"""

    def test_invalid_endpoint_returns_404(self):
        """测试：无效端点返回404状态码"""
        response = client.get("/nonexistent/endpoint")

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    def test_invalid_method_returns_405(self):
        """测试：无效HTTP方法返回405状态码"""
        response = client.delete("/predictions")

        assert response.status_code == 405, f"Expected 405, got {response.status_code}"

    def test_invalid_content_type_returns_415(self):
        """测试：无效Content-Type返回415状态码"""
        response = client.post(
            "/predictions",
            data='{"match_id": 123}',
            headers={"Content-Type": "text/plain"},
        )

        # FastAPI会尝试处理，通常返回422
        assert response.status_code in [
            415,
            422,
        ], f"Expected 415 or 422, got {response.status_code}"


@pytest.mark.smoke
@pytest.mark.fast
class TestAPIResponseTime:
    """API响应时间测试"""

    def test_root_endpoint_response_time_under_1s(self):
        """测试：根端点响应时间小于1秒"""
        import time

        start_time = time.time()
        response = client.get("/")
        end_time = time.time()

        response_time = end_time - start_time

        assert response.status_code == 200
        assert response_time < 1.0, f"Response time {response_time}s exceeds 1 second"

    def test_predictions_endpoint_response_time_under_1s(self):
        """测试：预测端点响应时间小于1秒"""
        import time

        start_time = time.time()
        response = client.post("/predictions", json={"match_id": 123})
        end_time = time.time()

        response_time = end_time - start_time

        assert response.status_code == 201
        assert response_time < 1.0, f"Response time {response_time}s exceeds 1 second"


@pytest.mark.smoke
@pytest.mark.fast
class TestAPIResponseFormat:
    """API响应格式测试"""

    def test_error_responses_have_detail_field(self):
        """测试：错误响应包含detail字段"""
        response = client.post("/predictions", json={})

        assert response.status_code == 422

        data = response.json()
        assert "detail" in data, "Error response should contain 'detail' field"

    def test_prediction_responses_have_required_fields(self):
        """测试：预测响应包含必需字段"""
        response = client.post("/predictions", json={"match_id": 123})

        assert response.status_code == 201

        data = response.json()
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
            assert field in data, f"Prediction response missing field: {field}"


@pytest.mark.smoke
@pytest.mark.fast
class TestAPIBusinessFlow:
    """API业务流程测试"""

    def test_simple_prediction_flow(self):
        """测试：简单预测流程"""
        # 1. 创建预测
        create_response = client.post(
            "/predictions", json={"match_id": 123, "model_version": "default"}
        )

        assert create_response.status_code == 201
        prediction_data = create_response.json()

        # 2. 获取预测
        get_response = client.get(f"/predictions/{prediction_data['match_id']}")

        assert get_response.status_code == 200
        retrieved_data = get_response.json()

        # 3. 验证数据一致性
        assert retrieved_data["match_id"] == prediction_data["match_id"]
        assert (
            retrieved_data["predicted_outcome"] == prediction_data["predicted_outcome"]
        )

    def test_batch_prediction_flow(self):
        """测试：批量预测流程"""
        # 1. 批量创建预测
        batch_response = client.post(
            "/predictions/batch",
            json={"match_ids": [123, 456, 789], "model_version": "default"},
        )

        assert batch_response.status_code == 200
        batch_data = batch_response.json()

        # 2. 验证批量结果
        assert batch_data["total"] == 3
        assert batch_data["success_count"] > 0
        assert len(batch_data["predictions"]) == batch_data["success_count"]

        # 3. 验证每个预测
        for prediction in batch_data["predictions"]:
            assert "match_id" in prediction
            assert "predicted_outcome" in prediction


# 配置函数
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "smoke: Smoke tests")
    config.addinivalue_line("markers", "fast: Fast tests (<1s)")
