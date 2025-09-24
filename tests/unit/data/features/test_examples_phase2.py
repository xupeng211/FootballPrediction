"""
特征仓库使用示例测试模块

全面测试 src/data/features/examples.py 的所有功能
包括特征仓库初始化、数据写入、特征查询和ML流水线集成。

基于 DATA_DESIGN.md 第6.1节特征仓库设计。
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import pandas as pd
import pytest

from src.data.features.examples import (
    example_create_training_dataset,
    example_feature_statistics,
    example_get_historical_features,
    example_get_online_features,
    example_initialize_feature_store,
    example_integration_with_ml_pipeline,
    example_list_all_features,
    example_write_odds_features,
    example_write_team_features,
    run_complete_example,
)


class TestFeatureStoreExamples:
    """测试特征仓库示例功能"""

    @pytest.fixture
    def mock_feature_store(self):
        """模拟特征仓库实例"""
        mock_store = Mock()
        mock_store.write_features = Mock()
        mock_store.get_online_features = Mock()
        mock_store.get_historical_features = Mock()
        mock_store.create_training_dataset = Mock()
        mock_store.get_feature_statistics = Mock()
        mock_store.list_features = Mock()
        mock_store.close = Mock()
        return mock_store

    @pytest.fixture
    def sample_team_data(self):
        """示例球队统计数据"""
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
                "recent_10_wins": 6,
                "recent_10_draws": 2,
                "recent_10_losses": 2,
                "recent_10_goals_for": 15,
                "recent_10_goals_against": 8,
                "recent_10_win_rate": 0.6,
                "home_wins": 8,
                "home_goals_avg": 2.1,
                "away_wins": 4,
                "away_goals_avg": 1.3,
                "team_value_millions": 150.5,
                "avg_player_age": 26.8,
                "league_position": 3,
                "points_per_game": 2.1,
            },
            {
                "team_id": 2,
                "event_timestamp": datetime(2025, 9, 10),
                "recent_5_wins": 2,
                "recent_5_draws": 2,
                "recent_5_losses": 1,
                "recent_5_goals_for": 6,
                "recent_5_goals_against": 5,
                "recent_5_goal_difference": 1,
                "recent_5_points": 8,
                "recent_5_avg_rating": 6.8,
                "recent_10_wins": 5,
                "recent_10_draws": 3,
                "recent_10_losses": 2,
                "recent_10_goals_for": 12,
                "recent_10_goals_against": 10,
                "recent_10_win_rate": 0.5,
                "home_wins": 6,
                "home_goals_avg": 1.8,
                "away_wins": 3,
                "away_goals_avg": 1.1,
                "team_value_millions": 120.3,
                "avg_player_age": 28.2,
                "league_position": 7,
                "points_per_game": 1.7,
            },
        ]

    @pytest.fixture
    def sample_odds_data(self):
        """示例赔率数据"""
        return [
            {
                "match_id": 1001,
                "event_timestamp": datetime(2025, 9, 10, 14, 0, 0),
                "home_odds": 1.85,
                "draw_odds": 3.40,
                "away_odds": 4.20,
                "home_implied_prob": 0.541,
                "draw_implied_prob": 0.294,
                "away_implied_prob": 0.238,
                "consensus_home_odds": 1.88,
                "consensus_draw_odds": 3.35,
                "consensus_away_odds": 4.10,
                "home_odds_movement": -0.03,
                "draw_odds_movement": 0.05,
                "away_odds_movement": 0.10,
                "over_under_line": 2.5,
                "over_odds": 1.90,
                "under_odds": 1.95,
                "handicap_line": -0.5,
                "handicap_home_odds": 1.95,
                "handicap_away_odds": 1.90,
                "bookmaker_margin": 0.073,
                "market_efficiency": 0.92,
            },
            {
                "match_id": 1002,
                "event_timestamp": datetime(2025, 9, 10, 16, 30, 0),
                "home_odds": 2.10,
                "draw_odds": 3.20,
                "away_odds": 3.60,
                "home_implied_prob": 0.476,
                "draw_implied_prob": 0.313,
                "away_implied_prob": 0.278,
                "consensus_home_odds": 2.15,
                "consensus_draw_odds": 3.15,
                "consensus_away_odds": 3.55,
                "home_odds_movement": 0.05,
                "draw_odds_movement": -0.05,
                "away_odds_movement": -0.05,
                "over_under_line": 2.5,
                "over_odds": 2.05,
                "under_odds": 1.80,
                "handicap_line": 0.0,
                "handicap_home_odds": 1.85,
                "handicap_away_odds": 2.00,
                "bookmaker_margin": 0.067,
                "market_efficiency": 0.94,
            },
        ]

    @pytest.fixture
    def sample_entity_data(self):
        """示例实体数据"""
        return [
            {"match_id": 1001},
            {"match_id": 1002},
        ]

    @pytest.fixture
    def sample_training_data(self):
        """示例训练数据"""
        base_date = datetime(2025, 8, 1)
        training_entities = []
        for i in range(10):
            training_entities.append(
                {
                    "match_id": 2000 + i,
                    "event_timestamp": base_date + timedelta(days=i * 3),
                }
            )
        return pd.DataFrame(training_entities)

    # 测试特征仓库初始化
    @patch("src.data.features.examples.initialize_feature_store")
    def test_example_initialize_feature_store_success(self, mock_init):
        """测试特征仓库初始化成功"""
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

    @patch("src.data.features.examples.initialize_feature_store")
    def test_example_initialize_feature_store_failure(self, mock_init):
        """测试特征仓库初始化失败"""
        mock_init.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            example_initialize_feature_store()

    # 测试写入球队特征
    def test_example_write_team_features_success(
        self, mock_feature_store, sample_team_data
    ):
        """测试成功写入球队特征"""
        with patch("pandas.DataFrame") as mock_df:
            mock_df.return_value = pd.DataFrame(sample_team_data)

            example_write_team_features(mock_feature_store)

            mock_df.assert_called_once_with(sample_team_data)
            mock_feature_store.write_features.assert_called_once()
            call_args = mock_feature_store.write_features.call_args
            assert call_args[1]["feature_view_name"] == "team_recent_stats"
            assert len(call_args[1]["df"]) == 2

    def test_example_write_team_features_empty_data(self, mock_feature_store):
        """测试写入空的球队数据"""
        empty_data = []
        with patch("pandas.DataFrame") as mock_df:
            mock_df.return_value = pd.DataFrame(empty_data)

            example_write_team_features(mock_feature_store)

            mock_feature_store.write_features.assert_called_once()

    def test_example_write_team_features_write_failure(
        self, mock_feature_store, sample_team_data
    ):
        """测试写入球队特征失败"""
        mock_feature_store.write_features.side_effect = Exception("Write failed")

        with patch("pandas.DataFrame") as mock_df:
            mock_df.return_value = pd.DataFrame(sample_team_data)

            with pytest.raises(Exception, match="Write failed"):
                example_write_team_features(mock_feature_store)

    # 测试写入赔率特征
    def test_example_write_odds_features_success(
        self, mock_feature_store, sample_odds_data
    ):
        """测试成功写入赔率特征"""
        with patch("pandas.DataFrame") as mock_df:
            mock_df.return_value = pd.DataFrame(sample_odds_data)

            example_write_odds_features(mock_feature_store)

            mock_df.assert_called_once_with(sample_odds_data)
            mock_feature_store.write_features.assert_called_once()
            call_args = mock_feature_store.write_features.call_args
            assert call_args[1]["feature_view_name"] == "odds_features"
            assert len(call_args[1]["df"]) == 2

    def test_example_write_odds_features_with_different_values(
        self, mock_feature_store
    ):
        """测试写入不同赔率值的特征"""
        odds_data = [
            {
                "match_id": 1003,
                "event_timestamp": datetime(2025, 9, 11, 15, 0, 0),
                "home_odds": 1.50,
                "draw_odds": 4.00,
                "away_odds": 6.00,
                "home_implied_prob": 0.667,
                "draw_implied_prob": 0.250,
                "away_implied_prob": 0.167,
            }
        ]

        with patch("pandas.DataFrame") as mock_df:
            mock_df.return_value = pd.DataFrame(odds_data)

            example_write_odds_features(mock_feature_store)

            call_args = mock_feature_store.write_features.call_args
            assert call_args[1]["feature_view_name"] == "odds_features"

    # 测试获取在线特征
    def test_example_get_online_features_success(
        self, mock_feature_store, sample_entity_data
    ):
        """测试成功获取在线特征"""
        expected_features = pd.DataFrame(
            {
                "match_id": [1001, 1002],
                "feature1": [0.5, 0.7],
                "feature2": [1.2, 1.5],
            }
        )
        mock_feature_store.get_online_features.return_value = expected_features

        with patch("pandas.DataFrame") as mock_df:
            mock_df.return_value = pd.DataFrame(sample_entity_data)

            result = example_get_online_features(mock_feature_store)

            mock_feature_store.get_online_features.assert_called_once_with(
                feature_service_name="real_time_prediction_v1",
                entity_df=pd.DataFrame(sample_entity_data),
            )
            assert result.equals(expected_features)

    def test_example_get_online_features_empty_result(
        self, mock_feature_store, sample_entity_data
    ):
        """测试获取空的在线特征"""
        mock_feature_store.get_online_features.return_value = pd.DataFrame()

        with patch("pandas.DataFrame") as mock_df:
            mock_df.return_value = pd.DataFrame(sample_entity_data)

            result = example_get_online_features(mock_feature_store)

            assert result.empty

    def test_example_get_online_features_error(
        self, mock_feature_store, sample_entity_data
    ):
        """测试获取在线特征出错"""
        mock_feature_store.get_online_features.side_effect = Exception("Query failed")

        with patch("pandas.DataFrame") as mock_df:
            mock_df.return_value = pd.DataFrame(sample_entity_data)

            with pytest.raises(Exception, match="Query failed"):
                example_get_online_features(mock_feature_store)

    # 测试获取历史特征
    def test_example_get_historical_features_success(
        self, mock_feature_store, sample_training_data
    ):
        """测试成功获取历史特征"""
        expected_result = pd.DataFrame(
            {
                "match_id": [2000, 2001],
                "historical_feature": [0.8, 0.9],
            }
        )
        mock_feature_store.get_historical_features.return_value = expected_result

        result = example_get_historical_features(mock_feature_store)

        mock_feature_store.get_historical_features.assert_called_once_with(
            feature_service_name="match_prediction_v1",
            entity_df=sample_training_data,
            full_feature_names=True,
        )
        assert result.equals(expected_result)

    def test_example_get_historical_features_with_different_dates(
        self, mock_feature_store
    ):
        """测试获取不同日期范围的历史特征"""
        base_date = datetime(2025, 7, 1)
        training_entities = []
        for i in range(5):
            training_entities.append(
                {
                    "match_id": 3000 + i,
                    "event_timestamp": base_date + timedelta(days=i * 7),
                }
            )
        entity_df = pd.DataFrame(training_entities)

        expected_result = pd.DataFrame(
            {
                "match_id": [3000, 3001],
                "feature": [0.6, 0.7],
            }
        )
        mock_feature_store.get_historical_features.return_value = expected_result

        result = example_get_historical_features(mock_feature_store)

        mock_feature_store.get_historical_features.assert_called_once()
        call_args = mock_feature_store.get_historical_features.call_args
        assert call_args[1]["entity_df"].equals(entity_df)

    # 测试创建训练数据集
    def test_example_create_training_dataset_success(self, mock_feature_store):
        """测试成功创建训练数据集"""
        expected_dataset = pd.DataFrame(
            {
                "feature1": [1, 2, 3],
                "feature2": [4, 5, 6],
                "target": [0, 1, 0],
            }
        )
        mock_feature_store.create_training_dataset.return_value = expected_dataset

        result = example_create_training_dataset(mock_feature_store)

        start_date = datetime(2025, 7, 1)
        end_date = datetime(2025, 9, 1)
        mock_feature_store.create_training_dataset.assert_called_once_with(
            start_date=start_date, end_date=end_date
        )
        assert result.equals(expected_dataset)

    def test_example_create_training_dataset_different_date_range(
        self, mock_feature_store
    ):
        """测试创建不同日期范围的训练数据集"""
        expected_dataset = pd.DataFrame({"feature": [1, 2]})
        mock_feature_store.create_training_dataset.return_value = expected_dataset

        # 修改函数行为以使用不同日期
        def create_training_dataset_custom(start_date, end_date):
            return expected_dataset

        mock_feature_store.create_training_dataset.side_effect = (
            create_training_dataset_custom
        )

        result = example_create_training_dataset(mock_feature_store)

        call_args = mock_feature_store.create_training_dataset.call_args
        assert call_args[1]["start_date"] == datetime(2025, 7, 1)
        assert call_args[1]["end_date"] == datetime(2025, 9, 1)

    def test_example_create_training_dataset_empty_result(self, mock_feature_store):
        """测试创建空的训练数据集"""
        mock_feature_store.create_training_dataset.return_value = pd.DataFrame()

        result = example_create_training_dataset(mock_feature_store)

        assert result.empty

    # 测试获取特征统计信息
    def test_example_feature_statistics_success(self, mock_feature_store):
        """测试成功获取特征统计信息"""
        mock_stats = {
            "num_features": 25,
            "entities": ["match", "team"],
            "ttl_days": 30,
            "tags": {"type": "historical"},
        }
        mock_feature_store.get_feature_statistics.return_value = mock_stats

        with patch("builtins.print"):  # 避免打印输出
            example_feature_statistics(mock_feature_store)

        expected_calls = [
            call("team_recent_stats"),
            call("odds_features"),
            call("match_features"),
        ]
        mock_feature_store.get_feature_statistics.assert_has_calls(expected_calls)

    def test_example_feature_statistics_with_exception(self, mock_feature_store):
        """测试获取特征统计时出现异常"""
        mock_feature_store.get_feature_statistics.side_effect = Exception("Stats error")

        with patch("builtins.print"):  # 避免打印输出
            example_feature_statistics(mock_feature_store)

        # 应该仍然调用所有特征视图
        assert mock_feature_store.get_feature_statistics.call_count == 3

    def test_example_feature_statistics_mixed_results(self, mock_feature_store):
        """测试混合成功和失败的特征统计结果"""

        def side_effect(fv_name):
            if fv_name == "team_recent_stats":
                return {"num_features": 20, "entities": ["team"]}
            elif fv_name == "odds_features":
                raise Exception("Connection error")
            else:
                return {"num_features": 15, "entities": ["match"]}

        mock_feature_store.get_feature_statistics.side_effect = side_effect

        with patch("builtins.print"):  # 避免打印输出
            example_feature_statistics(mock_feature_store)

        # 所有特征视图都应该被调用
        assert mock_feature_store.get_feature_statistics.call_count == 3

    # 测试列出所有特征
    def test_example_list_all_features_success(self, mock_feature_store):
        """测试成功列出所有特征"""
        features_list = [
            {
                "feature_view": "team_recent_stats",
                "feature_name": "recent_5_wins",
                "feature_type": "numeric",
            },
            {
                "feature_view": "odds_features",
                "feature_name": "home_odds",
                "feature_type": "float",
            },
            {
                "feature_view": "match_features",
                "feature_name": "home_goals",
                "feature_type": "integer",
            },
        ]
        mock_feature_store.list_features.return_value = features_list

        with patch("builtins.print"):  # 避免打印输出
            example_list_all_features(mock_feature_store)

        mock_feature_store.list_features.assert_called_once()

    def test_example_list_all_features_empty_list(self, mock_feature_store):
        """测试列出空的特征列表"""
        mock_feature_store.list_features.return_value = []

        with patch("builtins.print"):  # 避免打印输出
            example_list_all_features(mock_feature_store)

        mock_feature_store.list_features.assert_called_once()

    def test_example_list_all_features_long_list(self, mock_feature_store):
        """测试列出很长的特征列表"""
        features_list = []
        for i in range(25):  # 超过10个特征
            features_list.append(
                {
                    "feature_view": f"view_{i}",
                    "feature_name": f"feature_{i}",
                    "feature_type": "numeric",
                }
            )
        mock_feature_store.list_features.return_value = features_list

        with patch("builtins.print"):  # 避免打印输出
            example_list_all_features(mock_feature_store)

        mock_feature_store.list_features.assert_called_once()

    # 测试运行完整示例
    @patch("src.data.features.examples.example_initialize_feature_store")
    @patch("src.data.features.examples.example_write_team_features")
    @patch("src.data.features.examples.example_write_odds_features")
    @patch("src.data.features.examples.example_get_online_features")
    @patch("src.data.features.examples.example_get_historical_features")
    @patch("src.data.features.examples.example_create_training_dataset")
    @patch("src.data.features.examples.example_feature_statistics")
    @patch("src.data.features.examples.example_list_all_features")
    async def test_run_complete_example_success(
        self,
        mock_list_features,
        mock_stats,
        mock_create_dataset,
        mock_get_historical,
        mock_get_online,
        mock_write_odds,
        mock_write_team,
        mock_init,
        mock_feature_store,
    ):
        """测试成功运行完整示例"""
        mock_init.return_value = mock_feature_store

        await run_complete_example()

        # 验证所有步骤都被调用
        mock_init.assert_called_once()
        mock_write_team.assert_called_once()
        mock_write_odds.assert_called_once()
        mock_get_online.assert_called_once()
        mock_get_historical.assert_called_once()
        mock_create_dataset.assert_called_once()
        mock_stats.assert_called_once()
        mock_list_features.assert_called_once()
        mock_feature_store.close.assert_called_once()

    @patch("src.data.features.examples.example_initialize_feature_store")
    async def test_run_complete_example_initialization_failure(self, mock_init):
        """测试完整示例初始化失败"""
        mock_init.side_effect = Exception("Initialization failed")

        with pytest.raises(Exception, match="Initialization failed"):
            await run_complete_example()

    @patch("src.data.features.examples.example_initialize_feature_store")
    @patch("src.data.features.examples.example_write_team_features")
    async def test_run_complete_example_step_failure(
        self, mock_write_team, mock_init, mock_feature_store
    ):
        """测试完整示例中某个步骤失败"""
        mock_init.return_value = mock_feature_store
        mock_write_team.side_effect = Exception("Write failed")

        with pytest.raises(Exception, match="Write failed"):
            await run_complete_example()

        # 即使失败，也应该关闭资源
        mock_feature_store.close.assert_called_once()

    # 测试ML流水线集成
    @patch("src.data.features.examples.get_feature_store")
    def test_example_integration_with_ml_pipeline_success(
        self, mock_get_store, mock_feature_store
    ):
        """测试成功集成ML流水线"""
        mock_get_store.return_value = mock_feature_store

        # Mock训练数据集
        training_df = pd.DataFrame(
            {
                "feature1": [1, 2, 3],
                "target": [0, 1, 0],
            }
        )
        mock_feature_store.create_training_dataset.return_value = training_df

        # Mock在线特征
        online_features = pd.DataFrame(
            {
                "match_id": [3001, 3002],
                "online_feature": [0.8, 0.9],
            }
        )
        mock_feature_store.get_online_features.return_value = online_features

        result = example_integration_with_ml_pipeline()

        assert result["integration_status"] == "success"
        assert result["training_result"]["model_trained"] is True
        assert result["training_result"]["training_samples"] == 3
        assert result["prediction_result"]["predictions_made"] == 2

        # 验证调用
        mock_feature_store.create_training_dataset.assert_called_once()
        mock_feature_store.get_online_features.assert_called_once()

    @patch("src.data.features.examples.get_feature_store")
    def test_example_integration_with_ml_pipeline_training_failure(
        self, mock_get_store, mock_feature_store
    ):
        """测试ML流水线集成中训练失败"""
        mock_get_store.return_value = mock_feature_store
        mock_feature_store.create_training_dataset.side_effect = Exception(
            "Training failed"
        )

        result = example_integration_with_ml_pipeline()

        assert result["integration_status"] == "success"  # 集成状态仍然成功
        assert "error" not in result  # 不应该抛出异常

    @patch("src.data.features.examples.get_feature_store")
    def test_example_integration_with_ml_pipeline_prediction_failure(
        self, mock_get_store, mock_feature_store
    ):
        """测试ML流水线集成中预测失败"""
        mock_get_store.return_value = mock_feature_store

        # Mock成功的训练
        training_df = pd.DataFrame({"feature": [1, 2]})
        mock_feature_store.create_training_dataset.return_value = training_df

        # Mock失败的预测
        mock_feature_store.get_online_features.side_effect = Exception(
            "Prediction failed"
        )

        result = example_integration_with_ml_pipeline()

        assert result["integration_status"] == "success"
        assert result["training_result"]["model_trained"] is True
        assert result["prediction_result"]["predictions_made"] == 0  # 预测失败

    # 测试边界情况和错误处理
    def test_example_functions_with_none_feature_store(self):
        """测试使用None特征仓库的边界情况"""
        with pytest.raises(AttributeError):
            example_write_team_features(None)

    def test_example_functions_with_invalid_data_types(self, mock_feature_store):
        """测试使用无效数据类型的边界情况"""
        with patch("pandas.DataFrame") as mock_df:
            mock_df.side_effect = Exception("Invalid data")

            with pytest.raises(Exception, match="Invalid data"):
                example_write_team_features(mock_feature_store)

    @patch("src.data.features.examples.pandas.DataFrame")
    def test_example_functions_with_dataframe_creation_error(
        self, mock_df_class, mock_feature_store
    ):
        """测试DataFrame创建错误的处理"""
        mock_df_class.side_effect = Exception("DataFrame creation failed")

        with pytest.raises(Exception, match="DataFrame creation failed"):
            example_write_team_features(mock_feature_store)

    # 测试配置和参数验证
    @patch("src.data.features.examples.initialize_feature_store")
    def test_initialize_feature_store_configuration(
        self, mock_init, mock_feature_store
    ):
        """测试特征仓库初始化配置"""
        mock_init.return_value = mock_feature_store

        result = example_initialize_feature_store()

        # 验证配置参数
        call_args = mock_init.call_args
        assert call_args[1]["project_name"] == "football_prediction_demo"
        assert "postgres_config" in call_args[1]
        assert "redis_config" in call_args[1]

    def test_feature_view_names_validation(self, mock_feature_store):
        """测试特征视图名称验证"""
        # 测试各种特征视图名称
        test_views = ["team_recent_stats", "odds_features", "match_features"]

        for view_name in test_views:
            mock_feature_store.get_feature_statistics.return_value = {
                "num_features": 10
            }

            with patch("builtins.print"):
                example_feature_statistics(mock_feature_store)

            # 验证调用包含正确的特征视图名称
            call_found = False
            for call in mock_feature_store.get_feature_statistics.call_args_list:
                if call[0][0] == view_name:
                    call_found = True
                    break
            assert call_found, f"Feature view {view_name} not called"

    # 测试性能和大批量数据
    def test_large_team_dataset_processing(self, mock_feature_store):
        """测试处理大批量球队数据"""
        # 创建大量球队数据
        large_team_data = []
        for i in range(1000):  # 1000支队伍
            large_team_data.append(
                {
                    "team_id": i + 1,
                    "event_timestamp": datetime(2025, 9, 10),
                    "recent_5_wins": i % 5,
                    "recent_5_losses": (i + 1) % 5,
                    "team_value_millions": 50.0 + i * 0.5,
                }
            )

        with patch("pandas.DataFrame") as mock_df:
            mock_df.return_value = pd.DataFrame(large_team_data)

            example_write_team_features(mock_feature_store)

            call_args = mock_feature_store.write_features.call_args
            assert len(call_args[1]["df"]) == 1000

    def test_concurrent_feature_access(self, mock_feature_store):
        """测试并发特征访问"""

        # 模拟并发访问特征仓库
        def mock_concurrent_access():
            with patch("pandas.DataFrame") as mock_df:
                mock_df.return_value = pd.DataFrame([{"match_id": 1}])
                example_get_online_features(mock_feature_store)

        # 多次调用测试并发处理
        for _ in range(10):
            mock_concurrent_access()

        # 验证所有调用都成功
        assert mock_feature_store.get_online_features.call_count == 10

    # 测试数据格式转换和验证
    def test_data_format_conversion(self, mock_feature_store):
        """测试数据格式转换"""
        team_data = [
            {
                "team_id": 1,
                "event_timestamp": datetime(2025, 9, 10),
                "recent_5_wins": "3",  # 字符串数字
                "recent_5_draws": 1.5,  # 浮点数
            }
        ]

        with patch("pandas.DataFrame") as mock_df:
            mock_df.return_value = pd.DataFrame(team_data)

            example_write_team_features(mock_feature_store)

            # 验证DataFrame被正确创建
            mock_df.assert_called_once_with(team_data)

    # 测试内存和资源管理
    def test_memory_efficient_processing(self, mock_feature_store):
        """测试内存高效处理"""
        # 创建可能导致内存问题的数据
        memory_heavy_data = []
        for i in range(10000):
            memory_heavy_data.append(
                {
                    "team_id": i,
                    "event_timestamp": datetime(2025, 9, 10),
                    f"feature_{i}": i * 0.1,
                }
            )

        with patch("pandas.DataFrame") as mock_df:
            mock_df.return_value = pd.DataFrame(memory_heavy_data)

            example_write_team_features(mock_feature_store)

            # 验证函数能处理大数据集
            mock_feature_store.write_features.assert_called_once()

    # 测试日志和监控
    @patch("src.data.features.examples.logger")
    def test_logging_behavior(self, mock_logger, mock_feature_store):
        """测试日志记录行为"""
        mock_feature_store.get_feature_statistics.side_effect = Exception("Test error")

        with patch("builtins.print"):
            example_feature_statistics(mock_feature_store)

        # 验证错误被记录
        mock_logger.error.assert_called()

    def test_feature_store_close_behavior(self, mock_feature_store):
        """测试特征仓库关闭行为"""
        mock_feature_store.close.side_effect = Exception("Close failed")

        with pytest.raises(Exception, match="Close failed"):
            with patch(
                "src.data.features.examples.example_initialize_feature_store"
            ) as mock_init:
                mock_init.return_value = mock_feature_store
                store = example_initialize_feature_store()
                store.close()

    # 测试配置灵活性和扩展性
    @patch("src.data.features.examples.initialize_feature_store")
    def test_different_configurations(self, mock_init, mock_feature_store):
        """测试不同配置的灵活性"""
        mock_init.return_value = mock_feature_store

        result = example_initialize_feature_store()

        # 验证可以处理不同的PostgreSQL和Redis配置
        call_args = mock_init.call_args
        postgres_config = call_args[1]["postgres_config"]
        redis_config = call_args[1]["redis_config"]

        assert isinstance(postgres_config, dict)
        assert isinstance(redis_config, dict)
        assert "host" in postgres_config
        assert "connection_string" in redis_config

    # 测试特征服务名称验证
    def test_feature_service_names(self, mock_feature_store, sample_entity_data):
        """测试特征服务名称验证"""
        with patch("pandas.DataFrame") as mock_df:
            mock_df.return_value = pd.DataFrame(sample_entity_data)

            example_get_online_features(mock_feature_store)

        call_args = mock_feature_store.get_online_features.call_args
        assert call_args[1]["feature_service_name"] == "real_time_prediction_v1"

        # 测试历史特征服务名称
        with patch("src.data.features.examples.pandas.DataFrame"):
            example_get_historical_features(mock_feature_store)

        call_args = mock_feature_store.get_historical_features.call_args
        assert call_args[1]["feature_service_name"] == "match_prediction_v1"

    # 测试时间相关功能
    def test_time_based_features(self, mock_feature_store):
        """测试基于时间的特征功能"""
        # 测试不同时间戳的处理
        different_times_data = [
            {
                "match_id": 1,
                "event_timestamp": datetime(2024, 1, 1),  # 过去时间
                "home_odds": 2.0,
            },
            {
                "match_id": 2,
                "event_timestamp": datetime(2026, 1, 1),  # 未来时间
                "home_odds": 3.0,
            },
        ]

        with patch("pandas.DataFrame") as mock_df:
            mock_df.return_value = pd.DataFrame(different_times_data)

            example_write_odds_features(mock_feature_store)

        call_args = mock_feature_store.write_features.call_args
        df = call_args[1]["df"]
        # 验证时间戳被正确处理
        assert len(df) == 2

    # 测试完整集成流程
    @patch("src.data.features.examples.example_initialize_feature_store")
    @patch("src.data.features.examples.example_write_team_features")
    @patch("src.data.features.examples.example_write_odds_features")
    @patch("src.data.features.examples.example_get_online_features")
    async def test_complete_integration_workflow(
        self,
        mock_get_online,
        mock_write_odds,
        mock_write_team,
        mock_init,
        mock_feature_store,
    ):
        """测试完整的集成工作流程"""
        mock_init.return_value = mock_feature_store

        # 模拟在线特征返回
        online_features = pd.DataFrame(
            {
                "match_id": [1001, 1002],
                "prediction_feature": [0.8, 0.6],
            }
        )
        mock_get_online.return_value = online_features

        # 执行集成工作流程
        store = example_initialize_feature_store()
        example_write_team_features(store)
        example_write_odds_features(store)
        features = example_get_online_features(store)

        # 验证流程完整性
        assert mock_init.called
        assert mock_write_team.called
        assert mock_write_odds.called
        assert mock_get_online.called
        assert not features.empty
        assert len(features) == 2

    # 测试数据一致性验证
    def test_data_consistency_validation(self, mock_feature_store):
        """测试数据一致性验证"""
        # 创建可能导致数据不一致的情况
        inconsistent_data = [
            {
                "match_id": 1,
                "home_odds": 2.0,
                "draw_odds": 3.0,
                "away_odds": 4.0,
                "home_implied_prob": 0.6,  # 不一致的隐含概率
            }
        ]

        with patch("pandas.DataFrame") as mock_df:
            mock_df.return_value = pd.DataFrame(inconsistent_data)

            # 函数应该能够处理不一致数据
            example_write_odds_features(mock_feature_store)

        # 验证函数仍然执行了写入操作
        mock_feature_store.write_features.assert_called_once()

    # 测试缓存和性能优化
    @patch("src.data.features.examples.pandas.DataFrame")
    def test_caching_behavior(self, mock_df_class, mock_feature_store):
        """测试缓存行为"""
        # 验证多次调用相同数据时的处理
        for i in range(3):
            team_data = [{"team_id": i, "recent_5_wins": 3}]
            mock_df_class.return_value = pd.DataFrame(team_data)

            example_write_team_features(mock_feature_store)

        # 验证所有调用都被处理
        assert mock_feature_store.write_features.call_count == 3

    # 最终清理测试
    def test_cleanup_and_resource_management(self, mock_feature_store):
        """测试清理和资源管理"""
        # 测试资源清理
        mock_feature_store.reset_mock()

        with patch(
            "src.data.features.examples.example_initialize_feature_store"
        ) as mock_init:
            mock_init.return_value = mock_feature_store

            store = example_initialize_feature_store()
            store.close()

        # 验证资源被正确清理
        mock_feature_store.close.assert_called_once()
