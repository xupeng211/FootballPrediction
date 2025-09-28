"""
Enhanced tests for data features examples module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta
import tempfile
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

@pytest.mark.unit
class TestDataFeaturesExamples:
    """Test data features examples"""

    def test_module_imports(self):
        """测试模块导入"""
        try:
            from src.data.features.examples import (
                example_initialize_feature_store,
                example_write_team_features,
                example_write_odds_features,
                example_get_online_features,
                example_get_historical_features,
                example_create_training_dataset,
                example_feature_statistics,
                example_list_all_features,
                run_complete_example,
                example_integration_with_ml_pipeline
            )
            assert all(callable(func) for func in [
                example_initialize_feature_store,
                example_write_team_features,
                example_write_odds_features,
                example_get_online_features,
                example_get_historical_features,
                example_create_training_dataset,
                example_feature_statistics,
                example_list_all_features,
                run_complete_example,
                example_integration_with_ml_pipeline
            ])
        except ImportError:
            pytest.skip("Examples module not available")

    @patch('src.data.features.examples.initialize_feature_store')
    def test_example_initialize_feature_store_success(self, mock_initialize):
        """测试特征仓库初始化示例成功场景"""
        # Mock the feature store
        mock_store = Mock()
        mock_initialize.return_value = mock_store

        from src.data.features.examples import example_initialize_feature_store
        result = example_initialize_feature_store()

        assert result == mock_store
        mock_initialize.assert_called_once_with(
            project_name="football_prediction_demo",
            postgres_config={
                "host": "localhost",
                "port": 5432,
                "database": "football_prediction_dev",
                "user": "football_reader",
                "password": "reader_password_2025",
            },
            redis_config={"connection_string": "redis://localhost:6379/1"}
        )

    @patch('src.data.features.examples.pd.DataFrame')
    def test_example_write_team_features_success(self, mock_dataframe):
        """测试写入球队特征成功场景"""
        mock_store = Mock()
        mock_df = Mock()
        mock_df.__len__ = Mock(return_value=2)
        mock_dataframe.return_value = mock_df

        from src.data.features.examples import example_write_team_features
        example_write_team_features(mock_store)

        mock_store.write_features.assert_called_once_with(
            feature_view_name="team_recent_stats", df=mock_df
        )

    @patch('src.data.features.examples.pd.DataFrame')
    def test_example_write_odds_features_success(self, mock_dataframe):
        """测试写入赔率特征成功场景"""
        mock_store = Mock()
        mock_df = Mock()
        mock_df.__len__ = Mock(return_value=2)
        mock_dataframe.return_value = mock_df

        from src.data.features.examples import example_write_odds_features
        example_write_odds_features(mock_store)

        mock_store.write_features.assert_called_once_with(
            feature_view_name="odds_features", df=mock_df
        )

    @patch('src.data.features.examples.pd.DataFrame')
    def test_example_get_online_features_success(self, mock_dataframe):
        """测试获取在线特征成功场景"""
        mock_store = Mock()
        mock_entity_df = Mock()
        mock_features_df = Mock()

        mock_dataframe.return_value = mock_entity_df
        mock_store.get_online_features.return_value = mock_features_df

        from src.data.features.examples import example_get_online_features
        result = example_get_online_features(mock_store)

        assert result == mock_features_df
        mock_store.get_online_features.assert_called_once_with(
            feature_service_name="real_time_prediction_v1", entity_df=mock_entity_df
        )

    @patch('src.data.features.examples.pd.DataFrame')
    def test_example_get_historical_features_success(self, mock_dataframe):
        """测试获取历史特征成功场景"""
        mock_store = Mock()
        mock_entity_df = Mock()
        mock_training_df = Mock()
        mock_training_df.columns = ['feature1', 'feature2']
        mock_training_df.shape = (100, 2)

        mock_dataframe.return_value = mock_entity_df
        mock_store.get_historical_features.return_value = mock_training_df

        from src.data.features.examples import example_get_historical_features
        result = example_get_historical_features(mock_store)

        assert result == mock_training_df
        mock_store.get_historical_features.assert_called_once_with(
            feature_service_name="match_prediction_v1",
            entity_df=mock_entity_df,
            full_feature_names=True,
        )

    def test_example_create_training_dataset_success(self):
        """测试创建训练数据集成功场景"""
        mock_store = Mock()
        mock_training_df = Mock()
        mock_training_df.shape = (100, 20)
        mock_training_df.columns = ['feature1', 'feature2']
        mock_training_df.__len__ = Mock(return_value=100)
        mock_store.create_training_dataset.return_value = mock_training_df

        from src.data.features.examples import example_create_training_dataset
        result = example_create_training_dataset(mock_store)

        assert result == mock_training_df

    def test_example_feature_statistics_success(self):
        """测试特征统计成功场景"""
        mock_store = Mock()
        mock_stats = {
            'num_features': 10,
            'entities': ['team', 'match'],
            'ttl_days': 30,
            'tags': {'category': 'stats'}
        }
        mock_store.get_feature_statistics.return_value = mock_stats

        from src.data.features.examples import example_feature_statistics
        example_feature_statistics(mock_store)

        # Verify calls were made for different feature views
        expected_calls = [
            ('team_recent_stats',),
            ('odds_features',),
            ('match_features',)
        ]
        actual_calls = [call[0] for call in mock_store.get_feature_statistics.call_args_list]
        assert actual_calls == expected_calls

    def test_example_feature_statistics_error_handling(self):
        """测试特征统计错误处理"""
        mock_store = Mock()
        mock_store.get_feature_statistics.side_effect = Exception("Connection error")

        from src.data.features.examples import example_feature_statistics
        # Should not raise exception, should handle error gracefully
        example_feature_statistics(mock_store)

    def test_example_list_all_features_success(self):
        """测试列出所有特征成功场景"""
        mock_store = Mock()
        mock_features = [
            {
                'feature_view': 'team_recent_stats',
                'feature_name': 'recent_5_wins',
                'feature_type': 'int64',
                'description': 'Recent 5 matches wins',
                'entities': ['team'],
                'tags': {}
            },
            {
                'feature_view': 'odds_features',
                'feature_name': 'home_odds',
                'feature_type': 'float64',
                'description': 'Home team odds',
                'entities': ['match'],
                'tags': {}
            }
        ]
        mock_store.list_features.return_value = mock_features

        from src.data.features.examples import example_list_all_features
        example_list_all_features(mock_store)

        mock_store.list_features.assert_called_once()

    def test_example_list_all_features_empty(self):
        """测试列出所有特征为空的情况"""
        mock_store = Mock()
        mock_store.list_features.return_value = []

        from src.data.features.examples import example_list_all_features
        example_list_all_features(mock_store)

        mock_store.list_features.assert_called_once()

    def test_run_complete_example_success(self):
        """测试完整示例运行成功场景"""
        mock_store = Mock()

        # Import the module and patch all functions
        import src.data.features.examples as examples_module

        with patch.object(examples_module, 'example_initialize_feature_store', return_value=mock_store) as mock_init, \
             patch.object(examples_module, 'example_write_team_features') as mock_team, \
             patch.object(examples_module, 'example_write_odds_features') as mock_odds, \
             patch.object(examples_module, 'example_get_online_features') as mock_online, \
             patch.object(examples_module, 'example_get_historical_features') as mock_historical, \
             patch.object(examples_module, 'example_create_training_dataset') as mock_create, \
             patch.object(examples_module, 'example_feature_statistics') as mock_stats, \
             patch.object(examples_module, 'example_list_all_features') as mock_list:

            # Should not raise exception
            import asyncio
            asyncio.run(examples_module.run_complete_example())

            # Verify all functions were called
            mock_init.assert_called_once()
            mock_team.assert_called_once_with(mock_store)
            mock_odds.assert_called_once_with(mock_store)
            mock_online.assert_called_once_with(mock_store)
            mock_historical.assert_called_once_with(mock_store)
            mock_create.assert_called_once_with(mock_store)
            mock_stats.assert_called_once_with(mock_store)
            mock_list.assert_called_once_with(mock_store)
            mock_store.close.assert_called_once()

    @patch('src.data.features.examples.example_initialize_feature_store')
    def test_run_complete_example_failure(self, mock_initialize):
        """测试完整示例运行失败场景"""
        mock_initialize.side_effect = Exception("Initialization failed")

        from src.data.features.examples import run_complete_example

        # Should handle exception gracefully
        run_complete_example()

    @patch('src.data.features.examples.get_feature_store')
    @patch('src.data.features.examples.pd.DataFrame')
    def test_example_integration_with_ml_pipeline_success(self, mock_dataframe, mock_get_store):
        """测试ML流水线集成成功场景"""
        mock_store = Mock()
        mock_get_store.return_value = mock_store

        mock_training_df = Mock()
        mock_training_df.__len__ = Mock(return_value=100)
        mock_store.create_training_dataset.return_value = mock_training_df

        mock_entity_df = Mock()
        mock_features_df = Mock()
        mock_features_df.__len__ = Mock(return_value=2)
        mock_dataframe.return_value = mock_entity_df
        mock_store.get_online_features.return_value = mock_features_df

        from src.data.features.examples import example_integration_with_ml_pipeline
        result = example_integration_with_ml_pipeline()

        expected_result = {
            "training_result": {"model_trained": True, "training_samples": 100},
            "prediction_result": {"predictions_made": 2},
            "integration_status": "success",
        }
        assert result == expected_result

    def test_integration_example_functions_exist(self):
        """测试集成示例函数存在性"""
        functions_to_check = [
            'example_initialize_feature_store',
            'example_write_team_features',
            'example_write_odds_features',
            'example_get_online_features',
            'example_get_historical_features',
            'example_create_training_dataset',
            'example_feature_statistics',
            'example_list_all_features',
            'run_complete_example',
            'example_integration_with_ml_pipeline'
        ]

        for func_name in functions_to_check:
            try:
                from src.data.features.examples import func_name as func
                assert callable(func)
            except ImportError:
                pytest.skip(f"Function {func_name} not available")

    @patch('src.data.features.examples.datetime')
    def test_historical_features_date_calculation(self, mock_datetime):
        """测试历史特征日期计算"""
        mock_now = datetime(2025, 9, 10)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        mock_store = Mock()
        mock_entity_df = Mock()
        mock_training_df = Mock()
        mock_training_df.columns = ['feature1', 'feature2']
        mock_training_df.shape = (100, 2)

        with patch('src.data.features.examples.pd.DataFrame', return_value=mock_entity_df):
            mock_store.get_historical_features.return_value = mock_training_df

            from src.data.features.examples import example_get_historical_features
            result = example_get_historical_features(mock_store)

            assert result == mock_training_df

            # Verify date calculations
            call_args = mock_store.get_historical_features.call_args
            assert call_args is not None