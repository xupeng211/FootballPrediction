"""
数据库模型测试
Database Models Tests
"""

import pytest
from datetime import datetime, date
from typing import List

from src.database.models import (
    User,
    Team,
    League,
    Match,
    Predictions,
    Odds,
    DataCollectionLog,
    Prediction,
)
from src.database.models.features import Features
from src.database.models.audit_log import AuditLog
from src.database.models.data_quality_log import DataQualityLog


@pytest.mark.unit
@pytest.mark.database

class TestUser:
    """用户模型测试"""

    def test_user_creation(self):
        """测试用户创建"""
        _user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hashed123",
            is_active=True,
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed123"
        assert user.is_active is True

    def test_user_repr(self):
        """测试用户表示"""
        _user = User(username="testuser", email="test@example.com")
        repr_str = repr(user)

        assert "User" in repr_str
        assert "testuser" in repr_str

    def test_user_str(self):
        """测试用户字符串表示"""
        _user = User(username="testuser", email="test@example.com")
        str_str = str(user)

        assert "testuser" in str_str
        assert "test@example.com" in str_str


class TestTeam:
    """球队模型测试"""

    def test_team_creation(self):
        """测试球队创建"""
        team = Team(
            name="Test Team", short_name="TT", country="Test Country", founded=2000
        )

        assert team.name == "Test Team"
        assert team.short_name == "TT"
        assert team.country == "Test Country"
        assert team.founded == 2000

    def test_team_repr(self):
        """测试球队表示"""
        team = Team(name="Test Team", short_name="TT")
        repr_str = repr(team)

        assert "Team" in repr_str
        assert "Test Team" in repr_str

    def test_team_str(self):
        """测试球队字符串表示"""
        team = Team(name="Test Team", short_name="TT")
        str_str = str(team)

        assert "Test Team" in str_str
        assert "TT" in str_str


class TestLeague:
    """联赛模型测试"""

    def test_league_creation(self):
        """测试联赛创建"""
        league = League(name="Test League", country="Test Country", season="2023/2024")

        assert league.name == "Test League"
        assert league.country == "Test Country"
        assert league.season == "2023/2024"

    def test_league_repr(self):
        """测试联赛表示"""
        league = League(name="Test League", season="2023/2024")
        repr_str = repr(league)

        assert "League" in repr_str
        assert "Test League" in repr_str
        assert "2023/2024" in repr_str


class TestMatch:
    """比赛模型测试"""

    def test_match_creation(self):
        """测试比赛创建"""
        match_time = datetime.now()
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=3,
            match_time=match_time,
            status="SCHEDULED",
        )

        assert match.home_team_id == 1
        assert match.away_team_id == 2
        assert match.league_id == 3
        assert match.match_time == match_time
        assert match.status == "SCHEDULED"

    def test_match_with_scores(self):
        """测试带比分的比赛"""
        match = Match(
            home_team_id=1,
            away_team_id=2,
            league_id=3,
            home_score=2,
            away_score=1,
            status="FINISHED",
        )

        assert match.home_score == 2
        assert match.away_score == 1
        assert match.status == "FINISHED"

    def test_match_repr(self):
        """测试比赛表示"""
        match = Match(home_team_id=1, away_team_id=2, league_id=3, status="SCHEDULED")
        repr_str = repr(match)

        assert "Match" in repr_str
        assert "1" in repr_str
        assert "2" in repr_str

    def test_match_str(self):
        """测试比赛字符串表示"""
        match = Match(home_team_id=1, away_team_id=2, league_id=3, status="SCHEDULED")
        str_str = str(match)

        assert "Match" in str_str
        assert "SCHEDULED" in str_str


class TestPrediction:
    """预测模型测试"""

    def test_prediction_creation(self):
        """测试预测创建"""
        _prediction = Predictions(
            user_id=1,
            match_id=2,
            predicted_home_score=2,
            predicted_away_score=1,
            confidence=0.85,
        )

        assert prediction.user_id == 1
        assert prediction.match_id == 2
        assert prediction.predicted_home_score == 2
        assert prediction.predicted_away_score == 1
        assert prediction.confidence == 0.85

    def test_prediction_with_result(self):
        """测试带结果的预测"""
        _prediction = Predictions(
            user_id=1,
            match_id=2,
            predicted_home_score=2,
            predicted_away_score=1,
            actual_home_score=2,
            actual_away_score=2,
            is_correct=False,
        )

        assert prediction.actual_home_score == 2
        assert prediction.actual_away_score == 2
        assert prediction.is_correct is False

    def test_prediction_points(self):
        """测试预测得分"""
        _prediction = Predictions(
            user_id=1,
            match_id=2,
            predicted_home_score=2,
            predicted_away_score=1,
            points=3,
        )

        assert prediction.points == 3

    def test_prediction_repr(self):
        """测试预测表示"""
        _prediction = Predictions(
            user_id=1, match_id=2, predicted_home_score=2, predicted_away_score=1
        )
        repr_str = repr(prediction)

        assert "Prediction" in repr_str
        assert "1" in repr_str
        assert "2" in repr_str


