"""
Bronze层原始数据模型测试

测试原始比赛数据、赔率数据和比分数据模型的功能，
包括数据验证、JSONB操作、业务逻辑等。

基于 DATA_DESIGN.md 第2.1节Bronze层设计的测试覆盖。
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.base import Base
from src.database.models.raw_data import RawMatchData, RawOddsData, RawScoresData


@pytest.fixture(scope="function")
def session():
    """创建临时数据库会话"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


@pytest.fixture
def sample_match_json():
    """示例比赛JSON数据"""
    return {
        "match_id": "12345",
        "league": {"id": "EPL", "name": "英超联赛"},
        "homeTeam": {"id": "MUN", "name": "曼联"},
        "awayTeam": {"id": "LIV", "name": "利物浦"},
        "match_time": "2025-09-15T15:00:00Z",
        "status": "scheduled",
        "venue": "老特拉福德",
    }


@pytest.fixture
def sample_odds_json():
    """示例赔率JSON数据"""
    return {
        "match_id": "12345",
        "bookmaker": "bet365",
        "market": "1x2",
        "outcomes": [
            {"name": "home", "price": 2.10},
            {"name": "draw", "price": 3.20},
            {"name": "away", "price": 3.40},
        ],
        "last_update": "2025-09-15T14:30:00Z",
    }


@pytest.fixture
def sample_scores_json():
    """示例比分JSON数据"""
    return {
        "match_id": "12345",
        "status": "live",
        "minute": 67,
        "home_score": 1,
        "away_score": 2,
        "half_time_home": 1,
        "half_time_away": 1,
        "events": [
            {"type": "goal", "minute": 23, "player": "B.费尔南德斯", "team": "home"},
            {"type": "goal", "minute": 45, "player": "萨拉赫", "team": "away"},
            {"type": "goal", "minute": 67, "player": "马内", "team": "away"},
        ],
    }


class TestRawMatchDataModel:
    """测试RawMatchData模型"""

    def test_create_raw_match_data(self, session, sample_match_json):
        """测试创建原始比赛数据"""
        raw_match = RawMatchData(
            data_source="football-api",
            raw_data=sample_match_json,
            collected_at=datetime.utcnow(),
            external_match_id="12345",
            external_league_id="EPL",
            match_time=datetime(2025, 9, 15, 15, 0, 0),
        )

        session.add(raw_match)
        session.commit()

        assert raw_match.id is not None
        assert raw_match.data_source == "football-api"
        assert raw_match.raw_data == sample_match_json
        assert raw_match.external_match_id == "12345"
        assert not raw_match.is_processed
        assert raw_match.created_at is not None

    def test_data_source_validation(self, session):
        """测试数据源验证"""
        with pytest.raises(ValueError, match="Data source cannot be empty"):
            RawMatchData(
                data_source="  ",  # 空白字符串
                raw_data={},
                collected_at=datetime.utcnow(),
            )

    def test_mark_processed(self, session, sample_match_json):
        """测试标记为已处理"""
        raw_match = RawMatchData(
            data_source="test-api",
            raw_data=sample_match_json,
            collected_at=datetime.utcnow(),
        )

        session.add(raw_match)
        session.commit()

        assert not raw_match.is_processed

        raw_match.mark_processed()
        assert raw_match.is_processed

    def test_get_raw_data_field(self, session, sample_match_json):
        """测试获取原始数据字段"""
        raw_match = RawMatchData(
            data_source="test-api",
            raw_data=sample_match_json,
            collected_at=datetime.utcnow(),
        )

        # 测试深层字段访问
        assert raw_match.get_raw_data_field("homeTeam.name") == "曼联"
        assert raw_match.get_raw_data_field("awayTeam.id") == "LIV"
        assert raw_match.get_raw_data_field("league.name") == "英超联赛"

        # 测试不存在的字段
        assert raw_match.get_raw_data_field("nonexistent.field") is None
        assert raw_match.get_raw_data_field("homeTeam.nonexistent") is None

    def test_get_raw_data_field_empty_data(self, session):
        """测试空数据的字段获取"""
        raw_match = RawMatchData(
            data_source="test-api", raw_data=None, collected_at=datetime.utcnow()
        )

        assert raw_match.get_raw_data_field("any.field") is None

    def test_repr_string(self, session, sample_match_json):
        """测试字符串表示"""
        raw_match = RawMatchData(
            data_source="test-api",
            raw_data=sample_match_json,
            collected_at=datetime.utcnow(),
            external_match_id="12345",
        )

        session.add(raw_match)
        session.commit()

        repr_str = repr(raw_match)
        assert "RawMatchData" in repr_str
        assert "test-api" in repr_str
        assert "12345" in repr_str
        assert "False" in repr_str  # processed=False


