import os
"""
数据API端点测试 / Tests for Data API Endpoints

测试覆盖：
- 比赛数据接口
- 球队统计接口
- 联赛数据接口
- 特征数据接口
- 数据质量监控
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.data import router, format_match_response, format_team_response, format_league_response


class TestDataAPI:
    """数据API测试类"""

    @pytest.fixture
    def mock_match(self):
        """模拟比赛数据"""
        match = MagicMock()
        match.id = 12345
        match.home_team_id = 10
        match.away_team_id = 20
        match.league_id = 1
        match.season = os.getenv("TEST_DATA_COMPREHENSIVE_SEASON_30")
        match.match_time = datetime.now() + timedelta(days=1)
        match.match_status = os.getenv("TEST_DATA_COMPREHENSIVE_MATCH_STATUS_31")
        match.home_score = None
        match.away_score = None
        return match

    @pytest.fixture
    def mock_team(self):
        """模拟球队数据"""
        team = MagicMock()
        team.id = 10
        team.team_name = os.getenv("TEST_DATA_COMPREHENSIVE_TEAM_NAME_39")
        team.name = os.getenv("TEST_DATA_COMPREHENSIVE_NAME_41")
        team.short_name = "MUFC"
        team.founded_year = 1878
        team.country = os.getenv("TEST_DATA_COMPREHENSIVE_COUNTRY_43")
        team.league_id = 1
        team.stadium = os.getenv("TEST_DATA_COMPREHENSIVE_STADIUM_44")
        team.website = "https://www.manutd.com"
        return team

    @pytest.fixture
    def mock_league(self):
        """模拟联赛数据"""
        league = MagicMock()
        league.id = 1
        league.league_name = os.getenv("TEST_DATA_COMPREHENSIVE_LEAGUE_NAME_49")
        league.name = os.getenv("TEST_DATA_COMPREHENSIVE_NAME_50")
        league.country = os.getenv("TEST_DATA_COMPREHENSIVE_COUNTRY_43")
        league.league_code = "EPL"
        league.level = 1
        league.is_active = True
        return league

    def test_format_match_response(self):
        """测试比赛数据格式化"""
        # 测试ORM对象
        match = MagicMock()
        match.id = 123
        match.home_team_id = 10
        match.away_team_id = 20
        match.league_id = 1
        match.season = os.getenv("TEST_DATA_COMPREHENSIVE_SEASON_30")
        match.match_time = datetime.now()
        match.match_status = os.getenv("TEST_DATA_COMPREHENSIVE_MATCH_STATUS_31")
        match.home_score = 0
        match.away_score = 0

        response = format_match_response(match)

        assert response["id"] == 123
        assert response["home_team_id"] == 10
        assert response["away_team_id"] == 20
        assert response["season"] == "2024-25"
        assert response["match_status"] == "scheduled"

    def test_format_match_response_dict(self):
        """测试字典格式的比赛数据格式化"""
        match_dict = {
            "id": 456,
            "home_team_id": 30,
            "away_team_id": 40,
            "match_time": datetime.now().isoformat(),
            "match_status": "finished",
        }

        response = format_match_response(match_dict)

        assert response["id"] == 456
        assert response["home_team_id"] == 30
        assert response["away_team_id"] == 40
        assert response["match_status"] == "finished"

    def test_format_team_response(self):
        """测试球队数据格式化"""
        team = MagicMock()
        team.id = 10
        team.team_name = os.getenv("TEST_DATA_COMPREHENSIVE_TEAM_NAME_95")
        team.name = os.getenv("TEST_DATA_COMPREHENSIVE_NAME_97")
        team.short_name = "TT"
        team.founded_year = 1900
        team.country = os.getenv("TEST_DATA_COMPREHENSIVE_COUNTRY_100")
        team.stadium = os.getenv("TEST_DATA_COMPREHENSIVE_STADIUM_101")

        response = format_team_response(team)

        assert response["id"] == 10
        assert response["name"] == "Test Team FC"
        assert response["team_name"] == "Test Team"
        assert response["short_name"] == "TT"
        assert response["founded_year"] == 1900

    def test_format_team_response_dict(self):
        """测试字典格式的球队数据格式化"""
        team_dict = {
            "id": 20,
            "team_name": "Dict Team",
            "team_code": "DT",
            "founded": 1950,
        }

        response = format_team_response(team_dict)

        assert response["id"] == 20
        assert response["name"] == "Dict Team"
        assert response["team_name"] == "Dict Team"
        assert response["short_name"] == "DT"
        assert response["founded_year"] == 1950

    def test_format_league_response(self):
        """测试联赛数据格式化"""
        league = MagicMock()
        league.id = 1
        league.league_name = os.getenv("TEST_DATA_COMPREHENSIVE_LEAGUE_NAME_127")
        league.country = os.getenv("TEST_DATA_COMPREHENSIVE_COUNTRY_128")
        league.league_code = "TL"
        league.level = 1
        league.is_active = True

        response = format_league_response(league)

        assert response["id"] == 1
        assert response["name"] == "Test League"
        assert response["country"] == "Test Nation"
        assert response["code"] == "TL"
        assert response["level"] == 1
        assert response["is_active"] is True

    def test_format_league_response_dict(self):
        """测试字典格式的联赛数据格式化"""
        league_dict = {
            "id": 2,
            "name": "Dict League",
            "country": "Dict Land",
            "league_code": "DL",
            "is_active": False,
        }

        response = format_league_response(league_dict)

        assert response["id"] == 2
        assert response["name"] == "Dict League"
        assert response["country"] == "Dict Land"
        assert response["code"] == "DL"
        assert response["is_active"] is False

    @pytest.mark.asyncio
    @patch('src.api.data.select')
    async def test_get_matches(self, mock_select):
        """测试获取比赛列表"""
        # 设置模拟
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_match = self.mock_match()
        mock_result.scalars.return_value.all.return_value = [mock_match]
        mock_session.execute.return_value = mock_result

        # 执行测试
        from src.api.data import get_matches
        response = await get_matches(
            league_id=1,
            season = os.getenv("TEST_DATA_COMPREHENSIVE_SEASON_174"),
            limit=10,
            offset=0,
            session=mock_session
        )

        # 验证结果
        assert response["success"] is True
        assert "matches" in response["data"]
        assert len(response["data"]["matches"]) == 1

    @pytest.mark.asyncio
    @patch('src.api.data.select')
    async def test_get_match_by_id(self, mock_select):
        """测试根据ID获取比赛"""
        # 设置模拟
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_match = self.mock_match()
        mock_result.scalar_one_or_none.return_value = mock_match
        mock_session.execute.return_value = mock_result

        # 执行测试
        from src.api.data import get_match_by_id
        response = await get_match_by_id(12345, mock_session)

        # 验证结果
        assert response["success"] is True
        assert response["data"]["id"] == 12345

    @pytest.mark.asyncio
    @patch('src.api.data.select')
    async def test_get_match_by_id_not_found(self, mock_select):
        """测试获取不存在的比赛"""
        from src.api.data import get_match_by_id
        from fastapi import HTTPException

        # 设置模拟
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # 执行测试并验证异常
        with pytest.raises(HTTPException) as exc_info:
            await get_match_by_id(99999, mock_session)

        assert exc_info.value.status_code == 404
        assert "99999" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('src.api.data.select')
    async def test_get_teams(self, mock_select):
        """测试获取球队列表"""
        # 设置模拟
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_team = self.mock_team()
        mock_result.scalars.return_value.all.return_value = [mock_team]
        mock_session.execute.return_value = mock_result

        # 执行测试
        from src.api.data import get_teams
        response = await get_teams(
            league_id=1,
            limit=20,
            offset=0,
            session=mock_session
        )

        # 验证结果
        assert response["success"] is True
        assert "teams" in response["data"]
        assert len(response["data"]["teams"]) == 1

    @pytest.mark.asyncio
    @patch('src.api.data.select')
    async def test_get_team_by_id(self, mock_select):
        """测试根据ID获取球队"""
        # 设置模拟
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_team = self.mock_team()
        mock_result.scalar_one_or_none.return_value = mock_team
        mock_session.execute.return_value = mock_result

        # 执行测试
        from src.api.data import get_team_by_id
        response = await get_team_by_id(10, mock_session)

        # 验证结果
        assert response["success"] is True
        assert response["data"]["id"] == 10
        assert response["data"]["name"] == "Manchester United FC"

    @pytest.mark.asyncio
    @patch('src.api.data.select')
    async def test_get_leagues(self, mock_select):
        """测试获取联赛列表"""
        # 设置模拟
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_league = self.mock_league()
        mock_result.scalars.return_value.all.return_value = [mock_league]
        mock_session.execute.return_value = mock_result

        # 执行测试
        from src.api.data import get_leagues
        response = await get_leagues(
            country = os.getenv("TEST_DATA_COMPREHENSIVE_COUNTRY_283"),
            is_active=True,
            session=mock_session
        )

        # 验证结果
        assert response["success"] is True
        assert "leagues" in response["data"]
        assert len(response["data"]["leagues"]) == 1

    @pytest.mark.asyncio
    @patch('src.api.data.DataQualityMonitor')
    async def test_get_data_quality_report(self, mock_monitor_class):
        """测试获取数据质量报告"""
        # 设置模拟
        mock_monitor = MagicMock()
        mock_monitor.get_overall_quality_score.return_value = 0.95
        mock_monitor.get_quality_issues.return_value = []
        mock_monitor_class.return_value = mock_monitor
        mock_session = AsyncMock()

        # 执行测试
        from src.api.data import get_data_quality_report
        response = await get_data_quality_report(mock_session)

        # 验证结果
        assert response["success"] is True
        assert "quality_score" in response["data"]
        assert response["data"]["quality_score"] == 0.95

    @pytest.mark.asyncio
    @patch('src.api.data.select')
    async def test_get_match_features(self, mock_select):
        """测试获取比赛特征数据"""
        # 设置模拟
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_feature = MagicMock()
        mock_feature.feature_name = os.getenv("TEST_DATA_COMPREHENSIVE_FEATURE_NAME_319")
        mock_feature.feature_value = 0.65
        mock_result.scalars.return_value.all.return_value = [mock_feature]
        mock_session.execute.return_value = mock_result

        # 执行测试
        from src.api.data import get_match_features
        response = await get_match_features(12345, mock_session)

        # 验证结果
        assert response["success"] is True
        assert "features" in response["data"]
        assert len(response["data"]["features"]) == 1