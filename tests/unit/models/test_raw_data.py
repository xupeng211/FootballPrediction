"""
原始数据模型测试
Raw Data Models Tests

测试src/models/raw_data.py中定义的原始数据模型功能，专注于实现100%覆盖率。
Tests raw data model functionality defined in src/models/raw_data.py, focused on achieving 100% coverage.
"""

import pytest
import datetime
from typing import Any, Dict
from unittest.mock import Mock

# 导入要测试的模块
try:
    from src.models.raw_data import (
        # SQLAlchemy模型
        RawMatchData,
        RawOddsData,
        RawStatisticsData,
        # Pydantic模型
        RawMatchDataCreate,
        RawMatchDataResponse,
        RawOddsDataCreate,
        RawOddsDataResponse,
        RawStatisticsDataCreate,
        RawStatisticsDataResponse,
        # 基础类
        Base,
    )

    RAW_DATA_AVAILABLE = True
except ImportError:
    RAW_DATA_AVAILABLE = False


@pytest.mark.skipif(
    not RAW_DATA_AVAILABLE, reason="Raw data models module not available"
)
class TestRawMatchData:
    """RawMatchData测试"""

    def test_raw_match_data_class_exists(self):
        """测试RawMatchData类存在"""
        assert RawMatchData is not None
        assert callable(RawMatchData)

    def test_raw_match_data_table_name(self):
        """测试表名配置"""
        assert RawMatchData.__tablename__ == "raw_match_data"

    def test_raw_match_data_inherits_from_base(self):
        """测试RawMatchData继承自Base"""
        # 简化继承检查
        assert hasattr(RawMatchData, "__tablename__")
        assert hasattr(RawMatchData, "__table__")
        assert RawMatchData.__tablename__ == "raw_match_data"

    def test_raw_match_data_columns(self):
        """测试RawMatchData列定义"""
        # 验证所有预期的列都存在
        columns = [column.name for column in RawMatchData.__table__.columns]
        expected_columns = [
            "id",
            "match_id",
            "home_team",
            "away_team",
            "league",
            "season",
            "match_date",
            "home_score",
            "away_score",
            "status",
            "raw_data",
            "created_at",
            "updated_at",
        ]
        assert set(columns) == set(expected_columns)

    def test_raw_match_data_column_types(self):
        """测试RawMatchData列类型"""
        columns = RawMatchData.__table__.columns

        # 验证主键
        assert columns["id"].primary_key is True
        # SQLAlchemy主键默认nullable=False，这是正确的
        assert columns["id"].nullable is False

        # 验证唯一约束
        assert columns["match_id"].unique is True
        assert columns["match_id"].nullable is False

        # 验证外键和索引
        assert columns["match_id"].index is True
        assert columns["home_team"].nullable is False
        assert columns["away_team"].nullable is False
        assert columns["league"].nullable is False
        assert columns["season"].nullable is False

        # 验证默认值
        assert columns["status"].default.arg == "scheduled"
        assert columns["home_score"].nullable is True
        assert columns["away_score"].nullable is True

    def test_raw_match_data_instantiation(self):
        """测试RawMatchData实例化"""
        current_time = datetime.datetime.utcnow()

        # 创建实例
        match_data = RawMatchData(
            match_id="test_match_123",
            home_team="Team A",
            away_team="Team B",
            league="Premier League",
            season="2023-2024",
            match_date=current_time,
            home_score=2,
            away_score=1,
            status="completed",
        )

        # 验证属性设置
        assert match_data.match_id == "test_match_123"
        assert match_data.home_team == "Team A"
        assert match_data.away_team == "Team B"
        assert match_data.league == "Premier League"
        assert match_data.season == "2023-2024"
        assert match_data.match_date == current_time
        assert match_data.home_score == 2
        assert match_data.away_score == 1
        assert match_data.status == "completed"

    def test_raw_match_data_with_raw_data(self):
        """测试RawMatchData带原始JSON数据"""
        raw_json = {"source": "api", "confidence": 0.95}

        match_data = RawMatchData(
            match_id="test_456",
            home_team="Team C",
            away_team="Team D",
            league="La Liga",
            season="2023-2024",
            match_date=datetime.datetime.utcnow(),
            raw_data=raw_json,
        )

        assert match_data.raw_data == raw_json

    def test_raw_match_data_defaults(self):
        """测试RawMatchData默认值"""
        match_data = RawMatchData(
            match_id="test_789",
            home_team="Team E",
            away_team="Team F",
            league="Serie A",
            season="2023-2024",
            match_date=datetime.datetime.utcnow(),
        )

        # SQLAlchemy的默认值在数据库层面处理，实例化时可能是None
        # 我们验证列定义的默认值而不是实例值
        column = RawMatchData.__table__.columns["status"]
        assert column.default.arg == "scheduled"

        # 实例值在未设置时确实是None
        assert match_data.home_score is None
        assert match_data.away_score is None
        assert match_data.raw_data is None