class TestRawOddsDataModel:
    """测试RawOddsData模型"""

    def test_create_raw_odds_data(self, session, sample_odds_json):
        """测试创建原始赔率数据"""
        raw_odds = RawOddsData(
            data_source="odds-api",
            raw_data=sample_odds_json,
            collected_at=datetime.utcnow(),
            external_match_id="12345",
            bookmaker="bet365",
            market_type="1x2",
        )

        session.add(raw_odds)
        session.commit()

        assert raw_odds.id is not None
        assert raw_odds.data_source == "odds-api"
        assert raw_odds.bookmaker == "bet365"
        assert raw_odds.market_type == "1x2"
        assert not raw_odds.is_processed

    def test_get_odds_values(self, session, sample_odds_json):
        """测试提取赔率值"""
        raw_odds = RawOddsData(
            data_source="odds-api",
            raw_data=sample_odds_json,
            collected_at=datetime.utcnow(),
        )

        odds_values = raw_odds.get_odds_values()

        assert odds_values is not None
        assert odds_values["home"] == 2.10
        assert odds_values["draw"] == 3.20
        assert odds_values["away"] == 3.40

    def test_get_odds_values_empty_outcomes(self, session):
        """测试空outcomes的赔率提取"""
        odds_json = {"match_id": "12345", "bookmaker": "bet365", "outcomes": []}

        raw_odds = RawOddsData(
            data_source="odds-api", raw_data=odds_json, collected_at=datetime.utcnow()
        )

        odds_values = raw_odds.get_odds_values()
        assert odds_values is None

    def test_get_odds_values_invalid_data(self, session):
        """测试无效数据的赔率提取"""
        raw_odds = RawOddsData(
            data_source="odds-api", raw_data=None, collected_at=datetime.utcnow()
        )

        odds_values = raw_odds.get_odds_values()
        assert odds_values is None

    def test_repr_string(self, session, sample_odds_json):
        """测试字符串表示"""
        raw_odds = RawOddsData(
            data_source="odds-api",
            raw_data=sample_odds_json,
            collected_at=datetime.utcnow(),
            external_match_id="12345",
            bookmaker="bet365",
        )

        session.add(raw_odds)
        session.commit()

        repr_str = repr(raw_odds)
        assert "RawOddsData" in repr_str
        assert "odds-api" in repr_str
        assert "12345" in repr_str
        assert "bet365" in repr_str


