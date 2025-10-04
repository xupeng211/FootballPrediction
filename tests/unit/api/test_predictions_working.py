"""预测API单元测试（工作版）"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status


class TestPredictionsAPI:
    """预测API测试"""

    def test_batch_predict_too_many_matches(self, api_client_full):
        """测试批量预测比赛数量超过限制"""
        # Create 51 match IDs (exceeding the 50 limit)
        match_ids = list(range(1, 52))

        # Make request
        response = api_client_full.post(
            "/api/v1/predictions/batch",
            json=match_ids,
        )

        # Verify response
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        # Check if error message is in detail or message field
        error_msg = data.get("detail", data.get("message", ""))
        assert "批量预测最多支持50场比赛" in error_msg

    @pytest.mark.asyncio
    async def test_verify_prediction_success(self, api_client_full):
        """测试验证预测成功"""
        # Mock the prediction service
        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.verify_prediction = AsyncMock(return_value=True)

            # Make request
            response = api_client_full.post("/api/v1/predictions/12345/verify")

            # Verify response
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["match_id"] == 12345
            assert data["data"]["verified"] is True
            assert "预测结果验证完成" in data["message"]

    @pytest.mark.asyncio
    async def test_verify_prediction_failure(self, api_client_full):
        """测试验证预测失败"""
        # Mock the prediction service
        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.verify_prediction = AsyncMock(return_value=False)

            # Make request
            response = api_client_full.post("/api/v1/predictions/12345/verify")

            # Verify response
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is False
            assert data["data"]["verified"] is False
            assert "验证失败" in data["message"]

    @pytest.mark.asyncio
    async def test_verify_prediction_service_error(self, api_client_full):
        """测试验证预测服务错误"""
        # Mock the prediction service to raise an exception
        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.verify_prediction = AsyncMock(
                side_effect=Exception("Verification failed")
            )

            # Make request
            response = api_client_full.post("/api/v1/predictions/12345/verify")

            # Verify response
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_batch_predict_empty_list(self, api_client_full):
        """测试批量预测空列表"""
        # Make request with empty list
        response = api_client_full.post(
            "/api/v1/predictions/batch",
            json=[],
        )

        # Verify response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_requested"] == 0
        assert data["data"]["valid_matches"] == 0
        assert data["data"]["successful_predictions"] == 0

    def test_batch_predict_single_match(self, api_client_full):
        """测试批量预测单场比赛"""
        # Mock dependencies
        with patch("src.api.predictions.prediction_service") as mock_service:
            # Mock batch predict
            mock_result = MagicMock()
            mock_result.to_dict.return_value = {
                "match_id": 1,
                "predicted_result": "home_win",
                "confidence": 0.75,
            }
            mock_service.batch_predict_matches = AsyncMock(return_value=[mock_result])

            # Make request
            response = api_client_full.post(
                "/api/v1/predictions/batch",
                json=[1],
            )

            # Verify response
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert data["data"]["total_requested"] == 1
            assert data["data"]["valid_matches"] == 1
            assert data["data"]["successful_predictions"] == 1
            assert len(data["data"]["predictions"]) == 1

    @pytest.mark.asyncio
    async def test_predict_match_service_error(self, api_client_full):
        """测试预测服务错误"""
        # Mock the prediction service to raise an exception
        with patch("src.api.predictions.prediction_service") as mock_service:
            mock_service.predict_match = AsyncMock(
                side_effect=Exception("Prediction service failed")
            )

            # Make request
            response = api_client_full.post("/api/v1/predictions/12345/predict")

            # Verify response
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
