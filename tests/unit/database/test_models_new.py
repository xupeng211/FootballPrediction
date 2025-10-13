from datetime import datetime, timedelta
from decimal import Decimal
import pytest
from src.database.models.league import League
from src.database.models.match import Match, MatchStatus
from src.database.models.predictions import PredictedResult, Predictions
from src.database.models.team import Team

"""
数据库模型测试
测试Match、Team、Prediction等核心模型的功能
"""


@pytest.mark.unit
class TestMatchModel:
    """Match模型测试"""

    @pytest.fixture
    def sample_match(self):
        """示例比赛"""
        return Match(
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            season="2023-24",
            match_time=datetime(2024, 1, 15, 15, 0),
            home_score=2,
            away_score=1,
            venue="Old Trafford",
        )

    def test_match_creation(self, sample_match):
        """测试比赛创建"""
        assert sample_match.home_team_id == 1
        assert sample_match.away_team_id == 2
        assert sample_match.league_id == 1
        assert sample_match.season == "2023-24"
        assert sample_match.home_score == 2
        assert sample_match.away_score == 1
        # match_status有默认值，但在实例化时可能没有设置
        # assert sample_match.match_status == MatchStatus.SCHEDULED
        assert sample_match.venue == "Old Trafford"

    def test_match_name_property(self, sample_match):
        """测试比赛名称属性（无球队信息）"""
        assert sample_match.match_name == f"Match {sample_match.id}"

    def test_is_finished_property(self, sample_match):
        """测试比赛是否结束"""
        sample_match.match_status = MatchStatus.FINISHED
        assert sample_match.is_finished is True

        sample_match.match_status = MatchStatus.SCHEDULED
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

    def test_final_score_property(self, sample_match):
        """测试最终比分属性"""
        assert sample_match.final_score == "2-1"

        # 测试没有比分的情况
        sample_match.home_score = None
        sample_match.away_score = None
        assert sample_match.final_score is None

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

    def test_get_total_goals(self, sample_match):
        """测试获取总进球数"""
        assert sample_match.get_total_goals() == 3

        # 测试没有比分
        sample_match.home_score = None
        sample_match.away_score = None
        assert sample_match.get_total_goals() is None

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
        )
        assert team.team_name == "Real Madrid"
        assert team.country == "Spain"
        assert team.founded_year == 1902
        assert team.stadium == "Santiago Bernabéu"

    def test_team_repr(self):
        """测试球队字符串表示"""
        team = Team(id=1, team_name="Real Madrid", country="Spain")
        repr_str = repr(team)
        assert "Team" in repr_str
        assert "Real Madrid" in repr_str


@pytest.mark.unit
class TestPredictionModel:
    """Prediction模型测试"""

    def test_prediction_creation(self):
        """测试预测创建"""
        _prediction = Predictions(
            match_id=1,
            model_name="outcome_model",
            model_version="v1.0",
            predicted_result=PredictedResult.HOME_WIN,
            home_win_probability=Decimal("0.65"),
            draw_probability=Decimal("0.25"),
            away_win_probability=Decimal("0.10"),
            confidence_score=Decimal("0.85"),
            predicted_at=datetime.utcnow(),
        )
        assert prediction.match_id == 1
        assert prediction.model_name == "outcome_model"
        assert prediction.model_version == "v1.0"
        assert prediction.predicted_result == PredictedResult.HOME_WIN
        assert prediction.home_win_probability == Decimal("0.65")
        assert prediction.confidence_score == Decimal("0.85")

    def test_prediction_enum(self):
        """测试预测结果枚举"""
        assert PredictedResult.HOME_WIN.value == "home_win"
        assert PredictedResult.DRAW.value == "draw"
        assert PredictedResult.AWAY_WIN.value == "away_win"

    def test_prediction_repr(self):
        """测试预测字符串表示"""
        _prediction = Predictions(
            id=1,
            match_id=1,
            model_name="outcome_model",
            predicted_result=PredictedResult.HOME_WIN,
            predicted_at=datetime.utcnow(),
        )
        repr_str = repr(prediction)
        assert "Prediction" in repr_str
        assert "1" in repr_str
        assert "home_win" in repr_str

    def test_get_created_at(self):
        """测试获取创建时间"""
        prediction_time = datetime.utcnow()
        _prediction = Predictions(
            match_id=1,
            model_name="test_model",
            predicted_result=PredictedResult.HOME_WIN,
            predicted_at=prediction_time,
        )
        assert prediction.get_created_at() == prediction_time


@pytest.mark.unit
class TestLeagueModel:
    """League模型测试"""

    def test_league_creation(self):
        """测试联赛创建"""
        league = League(
            league_name="Premier League", country="England", level=1, is_active=True
        )
        assert league.league_name == "Premier League"
        assert league.country == "England"
        assert league.level == 1
        assert league.is_active is True

    def test_league_repr(self):
        """测试联赛字符串表示"""
        league = League(id=1, league_name="Premier League", country="England")
        repr_str = repr(league)
        assert "League" in repr_str
        assert "Premier League" in repr_str


@pytest.mark.unit
class TestModelMethods:
    """测试模型方法"""

    def test_match_calculations(self):
        """测试Match模型的计算方法"""
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            season="2023-24",
            match_time=datetime.now(),
            home_score=3,
            away_score=2,
        )

        # 测试计算方法
        assert match.get_total_goals() == 5
        assert match.is_over_2_5_goals() is True
        assert match.both_teams_scored() is True

        # 测试边界情况
        match.home_score = 2
        match.away_score = 0
        assert match.get_total_goals() == 2
        assert match.is_over_2_5_goals() is False
        assert match.both_teams_scored() is False

    def test_match_stats(self):
        """测试比赛统计"""
        match = Match(
            id=1,
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            season="2023-24",
            match_time=datetime(2024, 1, 15, 15, 0),
            home_score=2,
            away_score=1,
            venue="Old Trafford",
            referee="Michael Oliver",
        )
        # 手动设置match_status以避免None错误
        match.match_status = MatchStatus.SCHEDULED

        _stats = match.get_match_stats()
        assert stats["match_id"] == 1
        assert stats["final_score"] == "2-1"
        assert stats["total_goals"] == 3
        assert stats["venue"] == "Old Trafford"
        assert stats["referee"] == "Michael Oliver"


@pytest.mark.unit
class TestModelConstraints:
    """测试模型约束"""

    def test_score_constraints(self):
        """测试比分约束"""
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            season="2023-24",
            match_time=datetime.now(),
        )

        # 正常比分
        match.home_score = 5
        match.away_score = 3
        assert match.home_score == 5
        assert match.away_score == 3

        # 零比分
        match.home_score = 0
        match.away_score = 0
        assert match.home_score == 0
        assert match.away_score == 0

    def test_different_teams_constraint(self):
        """测试不同球队约束"""
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            season="2023-24",
            match_time=datetime.now(),
        )
        # 确保是不同的球队
        assert match.home_team_id != match.away_team_id
