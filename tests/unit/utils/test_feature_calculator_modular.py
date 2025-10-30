# TODO: Consider creating a fixture for 8 repeated Mock creations

# TODO: Consider creating a fixture for 8 repeated Mock creations

from unittest.mock import Mock, patch

"""""""
特征计算器模块化测试
"""""""


import pytest


def test_module_import():
    """测试模块导入"""
    # 测试导入新模块
    # 测试导入兼容模块
    from src.features.feature_calculator import (
        FeatureCalculator as LegacyFeatureCalculator,
    )
    from src.features.feature_calculator_mod import (
        BatchCalculator,
        FeatureCalculator,
        HistoricalMatchupCalculator,
        OddsFeaturesCalculator,
        RecentPerformanceCalculator,
        StatisticsUtils,
    )

    assert FeatureCalculator is not None
    assert RecentPerformanceCalculator is not None
    assert HistoricalMatchupCalculator is not None
    assert OddsFeaturesCalculator is not None
    assert BatchCalculator is not None
    assert StatisticsUtils is not None
    assert LegacyFeatureCalculator is not None


def test_statistics_utils():
    """测试统计工具类"""
    from src.features.feature_calculator_mod.statistics_utils import StatisticsUtils

    # 测试基础统计函数
    _data = [1, 2, 3, 4, 5]

    assert StatisticsUtils.calculate_mean(data) == 3.0
    assert StatisticsUtils.calculate_min(data) == 1.0
    assert StatisticsUtils.calculate_max(data) == 5.0
    assert StatisticsUtils.calculate_median(data) == 3.0

    # 测试空数据
    assert StatisticsUtils.calculate_mean([]) is None
    assert StatisticsUtils.calculate_mean(None) is None


def test_feature_calculator_initialization():
    """测试特征计算器初始化"""
    from src.features.feature_calculator_mod import FeatureCalculator

    calculator = FeatureCalculator()
    assert calculator.db_manager is not None
    assert calculator._config == {}
    assert calculator.features == []
    assert calculator.recent_calculator is not None
    assert calculator.historical_calculator is not None
    assert calculator.odds_calculator is not None
    assert calculator.batch_calculator is not None


def test_recent_performance_calculator():
    """测试近期战绩计算器"""
    from src.features.feature_calculator_mod import RecentPerformanceCalculator

    # Mock database manager
    db_manager = Mock()
    calculator = RecentPerformanceCalculator(db_manager)

    assert calculator.db_manager is not None

    # 测试静态方法
    _matches = [
        {"result": "win"},
        {"result": "draw"},
        {"result": "loss"},
        {"result": "win"},
    ]
    form = calculator.calculate_form(matches)
    assert form == 0.5833  # (3+1+0+3)/(4*3) = 7/12 ≈ 0.5833


def test_historical_matchup_calculator():
    """测试历史对战计算器"""
    from src.features.feature_calculator_mod import HistoricalMatchupCalculator

    db_manager = Mock()
    calculator = HistoricalMatchupCalculator(db_manager)

    assert calculator.db_manager is not None

    # 测试趋势分析
    _matches = [
        Mock(home_score=2, away_score=1),
        Mock(home_score=1, away_score=1),
        Mock(home_score=1, away_score=2),
        Mock(home_score=2, away_score=0),
    ]

    trend = calculator.calculate_head_to_head_trend(matches)
    assert "trend" in trend
    assert "dominance" in trend


def test_odds_features_calculator():
    """测试赔率特征计算器"""
    from src.features.feature_calculator_mod import OddsFeaturesCalculator

    db_manager = Mock()
    calculator = OddsFeaturesCalculator(db_manager)

    assert calculator.db_manager is not None

    # 测试市场趋势判断
    assert calculator._determine_market_trend({}) == "unknown"
    assert (
        calculator._determine_market_trend({"avg_home_odds_change": 0.02}) == "stable"
    )
    assert (
        calculator._determine_market_trend({"avg_home_odds_change": 0.15})
        == "home_drifting"
    )
    assert (
        calculator._determine_market_trend({"avg_home_odds_change": -0.15})
        == "home_steam"
    )


def test_batch_calculator():
    """测试批量计算器"""
    from src.features.feature_calculator_mod import BatchCalculator

    db_manager = Mock()
    calculator = BatchCalculator(db_manager)

    assert calculator.db_manager is not None

    # 测试批次优化
    batches = calculator.optimize_batch_size(150, 100)
    assert len(batches) == 2
    assert len(batches[0]) == 100
    assert len(batches[1]) == 50


def test_rolling_statistics():
    """测试滚动统计"""
    from src.features.feature_calculator_mod.statistics_utils import StatisticsUtils

    _data = [1, 2, 3, 4, 5]

    # 测试滚动平均
    rolling_mean = StatisticsUtils.calculate_rolling_mean(data, window=3)
    assert len(rolling_mean) == len(data)


def test_distribution_stats():
    """测试分布统计"""
    from src.features.feature_calculator_mod.statistics_utils import StatisticsUtils

    _data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    _stats = StatisticsUtils.calculate_distribution_stats(data)

    assert "count" in stats
    assert "mean" in stats
    assert "std" in stats
    assert "min" in stats
    assert "max" in stats
    assert stats["count"] == 10
    assert stats["mean"] == 5.5


def test_outlier_detection():
    """测试异常值检测"""
    from src.features.feature_calculator_mod.statistics_utils import StatisticsUtils

    _data = [1, 2, 3, 4, 5, 100]  # 100是异常值

    # IQR方法
    outliers_iqr = StatisticsUtils.detect_outliers(data, method="iqr")
    assert outliers_iqr["count"] > 0
    assert 100 in outliers_iqr["outliers"]

    # Z-score方法
    outliers_zscore = StatisticsUtils.detect_outliers(
        data, method="zscore", multiplier=2
    )
    assert "count" in outliers_zscore
    assert "method" in outliers_zscore


def test_backward_compatibility():
    """测试向后兼容性"""
    # 测试原始导入方式仍然有效
        FeatureCalculator,
        calculate_max,
        calculate_mean,
        calculate_min,
        calculate_std,
    )

    # 测试统计函数
    _data = [1, 2, 3, 4, 5]
    assert calculate_mean(data) == 3.0
    assert calculate_min(data) == 1.0
    assert calculate_max(data) == 5.0

    # 测试特征计算器
    calculator = FeatureCalculator()
    assert hasattr(calculator, "calculate_recent_performance_features")
    assert hasattr(calculator, "calculate_historical_matchup_features")
    assert hasattr(calculator, "calculate_odds_features")


@pytest.mark.asyncio
async def test_feature_calculator_async_methods():
    """测试特征计算器的异步方法"""
    from src.features.feature_calculator_mod import FeatureCalculator

    # Mock数据库会话 - 使用局部patch
    with patch("src.database.connection.DatabaseManager"):
        calculator = FeatureCalculator()

        # 测试方法存在（不执行实际查询）
        assert hasattr(calculator, "calculate_recent_performance_features")
        assert hasattr(calculator, "calculate_historical_matchup_features")
        assert hasattr(calculator, "calculate_odds_features")
        assert hasattr(calculator, "calculate_all_match_features")
        assert hasattr(calculator, "calculate_all_team_features")
        assert hasattr(calculator, "batch_calculate_team_features")
