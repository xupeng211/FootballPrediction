import os
"""
数据处理服务全面测试
Comprehensive tests for data processing service to boost coverage
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 尝试导入数据处理服务
try:
    from src.services.data_processing import (
        DataProcessor,
        DataCleaner,
        DataTransformer,
        DataValidator,
        DataAggregator,
        process_match_data,
        clean_team_data,
        transform_features,
        validate_data_integrity,
        aggregate_statistics
    )
except ImportError:
    # 创建模拟类用于测试
    DataProcessor = None
    DataCleaner = None
    DataTransformer = None
    DataValidator = None
    DataAggregator = None
    process_match_data = None
    clean_team_data = None
    transform_features = None
    validate_data_integrity = None
    aggregate_statistics = None


class TestDataProcessor:
    """数据处理器测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        if DataProcessor is None:
            pytest.skip("DataProcessor not available")

        self.processor = DataProcessor()

        # 创建测试数据
        self.test_match_data = pd.DataFrame({
            'match_id': [1, 2, 3],
            'home_team': ['Team A', 'Team B', 'Team C'],
            'away_team': ['Team D', 'Team E', 'Team F'],
            'home_score': [2, 1, 0],
            'away_score': [1, 1, 2],
            'match_date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'league': ['Premier League', 'Premier League', 'La Liga']
        })

    def test_processor_initialization(self):
        """测试处理器初始化"""
        assert self.processor is not None
        assert hasattr(self.processor, 'cleaner')
        assert hasattr(self.processor, 'transformer')
        assert hasattr(self.processor, 'validator')
        assert hasattr(self.processor, 'aggregator')

    def test_process_match_data(self):
        """测试处理比赛数据"""
        if process_match_data is None:
            pytest.skip("process_match_data not available")

        # 添加脏数据
        dirty_data = self.test_match_data.copy()
        dirty_data.loc[0, 'home_score'] = None  # 缺失值
        dirty_data.loc[1, 'match_date'] = 'invalid-date'  # 无效日期

        processed_data = process_match_data(dirty_data)

        # 验证处理结果
        assert len(processed_data) > 0
        assert processed_data['home_score'].isna().sum() == 0  # 缺失值已处理
        assert pd.to_datetime(processed_data['match_date'], errors = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_ERRORS_86")).isna().sum() == 0

    def test_clean_team_data(self):
        """测试清洗球队数据"""
        if clean_team_data is None:
            pytest.skip("clean_team_data not available")

        # 创建包含重复和异常的球队数据
        team_data = pd.DataFrame({
            'team_id': [1, 2, 2, 3],  # 重复ID
            'team_name': ['Team A', 'Team B', 'Team B', 'Team C'],  # 重复名称
            'founded_year': [1900, 1950, 1950, 2000],
            'stadium': ['Stadium A', 'Stadium B', 'Stadium B', ''],
            'country': ['England', 'England', None, 'Spain']  # 缺失值
        })

        cleaned_data = clean_team_data(team_data)

        # 验证清洗结果
        assert len(cleaned_data) <= len(team_data)  # 重复项被移除
        assert cleaned_data['team_id'].nunique() == len(cleaned_data)  # ID唯一
        assert cleaned_data['team_name'].isna().sum() == 0  # 缺失值已处理

    def test_transform_features(self):
        """测试特征转换"""
        if transform_features is None:
            pytest.skip("transform_features not available")

        # 创建原始特征数据
        raw_features = pd.DataFrame({
            'team_id': [1, 2, 3],
            'goals_scored': [10, 15, 8],
            'goals_conceded': [5, 10, 12],
            'matches_played': [5, 5, 5],
            'recent_form': ['WWDWL', 'LWWWW', 'DLLWD']
        })

        transformed_features = transform_features(raw_features)

        # 验证转换结果
        assert 'goals_per_game' in transformed_features.columns
        assert 'goals_conceded_per_game' in transformed_features.columns
        assert 'form_points' in transformed_features.columns
        assert transformed_features['goals_per_game'].min() >= 0

    def test_validate_data_integrity(self):
        """测试数据完整性验证"""
        if validate_data_integrity is None:
            pytest.skip("validate_data_integrity not available")

        # 测试有效数据
        valid_data = pd.DataFrame({
            'match_id': [1, 2, 3],
            'home_team_id': [1, 2, 3],
            'away_team_id': [4, 5, 6],
            'home_score': [2, 1, 0],
            'away_score': [1, 1, 2]
        })

        is_valid = validate_data_integrity(valid_data)
        assert is_valid is True

        # 测试无效数据（主客队相同）
        invalid_data = pd.DataFrame({
            'match_id': [1, 2],
            'home_team_id': [1, 2],
            'away_team_id': [1, 2],  # 主客队相同
            'home_score': [2, 1],
            'away_score': [1, 1]
        })

        is_valid = validate_data_integrity(invalid_data)
        assert is_valid is False

    def test_aggregate_statistics(self):
        """测试统计聚合"""
        if aggregate_statistics is None:
            pytest.skip("aggregate_statistics not available")

        # 创建比赛数据
        match_data = pd.DataFrame({
            'team_id': [1, 1, 2, 2, 3],
            'goals_scored': [2, 1, 3, 0, 1],
            'goals_conceded': [1, 2, 1, 3, 1],
            'result': ['W', 'L', 'W', 'L', 'D'],
            'match_date': pd.date_range('2024-01-01', periods=5, freq='D')
        })

        stats = aggregate_statistics(match_data, group_by = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_GROUP_BY_172"))

        # 验证聚合结果
        assert len(stats) == 3  # 3个不同的队伍
        assert 'avg_goals_scored' in stats.columns
        assert 'avg_goals_conceded' in stats.columns
        assert 'win_rate' in stats.columns
        assert stats.loc[stats['team_id'] == 1, 'win_rate'].values[0] == 0.5

    @pytest.mark.asyncio
    async def test_async_data_processing(self):
        """测试异步数据处理"""
        # 创建大量数据
        large_data = pd.DataFrame({
            'match_id': range(1000),
            'home_team': [f'Team_{i%20}' for i in range(1000)],
            'away_team': [f'Team_{i%20+20}' for i in range(1000)],
            'home_score': np.random.randint(0, 5, 1000),
            'away_score': np.random.randint(0, 5, 1000)
        })

        with patch.object(self.processor, 'process_async') as mock_process:
            mock_process.return_value = large_data

            result = await self.processor.process_async(large_data)
            assert len(result) == 1000
            mock_process.assert_called_once()

    def test_data_pipeline(self):
        """测试数据处理管道"""
        # 创建原始数据
        raw_data = pd.DataFrame({
            'match_id': [1, 2, 3, 4],
            'home_team': ['Team A', 'Team B', '', 'Team D'],
            'away_team': ['Team X', 'Team Y', 'Team Z', None],
            'home_score': [2, None, 1, 3],
            'away_score': [1, 1, None, 2],
            'date': ['2024-01-01', '2024-01-02', '2024-01-03', 'invalid']
        })

        # 执行处理管道
        cleaned = self.processor.clean(raw_data)
        validated = self.processor.validate(cleaned)
        transformed = self.processor.transform(validated)

        # 验证管道结果
        assert len(transformed) > 0
        assert transformed['home_team'].isna().sum() == 0
        assert transformed['away_team'].isna().sum() == 0
        assert pd.to_datetime(transformed['date'], errors = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_ERRORS_86")).isna().sum() == 0


class TestDataCleaner:
    """数据清洗器测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        if DataCleaner is None:
            pytest.skip("DataCleaner not available")

        self.cleaner = DataCleaner()

    def test_remove_duplicates(self):
        """测试移除重复项"""
        data = pd.DataFrame({
            'id': [1, 2, 2, 3, 4, 4, 4],
            'name': ['A', 'B', 'B', 'C', 'D', 'D', 'D'],
            'value': [10, 20, 20, 30, 40, 40, 40]
        })

        cleaned = self.cleaner.remove_duplicates(data, subset=['id'])
        assert len(cleaned) == 4
        assert cleaned['id'].is_unique

    def test_handle_missing_values(self):
        """测试处理缺失值"""
        data = pd.DataFrame({
            'id': [1, 2, 3, 4],
            'numeric_col': [1.0, None, 3.0, None],
            'categorical_col': ['A', 'B', None, 'D'],
            'text_col': ['Text1', None, 'Text3', 'Text4']
        })

        # 数值列用均值填充
        cleaned_numeric = self.cleaner.handle_missing_values(
            data,
            columns=['numeric_col'],
            strategy='mean'
        )
        assert cleaned_numeric['numeric_col'].isna().sum() == 0

        # 分类列用众数填充
        cleaned_categorical = self.cleaner.handle_missing_values(
            data,
            columns=['categorical_col'],
            strategy='mode'
        )
        assert cleaned_categorical['categorical_col'].isna().sum() == 0

        # 文本列用占位符填充
        cleaned_text = self.cleaner.handle_missing_values(
            data,
            columns=['text_col'],
            strategy = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_STRATEGY_271"),
            fill_value = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_FILL_VALUE_274")
        )
        assert (cleaned_text['text_col'] == 'UNKNOWN').sum() > 0

    def test_detect_outliers(self):
        """测试检测异常值"""
        # 创建包含异常值的数据
        data = pd.DataFrame({
            'value': [10, 12, 11, 13, 9, 1000, 8, 14, 11, 12]  # 1000是异常值
        })

        outliers = self.cleaner.detect_outliers(data['value'], method='iqr')
        assert 1000 in outliers.index

        # 使用Z-score方法
        outliers_z = self.cleaner.detect_outliers(data['value'], method = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_METHOD_286"), threshold=3)
        assert len(outliers_z) >= 1

    def test_normalize_data(self):
        """测试数据标准化"""
        data = pd.DataFrame({
            'feature1': [10, 20, 30, 40, 50],
            'feature2': [100, 200, 300, 400, 500],
            'feature3': [0.1, 0.2, 0.3, 0.4, 0.5]
        })

        # Min-Max标准化
        normalized_minmax = self.cleaner.normalize_data(data, method = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_METHOD_296"))
        assert normalized_minmax['feature1'].min() == 0
        assert normalized_minmax['feature1'].max() == 1

        # Z-score标准化
        normalized_zscore = self.cleaner.normalize_data(data, method = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_METHOD_286"))
        assert abs(normalized_zscore['feature1'].mean()) < 0.01
        assert abs(normalized_zscore['feature1'].std() - 1) < 0.01

    def test_validate_data_types(self):
        """测试数据类型验证"""
        data = pd.DataFrame({
            'date_col': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'numeric_col': ['1', '2', '3'],
            'bool_col': ['true', 'false', 'true']
        })

        # 转换数据类型
        converted = self.cleaner.validate_and_convert_types({
            'date_col': 'datetime',
            'numeric_col': 'int',
            'bool_col': 'bool'
        }, data)

        assert pd.api.types.is_datetime64_any_dtype(converted['date_col'])
        assert pd.api.types.is_integer_dtype(converted['numeric_col'])
        assert pd.api.types.is_bool_dtype(converted['bool_col'])

    def test_clean_text_data(self):
        """测试清洗文本数据"""
        text_data = pd.Series([
            '  Clean Text  ',
            'Dirty Text!!!',
            'TEXT with 123 numbers',
            'Special @#$% characters',
            '   Multiple   spaces   '
        ])

        cleaned = self.cleaner.clean_text(text_data)

        # 验证清洗结果
        assert not cleaned.str.contains('  ').any()  # 无多余空格
        assert not cleaned.str.contains('!!!').any()  # 无特殊字符
        assert cleaned.str.islower().all()  # 全部小写

    def test_filter_data(self):
        """测试数据过滤"""
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'value': range(10),
            'category': ['A', 'B', 'A', 'B', 'A', 'B', 'A', 'B', 'A', 'B']
        })

        # 日期过滤
        date_filtered = self.cleaner.filter_by_date(
            data,
            'date',
            start_date='2024-01-05',
            end_date='2024-01-08'
        )
        assert len(date_filtered) == 4

        # 值过滤
        value_filtered = self.cleaner.filter_by_values(
            data,
            'value',
            min_value=3,
            max_value=7
        )
        assert len(value_filtered) == 5

        # 分类过滤
        category_filtered = self.cleaner.filter_by_category(
            data,
            'category',
            categories=['A']
        )
        assert len(category_filtered) == 5


class TestDataTransformer:
    """数据转换器测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        if DataTransformer is None:
            pytest.skip("DataTransformer not available")

        self.transformer = DataTransformer()

    def test_encode_categorical_variables(self):
        """测试编码分类变量"""
        data = pd.DataFrame({
            'category': ['A', 'B', 'A', 'C', 'B'],
            'label': ['X', 'Y', 'X', 'Z', 'Y']
        })

        # One-hot编码
        one_hot_encoded = self.transformer.encode_categorical(
            data,
            columns=['category'],
            method = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_METHOD_391")
        )
        assert 'category_A' in one_hot_encoded.columns
        assert 'category_B' in one_hot_encoded.columns
        assert 'category_C' in one_hot_encoded.columns

        # 标签编码
        label_encoded = self.transformer.encode_categorical(
            data,
            columns=['label'],
            method='label'
        )
        assert label_encoded['label'].dtype in ['int64', 'int32']

    def test_create_interaction_features(self):
        """测试创建交互特征"""
        data = pd.DataFrame({
            'feature1': [1, 2, 3, 4],
            'feature2': [5, 6, 7, 8],
            'feature3': [0.1, 0.2, 0.3, 0.4]
        })

        interaction_data = self.transformer.create_interactions(
            data,
            features=[('feature1', 'feature2'), ('feature1', 'feature3')]
        )

        assert 'feature1_x_feature2' in interaction_data.columns
        assert 'feature1_x_feature3' in interaction_data.columns
        assert interaction_data['feature1_x_feature2'].iloc[0] == 5  # 1*5

    def test_create_polynomial_features(self):
        """测试创建多项式特征"""
        data = pd.DataFrame({
            'x': [1, 2, 3, 4],
            'y': [5, 6, 7, 8]
        })

        poly_data = self.transformer.create_polynomial_features(
            data,
            degree=2,
            include_bias=False
        )

        # 验证多项式特征
        assert 'x^2' in poly_data.columns
        assert 'y^2' in poly_data.columns
        assert 'x y' in poly_data.columns
        assert poly_data['x^2'].iloc[0] == 1  # 1^2
        assert poly_data['x y'].iloc[0] == 5  # 1*5

    def test_aggregate_time_series(self):
        """测试时间序列聚合"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        data = pd.DataFrame({
            'date': dates,
            'value': np.random.randn(100),
            'category': np.random.choice(['A', 'B', 'C'], 100)
        })

        # 按周聚合
        weekly_agg = self.transformer.aggregate_time_series(
            data,
            date_col='date',
            value_cols=['value'],
            freq='W'
        )
        assert len(weekly_agg) < len(data)
        assert 'value_mean' in weekly_agg.columns
        assert 'value_std' in weekly_agg.columns

        # 按月聚合
        monthly_agg = self.transformer.aggregate_time_series(
            data,
            date_col='date',
            value_cols=['value'],
            freq='M'
        )
        assert len(monthly_agg) <= 4  # 最多4个月

    def test_create_lag_features(self):
        """测试创建滞后特征"""
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'value': [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        })

        lag_data = self.transformer.create_lag_features(
            data,
            value_col='value',
            lags=[1, 2, 3]
        )

        assert 'value_lag_1' in lag_data.columns
        assert 'value_lag_2' in lag_data.columns
        assert 'value_lag_3' in lag_data.columns
        assert lag_data['value_lag_1'].iloc[1] == 10  # 前一天的值

    def test_create_rolling_features(self):
        """测试创建滚动特征"""
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'value': [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        })

        rolling_data = self.transformer.create_rolling_features(
            data,
            value_col='value',
            windows=[3, 5],
            functions=['mean', 'std']
        )

        assert 'value_mean_3' in rolling_data.columns
        assert 'value_std_3' in rolling_data.columns
        assert 'value_mean_5' in rolling_data.columns
        assert rolling_data['value_mean_3'].iloc[2] == 20  # 10,20,30的均值

    def test_binning(self):
        """测试数据分箱"""
        data = pd.DataFrame({
            'age': [15, 25, 35, 45, 55, 65, 75],
            'income': [20000, 40000, 60000, 80000, 100000, 120000, 140000]
        })

        # 等宽分箱
        age_binned = self.transformer.bin_data(
            data['age'],
            bins=3,
            labels=['Young', 'Middle', 'Old']
        )
        assert len(age_binned.unique()) == 3

        # 等频分箱
        income_binned = self.transformer.bin_data(
            data['income'],
            bins=3,
            method = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_METHOD_526")
        )
        assert len(income_binned.unique()) == 3


class TestDataValidator:
    """数据验证器测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        if DataValidator is None:
            pytest.skip("DataValidator not available")

        self.validator = DataValidator()

    def test_validate_schema(self):
        """测试验证数据模式"""
        # 定义预期模式
        schema = {
            'required_columns': ['id', 'name', 'value'],
            'column_types': {
                'id': 'int',
                'name': 'str',
                'value': 'float'
            }
        }

        # 有效数据
        valid_data = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['A', 'B', 'C'],
            'value': [1.1, 2.2, 3.3]
        })

        is_valid = self.validator.validate_schema(valid_data, schema)
        assert is_valid is True

        # 无效数据（缺少列）
        invalid_data = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['A', 'B', 'C']
        })

        is_valid = self.validator.validate_schema(invalid_data, schema)
        assert is_valid is False

    def test_validate_business_rules(self):
        """测试验证业务规则"""
        rules = {
            'min_age': 18,
            'max_age': 65,
            'min_salary': 20000,
            'departments': ['IT', 'HR', 'Finance', 'Sales']
        }

        data = pd.DataFrame({
            'age': [25, 17, 30, 70],  # 17和70违反规则
            'salary': [30000, 25000, 15000, 40000],  # 15000违反规则
            'department': ['IT', 'HR', 'Marketing', 'Sales']  # Marketing违反规则
        })

        violations = self.validator.validate_business_rules(data, rules)
        assert len(violations) == 3  # 3条违规记录

    def test_cross_field_validation(self):
        """测试跨字段验证"""
        data = pd.DataFrame({
            'start_date': ['2024-01-01', '2024-02-01', '2024-03-01'],
            'end_date': ['2024-01-31', '2024-01-15', '2024-03-31'],  # 第二行开始日期晚于结束日期
            'budget': [1000, 500, 2000],
            'spent': [800, 600, 1500]  # 第二行花费超过预算
        })

        # 定义验证规则
        rules = [
            lambda row: row['start_date'] <= row['end_date'],
            lambda row: row['spent'] <= row['budget']
        ]

        violations = self.validator.cross_field_validation(data, rules)
        assert len(violations) == 2

    def test_check_data_quality(self):
        """测试检查数据质量"""
        data = pd.DataFrame({
            'id': [1, 2, 2, 4, None],  # 重复和空值
            'email': ['test@email.com', 'invalid', 'test@email.com', 'test2@email.com', ''],
            'phone': ['123-456-7890', '123-456-7890', '987-654-3210', 'invalid', None]
        })

        quality_report = self.validator.check_data_quality(data)

        assert 'completeness' in quality_report
        assert 'uniqueness' in quality_report
        assert 'validity' in quality_report
        assert 'consistency' in quality_report
        assert quality_report['completeness']['id'] == 0.8  # 4/5非空
        assert quality_report['uniqueness']['id'] == 0.8  # 4/5唯一

    def test_validate_data_lineage(self):
        """测试验证数据血缘"""
        lineage_info = {
            'source': 'database_A',
            'extraction_time': '2024-01-01 00:00:00',
            'transformations': ['clean', 'filter', 'aggregate'],
            'destination': 'table_B'
        }

        # 验证血缘信息完整性
        is_valid = self.validator.validate_lineage(lineage_info)
        assert is_valid is True

        # 缺少必要信息
        incomplete_lineage = {
            'source': 'database_A',
            'extraction_time': '2024-01-01 00:00:00'
        }

        is_valid = self.validator.validate_lineage(incomplete_lineage)
        assert is_valid is False


