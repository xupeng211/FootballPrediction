"""
TDD Rolling Window Features Tests - 滚动窗口特征测试驱动开发

Phase 2: AI Modeling - 滚动窗口特征测试用例

按照TDD原则，先定义测试用例，明确滚动窗口特征应该具备的行为和接口。
重点测试数据泄露防护和时间序列安全性。
"""

import pytest
from datetime import datetime, timezone
from typing import List
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

# 注意：此时RollingAverageTransformer还不存在，这是TDD的核心
# 我们先定义期望的接口，然后在下一步实现


class TestRollingAverageTransformer:
    """滚动平均特征转换器的TDD测试用例"""

    @pytest.fixture
    def sample_team_data(self) -> pd.DataFrame:
        """
        创建示例团队数据，模拟真实的比赛数据结构。

        数据设计重点：
        1. 时间序列：包含match_date，确保时序安全
        2. 多团队：包含多个team_id，测试分组计算
        3. 目标变量：goals作为计算目标
        4. 历史数据：确保有足够历史记录进行滚动计算
        """
        return pd.DataFrame({
            'match_date': pd.date_range('2024-01-01', periods=12, freq='D'),
            'team_id': ['Team_A'] * 4 + ['Team_B'] * 4 + ['Team_C'] * 4,
            'goals': [2, 1, 3, 2, 1, 0, 2, 1, 3, 2, 4, 1],
            'shots': [10, 8, 15, 12, 6, 4, 8, 7, 12, 10, 16, 9],
            'possession': [55, 48, 62, 58, 42, 35, 45, 38, 65, 60, 70, 55],
        })

    @pytest.fixture
    def empty_data(self) -> pd.DataFrame:
        """创建空数据测试边界条件。"""
        return pd.DataFrame(columns=['match_date', 'team_id', 'goals'])

    def test_rolling_average_transformer_interface_definition(self):
        """
        测试目标：验证RollingAverageTransformer类的接口定义。

        期望行为：
        1. RollingAverageTransformer类应该存在
        2. 应该继承自BaseFeatureTransformer
        3. 应该有fit和transform方法
        4. 应该支持窗口大小配置
        """
        # 这个测试会失败，因为RollingAverageTransformer还不存在
        # 这是TDD的第一步：红阶段 (Red)
        from src.ml.features.rolling import RollingAverageTransformer

        # 验证类存在和继承关系
        assert RollingAverageTransformer is not None

        # 验证可以实例化
        transformer = RollingAverageTransformer(
            column='goals',
            window_size=3,
            group_by=['team_id']
        )

        # 验证接口方法存在
        assert hasattr(transformer, 'fit')
        assert hasattr(transformer, 'transform')
        assert hasattr(transformer, 'fit_transform')

    @pytest.mark.asyncio
    async def test_rolling_average_basic_functionality(self, sample_team_data):
        """
        测试目标：验证滚动平均基本功能。

        期望行为：
        1. 应该生成rolling_goals_3列
        2. 输出行数应与输入一致
        3. 计算正确的滚动平均值
        4. 保持输入数据的完整性
        """
        from src.ml.features.rolling import RollingAverageTransformer

        # 创建转换器
        transformer = RollingAverageTransformer(
            column='goals',
            window_size=3,
            group_by=['team_id']
        )

        # 执行转换
        result = transformer.fit_transform(sample_team_data)

        # 验证输出结构
        assert 'rolling_goals_3' in result.columns, "应该生成滚动平均特征列"
        assert len(result) == len(sample_team_data), "输出行数应与输入一致"

        # 验证基础数据完整性
        assert all(col in result.columns for col in sample_team_data.columns), \
            "应该保留所有输入列"

    @pytest.mark.asyncio
    async def test_rolling_average_anti_leakage_critical(self, sample_team_data):
        """
        测试目标：验证防数据泄露机制（关键测试）。

        期望行为：
        1. CRITICAL: 第一个记录必须为NaN（无历史数据）
        2. CRITICAL: 同一天的数据不能用于当日计算
        3. 严格的时间序列安全：只能使用t-1, t-2...的数据
        4. 防止未来信息泄露到过去

        这个测试是ML生产环境的关键安全检查！
        """
        from src.ml.features.rolling import RollingAverageTransformer

        transformer = RollingAverageTransformer(
            column='goals',
            window_size=3,
            group_by=['team_id']
        )

        result = transformer.fit_transform(sample_team_data)

        # 关键防泄露检查
        team_a_rows = result[result['team_id'] == 'Team_A']

        # 第一个Team_A记录必须为NaN（没有历史数据）
        first_team_a_value = team_a_rows['rolling_goals_3'].iloc[0]
        assert pd.isna(first_team_a_value), \
            f"第一个记录应该是NaN，但得到: {first_team_a_value}"

        # 第2个Team_A记录应该基于第1个记录计算
        second_team_a_value = team_a_rows['rolling_goals_3'].iloc[1]
        expected_second_value = sample_team_data[sample_team_data['team_id'] == 'Team_A']['goals'].iloc[0]
        assert second_team_a_value == expected_second_value, \
            f"第2个记录应该等于第1个记录: expected={expected_second_value}, got={second_team_a_value}"

        # 第4个Team_A记录应该基于第1-3个记录计算
        fourth_team_a_value = team_a_rows['rolling_goals_3'].iloc[3]
        team_a_goals = sample_team_data[sample_team_data['team_id'] == 'Team_A']['goals'].iloc[:3]
        expected_fourth_value = team_a_goals.mean()
        assert abs(fourth_team_a_value - expected_fourth_value) < 1e-6, \
            f"第4个记录应该是前3个的平均值: expected={expected_fourth_value}, got={fourth_team_a_value}"

    @pytest.mark.asyncio
    async def test_rolling_average_different_window_sizes(self, sample_team_data):
        """
        测试目标：验证不同窗口大小的行为。

        期望行为：
        1. window_size=1应该返回前一行的值
        2. window_size=2应该基于前2行计算
        3. 大窗口在数据不足时应该返回NaN
        """
        from src.ml.features.rolling import RollingAverageTransformer

        # 测试window_size=1
        transformer_1 = RollingAverageTransformer(
            column='goals',
            window_size=1,
            group_by=['team_id']
        )
        result_1 = transformer_1.fit_transform(sample_team_data)

        # 第一个记录应该是NaN
        assert pd.isna(result_1[result_1['team_id'] == 'Team_A']['rolling_goals_1'].iloc[0])

        # 第二个记录应该等于第一个记录
        team_a_result_1 = result_1[result_1['team_id'] == 'Team_A']
        assert team_a_result_1['rolling_goals_1'].iloc[1] == 2.0

        # 测试window_size=5（大于可用数据）
        transformer_5 = RollingAverageTransformer(
            column='goals',
            window_size=5,
            group_by=['team_id']
        )
        result_5 = transformer_5.fit_transform(sample_team_data)

        # 所有记录都应该是NaN（窗口大小大于历史数据）
        team_a_result_5 = result_5[result_5['team_id'] == 'Team_A']
        assert team_a_result_5['rolling_goals_5'].isna().all(), \
            "窗口大于历史数据时，所有值应该是NaN"

    @pytest.mark.asyncio
    async def test_rolling_average_multiple_columns(self, sample_team_data):
        """
        测试目标：验证多列滚动平均功能。

        期望行为：
        1. 可以同时计算多个列的滚动平均
        2. 每个列有独立的滚动窗口
        3. 正确处理不同列的数据类型
        """
        from src.ml.features.rolling import RollingAverageTransformer

        transformer = RollingAverageTransformer(
            columns=['goals', 'shots', 'possession'],
            window_size=2,
            group_by=['team_id']
        )

        result = transformer.fit_transform(sample_team_data)

        # 验证所有特征列都存在
        expected_columns = ['rolling_goals_2', 'rolling_shots_2', 'rolling_possession_2']
        for col in expected_columns:
            assert col in result.columns, f"应该包含列: {col}"

        # 验证防泄露仍然有效
        team_a_rows = result[result['team_id'] == 'Team_A']
        assert pd.isna(team_a_rows['rolling_goals_2'].iloc[0]), \
            "多列情况下也要防泄露"

    @pytest.mark.asyncio
    async def test_rolling_average_empty_data(self, empty_data):
        """
        测试目标：验证空数据处理。

        期望行为：
        1. 空数据应该正常处理
        2. 应该返回空的DataFrame
        3. 不应该抛出异常
        """
        from src.ml.features.rolling import RollingAverageTransformer

        transformer = RollingAverageTransformer(
            column='goals',
            window_size=3,
            group_by=['team_id']
        )

        # 应该不抛出异常
        result = transformer.fit_transform(empty_data)

        # 应该返回空DataFrame
        assert len(result) == 0, "空数据应该返回空DataFrame"
        assert 'rolling_goals_3' in result.columns, "即使空数据也应该包含特征列"

    @pytest.mark.asyncio
    async def test_rolling_average_invalid_input(self, sample_team_data):
        """
        测试目标：验证无效输入的处理。

        期望行为：
        1. 缺少必需列应该抛出异常
        2. 无效的窗口大小应该抛出异常
        3. 输入类型错误应该抛出异常
        """
        from src.ml.features.rolling import RollingAverageTransformer

        transformer = RollingAverageTransformer(
            column='goals',
            window_size=3,
            group_by=['team_id']
        )

        # 测试缺失必需列
        invalid_data = sample_team_data.drop('goals', axis=1)

        with pytest.raises(ValueError, match="缺少必需列"):
            transformer.fit_transform(invalid_data)

        # 测试无效窗口大小
        with pytest.raises(ValueError, match="window_size"):
            RollingAverageTransformer(
                column='goals',
                window_size=0,
                group_by=['team_id']
            )

    @pytest.mark.asyncio
    async def test_rolling_average_fit_transform_consistency(self, sample_team_data):
        """
        测试目标：验证fit和transform的一致性。

        期望行为：
        1. fit_transform应该等于fit().transform()
        2. 重复调用transform应该返回相同结果
        3. 状态应该保持一致
        """
        from src.ml.features.rolling import RollingAverageTransformer

        transformer1 = RollingAverageTransformer(
            column='goals',
            window_size=2,
            group_by=['team_id']
        )
        transformer2 = RollingAverageTransformer(
            column='goals',
            window_size=2,
            group_by=['team_id']
        )

        # fit_transform vs fit().transform()
        result1 = transformer1.fit_transform(sample_team_data.copy())
        result2 = transformer2.fit(sample_team_data.copy()).transform(sample_team_data.copy())

        pd.testing.assert_frame_equal(result1, result2,
                                     "fit_transform应该等于fit().transform()")

        # 重复transform测试
        result3 = transformer2.transform(sample_team_data.copy())
        pd.testing.assert_frame_equal(result2, result3,
                                     "重复transform应该返回相同结果")

    @pytest.mark.asyncio
    async def test_rolling_average_feature_names(self, sample_team_data):
        """
        测试目标：验证特征名称生成。

        期望行为：
        1. get_feature_names_out应该返回正确的特征名称
        2. 特征名称应该包含列名和窗口大小
        3. 特征名称应该符合ML管道要求
        """
        from src.ml.features.rolling import RollingAverageTransformer

        transformer = RollingAverageTransformer(
            column='goals',
            window_size=3,
            group_by=['team_id']
        )

        # 先fit
        transformer.fit(sample_team_data)

        # 获取特征名称
        feature_names = transformer.get_feature_names_out()

        assert isinstance(feature_names, list), "特征名称应该是列表"
        assert 'rolling_goals_3' in feature_names, "应该包含正确的特征名称"

        # 验证transform结果包含这些特征
        result = transformer.transform(sample_team_data)
        for name in feature_names:
            assert name in result.columns, f"结果应该包含特征: {name}"


