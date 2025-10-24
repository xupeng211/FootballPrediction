# TODO: Consider creating a fixture for 16 repeated Mock creations

# TODO: Consider creating a fixture for 16 repeated Mock creations

from unittest.mock import Mock, patch, AsyncMock
"""
数据质量异常处理器模块化测试
"""

import pytest
from datetime import datetime


def test_module_import():
    """测试模块导入"""
    # 测试导入新模块
    from src.data.quality.exception_handler_mod import (
        DataQualityExceptionHandler,
        MissingValueHandler,
        SuspiciousOddsHandler,
        InvalidDataHandler,
        QualityLogger,
        StatisticsProvider,
    )

    # 测试导入异常类
    from src.data.quality.exception_handler_mod import (
        DataQualityException,
        MissingValueException,
        SuspiciousOddsException,
    )

    # 测试导入兼容模块
    from src.data.quality.exception_handler_mod import (
        DataQualityExceptionHandler as LegacyDataQualityExceptionHandler,
    )

    assert DataQualityExceptionHandler is not None
    assert MissingValueHandler is not None
    assert SuspiciousOddsHandler is not None
    assert InvalidDataHandler is not None
    assert QualityLogger is not None
    assert StatisticsProvider is not None
    assert LegacyDataQualityExceptionHandler is not None


def test_exception_classes():
    """测试异常类"""
    from src.data.quality.exception_handler_mod import (
        DataQualityException,
        MissingValueException,
        SuspiciousOddsException,
        InvalidDataException,
    )

    # 测试基础异常
    base_exc = DataQualityException("Base error")
    assert str(base_exc) == "Base error"

    # 测试缺失值异常
    missing_exc = MissingValueException("Missing value", "matches", "score")
    assert missing_exc.table_name == "matches"
    assert missing_exc.column_name == "score"

    # 测试可疑赔率异常
    odds_exc = SuspiciousOddsException("Suspicious odds", {"match_id": 123})
    assert odds_exc.odds_data == {"match_id": 123}

    # 测试无效数据异常
    invalid_exc = InvalidDataException("Invalid data", "matches", 456)
    assert invalid_exc.table_name == "matches"
    assert invalid_exc.record_id == 456


def test_missing_value_handler():
    """测试缺失值处理器"""
    from src.data.quality.exception_handler_mod import MissingValueHandler

    # Mock database manager
    db_manager = Mock()
    handler = MissingValueHandler(db_manager)

    assert handler.db_manager is not None
    assert handler.config is not None
    assert handler._config["strategy"] == "historical_average"

    # 测试配置更新
    new_config = {"lookback_days": 60}
    handler.update_config(new_config)
    assert handler._config["lookback_days"] == 60


def test_suspicious_odds_handler():
    """测试可疑赔率处理器"""
    from src.data.quality.exception_handler_mod import SuspiciousOddsHandler

    db_manager = Mock()
    handler = SuspiciousOddsHandler(db_manager)

    assert handler.db_manager is not None
    assert handler.config is not None

    # 测试赔率可疑性检测
    # 正常赔率
    normal_odds = {
        "home_odds": 2.5,
        "draw_odds": 3.2,
        "away_odds": 2.8,
    }
    is_suspicious, reason = handler._is_odds_suspicious(normal_odds)
    assert not is_suspicious

    # 异常赔率（过低）
    low_odds = {
        "home_odds": 0.5,
        "draw_odds": 3.2,
        "away_odds": 2.8,
    }
    is_suspicious, reason = handler._is_odds_suspicious(low_odds)
    assert is_suspicious
    assert "too_low" in reason

    # 测试配置摘要
    summary = handler.get_config_summary()
    assert "min_odds" in summary
    assert "max_odds" in summary


def test_invalid_data_handler():
    """测试无效数据处理器"""
    from src.data.quality.exception_handler_mod import InvalidDataHandler

    db_manager = Mock()
    handler = InvalidDataHandler(db_manager)

    assert handler.db_manager is not None
    assert handler.config is not None
    assert handler._config["batch_size"] == 100


@pytest.mark.asyncio
async def test_quality_logger():
    """测试质量日志记录器"""
    from src.data.quality.exception_handler_mod import QualityLogger
    # from src.database.connection_mod import DatabaseManager

    # Mock database manager
    db_manager = Mock(spec=DatabaseManager)
    logger = QualityLogger(db_manager)

    assert logger.db_manager is not None

    # Mock session
    mock_session = AsyncMock()
    db_manager.get_async_session.return_value.__aenter__.return_value = mock_session

    # 测试创建质量日志
    await logger.create_quality_log(
        table_name="test_table",
        record_id=123,
        error_type="test_error",
        error_data={"message": "test"},
        requires_manual_review=False,
        session=mock_session,
    )

    # 验证session.add被调用
    mock_session.add.assert_called_once()