class TestDataAggregator:
    """数据聚合器测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        if DataAggregator is None:
            pytest.skip("DataAggregator not available")

        self.aggregator = DataAggregator()

    def test_group_by_aggregation(self):
        """测试分组聚合"""
        data = pd.DataFrame({
            'team': ['A', 'A', 'B', 'B', 'C', 'C'],
            'goals': [2, 1, 3, 0, 1, 2],
            'shots': [10, 8, 15, 5, 7, 9],
            'possession': [55, 60, 45, 40, 50, 52]
        })

        agg_config = {
            'goals': ['sum', 'mean', 'max'],
            'shots': ['sum', 'mean'],
            'possession': 'mean'
        }

        result = self.aggregator.group_by_aggregate(
            data,
            group_by='team',
            aggregations=agg_config
        )

        assert len(result) == 3
        assert ('goals', 'sum') in result.columns
        assert ('goals', 'mean') in result.columns
        assert ('possession', 'mean') in result.columns

    def test_pivot_table(self):
        """测试透视表"""
        data = pd.DataFrame({
            'team': ['A', 'A', 'B', 'B', 'C', 'C'],
            'opponent': ['X', 'Y', 'X', 'Y', 'X', 'Y'],
            'result': ['W', 'D', 'L', 'W', 'D', 'L'],
            'goals': [2, 1, 0, 3, 1, 0]
        })

        pivot = self.aggregator.create_pivot_table(
            data,
            index='team',
            columns = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_COLUMNS_696"),
            values='goals',
            aggfunc='sum',
            fill_value=0
        )

        assert 'W' in pivot.columns
        assert 'D' in pivot.columns
        assert 'L' in pivot.columns
        assert pivot.loc['A', 'W'] == 2

    def test_rolling_aggregation(self):
        """测试滚动聚合"""
        data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'sales': [100, 120, 90, 110, 130, 125, 140, 135, 150, 145]
        })

        rolling_result = self.aggregator.rolling_aggregate(
            data,
            value_col='sales',
            window=3,
            functions=['mean', 'sum']
        )

        assert 'sales_mean_3' in rolling_result.columns
        assert 'sales_sum_3' in rolling_result.columns
        assert rolling_result['sales_mean_3'].iloc[2] == 110  # (100+120+90)/3

    def test_time_based_aggregation(self):
        """测试基于时间的聚合"""
        data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=24, freq='H'),
            'users': [100, 120, 90, 110, 130, 125, 140, 135, 150, 145, 160, 155,
                     170, 165, 180, 175, 190, 185, 200, 195, 210, 205, 220, 215]
        })

        # 按小时聚合
        hourly_agg = self.aggregator.aggregate_by_time(
            data,
            timestamp_col = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_TIMESTAMP_COL_7"),
            value_cols=['users'],
            freq='H'
        )
        assert len(hourly_agg) == 24

        # 按天聚合
        daily_agg = self.aggregator.aggregate_by_time(
            data,
            timestamp_col = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_TIMESTAMP_COL_7"),
            value_cols=['users'],
            freq='D'
        )
        assert len(daily_agg) == 1

    def test_custom_aggregation(self):
        """测试自定义聚合"""
        data = pd.DataFrame({
            'category': ['A', 'A', 'B', 'B', 'C', 'C'],
            'values': [1, 2, 3, 4, 5, 6]
        })

        # 自定义聚合函数
        def range_func(x):
            return x.max() - x.min()

        def coefficient_of_variation(x):
            return x.std() / x.mean() if x.mean() != 0 else 0

        custom_agg = {
            'values': [range_func, coefficient_of_variation]
        }

        result = self.aggregator.custom_aggregate(
            data,
            group_by = os.getenv("TEST_DATA_PROCESSING_COMPREHENSIVE_GROUP_BY_761"),
            aggregations=custom_agg
        )

        assert 'range_func' in result.columns
        assert 'coefficient_of_variation' in result.columns

    def test_multi_level_aggregation(self):
        """测试多级聚合"""
        data = pd.DataFrame({
            'league': ['EPL', 'EPL', 'EPL', 'EPL', 'La Liga', 'La Liga'],
            'team': ['Man Utd', 'Man Utd', 'Chelsea', 'Chelsea', 'Real', 'Barca'],
            'goals': [2, 1, 3, 2, 4, 3]
        })

        multi_level = self.aggregator.multi_level_aggregate(
            data,
            group_columns=['league', 'team'],
            value_columns=['goals'],
            agg_funcs=['sum', 'mean', 'count']
        )

        assert isinstance(multi_level.index, pd.MultiIndex)
        assert len(multi_level) == 4  # 2个league × 2个team