class TestRawScoresDataModel:
    """测试RawScoresData模型"""

    def test_create_raw_scores_data(self, session, sample_scores_json):
        """测试创建原始比分数据"""
        raw_scores = RawScoresData(
            data_source="live-api",
            raw_data=sample_scores_json,
            collected_at=datetime.utcnow(),
            external_match_id="12345",
            match_status="live",
            home_score=1,
            away_score=2,
            match_minute=67,
        )

        session.add(raw_scores)
        session.commit()

        assert raw_scores.id is not None
        assert raw_scores.data_source == "live-api"
        assert raw_scores.match_status == "live"
        assert raw_scores.home_score == 1
        assert raw_scores.away_score == 2
        assert raw_scores.match_minute == 67
        assert not raw_scores.is_processed

    def test_score_validation_valid(self, session):
        """测试有效比分验证"""
        raw_scores = RawScoresData(
            data_source="live-api",
            raw_data={},
            collected_at=datetime.utcnow(),
            home_score=3,
            away_score=1,
        )

        session.add(raw_scores)
        session.commit()

        assert raw_scores.home_score == 3
        assert raw_scores.away_score == 1

    def test_score_validation_invalid(self, session):
        """测试无效比分验证"""
        with pytest.raises(ValueError, match="Score must be between 0 and 99"):
            raw_scores = RawScoresData(
                data_source="live-api",
                raw_data={},
                collected_at=datetime.utcnow(),
                home_score=100,  # 超出范围
            )
            session.add(raw_scores)
            session.flush()

    def test_score_validation_negative(self, session):
        """测试负数比分验证"""
        with pytest.raises(ValueError, match="Score must be between 0 and 99"):
            raw_scores = RawScoresData(
                data_source="live-api",
                raw_data={},
                collected_at=datetime.utcnow(),
                away_score=-1,  # 负数
            )
            session.add(raw_scores)
            session.flush()

    def test_is_live_property(self, session):
        """测试是否为直播状态"""
        # 测试直播状态
        live_statuses = ["live", "in_progress", "1H", "2H"]
        for status in live_statuses:
            raw_scores = RawScoresData(
                data_source="live-api",
                raw_data={},
                collected_at=datetime.utcnow(),
                match_status=status,
            )
            assert raw_scores.is_live

        # 测试非直播状态
        non_live_statuses = ["scheduled", "finished", "postponed"]
        for status in non_live_statuses:
            raw_scores = RawScoresData(
                data_source="live-api",
                raw_data={},
                collected_at=datetime.utcnow(),
                match_status=status,
            )
            assert not raw_scores.is_live

    def test_is_finished_property(self, session):
        """测试是否为已结束状态"""
        # 测试已结束状态
        finished_statuses = ["finished", "full_time", "ft"]
        for status in finished_statuses:
            raw_scores = RawScoresData(
                data_source="live-api",
                raw_data={},
                collected_at=datetime.utcnow(),
                match_status=status,
            )
            assert raw_scores.is_finished

        # 测试未结束状态
        non_finished_statuses = ["scheduled", "live", "1H", "2H"]
        for status in non_finished_statuses:
            raw_scores = RawScoresData(
                data_source="live-api",
                raw_data={},
                collected_at=datetime.utcnow(),
                match_status=status,
            )
            assert not raw_scores.is_finished

    def test_get_score_info(self, session, sample_scores_json):
        """测试获取比分信息"""
        raw_scores = RawScoresData(
            data_source="live-api",
            raw_data=sample_scores_json,
            collected_at=datetime.utcnow(),
            external_match_id="12345",
            match_status="live",
            home_score=1,
            away_score=2,
            match_minute=67,
        )

        score_info = raw_scores.get_score_info()

        assert score_info is not None
        assert score_info["home_score"] == 1
        assert score_info["away_score"] == 2
        assert score_info["status"] == "live"
        assert score_info["minute"] == 67
        assert score_info["half_time_home"] == 1
        assert score_info["half_time_away"] == 1
        assert len(score_info["events"]) == 3

    def test_get_score_info_empty_data(self, session):
        """测试空数据的比分信息获取"""
        raw_scores = RawScoresData(
            data_source="live-api", raw_data=None, collected_at=datetime.utcnow()
        )

        score_info = raw_scores.get_score_info()
        assert score_info is None

    def test_get_latest_events(self, session, sample_scores_json):
        """测试获取最新比赛事件"""
        raw_scores = RawScoresData(
            data_source="live-api",
            raw_data=sample_scores_json,
            collected_at=datetime.utcnow(),
        )

        # 获取所有事件（按时间倒序）
        all_events = raw_scores.get_latest_events()
        assert len(all_events) == 3
        assert all_events[0]["minute"] == 67  # 最新的在前
        assert all_events[1]["minute"] == 45
        assert all_events[2]["minute"] == 23

        # 过滤进球事件
        goal_events = raw_scores.get_latest_events(event_type="goal")
        assert len(goal_events) == 3
        for event in goal_events:
            assert event["type"] == "goal"

        # 过滤不存在的事件类型
        card_events = raw_scores.get_latest_events(event_type="card")
        assert len(card_events) == 0

    def test_get_latest_events_no_events(self, session):
        """测试无事件数据的情况"""
        raw_scores = RawScoresData(
            data_source="live-api",
            raw_data={"match_id": "12345"},  # 没有events字段
            collected_at=datetime.utcnow(),
        )

        events = raw_scores.get_latest_events()
        assert events == []

    def test_get_latest_events_empty_raw_data(self, session):
        """测试空原始数据的事件获取"""
        raw_scores = RawScoresData(
            data_source="live-api", raw_data=None, collected_at=datetime.utcnow()
        )

        events = raw_scores.get_latest_events()
        assert events == []

    def test_repr_string(self, session, sample_scores_json):
        """测试字符串表示"""
        raw_scores = RawScoresData(
            data_source="live-api",
            raw_data=sample_scores_json,
            collected_at=datetime.utcnow(),
            external_match_id="12345",
            match_status="live",
            home_score=1,
            away_score=2,
        )

        session.add(raw_scores)
        session.commit()

        repr_str = repr(raw_scores)
        assert "RawScoresData" in repr_str
        assert "live-api" in repr_str
        assert "12345" in repr_str
        assert "1-2" in repr_str
        assert "live" in repr_str


