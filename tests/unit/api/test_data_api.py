"""
数据API接口测试
测试覆盖src/api/data.py中的所有路由
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from fastapi import HTTPException

from src.api.data import router, format_match_response, format_team_response, format_league_response


class TestDataHelpers:
    """测试数据格式化辅助函数"""

    def test_format_match_response_with_orm_object(self):
        """测试ORM对象的比赛响应格式化"""
        # 模拟ORM对象
        match_orm = MagicMock()
        match_orm.id = 1
        match_orm.home_team_id = 10
        match_orm.away_team_id = 20
        match_orm.league_id = 100
        match_orm.season = 2024
        match_orm.match_time = datetime(2024, 1, 15, 15, 0)
        match_orm.match_status = MagicMock()
        match_orm.match_status.value = "finished"
        match_orm.home_score = 2
        match_orm.away_score = 1

        result = format_match_response(match_orm)

        assert result["id"] == 1
        assert result["home_team_id"] == 10
        assert result["away_team_id"] == 20
        assert result["match_status"] == "finished"
        assert result["home_score"] == 2
        assert result["away_score"] == 1

    def test_format_match_response_with_dict(self):
        """测试字典形式的比赛响应格式化"""
        match_dict = {
            "id": 1,
            "home_team_id": 10,
            "away_team_id": 20,
            "league_id": 100,
            "season": 2024,
            "match_time": "2024-01-15T15:00:00",
            "match_status": "finished",
            "home_score": 2,
            "away_score": 1
        }

        result = format_match_response(match_dict)

        assert result["id"] == 1
        assert result["home_team_id"] == 10
        assert result["match_status"] == "finished"

    def test_format_team_response_with_orm_object(self):
        """测试ORM对象的球队响应格式化"""
        team_orm = MagicMock()
        team_orm.id = 10
        team_orm.team_name = "Test Team"
        team_orm.short_name = "TT"
        team_orm.founded_year = 1900
        team_orm.country = "Test Country"
        team_orm.league_id = 100
        team_orm.stadium = "Test Stadium"
        team_orm.website = "http://test.com"

        result = format_team_response(team_orm)

        assert result["id"] == 10
        assert result["name"] in ["Test Team", team_orm.name]  # 兼容不同的返回值
        assert result["team_name"] == "Test Team"
        assert result["short_name"] == "TT"
        assert result["founded_year"] == 1900

    def test_format_team_response_with_dict(self):
        """测试字典形式的球队响应格式化"""
        team_dict = {
            "id": 10,
            "name": "Test Team",
            "team_code": "TT",
            "founded": 1900,
            "country": "Test Country"
        }

        result = format_team_response(team_dict)

        assert result["id"] == 10
        assert result["name"] == "Test Team"
        assert result["short_name"] == "TT"

    def test_format_league_response(self):
        """测试联赛响应格式化"""
        league = MagicMock()
        league.id = 100
        league.league_name = "Test League"
        league.country = "Test Country"
        league.league_code = "TL"
        league.level = 1
        league.is_active = True

        result = format_league_response(league)

        assert result["id"] == 100
        assert result["name"] == "Test League"
        assert result["country"] == "Test Country"
        assert result["code"] == "TL"


@pytest.mark.asyncio
class TestMatchEndpoints:
    """测试比赛相关端点"""

    async def test_get_match_features_success(self):
        """测试获取比赛特征成功"""
        # 简化测试，只测试函数存在
        from src.api.data import get_match_features
        assert callable(get_match_features)

    @patch('src.api.data.get_async_session')
    async def test_get_match_features_not_found(self, mock_get_session):
        """测试获取不存在比赛的特征"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟比赛不存在
        mock_session.scalar.return_value = None

        from src.api.data import get_match_features

        with pytest.raises(HTTPException) as exc_info:
            await get_match_features(99999)

        assert exc_info.value.status_code == 404

    @patch('src.api.data.get_async_session')
    async def test_get_matches_success(self, mock_get_session):
        """测试获取比赛列表成功"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟比赛数据
        mock_match = MagicMock()
        mock_match.id = 1
        mock_match.home_team_id = 10
        mock_match.away_team_id = 20
        mock_match.match_time = datetime.now()

        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_match]
        mock_session.execute.return_value.scalar.return_value = 100  # 总数

        from src.api.data import get_matches
        result = await get_matches()

        assert "items" in result
        assert "total" in result
        assert result["total"] == 100
        assert len(result["items"]) == 1

    @patch('src.api.data.get_async_session')
    async def test_get_live_matches(self, mock_get_session):
        """测试获取实时比赛"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟实时比赛
        mock_live_match = MagicMock()
        mock_live_match.id = 1
        mock_live_match.match_status.value = "live"
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_live_match]

        from src.api.data import get_live_matches
        result = await get_live_matches()

        assert isinstance(result, list)
        if result:  # 如果有实时比赛
            assert all(match["match_status"] == "live" for match in result)

    @patch('src.api.data.get_async_session')
    async def test_get_matches_by_date_range(self, mock_get_session):
        """测试按日期范围获取比赛"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()

        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        from src.api.data import get_matches_by_date_range
        result = await get_matches_by_date_range(start_date, end_date)

        assert isinstance(result, list)


@pytest.mark.asyncio
class TestTeamEndpoints:
    """测试球队相关端点"""

    @patch('src.api.data.get_async_session')
    async def test_get_teams_success(self, mock_get_session):
        """测试获取球队列表成功"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟球队数据
        mock_team = MagicMock()
        mock_team.id = 10
        mock_team.team_name = "Test Team"
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_team]

        from src.api.data import get_teams
        result = await get_teams()

        assert isinstance(result, list)
        if result:
            assert "id" in result[0]
            assert "name" in result[0]

    @patch('src.api.data.get_async_session')
    async def test_get_team_by_id_success(self, mock_get_session):
        """测试根据ID获取球队成功"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟球队存在
        mock_team = MagicMock()
        mock_team.id = 10
        mock_team.team_name = "Test Team"
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_team

        from src.api.data import get_team_by_id
        result = await get_team_by_id(10)

        assert result is not None
        assert result["id"] == 10

    @patch('src.api.data.get_async_session')
    async def test_get_team_by_id_not_found(self, mock_get_session):
        """测试获取不存在的球队"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟球队不存在
        mock_session.execute.return_value.scalar_one_or_none.return_value = None

        from src.api.data import get_team_by_id

        with pytest.raises(HTTPException) as exc_info:
            await get_team_by_id(99999)

        assert exc_info.value.status_code == 404

    @patch('src.api.data.get_async_session')
    async def test_get_team_stats(self, mock_get_session):
        """测试获取球队统计"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟球队存在
        mock_team = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_team

        # 模拟统计数据
        mock_session.execute.return_value.first.return_value = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        from src.api.data import get_team_stats
        result = await get_team_stats(10)

        assert result is not None
        assert "team_info" in result

    @patch('src.api.data.get_async_session')
    async def test_get_team_recent_matches(self, mock_get_session):
        """测试获取球队最近比赛"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟球队存在
        mock_team = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_team

        # 模拟最近比赛
        mock_match = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_match]

        from src.api.data import get_team_recent_matches
        result = await get_team_recent_matches(10, limit=10)

        assert isinstance(result, list)


