"""
联赛数据收集器测试
League Data Collector Tests
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.collectors.league_collector import LeagueCollector


class TestLeagueCollector:
    """联赛数据收集器测试"""

    @pytest.fixture
    def collector(self):
        """创建联赛数据收集器实例"""
        import os

        # 设置测试API key环境变量
        os.environ["FOOTBALL_DATA_API_KEY"] = "test_key"
        return LeagueCollector()

    @pytest.fixture
    def sample_league_data(self):
        """示例联赛数据"""
        return [
            {
                "id": 1,
                "name": "Premier League",
                "short_name": "EPL",
                "country": "England",
                "tier": 1,
                "total_teams": 20,
                "matches_per_team": 38,
                "season": "2024-25",
                "start_date": "2024-08-16T00:00:00Z",
                "end_date": "2025-05-25T00:00:00Z",
                "current_champion": "Manchester City",
                "most_titles": "Manchester United",
                "website": "https://www.premierleague.com",
                "logo_url": "https://example.com/logos/epl.png",
                "created_at": "2025-11-08T15:00:00Z",
            }
        ]

    def test_collector_initialization(self, collector):
        """测试收集器初始化"""
        assert collector is not None
        assert hasattr(collector, "collect_data")
        assert hasattr(collector, "collect_league_details")
        assert hasattr(collector, "normalize_league_data")
        assert hasattr(collector, "search_competitions")

    @pytest.mark.asyncio
    async def test_collect_data_method(self, collector):
        """测试collect_data方法"""
        with patch.object(collector, "collect_leagues") as mock_collect_leagues:
            mock_collect_leagues.return_value = AsyncMock(
                return_value=MagicMock(
                    success=True, data={"competitions": [], "count": 0}
                )
            )

            result = await collector.collect_data()

            assert isinstance(result, dict)
            assert "timestamp" in result
            assert "leagues" in result

    def test_normalize_league_data(self, collector):
        """测试联赛数据标准化"""
        raw_competition = {
            "id": 39,
            "name": "Premier League",
            "code": "PL",
            "type": "LEAGUE",
            "emblem": "https://example.com/pl.png",
            "currentSeason": {
                "id": 857,
                "startDate": "2024-08-16",
                "endDate": "2025-05-25",
                "currentMatchday": 10,
                "winner": None,
            },
            "numberOfAvailableSeasons": 30,
            "lastUpdated": "2025-11-08T15:00:00Z",
        }

        normalized = collector.normalize_league_data(raw_competition)

        assert isinstance(normalized, dict)
        # 根据实际实现，ID可能存储为external_id
        assert "id" in normalized or "external_id" in normalized
        assert "name" in normalized
        assert "code" in normalized

    @pytest.mark.asyncio
    async def test_search_competitions(self, collector):
        """测试比赛搜索"""
        with patch.object(collector, "collect_leagues") as mock_collect_leagues:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {"competitions": []}
            mock_collect_leagues.return_value = mock_result

            result = await collector.search_competitions("premier")

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_collect_league_details(self, collector):
        """测试收集联赛详情"""
        competition_code = "PL"

        with (
            patch.object(collector, "collect_leagues") as mock_collect_leagues,
            patch.object(collector, "fetch_competitions") as mock_fetch,
        ):
            mock_fetch.return_value = []
            mock_collect_leagues.return_value = MagicMock(
                success=True,
                data={
                    "competitions": [{"id": 39, "name": "Premier League", "code": "PL"}]
                },
            )

            result = await collector.collect_league_details(competition_code)

            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_available_seasons(self, collector):
        """测试获取可用赛季"""
        competition_code = "PL"

        with patch.object(collector, "collect_leagues") as mock_collect_leagues:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {"competitions": []}
            mock_collect_leagues.return_value = mock_result

            result = await collector.get_available_seasons(competition_code)

            assert isinstance(result, list)
