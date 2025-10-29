"""
Match领域模型边界条件测试 - 修复版本
基于实际Match模型API的完整测试覆盖，目标达到90%+覆盖率
"""

from datetime import datetime, timedelta

import pytest

from src.core.exceptions import DomainError
from src.domain.models.match import Match, MatchResult, MatchScore, MatchStatus


@pytest.mark.unit
class TestMatchScore:
    """MatchScore值对象边界条件测试"""

    def test_match_score_initialization_default(self) -> None:
        """✅ 成功用例：默认初始化"""
        score = MatchScore()
        assert score.home_score == 0
        assert score.away_score == 0

    def test_match_score_initialization_with_values(self) -> None:
        """✅ 成功用例：指定值初始化"""
        score = MatchScore(home_score=2, away_score=1)
        assert score.home_score == 2
        assert score.away_score == 1

    def test_match_score_negative_values_validation(self) -> None:
        """✅ 边界用例：负比分验证"""
        with pytest.raises(DomainError, match="比分不能为负数"):
            MatchScore(home_score=-1, away_score=0)

        with pytest.raises(DomainError, match="比分不能为负数"):
            MatchScore(home_score=0, away_score=-1)

        with pytest.raises(DomainError, match="比分不能为负数"):
            MatchScore(home_score=-1, away_score=-1)

    def test_match_score_total_goals_property(self) -> None:
        """✅ 成功用例：总进球数属性"""
        score = MatchScore(home_score=3, away_score=2)
        assert score.total_goals == 5

        score = MatchScore(home_score=0, away_score=0)
        assert score.total_goals == 0

    def test_match_score_goal_difference_property(self) -> None:
        """✅ 成功用例：净胜球属性"""
        score = MatchScore(home_score=3, away_score=1)
        assert score.goal_difference == 2

        score = MatchScore(home_score=1, away_score=3)
        assert score.goal_difference == -2

        score = MatchScore(home_score=2, away_score=2)
        assert score.goal_difference == 0

    def test_match_score_result_property(self) -> None:
        """✅ 成功用例：比赛结果属性"""
        # 主队获胜
        score = MatchScore(home_score=2, away_score=1)
        assert score.result == MatchResult.HOME_WIN

        # 客队获胜
        score = MatchScore(home_score=1, away_score=2)
        assert score.result == MatchResult.AWAY_WIN

        # 平局
        score = MatchScore(home_score=1, away_score=1)
        assert score.result == MatchResult.DRAW

        # 0-0平局
        score = MatchScore(home_score=0, away_score=0)
        assert score.result == MatchResult.DRAW

    def test_match_score_str_representation(self) -> None:
        """✅ 成功用例：字符串表示"""
        score = MatchScore(home_score=2, away_score=1)
        assert str(score) == "2-1"

        score = MatchScore(home_score=0, away_score=0)
        assert str(score) == "0-0"

    def test_match_score_edge_cases(self) -> None:
        """✅ 边界用例：极端比分"""
        # 大比分
        score = MatchScore(home_score=100, away_score=0)
        assert score.total_goals == 100
        assert score.goal_difference == 100
        assert score.result == MatchResult.HOME_WIN

        # 相反极端比分
        score = MatchScore(home_score=0, away_score=100)
        assert score.total_goals == 100
        assert score.goal_difference == -100
        assert score.result == MatchResult.AWAY_WIN


