"""
Test factories package
"""

from .team_factory import TeamFactory
from .user_factory import UserFactory


# Additional factories can be added as needed
def DataFactory(data_type: str, **kwargs):
    """Generic data factory for testing"""
    if data_type == "user":
        return UserFactory.create_test_user(**kwargs)
    else:
        raise ValueError(f"Unknown data type: {data_type}")


def MockFactory(mock_type: str, **kwargs):
    """Generic mock factory for testing"""
    from unittest.mock import Mock

    if mock_type == "user":
        mock_user = Mock()
        mock_user.id = kwargs.get("id", 1)
        mock_user.username = kwargs.get("username", "testuser")
        mock_user.email = kwargs.get("email", "test@example.com")
        return mock_user
    else:
        return Mock()


__all__ = [
    "UserFactory",
    "TeamFactory",
    "LeagueFactory",
    "MatchFactory",
    "OddsFactory",
    "PredictionFactory",
    "DataFactory",
    "MockFactory",
]


# 简单的 LeagueFactory 类用于测试
class LeagueFactory:
    @staticmethod
    def create():
        return {"id": 1, "name": "Test League", "country": "Test Country"}


class MatchFactory:
    @staticmethod
    def create():
        return {
            "id": 1,
            "home_team": "Team A",
            "away_team": "Team B",
            "date": "2024-01-01",
            "league": "Test League",
        }


class OddsFactory:
    @staticmethod
    def create():
        return {
            "id": 1,
            "home_win": 2.50,
            "draw": 3.20,
            "away_win": 2.80,
            "source": "Test Bookmaker",
        }


class PredictionFactory:
    @staticmethod
    def create():
        return {
            "id": 1,
            "match_id": 1,
            "predicted outcome": "home_win",
            "confidence": 0.75,
            "model_version": "v1.0",
            "created_at": "2024-01-01T00:00:00Z",
        }
