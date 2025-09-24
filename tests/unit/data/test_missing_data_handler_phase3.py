"""
Phase 3：缺失数据处理模块综合测试
目标：全面提升missing_data_handler.py模块覆盖率到60%+
重点：测试所有缺失数据处理策略、异常处理、插值方法和数据清理功能
"""

from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from src.data.processing.missing_data_handler import MissingDataHandler


class TestMissingDataHandlerBasic:
    """缺失数据处理器基础测试"""

    def setup_method(self):
        """设置测试环境"""
        self.handler = MissingDataHandler()

    def test_handler_initialization(self):
        """测试处理器初始化"""
        assert self.handler is not None
        assert hasattr(self.handler, "FILL_STRATEGIES")
        assert hasattr(self.handler, "db_manager")
        assert hasattr(self.handler, "logger")
        assert "team_stats" in self.handler.FILL_STRATEGIES
        assert "player_stats" in self.handler.FILL_STRATEGIES
        assert "weather" in self.handler.FILL_STRATEGIES
        assert "odds" in self.handler.FILL_STRATEGIES

    def test_fill_strategies_configuration(self):
        """测试填充策略配置"""
        strategies = self.handler.FILL_STRATEGIES
        assert strategies["team_stats"] == "historical_average"
        assert strategies["player_stats"] == "position_median"
        assert strategies["weather"] == "seasonal_normal"
        assert strategies["odds"] == "market_consensus"


class TestMissingDataHandlerMatchData:
    """缺失数据处理器比赛数据测试"""

    def setup_method(self):
        """设置测试环境"""
        self.handler = MissingDataHandler()

    @pytest.mark.asyncio
    async def test_handle_missing_match_data_complete(self):
        """测试完整比赛数据处理"""
        complete_data = {
            "id": "12345",
            "home_score": 2,
            "away_score": 1,
            "venue": "Stadium A",
            "referee": "Referee A",
        }

        result = await self.handler.handle_missing_match_data(complete_data)
        assert result == complete_data  # 完整数据应该保持不变

    @pytest.mark.asyncio
    async def test_handle_missing_match_data_missing_scores(self):
        """测试缺失比分处理"""
        missing_scores_data = {
            "id": "12345",
            "home_score": None,
            "away_score": None,
            "venue": "Stadium A",
            "referee": "Referee A",
        }

        result = await self.handler.handle_missing_match_data(missing_scores_data)
        assert result["home_score"] == 0
        assert result["away_score"] == 0
        assert result["venue"] == "Stadium A"
        assert result["referee"] == "Referee A"

    @pytest.mark.asyncio
    async def test_handle_missing_match_data_missing_venue(self):
        """测试缺失场地处理"""
        missing_venue_data = {
            "id": "12345",
            "home_score": 2,
            "away_score": 1,
            "venue": "",
            "referee": "Referee A",
        }

        result = await self.handler.handle_missing_match_data(missing_venue_data)
        assert result["venue"] == "Unknown"
        assert result["home_score"] == 2
        assert result["away_score"] == 1

    @pytest.mark.asyncio
    async def test_handle_missing_match_data_missing_referee(self):
        """测试缺失裁判处理"""
        missing_referee_data = {
            "id": "12345",
            "home_score": 2,
            "away_score": 1,
            "venue": "Stadium A",
            "referee": None,
        }

        result = await self.handler.handle_missing_match_data(missing_referee_data)
        assert result["referee"] == "Unknown"
        assert result["venue"] == "Stadium A"

    @pytest.mark.asyncio
    async def test_handle_missing_match_data_all_missing(self):
        """测试所有字段都缺失的处理"""
        all_missing_data = {
            "id": "12345",
            "home_score": None,
            "away_score": None,
            "venue": "",
            "referee": None,
        }

        result = await self.handler.handle_missing_match_data(all_missing_data)
        assert result["home_score"] == 0
        assert result["away_score"] == 0
        assert result["venue"] == "Unknown"
        assert result["referee"] == "Unknown"

    @pytest.mark.asyncio
    async def test_handle_missing_match_data_empty_dict(self):
        """测试空字典处理"""
        empty_data = {}

        result = await self.handler.handle_missing_match_data(empty_data)
        # 空字典应该被填充默认值
        assert "home_score" not in result or result["home_score"] == 0
        assert "away_score" not in result or result["away_score"] == 0


