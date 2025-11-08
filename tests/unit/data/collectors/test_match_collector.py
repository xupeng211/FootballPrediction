"""
比赛数据收集器测试
Match Data Collector Tests
"""

from unittest.mock import MagicMock, patch

import pytest

from src.collectors.match_collector import MatchCollector


class TestMatchCollector:
    """比赛数据收集器测试"""

    @pytest.fixture
    def collector(self):
        """创建比赛数据收集器实例"""
        return MatchCollector(api_key="test_key")

    @pytest.fixture
    def sample_match_data(self):
        """示例比赛数据"""
        return [
            {
                "id": 1,
                "home_team": "Team A",
                "away_team": "Team B",
                "home_score": 2,
                "away_score": 1,
                "match_date": "2025-11-08T15:00:00Z",
                "status": "completed",
                "league": "Premier League",
            },
            {
                "id": 2,
                "home_team": "Team C",
                "away_team": "Team D",
                "home_score": 0,
                "away_score": 0,
                "match_date": "2025-11-08T16:00:00Z",
                "status": "scheduled",
                "league": "Premier League",
            },
        ]

    def test_collector_initialization(self, collector):
        """测试收集器初始化"""
        assert collector is not None
        assert hasattr(collector, "collect_matches")
        assert hasattr(collector, "collect_teams")
        assert hasattr(collector, "collect_leagues")
        assert hasattr(collector, "normalize_match_data")

    @pytest.mark.asyncio
    async def test_collect_matches_method(self, collector):
        """测试collect_matches方法"""
        with patch.object(collector, "_make_request") as mock_request:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {"matches": []}
            mock_request.return_value = mock_result

            result = await collector.collect_matches()

            assert result is not None
            assert hasattr(result, "success")

    def test_normalize_match_data(self, collector):
        """测试比赛数据标准化"""
        raw_match = {
            "id": 123456,
            "utcDate": "2025-11-08T15:00:00Z",
            "status": "FINISHED",
            "matchday": 10,
            "stage": "REGULAR_SEASON",
            "group": None,
            "lastUpdated": "2025-11-08T16:30:00Z",
            "homeTeam": {"id": 66, "name": "Manchester United FC"},
            "awayTeam": {"id": 64, "name": "Liverpool FC"},
            "score": {
                "winner": "HOME_TEAM",
                "duration": "REGULAR",
                "fullTime": {"homeTeam": 2, "awayTeam": 1},
                "halfTime": {"homeTeam": 1, "awayTeam": 0},
            },
            "referees": [],
        }

        normalized = collector.normalize_match_data(raw_match)

        assert isinstance(normalized, dict)
        assert "id" in normalized
        assert "home_team" in normalized
        assert "away_team" in normalized
        assert "status" in normalized

    @pytest.mark.asyncio
    async def test_collect_upcoming_matches(self, collector):
        """测试收集即将到来的比赛"""
        with patch.object(collector, "_make_request") as mock_request:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {"matches": []}
            mock_request.return_value = mock_result

            result = await collector.collect_upcoming_matches()

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_collect_recent_matches(self, collector):
        """测试收集最近的比赛"""
        with patch.object(collector, "_make_request") as mock_request:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {"matches": []}
            mock_request.return_value = mock_result

            result = await collector.collect_recent_matches()

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_collect_teams(self, collector):
        """测试收集队伍数据"""
        with patch.object(collector, "_make_request") as mock_request:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {"teams": []}
            mock_request.return_value = mock_result

            result = await collector.collect_teams()

            assert result is not None
            assert hasattr(result, "success")

    @pytest.mark.asyncio
    async def test_collect_leagues(self, collector):
        """测试收集联赛数据"""
        with patch.object(collector, "_make_request") as mock_request:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {"competitions": []}
            mock_request.return_value = mock_result

            result = await collector.collect_leagues()

            assert result is not None
            assert hasattr(result, "success")