@pytest.mark.unit
class TestMatch:
    """Match领域模型边界条件测试"""

    def test_match_initialization_minimal(self) -> None:
        """✅ 成功用例：最小初始化"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")

        assert match.home_team_id == 1
        assert match.away_team_id == 2
        assert match.league_id == 10
        assert match.season == "2023-2024"
        assert match.status == MatchStatus.SCHEDULED
        assert match.score is None
        assert match.venue is None
        assert match.referee is None
        assert match.weather is None
        assert match.attendance is None

    def test_match_initialization_full(self) -> None:
        """✅ 成功用例：完整初始化"""
        match_date = datetime(2023, 6, 15, 18, 0)
        match = Match(
            id=1,
            home_team_id=100,
            away_team_id=200,
            league_id=10,
            season="2023-2024",
            match_date=match_date,
            status=MatchStatus.SCHEDULED,
            venue="Test Stadium",
            referee="Test Referee",
            weather="Sunny",
            attendance=50000,
        )

        assert match.id == 1
        assert match.home_team_id == 100
        assert match.away_team_id == 200
        assert match.league_id == 10
        assert match.season == "2023-2024"
        assert match.match_date == match_date
        assert match.status == MatchStatus.SCHEDULED
        assert match.venue == "Test Stadium"
        assert match.referee == "Test Referee"
        assert match.weather == "Sunny"
        assert match.attendance == 50000

    def test_match_validation_same_teams(self) -> None:
        """✅ 边界用例：相同球队验证"""
        with pytest.raises(DomainError, match="主队和客队不能相同"):
            Match(home_team_id=100, away_team_id=100, league_id=10, season="2023-2024")

    def test_match_validation_season_format_valid(self) -> None:
        """✅ 成功用例：有效赛季格式"""
        # 单年格式
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023")
        assert match.season == "2023"

        # 跨年格式
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")
        assert match.season == "2023-2024"

        # 空赛季
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="")
        assert match.season == ""

    def test_match_validation_season_format_invalid(self) -> None:
        """✅ 边界用例：无效赛季格式"""
        # 非数字
        with pytest.raises(DomainError, match="赛季格式无效"):
            Match(home_team_id=1, away_team_id=2, league_id=10, season="abc")

        # 错误年份长度
        with pytest.raises(DomainError, match="赛季格式无效"):
            Match(home_team_id=1, away_team_id=2, league_id=10, season="202")

        # 错误跨年格式
        with pytest.raises(DomainError, match="赛季格式无效"):
            Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2025")

    def test_match_start_match_method(self) -> None:
        """✅ 成功用例：开始比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")
        original_updated = match.updated_at

        import time

        time.sleep(0.01)

        match.start_match()

        assert match.status == MatchStatus.LIVE
        assert match.updated_at > original_updated

    def test_match_start_match_invalid_status(self) -> None:
        """✅ 边界用例：无效状态开始比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")

        # 已开始
        match.status = MatchStatus.LIVE
        with pytest.raises(DomainError, match="比赛状态为 live，无法开始"):
            match.start_match()

        # 已结束
        match.status = MatchStatus.FINISHED
        with pytest.raises(DomainError, match="比赛状态为 finished，无法开始"):
            match.start_match()

        # 已取消
        match.status = MatchStatus.CANCELLED
        with pytest.raises(DomainError, match="比赛状态为 cancelled，无法开始"):
            match.start_match()

    def test_match_update_score_method(self) -> None:
        """✅ 成功用例：更新比分"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")
        original_updated = match.updated_at

        import time

        time.sleep(0.01)

        match.update_score(2, 1)

        assert match.score is not None
        assert match.score.home_score == 2
        assert match.score.away_score == 1
        assert match.updated_at > original_updated

    def test_match_update_score_zero_scores(self) -> None:
        """✅ 成功用例：零比分更新"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")

        match.update_score(0, 0)

        assert match.score is not None
        assert match.score.home_score == 0
        assert match.score.away_score == 0
        assert match.status == MatchStatus.SCHEDULED  # 0-0不应该改变状态

    def test_match_update_score_invalid_status(self) -> None:
        """✅ 边界用例：无效状态更新比分"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")

        # 已结束的比赛
        match.status = MatchStatus.FINISHED
        with pytest.raises(DomainError, match="只有进行中或已安排的比赛才能更新比分"):
            match.update_score(1, 0)

        # 已取消的比赛
        match.status = MatchStatus.CANCELLED
        with pytest.raises(DomainError, match="只有进行中或已安排的比赛才能更新比分"):
            match.update_score(1, 0)

    def test_match_finish_match_method(self) -> None:
        """✅ 成功用例：结束比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")

        # 先开始比赛并设置比分
        match.start_match()
        match.update_score(2, 1)

        original_updated = match.updated_at
        import time

        time.sleep(0.01)

        match.finish_match()

        assert match.status == MatchStatus.FINISHED
        assert match.updated_at > original_updated

    def test_match_finish_match_invalid_status(self) -> None:
        """✅ 边界用例：无效状态结束比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")

        # 未开始的比赛
        with pytest.raises(DomainError, match="只有进行中的比赛才能结束"):
            match.finish_match()

        # 已安排的比赛
        with pytest.raises(DomainError, match="只有进行中的比赛才能结束"):
            match.finish_match()

    def test_match_finish_match_no_score(self) -> None:
        """✅ 边界用例：无比分结束比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")

        match.start_match()

        with pytest.raises(DomainError, match="比赛必须要有比分才能结束"):
            match.finish_match()

    def test_match_cancel_match_method(self) -> None:
        """✅ 成功用例：取消比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")

        original_updated = match.updated_at
        import time

        time.sleep(0.01)

        match.cancel_match()

        assert match.status == MatchStatus.CANCELLED
        assert match.updated_at > original_updated

    def test_match_cancel_match_invalid_status(self) -> None:
        """✅ 边界用例：无效状态取消比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")

        # 已结束的比赛
        match.status = MatchStatus.FINISHED
        with pytest.raises(DomainError, match="已结束或已取消的比赛无法再次取消"):
            match.cancel_match()

        # 已取消的比赛
        match.status = MatchStatus.CANCELLED
        with pytest.raises(DomainError, match="已结束或已取消的比赛无法再次取消"):
            match.cancel_match()

    def test_match_postpone_match_method(self) -> None:
        """✅ 成功用例：延期比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")

        new_date = datetime(2023, 12, 31, 15, 0)
        original_updated = match.updated_at
        import time

        time.sleep(0.01)

        match.postpone_match(new_date)

        assert match.status == MatchStatus.POSTPONED
        assert match.match_date == new_date
        assert match.updated_at > original_updated

    def test_match_postpone_match_invalid_status(self) -> None:
        """✅ 边界用例：无效状态延期比赛"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")

        # 已结束的比赛
        match.status = MatchStatus.FINISHED
        with pytest.raises(DomainError, match="已结束或已取消的比赛无法延期"):
            match.postpone_match()

        # 已取消的比赛
        match.status = MatchStatus.CANCELLED
        with pytest.raises(DomainError, match="已结束或已取消的比赛无法延期"):
            match.postpone_match()

    def test_match_is_upcoming_property(self) -> None:
        """✅ 成功用例：即将到来的比赛属性"""
        # 未来比赛
        future_match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            season="2023-2024",
            match_date=datetime.utcnow() + timedelta(days=1),
        )
        assert future_match.is_upcoming is True

        # 过去比赛
        past_match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            season="2023-2024",
            match_date=datetime.utcnow() - timedelta(days=1),
        )
        assert past_match.is_upcoming is False

    def test_match_is_finished_property(self) -> None:
        """✅ 成功用例：已完成比赛属性"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")

        assert match.is_finished is False

        match.status = MatchStatus.FINISHED
        assert match.is_finished is True

    def test_match_can_predict_property(self) -> None:
        """✅ 成功用例：可预测属性"""
        # 已安排的比赛
        scheduled_match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            season="2023-2024",
            match_date=datetime.utcnow() + timedelta(hours=1),
        )
        assert scheduled_match.can_be_predicted is True

        # 已结束的比赛
        finished_match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            season="2023-2024",
            status=MatchStatus.FINISHED,
        )
        assert finished_match.can_be_predicted is False

        # 已取消的比赛
        cancelled_match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            season="2023-2024",
            status=MatchStatus.CANCELLED,
        )
        assert cancelled_match.can_be_predicted is False

    def test_match_days_until_property(self) -> None:
        """✅ 成功用例：距离比赛天数属性"""
        # 未来的比赛
        future_date = datetime.utcnow() + timedelta(days=5, hours=2)
        future_match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            season="2023-2024",
            match_date=future_date,
        )
        assert 4 <= future_match.days_until_match <= 5  # 允许小时差异

        # 过去的比赛
        past_date = datetime.utcnow() - timedelta(days=2)
        past_match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            season="2023-2024",
            match_date=past_date,
        )
        assert past_match.days_until_match == 0  # 过去比赛返回0

        # 无比赛日期
        no_date_match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")
        assert no_date_match.days_until_match == 0

    def test_match_duration_method(self) -> None:
        """✅ 成功用例：比赛持续时间方法"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")

        # 未开始的比赛
        duration = match.get_duration()
        assert duration is None

        # 已结束的比赛 - 返回标准90分钟
        match.status = MatchStatus.FINISHED
        duration = match.get_duration()
        assert duration == 90

        # 其他状态的比赛
        match.status = MatchStatus.SCHEDULED
        duration = match.get_duration()
        assert duration is None

        match.status = MatchStatus.LIVE
        duration = match.get_duration()
        assert duration is None

    def test_match_domain_events(self) -> None:
        """✅ 成功用例：领域事件"""
        match = Match(home_team_id=1, away_team_id=2, league_id=10, season="2023-2024")

        # 初始状态无事件
        assert len(match.get_domain_events()) == 0

        # 结束比赛应该触发事件
        match.start_match()
        match.update_score(2, 1)
        match.finish_match()

        events = match.get_domain_events()
        assert len(events) > 0

    def test_match_serialization(self) -> None:
        """✅ 成功用例：序列化"""
        match_date = datetime(2023, 6, 15, 18, 0)
        match = Match(
            id=1,
            home_team_id=100,
            away_team_id=200,
            league_id=10,
            season="2023-2024",
            match_date=match_date,
            status=MatchStatus.SCHEDULED,
            venue="Test Stadium",
        )

        # 设置比分但不改变状态（update_score可能会改变状态）
        match.score = MatchScore(home_score=2, away_score=1)

        data = match.to_dict()

        assert data["id"] == 1
        assert data["home_team_id"] == 100
        assert data["away_team_id"] == 200
        assert data["league_id"] == 10
        assert data["season"] == "2023-2024"
        assert data["status"] == MatchStatus.SCHEDULED.value
        assert data["venue"] == "Test Stadium"
        assert data["score"] is not None
        assert data["score"]["home_score"] == 2
        assert data["score"]["away_score"] == 1

    def test_match_edge_cases(self) -> None:
        """✅ 边界用例：边界条件测试"""
        # 极端日期
        extreme_date = datetime(2099, 12, 31, 23, 59, 59)
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            season="2099-2100",
            match_date=extreme_date,
        )
        assert match.match_date == extreme_date

        # 零观众
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            season="2023-2024",
            attendance=0,
        )
        assert match.attendance == 0

        # 极端观众数
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=10,
            season="2023-2024",
            attendance=1000000,
        )
        assert match.attendance == 1000000

    def test_match_comprehensive_workflow(self) -> None:
        """✅ 综合用例：完整比赛工作流"""
        # 创建未来比赛
        future_date = datetime.utcnow() + timedelta(days=1)
        match = Match(
            id=1,
            home_team_id=100,
            away_team_id=200,
            league_id=10,
            season="2023-2024",
            venue="Test Stadium",
            referee="Test Referee",
            match_date=future_date,
        )

        # 验证初始状态
        assert match.status == MatchStatus.SCHEDULED
        assert match.is_upcoming is True
        assert match.is_finished is False
        assert match.can_be_predicted is True

        # 开始比赛
        match.start_match()
        assert match.status == MatchStatus.LIVE
        assert match.is_upcoming is False
        assert match.is_finished is False
        assert match.can_be_predicted is True  # LIVE状态也可以预测

        # 更新比分
        match.update_score(2, 1)
        assert match.score is not None
        assert match.score.result == MatchResult.HOME_WIN

        # 结束比赛
        match.finish_match()
        assert match.status == MatchStatus.FINISHED
        assert match.is_finished is True
        assert match.can_be_predicted is False

        # 验证有领域事件产生
        events = match.get_domain_events()
        assert len(events) > 0

    def test_match_season_format_validation_comprehensive(self) -> None:
        """✅ 边界用例：赛季格式验证综合测试"""
        valid_seasons = ["2023", "2023-2024", "2024-2025", "1999", "1999-2000"]
        invalid_seasons = [
            "abc",
            "202",
            "20233",
            "2023-2025",
            "2022-2024",
            "2024-2023",
            "20-2024",
            "2023-202",
            "2023-20245",
        ]

        for season in valid_seasons:
            try:
                match = Match(home_team_id=1, away_team_id=2, league_id=10, season=season)
                assert match.season == season
            except DomainError:
                pytest.fail(f"Valid season '{season}' should not raise DomainError")

        for season in invalid_seasons:
            with pytest.raises(DomainError, match="赛季格式无效"):
                Match(home_team_id=1, away_team_id=2, league_id=10, season=season)

    def test_match_performance_considerations(self) -> None:
        """✅ 性能用例：性能考虑"""
        import time

        # 测试大量Match对象创建性能
        start_time = time.perf_counter()

        for i in range(1000):
            match = Match(home_team_id=i, away_team_id=i + 1, league_id=10, season="2023-2024")

        end_time = time.perf_counter()

        # 1000个Match对象创建应该在1秒内完成
        assert end_time - start_time < 1.0

    def test_match_thread_safety_considerations(self) -> None:
        """✅ 并发用例：线程安全考虑"""
        import threading

        results = []
        errors = []

        def create_match(match_id: int):
            try:
                match = Match(
                    home_team_id=match_id,
                    away_team_id=match_id + 1,
                    league_id=10,
                    season="2023-2024",
                )
                results.append(match.home_team_id)
            except Exception as e:
                errors.append(e)

        # 创建多个线程同时创建Match对象
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_match, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证没有错误
        assert len(errors) == 0
        assert len(results) == 10