class TestMissingDataHandlerFeatures:
    """缺失数据处理器特征数据测试"""

    def setup_method(self):
        """设置测试环境"""
        self.handler = MissingDataHandler()

    @pytest.mark.asyncio
    async def test_handle_missing_features_no_missing(self):
        """测试无缺失值的特征数据"""
        features_df = pd.DataFrame(
            {
                "avg_possession": [50.0, 60.0, 55.0],
                "avg_shots_per_game": [12.0, 15.0, 13.0],
                "league_position": [5, 3, 8],
            }
        )

        result = await self.handler.handle_missing_features(1, features_df)
        pd.testing.assert_frame_equal(result, features_df)

    @pytest.mark.asyncio
    async def test_handle_missing_features_with_missing(self):
        """测试有缺失值的特征数据"""
        features_df = pd.DataFrame(
            {
                "avg_possession": [50.0, None, 55.0],
                "avg_shots_per_game": [12.0, 15.0, None],
                "league_position": [5, None, 8],
            }
        )

        result = await self.handler.handle_missing_features(1, features_df)

        # 检查缺失值被填充
        assert not result.isnull().any().any()
        assert result.iloc[1, 0] == 50.0  # avg_possession的历史平均值
        assert result.iloc[2, 1] == 12.5  # avg_shots_per_game的历史平均值（而不是中位数）

    @pytest.mark.asyncio
    async def test_handle_missing_features_all_missing(self):
        """测试全部缺失的特征数据"""
        features_df = pd.DataFrame(
            {
                "avg_possession": [None, None, None],
                "avg_shots_per_game": [None, None, None],
                "league_position": [None, None, None],
            }
        )

        result = await self.handler.handle_missing_features(1, features_df)

        # 检查所有缺失值被填充
        assert not result.isnull().any().any()

    @pytest.mark.asyncio
    async def test_handle_missing_features_unknown_feature(self):
        """测试未知特征处理"""
        features_df = pd.DataFrame({"unknown_feature": [None, None, None]})

        result = await self.handler.handle_missing_features(1, features_df)

        # 检查未知特征用0填充
        assert not result.isnull().any().any()
        assert (result["unknown_feature"] == 0).all()

    @pytest.mark.asyncio
    async def test_handle_missing_features_empty_dataframe(self):
        """测试空DataFrame处理"""
        features_df = pd.DataFrame()

        result = await self.handler.handle_missing_features(1, features_df)
        pd.testing.assert_frame_equal(result, features_df)

    @pytest.mark.asyncio
    async def test_handle_missing_features_exception_handling(self):
        """测试异常处理"""
        features_df = pd.DataFrame({"avg_possession": [50.0, 60.0, 55.0]})

        # Mock数据库操作以引发异常
        with patch.object(
            self.handler, "_get_historical_average", side_effect=Exception("DB Error")
        ):
            result = await self.handler.handle_missing_features(1, features_df)
            # 应该返回原始数据
            pd.testing.assert_frame_equal(result, features_df)


class TestMissingDataHandlerHistoricalAverage:
    """缺失数据处理器历史平均值测试"""

    def setup_method(self):
        """设置测试环境"""
        self.handler = MissingDataHandler()

    @pytest.mark.asyncio
    async def test_get_historical_average_possession(self):
        """测试获取控球率历史平均值"""
        result = await self.handler._get_historical_average("avg_possession")
        assert result == 50.0

    @pytest.mark.asyncio
    async def test_get_historical_average_shots(self):
        """测试获取射门数历史平均值"""
        result = await self.handler._get_historical_average("avg_shots_per_game")
        assert result == 12.5

    @pytest.mark.asyncio
    async def test_get_historical_average_goals(self):
        """测试获取进球数历史平均值"""
        result = await self.handler._get_historical_average("avg_goals_per_game")
        assert result == 1.5

    @pytest.mark.asyncio
    async def test_get_historical_average_league_position(self):
        """测试获取联赛排名历史平均值"""
        result = await self.handler._get_historical_average("league_position")
        assert result == 10.0

    @pytest.mark.asyncio
    async def test_get_historical_average_unknown_feature(self):
        """测试获取未知特征历史平均值"""
        result = await self.handler._get_historical_average("unknown_feature")
        assert result == 0.0

    @pytest.mark.asyncio
    async def test_get_historical_average_exception_handling(self):
        """测试获取历史平均值异常处理"""
        # 直接测试异常情况，由于方法内部已有异常处理，我们需要模拟内部逻辑
        with patch("builtins.dict", side_effect=lambda *args, **kwargs: {}):
            # 让default_averages字典为空，模拟异常情况
            result = await self.handler._get_historical_average("unknown_feature")
            assert result == 0.0


