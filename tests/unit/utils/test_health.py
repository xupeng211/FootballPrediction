# TODO: Consider creating a fixture for 5 repeated Mock creations

# TODO: Consider creating a fixture for 5 repeated Mock creations

from unittest.mock import AsyncMock, MagicMock, patch

"""API测试模板"""

import pytest
from fastapi import status

from src.api import predictions as predictions_module


@pytest.mark.unit
class TestHealthAPI:
    """健康检查API测试"""

    def test_health_check_success(self, api_client):
        """测试健康检查成功"""
        response = api_client.get("/api/health")

        assert response.status_code == status.HTTP_200_OK
        _data = response.json()
        assert _data["status"] == "healthy"
        assert "timestamp" in _data

        assert "version" in _data

    def test_health_check_with_database(self, api_client):
        """测试带数据库检查的健康检查"""
        with patch("src.api.health._collect_database_health", new=AsyncMock()) as mock_check:
            mock_check.return_value = {
                "healthy": True,
                "status": "healthy",
                "response_time_ms": 10,
                "details": {"message": "数据库连接正常"},
            }

            response = api_client.get("/api/health?check_db=true")

            assert response.status_code == status.HTTP_200_OK
            _data = response.json()
            assert _data["checks"]["database"]["status"] == "healthy"

    @pytest.mark.parametrize("endpoint", ["/api/health", "/api/health/"])
    def test_health_check_endpoints(self, api_client, endpoint):
        """测试多个健康检查端点"""
        response = api_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK


class TestPredictionAPI:
    """预测API路由测试"""

    def test_predictions_route_available_in_full_mode(self, api_client_full, sample_match):
        """在完整模式下预测路由可用，并可返回实时预测结果"""
        mock_match_result = MagicMock()
        mock_match_result.scalar_one_or_none.return_value = sample_match
        mock_prediction_result = MagicMock()
        mock_prediction_result.scalar_one_or_none.return_value = None

        api_client_full.mock_session.execute.side_effect = [
            mock_match_result,
            mock_prediction_result,
        ]

        prediction_payload = {
            "id": 42,
            "model_version": "2.1",
            "predicted_result": "home",
            "home_win_probability": 0.6,
            "draw_probability": 0.25,
            "away_win_probability": 0.15,
            "confidence_score": 0.8,
        }

        async_mock = AsyncMock()
        async_mock.return_value = MagicMock(to_dict=lambda: prediction_payload)

        with patch.object(predictions_module.prediction_service, "predict_match", new=async_mock):
            response = api_client_full.get("/api/v1/predictions/12345?force_predict=true")

        _data = response.json()
        assert response.status_code == status.HTTP_200_OK, data
        assert _data["success"] is True
        assert _data["data"]["match_id"] == 12345
        assert _data["data"]["prediction"]["id"] == 42
