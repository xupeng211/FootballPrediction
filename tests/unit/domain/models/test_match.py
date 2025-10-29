from unittest.mock import Mock, patch

"""
比赛模型测试
Tests for Match Model

测试src.domain.models.match模块的功能
"""

from datetime import datetime, timedelta

import pytest

from src.domain.models.match import (
    DomainError,
    Match,
    MatchResult,
    MatchScore,
    MatchStatus,
)


@pytest.mark.unit
class TestMatchStatus:
    """比赛状态测试"""

    def test_status_values(self):
        """测试：状态枚举值"""
        assert MatchStatus.SCHEDULED.value == "scheduled"
        assert MatchStatus.LIVE.value == "live"
        assert MatchStatus.FINISHED.value == "finished"
        assert MatchStatus.CANCELLED.value == "cancelled"
        assert MatchStatus.POSTPONED.value == "postponed"

    def test_status_comparison(self):
        """测试：状态比较"""
        assert MatchStatus.SCHEDULED != MatchStatus.LIVE
        assert MatchStatus.FINISHED == MatchStatus.FINISHED


class TestMatchResult:
    """比赛结果测试"""

    def test_result_values(self):
        """测试：结果枚举值"""
        assert MatchResult.HOME_WIN.value == "home_win"
        assert MatchResult.AWAY_WIN.value == "away_win"
        assert MatchResult.DRAW.value == "draw"

    def test_result_comparison(self):
        """测试：结果比较"""
        assert MatchResult.HOME_WIN != MatchResult.AWAY_WIN
        assert MatchResult.DRAW == MatchResult.DRAW


class TestMatchScore:
    """比赛比分测试"""

    def test_default_score(self):
        """测试：默认比分"""
        score = MatchScore()
        assert score.home_score == 0
        assert score.away_score == 0

    def test_custom_score(self):
        """测试：自定义比分"""
        score = MatchScore(home_score=2, away_score=1)
        assert score.home_score == 2
        assert score.away_score == 1

    def test_negative_score_validation(self):
        """测试：负数比分验证"""
        with pytest.raises(DomainError) as exc_info:
            MatchScore(home_score=-1, away_score=0)
        assert "比分不能为负数" in str(exc_info.value)

        with pytest.raises(DomainError):
            MatchScore(home_score=0, away_score=-1)

    def test_total_goals(self):
        """测试：总进球数"""
        score = MatchScore(2, 1)
        assert score.total_goals == 3

        score = MatchScore(0, 0)
        assert score.total_goals == 0

    def test_goal_difference(self):
        """测试：净胜球"""
        score = MatchScore(3, 1)
        assert score.goal_difference == 2

        score = MatchScore(1, 3)
        assert score.goal_difference == -2

        score = MatchScore(2, 2)
        assert score.goal_difference == 0

    def test_result_home_win(self):
        """测试：主队获胜结果"""
        score = MatchScore(2, 1)
        assert score._result == MatchResult.HOME_WIN

    def test_result_away_win(self):
        """测试：客队获胜结果"""
        score = MatchScore(1, 2)
        assert score._result == MatchResult.AWAY_WIN

    def test_result_draw(self):
        """测试：平局结果"""
        score = MatchScore(1, 1)
        assert score._result == MatchResult.DRAW

    def test_string_representation(self):
        """测试：字符串表示"""
        score = MatchScore(2, 1)
        assert str(score) == "2-1"

    def test_high_scores(self):
        """测试：高比分"""
        score = MatchScore(7, 5)
        assert score.total_goals == 12
        assert score.goal_difference == 2
        assert score._result == MatchResult.HOME_WIN

    def test_zero_scores(self):
        """测试：零比分"""
        score = MatchScore(0, 0)
        assert score.total_goals == 0
        assert score.goal_difference == 0
        assert score._result == MatchResult.DRAW