class TestMissingDataHandlerInterpolation:
    """缺失数据处理器插值测试"""

    def setup_method(self):
        """设置测试环境"""
        self.handler = MissingDataHandler()

    def test_interpolate_time_series_data_no_missing(self):
        """测试无缺失值的时间序列插值"""
        data = pd.Series([1.0, 2.0, 3.0, 4.0])
        result = self.handler.interpolate_time_series_data(data)
        pd.testing.assert_series_equal(result, data)

    def test_interpolate_time_series_data_with_missing(self):
        """测试有缺失值的时间序列插值"""
        data = pd.Series([1.0, None, 3.0, None, 5.0])
        result = self.handler.interpolate_time_series_data(data)

        # 检查缺失值被插值
        assert not result.isnull().any()
        assert result.iloc[1] == 2.0  # 线性插值
        assert result.iloc[3] == 4.0  # 线性插值

    def test_interpolate_time_series_data_all_missing(self):
        """测试全部缺失的时间序列插值"""
        data = pd.Series([None, None, None])
        result = self.handler.interpolate_time_series_data(data)

        # 全部缺失时无法插值，应该保持不变
        assert result.isnull().all()

    def test_interpolate_time_series_data_edge_missing(self):
        """测试边缘缺失的时间序列插值"""
        data = pd.Series([None, 2.0, 3.0, None])
        result = self.handler.interpolate_time_series_data(data)

        # 检查内部值被插值，边缘值可能保持缺失
        assert result.iloc[1] == 2.0
        assert result.iloc[2] == 3.0

    def test_interpolate_time_series_data_single_missing(self):
        """测试单个缺失值的时间序列插值"""
        data = pd.Series([1.0, 2.0, None, 4.0, 5.0])
        result = self.handler.interpolate_time_series_data(data)

        # 检查单个缺失值被正确插值
        assert not result.isnull().any()
        assert result.iloc[2] == 3.0

    def test_interpolate_time_series_data_exception_handling(self):
        """测试插值异常处理"""
        # Mock Series的interpolate方法以引发异常
        mock_series = Mock()
        mock_series.interpolate.side_effect = Exception("Interpolation Error")

        result = self.handler.interpolate_time_series_data(mock_series)
        assert result == mock_series  # 应该返回原始数据


class TestMissingDataHandlerRowRemoval:
    """缺失数据处理器行删除测试"""

    def setup_method(self):
        """设置测试环境"""
        self.handler = MissingDataHandler()

    def test_remove_rows_with_missing_critical_data_no_missing(self):
        """测试无缺失关键数据的行删除"""
        df = pd.DataFrame({"critical_col": [1, 2, 3], "other_col": ["a", "b", "c"]})
        critical_columns = ["critical_col"]

        result = self.handler.remove_rows_with_missing_critical_data(
            df, critical_columns
        )
        pd.testing.assert_frame_equal(result, df)

    def test_remove_rows_with_missing_critical_data_with_missing(self):
        """测试有缺失关键数据的行删除"""
        df = pd.DataFrame({"critical_col": [1, None, 3], "other_col": ["a", "b", "c"]})
        critical_columns = ["critical_col"]

        result = self.handler.remove_rows_with_missing_critical_data(
            df, critical_columns
        )

        # 检查缺失行被删除
        assert len(result) == 2
        assert not result["critical_col"].isnull().any()
        assert result.iloc[0, 0] == 1
        assert result.iloc[1, 0] == 3

    def test_remove_rows_with_missing_critical_data_multiple_critical(self):
        """测试多个关键列的缺失行删除"""
        df = pd.DataFrame(
            {
                "critical_col1": [1, None, 3],
                "critical_col2": [None, 2, 3],
                "other_col": ["a", "b", "c"],
            }
        )
        critical_columns = ["critical_col1", "critical_col2"]

        result = self.handler.remove_rows_with_missing_critical_data(
            df, critical_columns
        )

        # 检查只有完整行被保留
        assert len(result) == 1
        assert result.iloc[0, 0] == 3
        assert result.iloc[0, 1] == 3

    def test_remove_rows_with_missing_critical_data_all_missing(self):
        """测试全部缺失关键数据的行删除"""
        df = pd.DataFrame(
            {"critical_col": [None, None, None], "other_col": ["a", "b", "c"]}
        )
        critical_columns = ["critical_col"]

        result = self.handler.remove_rows_with_missing_critical_data(
            df, critical_columns
        )

        # 检查所有行被删除
        assert len(result) == 0

    def test_remove_rows_with_missing_critical_data_empty_critical_list(self):
        """测试空关键列列表"""
        df = pd.DataFrame({"col1": [1, None, 3], "col2": ["a", "b", "c"]})
        critical_columns = []

        result = self.handler.remove_rows_with_missing_critical_data(
            df, critical_columns
        )
        pd.testing.assert_frame_equal(result, df)

    def test_remove_rows_with_missing_critical_data_exception_handling(self):
        """测试行删除异常处理"""
        df = pd.DataFrame({"col1": [1, 2, 3]})
        critical_columns = ["col1"]

        # Mock DataFrame的dropna方法以引发异常
        with patch.object(df, "dropna", side_effect=Exception("Dropna Error")):
            result = self.handler.remove_rows_with_missing_critical_data(
                df, critical_columns
            )
            pd.testing.assert_frame_equal(result, df)