def test_statistics_provider():
    """测试统计信息提供器"""
    from src.data.quality.exception_handler_mod import StatisticsProvider

    db_manager = Mock()
    provider = StatisticsProvider(db_manager)

    assert provider.db_manager is not None

    # 测试质量评分等级
    assert provider._get_quality_grade(0.95) == "A+"
    assert provider._get_quality_grade(0.85) == "B+"
    assert provider._get_quality_grade(0.50) == "D"
    assert provider._get_quality_grade(0.30) == "F"


def test_exception_handler_initialization():
    """测试异常处理器初始化"""
    from src.data.quality.exception_handler_mod import DataQualityExceptionHandler

    with patch("src.database.connection.DatabaseManager"):
        handler = DataQualityExceptionHandler()

        assert handler.db_manager is not None
        assert handler.missing_value_handler is not None
        assert handler.suspicious_odds_handler is not None
        assert handler.invalid_data_handler is not None
        assert handler.quality_logger is not None
        assert handler.statistics_provider is not None

        # 验证配置
        _config = handler.get_config_summary()
        assert "missing_values" in config
        assert "suspicious_odds" in config
        assert "invalid_data" in config


def test_backward_compatibility():
    """测试向后兼容性"""
    # 测试原始导入方式仍然有效
    from src.data.quality.exception_handler_mod import (
        DataQualityExceptionHandler,
        MissingValueHandler,
        SuspiciousOddsHandler,
        DataQualityException,
    )

    # 验证类可以实例化
    with patch("src.database.connection.DatabaseManager"):
        handler = DataQualityExceptionHandler()
        assert hasattr(handler, "handle_missing_values")
        assert hasattr(handler, "handle_suspicious_odds")
        assert hasattr(handler, "handle_invalid_data")
        assert hasattr(handler, "get_handling_statistics")


@pytest.mark.asyncio
async def test_exception_handler_methods():
    """测试异常处理器的方法"""
    from src.data.quality.exception_handler_mod import DataQualityExceptionHandler

    with patch("src.database.connection.DatabaseManager"):
        handler = DataQualityExceptionHandler()

        # Mock 子处理器
        handler.missing_value_handler.handle_missing_values = AsyncMock(
            return_value=[{"id": 1}]
        )
        handler.suspicious_odds_handler.handle_suspicious_odds = AsyncMock(
            return_value={"total_processed": 1}
        )
        handler.invalid_data_handler.handle_invalid_data = AsyncMock(
            return_value={"logged_count": 1}
        )
        handler.statistics_provider.get_handling_statistics = AsyncMock(
            return_value={"total_issues": 0}
        )

        # 测试方法调用
        _result = await handler.handle_missing_values("matches", [{}])
        assert _result == [{"id": 1}]

        _result = await handler.handle_suspicious_odds([{}])
        assert _result["total_processed"] == 1

        _result = await handler.handle_invalid_data("matches", [{}], "invalid")
        assert _result["logged_count"] == 1

        _result = await handler.get_handling_statistics()
        assert _result["total_issues"] == 0


def test_urgency_score_calculation():
    """测试紧急程度评分计算"""
    from src.data.quality.exception_handler_mod import StatisticsProvider

    db_manager = Mock()
    provider = StatisticsProvider(db_manager)

    # Mock 数据库行对象
    class MockRow:
        def __init__(self, count, manual_review_count):
            self.count = count
            self.manual_review_count = manual_review_count

    # 测试评分计算
    row = MockRow(50, 10)
    score = provider._calculate_urgency_score(row)
    assert 0.5 <= score <= 1.0  # 基础分数应该是0.5

    # 测试高频率需要审核的问题
    row = MockRow(100, 100)
    score = provider._calculate_urgency_score(row)
    assert score >= 0.8  # 应该有较高的分数


@pytest.mark.asyncio
async def test_quality_dashboard():
    """测试质量仪表板"""
    from src.data.quality.exception_handler_mod import DataQualityExceptionHandler

    with patch("src.database.connection.DatabaseManager"):
        handler = DataQualityExceptionHandler()

        # Mock 统计提供器
        mock_stats = {"total_issues": 10}
        mock_trend = []
        mock_issues = []
        mock_score = {"quality_score": 0.9}
        mock_reviews = []

        handler.statistics_provider.get_handling_statistics = AsyncMock(
            return_value=mock_stats
        )
        handler.statistics_provider.get_daily_trend = AsyncMock(return_value=mock_trend)
        handler.statistics_provider.get_top_issues = AsyncMock(return_value=mock_issues)
        handler.statistics_provider.get_quality_score = AsyncMock(
            return_value=mock_score
        )
        handler.quality_logger.get_pending_reviews = AsyncMock(
            return_value=mock_reviews
        )

        # 获取仪表板数据
        dashboard = await handler.get_quality_dashboard("matches")

        assert dashboard["table_name"] == "matches"
        assert dashboard["last_24h_stats"] == mock_stats
        assert dashboard["quality_score"] == mock_score
        assert "timestamp" in dashboard
