"""数据库仓库测试"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from src.database.repositories import MatchRepository, TeamRepository
from src.database.models.match import Match, MatchStatus
from src.database.models.team import Team


class TestMatchRepository:
    """比赛仓库测试"""

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        return Mock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session):
        """创建比赛仓库"""
        return MatchRepository(mock_session)

    def test_get_match_by_id(self, repository, mock_session):
        """测试根据ID获取比赛"""
        # 设置模拟返回
        mock_match = Mock(spec=Match)
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_match
        )

        # 调用方法
        result = repository.get_by_id(1)

        # 验证
        assert result == mock_match
        mock_session.query.assert_called_once_with(Match)

    def test_get_matches_by_league(self, repository, mock_session):
        """测试根据联赛获取比赛"""
        # 设置模拟返回
        mock_matches = [Mock(spec=Match), Mock(spec=Match)]
        mock_session.query.return_value.filter.return_value.all.return_value = (
            mock_matches
        )

        # 调用方法
        result = repository.get_by_league("Premier League")

        # 验证
        assert result == mock_matches

    def test_get_matches_by_date_range(self, repository, mock_session):
        """测试根据日期范围获取比赛"""
        from datetime import date, datetime

        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        # 设置模拟返回
        mock_matches = [Mock(spec=Match)]
        mock_session.query.return_value.filter.return_value.all.return_value = (
            mock_matches
        )

        # 调用方法
        result = repository.get_by_date_range(start_date, end_date)

        # 验证
        assert result == mock_matches

    def test_create_match(self, repository, mock_session):
        """测试创建比赛"""
        match_data = {
            "home_team_id": 1,
            "away_team_id": 2,
            "date": datetime(2024, 1, 1, 15, 0),
            "league": "Premier League",
        }

        # 创建新比赛
        new_match = Match(**match_data)
        mock_session.add.return_value = None
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None

        # 调用方法
        result = repository.create(new_match)

        # 验证
        mock_session.add.assert_called_once_with(new_match)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(new_match)

    def test_update_match_score(self, repository, mock_session):
        """测试更新比赛比分"""
        # 设置模拟
        mock_match = Mock(spec=Match)
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_match
        )

        # 调用方法
        result = repository.update_score(1, 2, 1)

        # 验证
        assert result == mock_match
        mock_match.home_score = 2
        mock_match.away_score = 1
        mock_session.commit.assert_called_once()

    def test_get_live_matches(self, repository, mock_session):
        """测试获取进行中的比赛"""
        # 设置模拟返回
        mock_matches = [Mock(spec=Match), Mock(spec=Match)]
        mock_session.query.return_value.filter.return_value.all.return_value = (
            mock_matches
        )

        # 调用方法
        result = repository.get_live_matches()

        # 验证
        assert result == mock_matches
        mock_session.query.assert_called_once_with(Match)

    def test_delete_match(self, repository, mock_session):
        """测试删除比赛"""
        # 设置模拟
        mock_match = Mock(spec=Match)
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_match
        )

        # 调用方法
        result = repository.delete(1)

        # 验证
        assert result is True
        mock_session.delete.assert_called_once_with(mock_match)
        mock_session.commit.assert_called_once()


class TestTeamRepository:
    """球队仓库测试"""

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        return Mock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session):
        """创建球队仓库"""
        return TeamRepository(mock_session)

    def test_get_team_by_name(self, repository, mock_session):
        """测试根据名称获取球队"""
        # 设置模拟返回
        mock_team = Mock(spec=Team)
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_team
        )

        # 调用方法
        result = repository.get_by_name("Team A")

        # 验证
        assert result == mock_team
        mock_session.query.assert_called_once_with(Team)

    def test_get_teams_by_league(self, repository, mock_session):
        """测试根据联赛获取球队"""
        # 设置模拟返回
        mock_teams = [Mock(spec=Team), Mock(spec=Team)]
        mock_session.query.return_value.filter.return_value.all.return_value = (
            mock_teams
        )

        # 调用方法
        result = repository.get_by_league("Premier League")

        # 验证
        assert result == mock_teams

    def test_get_team_standings(self, repository, mock_session):
        """测试获取球队排名"""
        # 设置模拟返回
        mock_teams = [
            Mock(spec=Team, points=30, goal_diff=20),
            Mock(spec=Team, points=28, goal_diff=15),
            Mock(spec=Team, points=25, goal_diff=10),
        ]
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_teams

        # 调用方法
        result = repository.get_standings("Premier League")

        # 验证
        assert len(result) == 3
        assert result[0].points == 30  # 第一名

    def test_update_team_stats(self, repository, mock_session):
        """测试更新球队统计"""
        # 设置模拟
        mock_team = Mock(spec=Team)
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_team
        )

        stats_data = {"goals_scored": 5, "goals_conceded": 2, "matches_played": 3}

        # 调用方法
        result = repository.update_stats(1, stats_data)

        # 验证
        assert result == mock_team
        mock_team.goals_scored = 5
        mock_team.goals_conceded = 2
        mock_team.matches_played = 3
        mock_session.commit.assert_called_once()

    def test_search_teams(self, repository, mock_session):
        """测试搜索球队"""
        # 设置模拟返回
        mock_teams = [Mock(spec=Team)]
        mock_session.query.return_value.filter.return_value.all.return_value = (
            mock_teams
        )

        # 调用方法
        result = repository.search("United")

        # 验证
        assert result == mock_teams
