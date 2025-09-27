"""
Auto-generated tests for src.data.features.examples module
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any

from src.data.features.examples import (
    example_initialize_feature_store,
    example_write_team_features,
    example_write_odds_features,
    example_get_online_features,
    example_get_historical_features,
    example_create_training_dataset,
    example_feature_statistics,
    example_list_all_features,
    example_integration_with_ml_pipeline,
    run_complete_example,
)


class TestExampleInitializeFeatureStore:
    """测试特征仓库初始化示例"""

    @patch('src.data.features.examples.initialize_feature_store')
    def test_initialize_feature_store_basic(self, mock_init):
        """测试基本特征仓库初始化"""
        # 模拟返回值
        mock_store = MagicMock()
        mock_init.return_value = mock_store

        # 调用函数
        result = example_initialize_feature_store()

        # 验证结果
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

    @patch('src.data.features.examples.initialize_feature_store')
    def test_initialize_feature_store_with_exception(self, mock_init):
        """测试特征仓库初始化异常处理"""
        mock_init.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            example_initialize_feature_store()


class TestExampleWriteTeamFeatures:
    """测试写入球队特征示例"""

    @patch('src.data.features.examples.pd.DataFrame')
    def test_write_team_features_basic(self, mock_dataframe):
        """测试基本球队特征写入"""
        # 模拟依赖
        mock_store = MagicMock()
        mock_df = MagicMock()

        mock_dataframe.return_value = mock_df

        # 调用函数
        example_write_team_features(mock_store)

        # 验证调用
        mock_dataframe.assert_called_once()
        mock_store.write_features.assert_called_once_with(
            feature_view_name="team_recent_stats", df=mock_df
        )

    def test_write_team_features_data_structure(self):
        """测试球队特征数据结构"""
        mock_store = MagicMock()

        with patch('src.data.features.examples.pd.DataFrame') as mock_df_constructor:
            mock_df = MagicMock()
            mock_df_constructor.return_value = mock_df

            example_write_team_features(mock_store)

            # 验证数据结构
            call_args = mock_df_constructor.call_args[0][0]
            assert len(call_args) == 2  # 2条球队数据

            # 验证第一条数据
            first_team = call_args[0]
            assert first_team["team_id"] == 1
            assert first_team["recent_5_wins"] == 3
            assert first_team["recent_5_goals_for"] == 8
            assert first_team["team_value_millions"] == 150.5

            # 验证第二条数据
            second_team = call_args[1]
            assert second_team["team_id"] == 2
            assert second_team["recent_5_wins"] == 2
            assert second_team["away_goals_avg"] == 1.1


class TestExampleWriteOddsFeatures:
    """测试写入赔率特征示例"""

    @patch('src.data.features.examples.pd.DataFrame')
    def test_write_odds_features_basic(self, mock_dataframe):
        """测试基本赔率特征写入"""
        mock_store = MagicMock()
        mock_df = MagicMock()
        mock_dataframe.return_value = mock_df

        example_write_odds_features(mock_store)

        mock_dataframe.assert_called_once()
        mock_store.write_features.assert_called_once_with(
            feature_view_name="odds_features", df=mock_df
        )

    def test_write_odds_features_data_structure(self):
        """测试赔率特征数据结构"""
        mock_store = MagicMock()

        with patch('src.data.features.examples.pd.DataFrame') as mock_df_constructor:
            example_write_odds_features(mock_store)

            call_args = mock_df_constructor.call_args[0][0]
            assert len(call_args) == 2  # 2条赔率数据

            # 验证第一条赔率数据
            first_odds = call_args[0]
            assert first_odds["match_id"] == 1001
            assert first_odds["home_odds"] == 1.85
            assert first_odds["draw_odds"] == 3.40
            assert first_odds["away_odds"] == 4.20
            assert first_odds["home_implied_prob"] == 0.541
            assert first_odds["bookmaker_margin"] == 0.073


class TestExampleGetOnlineFeatures:
    """测试获取在线特征示例"""

    def test_get_online_features_basic(self):
        """测试基本在线特征获取"""
        mock_store = MagicMock()
        mock_entity_df = pd.DataFrame([{"match_id": 1001}, {"match_id": 1002}])
        mock_features_df = pd.DataFrame({"feature1": [1, 2], "feature2": [3, 4]})

        with patch('src.data.features.examples.pd.DataFrame', return_value=mock_entity_df):
            mock_store.get_online_features.return_value = mock_features_df

            result = example_get_online_features(mock_store)

            # 验证结果
            assert result.equals(mock_features_df)
            mock_store.get_online_features.assert_called_once_with(
                feature_service_name="real_time_prediction_v1", entity_df=mock_entity_df
            )

    def test_get_online_features_entity_data(self):
        """测试在线特征实体数据构建"""
        mock_store = MagicMock()

        with patch('src.data.features.examples.pd.DataFrame') as mock_df_constructor:
            mock_entity_df = pd.DataFrame([{"match_id": 1001}, {"match_id": 1002}])
            mock_df_constructor.return_value = mock_entity_df

            mock_store.get_online_features.return_value = mock_entity_df

            example_get_online_features(mock_store)

            # 验证实体数据构建
            call_args = mock_df_constructor.call_args[0][0]
            expected_entities = [{"match_id": 1001}, {"match_id": 1002}]
            assert call_args == expected_entities


class TestExampleGetHistoricalFeatures:
    """测试获取历史特征示例"""

    def test_get_historical_features_basic(self):
        """测试基本历史特征获取"""
        mock_store = MagicMock()
        mock_training_df = pd.DataFrame({"match_id": [2000, 2001], "feature1": [1, 2]})

        with patch('src.data.features.examples.pd.DataFrame') as mock_df_constructor:
            mock_entity_df = pd.DataFrame([{"match_id": 2000}, {"match_id": 2001}])
            mock_df_constructor.return_value = mock_entity_df

            mock_store.get_historical_features.return_value = mock_training_df

            result = example_get_historical_features(mock_store)

            assert result.equals(mock_training_df)
            mock_store.get_historical_features.assert_called_once_with(
                feature_service_name="match_prediction_v1",
                entity_df=mock_entity_df,
                full_feature_names=True,
            )

    def test_get_historical_features_entity_generation(self):
        """测试历史特征实体生成"""
        mock_store = MagicMock()

        with patch('src.data.features.examples.pd.DataFrame') as mock_df_constructor:
            mock_entity_df = pd.DataFrame([{"match_id": 2000}, {"match_id": 2001}])
            mock_df_constructor.return_value = mock_entity_df

            mock_store.get_historical_features.return_value = mock_entity_df

            example_get_historical_features(mock_store)

            # 验证实体生成逻辑
            call_args = mock_df_constructor.call_args[0][0]
            assert len(call_args) == 10  # 10场历史比赛

            # 验证时间序列
            base_date = datetime(2025, 8, 1)
            for i, entity in enumerate(call_args):
                assert entity["match_id"] == 2000 + i
                expected_time = base_date + timedelta(days=i * 3)
                assert entity["event_timestamp"] == expected_time


class TestExampleCreateTrainingDataset:
    """测试创建训练数据集示例"""

    def test_create_training_dataset_basic(self):
        """测试基本训练数据集创建"""
        mock_store = MagicMock()
        mock_training_df = pd.DataFrame({"target": [0, 1], "feature1": [1, 2]})
        mock_store.create_training_dataset.return_value = mock_training_df

        result = example_create_training_dataset(mock_store)

        assert result.equals(mock_training_df)

        # 验证调用参数
        start_date = datetime(2025, 7, 1)
        end_date = datetime(2025, 9, 1)
        mock_store.create_training_dataset.assert_called_once_with(
            start_date=start_date, end_date=end_date
        )


class TestExampleFeatureStatistics:
    """测试特征统计示例"""

    def test_feature_statistics_basic(self):
        """测试基本特征统计"""
        mock_store = MagicMock()

        # 模拟统计数据
        mock_stats = {
            "num_features": 15,
            "entities": ["match", "team"],
            "ttl_days": 7,
            "tags": {"category": "match_features"}
        }
        mock_store.get_feature_statistics.return_value = mock_stats

        example_feature_statistics(mock_store)

        # 验证调用
        expected_views = ["team_recent_stats", "odds_features", "match_features"]
        calls = mock_store.get_feature_statistics.call_args_list
        assert len(calls) == len(expected_views)

        for i, view_name in enumerate(expected_views):
            assert calls[i][0][0] == view_name

    def test_feature_statistics_with_exception(self):
        """测试特征统计异常处理"""
        mock_store = MagicMock()
        mock_store.get_feature_statistics.side_effect = Exception("Stats not available")

        # 应该不抛出异常，而是记录警告
        example_feature_statistics(mock_store)  # 应该正常完成


class TestExampleListAllFeatures:
    """测试列出所有特征示例"""

    def test_list_all_features_with_data(self):
        """测试有数据时的特征列表"""
        mock_store = MagicMock()

        # 模拟特征列表
        mock_features = [
            {"feature_view": "team_recent_stats", "feature_name": "recent_5_wins", "feature_type": "integer"},
            {"feature_view": "team_recent_stats", "feature_name": "recent_5_goals", "feature_type": "float"},
            {"feature_view": "odds_features", "feature_name": "home_odds", "feature_type": "float"},
        ]
        mock_store.list_features.return_value = mock_features

        example_list_all_features(mock_store)

        mock_store.list_features.assert_called_once()

    def test_list_all_features_empty(self):
        """测试空特征列表"""
        mock_store = MagicMock()
        mock_store.list_features.return_value = []

        example_list_all_features(mock_store)  # 应该正常完成


class TestExampleIntegrationWithMLPipeline:
    """测试ML流水线集成示例"""

    @patch('src.data.features.examples.get_feature_store')
    @patch('src.data.features.examples.pd.DataFrame')
    def test_integration_with_ml_pipeline_basic(self, mock_dataframe, mock_get_store):
        """测试基本ML流水线集成"""
        # 模拟依赖
        mock_store = MagicMock()
        mock_get_store.return_value = mock_store

        mock_training_df = pd.DataFrame({"target": [0, 1]})
        mock_entity_df = pd.DataFrame([{"match_id": 3001}, {"match_id": 3002}])
        mock_features_df = pd.DataFrame({"feature1": [1, 2]})

        mock_store.create_training_dataset.return_value = mock_training_df
        mock_dataframe.return_value = mock_entity_df
        mock_store.get_online_features.return_value = mock_features_df

        result = example_integration_with_ml_pipeline()

        # 验证结果
        assert result["integration_status"] == "success"
        assert result["training_result"]["model_trained"] is True
        assert result["training_result"]["training_samples"] == 2
        assert result["prediction_result"]["predictions_made"] == 2

    @patch('src.data.features.examples.get_feature_store')
    def test_integration_with_ml_pipeline_exceptions(self, mock_get_store):
        """测试ML流水线集成异常处理"""
        mock_store = MagicMock()
        mock_get_store.return_value = mock_store
        mock_store.create_training_dataset.side_effect = Exception("Training failed")

        result = example_integration_with_ml_pipeline()

        # 集成状态仍应为成功，但训练结果会反映异常
        assert result["integration_status"] == "success"


class TestRunCompleteExample:
    """测试完整示例运行"""

    @pytest.mark.asyncio
    @patch('src.data.features.examples.example_initialize_feature_store')
    @patch('src.data.features.examples.example_write_team_features')
    @patch('src.data.features.examples.example_write_odds_features')
    @patch('src.data.features.examples.example_get_online_features')
    @patch('src.data.features.examples.example_get_historical_features')
    @patch('src.data.features.examples.example_create_training_dataset')
    @patch('src.data.features.examples.example_feature_statistics')
    @patch('src.data.features.examples.example_list_all_features')
    async def test_run_complete_example_success(
        self,
        mock_list_features,
        mock_stats,
        mock_create_dataset,
        mock_get_historical,
        mock_get_online,
        mock_write_odds,
        mock_write_team,
        mock_write_features,
        mock_init
    ):
        """测试完整示例成功运行"""
        # 模拟依赖
        mock_store = MagicMock()
        mock_init.return_value = mock_store

        # 运行示例
        await run_complete_example()

        # 验证所有步骤都被调用
        mock_init.assert_called_once()
        mock_write_team.assert_called_once_with(mock_store)
        mock_write_odds.assert_called_once_with(mock_store)
        mock_get_online.assert_called_once_with(mock_store)
        mock_get_historical.assert_called_once_with(mock_store)
        mock_create_dataset.assert_called_once_with(mock_store)
        mock_stats.assert_called_once_with(mock_store)
        mock_list_features.assert_called_once_with(mock_store)
        mock_store.close.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.data.features.examples.example_initialize_feature_store')
    async def test_run_complete_example_with_exception(self, mock_init):
        """测试完整示例异常处理"""
        mock_init.side_effect = Exception("Initialization failed")

        # 应该捕获异常并记录日志
        await run_complete_example()  # 不应该抛出异常


@pytest.fixture
def mock_feature_store():
    """模拟特征仓库fixture"""
    store = MagicMock()
    return store


@pytest.fixture
def sample_team_data():
    """示例球队数据fixture"""
    return [
        {
            "team_id": 1,
            "event_timestamp": datetime(2025, 9, 10),
            "recent_5_wins": 3,
            "recent_5_draws": 1,
            "recent_5_losses": 1,
            "recent_5_goals_for": 8,
            "recent_5_goals_against": 4,
            "recent_5_goal_difference": 4,
            "recent_5_points": 10,
            "recent_5_avg_rating": 7.2,
        }
    ]


@pytest.fixture
def sample_odds_data():
    """示例赔率数据fixture"""
    return [
        {
            "match_id": 1001,
            "event_timestamp": datetime(2025, 9, 10, 14, 0, 0),
            "home_odds": 1.85,
            "draw_odds": 3.40,
            "away_odds": 4.20,
            "home_implied_prob": 0.541,
            "bookmaker_margin": 0.073,
        }
    ]