class TestRollingSumTransformer:
    """滚动求和特征转换器的TDD测试用例"""

    @pytest.fixture
    def sample_cumulative_data(self) -> pd.DataFrame:
        """
        创建累积数据测试滚动求和功能。
        """
        return pd.DataFrame({
            'match_date': pd.date_range('2024-01-01', periods=8, freq='D'),
            'team_id': ['Team_A'] * 8,
            'goals': [1, 2, 1, 3, 2, 4, 1, 2],
            'yellow_cards': [1, 2, 0, 1, 3, 2, 1, 0],
        })

    def test_rolling_sum_transformer_interface_definition(self, sample_cumulative_data):
        """
        测试目标：验证RollingSumTransformer类的接口定义。
        """
        # 这会失败，因为RollingSumTransformer还不存在
        from src.ml.features.rolling import RollingSumTransformer

        transformer = RollingSumTransformer(
            column='goals',
            window_size=3,
            group_by=['team_id']
        )

        assert hasattr(transformer, 'fit')
        assert hasattr(transformer, 'transform')

    @pytest.mark.asyncio
    async def test_rolling_sum_basic_functionality(self, sample_cumulative_data):
        """
        测试目标：验证滚动求和基本功能。
        """
        from src.ml.features.rolling import RollingSumTransformer

        transformer = RollingSumTransformer(
            column='goals',
            window_size=3,
            group_by=['team_id']
        )

        result = transformer.fit_transform(sample_cumulative_data)

        assert 'rolling_sum_goals_3' in result.columns
        assert len(result) == len(sample_cumulative_data)

        # 验证计算正确性
        # 第4行应该是前3行的和: 1 + 2 + 1 = 4
        assert result['rolling_sum_goals_3'].iloc[3] == 4.0

        # 防泄露：第1行应该是NaN
        assert pd.isna(result['rolling_sum_goals_3'].iloc[0])


