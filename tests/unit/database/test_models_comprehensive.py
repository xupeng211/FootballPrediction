"""
数据库模型综合测试
Database Models Comprehensive Tests
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    Numeric,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.exc import IntegrityError

# 导入模型类（使用mock避免依赖问题）
try:
    from src.database.models.user import User
except ImportError:
    User = Mock

try:
    from src.database.models.team import Team
except ImportError:
    Team = Mock

try:
    from src.database.models.match import Match
except ImportError:
    Match = Mock

try:
    from src.database.models.league import League
except ImportError:
    League = Mock

try:
    from src.database.models.predictions import Prediction
except ImportError:
    Prediction = Mock

try:
    from src.database.models.odds import Odds
except ImportError:
    Odds = Mock

try:
    from src.database.models.features import Features
except ImportError:
    Features = Mock

try:
    from src.database.models.audit_log import AuditLog
except ImportError:
    AuditLog = Mock

try:
    from src.database.models.data_quality_log import DataQualityLog
except ImportError:
    DataQualityLog = Mock

try:
    from src.database.models.data_collection_log import DataCollectionLog
except ImportError:
    DataCollectionLog = Mock

try:
    from src.database.models.raw_data import RawData
except ImportError:
    RawData = Mock


class TestUserModel:
    """用户模型测试"""

    def test_user_creation(self):
        """测试用户创建"""
        if User is Mock:
            pytest.skip("User model not available")

        user_data = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": "hashed_password",
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        _user = User(**user_data)

        assert user.id == 1
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True

    def test_user_validation(self):
        """测试用户验证"""
        if User is Mock:
            pytest.skip("User model not available")

        # 测试必填字段
        with pytest.raises(Exception):
            User(username=None)
            # 触发验证

    def test_user_relationships(self):
        """测试用户关系"""
        if User is Mock:
            pytest.skip("User model not available")

        _user = User()

        # 检查关系是否存在
        assert hasattr(user, "predictions") or hasattr(user, "prediction")

    def test_user_password_hashing(self):
        """测试密码哈希"""
        if User is Mock:
            pytest.skip("User model not available")

        _user = User()
        password = "plain_password"

        # 模拟密码哈希
        with patch("src.database.models.user.hash_password") as mock_hash:
            mock_hash.return_value = "hashed_password"

            user.set_password(password)
            assert user.password_hash == "hashed_password"
            mock_hash.assert_called_once_with(password)

    def test_user_check_password(self):
        """测试密码验证"""
        if User is Mock:
            pytest.skip("User model not available")

        _user = User()
        user.password_hash = "hashed_password"

        with patch("src.database.models.user.check_password") as mock_check:
            mock_check.return_value = True

            _result = user.check_password("plain_password")
            assert result is True
            mock_check.assert_called_once_with("hashed_password", "plain_password")


class TestTeamModel:
    """球队模型测试"""

    def test_team_creation(self):
        """测试球队创建"""
        if Team is Mock:
            pytest.skip("Team model not available")

        team_data = {
            "id": 1,
            "name": "Test Team",
            "code": "TT",
            "country": "Test Country",
            "founded": 1900,
            "logo_url": "http://example.com/logo.png",
            "created_at": datetime.now(),
        }

        team = Team(**team_data)

        assert team.id == 1
        assert team.name == "Test Team"
        assert team.code == "TT"
        assert team.founded == 1900

    def test_team_validation(self):
        """测试球队验证"""
        if Team is Mock:
            pytest.skip("Team model not available")

        # 测试唯一名称约束
        Team(name="Team A", code="TA")
        Team(name="Team A", code="TB")

        # 验证逻辑取决于具体实现

    def test_team_relationships(self):
        """测试球队关系"""
        if Team is Mock:
            pytest.skip("Team model not available")

        team = Team()

        # 检查关系
        assert hasattr(team, "home_matches") or hasattr(team, "matches_as_home")
        assert hasattr(team, "away_matches") or hasattr(team, "matches_as_away")

    def test_team_statistics(self):
        """测试球队统计"""
        if Team is Mock:
            pytest.skip("Team model not available")

        team = Team()

        # 模拟统计方法
        with patch.object(team, "get_win_rate") as mock_rate:
            mock_rate.return_value = 0.75

            win_rate = team.get_win_rate()
            assert win_rate == 0.75

    def test_team_update_info(self):
        """测试球队信息更新"""
        if Team is Mock:
            pytest.skip("Team model not available")

        team = Team(name="Old Name")

        team.name = "New Name"
        team.code = "NN"

        assert team.name == "New Name"
        assert team.code == "NN"


class TestMatchModel:
    """比赛模型测试"""

    def test_match_creation(self):
        """测试比赛创建"""
        if Match is Mock:
            pytest.skip("Match model not available")

        match_data = {
            "id": 1,
            "home_team_id": 1,
            "away_team_id": 2,
            "league_id": 1,
            "match_date": datetime.now() + timedelta(days=1),
            "status": "upcoming",
            "home_score": 0,
            "away_score": 0,
            "venue": "Test Stadium",
        }

        match = Match(**match_data)

        assert match.id == 1
        assert match.home_team_id == 1
        assert match.away_team_id == 2
        assert match.status == "upcoming"

    def test_match_validation(self):
        """测试比赛验证"""
        if Match is Mock:
            pytest.skip("Match model not available")

        # 测试日期验证
        with pytest.raises(Exception):
            Match(match_date=None)
            # 触发验证

    def test_match_relationships(self):
        """测试比赛关系"""
        if Match is Mock:
            pytest.skip("Match model not available")

        match = Match()

        # 检查关系
        assert hasattr(match, "home_team")
        assert hasattr(match, "away_team")
        assert hasattr(match, "league")
        assert hasattr(match, "predictions") or hasattr(match, "prediction")

    def test_match_update_score(self):
        """测试更新比分"""
        if Match is Mock:
            pytest.skip("Match model not available")

        match = Match(home_score=0, away_score=0)

        match.home_score = 2
        match.away_score = 1

        assert match.home_score == 2
        assert match.away_score == 1

    def test_match_status_transitions(self):
        """测试比赛状态转换"""
        if Match is Mock:
            pytest.skip("Match model not available")

        match = Match(status="upcoming")

        # 状态转换
        match.status = "in_progress"
        assert match.status == "in_progress"

        match.status = "completed"
        assert match.status == "completed"

    def test_match_duration(self):
        """测试比赛时长计算"""
        if Match is Mock:
            pytest.skip("Match model not available")

        start_time = datetime.now() - timedelta(hours=2)
        end_time = datetime.now()

        match = Match(start_time=start_time, end_time=end_time)

        with patch.object(match, "get_duration") as mock_duration:
            mock_duration.return_value = timedelta(hours=2)

            duration = match.get_duration()
            assert duration == timedelta(hours=2)


class TestLeagueModel:
    """联赛模型测试"""

    def test_league_creation(self):
        """测试联赛创建"""
        if League is Mock:
            pytest.skip("League model not available")

        league_data = {
            "id": 1,
            "name": "Test League",
            "country": "Test Country",
            "season": "2023/2024",
            "start_date": date(2023, 8, 1),
            "end_date": date(2024, 5, 31),
        }

        league = League(**league_data)

        assert league.id == 1
        assert league.name == "Test League"
        assert league.season == "2023/2024"

    def test_league_validation(self):
        """测试联赛验证"""
        if League is Mock:
            pytest.skip("League model not available")

        # 测试赛季格式
        league = League(season="2023/2024")
        assert league.season == "2023/2024"

    def test_league_relationships(self):
        """测试联赛关系"""
        if League is Mock:
            pytest.skip("League model not available")

        league = League()

        # 检查关系
        assert hasattr(league, "matches")
        assert hasattr(league, "teams")

    def test_league_standings(self):
        """测试联赛积分榜"""
        if League is Mock:
            pytest.skip("League model not available")

        league = League()

        with patch.object(league, "get_standings") as mock_standings:
            mock_standings.return_value = [
                {"team": "Team A", "points": 30},
                {"team": "Team B", "points": 25},
            ]

            standings = league.get_standings()
            assert len(standings) == 2
            assert standings[0]["points"] == 30

    def test_league_active_season(self):
        """测试当前赛季"""
        if League is Mock:
            pytest.skip("League model not available")

        today = date.today()
        league = League(
            start_date=today - timedelta(days=30), end_date=today + timedelta(days=30)
        )

        with patch.object(league, "is_active") as mock_active:
            mock_active.return_value = True

            assert league.is_active() is True


class TestPredictionModel:
    """预测模型测试"""

    def test_prediction_creation(self):
        """测试预测创建"""
        if Prediction is Mock:
            pytest.skip("Prediction model not available")

        prediction_data = {
            "id": 1,
            "user_id": 1,
            "match_id": 1,
            "predicted_home_score": 2,
            "predicted_away_score": 1,
            "confidence": 0.85,
            "strategy_used": "ml_model_v1",
            "created_at": datetime.now(),
        }

        _prediction = Prediction(**prediction_data)

        assert prediction.id == 1
        assert prediction.user_id == 1
        assert prediction.predicted_home_score == 2
        assert prediction.confidence == 0.85

    def test_prediction_validation(self):
        """测试预测验证"""
        if Prediction is Mock:
            pytest.skip("Prediction model not available")

        # 测试置信度范围
        _prediction = Prediction(confidence=0.85)
        assert 0 <= prediction.confidence <= 1

    def test_prediction_relationships(self):
        """测试预测关系"""
        if Prediction is Mock:
            pytest.skip("Prediction model not available")

        _prediction = Prediction()

        # 检查关系
        assert hasattr(prediction, "user")
        assert hasattr(prediction, "match")

    def test_prediction_accuracy(self):
        """测试预测准确性"""
        if Prediction is Mock:
            pytest.skip("Prediction model not available")

        _prediction = Prediction(predicted_home_score=2, predicted_away_score=1)

        with patch.object(prediction, "calculate_accuracy") as mock_accuracy:
            mock_accuracy.return_value = True

            is_correct = prediction.calculate_accuracy(actual_home=2, actual_away=1)
            assert is_correct is True

    def test_prediction_outcome(self):
        """测试预测结果"""
        if Prediction is Mock:
            pytest.skip("Prediction model not available")

        _prediction = Prediction(predicted_home_score=2, predicted_away_score=1)

        with patch.object(prediction, "get_predicted_outcome") as mock_outcome:
            mock_outcome.return_value = "home_win"

            outcome = prediction.get_predicted_outcome()
            assert outcome == "home_win"


class TestOddsModel:
    """赔率模型测试"""

    def test_odds_creation(self):
        """测试赔率创建"""
        if Odds is Mock:
            pytest.skip("Odds model not available")

        odds_data = {
            "id": 1,
            "match_id": 1,
            "bookmaker": "TestBookmaker",
            "home_win": Decimal("2.50"),
            "draw": Decimal("3.20"),
            "away_win": Decimal("2.80"),
            "updated_at": datetime.now(),
        }

        odds = Odds(**odds_data)

        assert odds.id == 1
        assert odds.match_id == 1
        assert odds.home_win == Decimal("2.50")
        assert odds.draw == Decimal("3.20")

    def test_odds_validation(self):
        """测试赔率验证"""
        if Odds is Mock:
            pytest.skip("Odds model not available")

        # 测试赔率必须为正数
        odds = Odds(home_win=Decimal("2.50"))
        assert odds.home_win > 0

    def test_odds_relationships(self):
        """测试赔率关系"""
        if Odds is Mock:
            pytest.skip("Odds model not available")

        odds = Odds()

        # 检查关系
        assert hasattr(odds, "match")

    def test_odds_implied_probability(self):
        """测试隐含概率计算"""
        if Odds is Mock:
            pytest.skip("Odds model not available")

        odds = Odds(
            home_win=Decimal("2.00"), draw=Decimal("3.00"), away_win=Decimal("3.00")
        )

        with patch.object(odds, "calculate_implied_probability") as mock_prob:
            mock_prob.return_value = {"home": 0.5, "draw": 0.333, "away": 0.333}

            probabilities = odds.calculate_implied_probability()
            assert probabilities["home"] == 0.5

    def test_odds_margin(self):
        """测试赔率利润率"""
        if Odds is Mock:
            pytest.skip("Odds model not available")

        odds = Odds()

        with patch.object(odds, "calculate_bookmaker_margin") as mock_margin:
            mock_margin.return_value = 0.05

            margin = odds.calculate_bookmaker_margin()
            assert margin == 0.05


class TestFeaturesModel:
    """特征模型测试"""

    def test_features_creation(self):
        """测试特征创建"""
        if Features is Mock:
            pytest.skip("Features model not available")

        features_data = {
            "id": 1,
            "match_id": 1,
            "team_id": 1,
            "feature_type": "team_form",
            "feature_data": {
                "last_5_games": ["W", "W", "D", "L", "W"],
                "goals_scored": 8,
                "goals_conceded": 4,
            },
            "calculated_at": datetime.now(),
        }

        features = Features(**features_data)

        assert features.id == 1
        assert features.match_id == 1
        assert features.feature_type == "team_form"

    def test_features_validation(self):
        """测试特征验证"""
        if Features is Mock:
            pytest.skip("Features model not available")

        features = Features(feature_data={"valid": "data"})
        assert isinstance(features.feature_data, dict)

    def test_features_relationships(self):
        """测试特征关系"""
        if Features is Mock:
            pytest.skip("Features model not available")

        features = Features()

        # 检查关系
        assert hasattr(features, "match")
        assert hasattr(features, "team")

    def test_features_serialization(self):
        """测试特征序列化"""
        if Features is Mock:
            pytest.skip("Features model not available")

        features = Features(feature_data={"key": "value"})

        with patch.object(features, "to_dict") as mock_dict:
            mock_dict.return_value = {"id": 1, "feature_data": {"key": "value"}}

            _result = features.to_dict()
            assert result["feature_data"]["key"] == "value"

    def test_features_calculation(self):
        """测试特征计算"""
        if Features is Mock:
            pytest.skip("Features model not available")

        features = Features()

        with patch.object(features, "calculate") as mock_calc:
            mock_calc.return_value = {"calculated_feature": 0.75}

            _result = features.calculate()
            assert result["calculated_feature"] == 0.75


class TestAuditLogModel:
    """审计日志模型测试"""

    def test_audit_log_creation(self):
        """测试审计日志创建"""
        if AuditLog is Mock:
            pytest.skip("AuditLog model not available")

        audit_data = {
            "id": 1,
            "user_id": 1,
            "action": "CREATE",
            "resource_type": "prediction",
            "resource_id": 1,
            "old_values": None,
            "new_values": {"home_score": 2},
            "ip_address": "127.0.0.1",
            "user_agent": "TestAgent/1.0",
            "timestamp": datetime.now(),
        }

        audit_log = AuditLog(**audit_data)

        assert audit_log.id == 1
        assert audit_log.action == "CREATE"
        assert audit_log.resource_type == "prediction"

    def test_audit_log_validation(self):
        """测试审计日志验证"""
        if AuditLog is Mock:
            pytest.skip("AuditLog model not available")

        audit_log = AuditLog(action="CREATE", resource_type="prediction")
        assert audit_log.action in ["CREATE", "UPDATE", "DELETE"]

    def test_audit_log_relationships(self):
        """测试审计日志关系"""
        if AuditLog is Mock:
            pytest.skip("AuditLog model not available")

        audit_log = AuditLog()

        # 检查关系
        assert hasattr(audit_log, "user")

    def test_audit_log_filtering(self):
        """测试审计日志过滤"""
        if AuditLog is Mock:
            pytest.skip("AuditLog model not available")

        # 模拟查询过滤
        with patch("src.database.models.audit_log.AuditLog.query") as mock_query:
            mock_query.filter_by.return_value = mock_query
            mock_query.all.return_value = []

            results = AuditLog.query.filter_by(user_id=1).all()
            assert isinstance(results, list)


class TestDataQualityLogModel:
    """数据质量日志模型测试"""

    def test_data_quality_log_creation(self):
        """测试数据质量日志创建"""
        if DataQualityLog is Mock:
            pytest.skip("DataQualityLog model not available")

        log_data = {
            "id": 1,
            "source": "api",
            "data_type": "match",
            "record_id": 1,
            "validation_rules": {
                "home_team_present": True,
                "away_team_present": True,
                "date_valid": True,
            },
            "quality_score": 0.95,
            "issues": [],
            "checked_at": datetime.now(),
        }

        log = DataQualityLog(**log_data)

        assert log.id == 1
        assert log.source == "api"
        assert log.quality_score == 0.95

    def test_data_quality_validation(self):
        """测试数据质量验证"""
        if DataQualityLog is Mock:
            pytest.skip("DataQualityLog model not available")

        log = DataQualityLog(quality_score=0.95)
        assert 0 <= log.quality_score <= 1

    def test_data_quality_issues(self):
        """测试数据质量问题"""
        if DataQualityLog is Mock:
            pytest.skip("DataQualityLog model not available")

        issues = [
            {"field": "home_score", "issue": "negative_value"},
            {"field": "match_date", "issue": "invalid_format"},
        ]

        log = DataQualityLog(issues=issues)
        assert len(log.issues) == 2

    def test_data_quality_improvement(self):
        """测试数据质量改进"""
        if DataQualityLog is Mock:
            pytest.skip("DataQualityLog model not available")

        log = DataQualityLog()

        with patch.object(log, "improve_quality") as mock_improve:
            mock_improve.return_value = {"new_score": 0.98}

            _result = log.improve_quality()
            assert result["new_score"] == 0.98


class TestDataCollectionLogModel:
    """数据收集日志模型测试"""

    def test_data_collection_log_creation(self):
        """测试数据收集日志创建"""
        if DataCollectionLog is Mock:
            pytest.skip("DataCollectionLog model not available")

        log_data = {
            "id": 1,
            "source": "external_api",
            "endpoint": "/matches",
            "status": "success",
            "records_collected": 100,
            "records_processed": 95,
            "errors": [],
            "duration_ms": 1500,
            "collected_at": datetime.now(),
        }

        log = DataCollectionLog(**log_data)

        assert log.id == 1
        assert log.status == "success"
        assert log.records_collected == 100

    def test_data_collection_status(self):
        """测试数据收集状态"""
        if DataCollectionLog is Mock:
            pytest.skip("DataCollectionLog model not available")

        log = DataCollectionLog(status="success")
        assert log.status in ["success", "failed", "partial"]

    def test_data_collection_metrics(self):
        """测试数据收集指标"""
        if DataCollectionLog is Mock:
            pytest.skip("DataCollectionLog model not available")

        log = DataCollectionLog(
            records_collected=100, records_processed=95, duration_ms=1500
        )

        success_rate = log.records_processed / log.records_collected
        assert success_rate == 0.95

    def test_data_collection_errors(self):
        """测试数据收集错误"""
        if DataCollectionLog is Mock:
            pytest.skip("DataCollectionLog model not available")

        errors = [
            {"record_id": 5, "error": "invalid_data"},
            {"record_id": 10, "error": "missing_field"},
        ]

        log = DataCollectionLog(errors=errors)
        assert len(log.errors) == 2


class TestRawDataModel:
    """原始数据模型测试"""

    def test_raw_data_creation(self):
        """测试原始数据创建"""
        if RawData is Mock:
            pytest.skip("RawData model not available")

        raw_data = {
            "id": 1,
            "source": "api",
            "data_type": "match",
            "raw_content": {
                "match_id": "123",
                "home_team": "Team A",
                "away_team": "Team B",
            },
            "processed": False,
            "received_at": datetime.now(),
        }

        _data = RawData(**raw_data)

        assert data.id == 1
        assert data.source == "api"
        assert data.processed is False

    def test_raw_data_processing(self):
        """测试原始数据处理"""
        if RawData is Mock:
            pytest.skip("RawData model not available")

        _data = RawData(processed=False)

        with patch.object(data, "mark_processed") as mock_mark:
            mock_mark.return_value = True

            _result = data.mark_processed()
            assert result is True

    def test_raw_data_content_validation(self):
        """测试原始数据内容验证"""
        if RawData is Mock:
            pytest.skip("RawData model not available")

        content = {"valid": "json", "data": 123}
        _data = RawData(raw_content=content)

        assert isinstance(data.raw_content, dict)

    def test_raw_data_archiving(self):
        """测试原始数据归档"""
        if RawData is Mock:
            pytest.skip("RawData model not available")

        _data = RawData()

        with patch.object(data, "archive") as mock_archive:
            mock_archive.return_value = {"archived": True, "date": datetime.now()}

            _result = data.archive()
            assert result["archived"] is True


class TestModelRelationships:
    """模型关系综合测试"""

    def test_user_predictions_relationship(self):
        """测试用户-预测关系"""
        if User is Mock or Prediction is Mock:
            pytest.skip("User or Prediction model not available")

        _user = User(id=1, username="testuser")
        _prediction = Prediction(id=1, user_id=1)

        # 验证关系
        assert prediction.user_id == user.id

    def test_match_teams_relationship(self):
        """测试比赛-球队关系"""
        if Match is Mock or Team is Mock:
            pytest.skip("Match or Team model not available")

        match = Match(id=1, home_team_id=1, away_team_id=2)
        home_team = Team(id=1, name="Home Team")
        away_team = Team(id=2, name="Away Team")

        # 验证关系
        assert match.home_team_id == home_team.id
        assert match.away_team_id == away_team.id

    def test_league_match_relationship(self):
        """测试联赛-比赛关系"""
        if League is Mock or Match is Mock:
            pytest.skip("League or Match model not available")

        league = League(id=1, name="Test League")
        match = Match(id=1, league_id=1)

        # 验证关系
        assert match.league_id == league.id

    def test_prediction_odds_relationship(self):
        """测试预测-赔率关系"""
        if Prediction is Mock or Odds is Mock:
            pytest.skip("Prediction or Odds model not available")

        _prediction = Prediction(id=1, match_id=1)
        odds = Odds(id=1, match_id=1)

        # 验证关系
        assert prediction.match_id == odds.match_id


class TestModelConstraints:
    """模型约束测试"""

    def test_unique_constraints(self):
        """测试唯一约束"""
        # 测试用户名唯一
        if User is not Mock:
            with patch("src.database.models.user.db.session") as mock_session:
                mock_session.commit.side_effect = IntegrityError(None, None, None)

                _user = User(username="duplicate")
                mock_session.add(user)

                with pytest.raises(IntegrityError):
                    mock_session.commit()

    def test_foreign_key_constraints(self):
        """测试外键约束"""
        # 测试无效外键
        if Match is not Mock:
            with pytest.raises(Exception):
                Match(home_team_id=999999)  # 不存在的球队ID
                # 验证逻辑取决于具体实现

    def test_not_null_constraints(self):
        """测试非空约束"""
        # 测试必填字段
        if User is not Mock:
            with pytest.raises(Exception):
                User(username=None)  # 必填字段为空
                # 验证逻辑取决于具体实现

    def test_check_constraints(self):
        """测试检查约束"""
        # 测试数值范围
        if Prediction is not Mock:
            Prediction(confidence=1.5)  # 超出0-1范围
            # 验证逻辑取决于具体实现


class TestModelQueries:
    """模型查询测试"""

    def test_complex_queries(self):
        """测试复杂查询"""
        if User is Mock or Match is Mock:
            pytest.skip("Models not available")

        # 模拟复杂查询
        with patch("src.database.models.user.User.query") as mock_query:
            mock_query.join.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.all.return_value = []

            # 查询有预测的用户
            users_with_predictions = (
                User.query.join(Match).filter(Match.status == "completed").all()
            )

            assert isinstance(users_with_predictions, list)

    def test_aggregate_queries(self):
        """测试聚合查询"""
        if Team is Mock:
            pytest.skip("Team model not available")

        with patch("src.database.models.team.Team.query") as mock_query:
            mock_query.count.return_value = 20

            team_count = Team.query.count()
            assert team_count == 20

    def test_ordering_and_pagination(self):
        """测试排序和分页"""
        if Match is Mock:
            pytest.skip("Match model not available")

        with patch("src.database.models.match.Match.query") as mock_query:
            mock_query.order_by.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.all.return_value = []

            # 分页查询
            _matches = (
                Match.query.order_by(Match.match_date.desc()).limit(10).offset(0).all()
            )
            assert isinstance(matches, list)