class TestBronzeLayerIntegration:
    """测试Bronze层模型的集成功能"""

    def test_all_models_creation(
        self, session, sample_match_json, sample_odds_json, sample_scores_json
    ):
        """测试所有Bronze层模型的创建"""
        # 创建比赛数据
        raw_match = RawMatchData(
            data_source="match-api",
            raw_data=sample_match_json,
            collected_at=datetime.utcnow(),
            external_match_id="12345",
        )

        # 创建赔率数据
        raw_odds = RawOddsData(
            data_source="odds-api",
            raw_data=sample_odds_json,
            collected_at=datetime.utcnow(),
            external_match_id="12345",
            bookmaker="bet365",
        )

        # 创建比分数据
        raw_scores = RawScoresData(
            data_source="live-api",
            raw_data=sample_scores_json,
            collected_at=datetime.utcnow(),
            external_match_id="12345",
            match_status="live",
            home_score=1,
            away_score=2,
        )

        session.add_all([raw_match, raw_odds, raw_scores])
        session.commit()

        # 验证所有记录都已创建
        assert raw_match.id is not None
        assert raw_odds.id is not None
        assert raw_scores.id is not None

        # 验证外部ID一致性
        assert (
            raw_match.external_match_id
            == raw_odds.external_match_id
            == raw_scores.external_match_id
        )

    def test_batch_processing_workflow(self, session, sample_match_json):
        """测试批量处理工作流"""
        # 创建多个未处理的记录
        records = []
        for i in range(5):
            record = RawMatchData(
                data_source="batch-api",
                raw_data={**sample_match_json, "match_id": f"match_{i}"},
                collected_at=datetime.utcnow(),
                external_match_id=f"match_{i}",
            )
            records.append(record)

        session.add_all(records)
        session.commit()

        # 验证所有记录都未处理
        unprocessed_count = (
            session.query(RawMatchData).filter_by(processed=False).count()
        )
        assert unprocessed_count == 5

        # 模拟处理流程
        for record in records[:3]:  # 处理前3个
            record.mark_processed()
        session.commit()

        # 验证处理状态
        processed_count = session.query(RawMatchData).filter_by(processed=True).count()
        unprocessed_count = (
            session.query(RawMatchData).filter_by(processed=False).count()
        )

        assert processed_count == 3
        assert unprocessed_count == 2

    def test_data_quality_constraints(self, session):
        """测试数据质量约束"""
        # 测试必需字段约束
        with pytest.raises(ValueError, match="Data source cannot be empty"):
            RawMatchData(
                data_source=None,  # None值会被转换为空字符串触发验证
                raw_data={},
                collected_at=datetime.utcnow(),
            )

    def test_timestamp_fields(self, session, sample_match_json):
        """测试时间戳字段"""
        before_create = datetime.utcnow()

        raw_match = RawMatchData(
            data_source="time-test",
            raw_data=sample_match_json,
            collected_at=before_create,
        )

        session.add(raw_match)
        session.commit()

        # 验证创建时间在合理范围内（允许1秒误差）
        assert abs((raw_match.created_at - before_create).total_seconds()) < 1
        assert raw_match.collected_at == before_create
