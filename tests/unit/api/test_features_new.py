from typing import Optional

"""API特征端点测试"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


class TestAPIFeatures:
    """API特征端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from src.api.app import app

        return TestClient(app)

    def test_get_features_list(self, client):
        """测试获取特征列表"""
        with patch("src.api.features.get_features") as mock_get:
            mock_get.return_value = [
                {
                    "name": "goals_scored",
                    "type": "numeric",
                    "description": "Number of goals scored",
                },
                {
                    "name": "possession",
                    "type": "percentage",
                    "description": "Ball possession percentage",
                },
            ]

            response = client.get("/api/features")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2

    def test_calculate_features(self, client):
        """测试计算特征"""
        match_data = {
            "match_id": 123,
            "home_team": "Team A",
            "away_team": "Team B",
            "historical_data": True,
        }

        with patch("src.api.features.calculate_match_features") as mock_calc:
            mock_calc.return_value = {
                "home_goals_avg": 2.5,
                "away_goals_avg": 1.8,
                "home_form": [1, 1, 0, 1, 1],
                "away_form": [0, 1, 0, 0, 1],
            }

            response = client.post("/api/features/calculate", json=match_data)
            assert response.status_code == 200
            data = response.json()
            assert "home_goals_avg" in data

    def test_get_feature_importance(self, client):
        """测试获取特征重要性"""
        with patch("src.api.features.get_feature_importance") as mock_importance:
            mock_importance.return_value = {
                "features": [
                    {"name": "goals_scored", "importance": 0.35},
                    {"name": "possession", "importance": 0.25},
                    {"name": "recent_form", "importance": 0.20},
                ]
            }

            response = client.get("/api/features/importance")
            assert response.status_code == 200
            data = response.json()
            assert "features" in data
            assert len(data["features"]) == 3

    def test_feature_validation(self, client):
        """测试特征验证"""
        invalid_data = {
            "match_id": None,  # 无效的match_id
            "home_team": "",  # 空字符串
        }

        response = client.post("/api/features/calculate", json=invalid_data)
        assert response.status_code == 422

    def test_batch_feature_calculation(self, client):
        """测试批量特征计算"""
        batch_data = {
            "matches": [
                {"match_id": 1, "home_team": "A", "away_team": "B"},
                {"match_id": 2, "home_team": "C", "away_team": "D"},
            ]
        }

        with patch("src.api.features.batch_calculate_features") as mock_batch:
            mock_batch.return_value = {
                "results": [
                    {"match_id": 1, "features": {"goal_diff": 1.5}},
                    {"match_id": 2, "features": {"goal_diff": -0.5}},
                ]
            }

            response = client.post("/api/features/batch-calculate", json=batch_data)
            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 2