#!/usr/bin/env python3
"""
足球数据清洗器单元测试

测试 src.data.processing.football_data_cleaner 模块的功能
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

# 导入被测试的模块
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from src.data.processing.football_data_cleaner import FootballDataCleaner


class TestFootballDataCleaner:
    """足球数据清洗器测试类"""

    @pytest.fixture
    def cleaner(self):
        """创建清洗器实例"""
        return FootballDataCleaner()

    @pytest.fixture
    def sample_match_data(self):
        """创建示例比赛数据"""
        return pd.DataFrame({
            'match_id': [1, 2, 3, 4, 5, 1],  # 包含重复
            'home_team_id': [100, 200, 300, 400, 500, 100],
            'away_team_id': [200, 100, 400, 300, 600, 200],
            'home_score': [2, 1, 0, 3, 1, 2],
            'away_score': [1, 2, 1, 0, 0, 1],
            'match_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05', '2024-01-01'],
            'home_goals': [2, 1, 0, 3, 1, 2],
            'away_goals': [1, 2, 1, 0, 0, 1],
            'possession_home': [60.5, 45.2, 52.1, 58.7, 49.8, 60.5],
            'possession_away': [39.5, 54.8, 47.9, 41.3, 50.2, 39.5]
        })

    @pytest.fixture
    def sample_data_with_missing(self):
        """创建包含缺失值的示例数据"""
        return pd.DataFrame({
            'match_id': [1, 2, 3, 4],
            'home_team_id': [100, 200, np.nan, 400],
            'away_team_id': [200, np.nan, 400, 300],
            'home_score': [2, np.nan, 0, 3],
            'away_score': [1, 2, np.nan, 0],
            'match_date': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04'],
            'possession_home': [60.5, 45.2, np.nan, 58.7],
            'possession_away': [39.5, np.nan, 47.9, 41.3]
        })

    def test_cleaner_initialization(self, cleaner):
        """测试清洗器初始化"""
        assert cleaner is not None
        assert hasattr(cleaner, '_get_default_config')
        assert hasattr(cleaner, 'clean_dataset')
        assert hasattr(cleaner, 'get_cleaning_report')

    def test_default_config(self, cleaner):
        """测试默认配置"""
        config = cleaner._get_default_config()
        assert isinstance(config, dict)
        assert 'remove_duplicates' in config
        assert 'handle_missing' in config
        assert 'detect_outliers' in config
        assert 'validate_data' in config
        assert config['remove_duplicates'] is True
        assert config['handle_missing'] is True

    def test_remove_duplicates_with_match_id(self, cleaner, sample_match_data):
        """测试基于match_id的去重功能"""
        original_count = len(sample_match_data)
        cleaned_data = cleaner._remove_duplicates(sample_match_data, 'matches')

        # 应该移除一个重复项
        assert len(cleaned_data) == original_count - 1
        assert len(cleaned_data) == 5

        # 验证没有重复的match_id
        assert cleaned_data['match_id'].nunique() == len(cleaned_data)

    def test_remove_duplicates_general(self, cleaner):
        """测试通用去重功能"""
        data = pd.DataFrame({
            'col1': [1, 2, 2, 3],
            'col2': ['a', 'b', 'b', 'c']
        })
        cleaned_data = cleaner._remove_duplicates(data, 'general')

        # 应该移除重复行
        assert len(cleaned_data) == 3
        assert cleaned_data['col1'].tolist() == [1, 2, 3]

    def test_handle_missing_values_numeric(self, cleaner):
        """测试数值型缺失值处理"""
        data = pd.DataFrame({
            'numeric_col': [1, 2, np.nan, 4, 5],
            'text_col': ['A', 'B', 'C', 'D', 'E']
        })

        processed_data = cleaner._handle_missing_values_adaptive(data.copy())

        # 数值列应该用中位数填充
        assert processed_data['numeric_col'].isnull().sum() == 0
        expected_median = 3.0  # [1, 2, 4, 5] 的中位数
        assert processed_data.loc[2, 'numeric_col'] == expected_median

    def test_handle_missing_values_text(self, cleaner):
        """测试文本型缺失值处理"""
        data = pd.DataFrame({
            'numeric_col': [1, 2, 3, 4, 5],
            'text_col': ['A', 'B', np.nan, 'D', 'E']
        })

        processed_data = cleaner._handle_missing_values_adaptive(data.copy())

        # 文本列应该用'Unknown'填充
        assert processed_data['text_col'].isnull().sum() == 0
        assert processed_data.loc[2, 'text_col'] == 'Unknown'

    def test_detect_outliers_iqr(self, cleaner):
        """测试IQR异常值检测"""
        # 创建包含异常值的数据
        data = pd.Series([1, 2, 3, 4, 5, 100])  # 100是异常值
        outliers = cleaner._detect_outliers_iqr(data)

        assert outliers.sum() == 1
        assert outliers.iloc[-1] is True  # 最后一个值是异常值

    def test_handle_outliers(self, cleaner):
        """测试异常值处理"""
        data = pd.DataFrame({
            'values': [1, 2, 3, 4, 5, 100]
        })
        outliers = pd.Series([False, False, False, False, False, True])

        processed_data = cleaner._handle_outliers(data.copy(), 'values', outliers)

        # 异常值应该被替换为边界值
        assert processed_data.loc[5, 'values'] < 100
        # 检查替换的值是否合理（应该是上边界）
        Q1 = data['values'].quantile(0.25)
        Q3 = data['values'].quantile(0.75)
        IQR = Q3 - Q1
        upper_bound = Q3 + 1.5 * IQR
        assert processed_data.loc[5, 'values'] == upper_bound

    def test_clean_dataset_complete_workflow(self, cleaner, sample_data_with_missing):
        """测试完整的数据清洗工作流"""
        original_shape = sample_data_with_missing.shape
        cleaned_data = cleaner.clean_dataset(sample_data_with_missing, 'matches')

        # 验证清洗后的数据
        assert isinstance(cleaned_data, pd.DataFrame)
        assert len(cleaned_data) > 0  # 应该还有数据剩余

        # 验证缺失值被处理
        assert cleaned_data.isnull().sum().sum() < original_shape[0] * original_shape[1]

        # 验证数据完整性
        assert 'match_id' in cleaned_data.columns
        assert 'home_team_id' in cleaned_data.columns

    def test_get_cleaning_report(self, cleaner, sample_data_with_missing):
        """测试清洗报告"""
        # 执行清洗
        cleaner.clean_dataset(sample_data_with_missing, 'matches')

        # 获取报告
        report = cleaner.get_cleaning_report()

        assert isinstance(report, dict)
        assert 'original_shape' in report
        assert 'cleaned_shape' in report
        assert 'cleaning_steps' in report

        assert report['original_shape'] == sample_data_with_missing.shape
        assert isinstance(report['cleaning_steps'], list)

    def test_data_validation(self, cleaner):
        """测试数据验证功能"""
        valid_data = pd.DataFrame({
            'match_id': [1, 2, 3],
            'home_score': [1, 2, 3],
            'away_score': [0, 1, 2]
        })

        # 有效数据应该通过验证
        validation_result = cleaner._validate_data(valid_data)
        assert validation_result is True

    def test_invalid_data_handling(self, cleaner):
        """测试无效数据处理"""
        invalid_data = pd.DataFrame({
            'match_id': [-1, 0, 1],  # 包含无效ID
            'home_score': [1, 2, 3],
            'away_score': [0, 1, 2]
        })

        # 无效数据应该被标记或修复
        processed_data = cleaner._validate_and_fix_data(invalid_data)
        assert len(processed_data) == len(invalid_data)
        # 可能的验证逻辑取决于具体实现

    def test_edge_cases(self, cleaner):
        """测试边界情况"""
        # 空数据框
        empty_data = pd.DataFrame()
        result = cleaner.clean_dataset(empty_data, 'matches')
        assert isinstance(result, pd.DataFrame)

        # 单行数据
        single_row = pd.DataFrame({
            'match_id': [1],
            'home_score': [1],
            'away_score': [0]
        })
        result = cleaner.clean_dataset(single_row, 'matches')
        assert len(result) == 1

    def test_performance_with_large_dataset(self, cleaner):
        """测试大数据集性能"""
        # 创建较大的数据集
        large_data = pd.DataFrame({
            'match_id': range(1000),
            'home_score': np.random.randint(0, 10, 1000),
            'away_score': np.random.randint(0, 10, 1000),
            'possession_home': np.random.uniform(30, 70, 1000),
            'possession_away': np.random.uniform(30, 70, 1000)
        })

        # 添加一些缺失值
        large_data.loc[10:20, 'home_score'] = np.nan

        start_time = datetime.now()
        result = cleaner.clean_dataset(large_data, 'matches')
        end_time = datetime.now()

        # 验证处理时间合理（应该在几秒内完成）
        processing_time = (end_time - start_time).total_seconds()
        assert processing_time < 10.0  # 应该在10秒内完成
        assert len(result) > 0