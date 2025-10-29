"""API数据端点扩展测试"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestAPIDataExtended:
    """API数据端点扩展测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
from src.api.app import app

        return TestClient(app)

    def test_get_matches(self, client):
        """测试获取比赛列表"""
        with patch("src.api.data.get_matches") as mock_get:
            mock_get.return_value = [
                {"id": 1, "home": "Team A", "away": "Team B", "date": "2024-01-01"},
                {"id": 2, "home": "Team C", "away": "Team D", "date": "2024-01-02"},
            ]

            response = client.get("/api/data/matches")
            assert response.status_code == 200
            _data = response.json()
            assert len(data) == 2

    def test_get_matches_with_filters(self, client):
        """测试带过滤器的比赛查询"""
        with patch("src.api.data.get_matches") as mock_get:
            mock_get.return_value = [
                {
                    "id": 1,
                    "home": "Team A",
                    "away": "Team B",
                    "league": "Premier League",
                }
            ]

            response = client.get("/api/data/matches?league=Premier League&date=2024-01-01")
            assert response.status_code == 200
            mock_get.assert_called_once()

    def test_get_match_by_id(self, client):
        """测试根据ID获取比赛"""
        with patch("src.api.data.get_match_by_id") as mock_get:
            mock_get.return_value = {
                "id": 1,
                "home": "Team A",
                "away": "Team B",
                "score": {"home": 2, "away": 1},
                "stats": {"possession": {"home": 60, "away": 40}},
            }

            response = client.get("/api/data/matches/1")
            assert response.status_code == 200
            _data = response.json()
            assert _data["id"] == 1
            assert "score" in _data

    def test_get_teams(self, client):
        """测试获取球队列表"""
        with patch("src.api.data.get_teams") as mock_get:
            mock_get.return_value = [
                {"id": 1, "name": "Team A", "league": "Premier League"},
                {"id": 2, "name": "Team B", "league": "Premier League"},
            ]

            response = client.get("/api/data/teams")
            assert response.status_code == 200
            _data = response.json()
            assert len(data) == 2

    def test_export_data_csv(self, client):
        """测试导出CSV数据"""
        with patch("src.api.data.export_matches_csv") as mock_export:
            mock_export.return_value = "id,home,away,date\n1,Team A,Team B,2024-01-01\n"

            response = client.get("/api/data/export/csv")
            assert response.status_code == 200
            assert "text/csv" in response.headers["content-type"]

    def test_export_data_json(self, client):
        """测试导出JSON数据"""
        with patch("src.api.data.export_matches_json") as mock_export:
            mock_export.return_value = {"matches": []}

            response = client.get("/api/data/export/json")
            assert response.status_code == 200
            _data = response.json()
            assert "matches" in _data

    def test_data_validation_error(self, client):
        """测试数据验证错误"""
        response = client.get("/api/data/matches?date=invalid-date")
        assert response.status_code == 400