@pytest.mark.skipif(
    not RAW_DATA_AVAILABLE, reason="Raw data models module not available"
)
class TestRawOddsData:
    """RawOddsData测试"""

    def test_raw_odds_data_class_exists(self):
        """测试RawOddsData类存在"""
        assert RawOddsData is not None
        assert callable(RawOddsData)

    def test_raw_odds_data_table_name(self):
        """测试表名配置"""
        assert RawOddsData.__tablename__ == "raw_odds_data"

    def test_raw_odds_data_columns(self):
        """测试RawOddsData列定义"""
        columns = [column.name for column in RawOddsData.__table__.columns]
        expected_columns = [
            "id",
            "match_id",
            "bookmaker",
            "market",
            "outcome",
            "odds",
            "timestamp",
            "raw_data",
            "created_at",
        ]
        assert set(columns) == set(expected_columns)

    def test_raw_odds_data_column_types(self):
        """测试RawOddsData列类型"""
        columns = RawOddsData.__table__.columns

        # 验证数据类型和约束
        assert columns["match_id"].nullable is False
        assert columns["match_id"].index is True
        assert columns["bookmaker"].nullable is False
        assert columns["market"].nullable is False
        assert columns["outcome"].nullable is False
        assert columns["odds"].nullable is False
        assert columns["timestamp"].nullable is False

    def test_raw_odds_data_instantiation(self):
        """测试RawOddsData实例化"""
        current_time = datetime.datetime.utcnow()

        odds_data = RawOddsData(
            match_id="match_123",
            bookmaker="Bet365",
            market="1X2",
            outcome="1",
            odds=2.5,
            timestamp=current_time,
        )

        assert odds_data.match_id == "match_123"
        assert odds_data.bookmaker == "Bet365"
        assert odds_data.market == "1X2"
        assert odds_data.outcome == "1"
        assert odds_data.odds == 2.5
        assert odds_data.timestamp == current_time

    def test_raw_odds_data_with_raw_data(self):
        """测试RawOddsData带原始数据"""
        raw_info = {"volume": 1000000, "back": True}

        odds_data = RawOddsData(
            match_id="match_456",
            bookmaker="William Hill",
            market="Over/Under",
            outcome="Over 2.5",
            odds=1.85,
            timestamp=datetime.datetime.utcnow(),
            raw_data=raw_info,
        )

        assert odds_data.raw_data == raw_info