@pytest.mark.integration
class TestRollingFeaturesIntegration:
    """滚动窗口特征集成测试"""

    @pytest.fixture
    def large_sample_data(self) -> pd.DataFrame:
        """创建更大的样本数据用于集成测试。"""
        np.random.seed(42)
        n_matches = 100
        n_teams = 10
        teams = [f'Team_{i}' for i in range(n_teams)]

        data = []
        for i in range(n_matches):
            team_id = np.random.choice(teams)
            data.append({
                'match_date': pd.Timestamp('2024-01-01') + pd.Timedelta(days=i),
                'team_id': team_id,
                'goals': np.random.poisson(1.5),
                'shots': np.random.poisson(12),
                'possession': np.random.normal(50, 15),
            })

        return pd.DataFrame(data)

    @pytest.mark.asyncio
    async def test_rolling_features_performance(self, large_sample_data):
        """
        测试目标：验证滚动特征的性能。

        期望行为：
        1. 应该在合理时间内完成
        2. 内存使用应该可控
        3. 应该处理大数据集
        """
        from src.ml.features.rolling import RollingAverageTransformer

        transformer = RollingAverageTransformer(
            columns=['goals', 'shots'],
            window_size=5,
            group_by=['team_id']
        )

        # 测试性能
        import time
        start_time = time.time()

        result = transformer.fit_transform(large_sample_data.copy())

        end_time = time.time()
        processing_time = end_time - start_time

        assert len(result) == len(large_sample_data)
        assert processing_time < 5.0, f"处理时间过长: {processing_time:.2f}秒"

    @pytest.mark.slow
    async def test_rolling_features_memory_efficiency(self):
        """
        测试目标：验证内存效率。

        期望行为：
        1. 应该避免内存泄漏
        2. 应该正确处理大数据集
        """
        from src.ml.features.rolling import RollingAverageTransformer

        # 创建大量数据
        large_data = pd.DataFrame({
            'match_date': pd.date_range('2020-01-01', periods=10000, freq='D'),
            'team_id': ['Team_A'] * 10000,
            'goals': np.random.poisson(1.5, 10000),
        })

        transformer = RollingAverageTransformer(
            column='goals',
            window_size=10,
            group_by=['team_id']
        )

        # 应该能处理大数据集
        result = transformer.fit_transform(large_data.copy())
        assert len(result) == len(large_data)

        # 清理内存
        del large_data, result
        import gc
        gc.collect()