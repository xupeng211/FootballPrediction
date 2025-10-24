from unittest.mock import AsyncMock, MagicMock
"""
测试拆分后的数据API
Test Split Data API
"""

import pytest


# 测试导入是否正常
@pytest.mark.unit
@pytest.mark.api
@pytest.mark.external_api

def test_import_data_api():
    """测试能否正常导入data_api模块"""
    from src.api import data_api

    # 验证导出符号
    assert hasattr(data_api, "router")
    assert hasattr(data_api, "TeamInfo")
    assert hasattr(data_api, "LeagueInfo")
    assert hasattr(data_api, "MatchInfo")
    assert hasattr(data_api, "OddsInfo")


def test_import_data_module():
    """测试能否正常导入data模块"""
    from src.api.data import router

    # 验证路由器存在
    assert router is not None
    assert hasattr(router, "routes")


def test_import_models():
    """测试能否正常导入模型"""
    from src.api.data.models.common import TeamInfo, LeagueInfo, MatchInfo, OddsInfo

    # 验证模型类
    assert TeamInfo is not None
    assert LeagueInfo is not None
    assert MatchInfo is not None
    assert OddsInfo is not None


def test_import_match_routes():
    """测试能否正常导入比赛路由"""
    from src.api.data.matches.routes import router as match_router

    assert match_router is not None
    assert hasattr(match_router, "routes")


def test_import_team_routes():
    """测试能否正常导入球队路由"""
    from src.api.data.teams.routes import router as team_router

    assert team_router is not None
    assert hasattr(team_router, "routes")


def test_import_league_routes():
    """测试能否正常导入联赛路由"""
    from src.api.data.leagues.routes import router as league_router

    assert league_router is not None
    assert hasattr(league_router, "routes")


def test_import_odds_routes():
    """测试能否正常导入赔率路由"""
    from src.api.data.odds.routes import router as odds_router

    assert odds_router is not None
    assert hasattr(odds_router, "routes")


def test_import_statistics_routes():
    """测试能否正常导入统计路由"""
    from src.api.data.statistics.routes import router as stats_router

    assert stats_router is not None
    assert hasattr(stats_router, "routes")


# 测试模型创建
def test_create_team_info():
    """测试创建TeamInfo模型"""
    from src.api.data.models.common import TeamInfo

    team = TeamInfo(
        id=1,
        name="Test Team",
        country="Test Country",
        founded_year=2000,
        stadium="Test Stadium",
        logo_url="http://test.com/logo.png",
        is_active=True,
    )

    assert team.id == 1
    assert team.name == "Test Team"
    assert team.country == "Test Country"


def test_create_league_info():
    """测试创建LeagueInfo模型"""
    from datetime import datetime
    from src.api.data.models.common import LeagueInfo

    league = LeagueInfo(
        id=1,
        name="Test League",
        country="Test Country",
        season="2023-2024",
        start_date=datetime(2023, 8, 1),
        end_date=datetime(2024, 5, 31),
        is_active=True,
    )

    assert league.id == 1
    assert league.name == "Test League"
    assert league.season == "2023-2024"


def test_create_match_info():
    """测试创建MatchInfo模型"""
    from datetime import datetime
    from src.api.data.models.common import MatchInfo, TeamInfo, LeagueInfo

    home_team = TeamInfo(
        id=1,
        name="Home Team",
        country="Country",
        founded_year=2000,
        stadium="Home Stadium",
        logo_url="http://test.com/home.png",
        is_active=True,
    )
    away_team = TeamInfo(
        id=2,
        name="Away Team",
        country="Country",
        founded_year=2001,
        stadium="Away Stadium",
        logo_url="http://test.com/away.png",
        is_active=True,
    )
    league = LeagueInfo(
        id=1,
        name="League",
        country="Country",
        season="2023",
        start_date=datetime(2023, 8, 1),
        end_date=datetime(2024, 5, 31),
        is_active=True,
    )

    match = MatchInfo(
        id=1,
        home_team=home_team,
        away_team=away_team,
        league=league,
        match_time=datetime(2024, 1, 1, 15, 0),
        match_status="SCHEDULED",
        venue="Stadium",
        home_score=None,
        away_score=None,
        home_half_score=None,
        away_half_score=None,
    )

    assert match.id == 1
    assert match.home_team.name == "Home Team"
    assert match.away_team.name == "Away Team"
    assert match.match_status == "SCHEDULED"