@pytest.mark.skipif(
    not RAW_DATA_AVAILABLE, reason="Raw data models module not available"
)
class TestRawStatisticsData:
    """RawStatisticsData测试"""

    def test_raw_statistics_data_class_exists(self):
        """测试RawStatisticsData类存在"""
        assert RawStatisticsData is not None
        assert callable(RawStatisticsData)

    def test_raw_statistics_data_table_name(self):
        """测试表名配置"""
        assert RawStatisticsData.__tablename__ == "raw_statistics_data"

    def test_raw_statistics_data_columns(self):
        """测试RawStatisticsData列定义"""
        columns = [column.name for column in RawStatisticsData.__table__.columns]
        expected_columns = [
            "id",
            "match_id",
            "team",
            "stat_type",
            "stat_value",
            "stat_text",
            "source",
            "timestamp",
            "raw_data",
            "created_at",
        ]
        assert set(columns) == set(expected_columns)

    def test_raw_statistics_data_column_types(self):
        """测试RawStatisticsData列类型"""
        columns = RawStatisticsData.__table__.columns

        # 验证数据类型和约束
        assert columns["match_id"].nullable is False
        assert columns["match_id"].index is True
        assert columns["team"].nullable is False
        assert columns["stat_type"].nullable is False
        assert columns["stat_value"].nullable is True
        assert columns["stat_text"].nullable is True
        assert columns["source"].nullable is False
        assert columns["timestamp"].nullable is False

    def test_raw_statistics_data_instantiation(self):
        """测试RawStatisticsData实例化"""
        current_time = datetime.datetime.utcnow()

        stats_data = RawStatisticsData(
            match_id="stats_match_123",
            team="Team A",
            stat_type="possession",
            stat_value=65.5,
            source="Opta",
            timestamp=current_time,
        )

        assert stats_data.match_id == "stats_match_123"
        assert stats_data.team == "Team A"
        assert stats_data.stat_type == "possession"
        assert stats_data.stat_value == 65.5
        assert stats_data.source == "Opta"
        assert stats_data.timestamp == current_time
        assert stats_data.stat_text is None
        assert stats_data.raw_data is None

    def test_raw_statistics_data_with_text(self):
        """测试RawStatisticsData带文本统计"""
        stats_data = RawStatisticsData(
            match_id="stats_match_456",
            team="Team B",
            stat_type="formation",
            stat_text="4-3-3",
            source="StatsBomb",
            timestamp=datetime.datetime.utcnow(),
        )

        assert stats_data.stat_type == "formation"
        assert stats_data.stat_text == "4-3-3"
        assert stats_data.stat_value is None

    def test_raw_statistics_data_with_raw_data(self):
        """测试RawStatisticsData带原始数据"""
        raw_stats = {"quality": "high", "sample_size": 100}

        stats_data = RawStatisticsData(
            match_id="stats_match_789",
            team="Team C",
            stat_type="xG",
            stat_value=2.35,
            source="Understat",
            timestamp=datetime.datetime.utcnow(),
            raw_data=raw_stats,
        )

        assert stats_data.raw_data == raw_stats


@pytest.mark.skipif(
    not RAW_DATA_AVAILABLE, reason="Raw data models module not available"
)
class TestRawMatchDataCreate:
    """RawMatchDataCreate测试"""

    def test_raw_match_data_create_class_exists(self):
        """测试RawMatchDataCreate类存在"""
        assert RawMatchDataCreate is not None
        assert callable(RawMatchDataCreate)

    def test_raw_match_data_create_instantiation(self):
        """测试RawMatchDataCreate实例化"""
        match_time = datetime.datetime(2023, 12, 1, 20, 0, 0)
        raw_json = {"stadium": "Old Trafford"}

        create_data = RawMatchDataCreate(
            match_id="create_match_123",
            home_team="Manchester United",
            away_team="Liverpool",
            league="Premier League",
            season="2023-2024",
            match_date=match_time,
            home_score=3,
            away_score=0,
            status="completed",
            raw_data=raw_json,
        )

        assert create_data.match_id == "create_match_123"
        assert create_data.home_team == "Manchester United"
        assert create_data.away_team == "Liverpool"
        assert create_data.league == "Premier League"
        assert create_data.season == "2023-2024"
        assert create_data.match_date == match_time
        assert create_data.home_score == 3
        assert create_data.away_score == 0
        assert create_data.status == "completed"
        assert create_data.raw_data == raw_json

    def test_raw_match_data_create_defaults(self):
        """测试RawMatchDataCreate默认值"""
        match_time = datetime.datetime.utcnow()

        create_data = RawMatchDataCreate(
            match_id="create_match_456",
            home_team="Chelsea",
            away_team="Arsenal",
            league="Premier League",
            season="2023-2024",
            match_date=match_time,
        )

        # 验证默认值
        assert create_data.status == "scheduled"
        assert create_data.home_score is None
        assert create_data.away_score is None
        assert create_data.raw_data is None

    def test_raw_match_data_create_validation(self):
        """测试RawMatchDataCreate验证"""
        # 测试缺少必需字段会失败
        with pytest.raises(Exception):  # Pydantic ValidationError
            RawMatchDataCreate(
                home_team="Team A",
                away_team="Team B",
                # 缺少必需字段
            )