class TestOdds:
    """赔率模型测试"""

    def test_odds_creation(self):
        """测试赔率创建"""
        odds = Odds(
            match_id=1, home_win=2.50, draw=3.20, away_win=2.80, source="test_source"
        )

        assert odds.match_id == 1
        assert odds.home_win == 2.50
        assert odds.draw == 3.20
        assert odds.away_win == 2.80
        assert odds.source == "test_source"

    def test_odds_with_timestamp(self):
        """测试带时间戳的赔率"""
        timestamp = datetime.now()
        odds = Odds(
            match_id=1, home_win=2.50, draw=3.20, away_win=2.80, timestamp=timestamp
        )

        assert odds.timestamp == timestamp

    def test_odds_repr(self):
        """测试赔率表示"""
        odds = Odds(match_id=1, home_win=2.50, draw=3.20, away_win=2.80)
        repr_str = repr(odds)

        assert "Odds" in repr_str
        assert "1" in repr_str
        assert "2.5" in repr_str


class TestFeatures:
    """特征模型测试"""

    def test_features_creation(self):
        """测试特征创建"""
        features = Features(
            match_id=1,
            team_id=2,
            feature_type="TEAM_FORM",
            feature_data={"form": "WWLDW", "goals_scored": 10},
        )

        assert features.match_id == 1
        assert features.team_id == 2
        assert features.feature_type == "TEAM_FORM"
        assert features.feature_data["form"] == "WWLDW"
        assert features.feature_data["goals_scored"] == 10

    def test_features_with_metadata(self):
        """测试带元数据的特征"""
        features = Features(
            match_id=1,
            team_id=2,
            feature_type="HEAD_TO_HEAD",
            feature_data={"wins": 5, "draws": 2, "losses": 3},
            _metadata={"last_updated": datetime.now()},
        )

        assert features.feature_data["wins"] == 5
        assert "last_updated" in features.metadata

    def test_features_repr(self):
        """测试特征表示"""
        features = Features(match_id=1, team_id=2, feature_type="TEAM_FORM")
        repr_str = repr(features)

        assert "Features" in repr_str
        assert "TEAM_FORM" in repr_str


class TestDataCollectionLog:
    """数据收集日志模型测试"""

    def test_collection_log_creation(self):
        """测试收集日志创建"""
        log = DataCollectionLog(
            source="test_source",
            data_type="MATCH",
            status="SUCCESS",
            records_processed=100,
        )

        assert log.source == "test_source"
        assert log.data_type == "MATCH"
        assert log.status == "SUCCESS"
        assert log.records_processed == 100

    def test_collection_log_with_error(self):
        """测试带错误的收集日志"""
        log = DataCollectionLog(
            source="test_source",
            data_type="ODDS",
            status="ERROR",
            error_message="Connection timeout",
            records_processed=0,
        )

        assert log.status == "ERROR"
        assert log.error_message == "Connection timeout"
        assert log.records_processed == 0

    def test_collection_log_repr(self):
        """测试收集日志表示"""
        log = DataCollectionLog(
            source="test_source", data_type="MATCH", status="SUCCESS"
        )
        repr_str = repr(log)

        assert "DataCollectionLog" in repr_str
        assert "test_source" in repr_str
        assert "SUCCESS" in repr_str


class TestDataQualityLog:
    """数据质量日志模型测试"""

    def test_quality_log_creation(self):
        """测试质量日志创建"""
        log = DataQualityLog(
            table_name="matches",
            record_id=1,
            issue_type="MISSING_VALUE",
            field_name="home_score",
            severity="WARNING",
        )

        assert log.table_name == "matches"
        assert log.record_id == 1
        assert log.issue_type == "MISSING_VALUE"
        assert log.field_name == "home_score"
        assert log.severity == "WARNING"

    def test_quality_log_with_description(self):
        """测试带描述的质量日志"""
        log = DataQualityLog(
            table_name="predictions",
            record_id=5,
            issue_type="INVALID_VALUE",
            field_name="confidence",
            severity="ERROR",
            description="Confidence value must be between 0 and 1",
            suggested_fix="Set confidence to 0.85",
        )

        assert log.issue_type == "INVALID_VALUE"
        assert log.description == "Confidence value must be between 0 and 1"
        assert log.suggested_fix == "Set confidence to 0.85"

    def test_quality_log_repr(self):
        """测试质量日志表示"""
        log = DataQualityLog(
            table_name="matches", record_id=1, issue_type="MISSING_VALUE"
        )
        repr_str = repr(log)

        assert "DataQualityLog" in repr_str
        assert "matches" in repr_str
        assert "MISSING_VALUE" in repr_str


class TestAuditLog:
    """审计日志模型测试"""

    def test_audit_log_creation(self):
        """测试审计日志创建"""
        log = AuditLog(
            user_id=1, action="CREATE", table_name="predictions", record_id=5
        )

        assert log.user_id == 1
        assert log.action == "CREATE"
        assert log.table_name == "predictions"
        assert log.record_id == 5

    def test_audit_log_with_changes(self):
        """测试带变更的审计日志"""
        log = AuditLog(
            user_id=1,
            action="UPDATE",
            table_name="predictions",
            record_id=5,
            old_values='{"predicted_home_score": 2}',
            new_values='{"predicted_home_score": 3}',
        )

        assert log.action == "UPDATE"
        assert log.old_values == '{"predicted_home_score": 2}'
        assert log.new_values == '{"predicted_home_score": 3}'

    def test_audit_log_repr(self):
        """测试审计日志表示"""
        log = AuditLog(user_id=1, action="DELETE", table_name="matches", record_id=10)
        repr_str = repr(log)

        assert "AuditLog" in repr_str
        assert "DELETE" in repr_str
        assert "matches" in repr_str
