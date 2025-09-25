import pytest

from datetime import datetime
from unittest.mock import Mock, patch

pytestmark = pytest.mark.unit

from sqlalchemy.orm import Session

from src.database.models.match import Match, MatchStatus


class TestMatchModelEnhancedCoverage:
    """测试Match模型未覆盖的方法和边界情况"""

    def test_match_name_property_without_teams(self):
        """测试match_name属性 - 无球队信息的情况 (覆盖150行)"""
        from src.database.models.match import Match

        # 创建没有球队信息的Match实例
        match = Match()
        match.id = 123
        match.home_team = None
        match.away_team = None

        # 执行测试
        result = match.match_name

        # 验证返回格式正确
        assert result == "Match 123"

    def test_get_result_with_none_scores(self):
        """测试get_result方法 - 比分为None的情况 (覆盖187行)"""
        from src.database.models.match import Match, MatchStatus

        # 创建比赛但没有比分
        match = Match()
        match.match_status = MatchStatus.FINISHED  # 已结束
        match.home_score = None  # 主队比分为None
        match.away_score = 2

        # 执行测试
        result = match.get_result()

        # 验证返回None（因为有比分缺失）
        assert result is None

    def test_get_result_with_unfinished_match(self):
        """测试get_result方法 - 比赛未结束的情况"""

        # 创建未结束的比赛
        match = Match()
        match.match_status = MatchStatus.SCHEDULED  # 未开始
        match.home_score = 2
        match.away_score = 1

        # 执行测试
        result = match.get_result()

        # 验证返回None（因为比赛未结束）
        assert result is None

    def test_is_over_2_5_goals_with_none_scores(self):
        """测试is_over_2_5_goals方法 - 比分为None的情况 (覆盖207行)"""

        # 创建比分缺失的比赛
        match = Match()
        match.home_score = None
        match.away_score = 2

        # 执行测试
        result = match.is_over_2_5_goals()

        # 验证返回None
        assert result is None

    def test_both_teams_scored_with_none_scores(self):
        """测试both_teams_scored方法 - 比分为None的情况 (覆盖213行)"""

        # 创建比分缺失的比赛
        match = Match()
        match.home_score = 1
        match.away_score = None  # 客队比分为None

        # 执行测试
        result = match.both_teams_scored()

        # 验证返回None
        assert result is None

    def test_get_upcoming_matches_classmethod(self):
        """测试get_upcoming_matches类方法 (覆盖275-280行)"""

        # 创建模拟会话
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        mock_session.query.return_value = mock_query

        # 设置查询链
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_upcoming_matches = [Mock(), Mock()]
        mock_query.all.return_value = mock_upcoming_matches

        # 执行测试
        with patch("src.database.models.match.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 15, 12, 0, 0)

            result = Match.get_upcoming_matches(mock_session, days=7)

        # 验证查询被正确调用
        mock_session.query.assert_called_once_with(Match)
        mock_query.filter.assert_called_once()
        mock_query.order_by.assert_called_once()
        mock_query.all.assert_called_once()

        # 验证返回结果
        assert result == mock_upcoming_matches

    def test_get_finished_matches_with_league_filter(self):
        """测试get_finished_matches类方法 - 带联赛过滤 (覆盖295-302行)"""

        # 创建模拟会话
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        mock_session.query.return_value = mock_query

        # 设置查询链
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_finished_matches = [Mock(), Mock(), Mock()]
        mock_query.all.return_value = mock_finished_matches

        # 执行测试 - 带联赛ID和赛季过滤
        result = Match.get_finished_matches(
            mock_session, league_id=123, season="2023-24"
        )

        # 验证查询被正确调用
        mock_session.query.assert_called_once_with(Match)
        assert mock_query.filter.call_count == 3  # status + league_id + season
        mock_query.order_by.assert_called_once()
        mock_query.all.assert_called_once()

        # 验证返回结果
        assert result == mock_finished_matches

    def test_get_finished_matches_no_filters(self):
        """测试get_finished_matches类方法 - 无过滤条件"""

        # 创建模拟会话
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        mock_session.query.return_value = mock_query

        # 设置查询链
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_finished_matches = [Mock()]
        mock_query.all.return_value = mock_finished_matches

        # 执行测试 - 不带过滤条件
        result = Match.get_finished_matches(mock_session)

        # 验证只过滤了状态
        mock_session.query.assert_called_once_with(Match)
        assert mock_query.filter.call_count == 1  # 只有status过滤
        mock_query.order_by.assert_called_once()

        # 验证返回结果
        assert result == mock_finished_matches

    def test_get_team_matches_with_season_filter(self):
        """测试get_team_matches类方法 - 带赛季过滤 (覆盖307-316行)"""

        # 创建模拟会话
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        mock_session.query.return_value = mock_query

        # 设置查询链
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_team_matches = [Mock(), Mock()]
        mock_query.all.return_value = mock_team_matches

        # 执行测试 - 带赛季过滤
        result = Match.get_team_matches(mock_session, team_id=456, season="2023-24")

        # 验证查询被正确调用
        mock_session.query.assert_called_once_with(Match)
        assert mock_query.filter.call_count == 2  # team filter + season filter
        mock_query.order_by.assert_called_once()
        mock_query.all.assert_called_once()

        # 验证返回结果
        assert result == mock_team_matches

    def test_get_team_matches_no_season_filter(self):
        """测试get_team_matches类方法 - 无赛季过滤"""

        # 创建模拟会话
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        mock_session.query.return_value = mock_query

        # 设置查询链
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_team_matches = [Mock()]
        mock_query.all.return_value = mock_team_matches

        # 执行测试 - 不带赛季过滤
        result = Match.get_team_matches(mock_session, team_id=456)

        # 验证只过滤了球队
        mock_session.query.assert_called_once_with(Match)
        assert mock_query.filter.call_count == 1  # 只有team过滤
        mock_query.order_by.assert_called_once()

        # 验证返回结果
        assert result == mock_team_matches

    def test_get_match_stats_with_none_teams(self):
        """测试get_match_stats方法 - 球队为None的情况 (覆盖可能的262行)"""

        # 创建没有关联球队和联赛的比赛
        match = Match()
        match.id = 123
        match.home_team = None  # 主队为None
        match.away_team = None  # 客队为None
        match.league = None  # 联赛为None
        match.home_score = 2
        match.away_score = 1
        match.match_status = MatchStatus.FINISHED
        match.match_time = datetime(2024, 1, 15)

        # 执行测试
        result = match.get_match_stats()

        # 验证统计信息包含None值
        assert result["match_id"] == 123
        assert result["home_team"] is None
        assert result["away_team"] is None
        assert result["league"] is None
        assert result["status"] == "finished"
        assert result["result"] == "home_win"  # 基于比分计算

    def test_complex_match_scenarios(self):
        """测试复杂的比赛场景组合"""

        # 测试各种边界情况的组合
        # 情况1: 比赛进行中，部分数据缺失
        match1 = Match()
        match1.match_status = MatchStatus.LIVE
        match1.home_score = None
        match1.away_score = None

        assert match1.get_result() is None
        assert match1.get_total_goals() is None
        assert match1.is_over_2_5_goals() is None
        assert match1.both_teams_scored() is None

        # 情况2: 已结束，0-0平局
        match2 = Match()
        match2.match_status = MatchStatus.FINISHED
        match2.home_score = 0
        match2.away_score = 0

        assert match2.get_result() == "draw"
        assert match2.get_total_goals() == 0
        assert match2.is_over_2_5_goals() is False
        assert match2.both_teams_scored() is False

        # 情况3: 高比分比赛
        match3 = Match()
        match3.match_status = MatchStatus.FINISHED
        match3.home_score = 4
        match3.away_score = 3

        assert match3.get_result() == "home_win"
        assert match3.get_total_goals() == 7
        assert match3.is_over_2_5_goals() is True
        assert match3.both_teams_scored() is True

    def test_match_time_edge_cases(self):
        """测试match_time相关的边界情况"""

        # 创建模拟会话用于测试时间相关查询
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        # 测试边界时间情况
        with patch("src.database.models.match.datetime") as mock_datetime:
            # 测试跨月查询
            mock_datetime.utcnow.return_value = datetime(2024, 1, 31, 23, 59, 59)

            result = Match.get_upcoming_matches(mock_session, days=5)

            # 验证查询被调用
            mock_session.query.assert_called_with(Match)
            assert result == []

    def test_match_status_edge_cases(self):
        """测试不同match_status的边界情况"""

        # 测试所有可能的状态组合
        statuses_to_test = [
            MatchStatus.SCHEDULED,
            MatchStatus.LIVE,
            MatchStatus.FINISHED,
            MatchStatus.CANCELLED,
        ]

        for status in statuses_to_test:
            match = Match()
            match.match_status = status
            match.home_score = 1
            match.away_score = 0

            # 只有FINISHED状态才能获取结果
            if status == MatchStatus.FINISHED:
                assert match.get_result() == "home_win"
                assert match.is_finished is True
            else:
                assert match.get_result() is None
                assert match.is_finished is False