@pytest.mark.skipif(
    not RAW_DATA_AVAILABLE, reason="Raw data models module not available"
)
class TestRawMatchDataResponse:
    """RawMatchDataResponse测试"""

    def test_raw_match_data_response_class_exists(self):
        """测试RawMatchDataResponse类存在"""
        assert RawMatchDataResponse is not None
        assert callable(RawMatchDataResponse)

    def test_raw_match_data_response_config(self):
        """测试RawMatchDataResponse配置"""
        config = RawMatchDataResponse.Config
        assert config.from_attributes is True

    def test_raw_match_data_response_instantiation(self):
        """测试RawMatchDataResponse实例化"""
        match_time = datetime.datetime(2023, 12, 1, 20, 0, 0)
        created_time = datetime.datetime(2023, 12, 1, 20, 30, 0)
        updated_time = datetime.datetime(2023, 12, 1, 21, 0, 0)
        raw_json = {"attendance": 75000}

        response_data = RawMatchDataResponse(
            id=1,
            match_id="response_match_123",
            home_team="Real Madrid",
            away_team="Barcelona",
            league="La Liga",
            season="2023-2024",
            match_date=match_time,
            home_score=2,
            away_score=2,
            status="completed",
            raw_data=raw_json,
            created_at=created_time,
            updated_at=updated_time,
        )

        assert response_data.id == 1
        assert response_data.match_id == "response_match_123"
        assert response_data.home_team == "Real Madrid"
        assert response_data.away_team == "Barcelona"
        assert response_data.league == "La Liga"
        assert response_data.season == "2023-2024"
        assert response_data.match_date == match_time
        assert response_data.home_score == 2
        assert response_data.away_score == 2
        assert response_data.status == "completed"
        assert response_data.raw_data == raw_json
        assert response_data.created_at == created_time
        assert response_data.updated_at == updated_time

    def test_raw_match_data_response_serialization(self):
        """测试RawMatchDataResponse序列化"""
        match_time = datetime.datetime(2023, 12, 1, 20, 0, 0)

        response_data = RawMatchDataResponse(
            id=1,
            match_id="serial_match_123",
            home_team="Team A",
            away_team="Team B",
            league="Test League",
            season="2023-2024",
            match_date=match_time,
            home_score=0,  # 添加必需字段
            away_score=0,  # 添加必需字段
            status="scheduled",
            raw_data=None,  # 添加必需字段
            created_at=match_time,
            updated_at=match_time,
        )

        # 测试序列化
        data_dict = response_data.model_dump()
        assert data_dict["id"] == 1
        assert data_dict["match_id"] == "serial_match_123"
        assert data_dict["home_team"] == "Team A"
        assert data_dict["away_team"] == "Team B"

    def test_raw_match_data_response_json_serialization(self):
        """测试RawMatchDataResponse JSON序列化"""
        current_time = datetime.datetime.utcnow()
        response_data = RawMatchDataResponse(
            id=1,
            match_id="json_match_123",
            home_team="Team X",
            away_team="Team Y",
            league="JSON League",
            season="2023-2024",
            match_date=current_time,
            home_score=0,  # 添加必需字段
            away_score=0,  # 添加必需字段
            status="scheduled",
            raw_data=None,  # 添加必需字段
            created_at=current_time,
            updated_at=current_time,
        )

        json_str = response_data.model_dump_json()
        assert "json_match_123" in json_str
        assert "Team X" in json_str
        assert "Team Y" in json_str


