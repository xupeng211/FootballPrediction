"""足球数据清洗器单元测试。"""

from unittest.mock import AsyncMock, patch

import pytest

from src.data.processing.football_data_cleaner import FootballDataCleaner


class TestFootballDataCleaner:
    @pytest.fixture
    def data_cleaner(self):
        with patch("src.data.processing.football_data_cleaner.DatabaseManager"):
            return FootballDataCleaner()

    def test_data_cleaner_initialization(self, data_cleaner):
    assert data_cleaner is not None
    assert hasattr(data_cleaner, "logger")

    @pytest.mark.asyncio
    async def test_clean_match_data_transforms_payload(self, data_cleaner):
        raw_data = {
            "id": 555,
            "homeTeam": {"id": "H1", "name": "Home Club"},
            "awayTeam": {"id": "A1", "name": "Away Club"},
            "utcDate": "2025-01-02T15:00:00Z",
            "competition": {"id": "10", "name": "Premier League"},
            "status": "SCHEDULED",
            "score": {
                "fullTime": {"home": 2, "away": "1"},
                "halfTime": {"home": 1, "away": 1},
            },
            "season": {"id": "2024"},
            "matchday": 16,
            "venue": "  Old Trafford  ",
            "referees": [{"role": "REFEREE", "name": "  Mike  Dean  "}],
        }

        with patch.object(
            data_cleaner,
            "_map_team_id",
            new=AsyncMock(side_effect=[101, 202]),
        ), patch.object(
            data_cleaner, "_map_league_id", new=AsyncMock(return_value=301)
        ):
            cleaned = await data_cleaner.clean_match_data(raw_data)

    assert cleaned is not None
    assert cleaned["external_match_id"] == "555"
    assert cleaned["match_status"] == "scheduled"
    assert cleaned["home_team_id"] == 101
    assert cleaned["away_team_id"] == 202
    assert cleaned["league_id"] == 301
    assert cleaned["home_score"] == 2
    assert cleaned["away_score"] == 1
    assert cleaned["home_ht_score"] == 1
    assert cleaned["away_ht_score"] == 1
    assert cleaned["matchday"] == 16
    assert cleaned["season"] == "2024"
    assert cleaned["match_time"] == "2025-01-02T15:00:00+00:00"

        # 确认可读字段被清理
    assert cleaned["venue"] == "Old Trafford"
    assert cleaned["referee"] == "Mike Dean"
    assert cleaned["data_source"] == "cleaned"
    assert cleaned["cleaned_at"] is not None

    @pytest.mark.asyncio
    async def test_clean_match_data_invalid_payload_returns_none(self, data_cleaner):
        result = await data_cleaner.clean_match_data({"homeTeam": {}})
    assert result is None

    @pytest.mark.asyncio
    async def test_clean_odds_data_filters_invalid_entries(self, data_cleaner):
        raw_odds = [
            {
                "match_id": 555,
                "bookmaker": "ACME BOOKS",
                "market_type": "h2h",
                "outcomes": [
                    {"name": "1", "price": 1.5},
                    {"name": "X", "price": 3.2},
                    {"name": "2", "price": 5.0},
                    {"name": "invalid", "price": 0.5},
                ],
                "last_update": "2025-01-02T16:00:00Z",
            }
        ]

        cleaned = await data_cleaner.clean_odds_data(raw_odds)

    assert len(cleaned) == 1
        entry = cleaned[0]
    assert entry["bookmaker"] == "acme_books"
    assert entry["market_type"] == "1x2"
    assert {o["name"] for o in entry["outcomes"]} == {"home", "draw", "away"}
    assert all(o["price"] >= 1.01 for o in entry["outcomes"])
    assert abs(sum(entry["implied_probabilities"].values()) - 1.0) < 0.01
    assert entry["cleaned_at"] is not None
