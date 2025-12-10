from typing import Optional

"""API预测端点测试"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


class TestAPIPredictions:
    """API预测端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from src.api.app import app

        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        """认证头"""
        return {"Authorization": "Bearer test-token"}

    def test_get_predictions_list(self, client, auth_headers):
        """测试获取预测列表"""
        with patch("src.api.predictions.get_predictions") as mock_get:
            mock_get.return_value = [
                {"id": 1, "match": "Team A vs Team B", "prediction": "Win"},
                {"id": 2, "match": "Team C vs Team D", "prediction": "Draw"},
            ]

            response = client.get("/api/predictions", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2

    def test_create_prediction(self, client, auth_headers):
        """测试创建预测"""
        prediction_data = {
            "match_id": 123,
            "predicted_winner": "Team A",
            "confidence": 0.85,
            "features": {"goals": 2.5, "possession": 60},
        }

        with patch("src.api.predictions.create_prediction") as mock_create:
            mock_create.return_value = {"id": 999, **prediction_data}

            response = client.post(
                "/api/predictions", json=prediction_data, headers=auth_headers
            )
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 999
            assert data["match_id"] == 123

    def test_get_prediction_by_id(self, client, auth_headers):
        """测试根据ID获取预测"""
        with patch("src.api.predictions.get_prediction_by_id") as mock_get:
            mock_get.return_value = {
                "id": 1,
                "match": "Team A vs Team B",
                "prediction": "Win",
                "confidence": 0.85,
            }

            response = client.get("/api/predictions/1", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1

    def test_prediction_not_found(self, client, auth_headers):
        """测试预测不存在"""
        with patch("src.api.predictions.get_prediction_by_id") as mock_get:
            mock_get.return_value = None

            response = client.get("/api/predictions/9999", headers=auth_headers)
            assert response.status_code == 404

    def test_invalid_prediction_data(self, client, auth_headers):
        """测试无效的预测数据"""
        invalid_data = {"match_id": "not-a-number", "confidence": 1.5}  # 超出0-1范围

        response = client.post(
            "/api/predictions", json=invalid_data, headers=auth_headers
        )
        assert response.status_code == 422

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/predictions")
        assert response.status_code == 401