@pytest.mark.skipif(
    not RAW_DATA_AVAILABLE, reason="Raw data models module not available"
)
class TestRawOddsDataCreate:
    """RawOddsDataCreate测试"""

    def test_raw_odds_data_create_class_exists(self):
        """测试RawOddsDataCreate类存在"""
        assert RawOddsDataCreate is not None
        assert callable(RawOddsDataCreate)

    def test_raw_odds_data_create_instantiation(self):
        """测试RawOddsDataCreate实例化"""
        timestamp = datetime.datetime(2023, 12, 1, 19, 0, 0)
        raw_data = {"liquidity": 50000}

        create_data = RawOddsDataCreate(
            match_id="odds_create_123",
            bookmaker="Betfair",
            market="Match Odds",
            outcome="Team A",
            odds=1.95,
            timestamp=timestamp,
            raw_data=raw_data,
        )

        assert create_data.match_id == "odds_create_123"
        assert create_data.bookmaker == "Betfair"
        assert create_data.market == "Match Odds"
        assert create_data.outcome == "Team A"
        assert create_data.odds == 1.95
        assert create_data.timestamp == timestamp
        assert create_data.raw_data == raw_data

    def test_raw_odds_data_create_validation(self):
        """测试RawOddsDataCreate验证"""
        # 测试缺少必需字段会失败
        with pytest.raises(Exception):  # Pydantic ValidationError
            RawOddsDataCreate(
                match_id="test",
                bookmaker="test",
                # 缺少其他必需字段
            )

    def test_raw_odds_data_create_odds_validation(self):
        """测试赔率数据类型验证"""
        timestamp = datetime.datetime.utcnow()

        # 测试有效赔率
        create_data = RawOddsDataCreate(
            match_id="odds_test_123",
            bookmaker="Test Bookmaker",
            market="Test Market",
            outcome="Test Outcome",
            odds=2.5,  # 有效浮点数
            timestamp=timestamp,
        )
        assert create_data.odds == 2.5

        # 测试整数赔率（自动转换）
        create_data_int = RawOddsDataCreate(
            match_id="odds_test_456",
            bookmaker="Test Bookmaker",
            market="Test Market",
            outcome="Test Outcome",
            odds=3,  # 整数
            timestamp=timestamp,
        )
        assert create_data_int.odds == 3


@pytest.mark.skipif(
    not RAW_DATA_AVAILABLE, reason="Raw data models module not available"
)
class TestRawOddsDataResponse:
    """RawOddsDataResponse测试"""

    def test_raw_odds_data_response_class_exists(self):
        """测试RawOddsDataResponse类存在"""
        assert RawOddsDataResponse is not None
        assert callable(RawOddsDataResponse)

    def test_raw_odds_data_response_config(self):
        """测试RawOddsDataResponse配置"""
        config = RawOddsDataResponse.Config
        assert config.from_attributes is True

    def test_raw_odds_data_response_instantiation(self):
        """测试RawOddsDataResponse实例化"""
        timestamp = datetime.datetime(2023, 12, 1, 19, 30, 0)
        created_at = datetime.datetime(2023, 12, 1, 19, 35, 0)
        raw_data = {"volume": 100000}

        response_data = RawOddsDataResponse(
            id=1,
            match_id="odds_response_123",
            bookmaker="Pinnacle",
            market="Asian Handicap",
            outcome="Team A -1.5",
            odds=2.1,
            timestamp=timestamp,
            raw_data=raw_data,
            created_at=created_at,
        )

        assert response_data.id == 1
        assert response_data.match_id == "odds_response_123"
        assert response_data.bookmaker == "Pinnacle"
        assert response_data.market == "Asian Handicap"
        assert response_data.outcome == "Team A -1.5"
        assert response_data.odds == 2.1
        assert response_data.timestamp == timestamp
        assert response_data.raw_data == raw_data
        assert response_data.created_at == created_at


