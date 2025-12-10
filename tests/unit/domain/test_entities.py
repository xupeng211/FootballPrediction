from typing import Optional

"""
领域实体测试模块
Domain Entities Test Module

测试核心领域实体的功能和行为
"""

from datetime import datetime

from src.domain.entities import (
    League,
    Match,
    MatchStatus,
    Prediction,
    Team,
    TeamStatus,
    create_test_match,
    create_test_team,
    validate_prediction_confidence,
)


class TestTeamStatus:
    """测试TeamStatus枚举"""

    def test_team_status_values(self):
        """测试队伍状态枚举值"""
        assert TeamStatus.ACTIVE.value == "ACTIVE"
        assert TeamStatus.INACTIVE.value == "INACTIVE"
        assert TeamStatus.SUSPENDED.value == "SUSPENDED"

    def test_team_status_equality(self):
        """测试队伍状态比较"""
        status1 = TeamStatus.ACTIVE
        status2 = TeamStatus.ACTIVE
        status3 = TeamStatus.INACTIVE

        assert status1 == status2
        assert status1 != status3
        assert hash(status1) == hash(status2)
        assert hash(status1) != hash(status3)


class TestMatchStatus:
    """测试MatchStatus枚举"""

    def test_match_status_values(self):
        """测试比赛状态枚举值"""
        assert MatchStatus.SCHEDULED.value == "SCHEDULED"
        assert MatchStatus.LIVE.value == "LIVE"
        assert MatchStatus.FINISHED.value == "FINISHED"
        assert MatchStatus.POSTPONED.value == "POSTPONED"
        assert MatchStatus.CANCELLED.value == "CANCELLED"

    def test_match_status_equality(self):
        """测试比赛状态比较"""
        status1 = MatchStatus.SCHEDULED
        status2 = MatchStatus.SCHEDULED
        status3 = MatchStatus.FINISHED

        assert status1 == status2
        assert status1 != status3
        assert hash(status1) == hash(status2)
        assert hash(status1) != hash(status3)


class TestTeam:
    """测试Team实体"""

    def test_team_creation_minimal(self):
        """测试最小参数创建队伍"""
        team = Team(id=1, name="Test Team", status=TeamStatus.ACTIVE)

        assert team.id == 1
        assert team.name == "Test Team"
        assert team.status == TeamStatus.ACTIVE
        assert team.league_id is None
        assert team.created_at is None

    def test_team_creation_full(self):
        """测试完整参数创建队伍"""
        created_at = datetime.now()
        team = Team(
            id=1,
            name="Test Team",
            status=TeamStatus.ACTIVE,
            league_id=100,
            created_at=created_at,
        )

        assert team.id == 1
        assert team.name == "Test Team"
        assert team.status == TeamStatus.ACTIVE
        assert team.league_id == 100
        assert team.created_at == created_at

    def test_team_equality(self):
        """测试队伍对象比较"""
        team1 = Team(id=1, name="Team A", status=TeamStatus.ACTIVE)
        team2 = Team(id=1, name="Team A", status=TeamStatus.ACTIVE)
        team3 = Team(id=2, name="Team B", status=TeamStatus.INACTIVE)

        assert team1 == team2
        assert team1 != team3

    def test_team_repr(self):
        """测试队伍字符串表示"""
        team = Team(id=1, name="Test Team", status=TeamStatus.ACTIVE)
        repr_str = repr(team)

        assert "Team" in repr_str
        assert "id=1" in repr_str
        assert "name='Test Team'" in repr_str
        assert "TeamStatus.ACTIVE" in repr_str


class TestMatch:
    """测试Match实体"""

    def test_match_creation_minimal(self):
        """测试最小参数创建比赛"""
        match = Match(
            id=1,
            home_team_id=100,
            away_team_id=200,
            league_id=10,
            status=MatchStatus.SCHEDULED,
        )

        assert match.id == 1
        assert match.home_team_id == 100
        assert match.away_team_id == 200
        assert match.league_id == 10
        assert match.status == MatchStatus.SCHEDULED
        assert match.scheduled_at is None
        assert match.started_at is None
        assert match.finished_at is None
        assert match.home_score == 0
        assert match.away_score == 0

    def test_match_creation_full(self):
        """测试完整参数创建比赛"""
        scheduled_at = datetime.now()
        started_at = datetime.now()
        finished_at = datetime.now()

        match = Match(
            id=1,
            home_team_id=100,
            away_team_id=200,
            league_id=10,
            status=MatchStatus.FINISHED,
            scheduled_at=scheduled_at,
            started_at=started_at,
            finished_at=finished_at,
            home_score=2,
            away_score=1,
        )

        assert match.id == 1
        assert match.home_team_id == 100
        assert match.away_team_id == 200
        assert match.league_id == 10
        assert match.status == MatchStatus.FINISHED
        assert match.scheduled_at == scheduled_at
        assert match.started_at == started_at
        assert match.finished_at == finished_at
        assert match.home_score == 2
        assert match.away_score == 1

    def test_match_equality(self):
        """测试比赛对象比较"""
        match1 = Match(
            id=1,
            home_team_id=100,
            away_team_id=200,
            league_id=10,
            status=MatchStatus.SCHEDULED,
        )
        match2 = Match(
            id=1,
            home_team_id=100,
            away_team_id=200,
            league_id=10,
            status=MatchStatus.SCHEDULED,
        )
        match3 = Match(
            id=2,
            home_team_id=300,
            away_team_id=400,
            league_id=20,
            status=MatchStatus.LIVE,
        )

        assert match1 == match2
        assert match1 != match3

    def test_match_repr(self):
        """测试比赛字符串表示"""
        match = Match(
            id=1,
            home_team_id=100,
            away_team_id=200,
            league_id=10,
            status=MatchStatus.SCHEDULED,
        )
        repr_str = repr(match)

        assert "Match" in repr_str
        assert "id=1" in repr_str
        assert "home_team_id=100" in repr_str
        assert "away_team_id=200" in repr_str
        assert "MatchStatus.SCHEDULED" in repr_str


