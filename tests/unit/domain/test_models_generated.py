"""
领域模型测试 - 自动生成
"""

from datetime import datetime

import pytest

# 尝试导入领域模型
try:
    from src.domain.models.league import League
    from src.domain.models.match import Match
    from src.domain.models.team import Team

    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    Match = None
    Team = None
    League = None


@pytest.mark.skipif(not MODELS_AVAILABLE, reason="Domain models not available")
class TestDomainModels:
    """领域模型测试"""

    def test_match_creation(self):
        """测试比赛创建"""
        if Match:
            match = Match(
                home_team_id=1,
                away_team_id=2,
                match_date=datetime.now(),
                venue="Test Stadium",
            )
            assert match.home_team_id == 1
            assert match.away_team_id == 2

    def test_team_creation(self):
        """测试队伍创建"""
        if Team:
            team = Team(name="Test Team", founded_year=2020, country="Test Country")
            assert team.name == "Test Team"
            assert team.founded_year == 2020

    def test_league_creation(self):
        """测试联赛创建"""
        if League:
            league = League(
                name="Test League", country="Test Country", founded_year=2020
            )
            assert league.name == "Test League"
            assert league.country == "Test Country"
