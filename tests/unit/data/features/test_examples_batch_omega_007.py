"""
Examples Batch-Ω-007 测试套件

专门为 examples.py 设计的测试，目标是将其覆盖率从 0% 提升至 ≥70%
覆盖所有特征仓库示例功能、数据创建、ML集成等
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any
import pandas as pd
import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

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
    example_integration_with_ml_pipeline,
)


class TestExamplesBatchOmega007:
    """Examples Batch-Ω-007 测试类"""

    @pytest.fixture
    def mock_feature_store(self):
        """创建模拟特征仓库"""
        mock_store = Mock()
        mock_store.write_features = Mock()
        mock_store.get_online_features = Mock(return_value=pd.DataFrame({
            'match_id': [1001, 1002],
            'feature1': [1.0, 2.0],
            'feature2': [3.0, 4.0]
        }))
        mock_store.get_historical_features = Mock(return_value=pd.DataFrame({
            'match_id': [2000, 2001],
            'historical_feature1': [10.0, 20.0],
            'historical_feature2': [30.0, 40.0]
        }))
        mock_store.create_training_dataset = Mock(return_value=pd.DataFrame({
            'training_feature1': [100.0, 200.0],
            'training_feature2': [300.0, 400.0],
            'target': [0, 1]
        }))
        mock_store.get_feature_statistics = Mock(return_value={
            'num_features': 15,
            'entities': ['match', 'team'],
            'ttl_days': 7,
            'tags': {'purpose': 'prediction'}
        })
        mock_store.list_features = Mock(return_value=[
            {'feature_view': 'team_recent_stats', 'feature_name': 'recent_5_wins', 'feature_type': 'int'},
            {'feature_view': 'odds_features', 'feature_name': 'home_odds', 'feature_type': 'float'},
            {'feature_view': 'match_features', 'feature_name': 'home_team_id', 'feature_type': 'int'}
        ])
        mock_store.close = Mock()
        return mock_store

    def test_example_initialize_feature_store_basic(self):
        """测试初始化特征仓库基本功能"""
        with patch('src.data.features.examples.initialize_feature_store') as mock_init:
            mock_store = Mock()
            mock_init.return_value = mock_store

            result = example_initialize_feature_store()

            assert result == mock_store
            mock_init.assert_called_once_with(
                project_name="football_prediction_demo",
                postgres_config={
                    "host": "localhost",
                    "port": 5432,
                    "database": "football_prediction_dev",
                    "user": "football_reader",
                    "password": "reader_password_2025",
                },
                redis_config={"connection_string": "redis://localhost:6379/1"},
            )

    def test_example_write_team_features_basic(self, mock_feature_store):
        """测试写入球队特征基本功能"""
        example_write_team_features(mock_feature_store)

        # 验证写入调用
        mock_feature_store.write_features.assert_called_once()
        call_args = mock_feature_store.write_features.call_args[1]

        assert call_args["feature_view_name"] == "team_recent_stats"
        assert isinstance(call_args["df"], pd.DataFrame)

        # 验证数据内容
        df = call_args["df"]
        assert len(df) == 2
        assert "team_id" in df.columns
        assert "recent_5_wins" in df.columns
        assert "event_timestamp" in df.columns

    def test_example_write_odds_features_basic(self, mock_feature_store):
        """测试写入赔率特征基本功能"""
        example_write_odds_features(mock_feature_store)

        # 验证写入调用
        mock_feature_store.write_features.assert_called_once()
        call_args = mock_feature_store.write_features.call_args[1]

        assert call_args["feature_view_name"] == "odds_features"
        assert isinstance(call_args["df"], pd.DataFrame)

        # 验证数据内容
        df = call_args["df"]
        assert len(df) == 2
        assert "match_id" in df.columns
        assert "home_odds" in df.columns
        assert "away_odds" in df.columns

    def test_example_get_online_features_basic(self, mock_feature_store):
        """测试获取在线特征基本功能"""
        result = example_get_online_features(mock_feature_store)

        # 验证返回结果
        assert isinstance(result, pd.DataFrame)

        # 验证调用
        mock_feature_store.get_online_features.assert_called_once()
        call_args = mock_feature_store.get_online_features.call_args[1]

        assert call_args["feature_service_name"] == "real_time_prediction_v1"
        assert isinstance(call_args["entity_df"], pd.DataFrame)

    def test_example_get_historical_features_basic(self, mock_feature_store):
        """测试获取历史特征基本功能"""
        result = example_get_historical_features(mock_feature_store)

        # 验证返回结果
        assert isinstance(result, pd.DataFrame)

        # 验证调用
        mock_feature_store.get_historical_features.assert_called_once()
        call_args = mock_feature_store.get_historical_features.call_args[1]

        assert call_args["feature_service_name"] == "match_prediction_v1"
        assert call_args["full_feature_names"] is True
        assert isinstance(call_args["entity_df"], pd.DataFrame)

    def test_example_create_training_dataset_basic(self, mock_feature_store):
        """测试创建训练数据集基本功能"""
        result = example_create_training_dataset(mock_feature_store)

        # 验证返回结果
        assert isinstance(result, pd.DataFrame)

        # 验证调用
        mock_feature_store.create_training_dataset.assert_called_once()
        call_args = mock_feature_store.create_training_dataset.call_args[1]

        assert call_args["start_date"] == datetime(2025, 7, 1)
        assert call_args["end_date"] == datetime(2025, 9, 1)

    def test_example_feature_statistics_basic(self, mock_feature_store):
        """测试特征统计基本功能"""
        example_feature_statistics(mock_feature_store)

        # 验证调用
        assert mock_feature_store.get_feature_statistics.call_count == 3

        # 验证调用的特征视图名称
        call_args_list = mock_feature_store.get_feature_statistics.call_args_list
        feature_views = [call[0][0] for call in call_args_list]
        expected_views = ["team_recent_stats", "odds_features", "match_features"]
        assert feature_views == expected_views

    def test_example_feature_statistics_with_error(self, mock_feature_store):
        """测试特征统计错误处理"""
        # 设置某些调用抛出异常
        mock_feature_store.get_feature_statistics.side_effect = [
            {"num_features": 10, "entities": ["match"]},  # 成功
            Exception("Connection failed"),  # 失败
            {"num_features": 15, "entities": ["team"]},  # 成功
        ]

        # 应该不会抛出异常
        example_feature_statistics(mock_feature_store)

        # 验证仍然调用了所有特征视图
        assert mock_feature_store.get_feature_statistics.call_count == 3

    def test_example_list_all_features_basic(self, mock_feature_store):
        """测试列出所有特征基本功能"""
        example_list_all_features(mock_feature_store)

        # 验证调用
        mock_feature_store.list_features.assert_called_once()

    def test_example_list_all_features_empty(self, mock_feature_store):
        """测试列出所有特征空结果"""
        mock_feature_store.list_features.return_value = []

        example_list_all_features(mock_feature_store)

        # 应该处理空列表情况而不出错
        mock_feature_store.list_features.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_complete_example_success(self, mock_feature_store):
        """测试运行完整示例成功场景"""
        with patch('src.data.features.examples.example_initialize_feature_store') as mock_init, \
             patch('src.data.features.examples.example_write_team_features') as mock_write_team, \
             patch('src.data.features.examples.example_write_odds_features') as mock_write_odds, \
             patch('src.data.features.examples.example_get_online_features') as mock_get_online, \
             patch('src.data.features.examples.example_get_historical_features') as mock_get_historical, \
             patch('src.data.features.examples.example_create_training_dataset') as mock_create_dataset, \
             patch('src.data.features.examples.example_feature_statistics') as mock_stats, \
             patch('src.data.features.examples.example_list_all_features') as mock_list:

            mock_init.return_value = mock_feature_store

            # 应该不抛出异常
            await run_complete_example()

            # 验证所有步骤都被调用
            mock_init.assert_called_once()
            mock_write_team.assert_called_once_with(mock_feature_store)
            mock_write_odds.assert_called_once_with(mock_feature_store)
            mock_get_online.assert_called_once_with(mock_feature_store)
            mock_get_historical.assert_called_once_with(mock_feature_store)
            mock_create_dataset.assert_called_once_with(mock_feature_store)
            mock_stats.assert_called_once_with(mock_feature_store)
            mock_list.assert_called_once_with(mock_feature_store)
            mock_feature_store.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_complete_example_with_exception(self):
        """测试运行完整示例异常处理"""
        with patch('src.data.features.examples.example_initialize_feature_store') as mock_init:
            mock_init.side_effect = Exception("Initialization failed")

            # 应该不抛出异常
            await run_complete_example()

            # 验证初始化被调用
            mock_init.assert_called_once()

    def test_example_integration_with_ml_pipeline_basic(self):
        """测试ML流水线集成基本功能"""
        with patch('src.data.features.examples.get_feature_store') as mock_get_store, \
             patch('src.data.features.examples.pd.DataFrame') as mock_dataframe:

            mock_store = Mock()
            mock_get_store.return_value = mock_store

            # 设置模拟返回值
            mock_store.create_training_dataset.return_value = pd.DataFrame({
                'feature1': [1, 2], 'target': [0, 1]
            })
            mock_store.get_online_features.return_value = pd.DataFrame({
                'online_feature1': [10, 20]
            })

            # 模拟DataFrame构造
            mock_df_instance = Mock()
            mock_dataframe.return_value = mock_df_instance

            result = example_integration_with_ml_pipeline()

            # 验证结果结构
            assert isinstance(result, dict)
            assert "training_result" in result
            assert "prediction_result" in result
            assert "integration_status" in result
            assert result["integration_status"] == "success"

    
    
    def test_historical_features_entity_creation(self):
        """测试历史特征实体创建"""
        mock_store = Mock()

        # Mock get_historical_features to return a DataFrame
        mock_store.get_historical_features.return_value = pd.DataFrame({
            'feature1': [1, 2], 'feature2': [3, 4], 'target': [0, 1]
        })

        with patch('src.data.features.examples.pd.DataFrame') as mock_dataframe:
            mock_df_instance = Mock()
            mock_dataframe.return_value = mock_df_instance

            example_get_historical_features(mock_store)

            # 验证DataFrame被创建用于实体数据
            mock_dataframe.assert_called()

            # 检查调用参数
            call_args_list = mock_dataframe.call_args_list
            # 应该有一次调用用于创建实体DataFrame
            assert len(call_args_list) >= 1

    def test_configuration_parameters(self):
        """测试配置参数正确性"""
        with patch('src.data.features.examples.initialize_feature_store') as mock_init:
            mock_store = Mock()
            mock_init.return_value = mock_store

            example_initialize_feature_store()

            # 验证配置参数
            call_args = mock_init.call_args[1]

            # 验证PostgreSQL配置
            postgres_config = call_args["postgres_config"]
            assert postgres_config["host"] == "localhost"
            assert postgres_config["port"] == 5432
            assert postgres_config["database"] == "football_prediction_dev"
            assert postgres_config["user"] == "football_reader"

            # 验证Redis配置
            redis_config = call_args["redis_config"]
            assert redis_config["connection_string"] == "redis://localhost:6379/1"

    def test_feature_data_structure_validation(self):
        """测试特征数据结构验证"""
        mock_store = Mock()

        example_write_team_features(mock_store)

        # 获取传递给write_features的DataFrame
        call_args = mock_store.write_features.call_args[1]
        df = call_args["df"]

        # 验证DataFrame包含预期的列
        expected_columns = [
            "team_id", "event_timestamp", "recent_5_wins", "recent_5_draws",
            "recent_5_losses", "recent_5_goals_for", "recent_5_goals_against",
            "recent_5_goal_difference", "recent_5_points", "recent_5_avg_rating"
        ]

        for col in expected_columns:
            assert col in df.columns

    def test_odds_data_structure_validation(self):
        """测试赔率数据结构验证"""
        mock_store = Mock()

        example_write_odds_features(mock_store)

        # 获取传递给write_features的DataFrame
        call_args = mock_store.write_features.call_args[1]
        df = call_args["df"]

        # 验证DataFrame包含预期的列
        expected_columns = [
            "match_id", "event_timestamp", "home_odds", "draw_odds", "away_odds",
            "home_implied_prob", "draw_implied_prob", "away_implied_prob"
        ]

        for col in expected_columns:
            assert col in df.columns

    def test_online_features_entity_structure(self):
        """测试在线特征实体结构"""
        mock_store = Mock()

        with patch('src.data.features.examples.pd.DataFrame') as mock_dataframe:
            mock_df_instance = Mock()
            mock_dataframe.return_value = mock_df_instance

            example_get_online_features(mock_store)

            # 验证实体数据结构
            call_args = mock_dataframe.call_args[0][0]
            entities = call_args

            assert isinstance(entities, list)
            assert len(entities) == 2
            assert all(isinstance(entity, dict) for entity in entities)
            assert all("match_id" in entity for entity in entities)

    def test_error_handling_integration(self):
        """测试错误处理集成"""
        mock_store = Mock()
        mock_store.get_feature_statistics.side_effect = Exception("Test error")

        # 应该不抛出异常
        example_feature_statistics(mock_store)

        # 验证方法仍然被调用
        assert mock_store.get_feature_statistics.called

    def test_async_function_structure(self):
        """测试异步函数结构"""
        # 验证函数是异步的
        import inspect

        # run_complete_example应该是异步函数
        assert inspect.iscoroutinefunction(run_complete_example)

    def test_main_execution_path(self):
        """测试主执行路径"""
        with patch('src.data.features.examples.asyncio.run') as mock_run, \
             patch('src.data.features.examples.example_integration_with_ml_pipeline') as mock_integration:

            # 测试主执行块
            mock_integration.return_value = {"test": "result"}

            # 模拟导入和执行
            with patch.dict('__main__.__dict__', {'__name__': '__main__'}):
                try:
                    exec("""
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
from src.data.features.examples import run_complete_example, example_integration_with_ml_pipeline

# 设置日志级别
import logging
logging.basicConfig(level=logging.INFO)

# 运行完整示例
asyncio.run(run_complete_example())

# 运行ML集成示例
ml_results = example_integration_with_ml_pipeline()
""")
                except Exception:
                    pass  # 预期会有异常，因为我们不能真正运行异步代码

            # 验证调用
            assert mock_run.called
            assert mock_integration.called