class TestLeague:
    """测试League实体"""

    def test_league_creation_minimal(self):
        """测试最小参数创建联赛"""
        league = League(id=1, name="Test League", country="Test Country", season="2023")

        assert league.id == 1
        assert league.name == "Test League"
        assert league.country == "Test Country"
        assert league.season == "2023"
        assert league.is_active is True  # 默认值

    def test_league_creation_full(self):
        """测试完整参数创建联赛"""
        league = League(
            id=1,
            name="Test League",
            country="Test Country",
            season="2023",
            is_active=False,
        )

        assert league.id == 1
        assert league.name == "Test League"
        assert league.country == "Test Country"
        assert league.season == "2023"
        assert league.is_active is False

    def test_league_equality(self):
        """测试联赛对象比较"""
        league1 = League(id=1, name="League A", country="Country A", season="2023")
        league2 = League(id=1, name="League A", country="Country A", season="2023")
        league3 = League(id=2, name="League B", country="Country B", season="2024")

        assert league1 == league2
        assert league1 != league3

    def test_league_repr(self):
        """测试联赛字符串表示"""
        league = League(id=1, name="Test League", country="Test Country", season="2023")
        repr_str = repr(league)

        assert "League" in repr_str
        assert "id=1" in repr_str
        assert "name='Test League'" in repr_str
        assert "country='Test Country'" in repr_str
        assert "season='2023'" in repr_str


class TestPrediction:
    """测试Prediction实体"""

    def test_prediction_creation_minimal(self):
        """测试最小参数创建预测"""
        created_at = datetime.now()
        prediction = Prediction(
            id=1,
            match_id=100,
            user_id=200,
            predicted_result="HOME_WIN",
            confidence=0.8,
            created_at=created_at,
        )

        assert prediction.id == 1
        assert prediction.match_id == 100
        assert prediction.user_id == 200
        assert prediction.predicted_result == "HOME_WIN"
        assert prediction.confidence == 0.8
        assert prediction.created_at == created_at
        assert prediction.is_correct is None

    def test_prediction_creation_full(self):
        """测试完整参数创建预测"""
        created_at = datetime.now()
        prediction = Prediction(
            id=1,
            match_id=100,
            user_id=200,
            predicted_result="HOME_WIN",
            confidence=0.8,
            created_at=created_at,
            is_correct=True,
        )

        assert prediction.id == 1
        assert prediction.match_id == 100
        assert prediction.user_id == 200
        assert prediction.predicted_result == "HOME_WIN"
        assert prediction.confidence == 0.8
        assert prediction.created_at == created_at
        assert prediction.is_correct is True

    def test_prediction_equality(self):
        """测试预测对象比较"""
        created_at = datetime.now()
        prediction1 = Prediction(
            id=1,
            match_id=100,
            user_id=200,
            predicted_result="HOME_WIN",
            confidence=0.8,
            created_at=created_at,
        )
        prediction2 = Prediction(
            id=1,
            match_id=100,
            user_id=200,
            predicted_result="HOME_WIN",
            confidence=0.8,
            created_at=created_at,
        )
        prediction3 = Prediction(
            id=2,
            match_id=300,
            user_id=400,
            predicted_result="AWAY_WIN",
            confidence=0.6,
            created_at=created_at,
        )

        assert prediction1 == prediction2
        assert prediction1 != prediction3

    def test_prediction_repr(self):
        """测试预测字符串表示"""
        created_at = datetime.now()
        prediction = Prediction(
            id=1,
            match_id=100,
            user_id=200,
            predicted_result="HOME_WIN",
            confidence=0.8,
            created_at=created_at,
        )
        repr_str = repr(prediction)

        assert "Prediction" in repr_str
        assert "id=1" in repr_str
        assert "match_id=100" in repr_str
        assert "user_id=200" in repr_str
        assert "predicted_result='HOME_WIN'" in repr_str
        assert "confidence=0.8" in repr_str


