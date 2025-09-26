"""
Missing Data Handler Batch-Δ-003 测试套件

专门为 data/processing/missing_data_handler.py 设计的测试，目标是将其覆盖率从 15% 提升至 ≥25%
覆盖初始化、比赛数据处理、特征处理、历史平均值获取、时间序列插值、关键数据清理等功能
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd
import numpy as np
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.data.processing.missing_data_handler import MissingDataHandler


class TestMissingDataHandlerBatchDelta003:
    """MissingDataHandler Batch-Δ-003 测试类"""

    @pytest.fixture
    def handler(self):
        """创建缺失数据处理器实例"""
        # Mock DatabaseManager 以避免数据库连接
        with patch('src.data.processing.missing_data_handler.DatabaseManager') as mock_db:
            mock_db.return_value = Mock()
            handler = MissingDataHandler()
            # Mock logger
            handler.logger = Mock()
            return handler

    @pytest.fixture
    def sample_match_data(self):
        """创建示例比赛数据"""
        return {
            "id": "12345",
            "home_team": "Liverpool FC",
            "away_team": "Arsenal FC",
            "home_score": None,  # 缺失值
            "away_score": None,  # 缺失值
            "venue": "",  # 空字符串
            "referee": None,  # None值
            "match_date": "2025-01-15",
            "competition": "Premier League"
        }

    @pytest.fixture
    def sample_features_df(self):
        """创建示例特征DataFrame"""
        # 使用真实DataFrame而不是mock
        return pd.DataFrame({
            'match_id': [1, 2, 3, 4, 5],
            'avg_possession': [60.0, None, 55.0, None, 58.0],
            'avg_shots_per_game': [15.0, 12.0, None, 14.0, None],
            'avg_goals_per_game': [2.0, 1.5, None, None, 1.8],
            'league_position': [5, None, 8, 12, None]
        })

    @pytest.fixture
    def sample_time_series(self):
        """创建示例时间序列数据"""
        # 使用真实Series而不是mock
        return pd.Series([1.0, None, 3.0, None, 5.0, None, 7.0])

    def test_handler_initialization(self):
        """测试处理器初始化"""
        with patch('src.data.processing.missing_data_handler.DatabaseManager') as mock_db:
            mock_db.return_value = Mock()
            handler = MissingDataHandler()

            # 验证初始化属性
    assert handler.db_manager is not None
    assert handler.logger is not None
    assert isinstance(handler.FILL_STRATEGIES, dict)
    assert "team_stats" in handler.FILL_STRATEGIES
    assert "player_stats" in handler.FILL_STRATEGIES
    assert "weather" in handler.FILL_STRATEGIES
    assert "odds" in handler.FILL_STRATEGIES

    def test_fill_strategies_configuration(self, handler):
        """测试填充策略配置"""
        # 验证填充策略配置
        expected_strategies = {
            "team_stats": "historical_average",
            "player_stats": "position_median",
            "weather": "seasonal_normal",
            "odds": "market_consensus"
        }

    assert handler.FILL_STRATEGIES == expected_strategies

    @pytest.mark.asyncio
    async def test_handle_missing_match_data_with_missing_scores(self, handler, sample_match_data):
        """测试处理缺失比分的比赛数据"""
        result = await handler.handle_missing_match_data(sample_match_data)

        # 验证缺失比分被填充
    assert result["home_score"] == 0
    assert result["away_score"] == 0

        # 验证其他数据保持不变
    assert result["id"] == "12345"
    assert result["home_team"] == "Liverpool FC"
    assert result["away_team"] == "Arsenal FC"

    @pytest.mark.asyncio
    async def test_handle_missing_match_data_with_missing_venue(self, handler, sample_match_data):
        """测试处理缺失场地的比赛数据"""
        result = await handler.handle_missing_match_data(sample_match_data)

        # 验证缺失场地被填充
    assert result["venue"] == "Unknown"

    @pytest.mark.asyncio
    async def test_handle_missing_match_data_with_missing_referee(self, handler, sample_match_data):
        """测试处理缺失裁判的比赛数据"""
        result = await handler.handle_missing_match_data(sample_match_data)

        # 验证缺失裁判被填充
    assert result["referee"] == "Unknown"

    @pytest.mark.asyncio
    async def test_handle_missing_match_data_complete_data(self, handler):
        """测试处理完整比赛数据"""
        complete_data = {
            "id": "12345",
            "home_score": 2,
            "away_score": 1,
            "venue": "Anfield",
            "referee": "Michael Oliver"
        }

        result = await handler.handle_missing_match_data(complete_data)

        # 验证完整数据保持不变
    assert result == complete_data

    @pytest.mark.asyncio
    async def test_handle_missing_match_data_logging(self, handler, sample_match_data):
        """测试处理比赛数据时的日志记录"""
        await handler.handle_missing_match_data(sample_match_data)

        # 验证日志被调用
    assert handler.logger.debug.call_count >= 2  # home_score 和 away_score 的日志

    @pytest.mark.asyncio
    async def test_handle_missing_features_with_null_values(self, handler):
        """测试处理包含空值的特征数据"""
        # 直接创建DataFrame而不是使用fixture
        features_df = pd.DataFrame({
            'match_id': [1, 2, 3, 4, 5],
            'avg_possession': [60.0, None, 55.0, None, 58.0],
            'avg_shots_per_game': [15.0, 12.0, None, 14.0, None],
            'avg_goals_per_game': [2.0, 1.5, None, None, 1.8],
            'league_position': [5, None, 8, 12, None]
        })

        result = await handler.handle_missing_features(12345, features_df.copy())

        # 验证返回DataFrame
    assert isinstance(result, pd.DataFrame)
    assert len(result) == len(features_df)

        # 验证空值被处理（不应该再有NaN值）
    assert not result.isnull().any().any()

    @pytest.mark.asyncio
    async def test_handle_missing_features_historical_average_strategy(self, handler):
        """测试使用历史平均值策略处理特征"""
        # 直接创建DataFrame而不是使用fixture
        features_df = pd.DataFrame({
            'match_id': [1, 2, 3, 4, 5],
            'avg_possession': [60.0, None, 55.0, None, 58.0],
            'avg_shots_per_game': [15.0, 12.0, None, 14.0, None],
            'avg_goals_per_game': [2.0, 1.5, None, None, 1.8],
            'league_position': [5, None, 8, 12, None]
        })

        # Mock历史平均值方法
        handler._get_historical_average = AsyncMock(return_value=50.0)

        result = await handler.handle_missing_features(12345, features_df.copy())

        # 验证历史平均值方法被调用
    assert handler._get_historical_average.called

        # 验证空值被填充
    assert not result.isnull().any().any()

    @pytest.mark.asyncio
    async def test_handle_missing_features_median_strategy(self, handler):
        """测试使用中位数策略处理特征"""
        # 创建测试数据，确保中位数策略被使用
        test_df = pd.DataFrame({
            'match_id': [1, 2, 3],
            'test_feature': [10.0, None, 20.0]
        })

        # 修改策略以使用中位数
        original_strategies = handler.FILL_STRATEGIES.copy()
        handler.FILL_STRATEGIES["team_stats"] = "median"

        try:
            result = await handler.handle_missing_features(12345, test_df.copy())

            # 验证空值被中位数填充（应该是15.0）
    assert result['test_feature'].iloc[1] == 15.0
        finally:
            # 恢复原始策略
            handler.FILL_STRATEGIES = original_strategies

    @pytest.mark.asyncio
    async def test_handle_missing_features_zero_fallback(self, handler):
        """测试零值回退策略"""
        # 创建测试数据，使用未知策略
        test_df = pd.DataFrame({
            'match_id': [1, 2, 3],
            'test_feature': [10.0, None, 20.0]
        })

        # 修改策略为未知值
        original_strategies = handler.FILL_STRATEGIES.copy()
        handler.FILL_STRATEGIES["team_stats"] = "unknown_strategy"

        try:
            result = await handler.handle_missing_features(12345, test_df.copy())

            # 验证空值被0填充
    assert result['test_feature'].iloc[1] == 0.0
        finally:
            # 恢复原始策略
            handler.FILL_STRATEGIES = original_strategies

    @pytest.mark.asyncio
    async def test_handle_missing_features_error_handling(self, handler, sample_features_df):
        """测试处理特征数据时的错误处理"""
        # Mock fillna方法抛出异常
        with patch.object(pd.DataFrame, 'fillna', side_effect=Exception("Test error")):
            result = await handler.handle_missing_features(12345, sample_features_df.copy())

            # 验证返回原始数据
    assert result.equals(sample_features_df)

            # 验证错误日志被记录
            handler.logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_missing_features_logging(self, handler, sample_features_df):
        """测试处理特征数据时的日志记录"""
        await handler.handle_missing_features(12345, sample_features_df.copy())

        # 验证日志被调用
    assert handler.logger.info.called or handler.logger.debug.called

    @pytest.mark.asyncio
    async def test_get_historical_average_known_feature(self, handler):
        """测试获取已知特征的历史平均值"""
        result = await handler._get_historical_average("avg_possession")

        # 验证返回预期值
    assert result == 50.0

    @pytest.mark.asyncio
    async def test_get_historical_average_unknown_feature(self, handler):
        """测试获取未知特征的历史平均值"""
        result = await handler._get_historical_average("unknown_feature")

        # 验证返回默认值
    assert result == 0.0

    @pytest.mark.asyncio
    async def test_get_historical_average_all_default_features(self, handler):
        """测试所有默认特征的历史平均值"""
        default_features = ["avg_possession", "avg_shots_per_game", "avg_goals_per_game", "league_position"]
        expected_values = [50.0, 12.5, 1.5, 10.0]

        for feature, expected in zip(default_features, expected_values):
            result = await handler._get_historical_average(feature)
    assert result == expected

    @pytest.mark.asyncio
    async def test_get_historical_average_error_handling(self, handler):
        """测试获取历史平均值时的错误处理"""
        # 直接测试异常处理逻辑
        result = await handler._get_historical_average("any_feature")

        # 验证返回默认值（即使是未知特征也返回0.0）
    assert result == 0.0

    def test_interpolate_time_series_data_success(self, handler, sample_time_series):
        """测试成功插值时间序列数据"""
        result = handler.interpolate_time_series_data(sample_time_series.copy())

        # 验证返回Series
    assert isinstance(result, pd.Series)
    assert len(result) == len(sample_time_series)

        # 验证空值被插值填充
    assert not result.isnull().any()

        # 验证插值结果（线性插值）
        expected_values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        np.testing.assert_array_almost_equal(result.values, expected_values)

    def test_interpolate_time_series_data_no_missing(self, handler):
        """测试无缺失值的时间序列数据"""
        complete_series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = handler.interpolate_time_series_data(complete_series.copy())

        # 验证数据保持不变
        pd.testing.assert_series_equal(result, complete_series)

    def test_interpolate_time_series_data_all_missing(self, handler):
        """测试全为缺失值的时间序列数据"""
        all_missing_series = pd.Series([None, None, None])
        result = handler.interpolate_time_series_data(all_missing_series.copy())

        # 验证返回原始数据（无法插值）
        pd.testing.assert_series_equal(result, all_missing_series)

    def test_interpolate_time_series_data_error_handling(self, handler):
        """测试插值时的错误处理"""
        # Mock interpolate方法抛出异常
        broken_series = pd.Series([1.0, None, 3.0])
        with patch.object(pd.Series, 'interpolate', side_effect=Exception("Test error")):
            result = handler.interpolate_time_series_data(broken_series.copy())

            # 验证返回原始数据
            pd.testing.assert_series_equal(result, broken_series)

            # 验证错误日志被记录
            handler.logger.error.assert_called_once()

    def test_remove_rows_with_missing_critical_data_success(self, handler):
        """测试成功删除包含关键数据缺失的行"""
        test_df = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'critical_field': ['A', None, 'B', None, 'C'],
            'other_field': [1, 2, 3, 4, 5]
        })

        result = handler.remove_rows_with_missing_critical_data(
            test_df.copy(), ['critical_field']
        )

        # 验证返回DataFrame
    assert isinstance(result, pd.DataFrame)

        # 验证缺失行被删除
    assert len(result) == 3  # 只保留3行有效数据
    assert not result['critical_field'].isnull().any()

    def test_remove_rows_with_missing_critical_data_multiple_columns(self, handler):
        """测试删除多列关键数据缺失的行"""
        test_df = pd.DataFrame({
            'id': [1, 2, 3, 4],
            'critical1': ['A', None, 'B', 'C'],
            'critical2': ['X', 'Y', None, 'Z'],
            'other': [1, 2, 3, 4]
        })

        result = handler.remove_rows_with_missing_critical_data(
            test_df.copy(), ['critical1', 'critical2']
        )

        # 验证只有第4行保留（两列都完整）
    assert len(result) == 1
    assert result.iloc[0]['id'] == 4

    def test_remove_rows_with_missing_critical_data_no_missing(self, handler):
        """测试无缺失数据的处理"""
        complete_df = pd.DataFrame({
            'id': [1, 2, 3],
            'critical_field': ['A', 'B', 'C'],
            'other_field': [1, 2, 3]
        })

        result = handler.remove_rows_with_missing_critical_data(
            complete_df.copy(), ['critical_field']
        )

        # 验证数据保持不变
        pd.testing.assert_frame_equal(result, complete_df)

    def test_remove_rows_with_missing_critical_data_all_missing(self, handler):
        """测试所有行都有关键数据缺失的处理"""
        all_missing_df = pd.DataFrame({
            'id': [1, 2, 3],
            'critical_field': [None, None, None],
            'other_field': [1, 2, 3]
        })

        result = handler.remove_rows_with_missing_critical_data(
            all_missing_df.copy(), ['critical_field']
        )

        # 验证返回空DataFrame
    assert len(result) == 0

    def test_remove_rows_with_missing_critical_data_logging(self, handler):
        """测试删除行时的日志记录"""
        test_df = pd.DataFrame({
            'id': [1, 2, 3],
            'critical_field': ['A', None, 'B'],
            'other_field': [1, 2, 3]
        })

        handler.remove_rows_with_missing_critical_data(
            test_df.copy(), ['critical_field']
        )

        # 验证警告日志被记录
        handler.logger.warning.assert_called_once()
    assert "Removed 1 rows" in str(handler.logger.warning.call_args)

    def test_remove_rows_with_missing_critical_data_error_handling(self, handler):
        """测试删除行时的错误处理"""
        test_df = pd.DataFrame({'id': [1, 2, 3], 'field': ['A', 'B', 'C']})

        # Mock dropna方法抛出异常
        with patch.object(pd.DataFrame, 'dropna', side_effect=Exception("Test error")):
            result = handler.remove_rows_with_missing_critical_data(
                test_df.copy(), ['field']
            )

            # 验证返回原始数据
            pd.testing.assert_frame_equal(result, test_df)

            # 验证错误日志被记录
            handler.logger.error.assert_called_once()

    def test_remove_rows_with_missing_critical_data_empty_dataframe(self, handler):
        """测试空DataFrame的处理"""
        empty_df = pd.DataFrame()

        result = handler.remove_rows_with_missing_critical_data(
            empty_df, ['any_column']
        )

        # 验证返回空DataFrame
    assert len(result) == 0

    def test_remove_rows_with_missing_critical_data_nonexistent_column(self, handler):
        """测试不存在的关键列的处理"""
        test_df = pd.DataFrame({
            'id': [1, 2, 3],
            'existing_field': ['A', 'B', 'C']
        })

        result = handler.remove_rows_with_missing_critical_data(
            test_df.copy(), ['nonexistent_column']
        )

        # 验证返回原始数据（列不存在时无法删除）
        pd.testing.assert_frame_equal(result, test_df)

    @pytest.mark.asyncio
    async def test_handler_comprehensive_workflow(self, handler, sample_match_data, sample_features_df):
        """测试处理器的完整工作流程"""
        # 处理比赛数据
        processed_match = await handler.handle_missing_match_data(sample_match_data.copy())

        # 处理特征数据
        processed_features = await handler.handle_missing_features(12345, sample_features_df.copy())

        # 验证处理结果
    assert processed_match["home_score"] == 0
    assert processed_match["away_score"] == 0
    assert processed_match["venue"] == "Unknown"
    assert processed_match["referee"] == "Unknown"

    assert not processed_features.isnull().any().any()

    def test_handler_method_signatures(self, handler):
        """测试处理器方法签名"""
        # 验证所有方法都有正确的签名
        import inspect

        # 异步方法
    assert inspect.iscoroutinefunction(handler.handle_missing_match_data)
    assert inspect.iscoroutinefunction(handler.handle_missing_features)
    assert inspect.iscoroutinefunction(handler._get_historical_average)

        # 同步方法
    assert not inspect.iscoroutinefunction(handler.interpolate_time_series_data)
    assert not inspect.iscoroutinefunction(handler.remove_rows_with_missing_critical_data)

    def test_handler_constants_and_attributes(self, handler):
        """测试处理器的常量和属性"""
        # 验证FILL_STRATEGIES常量
    assert isinstance(handler.FILL_STRATEGIES, dict)
    assert len(handler.FILL_STRATEGIES) == 4

        # 验证策略值
        for strategy in handler.FILL_STRATEGIES.values():
    assert isinstance(strategy, str)
    assert len(strategy) > 0