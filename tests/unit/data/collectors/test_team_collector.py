"""
队伍数据收集器测试
Team Data Collector Tests
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.collectors.team_collector import TeamCollector


class TestTeamCollector:
    """队伍数据收集器测试"""

    @pytest.fixture
    def collector(self):
        """创建队伍数据收集器实例"""
        import os

        # 设置测试API key环境变量
        os.environ["FOOTBALL_DATA_API_KEY"] = "test_key"
        return TeamCollector()

    @pytest.fixture
    def sample_team_data(self):
        """示例队伍数据"""
        return [
            {
                "id": 66,
                "name": "Manchester United FC",
                "shortName": "Man United",
                "tla": "MUN",
                "crest": "https://example.com/crest.png",
                "address": "Sir Matt Busby Way",
                "website": "https://www.manutd.com",
                "founded": 1878,
                "clubColors": "Red / White",
                "venue": "Old Trafford",
            }
        ]

    def test_collector_initialization(self, collector):
        """测试收集器初始化"""
        assert collector is not None
        assert hasattr(collector, "collect_data")
        assert hasattr(collector, "collect_competition_teams")
        assert hasattr(collector, "normalize_team_data")
        assert hasattr(collector, "search_teams")

    @pytest.mark.asyncio
    async def test_collect_data_method(self, collector):
        """测试collect_data方法"""
        with patch.object(collector, "collect_teams") as mock_collect_teams:
            mock_collect_teams.return_value = AsyncMock(
                return_value=MagicMock(success=True, data={"teams": [], "count": 0})
            )

            result = await collector.collect_data()

            assert isinstance(result, dict)
            assert "timestamp" in result
            assert "teams" in result

    def test_normalize_team_data(self, collector):
        """测试队伍数据标准化"""
        raw_team = {
            "id": 66,
            "name": "Manchester United FC",
            "shortName": "Man United",
            "tla": "MUN",
            "crest": "https://example.com/crest.png",
            "address": "Sir Matt Busby Way",
            "website": "https://www.manutd.com",
            "founded": 1878,
            "clubColors": "Red / White",
            "venue": "Old Trafford",
        }

        normalized = collector.normalize_team_data(raw_team)

        assert isinstance(normalized, dict)
        assert "id" in normalized
        assert "name" in normalized
        assert "founded" in normalized

    @pytest.mark.asyncio
    async def test_search_teams(self, collector):
        """测试队伍搜索"""
        with patch.object(collector, "collect_teams") as mock_collect_teams:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {"teams": []}
            mock_collect_teams.return_value = mock_result

            result = await collector.search_teams("united")

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_collect_competition_teams(self, collector):
        """测试收集联赛队伍"""
        competition_id = 66  # Premier League ID

        with patch.object(collector, "collect_teams") as mock_collect_teams:
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {
                "teams": [
                    {"id": 66, "name": "Manchester United FC"},
                    {"id": 64, "name": "Liverpool FC"},
                ],
                "count": 2,
            }
            mock_collect_teams.return_value = mock_result

            result = await collector.collect_competition_teams(competition_id)

            assert isinstance(result, dict)
            mock_collect_teams.assert_called_once_with(league_id=competition_id)