class TestMatch:
    """比赛实体测试"""

    def test_match_creation_minimal(self):
        """测试：创建最小比赛对象"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10)

        assert match.home_team_id == 1
        assert match.away_team_id == 2
        assert match.league_id == 10
        assert match.status == MatchStatus.SCHEDULED
        assert match.score is None
        assert match.season == ""

    def test_match_creation_full(self):
        """测试：创建完整比赛对象"""
        now = datetime.utcnow()
        score = MatchScore(2, 1)

        match = Match(
            id=100,
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            season="2023-2024",
            match_date=now,
            status=MatchStatus.FINISHED,
            score=score,
            venue="Camp Nou",
            referee="John Smith",
            weather="Sunny",
            attendance=80000,
        )

        assert match.id == 100
        assert match.home_team_id == 1
        assert match.away_team_id == 2
        assert match.season == "2023-2024"
        assert match.match_date == now
        assert match.status == MatchStatus.FINISHED
        assert match.score == score
        assert match.venue == "Camp Nou"
        assert match.referee == "John Smith"
        assert match.weather == "Sunny"
        assert match.attendance == 80000

    def test_same_team_validation(self):
        """测试：相同球队验证"""
        with pytest.raises(DomainError) as exc_info:
            Match(home_team_id=1, away_team_id=1, league_id=10)
        assert "主队和客队不能相同" in str(exc_info.value)

    def test_season_format_validation(self):
        """测试：赛季格式验证"""
        # 有效格式
        match1 = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023")
        assert match1.season == "2023"

        match2 = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")
        assert match2.season == "2023-2024"

        # 无效格式
        with pytest.raises(DomainError):
            Match(home_team_id=1, away_team_id=2, league_id=10, season="23-24")

        with pytest.raises(DomainError):
            Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2025")

        with pytest.raises(DomainError):
            Match(home_team_id=1, away_team_id=2, league_id=10, season="abc")

    def test_start_match_success(self):
        """测试：成功开始比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10)

        match.start_match()
        assert match.status == MatchStatus.LIVE
        assert match.updated_at > match.created_at

    def test_start_match_already_started(self):
        """测试：开始已开始的比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.LIVE)

        with pytest.raises(DomainError) as exc_info:
            match.start_match()
        assert "比赛状态为 live" in str(exc_info.value)

    def test_start_match_finished(self):
        """测试：开始已结束的比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.FINISHED)

        with pytest.raises(DomainError):
            match.start_match()

    def test_update_score_scheduled(self):
        """测试：更新已安排比赛的比分"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10)

        match.update_score(1, 0)
        assert match.score.home_score == 1
        assert match.score.away_score == 0
        assert match.status == MatchStatus.LIVE

    def test_update_score_live(self):
        """测试：更新进行中比赛的比分"""
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            status=MatchStatus.LIVE,
            score=MatchScore(1, 0),
        )

        match.update_score(1, 1)
        assert match.score.home_score == 1
        assert match.score.away_score == 1
        assert match.status == MatchStatus.LIVE

    def test_update_score_no_goal_change(self):
        """测试：更新比分为0-0"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10)

        match.update_score(0, 0)
        assert match.score.home_score == 0
        assert match.score.away_score == 0
        assert match.status == MatchStatus.SCHEDULED

    def test_update_score_finished(self):
        """测试：更新已结束比赛的比分"""
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            status=MatchStatus.FINISHED,
            score=MatchScore(2, 1),
        )

        with pytest.raises(DomainError) as exc_info:
            match.update_score(3, 1)
        assert "只有进行中或已安排的比赛才能更新比分" in str(exc_info.value)

    def test_finish_match_success(self):
        """测试：成功结束比赛"""
        match = Match(
            id=100,
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            status=MatchStatus.LIVE,
            score=MatchScore(2, 1),
        )

        with patch("src.domain.events.MatchFinishedEvent") as mock_event:
            mock_event.return_value = Mock()
            match.finish_match()

            assert match.status == MatchStatus.FINISHED
            assert match.updated_at > match.created_at
            # 验证领域事件被添加
            assert len(match.get_domain_events()) == 1
            mock_event.assert_called_once()

    def test_finish_match_not_live(self):
        """测试：结束未开始的比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.SCHEDULED)

        with pytest.raises(DomainError) as exc_info:
            match.finish_match()
        assert "只有进行中的比赛才能结束" in str(exc_info.value)

    def test_finish_match_no_score(self):
        """测试：结束没有比分的比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.LIVE)

        with pytest.raises(DomainError) as exc_info:
            match.finish_match()
        assert "比赛必须要有比分才能结束" in str(exc_info.value)

    def test_cancel_match_success(self):
        """测试：成功取消比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.SCHEDULED)

        match.cancel_match("Weather conditions")
        assert match.status == MatchStatus.CANCELLED
        assert match.updated_at > match.created_at

    def test_cancel_match_finished(self):
        """测试：取消已结束的比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.FINISHED)

        with pytest.raises(DomainError) as exc_info:
            match.cancel_match()
        assert "已结束或已取消的比赛无法再次取消" in str(exc_info.value)

    def test_cancel_match_already_cancelled(self):
        """测试：取消已取消的比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.CANCELLED)

        with pytest.raises(DomainError):
            match.cancel_match()

    def test_postpone_match_success(self):
        """测试：成功延期比赛"""
        future_date = datetime.utcnow() + timedelta(days=7)
        match = Match(home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.SCHEDULED)

        match.postpone_match(future_date)
        assert match.status == MatchStatus.POSTPONED
        assert match.match_date == future_date
        assert match.updated_at > match.created_at

    def test_postpone_match_without_date(self):
        """测试：延期比赛不指定新日期"""
        original_date = datetime.utcnow() + timedelta(days=1)
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            match_date=original_date,
            status=MatchStatus.SCHEDULED,
        )

        match.postpone_match()
        assert match.status == MatchStatus.POSTPONED
        assert match.match_date == original_date

    def test_postpone_match_finished(self):
        """测试：延期已结束的比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.FINISHED)

        with pytest.raises(DomainError):
            match.postpone_match()

    def test_is_same_team(self):
        """测试：检查是否是参赛球队"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10)

        assert match.is_same_team(1) is True
        assert match.is_same_team(2) is True
        assert match.is_same_team(3) is False

    def test_is_home_team(self):
        """测试：检查是否是主队"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10)

        assert match.is_home_team(1) is True
        assert match.is_home_team(2) is False

    def test_is_away_team(self):
        """测试：检查是否是客队"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10)

        assert match.is_away_team(2) is True
        assert match.is_away_team(1) is False

    def test_get_opponent_id(self):
        """测试：获取对手ID"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10)

        assert match.get_opponent_id(1) == 2
        assert match.get_opponent_id(2) == 1
        assert match.get_opponent_id(3) is None

    def test_is_upcoming_future(self):
        """测试：是否是即将开始的比赛（未来）"""
        future_date = datetime.utcnow() + timedelta(days=5)
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            match_date=future_date,
            status=MatchStatus.SCHEDULED,
        )

        assert match.is_upcoming is True
        # days_until_match 可能会因时间差而有1天的差异，所以检查范围
        assert 4 <= match.days_until_match <= 5

    def test_is_upcoming_past(self):
        """测试：是否是即将开始的比赛（过去）"""
        past_date = datetime.utcnow() - timedelta(days=5)
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            match_date=past_date,
            status=MatchStatus.SCHEDULED,
        )

        assert match.is_upcoming is False
        assert match.days_until_match == 0

    def test_is_live(self):
        """测试：是否正在进行"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.LIVE)

        assert match.is_live is True

    def test_is_finished(self):
        """测试：是否已结束"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.FINISHED)

        assert match.is_finished is True

    def test_can_be_predicted(self):
        """测试：是否可以预测"""
        scheduled_match = Match(
            home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.SCHEDULED
        )
        assert scheduled_match.can_be_predicted is True

        live_match = Match(home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.LIVE)
        assert live_match.can_be_predicted is True

        finished_match = Match(
            home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.FINISHED
        )
        assert finished_match.can_be_predicted is False

        cancelled_match = Match(
            home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.CANCELLED
        )
        assert cancelled_match.can_be_predicted is False

    def test_get_duration_finished(self):
        """测试：获取已结束比赛的时长"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.FINISHED)
        assert match.get_duration() == 90

    def test_get_duration_not_finished(self):
        """测试：获取未结束比赛的时长"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.LIVE)
        assert match.get_duration() is None

    def test_domain_events_management(self):
        """测试：领域事件管理"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10)

        # 初始状态没有事件
        assert len(match.get_domain_events()) == 0

        # 添加事件
        mock_event = Mock()
        match._add_domain_event(mock_event)
        assert len(match.get_domain_events()) == 1
        assert match.get_domain_events()[0] is mock_event

        # 清除事件
        match.clear_domain_events()
        assert len(match.get_domain_events()) == 0

    def test_to_dict_without_score(self):
        """测试：转换为字典（无比分）"""
        match = Match(
            id=100,
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            season="2023-2024",
            venue="Camp Nou",
        )

        _data = match.to_dict()
        assert _data["id"] == 100
        assert _data["home_team_id"] == 1
        assert _data["away_team_id"] == 2
        assert _data["league_id"] == 10
        assert _data["season"] == "2023-2024"
        assert _data["status"] == "scheduled"
        assert _data["score"] is None
        assert _data["venue"] == "Camp Nou"

    def test_to_dict_with_score(self):
        """测试：转换为字典（有比分）"""
        score = MatchScore(2, 1)
        match = Match(
            id=100,
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            status=MatchStatus.FINISHED,
            score=score,
        )

        _data = match.to_dict()
        assert _data["status"] == "finished"
        assert _data["score"]["home_score"] == 2
        assert _data["score"]["away_score"] == 1
        assert _data["score"]["result"] == "home_win"

    def test_from_dict_without_score(self):
        """测试：从字典创建实例（无比分）"""
        _data = {
            "id": 100,
            "home_team_id": 1,
            "away_team_id": 2,
            "league_id": 10,
            "season": "2023-2024",
            "status": "scheduled",
            "venue": "Camp Nou",
        }

        match = Match.from_dict(data)
        assert match.id == 100
        assert match.home_team_id == 1
        assert match.away_team_id == 2
        assert match.season == "2023-2024"
        assert match.status == MatchStatus.SCHEDULED
        assert match.score is None
        assert match.venue == "Camp Nou"

    def test_from_dict_with_score(self):
        """测试：从字典创建实例（有比分）"""
        _data = {
            "id": 100,
            "home_team_id": 1,
            "away_team_id": 2,
            "league_id": 10,
            "status": "finished",
            "score": {"home_score": 2, "away_score": 1, "result": "home_win"},
        }

        match = Match.from_dict(data)
        assert match.status == MatchStatus.FINISHED
        assert match.score.home_score == 2
        assert match.score.away_score == 1
        assert match.score._result == MatchResult.HOME_WIN

    def test_from_dict_with_dates(self):
        """测试：从字典创建实例（包含日期）"""
        _data = {
            "home_team_id": 1,
            "away_team_id": 2,
            "league_id": 10,
            "match_date": "2023-01-01T20:00:00",
            "created_at": "2023-01-01T19:00:00",
            "updated_at": "2023-01-01T19:00:00",
            "status": "scheduled",
        }

        match = Match.from_dict(data)
        assert isinstance(match.match_date, datetime)
        assert isinstance(match.created_at, datetime)
        assert isinstance(match.updated_at, datetime)

    def test_string_representation(self):
        """测试：字符串表示"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, status=MatchStatus.SCHEDULED)
        assert "Team1 vs Team2" in str(match)
        assert "scheduled" in str(match)

        match_with_score = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            status=MatchStatus.FINISHED,
            score=MatchScore(2, 1),
        )
        assert "(2-1)" in str(match_with_score)
        assert "finished" in str(match_with_score)

    def test_edge_cases(self):
        """测试：边界情况"""
        # 零ID球队
        match = Match(home_team_id=0, away_team_id=1, league_id=0)
        assert match.home_team_id == 0
        assert match.league_id == 0

        # 空字符串venue
        match = Match(home_team_id=1, away_team_id=2, league_id=10, venue="")
        assert match.venue == ""

        # 零观众
        match = Match(home_team_id=1, away_team_id=2, league_id=10, attendance=0)
        assert match.attendance == 0

    def test_full_match_lifecycle(self):
        """测试：完整的比赛生命周期"""
        # 1. 创建比赛
        match = Match(
            id=100,
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            season="2023-2024",
            venue="Camp Nou",
        )
        assert match.status == MatchStatus.SCHEDULED

        # 2. 开始比赛
        match.start_match()
        assert match.status == MatchStatus.LIVE

        # 3. 更新比分
        match.update_score(1, 0)
        assert match.score.home_score == 1
        assert match.score.away_score == 0

        # 4. 继续更新比分
        match.update_score(2, 0)
        assert match.score.home_score == 2

        # 5. 结束比赛
        with patch("src.domain.events.MatchFinishedEvent"):
            match.finish_match()
        assert match.status == MatchStatus.FINISHED
        assert match.is_finished is True
        assert match.can_be_predicted is False