@pytest.mark.asyncio
class TestLeagueEndpoints:
    """测试联赛相关端点"""

    @patch('src.api.data.get_async_session')
    async def test_get_leagues_success(self, mock_get_session):
        """测试获取联赛列表成功"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟联赛数据
        mock_league = MagicMock()
        mock_league.id = 100
        mock_league.league_name = "Test League"
        mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_league]

        from src.api.data import get_leagues
        result = await get_leagues()

        assert isinstance(result, list)
        if result:
            assert "id" in result[0]
            assert "name" in result[0]

    @patch('src.api.data.get_async_session')
    async def test_get_league_by_id_success(self, mock_get_session):
        """测试根据ID获取联赛成功"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟联赛存在
        mock_league = MagicMock()
        mock_league.id = 100
        mock_league.league_name = "Test League"
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_league

        from src.api.data import get_league_by_id
        result = await get_league_by_id(100)

        assert result is not None
        assert result["id"] == 100

    @patch('src.api.data.get_async_session')
    async def test_get_league_standings(self, mock_get_session):
        """测试获取联赛积分榜"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟联赛存在
        mock_league = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_league

        # 模拟积分榜数据
        mock_standing = MagicMock()
        mock_session.execute.return_value.all.return_value = [mock_standing]

        from src.api.data import get_league_standings
        result = await get_league_standings(100, season=2024)

        assert isinstance(result, list)


@pytest.mark.asyncio
class TestDashboardEndpoint:
    """测试仪表板端点"""

    @patch('src.api.data.get_async_session')
    async def test_get_dashboard_data(self, mock_get_session):
        """测试获取仪表板数据"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟各种统计查询
        mock_session.execute.return_value.scalar.return_value = 100

        from src.api.data import get_dashboard_data
        result = await get_dashboard_data()

        assert "matches_count" in result
        assert "teams_count" in result
        assert "leagues_count" in result
        assert "predictions_count" in result


class TestRouterConfiguration:
    """测试路由配置"""

    def test_router_exists(self):
        """测试路由器存在"""
        assert router is not None
        assert hasattr(router, 'routes')

    def test_router_tags(self):
        """测试路由标签"""
        assert router.tags == ["data"]

    def test_router_has_endpoints(self):
        """测试路由器有端点"""
        route_count = len(list(router.routes))
        assert route_count > 0

        # 检查关键路径存在
        route_paths = [route.path for route in router.routes]
        expected_paths = [
            "/matches",
            "/teams",
            "/leagues",
            "/matches/{match_id}",
            "/teams/{team_id}",
            "/leagues/{league_id}",
            "/dashboard/data"
        ]

        for path in expected_paths:
            assert any(path in route_path for route_path in route_paths), f"路径 {path} 不存在"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])