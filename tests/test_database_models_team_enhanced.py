"""
Team模型增强测试

专门针对src/database/models/team.py中未覆盖的代码路径进行测试，提升覆盖率从59%到80%+
主要覆盖：get_home_record, get_away_record, get_season_stats, get_recent_matches等方法
"""

from unittest.mock import Mock

from sqlalchemy.orm import Session


def create_mock_session():
    """创建模拟的数据库会话"""
    mock_session = Mock(spec=Session)
    mock_query = Mock()
    mock_session.query.return_value = mock_query
    return mock_session, mock_query


class TestTeamModelEnhancedCoverage:
    """测试Team模型未覆盖的方法"""

    def test_get_home_record(self):
        """测试获取主场战绩方法 (覆盖108-123行)"""
        from src.database.models.team import Team

        # 创建Team实例
        team = Team()
        team.id = 1
        team.team_name = "测试队伍"
        team.league_id = 1

        # 创建模拟会话
        mock_session, mock_query = create_mock_session()

        # 模拟查询链
        mock_filter_result = Mock()
        mock_query.filter.return_value = mock_filter_result

        # 模拟不同的过滤结果
        mock_wins_filter = Mock()
        mock_draws_filter = Mock()
        mock_losses_filter = Mock()

        mock_filter_result.filter.side_effect = [
            mock_wins_filter,  # 胜场过滤
            mock_draws_filter,  # 平局过滤
            mock_losses_filter,  # 负场过滤
        ]

        # 设置计数结果
        mock_wins_filter.count.return_value = 5
        mock_draws_filter.count.return_value = 3
        mock_losses_filter.count.return_value = 2

        # 执行测试
        result = team.get_home_record(mock_session)

        # 验证结果
        assert result["wins"] == 5
        assert result["draws"] == 3
        assert result["losses"] == 2
        assert result["total"] == 10

        # 验证查询被正确调用
        mock_session.query.assert_called_once()
        assert mock_query.filter.call_count == 1
        assert mock_filter_result.filter.call_count == 3

    def test_get_away_record(self):
        """测试获取客场战绩方法 (覆盖125-142行)"""
        from src.database.models.team import Team

        # 创建Team实例
        team = Team()
        team.id = 2
        team.team_name = "客队"
        team.league_id = 1

        # 创建模拟会话
        mock_session, mock_query = create_mock_session()

        # 模拟查询链
        mock_filter_result = Mock()
        mock_query.filter.return_value = mock_filter_result

        # 模拟不同的过滤结果
        mock_wins_filter = Mock()
        mock_draws_filter = Mock()
        mock_losses_filter = Mock()

        mock_filter_result.filter.side_effect = [
            mock_wins_filter,
            mock_draws_filter,
            mock_losses_filter,
        ]

        # 设置计数结果 (客场战绩较差)
        mock_wins_filter.count.return_value = 2
        mock_draws_filter.count.return_value = 4
        mock_losses_filter.count.return_value = 6

        # 执行测试
        result = team.get_away_record(mock_session)

        # 验证结果
        assert result["wins"] == 2
        assert result["draws"] == 4
        assert result["losses"] == 6
        assert result["total"] == 12

    def test_get_season_stats(self):
        """测试获取赛季统计方法 (覆盖144-180行)"""
        from src.database.models.team import Team

        team = Team()
        team.id = 1
        team.team_name = "队伍A"
        team.league_id = 1

        # 创建模拟会话
        mock_session, mock_query = create_mock_session()

        # 创建模拟比赛数据
        mock_match1 = Mock()
        mock_match1.home_team_id = 1  # 主场比赛
        mock_match1.away_team_id = 2
        mock_match1.home_score = 2
        mock_match1.away_score = 1

        mock_match2 = Mock()
        mock_match2.home_team_id = 3
        mock_match2.away_team_id = 1  # 客场比赛
        mock_match2.home_score = 0
        mock_match2.away_score = 3

        mock_match3 = Mock()
        mock_match3.home_team_id = 1  # 主场平局
        mock_match3.away_team_id = 4
        mock_match3.home_score = 1
        mock_match3.away_score = 1

        mock_matches = [mock_match1, mock_match2, mock_match3]

        # 设置查询返回
        mock_query.filter.return_value.all.return_value = mock_matches

        # 执行测试
        result = team.get_season_stats(mock_session, "2023-24")

        # 验证结果
        assert result["matches_played"] == 3
        assert result["wins"] == 2  # 一场主场胜利 + 一场客场胜利
        assert result["draws"] == 1  # 一场主场平局
        assert result["losses"] == 0
        assert result["goals_for"] == 6  # 2+3+1
        assert result["goals_against"] == 2  # 1+0+1
        assert result["points"] == 7  # 2*3 + 1*1
        assert result["goal_difference"] == 4  # 6-2

    def test_get_recent_matches_with_limit(self):
        """测试获取最近比赛方法 (覆盖88-103行)"""
        from src.database.models.team import Team

        team = Team()
        team.id = 1
        team.team_name = "测试队"
        team.league_id = 1

        # 创建模拟会话
        mock_session, mock_query = create_mock_session()

        # 创建模拟比赛数据
        mock_matches = [Mock(), Mock(), Mock()]
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
            mock_matches
        )

        # 执行测试
        result = team.get_recent_matches(mock_session, limit=5)

        # 验证结果
        assert result == mock_matches
        mock_query.filter.return_value.order_by.return_value.limit.assert_called_with(5)

    def test_get_recent_matches_without_limit(self):
        """测试获取最近比赛方法 (默认限制版本)"""
        from src.database.models.team import Team

        team = Team()
        team.id = 1
        team.team_name = "测试队"
        team.league_id = 1

        # 创建模拟会话
        mock_session, mock_query = create_mock_session()

        # 创建模拟比赛数据
        mock_matches = [Mock(), Mock()]
        mock_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
            mock_matches
        )

        # 执行测试 (使用默认limit=5)
        result = team.get_recent_matches(mock_session)

        # 验证结果
        assert result == mock_matches
        mock_query.filter.return_value.order_by.return_value.limit.assert_called_with(5)

    def test_process_home_match(self):
        """测试处理主场比赛统计方法 (覆盖182-192行)"""
        from src.database.models.team import Team

        team = Team()
        team.id = 1

        # 创建模拟比赛数据
        mock_match_win = Mock()
        mock_match_win.home_score = 3
        mock_match_win.away_score = 1

        mock_match_draw = Mock()
        mock_match_draw.home_score = 2
        mock_match_draw.away_score = 2

        mock_match_loss = Mock()
        mock_match_loss.home_score = 0
        mock_match_loss.away_score = 1

        # 测试胜利情况
        stats_win = {
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
        }
        team._process_home_match(mock_match_win, stats_win)
        assert stats_win["wins"] == 1
        assert stats_win["goals_for"] == 3
        assert stats_win["goals_against"] == 1

        # 测试平局情况
        stats_draw = {
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
        }
        team._process_home_match(mock_match_draw, stats_draw)
        assert stats_draw["draws"] == 1
        assert stats_draw["goals_for"] == 2
        assert stats_draw["goals_against"] == 2

        # 测试失败情况
        stats_loss = {
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
        }
        team._process_home_match(mock_match_loss, stats_loss)
        assert stats_loss["losses"] == 1
        assert stats_loss["goals_for"] == 0
        assert stats_loss["goals_against"] == 1

    def test_process_away_match(self):
        """测试处理客场比赛统计方法 (覆盖194-204行)"""
        from src.database.models.team import Team

        team = Team()
        team.id = 1

        # 创建模拟比赛数据
        mock_match_win = Mock()
        mock_match_win.home_score = 1  # 对方主场得分
        mock_match_win.away_score = 3  # 我方客场得分

        mock_match_draw = Mock()
        mock_match_draw.home_score = 2
        mock_match_draw.away_score = 2

        mock_match_loss = Mock()
        mock_match_loss.home_score = 2
        mock_match_loss.away_score = 0

        # 测试客场胜利情况
        stats_win = {
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
        }
        team._process_away_match(mock_match_win, stats_win)
        assert stats_win["wins"] == 1
        assert stats_win["goals_for"] == 3  # away_score
        assert stats_win["goals_against"] == 1  # home_score

        # 测试客场平局情况
        stats_draw = {
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
        }
        team._process_away_match(mock_match_draw, stats_draw)
        assert stats_draw["draws"] == 1
        assert stats_draw["goals_for"] == 2
        assert stats_draw["goals_against"] == 2

        # 测试客场失败情况
        stats_loss = {
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
        }
        team._process_away_match(mock_match_loss, stats_loss)
        assert stats_loss["losses"] == 1
        assert stats_loss["goals_for"] == 0
        assert stats_loss["goals_against"] == 2

    def test_get_by_code_classmethod(self):
        """测试根据球队代码获取球队的类方法 (覆盖207-209行)"""
        from src.database.models.team import Team

        # 创建模拟会话
        mock_session, mock_query = create_mock_session()

        # 模拟查询结果
        mock_team = Mock()
        mock_query.filter.return_value.first.return_value = mock_team

        # 执行测试
        result = Team.get_by_code(mock_session, "MAN")

        # 验证结果
        assert result == mock_team
        mock_session.query.assert_called_with(Team)
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.first.assert_called_once()

    def test_get_by_league_classmethod(self):
        """测试获取指定联赛球队的类方法 (覆盖212-214行)"""
        from src.database.models.team import Team

        # 创建模拟会话
        mock_session, mock_query = create_mock_session()

        # 模拟查询结果
        mock_teams = [Mock(), Mock(), Mock()]
        mock_query.filter.return_value.all.return_value = mock_teams

        # 执行测试
        result = Team.get_by_league(mock_session, league_id=1)

        # 验证结果
        assert result == mock_teams
        mock_session.query.assert_called_with(Team)
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.all.assert_called_once()

    def test_get_active_teams_classmethod(self):
        """测试获取所有活跃球队的类方法 (覆盖217-219行)"""
        from src.database.models.team import Team

        # 创建模拟会话
        mock_session, mock_query = create_mock_session()

        # 模拟查询结果
        mock_active_teams = [Mock(), Mock()]
        mock_query.filter.return_value.all.return_value = mock_active_teams

        # 执行测试
        result = Team.get_active_teams(mock_session)

        # 验证结果
        assert result == mock_active_teams
        mock_session.query.assert_called_with(Team)
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.all.assert_called_once()
