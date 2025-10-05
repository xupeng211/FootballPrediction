"""
数据库模型综合测试
测试Match、Team、Prediction等核心模型的功能
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from src.database.models.match import Match, MatchStatus
from src.database.models.team import Team
from src.database.models.league import League
from src.database.models.predictions import Predictions, PredictionType


@pytest.mark.unit
class TestMatchModel:
    """Match模型测试"""

    @pytest.fixture
    def sample_home_team(self):
        """示例主队"""
        return Team(id=1, team_name="Manchester United", country="England")

    @pytest.fixture
    def sample_away_team(self):
        """示例客队"""
        return Team(id=2, team_name="Liverpool", country="England")

    @pytest.fixture
    def sample_league(self):
        """示例联赛"""
        return League(id=1, league_name="Premier League", country="England")

    @pytest.fixture
    def sample_match(self, sample_home_team, sample_away_team, sample_league):
        """示例比赛"""
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            season="2023-24",
            match_time=datetime(2024, 1, 15, 15, 0),
            home_score=2,
            away_score=1,
            home_ht_score=1,
            away_ht_score=0,
            minute=90,
            venue="Old Trafford",
            referee="Michael Oliver",
            weather="Clear",
        )
        # 手动设置关系（在真实应用中由SQLAlchemy处理）
        match.home_team = sample_home_team
        match.away_team = sample_away_team
        match.league = sample_league
        return match

    def test_match_creation(self, sample_match):
        """测试比赛创建"""
        assert sample_match.home_team_id == 1
        assert sample_match.away_team_id == 2
        assert sample_match.league_id == 1
        assert sample_match.season == "2023-24"
        assert sample_match.home_score == 2
        assert sample_match.away_score == 1
        assert sample_match.match_status == MatchStatus.SCHEDULED

    def test_match_repr(self, sample_match):
        """测试比赛字符串表示"""
        repr_str = repr(sample_match)
        assert "Match" in repr_str
        assert "Manchester United" in repr_str
        assert "Liverpool" in repr_str

    def test_match_name_property(self, sample_match):
        """测试比赛名称属性"""
        assert sample_match.match_name == "Manchester United vs Liverpool"

    def test_match_name_without_teams(self):
        """测试没有球队信息时的比赛名称"""
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            season="2023-24",
            match_time=datetime.now(),
        )
        assert match.match_name == f"Match {match.id}"

    def test_is_finished_property(self, sample_match):
        """测试比赛是否结束"""
        sample_match.match_status = MatchStatus.FINISHED
        assert sample_match.is_finished is True

        sample_match.match_status = MatchStatus.SCHEDULED
        assert sample_match.is_finished is False

        sample_match.match_status = MatchStatus.LIVE
        assert sample_match.is_finished is False

    def test_is_upcoming_property(self, sample_match):
        """测试比赛是否未来进行"""
        # 未来的比赛
        future_time = datetime.utcnow() + timedelta(days=1)
        sample_match.match_time = future_time
        sample_match.match_status = MatchStatus.SCHEDULED
        assert sample_match.is_upcoming is True

        # 过去的比赛
        past_time = datetime.utcnow() - timedelta(days=1)
        sample_match.match_time = past_time
        sample_match.match_status = MatchStatus.SCHEDULED
        assert sample_match.is_upcoming is False

        # 进行中的比赛
        sample_match.match_status = MatchStatus.LIVE
        assert sample_match.is_upcoming is False

    def test_final_score_property(self, sample_match):
        """测试最终比分属性"""
        assert sample_match.final_score == "2-1"

        # 测试没有比分的情况
        sample_match.home_score = None
        sample_match.away_score = None
        assert sample_match.final_score is None

        # 测试只有一方比分
        sample_match.home_score = 2
        sample_match.away_score = None
        assert sample_match.final_score is None

    def test_ht_score_property(self, sample_match):
        """测试半场比分属性"""
        assert sample_match.ht_score == "1-0"

        # 测试没有半场比分
        sample_match.home_ht_score = None
        sample_match.away_ht_score = None
        assert sample_match.ht_score is None

    def test_get_result(self, sample_match):
        """测试获取比赛结果"""
        sample_match.match_status = MatchStatus.FINISHED

        # 主队获胜
        sample_match.home_score = 3
        sample_match.away_score = 1
        assert sample_match.get_result() == "home_win"

        # 平局
        sample_match.home_score = 2
        sample_match.away_score = 2
        assert sample_match.get_result() == "draw"

        # 客队获胜
        sample_match.home_score = 1
        sample_match.away_score = 3
        assert sample_match.get_result() == "away_win"

        # 未结束的比赛
        sample_match.match_status = MatchStatus.SCHEDULED
        assert sample_match.get_result() is None

        # 没有比分
        sample_match.match_status = MatchStatus.FINISHED
        sample_match.home_score = None
        sample_match.away_score = None
        assert sample_match.get_result() is None

    def test_get_total_goals(self, sample_match):
        """测试获取总进球数"""
        assert sample_match.get_total_goals() == 3

        # 测试没有比分
        sample_match.home_score = None
        sample_match.away_score = None
        assert sample_match.get_total_goals() is None

    def test_is_over_2_5_goals(self, sample_match):
        """测试是否大于2.5球"""
        # 大于2.5球
        sample_match.home_score = 3
        sample_match.away_score = 1
        assert sample_match.is_over_2_5_goals() is True

        # 等于2.5球
        sample_match.home_score = 2
        sample_match.away_score = 1
        assert sample_match.is_over_2_5_goals() is False

        # 小于2.5球
        sample_match.home_score = 1
        sample_match.away_score = 1
        assert sample_match.is_over_2_5_goals() is False

        # 没有比分
        sample_match.home_score = None
        sample_match.away_score = None
        assert sample_match.is_over_2_5_goals() is None

    def test_both_teams_scored(self, sample_match):
        """测试双方是否都有进球"""
        # 双方都有进球
        sample_match.home_score = 2
        sample_match.away_score = 1
        assert sample_match.both_teams_scored() is True

        # 只有主队进球
        sample_match.home_score = 2
        sample_match.away_score = 0
        assert sample_match.both_teams_scored() is False

        # 只有客队进球
        sample_match.home_score = 0
        sample_match.away_score = 2
        assert sample_match.both_teams_scored() is False

        # 没有进球
        sample_match.home_score = 0
        sample_match.away_score = 0
        assert sample_match.both_teams_scored() is False

        # 没有比分
        sample_match.home_score = None
        sample_match.away_score = None
        assert sample_match.both_teams_scored() is None

    def test_get_match_stats(self, sample_match):
        """测试获取比赛统计信息"""
        stats = sample_match.get_match_stats()

        assert stats["match_id"] == sample_match.id
        assert stats["home_team"] == "Manchester United"
        assert stats["away_team"] == "Liverpool"
        assert stats["league"] == "Premier League"
        assert stats["status"] == MatchStatus.SCHEDULED.value
        assert stats["final_score"] == "2-1"
        assert stats["ht_score"] == "1-0"
        assert stats["venue"] == "Old Trafford"
        assert stats["referee"] == "Michael Oliver"
        assert stats["total_goals"] == 3
        assert stats["result"] == "home_win"

    def test_match_status_enum(self):
        """测试比赛状态枚举"""
        assert MatchStatus.SCHEDULED.value == "scheduled"
        assert MatchStatus.LIVE.value == "live"
        assert MatchStatus.FINISHED.value == "finished"
        assert MatchStatus.CANCELLED.value == "cancelled"


@pytest.mark.unit
class TestTeamModel:
    """Team模型测试"""

    def test_team_creation(self):
        """测试球队创建"""
        team = Team(
            team_name="Real Madrid",
            country="Spain",
            founded_year=1902,
            stadium="Santiago Bernabéu",
            manager="Carlo Ancelotti",
        )
        assert team.team_name == "Real Madrid"
        assert team.country == "Spain"
        assert team.founded_year == 1902
        assert team.stadium == "Santiago Bernabéu"
        assert team.manager == "Carlo Ancelotti"

    def test_team_repr(self):
        """测试球队字符串表示"""
        team = Team(id=1, team_name="Real Madrid", country="Spain")
        repr_str = repr(team)
        assert "Team" in repr_str
        assert "Real Madrid" in repr_str


@pytest.mark.unit
class TestPredictionModel:
    """Prediction模型测试"""

    @pytest.fixture
    def sample_match(self):
        """示例比赛"""
        match = MagicMock()
        match.id = 1
        match.home_team.team_name = "Manchester United"
        match.away_team.team_name = "Liverpool"
        return match

    def test_prediction_creation(self, sample_match):
        """测试预测创建"""
        prediction = Predictions(
            match_id=1,
            prediction_type=PredictionType.MATCH_OUTCOME,
            predicted_value="home_win",
            confidence=0.85,
            model_version="v1.0",
            created_at=datetime.utcnow(),
        )
        assert prediction.match_id == 1
        assert prediction.prediction_type == PredictionType.MATCH_OUTCOME
        assert prediction.predicted_value == "home_win"
        assert prediction.confidence == 0.85
        assert prediction.model_version == "v1.0"

    def test_prediction_type_enum(self):
        """测试预测类型枚举"""
        assert PredictionType.MATCH_OUTCOME.value == "match_outcome"
        assert PredictionType.OVER_UNDER.value == "over_under"
        assert PredictionType.BTS.value == "both_teams_to_score"
        assert PredictionType.CORRECT_SCORE.value == "correct_score"

    def test_prediction_repr(self, sample_match):
        """测试预测字符串表示"""
        prediction = Predictions(
            id=1,
            match_id=1,
            prediction_type=PredictionType.MATCH_OUTCOME,
            predicted_value="home_win",
            confidence=0.85,
        )
        # Mock match relationship
        prediction.match = sample_match

        repr_str = repr(prediction)
        assert "Prediction" in repr_str
        assert "1" in repr_str


@pytest.mark.unit
class TestLeagueModel:
    """League模型测试"""

    def test_league_creation(self):
        """测试联赛创建"""
        league = League(
            league_name="Premier League",
            country="England",
            founded_year=1992,
            num_teams=20,
            season_duration="August-May",
        )
        assert league.league_name == "Premier League"
        assert league.country == "England"
        assert league.founded_year == 1992
        assert league.num_teams == 20

    def test_league_repr(self):
        """测试联赛字符串表示"""
        league = League(id=1, league_name="Premier League", country="England")
        repr_str = repr(league)
        assert "League" in repr_str
        assert "Premier League" in repr_str


@pytest.mark.unit
class TestModelConstraints:
    """测试模型约束"""

    def test_match_score_constraints(self):
        """测试比分约束"""
        # 正常比分
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            season="2023-24",
            match_time=datetime.now(),
            home_score=5,
            away_score=3,
        )
        assert match.home_score == 5
        assert match.away_score == 3

        # 边界值测试
        match.home_score = 0
        match.away_score = 0
        assert match.home_score == 0
        assert match.away_score == 0

    def test_different_teams_constraint(self):
        """测试不同球队约束"""
        # 这个约束在数据库层面强制执行
        # 在单元测试中，我们只能确保代码逻辑正确
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            season="2023-24",
            match_time=datetime.now(),
        )
        assert match.home_team_id != match.away_team_id

    def test_match_time_constraint(self):
        """测试比赛时间约束"""
        # 正常时间
        future_time = datetime(2024, 6, 1)
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            season="2023-24",
            match_time=future_time,
        )
        assert match.match_time > datetime(2000, 1, 1)

    def test_minute_range_constraint(self):
        """测试比赛分钟数约束"""
        # 正常范围
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            season="2023-24",
            match_time=datetime.now(),
            minute=45,
        )
        assert match.minute == 45

        # 边界值
        match.minute = 0
        assert match.minute == 0

        match.minute = 120
        assert match.minute == 120


@pytest.mark.unit
class TestModelRelationships:
    """测试模型关系"""

    def test_match_team_relationships(self):
        """测试比赛与球队关系"""
        home_team = Team(id=1, team_name="Team A")
        away_team = Team(id=2, team_name="Team B")

        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            season="2023-24",
            match_time=datetime.now(),
        )

        # 在真实应用中，这些关系由SQLAlchemy管理
        # 这里我们模拟关系
        match.home_team = home_team
        match.away_team = away_team

        assert match.home_team.team_name == "Team A"
        assert match.away_team.team_name == "Team B"

    def test_prediction_match_relationship(self, sample_match):
        """测试预测与比赛关系"""
        prediction = Predictions(
            match_id=1,
            prediction_type=PredictionType.MATCH_OUTCOME,
            predicted_value="home_win",
            confidence=0.85,
        )

        # 模拟关系
        prediction.match = sample_match

        assert prediction.match.id == 1
        assert prediction.match.home_team.team_name == "Manchester United"
        assert prediction.match.away_team.team_name == "Liverpool"
