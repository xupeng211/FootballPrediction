#!/usr/bin/env python3
"""
Phase 4.2 - Domain模块高价值深度优化
比赛领域模型comprehensive测试，业务逻辑全覆盖
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


class TestMatchScoreComprehensive:
    """MatchScore值对象全面测试"""

    def test_match_score_default(self):
        """测试默认比分创建"""
        score = MatchScore()
        assert score.home_score == 0
        assert score.away_score == 0
        assert score.total_goals == 0
        assert score.goal_difference == 0
        assert score.result == MatchResult.DRAW

    def test_match_score_custom(self):
        """测试自定义比分创建"""
        score = MatchScore(home_score=3, away_score=1)
        assert score.home_score == 3
        assert score.away_score == 1
        assert score.total_goals == 4
        assert score.goal_difference == 2
        assert score.result == MatchResult.HOME_WIN

    def test_match_score_away_win(self):
        """测试客队获胜"""
        score = MatchScore(home_score=1, away_score=2)
        assert score.total_goals == 3
        assert score.goal_difference == -1
        assert score.result == MatchResult.AWAY_WIN

    def test_match_score_high_scoring(self):
        """测试高分比赛"""
        score = MatchScore(home_score=5, away_score=4)
        assert score.total_goals == 9
        assert score.goal_difference == 1
        assert score.result == MatchResult.HOME_WIN

    def test_match_score_negative_validation(self):
        """测试负数比分验证"""
        with pytest.raises(DomainError, match="比分不能为负数"):
            MatchScore(home_score=-1, away_score=2)

        with pytest.raises(DomainError, match="比分不能为负数"):
            MatchScore(home_score=2, away_score=-1)

        with pytest.raises(DomainError, match="比分不能为负数"):
            MatchScore(home_score=-1, away_score=-1)

    def test_match_score_properties(self):
        """测试比分属性计算"""
        # 大比分胜利
        score = MatchScore(home_score=4, away_score=0)
        assert score.total_goals == 4
        assert score.goal_difference == 4
        assert score.result == MatchResult.HOME_WIN

        # 大比分失败
        score = MatchScore(home_score=0, away_score=5)
        assert score.total_goals == 5
        assert score.goal_difference == -5
        assert score.result == MatchResult.AWAY_WIN

    def test_match_score_string_representation(self):
        """测试比分字符串表示"""
        score = MatchScore(home_score=2, away_score=1)
        assert str(score) == "2-1"

        score = MatchScore(home_score=0, away_score=0)
        assert str(score) == "0-0"

    def test_match_score_edge_cases(self):
        """测试比分边界情况"""
        # 最大合理比分
        score = MatchScore(home_score=99, away_score=99)
        assert score.total_goals == 198
        assert score.result == MatchResult.DRAW

        # 单球比赛
        score = MatchScore(home_score=1, away_score=0)
        assert score.total_goals == 1
        assert score.result == MatchResult.HOME_WIN


class TestMatchDomainComprehensive:
    """Match领域模型全面测试"""

    def test_match_creation_valid(self):
        """测试有效比赛创建"""
        future_date = datetime.utcnow() + timedelta(days=1)
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=100,
            season="2023-2024",
            match_date=future_date,
        )

        assert match.home_team_id == 1
        assert match.away_team_id == 2
        assert match.league_id == 100
        assert match.season == "2023-2024"
        assert match.status == MatchStatus.SCHEDULED
        assert match.score is None
        assert match.is_upcoming

    def test_match_creation_same_teams(self):
        """测试相同队伍创建比赛"""
        with pytest.raises(DomainError, match="主队和客队不能相同"):
            Match(home_team_id=1, away_team_id=1, league_id=100)

    def test_match_creation_invalid_season(self):
        """测试无效赛季格式"""
        # 无效年份格式
        with pytest.raises(DomainError, match="赛季格式无效"):
            Match(home_team_id=1, away_team_id=2, league_id=100, season="23")

        # 无效跨年格式
        with pytest.raises(DomainError, match="赛季格式无效"):
            Match(home_team_id=1, away_team_id=2, league_id=100, season="2023-2025")

        # 跨年但不连续
        with pytest.raises(DomainError, match="赛季格式无效"):
            Match(home_team_id=1, away_team_id=2, league_id=100, season="2023-2025")

    def test_match_creation_valid_season_formats(self):
        """测试有效赛季格式"""
        # 单年格式
        match1 = Match(home_team_id=1, away_team_id=2, league_id=100, season="2023")
        assert match1.season == "2023"

        # 跨年格式
        match2 = Match(
            home_team_id=1, away_team_id=2, league_id=100, season="2023-2024"
        )
        assert match2.season == "2023-2024"

        # 边界年份
        match3 = Match(
            home_team_id=1, away_team_id=2, league_id=100, season="1999-2000"
        )
        assert match3.season == "1999-2000"

    def test_start_match_success(self):
        """测试成功开始比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)

        match.start_match()

        assert match.status == MatchStatus.LIVE
        assert not match.is_upcoming
        assert match.is_live

    def test_start_match_invalid_status(self):
        """测试无效状态开始比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)
        match.status = MatchStatus.FINISHED

        with pytest.raises(DomainError, match="比赛状态为 finished，无法开始"):
            match.start_match()

    def test_update_score_scheduled_to_live(self):
        """测试从安排状态更新比分到进行中"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)

        # 首次有进球，状态变为进行中
        match.update_score(1, 0)

        assert match.status == MatchStatus.LIVE
        assert match.score.home_score == 1
        assert match.score.away_score == 0
        assert match.is_live

    def test_update_score_live_match(self):
        """测试进行中比赛更新比分"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)
        match.status = MatchStatus.LIVE

        # 更新比分
        match.update_score(2, 1)

        assert match.status == MatchStatus.LIVE
        assert match.score.home_score == 2
        assert match.score.away_score == 1

    def test_update_score_no_goals(self):
        """测试更新比分为0-0不改变状态"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)

        # 0-0比分，状态应该保持安排
        match.update_score(0, 0)

        assert match.status == MatchStatus.SCHEDULED
        # 注意：即使0-0，因为调用了update_score，match_date可能已经过了
        # 我们只验证状态保持SCHEDULED

    def test_update_score_invalid_status(self):
        """测试无效状态更新比分"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)
        match.status = MatchStatus.FINISHED

        with pytest.raises(DomainError, match="只有进行中或已安排的比赛才能更新比分"):
            match.update_score(1, 0)

    def test_finish_match_success(self):
        """测试成功结束比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)
        match.start_match()
        match.update_score(2, 1)

        match.finish_match()

        assert match.status == MatchStatus.FINISHED
        assert match.is_finished
        assert not match.is_live
        assert match.score.result == MatchResult.HOME_WIN

    def test_finish_match_no_score(self):
        """测试没有比分结束比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)
        match.start_match()

        with pytest.raises(DomainError, match="比赛必须要有比分才能结束"):
            match.finish_match()

    def test_finish_match_invalid_status(self):
        """测试无效状态结束比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)

        with pytest.raises(DomainError, match="只有进行中的比赛才能结束"):
            match.finish_match()

    def test_cancel_match_success(self):
        """测试成功取消比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)

        match.cancel_match("天气原因")

        assert match.status == MatchStatus.CANCELLED
        assert not match.is_upcoming
        assert not match.is_live

    def test_cancel_match_finished(self):
        """测试取消已结束比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)
        match.start_match()
        match.update_score(1, 0)
        match.finish_match()

        with pytest.raises(DomainError, match="已结束或已取消的比赛无法再次取消"):
            match.cancel_match()

    def test_cancel_match_already_cancelled(self):
        """测试取消已取消比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)
        match.cancel_match()

        with pytest.raises(DomainError, match="已结束或已取消的比赛无法再次取消"):
            match.cancel_match()

    def test_postpone_match_success(self):
        """测试成功延期比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)
        new_date = datetime.utcnow() + timedelta(days=7)

        match.postpone_match(new_date)

        assert match.status == MatchStatus.POSTPONED
        assert match.match_date == new_date

    def test_postpone_match_without_new_date(self):
        """测试延期比赛不指定新日期"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)
        original_date = match.match_date

        match.postpone_match()

        assert match.status == MatchStatus.POSTPONED
        assert match.match_date == original_date

    def test_postpone_match_finished(self):
        """测试延期已结束比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)
        match.start_match()
        match.update_score(1, 0)
        match.finish_match()

        with pytest.raises(DomainError, match="已结束或已取消的比赛无法延期"):
            match.postpone_match()

    def test_team_relationship_methods(self):
        """测试队伍关系方法"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)

        # 检查是否是参赛队伍
        assert match.is_same_team(1)
        assert match.is_same_team(2)
        assert not match.is_same_team(3)

        # 检查主队
        assert match.is_home_team(1)
        assert not match.is_home_team(2)
        assert not match.is_home_team(3)

        # 检查客队
        assert match.is_away_team(2)
        assert not match.is_away_team(1)
        assert not match.is_away_team(3)

        # 获取对手ID
        assert match.get_opponent_id(1) == 2
        assert match.get_opponent_id(2) == 1
        assert match.get_opponent_id(3) is None

    def test_upcoming_match_calculation(self):
        """测试即将开始比赛计算"""
        future_date = datetime.utcnow() + timedelta(days=5)
        past_date = datetime.utcnow() - timedelta(days=5)

        # 未来比赛
        future_match = Match(
            home_team_id=1, away_team_id=2, league_id=100, match_date=future_date
        )
        assert future_match.is_upcoming
        assert future_match.days_until_match >= 4  # 可能是4或5天，取决于精确时间

        # 过去比赛
        past_match = Match(
            home_team_id=1, away_team_id=2, league_id=100, match_date=past_date
        )
        assert not past_match.is_upcoming
        assert past_match.days_until_match == 0

    def test_can_be_predicted_property(self):
        """测试是否可以预测属性"""
        # 已安排的比赛
        scheduled_match = Match(home_team_id=1, away_team_id=2, league_id=100)
        assert scheduled_match.can_be_predicted

        # 进行中的比赛
        live_match = Match(home_team_id=1, away_team_id=2, league_id=100)
        live_match.status = MatchStatus.LIVE
        assert live_match.can_be_predicted

        # 已结束的比赛
        finished_match = Match(home_team_id=1, away_team_id=2, league_id=100)
        finished_match.status = MatchStatus.FINISHED
        assert not finished_match.can_be_predicted

        # 已取消的比赛
        cancelled_match = Match(home_team_id=1, away_team_id=2, league_id=100)
        cancelled_match.status = MatchStatus.CANCELLED
        assert not cancelled_match.can_be_predicted

    def test_get_duration_finished_match(self):
        """测试获取已结束比赛时长"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)
        match.status = MatchStatus.FINISHED

        duration = match.get_duration()
        assert duration == 90  # 标准足球比赛时长

    def test_get_duration_unfinished_match(self):
        """测试获取未结束比赛时长"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)

        duration = match.get_duration()
        assert duration is None

    def test_domain_event_management(self):
        """测试领域事件管理"""
        match = Match(home_team_id=1, away_team_id=2, league_id=100)

        # 开始时没有事件
        events = match.get_domain_events()
        assert len(events) == 0

        # 结束比赛产生事件
        match.start_match()
        match.update_score(2, 1)
        match.finish_match()

        events = match.get_domain_events()
        assert len(events) >= 1  # 至少有MatchFinishedEvent

        # 清除事件
        match.clear_domain_events()
        events = match.get_domain_events()
        assert len(events) == 0

    def test_to_dict_serialization(self):
        """测试字典序列化"""
        match = Match(
            id=1,
            home_team_id=100,
            away_team_id=200,
            league_id=10,
            season="2023-2024",
            venue="老特拉福德球场",
            referee="迈克尔·奥利弗",
            weather="晴朗",
            attendance=75000,
        )
        match.start_match()
        match.update_score(3, 1)

        data = match.to_dict()

        assert data["id"] == 1
        assert data["home_team_id"] == 100
        assert data["away_team_id"] == 200
        assert data["season"] == "2023-2024"
        assert data["venue"] == "老特拉福德球场"
        assert data["referee"] == "迈克尔·奥利弗"
        assert data["weather"] == "晴朗"
        assert data["attendance"] == 75000
        assert data["status"] == "live"
        assert data["score"]["home_score"] == 3
        assert data["score"]["away_score"] == 1
        assert data["score"]["result"] == "home_win"

    def test_from_dict_deserialization(self):
        """测试字典反序列化"""
        data = {
            "id": 1,
            "home_team_id": 100,
            "away_team_id": 200,
            "league_id": 10,
            "season": "2023-2024",
            "match_date": "2024-01-01T15:00:00",
            "status": "finished",
            "score": {"home_score": 2, "away_score": 1, "result": "home_win"},
            "venue": "老特拉福德球场",
            "referee": "迈克尔·奥利弗",
            "weather": "晴朗",
            "attendance": 75000,
            "created_at": "2024-01-01T10:00:00",
            "updated_at": "2024-01-01T17:00:00",
        }

        match = Match.from_dict(data)

        assert match.id == 1
        assert match.home_team_id == 100
        assert match.away_team_id == 200
        assert match.season == "2023-2024"
        assert match.status == MatchStatus.FINISHED
        assert match.score.home_score == 2
        assert match.score.away_score == 1
        assert match.score.result == MatchResult.HOME_WIN
        assert match.venue == "老特拉福德球场"

    def test_string_representation(self):
        """测试字符串表示"""
        match = Match(home_team_id=100, away_team_id=200, league_id=10)

        # 无比分
        assert "Team100 vs Team200" in str(match)
        assert "scheduled" in str(match)

        # 有比分
        match.update_score(2, 1)
        assert "Team100 vs Team200" in str(match)
        assert "2-1" in str(match)

    def test_complete_match_lifecycle(self):
        """测试完整比赛生命周期"""
        # 创建比赛
        future_date = datetime.utcnow() + timedelta(days=1)
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=100,
            season="2023-2024",
            match_date=future_date,
            venue="体育场",
            referee="裁判员",
        )

        # 初始状态
        assert match.status == MatchStatus.SCHEDULED
        assert match.is_upcoming
        assert match.can_be_predicted

        # 开始比赛
        match.start_match()
        assert match.status == MatchStatus.LIVE
        assert match.is_live
        assert match.can_be_predicted

        # 进球
        match.update_score(1, 0)
        assert match.score.home_score == 1
        assert match.score.result == MatchResult.HOME_WIN

        # 更多进球
        match.update_score(2, 0)
        match.update_score(2, 1)
        assert match.score.total_goals == 3
        assert match.score.result == MatchResult.HOME_WIN

        # 结束比赛
        match.finish_match()
        assert match.status == MatchStatus.FINISHED
        assert match.is_finished
        assert not match.can_be_predicted

        # 验证最终状态
        assert match.score.home_score == 2
        assert match.score.away_score == 1
        assert match.score.result == MatchResult.HOME_WIN


def test_match_domain_comprehensive_suite():
    """比赛领域模型综合测试套件"""
    # 快速验证核心功能
    future_date = datetime.utcnow() + timedelta(days=1)
    match = Match(home_team_id=1, away_team_id=2, league_id=100, match_date=future_date)
    assert match.is_upcoming

    match.start_match()
    assert match.is_live

    match.update_score(2, 1)
    assert match.score.total_goals == 3

    match.finish_match()
    assert match.is_finished


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
