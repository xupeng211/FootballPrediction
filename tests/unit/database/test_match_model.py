"""比赛模型测试"""

import pytest
from datetime import datetime
from src.database.models.match import Match, MatchStatus, MatchResult
from src.database.models.team import Team


class TestMatchModel:
    """比赛模型测试"""

    def test_match_creation(self):
        """测试比赛创建"""
        home_team = Team(id=1, name="Team A", league="Premier League")
        away_team = Team(id=2, name="Team B", league="Premier League")

        match = Match(
            id=1,
            home_team=home_team,
            away_team=away_team,
            date=datetime(2024, 1, 1, 15, 0),
            status=MatchStatus.SCHEDULED,
            league="Premier League",
            season="2023-24",
        )

        assert match.id == 1
        assert match.home_team == home_team
        assert match.away_team == away_team
        assert match.status == MatchStatus.SCHEDULED

    def test_match_status_transitions(self):
        """测试比赛状态转换"""
        match = Match(
            id=1,
            home_team=Team(id=1, name="Team A"),
            away_team=Team(id=2, name="Team B"),
            date=datetime(2024, 1, 1),
            status=MatchStatus.SCHEDULED,
        )

        # 从预定到进行中
        match.status = MatchStatus.LIVE
        assert match.status == MatchStatus.LIVE

        # 从进行中到完成
        match.status = MatchStatus.COMPLETED
        assert match.status == MatchStatus.COMPLETED

        # 从完成到已取消（特殊情况）
        match.status = MatchStatus.CANCELLED
        assert match.status == MatchStatus.CANCELLED

    def test_match_result_calculation(self):
        """测试比赛结果计算"""
        home_team = Team(id=1, name="Team A")
        away_team = Team(id=2, name="Team B")

        match = Match(
            id=1,
            home_team=home_team,
            away_team=away_team,
            home_score=2,
            away_score=1,
            status=MatchStatus.COMPLETED,
        )

        assert match.result == MatchResult.HOME_WIN

        match.home_score = 1
        match.away_score = 1
        assert match.result == MatchResult.DRAW

        match.home_score = 0
        match.away_score = 1
        assert match.result == MatchResult.AWAY_WIN

    def test_match_properties(self):
        """测试比赛属性"""
        match = Match(
            id=1,
            home_team=Team(id=1, name="Team A"),
            away_team=Team(id=2, name="Team B"),
            date=datetime(2024, 1, 1, 15, 0),
            home_score=2,
            away_score=1,
            status=MatchStatus.COMPLETED,
        )

        assert match.goal_difference == 1
        assert match.total_goals == 3
        assert match.home_goals == 2
        assert match.away_goals == 1

    def test_match_to_dict(self):
        """测试比赛转换为字典"""
        home_team = Team(id=1, name="Team A", code="TA")
        away_team = Team(id=2, name="Team B", code="TB")

        match = Match(
            id=1,
            home_team=home_team,
            away_team=away_team,
            date=datetime(2024, 1, 1),
            home_score=3,
            away_score=0,
            status=MatchStatus.COMPLETED,
            league="Premier League",
        )

        match_dict = match.to_dict()
        assert match_dict["id"] == 1
        assert match_dict["home_team_name"] == "Team A"
        assert match_dict["away_team_name"] == "Team B"
        assert match_dict["home_score"] == 3
        assert match_dict["away_score"] == 0

    def test_match_validation(self):
        """测试比赛验证"""
        # 测试无效的比分
        with pytest.raises(ValueError):
            Match(
                id=1,
                home_team=Team(id=1, name="Team A"),
                away_team=Team(id=2, name="Team B"),
                home_score=-1,  # 无效的比分
                away_score=1,
                status=MatchStatus.COMPLETED,
            )

        # 测试取消的比赛没有比分
        match = Match(
            id=1,
            home_team=Team(id=1, name="Team A"),
            away_team=Team(id=2, name="Team B"),
            status=MatchStatus.CANCELLED,
        )
        assert match.home_score is None
        assert match.away_score is None

    def test_match_string_representation(self):
        """测试比赛字符串表示"""
        match = Match(
            id=1,
            home_team=Team(id=1, name="Team A"),
            away_team=Team(id=2, name="Team B"),
            date=datetime(2024, 1, 1),
        )
        assert "Team A vs Team B" in str(match)
