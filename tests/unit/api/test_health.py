"""API测试模板"""

import pytest
from fastapi import status
from unittest.mock import patch


class TestHealthAPI:
    """健康检查API测试"""

    def test_health_check_success(self, api_client):
        """测试健康检查成功"""
        response = api_client.get("/api/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    @pytest.mark.skip(reason="需要重构：当前API不支持check_db参数")
    def test_health_check_with_database(self, api_client, mock_db_session):
        """测试带数据库检查的健康检查"""
        with patch("src.api.health.database.check") as mock_check:
            mock_check.return_value = True

            response = api_client.get("/api/health?check_db=true")

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["database"] == "connected"

    @pytest.mark.parametrize("endpoint", ["/api/health", "/api/health/"])
    def test_health_check_endpoints(self, api_client, endpoint):
        """测试多个健康检查端点"""
        response = api_client.get(endpoint)
        assert response.status_code == status.HTTP_200_OK


class TestPredictionAPI:
    """预测API测试"""

    @pytest.mark.skip(reason="需要实现auth_headers和sample_prediction_data fixtures")
    def test_create_prediction_success(self, api_client, auth_headers, sample_prediction_data):
        """测试创建预测成功"""
        with patch("src.api.predictions.PredictionService") as mock_service:
            mock_service.create_prediction.return_value = {
                "id": 1,
                **sample_prediction_data,
                "status": "pending"
            }

            response = api_client.post(
                "/api/predictions",
                json=sample_prediction_data,
                headers=auth_headers
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["id"] == 1
            assert data["status"] == "pending"

    @pytest.mark.skip(reason="需要实现sample_prediction_data fixture")
    def test_create_prediction_unauthorized(self, api_client, sample_prediction_data):
        """测试未授权创建预测"""
        response = api_client.post("/api/predictions", json=sample_prediction_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.skip(reason="需要实现auth_headers fixture")
    def test_create_prediction_invalid_data(self, api_client, auth_headers):
        """测试无效数据创建预测"""
        invalid_data = {"match_id": "invalid"}

        response = api_client.post(
            "/api/predictions",
            json=invalid_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.skip(reason="需要实现auth_headers fixture")
    def test_get_prediction_success(self, api_client, auth_headers):
        """测试获取预测成功"""
        with patch("src.api.predictions.PredictionService") as mock_service:
            mock_service.get_prediction.return_value = {
                "id": 1,
                "result": "2-1",
                "confidence": 0.75
            }

            response = api_client.get("/api/predictions/1", headers=auth_headers)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == 1

    @pytest.mark.skip(reason="需要实现auth_headers fixture")
    def test_get_prediction_not_found(self, api_client, auth_headers):
        """测试获取不存在的预测"""
        with patch("src.api.predictions.PredictionService") as mock_service:
            mock_service.get_prediction.return_value = None

            response = api_client.get("/api/predictions/999", headers=auth_headers)

            assert response.status_code == status.HTTP_404_NOT_FOUND