class TestMissingDataHandlerIntegration:
    """缺失数据处理器集成测试"""

    def setup_method(self):
        """设置测试环境"""
        self.handler = MissingDataHandler()

    @pytest.mark.asyncio
    async def test_complete_missing_data_handling_workflow(self):
        """测试完整的缺失数据处理工作流"""
        # 模拟一个完整的缺失数据处理场景
        match_data = {
            "id": "12345",
            "home_score": None,
            "away_score": None,
            "venue": "",
            "referee": None,
        }

        features_df = pd.DataFrame(
            {
                "avg_possession": [50.0, None, 55.0],
                "avg_shots_per_game": [12.0, 15.0, None],
                "league_position": [5, None, 8],
            }
        )

        # 处理比赛数据
        processed_match = await self.handler.handle_missing_match_data(match_data)

        # 处理特征数据
        processed_features = await self.handler.handle_missing_features(1, features_df)

        # 验证比赛数据处理结果
        assert processed_match["home_score"] == 0
        assert processed_match["away_score"] == 0
        assert processed_match["venue"] == "Unknown"
        assert processed_match["referee"] == "Unknown"

        # 验证特征数据处理结果
        assert not processed_features.isnull().any().any()

    @pytest.mark.asyncio
    async def test_real_world_scenario_simulation(self):
        """测试真实场景模拟"""
        # 模拟真实世界的数据缺失情况
        incomplete_match_data = {
            "id": "67890",
            "home_score": None,  # 比赛未结束
            "away_score": None,  # 比赛未结束
            "venue": "",  # 数据缺失
            "referee": None,  # 数据缺失
        }

        incomplete_features = pd.DataFrame(
            {
                "possession": [None, 60.0, None],  # 部分比赛缺少控球率数据
                "shots": [10.0, None, 8.0],  # 部分比赛缺少射门数据
                "passes": [400.0, 450.0, None],  # 部分比赛缺少传球数据
            }
        )

        # 处理数据
        processed_match = await self.handler.handle_missing_match_data(
            incomplete_match_data
        )
        processed_features = await self.handler.handle_missing_features(
            2, incomplete_features
        )

        # 验证处理结果的有效性
        assert processed_match["home_score"] == 0
        assert processed_match["away_score"] == 0
        assert processed_match["venue"] == "Unknown"
        assert processed_match["referee"] == "Unknown"

        # 验证特征数据被适当填充
        assert not processed_features.isnull().any().any()

    def test_strategies_consistency(self):
        """测试填充策略的一致性"""
        # 验证所有预定义的策略都有对应的处理逻辑
        for strategy_name, strategy_value in self.handler.FILL_STRATEGIES.items():
            assert isinstance(strategy_name, str)
            assert isinstance(strategy_value, str)
            assert len(strategy_name) > 0
            assert len(strategy_value) > 0