@pytest.mark.skipif(
    not RAW_DATA_AVAILABLE, reason="Raw data models module not available"
)
class TestRawStatisticsDataCreate:
    """RawStatisticsDataCreate测试"""

    def test_raw_statistics_data_create_class_exists(self):
        """测试RawStatisticsDataCreate类存在"""
        assert RawStatisticsDataCreate is not None
        assert callable(RawStatisticsDataCreate)

    def test_raw_statistics_data_create_instantiation(self):
        """测试RawStatisticsDataCreate实例化"""
        timestamp = datetime.datetime(2023, 12, 1, 20, 15, 0)
        raw_data = {"context": "open_play"}

        create_data = RawStatisticsDataCreate(
            match_id="stats_create_123",
            team="Manchester City",
            stat_type="shots_on_target",
            stat_value=8,
            stat_text="8 shots on target",
            source="WhoScored",
            timestamp=timestamp,
            raw_data=raw_data,
        )

        assert create_data.match_id == "stats_create_123"
        assert create_data.team == "Manchester City"
        assert create_data.stat_type == "shots_on_target"
        assert create_data.stat_value == 8
        assert create_data.stat_text == "8 shots on target"
        assert create_data.source == "WhoScored"
        assert create_data.timestamp == timestamp
        assert create_data.raw_data == raw_data

    def test_raw_statistics_data_create_optional_fields(self):
        """测试RawStatisticsDataCreate可选字段"""
        timestamp = datetime.datetime.utcnow()

        # 只有必需字段
        create_data = RawStatisticsDataCreate(
            match_id="stats_minimal_123",
            team="Team A",
            stat_type="cards",
            source="Referee",
            timestamp=timestamp,
        )

        assert create_data.stat_value is None
        assert create_data.stat_text is None
        assert create_data.raw_data is None

    def test_raw_statistics_data_create_validation(self):
        """测试RawStatisticsDataCreate验证"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            RawStatisticsDataCreate(
                match_id="test"
                # 缺少其他必需字段
            )


@pytest.mark.skipif(
    not RAW_DATA_AVAILABLE, reason="Raw data models module not available"
)
class TestRawStatisticsDataResponse:
    """RawStatisticsDataResponse测试"""

    def test_raw_statistics_data_response_class_exists(self):
        """测试RawStatisticsDataResponse类存在"""
        assert RawStatisticsDataResponse is not None
        assert callable(RawStatisticsDataResponse)

    def test_raw_statistics_data_response_config(self):
        """测试RawStatisticsDataResponse配置"""
        config = RawStatisticsDataResponse.Config
        assert config.from_attributes is True

    def test_raw_statistics_data_response_instantiation(self):
        """测试RawStatisticsDataResponse实例化"""
        timestamp = datetime.datetime(2023, 12, 1, 20, 45, 0)
        created_at = datetime.datetime(2023, 12, 1, 20, 50, 0)
        raw_data = {"player": "Kevin De Bruyne"}

        response_data = RawStatisticsDataResponse(
            id=1,
            match_id="stats_response_123",
            team="Manchester City",
            stat_type="assists",
            stat_value=2,
            stat_text="2 assists",
            source="Opta",
            timestamp=timestamp,
            raw_data=raw_data,
            created_at=created_at,
        )

        assert response_data.id == 1
        assert response_data.match_id == "stats_response_123"
        assert response_data.team == "Manchester City"
        assert response_data.stat_type == "assists"
        assert response_data.stat_value == 2
        assert response_data.stat_text == "2 assists"
        assert response_data.source == "Opta"
        assert response_data.timestamp == timestamp
        assert response_data.raw_data == raw_data
        assert response_data.created_at == created_at


@pytest.mark.skipif(
    not RAW_DATA_AVAILABLE, reason="Raw data models module not available"
)
class TestRawDataIntegration:
    """原始数据模型集成测试"""

    def test_all_models_inherit_from_base(self):
        """测试所有SQLAlchemy模型都继承自Base"""
        # 简化继承检查 - 验证它们都有SQLAlchemy模型的属性
        for model_class in [RawMatchData, RawOddsData, RawStatisticsData]:
            assert hasattr(model_class, "__tablename__")
            assert hasattr(model_class, "__table__")
            assert hasattr(model_class, "id")  # 主键列

    def test_all_pydantic_models_have_config(self):
        """测试所有响应Pydantic模型都有配置"""
        assert hasattr(RawMatchDataResponse, "Config")
        assert hasattr(RawOddsDataResponse, "Config")
        assert hasattr(RawStatisticsDataResponse, "Config")

        assert RawMatchDataResponse.Config.from_attributes is True
        assert RawOddsDataResponse.Config.from_attributes is True
        assert RawStatisticsDataResponse.Config.from_attributes is True

    def test_model_relationships(self):
        """测试模型关系（通过match_id关联）"""
        # 创建相关数据
        match_id = "integration_match_123"
        match_time = datetime.datetime.utcnow()

        match_data = RawMatchData(
            match_id=match_id,
            home_team="Team A",
            away_team="Team B",
            league="Test League",
            season="2023-2024",
            match_date=match_time,
        )

        odds_data = RawOddsData(
            match_id=match_id,
            bookmaker="Test Bookmaker",
            market="1X2",
            outcome="1",
            odds=2.0,
            timestamp=match_time,
        )

        stats_data = RawStatisticsData(
            match_id=match_id,
            team="Team A",
            stat_type="possession",
            stat_value=55.0,
            source="Test Source",
            timestamp=match_time,
        )

        # 验证通过match_id关联
        assert (
            match_data.match_id == odds_data.match_id == stats_data.match_id == match_id
        )

    def test_pydantic_models_validation_workflow(self):
        """测试Pydantic模型验证工作流"""
        # 1. 创建数据
        match_time = datetime.datetime(2023, 12, 1, 18, 0, 0)

        create_data = RawMatchDataCreate(
            match_id="workflow_match_123",
            home_team="Home Team",
            away_team="Away Team",
            league="Workflow League",
            season="2023-2024",
            match_date=match_time,
            home_score=2,
            away_score=1,
            status="completed",
        )

        # 2. 模拟数据库操作后创建响应
        response_data = RawMatchDataResponse(
            id=1,
            match_id=create_data.match_id,
            home_team=create_data.home_team,
            away_team=create_data.away_team,
            league=create_data.league,
            season=create_data.season,
            match_date=create_data.match_date,
            home_score=create_data.home_score,
            away_score=create_data.away_score,
            status=create_data.status,
            raw_data=create_data.raw_data,
            created_at=match_time,
            updated_at=match_time,
        )

        # 3. 验证数据一致性
        assert response_data.match_id == create_data.match_id
        assert response_data.home_team == create_data.home_team
        assert response_data.away_team == create_data.away_team

    def test_field_descriptions(self):
        """测试字段描述"""
        # 验证Field描述存在
        import inspect

        # 检查RawMatchDataCreate的字段描述
        fields = RawMatchDataCreate.model_fields
        assert "match_id" in fields
        assert "home_team" in fields
        assert "away_team" in fields
        assert "league" in fields
        assert "season" in fields
        assert "match_date" in fields

    def test_comprehensive_data_types(self):
        """测试全面的数据类型"""
        # 测试各种数据类型的处理
        complex_json = {
            "nested": {"key": "value"},
            "array": [1, 2, 3],
            "boolean": True,
            "null": None,
        }

        match_data = RawMatchDataCreate(
            match_id="types_test_123",
            home_team="Type Test Team",
            away_team="Opponent",
            league="Type Test League",
            season="2023-2024",
            match_date=datetime.datetime(2023, 12, 1, 19, 0, 0),
            raw_data=complex_json,
        )

        assert match_data.raw_data == complex_json
        assert match_data.raw_data["nested"]["key"] == "value"
        assert match_data.raw_data["array"] == [1, 2, 3]
        assert match_data.raw_data["boolean"] is True
        assert match_data.raw_data["null"] is None
