"""
测试 MatchService 领域服务
"""

import pytest
from datetime import datetime, timedelta

import sys

sys.path.insert(0, "src")

from domain.models.match import Match, MatchStatus, MatchScore
from domain.models.team import Team
from domain.services.match_service import MatchService


class TestMatchService:
    """测试 MatchService"""

    def setup_method(self):
        """设置测试环境"""
        self.service = MatchService()
        self.home_team = Team(id=1, name="Team A", stadium="Stadium A")
        self.away_team = Team(id=2, name="Team B", stadium="Stadium B")
        self.match_time = datetime.utcnow() + timedelta(days=1)

    def test_schedule_match_success(self):
        """测试成功安排比赛"""
        match = self.service.schedule_match(
            home_team=self.home_team,
            away_team=self.away_team,
            match_time=self.match_time,
            venue="Test Venue",
        )

        assert match.home_team_id == 1
        assert match.away_team_id == 2
        assert match.match_date == self.match_time
        assert match.venue == "Test Venue"
        assert match.status == MatchStatus.SCHEDULED

    def test_schedule_same_teams_error(self):
        """测试安排相同球队比赛应该失败"""
        with pytest.raises(ValueError, match="主队和客队不能是同一支球队"):
            self.service.schedule_match(
                home_team=self.home_team,
                away_team=self.home_team,
                match_time=self.match_time,
            )

    def test_start_match_success(self):
        """测试成功开始比赛"""
        # 安排一场过去的比赛
        past_time = datetime.utcnow() - timedelta(hours=1)
        match = self.service.schedule_match(
            home_team=self.home_team, away_team=self.away_team, match_time=past_time
        )

        # 开始比赛
        self.service.start_match(match)
        assert match.status == MatchStatus.LIVE
        assert len(self.service._events) == 1

    def test_start_future_match_error(self):
        """测试开始未来的比赛应该失败"""
        match = self.service.schedule_match(
            home_team=self.home_team,
            away_team=self.away_team,
            match_time=self.match_time,
        )

        with pytest.raises(ValueError, match="比赛时间还未到"):
            self.service.start_match(match)

    def test_update_match_score_success(self):
        """测试更新比分成功"""
        past_time = datetime.utcnow() - timedelta(hours=1)
        match = self.service.schedule_match(
            home_team=self.home_team, away_team=self.away_team, match_time=past_time
        )
        match.start_match()

        # 更新比分
        self.service.update_match_score(match, 2, 1)
        assert match.score.home_score == 2
        assert match.score.away_score == 1

    def test_update_negative_score_error(self):
        """测试更新负数比分应该失败"""
        past_time = datetime.utcnow() - timedelta(hours=1)
        match = self.service.schedule_match(
            home_team=self.home_team, away_team=self.away_team, match_time=past_time
        )
        match.start_match()

        with pytest.raises(ValueError, match="比分不能为负数"):
            self.service.update_match_score(match, -1, 0)

    def test_finish_match_success(self):
        """测试结束比赛成功"""
        past_time = datetime.utcnow() - timedelta(hours=1)
        match = self.service.schedule_match(
            home_team=self.home_team, away_team=self.away_team, match_time=past_time
        )
        match.start_match()
        match.update_score(2, 1)

        # 结束比赛
        self.service.finish_match(match)
        assert match.status == MatchStatus.FINISHED
        assert len(self.service._events) == 2  # start + finish

    def test_cancel_match_success(self):
        """测试取消比赛成功"""
        match = self.service.schedule_match(
            home_team=self.home_team,
            away_team=self.away_team,
            match_time=self.match_time,
        )

        # 取消比赛
        self.service.cancel_match(match, "Bad weather")
        assert match.status == MatchStatus.CANCELLED
        assert len(self.service._events) == 1

    def test_postpone_match_success(self):
        """测试延期比赛成功"""
        match = self.service.schedule_match(
            home_team=self.home_team,
            away_team=self.away_team,
            match_time=self.match_time,
        )

        new_time = datetime.utcnow() + timedelta(days=2)
        # 延期比赛
        self.service.postpone_match(match, new_time, "Bad weather")
        assert match.status == MatchStatus.POSTPONED
        assert match.match_date == new_time
