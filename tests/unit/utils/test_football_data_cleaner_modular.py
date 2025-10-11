"""
足球数据清洗器模块化测试
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch


def test_module_imports():
    """测试模块导入"""
    # 测试导入新模块
    from src.data.processing.football_data_cleaner_mod import (
        FootballDataCleaner,
        TimeProcessor,
        IDMapper,
        DataValidator,
        OddsProcessor,
    )

    assert FootballDataCleaner is not None
    assert TimeProcessor is not None
    assert IDMapper is not None
    assert DataValidator is not None
    assert OddsProcessor is not None


def test_time_processor():
    """测试时间处理器"""
    from src.data.processing.football_data_cleaner_mod import TimeProcessor

    processor = TimeProcessor()

    # 测试UTC时间转换
    # 带Z后缀的ISO时间
    utc_time = processor.to_utc_time("2024-01-01T12:00:00Z")
    assert utc_time is not None
    assert "Z" not in utc_time
    assert "+00:00" in utc_time

    # 带UTC后缀的时间
    utc_time = processor.to_utc_time("2024-01-01T12:00:00UTC")
    assert utc_time is not None

    # 无效时间格式
    invalid_time = processor.to_utc_time("invalid-time")
    assert invalid_time is None

    # 空值处理
    none_time = processor.to_utc_time(None)
    assert none_time is None

    # 测试赛季提取
    season_data = {"id": 2023}
    season = processor.extract_season(season_data)
    assert season == "2023"

    # 从日期构建赛季
    season_data = {
        "startDate": "2023-08-01T00:00:00Z",
        "endDate": "2024-05-31T23:59:59Z",
    }
    season = processor.extract_season(season_data)
    assert season == "2023-2024"

    # 空赛季数据
    none_season = processor.extract_season(None)
    assert none_season is None


def test_data_validator():
    """测试数据验证器"""
    from src.data.processing.football_data_cleaner_mod import DataValidator

    validator = DataValidator()

    # 测试比赛数据验证
    valid_match = {
        "id": 123,
        "homeTeam": {"id": 1, "name": "Team A"},
        "awayTeam": {"id": 2, "name": "Team B"},
        "utcDate": "2024-01-01T12:00:00Z",
    }
    assert validator.validate_match_data(valid_match) is True

    invalid_match = {"id": 123}
    assert validator.validate_match_data(invalid_match) is False

    # 测试比分验证
    valid_score = validator.validate_score(3)
    assert valid_score == 3

    invalid_score_high = validator.validate_score(100)
    assert invalid_score_high is None

    invalid_score_negative = validator.validate_score(-1)
    assert invalid_score_negative is None

    invalid_score_format = validator.validate_score("abc")
    assert invalid_score_format is None

    none_score = validator.validate_score(None)
    assert none_score is None

    # 测试比赛状态标准化
    assert validator.standardize_match_status("SCHEDULED") == "scheduled"
    assert validator.standardize_match_status("IN_PLAY") == "live"
    assert validator.standardize_match_status("FINISHED") == "finished"
    assert validator.standardize_match_status("POSTPONED") == "postponed"
    assert validator.standardize_match_status("CANCELLED") == "cancelled"
    assert validator.standardize_match_status("UNKNOWN") == "unknown"
    assert validator.standardize_match_status(None) == "unknown"
    assert validator.standardize_match_status("") == "unknown"

    # 测试场地名称清洗
    clean_venue = validator.clean_venue_name("  Old   Trafford  ")
    assert clean_venue == "Old Trafford"

    none_venue = validator.clean_venue_name(None)
    assert none_venue is None

    # 测试裁判姓名清洗
    referees = [
        {"role": "REFEREE", "name": "  Michael   Oliver  "},
        {"role": "ASSISTANT", "name": "Assistant 1"},
    ]
    referee_name = validator.clean_referee_name(referees)
    assert referee_name == "Michael Oliver"

    none_referee = validator.clean_referee_name(None)
    assert none_referee is None


def test_odds_processor():
    """测试赔率处理器"""
    from src.data.processing.football_data_cleaner_mod import OddsProcessor

    processor = OddsProcessor()

    # 测试赔率值验证
    assert processor.validate_odds_value(2.5) is True
    assert processor.validate_odds_value(1.01) is True
    assert processor.validate_odds_value(1.0) is False
    assert processor.validate_odds_value("2.5") is True
    assert processor.validate_odds_value("invalid") is False

    # 测试结果名称标准化
    assert processor.standardize_outcome_name("1") == "home"
    assert processor.standardize_outcome_name("X") == "draw"
    assert processor.standardize_outcome_name("2") == "away"
    assert processor.standardize_outcome_name("HOME") == "home"
    assert processor.standardize_outcome_name("Over") == "over"
    assert processor.standardize_outcome_name(None) == "unknown"
    assert processor.standardize_outcome_name("") == "unknown"

    # 测试博彩公司名称标准化
    assert processor.standardize_bookmaker_name("Bet365") == "bet365"
    assert processor.standardize_bookmaker_name("William Hill") == "william_hill"
    assert processor.standardize_bookmaker_name(None) == "unknown"

    # 测试市场类型标准化
    assert processor.standardize_market_type("h2h") == "1x2"
    assert processor.standardize_market_type("spreads") == "asian_handicap"
    assert processor.standardize_market_type("totals") == "over_under"
    assert processor.standardize_market_type("btts") == "both_teams_score"
    assert processor.standardize_market_type(None) == "unknown"

    # 测试赔率合理性验证
    consistent_outcomes = [
        {"name": "home", "price": 2.5},
        {"name": "draw", "price": 3.2},
        {"name": "away", "price": 2.8},
    ]
    assert processor.validate_odds_consistency(consistent_outcomes) is True

    # 空结果列表
    assert processor.validate_odds_consistency([]) is False

    # 测试隐含概率计算
    probabilities = processor.calculate_implied_probabilities(consistent_outcomes)
    assert "home" in probabilities
    assert "draw" in probabilities
    assert "away" in probabilities
    # 验证概率总和为1
    assert abs(sum(probabilities.values()) - 1.0) < 0.01

    # 测试结果处理
    raw_outcomes = [
        {"name": "1", "price": 2.5},
        {"name": "X", "price": 3.2},
        {"name": "invalid", "price": 0.5},  # 无效赔率
    ]
    cleaned = processor.process_outcomes(raw_outcomes)
    assert len(cleaned) == 2  # 只有两个有效结果
    assert cleaned[0]["name"] == "home"
    assert cleaned[0]["price"] == 2.5


@pytest.mark.asyncio
async def test_id_mapper():
    """测试ID映射器"""
    from src.data.processing.football_data_cleaner_mod import IDMapper
    from src.database.connection_mod import DatabaseManager

    # Mock数据库管理器
    db_manager = Mock(spec=DatabaseManager)
    mapper = IDMapper(db_manager)

    # 测试确定性ID生成
    id1 = mapper._deterministic_id("test_key", modulus=1000)
    id2 = mapper._deterministic_id("test_key", modulus=1000)
    assert id1 == id2  # 相同输入应该产生相同输出

    id3 = mapper._deterministic_id("different_key", modulus=1000)
    assert id1 != id3  # 不同输入应该产生不同输出

    # 测试球队ID映射（使用Mock）
    mock_session = AsyncMock()
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = 123
    mock_session.execute.return_value = mock_result

    # 正确配置async context manager mock
    mock_async_context = AsyncMock()
    mock_async_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_async_context.__aexit__ = AsyncMock(return_value=None)
    db_manager.get_async_session.return_value = mock_async_context

    team_data = {"id": 456, "name": "Test Team"}
    team_id = await mapper.map_team_id(team_data)
    assert team_id == 123

    # 测试联赛ID映射
    league_data = {"id": 789, "name": "Test League"}
    league_id = await mapper.map_league_id(league_data)
    assert league_id == 123


def test_football_data_cleaner_initialization():
    """测试足球数据清洗器初始化"""
    from src.data.processing.football_data_cleaner_mod import FootballDataCleaner

    with patch("src.database.connection.DatabaseManager"):
        cleaner = FootballDataCleaner()

        assert cleaner.time_processor is not None
        assert cleaner.id_mapper is not None
        assert cleaner.data_validator is not None
        assert cleaner.odds_processor is not None


@pytest.mark.asyncio
async def test_football_data_cleaner_methods():
    """测试足球数据清洗器方法"""
    from src.data.processing.football_data_cleaner_mod import FootballDataCleaner

    with patch("src.database.connection.DatabaseManager"):
        cleaner = FootballDataCleaner()

        # Mock子处理器
        cleaner.data_validator.validate_match_data = Mock(return_value=True)
        cleaner.id_mapper.map_league_id = AsyncMock(return_value=1)
        cleaner.id_mapper.map_team_id = AsyncMock(return_value=2)
        cleaner.time_processor.to_utc_time = Mock(
            return_value="2024-01-01T12:00:00+00:00"
        )
        cleaner.data_validator.standardize_match_status = Mock(return_value="scheduled")
        cleaner.data_validator.validate_score = Mock(side_effect=[1, 0, 0, 0])
        cleaner.time_processor.extract_season = Mock(return_value="2023-2024")
        cleaner.data_validator.clean_venue_name = Mock(return_value="Stadium")
        cleaner.data_validator.clean_referee_name = Mock(return_value="Referee")

        # 测试清洗比赛数据
        raw_data = {
            "id": "123",
            "competition": {"id": "456"},
            "homeTeam": {"id": "1", "name": "Team A"},
            "awayTeam": {"id": "2", "name": "Team B"},
            "utcDate": "2024-01-01T12:00:00Z",
            "status": "SCHEDULED",
            "score": {
                "fullTime": {"home": 1, "away": 0},
                "halfTime": {"home": 0, "away": 0},
            },
            "season": {"id": 2023},
            "matchday": 1,
            "venue": "Stadium",
            "referees": [{"role": "REFEREE", "name": "Referee"}],
        }

        cleaned = await cleaner.clean_match_data(raw_data)
        assert cleaned is not None
        assert cleaned["external_match_id"] == "123"
        assert cleaned["home_team_id"] == 2
        assert cleaned["away_team_id"] == 2
        assert cleaned["league_id"] == 1
        assert cleaned["match_status"] == "scheduled"
        assert cleaned["home_score"] == 1
        assert cleaned["away_score"] == 0
        assert cleaned["season"] == "2023-2024"

        # 测试清洗赔率数据
        cleaner.odds_processor.clean_odds_data = AsyncMock(
            return_value=[{"test": "odds"}]
        )
        raw_odds = [
            {
                "match_id": "123",
                "bookmaker": "Test",
                "market_type": "h2h",
                "outcomes": [],
            }
        ]

        cleaned_odds = await cleaner.clean_odds_data(raw_odds)
        assert len(cleaned_odds) == 1
        assert cleaned_odds[0]["test"] == "odds"


def test_backward_compatibility():
    """测试向后兼容性"""
    # 测试原始导入方式仍然有效
    from src.data.processing.football_data_cleaner_mod import FootballDataCleaner

    # 验证类可以实例化
    with patch("src.database.connection.DatabaseManager"):
        cleaner = FootballDataCleaner()
        assert hasattr(cleaner, "clean_match_data")
        assert hasattr(cleaner, "clean_odds_data")
        assert hasattr(cleaner, "_validate_match_data")
        assert hasattr(cleaner, "_validate_score")
        assert hasattr(cleaner, "_to_utc_time")


@pytest.mark.asyncio
async def test_error_handling():
    """测试错误处理"""
    from src.data.processing.football_data_cleaner_mod import FootballDataCleaner

    with patch("src.database.connection.DatabaseManager"):
        cleaner = FootballDataCleaner()

        # 测试无效比赛数据
        invalid_data = {"id": "123"}  # 缺少必需字段
        result = await cleaner.clean_match_data(invalid_data)
        assert result is None

        # 测试验证失败的情况
        cleaner.data_validator.validate_match_data = Mock(return_value=False)
        result = await cleaner.clean_match_data({"id": "123"})
        assert result is None

        # 测试异常处理
        cleaner.data_validator.validate_match_data = Mock(
            side_effect=Exception("Test error")
        )
        result = await cleaner.clean_match_data({"id": "123"})
        assert result is None
