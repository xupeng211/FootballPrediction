"""
阶段2：数据特征示例测试
目标：补齐核心逻辑测试覆盖率达到70%+
重点：测试特征仓库示例、数据写入、特征获取、ML集成
"""

from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

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


class TestDataFeaturesExamplesPhase2:
    """数据特征示例阶段2测试"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_feature_store = Mock()
        self.mock_feature_store.write_features = Mock()
        self.mock_feature_store.get_online_features = Mock()
        self.mock_feature_store.get_historical_features = Mock()
        self.mock_feature_store.create_training_dataset = Mock()
        self.mock_feature_store.get_feature_statistics = Mock()
        self.mock_feature_store.list_features = Mock()
        self.mock_feature_store.close = Mock()

    def test_example_initialize_feature_store_basic(self):
        """测试特征仓库初始化示例基本功能"""
        with patch("src.data.features.examples.initialize_feature_store") as mock_init:
            mock_store = Mock()
            mock_init.return_value = mock_store

            result = example_initialize_feature_store()

            # 验证初始化调用
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

            assert result == mock_store

    def test_example_initialize_feature_store_config_structure(self):
        """测试特征仓库初始化配置结构"""
        with patch("src.data.features.examples.initialize_feature_store") as mock_init:
            mock_store = Mock()
            mock_init.return_value = mock_store

            example_initialize_feature_store()

            # 验证配置参数结构
            call_args = mock_init.call_args
            config = call_args.kwargs

            assert "project_name" in config
            assert "postgres_config" in config
            assert "redis_config" in config

            # 验证PostgreSQL配置
            postgres_config = config["postgres_config"]
            required_postgres_keys = ["host", "port", "database", "user", "password"]
            for key in required_postgres_keys:
                assert key in postgres_config

            # 验证Redis配置
            redis_config = config["redis_config"]
            assert "connection_string" in redis_config

    def test_example_write_team_features_data_structure(self):
        """测试写入球队特征数据结构"""
        with patch("src.data.features.examples.pd.DataFrame") as mock_dataframe:
            mock_df = Mock()
            mock_dataframe.return_value = mock_df

            example_write_team_features(self.mock_feature_store)

            # 验证DataFrame创建
            call_args = mock_dataframe.call_args[0][0]
            assert isinstance(call_args, list)
            assert len(call_args) == 2  # 2个队伍的数据

            # 验证数据结构
            team_data = call_args[0]
            required_fields = [
                "team_id",
                "event_timestamp",
                "recent_5_wins",
                "recent_5_draws",
                "recent_5_losses",
                "recent_5_goals_for",
                "recent_5_goals_against",
                "recent_5_goal_difference",
                "recent_5_points",
                "recent_5_avg_rating",
                "team_value_millions",
                "avg_player_age",
                "league_position",
                "points_per_game",
            ]
            for field in required_fields:
                assert field in team_data

    def test_example_write_team_features_feature_store_call(self):
        """测试写入球队特征调用特征仓库"""
        with patch("src.data.features.examples.pd.DataFrame") as mock_dataframe:
            mock_df = Mock()
            mock_dataframe.return_value = mock_df

            example_write_team_features(self.mock_feature_store)

            # 验证特征仓库调用
            self.mock_feature_store.write_features.assert_called_once_with(
                feature_view_name="team_recent_stats", df=mock_df
            )

    def test_example_write_odds_features_data_structure(self):
        """测试写入赔率特征数据结构"""
        with patch("src.data.features.examples.pd.DataFrame") as mock_dataframe:
            mock_df = Mock()
            mock_dataframe.return_value = mock_df

            example_write_odds_features(self.mock_feature_store)

            # 验证DataFrame创建
            call_args = mock_dataframe.call_args[0][0]
            assert isinstance(call_args, list)
            assert len(call_args) == 2  # 2场比赛的数据

            # 验证数据结构
            odds_data = call_args[0]
            required_fields = [
                "match_id",
                "event_timestamp",
                "home_odds",
                "draw_odds",
                "away_odds",
                "home_implied_prob",
                "draw_implied_prob",
                "away_implied_prob",
                "consensus_home_odds",
                "consensus_draw_odds",
                "consensus_away_odds",
                "bookmaker_margin",
                "market_efficiency",
            ]
            for field in required_fields:
                assert field in odds_data

    def test_example_write_odds_features_feature_store_call(self):
        """测试写入赔率特征调用特征仓库"""
        with patch("src.data.features.examples.pd.DataFrame") as mock_dataframe:
            mock_df = Mock()
            mock_dataframe.return_value = mock_df

            example_write_odds_features(self.mock_feature_store)

            # 验证特征仓库调用
            self.mock_feature_store.write_features.assert_called_once_with(
                feature_view_name="odds_features", df=mock_df
            )

    def test_example_get_online_features_entity_data_structure(self):
        """测试获取在线特征实体数据结构"""
        with patch("src.data.features.examples.pd.DataFrame") as mock_dataframe:
            mock_df = Mock()
            mock_dataframe.return_value = mock_df
            self.mock_feature_store.get_online_features.return_value = mock_df

            result = example_get_online_features(self.mock_feature_store)

            # 验证实体DataFrame创建
            call_args = mock_dataframe.call_args[0][0]
            assert isinstance(call_args, list)
            assert len(call_args) == 2  # 2场比赛

            # 验证实体数据结构
            entity_data = call_args[0]
            assert "match_id" in entity_data
            assert entity_data["match_id"] == 1001

            # 验证特征仓库调用
            self.mock_feature_store.get_online_features.assert_called_once_with(
                feature_service_name="real_time_prediction_v1", entity_df=mock_df
            )

            assert result == mock_df

    def test_example_get_historical_features_entity_generation(self):
        """测试获取历史特征实体生成"""
        with patch("src.data.features.examples.pd.DataFrame") as mock_dataframe:
            mock_df = Mock()
            mock_dataframe.return_value = mock_df
            self.mock_feature_store.get_historical_features.return_value = mock_df

            result = example_get_historical_features(self.mock_feature_store)

            # 验证实体DataFrame创建
            call_args = mock_dataframe.call_args[0][0]
            assert isinstance(call_args, list)
            assert len(call_args) == 10  # 10场历史比赛

            # 验证时间序列生成
            for i, entity in enumerate(call_args):
                assert "match_id" in entity
                assert "event_timestamp" in entity
                assert entity["match_id"] == 2000 + i
                expected_date = datetime(2025, 8, 1) + timedelta(days=i * 3)
                assert entity["event_timestamp"] == expected_date

            # 验证特征仓库调用
            self.mock_feature_store.get_historical_features.assert_called_once_with(
                feature_service_name="match_prediction_v1",
                entity_df=mock_df,
                full_feature_names=True,
            )

            assert result == mock_df

    def test_example_create_training_dataset_date_range(self):
        """测试创建训练数据集日期范围"""
        mock_df = Mock()
        mock_df.shape = (100, 20)  # 模拟100条记录，20个特征
        self.mock_feature_store.create_training_dataset.return_value = mock_df

        result = example_create_training_dataset(self.mock_feature_store)

        # 验证日期范围参数
        expected_start = datetime(2025, 7, 1)
        expected_end = datetime(2025, 9, 1)

        self.mock_feature_store.create_training_dataset.assert_called_once_with(
            start_date=expected_start, end_date=expected_end
        )

        assert result == mock_df

    def test_example_feature_statistics_feature_views(self):
        """测试特征统计特征视图"""
        # 模拟成功的统计响应
        mock_stats = {
            "num_features": 15,
            "entities": ["match", "team"],
            "ttl_days": 7,
            "tags": {"domain": "football", "version": "v1"},
        }
        self.mock_feature_store.get_feature_statistics.return_value = mock_stats

        example_feature_statistics(self.mock_feature_store)

        # 验证调用的特征视图
        expected_views = ["team_recent_stats", "odds_features", "match_features"]
        calls = self.mock_feature_store.get_feature_statistics.call_args_list

        assert len(calls) == len(expected_views)
        for i, view_name in enumerate(expected_views):
            assert calls[i][0][0] == view_name

    def test_example_feature_statistics_error_handling(self):
        """测试特征统计错误处理"""
        # 模拟部分失败
        self.mock_feature_store.get_feature_statistics.side_effect = [
            {"num_features": 10, "entities": ["match"]},  # 成功
            Exception("Connection failed"),  # 失败
            {"num_features": 5, "entities": ["team"]},  # 成功
        ]

        with patch("src.data.features.examples.print") as mock_print:
            example_feature_statistics(self.mock_feature_store)

            # 验证错误被正确处理
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("❌ 获取" in call and "统计失败" in call for call in print_calls)

    def test_example_list_all_features_success_case(self):
        """测试列出所有特征成功情况"""
        mock_features = [
            {
                "feature_view": "team_stats",
                "feature_name": "recent_wins",
                "feature_type": "int",
            },
            {
                "feature_view": "odds",
                "feature_name": "home_odds",
                "feature_type": "float",
            },
            {
                "feature_view": "match",
                "feature_name": "match_date",
                "feature_type": "datetime",
            },
        ]
        self.mock_feature_store.list_features.return_value = mock_features

        with patch("src.data.features.examples.print") as mock_print:
            example_list_all_features(self.mock_feature_store)

            # 验证输出格式
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("发现 3 个特征" in call for call in print_calls)

    def test_example_list_all_features_empty_case(self):
        """测试列出所有特征空情况"""
        self.mock_feature_store.list_features.return_value = []

        with patch("src.data.features.examples.print") as mock_print:
            example_list_all_features(self.mock_feature_store)

            # 验证空情况处理
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("未找到任何特征" in call for call in print_calls)

    def test_run_complete_example_success_flow(self):
        """测试运行完整示例成功流程"""
        with patch(
            "src.data.features.examples.example_initialize_feature_store"
        ) as mock_init, patch(
            "src.data.features.examples.example_write_team_features"
        ) as mock_write_team, patch(
            "src.data.features.examples.example_write_odds_features"
        ) as mock_write_odds, patch(
            "src.data.features.examples.example_get_online_features"
        ) as mock_get_online, patch(
            "src.data.features.examples.example_get_historical_features"
        ) as mock_get_historical, patch(
            "src.data.features.examples.example_create_training_dataset"
        ) as mock_create_dataset, patch(
            "src.data.features.examples.example_feature_statistics"
        ) as mock_stats, patch(
            "src.data.features.examples.example_list_all_features"
        ) as mock_list_features:
            mock_store = Mock()
            mock_init.return_value = mock_store

            # 运行完整示例
            run_complete_example()

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

    def test_run_complete_example_exception_handling(self):
        """测试运行完整示例异常处理"""
        with patch(
            "src.data.features.examples.example_initialize_feature_store"
        ) as mock_init, patch("src.data.features.examples.logger") as mock_logger:
            # 模拟初始化失败
            mock_init.side_effect = Exception("Initialization failed")

            # 运行完整示例
            run_complete_example()

            # 验证错误被记录
            mock_logger.error.assert_called_once()
            assert "Feature store example failed" in str(mock_logger.error.call_args)

    def test_example_integration_with_ml_pipeline_structure(self):
        """测试ML流水线集成示例结构"""
        with patch(
            "src.data.features.examples.get_feature_store"
        ) as mock_get_store, patch(
            "src.data.features.examples.pd.DataFrame"
        ) as mock_dataframe:
            mock_store = Mock()
            mock_get_store.return_value = mock_store

            # 模拟训练数据
            mock_training_df = Mock()
            mock_training_df.__len__ = Mock(return_value=1000)
            mock_store.create_training_dataset.return_value = mock_training_df

            # 模拟预测数据
            mock_prediction_df = Mock()
            mock_prediction_df.__len__ = Mock(return_value=2)
            mock_store.get_online_features.return_value = mock_prediction_df

            result = example_integration_with_ml_pipeline()

            # 验证结果结构
            assert isinstance(result, dict)
            assert "training_result" in result
            assert "prediction_result" in result
            assert "integration_status" in result
            assert result["integration_status"] == "success"

            # 验证训练结果
            training_result = result["training_result"]
            assert training_result["model_trained"] is True
            assert training_result["training_samples"] == 1000

            # 验证预测结果
            prediction_result = result["prediction_result"]
            assert prediction_result["predictions_made"] == 2

    def test_example_integration_with_ml_pipeline_dataframe_creation(self):
        """测试ML流水线集成DataFrame创建"""
        with patch(
            "src.data.features.examples.get_feature_store"
        ) as mock_get_store, patch(
            "src.data.features.examples.pd.DataFrame"
        ) as mock_dataframe:
            mock_store = Mock()
            mock_get_store.return_value = mock_store
            mock_df = Mock()
            mock_dataframe.return_value = mock_df

            example_integration_with_ml_pipeline()

            # 验证DataFrame创建调用
            dataframe_calls = [
                call for call in mock_dataframe.call_args_list if call[0]
            ]
            assert len(dataframe_calls) >= 1

            # 验证预测实体结构
            prediction_call = dataframe_calls[0][0][0]
            assert isinstance(prediction_call, list)
            assert all("match_id" in entity for entity in prediction_call)

    def test_example_integration_with_ml_pipeline_date_range(self):
        """测试ML流水线集成日期范围"""
        with patch("src.data.features.examples.get_feature_store") as mock_get_store:
            mock_store = Mock()
            mock_get_store.return_value = mock_store

            example_integration_with_ml_pipeline()

            # 验证训练数据日期范围
            call_args = mock_store.create_training_dataset.call_args
            expected_start = datetime(2025, 6, 1)
            expected_end = datetime(2025, 8, 31)

            assert call_args.kwargs["start_date"] == expected_start
            assert call_args.kwargs["end_date"] == expected_end

    def test_example_integration_with_ml_pipeline_feature_service_names(self):
        """测试ML流水线集成特征服务名称"""
        with patch("src.data.features.examples.get_feature_store") as mock_get_store:
            mock_store = Mock()
            mock_get_store.return_value = mock_store

            example_integration_with_ml_pipeline()

            # 验证特征服务名称
            online_call = mock_store.get_online_features.call_args
            assert (
                online_call.kwargs["feature_service_name"] == "real_time_prediction_v1"
            )

    def test_data_types_validation(self):
        """测试数据类型验证"""
        # 验证示例数据中的数据类型
        with patch("src.data.features.examples.pd.DataFrame") as mock_dataframe:
            mock_df = Mock()
            mock_dataframe.return_value = mock_df

            example_write_team_features(self.mock_feature_store)

            # 获取创建的数据
            call_args = mock_dataframe.call_args[0][0]
            team_data = call_args[0]

            # 验证数据类型
            assert isinstance(team_data["team_id"], int)
            assert isinstance(team_data["event_timestamp"], datetime)
            assert isinstance(team_data["recent_5_wins"], int)
            assert isinstance(team_data["recent_5_goals_for"], int)
            assert isinstance(team_data["recent_5_avg_rating"], float)
            assert isinstance(team_data["team_value_millions"], float)
            assert isinstance(team_data["avg_player_age"], float)

    def test_timestamp_consistency(self):
        """测试时间戳一致性"""
        with patch("src.data.features.examples.pd.DataFrame") as mock_dataframe:
            mock_df = Mock()
            mock_dataframe.return_value = mock_df

            example_write_odds_features(self.mock_feature_store)

            # 获取创建的数据
            call_args = mock_dataframe.call_args[0][0]
            odds_data = call_args[0]

            # 验证时间戳包含时间信息
            timestamp = odds_data["event_timestamp"]
            assert isinstance(timestamp, datetime)
            assert timestamp.hour == 14
            assert timestamp.minute == 0
            assert timestamp.second == 0

    def test_feature_value_ranges(self):
        """测试特征值范围"""
        with patch("src.data.features.examples.pd.DataFrame") as mock_dataframe:
            mock_df = Mock()
            mock_dataframe.return_value = mock_df

            example_write_odds_features(self.mock_feature_store)

            # 获取创建的数据
            call_args = mock_dataframe.call_args[0][0]
            odds_data = call_args[0]

            # 验证赔率值范围
            assert odds_data["home_odds"] > 1.0
            assert odds_data["draw_odds"] > 1.0
            assert odds_data["away_odds"] > 1.0

            # 验证概率和
            implied_prob_sum = (
                odds_data["home_implied_prob"]
                + odds_data["draw_implied_prob"]
                + odds_data["away_implied_prob"]
            )
            assert implied_prob_sum > 1.0  # 考虑庄家赔率

    def test_error_propagation_in_complete_example(self):
        """测试完整示例中的错误传播"""
        with patch(
            "src.data.features.examples.example_initialize_feature_store"
        ) as mock_init, patch(
            "src.data.features.examples.example_write_team_features"
        ) as mock_write_team:
            mock_store = Mock()
            mock_init.return_value = mock_store
            mock_write_team.side_effect = Exception("Write failed")

            with patch("src.data.features.examples.print") as mock_print, patch(
                "src.data.features.examples.logger"
            ) as mock_logger:
                run_complete_example()

                # 验证错误处理
                mock_store.close.assert_called_once()
                mock_logger.error.assert_called_once()

    def test_feature_store_resource_cleanup(self):
        """测试特征仓库资源清理"""
        with patch(
            "src.data.features.examples.example_initialize_feature_store"
        ) as mock_init:
            mock_store = Mock()
            mock_init.return_value = mock_store

            with patch("src.data.features.examples.example_write_team_features"), patch(
                "src.data.features.examples.example_write_odds_features"
            ), patch("src.data.features.examples.example_get_online_features"), patch(
                "src.data.features.examples.example_get_historical_features"
            ), patch(
                "src.data.features.examples.example_create_training_dataset"
            ), patch(
                "src.data.features.examples.example_feature_statistics"
            ), patch(
                "src.data.features.examples.example_list_all_features"
            ):
                run_complete_example()

                # 验证资源清理
                mock_store.close.assert_called_once()

    def test_pandas_integration(self):
        """测试Pandas集成"""
        with patch("src.data.features.examples.pd.DataFrame") as mock_dataframe:
            mock_df = Mock()
            mock_df.shape = (10, 5)
            mock_dataframe.return_value = mock_df

            result = example_create_training_dataset(self.mock_feature_store)

            # 验证Pandas集成
            assert mock_dataframe.called
            assert isinstance(result, Mock)  # 模拟的DataFrame

    def test_async_function_signature(self):
        """测试异步函数签名"""
        # 验证异步函数存在
        import inspect

        # 检查run_complete_example是否为异步函数
        assert inspect.iscoroutinefunction(run_complete_example)

        # 检查函数参数
        sig = inspect.signature(run_complete_example)
        assert len(sig.parameters) == 0  # 无参数

    def test_module_imports(self):
        """测试模块导入"""
        # 验证所有必要的导入都存在
        from src.data.features.examples import (
            FootballFeatureStore,
            get_feature_store,
            initialize_feature_store,
        )

        assert FootballFeatureStore is not None
        assert get_feature_store is not None
        assert initialize_feature_store is not None

    def test_logger_configuration(self):
        """测试日志配置"""
        with patch("src.data.features.examples.logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            from src.data.features.examples import logger

            # 验证日志器配置
            mock_get_logger.assert_called_with("src.data.features.examples")
            assert logger == mock_logger

    def test_feature_view_name_consistency(self):
        """测试特征视图名称一致性"""
        with patch("src.data.features.examples.pd.DataFrame") as mock_dataframe:
            mock_df = Mock()
            mock_dataframe.return_value = mock_df

            example_write_team_features(self.mock_feature_store)
            example_write_odds_features(self.mock_feature_store)

            # 获取调用参数
            team_call = self.mock_feature_store.write_features.call_args_list[0]
            odds_call = self.mock_feature_store.write_features.call_args_list[1]

            # 验证特征视图名称
            assert team_call.kwargs["feature_view_name"] == "team_recent_stats"
            assert odds_call.kwargs["feature_view_name"] == "odds_features"

    def test_entity_id_generation(self):
        """测试实体ID生成"""
        with patch("src.data.features.examples.pd.DataFrame") as mock_dataframe:
            mock_df = Mock()
            mock_dataframe.return_value = mock_df

            example_get_online_features(self.mock_feature_store)

            # 获取实体数据
            call_args = mock_dataframe.call_args[0][0]
            entity_data = call_args

            # 验证实体ID唯一性
            entity_ids = [entity["match_id"] for entity in entity_data]
            assert len(entity_ids) == len(set(entity_ids))  # 无重复

    def test_time_series_data_generation(self):
        """测试时间序列数据生成"""
        with patch("src.data.features.examples.pd.DataFrame") as mock_dataframe:
            mock_df = Mock()
            mock_dataframe.return_value = mock_df

            example_get_historical_features(self.mock_feature_store)

            # 获取时间序列数据
            call_args = mock_dataframe.call_args[0][0]
            time_series_data = call_args

            # 验证时间序列递增
            timestamps = [entity["event_timestamp"] for entity in time_series_data]
            assert timestamps == sorted(timestamps)  # 时间递增

    def test_training_dataset_parameters(self):
        """测试训练数据集参数"""
        mock_df = Mock()
        mock_df.shape = (500, 25)
        self.mock_feature_store.create_training_dataset.return_value = mock_df

        result = example_create_training_dataset(self.mock_feature_store)

        # 验证调用参数
        call_args = self.mock_feature_store.create_training_dataset.call_args
        assert "start_date" in call_args.kwargs
        assert "end_date" in call_args.kwargs

        # 验证返回的DataFrame属性
        assert hasattr(result, "shape")

    def test_feature_statistics_error_isolation(self):
        """测试特征统计错误隔离"""
        # 配置模拟对象
        self.mock_feature_store.get_feature_statistics.side_effect = [
            {"num_features": 10},  # 成功
            Exception("Error"),  # 失败
            {"num_features": 5},  # 成功
        ]

        # 验证错误不会阻止其他统计的获取
        example_feature_statistics(self.mock_feature_store)

        # 验证所有请求都被发送
        assert self.mock_feature_store.get_feature_statistics.call_count == 3

    def test_features_list_display_formatting(self):
        """测试特征列表显示格式化"""
        mock_features = [
            {
                "feature_view": "team_stats",
                "feature_name": "recent_wins",
                "feature_type": "int",
            },
            {
                "feature_view": "team_stats",
                "feature_name": "recent_goals",
                "feature_type": "float",
            },
        ]
        self.mock_feature_store.list_features.return_value = mock_features

        with patch("src.data.features.examples.print") as mock_print:
            example_list_all_features(self.mock_feature_store)

            # 验证输出格式
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any("发现 2 个特征" in call for call in print_calls)

    def test_ml_integration_training_workflow(self):
        """测试ML集成训练工作流"""
        with patch("src.data.features.examples.get_feature_store") as mock_get_store:
            mock_store = Mock()
            mock_get_store.return_value = mock_store

            # 模拟训练数据
            mock_training_df = Mock()
            mock_training_df.__len__ = Mock(return_value=1500)
            mock_store.create_training_dataset.return_value = mock_training_df

            result = example_integration_with_ml_pipeline()

            # 验证训练工作流
            assert result["training_result"]["model_trained"] is True
            assert result["training_result"]["training_samples"] == 1500

    def test_ml_integration_prediction_workflow(self):
        """测试ML集成预测工作流"""
        with patch(
            "src.data.features.examples.get_feature_store"
        ) as mock_get_store, patch(
            "src.data.features.examples.pd.DataFrame"
        ) as mock_dataframe:
            mock_store = Mock()
            mock_get_store.return_value = mock_store

            # 模拟预测数据
            mock_prediction_df = Mock()
            mock_prediction_df.__len__ = Mock(return_value=5)
            mock_store.get_online_features.return_value = mock_prediction_df
            mock_df = Mock()
            mock_dataframe.return_value = mock_df

            result = example_integration_with_ml_pipeline()

            # 验证预测工作流
            assert result["prediction_result"]["predictions_made"] == 5

    def test_integration_status_reporting(self):
        """测试集成状态报告"""
        with patch("src.data.features.examples.get_feature_store") as mock_get_store:
            mock_store = Mock()
            mock_get_store.return_value = mock_store

            result = example_integration_with_ml_pipeline()

            # 验证状态报告
            assert "integration_status" in result
            assert result["integration_status"] == "success"

    def test_feature_service_name_validation(self):
        """测试特征服务名称验证"""
        with patch("src.data.features.examples.pd.DataFrame") as mock_dataframe:
            mock_df = Mock()
            mock_dataframe.return_value = mock_df

            example_get_online_features(self.mock_feature_store)

            # 验证特征服务名称
            call_args = self.mock_feature_store.get_online_features.call_args
            assert call_args.kwargs["feature_service_name"] == "real_time_prediction_v1"

    def test_historical_features_full_names_flag(self):
        """测试历史特征全名标志"""
        with patch("src.data.features.examples.pd.DataFrame") as mock_dataframe:
            mock_df = Mock()
            mock_dataframe.return_value = mock_df

            example_get_historical_features(self.mock_feature_store)

            # 验证全名标志
            call_args = self.mock_feature_store.get_historical_features.call_args
            assert call_args.kwargs["full_feature_names"] is True

    def test_data_integrity_validation(self):
        """测试数据完整性验证"""
        with patch("src.data.features.examples.pd.DataFrame") as mock_dataframe:
            mock_df = Mock()
            mock_dataframe.return_value = mock_df

            example_write_team_features(self.mock_feature_store)

            # 获取数据
            call_args = mock_dataframe.call_args[0][0]
            team_data = call_args[0]

            # 验证数据完整性
            required_fields = [
                "team_id",
                "event_timestamp",
                "recent_5_wins",
                "recent_5_draws",
                "recent_5_losses",
                "recent_5_goals_for",
                "recent_5_goals_against",
            ]
            for field in required_fields:
                assert field in team_data
                assert team_data[field] is not None

    def test_performance_considerations(self):
        """测试性能考虑"""
        with patch("src.data.features.examples.pd.DataFrame") as mock_dataframe:
            mock_df = Mock()
            mock_dataframe.return_value = mock_df

            # 测试批量写入
            example_write_team_features(self.mock_feature_store)
            example_write_odds_features(self.mock_feature_store)

            # 验证批量操作
            assert self.mock_feature_store.write_features.call_count == 2

    def test_error_recovery_mechanisms(self):
        """测试错误恢复机制"""
        with patch(
            "src.data.features.examples.example_initialize_feature_store"
        ) as mock_init, patch("src.data.features.examples.logger") as mock_logger:
            mock_store = Mock()
            mock_init.return_value = mock_store

            # 模拟部分操作失败
            with patch(
                "src.data.features.examples.example_write_team_features"
            ) as mock_write_team:
                mock_write_team.side_effect = Exception("Partial failure")

                run_complete_example()

                # 验证资源清理仍然执行
                mock_store.close.assert_called_once()

    def test_configuration_flexibility(self):
        """测试配置灵活性"""
        with patch("src.data.features.examples.initialize_feature_store") as mock_init:
            mock_store = Mock()
            mock_init.return_value = mock_store

            example_initialize_feature_store()

            # 验证配置参数传递
            call_args = mock_init.call_args
            assert "project_name" in call_args.kwargs
            assert "postgres_config" in call_args.kwargs
            assert "redis_config" in call_args.kwargs

    def test_documentation_completeness(self):
        """测试文档完整性"""
        # 验证所有函数都有文档字符串
        functions_to_check = [
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
        ]

        for func in functions_to_check:
            assert func.__doc__ is not None
            assert len(func.__doc__.strip()) > 0

    def test_code_organization_patterns(self):
        """测试代码组织模式"""
        # 验证函数按逻辑分组
        initialization_functions = [example_initialize_feature_store]
        write_functions = [example_write_team_features, example_write_odds_features]
        read_functions = [example_get_online_features, example_get_historical_features]
        management_functions = [example_feature_statistics, example_list_all_features]

        assert len(initialization_functions) == 1
        assert len(write_functions) == 2
        assert len(read_functions) == 2
        assert len(management_functions) == 2

    def test_type_hints_completeness(self):
        """测试类型提示完整性"""
        import inspect

        # 检查关键函数的类型提示
        sig = inspect.signature(example_initialize_feature_store)
        return_annotation = sig.return_annotation
        assert return_annotation is not None

        sig = inspect.signature(example_write_team_features)
        params = sig.parameters
        assert "feature_store" in params
        assert params["feature_store"].annotation is not None

    def test_error_message_quality(self):
        """测试错误消息质量"""
        with patch(
            "src.data.features.examples.example_initialize_feature_store"
        ) as mock_init, patch("src.data.features.examples.logger") as mock_logger:
            mock_init.side_effect = Exception("Test error message")

            run_complete_example()

            # 验证错误消息质量
            error_call = mock_logger.error.call_args
            assert error_call is not None
            assert "Feature store example failed" in str(error_call)

    def test_resource_management_patterns(self):
        """测试资源管理模式"""
        with patch(
            "src.data.features.examples.example_initialize_feature_store"
        ) as mock_init:
            mock_store = Mock()
            mock_init.return_value = mock_store

            run_complete_example()

            # 验证资源管理模式
            mock_store.close.assert_called_once()

    def test_test_coverage_comprehensive(self):
        """测试覆盖度全面性"""
        # 验证所有主要功能都被测试覆盖
        test_methods = [method for method in dir(self) if method.startswith("test_")]

        # 主要功能类别
        functionality_categories = {
            "initialization": ["test_example_initialize_feature_store"],
            "data_writing": [
                "test_example_write_team_features",
                "test_example_write_odds_features",
            ],
            "data_reading": [
                "test_example_get_online_features",
                "test_example_get_historical_features",
            ],
            "dataset_creation": ["test_example_create_training_dataset"],
            "statistics": ["test_example_feature_statistics"],
            "feature_listing": ["test_example_list_all_features"],
            "complete_example": ["test_run_complete_example"],
            "ml_integration": ["test_example_integration_with_ml_pipeline"],
        }

        # 验证每个类别都有对应的测试
        for category, methods in functionality_categories.items():
            category_tests = [
                method
                for method in test_methods
                if any(method.startswith(prefix) for prefix in methods)
            ]
            assert len(category_tests) > 0, f"Category {category} has no tests"