class TestUtilityFunctions:
    """测试工具函数"""

    def test_create_test_team(self):
        """测试创建测试队伍函数"""
        team = create_test_team(1, "Test Team")

        assert team.id == 1
        assert team.name == "Test Team"
        assert team.status == TeamStatus.ACTIVE
        assert team.league_id is None
        assert team.created_at is None

    def test_create_test_match(self):
        """测试创建测试比赛函数"""
        match = create_test_match(1, 100, 200)

        assert match.id == 1
        assert match.home_team_id == 100
        assert match.away_team_id == 200
        assert match.league_id == 1
        assert match.status == MatchStatus.SCHEDULED
        assert match.scheduled_at is None
        assert match.started_at is None
        assert match.finished_at is None
        assert match.home_score == 0
        assert match.away_score == 0

    def test_validate_prediction_confidence_valid(self):
        """测试有效预测置信度验证"""
        valid_confidences = [0.0, 0.5, 0.8, 1.0]

        for confidence in valid_confidences:
            assert validate_prediction_confidence(confidence) is True

    def test_validate_prediction_confidence_invalid(self):
        """测试无效预测置信度验证"""
        invalid_confidences = [-0.1, -1.0, 1.1, 2.0]

        for confidence in invalid_confidences:
            assert validate_prediction_confidence(confidence) is False

    def test_validate_prediction_confidence_edge_cases(self):
        """测试预测置信度边界情况"""
        # 测试边界值
        assert validate_prediction_confidence(0.0) is True
        assert validate_prediction_confidence(1.0) is True

        # 测试非常接近边界值
        assert validate_prediction_confidence(0.0000001) is True
        assert validate_prediction_confidence(0.9999999) is True

        # 测试稍微超出边界值
        assert validate_prediction_confidence(-0.0000001) is False
        assert validate_prediction_confidence(1.0000001) is False


class TestIntegrationScenarios:
    """测试集成场景"""

    def test_complete_match_workflow(self):
        """测试完整比赛工作流程"""
        # 创建联赛
        league = League(
            id=1, name="Premier League", country="England", season="2023/2024"
        )

        # 创建队伍
        home_team = create_test_team(100, "Manchester United")
        away_team = create_test_team(200, "Liverpool")
        home_team.league_id = league.id
        away_team.league_id = league.id

        # 创建比赛
        match = create_test_match(1, home_team.id, away_team.id)
        match.league_id = league.id

        # 创建预测
        created_at = datetime.now()
        prediction = Prediction(
            id=1,
            match_id=match.id,
            user_id=300,
            predicted_result="HOME_WIN",
            confidence=0.7,
            created_at=created_at,
        )

        # 验证数据完整性
        assert league.id == 1
        assert home_team.league_id == league.id
        assert away_team.league_id == league.id
        assert match.home_team_id == home_team.id
        assert match.away_team_id == away_team.id
        assert match.league_id == league.id
        assert prediction.match_id == match.id
        assert validate_prediction_confidence(prediction.confidence) is True

    def test_multiple_matches_for_league(self):
        """测试联赛的多场比赛"""
        league = League(id=1, name="Test League", country="Test", season="2023")

        matches = []
        for i in range(5):
            match = create_test_match(i + 1, i * 10 + 1, i * 10 + 2)
            match.league_id = league.id
            matches.append(match)

        # 验证所有比赛都属于同一联赛
        for match in matches:
            assert match.league_id == league.id
            assert match.status == MatchStatus.SCHEDULED

        # 验证比赛数量
        assert len(matches) == 5

    def test_team_status_transitions(self):
        """测试队伍状态转换"""
        team = create_test_team(1, "Test Team")

        # 初始状态
        assert team.status == TeamStatus.ACTIVE

        # 状态转换
        team.status = TeamStatus.SUSPENDED
        assert team.status == TeamStatus.SUSPENDED

        team.status = TeamStatus.INACTIVE
        assert team.status == TeamStatus.INACTIVE

    def test_match_status_lifecycle(self):
        """测试比赛状态生命周期"""
        match = create_test_match(1, 100, 200)

        # 初始状态
        assert match.status == MatchStatus.SCHEDULED

        # 比赛开始
        match.status = MatchStatus.LIVE
        match.started_at = datetime.now()
        assert match.status == MatchStatus.LIVE
        assert match.started_at is not None

        # 比赛结束
        match.status = MatchStatus.FINISHED
        match.finished_at = datetime.now()
        match.home_score = 2
        match.away_score = 1
        assert match.status == MatchStatus.FINISHED
        assert match.finished_at is not None
        assert match.home_score == 2
        assert match.away_score == 1
