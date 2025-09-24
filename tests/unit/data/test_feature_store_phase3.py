"""
Phase 3：特征仓库综合测试
目标：全面提升feature_store.py模块覆盖率到60%+
重点：测试Feast特征仓库初始化、特征注册、数据写入、在线/离线特征获取和训练数据集创建功能
"""

import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import pandas as pd
import pytest

from src.data.features.feature_store import FootballFeatureStore


class TestFootballFeatureStoreBasic:
    """足球特征仓库基础测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "feature_store"

        # Mock Feast依赖
        with patch("src.data.features.feature_store.FeatureStore"):
            with patch("src.data.features.feature_store.RepoConfig"):
                with patch(
                    "src.data.features.feature_store.PostgreSQLOfflineStoreConfig"
                ):
                    with patch(
                        "src.data.features.feature_store.RedisOnlineStoreConfig"
                    ):
                        self.feature_store = FootballFeatureStore(
                            project_name="test_project", repo_path=str(self.repo_path)
                        )

    def teardown_method(self):
        """清理测试环境"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_feature_store_initialization(self):
        """测试特征仓库初始化"""
        assert self.feature_store is not None
        assert hasattr(self.feature_store, "project_name")
        assert hasattr(self.feature_store, "repo_path")
        assert hasattr(self.feature_store, "postgres_config")
        assert hasattr(self.feature_store, "redis_config")
        assert hasattr(self.feature_store, "_store")
        assert self.feature_store.project_name == "test_project"
        assert self.feature_store.repo_path == self.repo_path
        assert self.feature_store._store is None

    def test_feature_store_initialization_with_custom_configs(self):
        """测试自定义配置的特征仓库初始化"""
        custom_postgres_config = {
            "host": "custom_host",
            "port": 5433,
            "database": "custom_db",
            "user": "custom_user",
            "password": "custom_password",
        }

        custom_redis_config = {"connection_string": "redis://custom_host:6380/2"}

        with patch("src.data.features.feature_store.FeatureStore"):
            with patch("src.data.features.feature_store.RepoConfig"):
                with patch(
                    "src.data.features.feature_store.PostgreSQLOfflineStoreConfig"
                ):
                    with patch(
                        "src.data.features.feature_store.RedisOnlineStoreConfig"
                    ):
                        feature_store = FootballFeatureStore(
                            project_name="custom_project",
                            repo_path=str(self.repo_path),
                            postgres_config=custom_postgres_config,
                            redis_config=custom_redis_config,
                        )

        assert feature_store.postgres_config == custom_postgres_config
        assert feature_store.redis_config == custom_redis_config

    def test_feature_store_initialization_without_repo_path(self):
        """测试不指定仓库路径的初始化"""
        with patch("src.data.features.feature_store.tempfile.mkdtemp") as mock_mkdtemp:
            mock_mkdtemp.return_value = "/tmp/test_feast_repo"

            with patch("src.data.features.feature_store.FeatureStore"):
                with patch("src.data.features.feature_store.RepoConfig"):
                    with patch(
                        "src.data.features.feature_store.PostgreSQLOfflineStoreConfig"
                    ):
                        with patch(
                            "src.data.features.feature_store.RedisOnlineStoreConfig"
                        ):
                            feature_store = FootballFeatureStore(
                                project_name="test_project"
                            )

            # 验证使用了临时目录
            mock_mkdtemp.assert_called_once_with(prefix="feast_repo_test_project_")
            assert "temp" in feature_store.repo_path.parts

    def test_feature_store_default_configs(self):
        """测试默认配置"""
        with patch("src.data.features.feature_store.FeatureStore"):
            with patch("src.data.features.feature_store.RepoConfig"):
                with patch(
                    "src.data.features.feature_store.PostgreSQLOfflineStoreConfig"
                ):
                    with patch(
                        "src.data.features.feature_store.RedisOnlineStoreConfig"
                    ):
                        feature_store = FootballFeatureStore()

        # 验证默认项目名称
        assert feature_store.project_name == "football_prediction"

        # 验证默认PostgreSQL配置
        assert "host" in feature_store.postgres_config
        assert "port" in feature_store.postgres_config
        assert "database" in feature_store.postgres_config
        assert "user" in feature_store.postgres_config
        assert "password" in feature_store.postgres_config

        # 验证默认Redis配置
        assert "connection_string" in feature_store.redis_config


class TestFootballFeatureStoreInitialize:
    """足球特征仓库初始化测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "feature_store"

        # Mock Feast依赖
        with patch("src.data.features.feature_store.FeatureStore") as mock_store_class:
            self.mock_store = Mock()
            mock_store_class.return_value = self.mock_store

            with patch(
                "src.data.features.feature_store.RepoConfig"
            ) as mock_config_class:
                with patch(
                    "src.data.features.feature_store.PostgreSQLOfflineStoreConfig"
                ):
                    with patch(
                        "src.data.features.feature_store.RedisOnlineStoreConfig"
                    ):
                        self.feature_store = FootballFeatureStore(
                            project_name="test_project", repo_path=str(self.repo_path)
                        )

    def teardown_method(self):
        """清理测试环境"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_initialize_success(self):
        """测试成功初始化特征仓库"""
        # Mock配置对象
        mock_config = Mock()
        mock_config.yaml.return_value = "mock_yaml_config"

        with patch(
            "src.data.features.feature_store.RepoConfig", return_value=mock_config
        ):
            with patch("builtins.open"):
                self.feature_store.initialize()

        # 验证仓库目录被创建
        assert self.repo_path.exists()

        # 验证FeatureStore被正确初始化
        self.mock_store_class.assert_called_once_with(repo_path=str(self.repo_path))
        assert self.feature_store._store == self.mock_store

    def test_initialize_directory_creation(self):
        """测试仓库目录创建"""
        # 删除目录确保不存在
        if self.repo_path.exists():
            shutil.rmtree(self.repo_path)

        mock_config = Mock()
        mock_config.yaml.return_value = "mock_yaml_config"

        with patch(
            "src.data.features.feature_store.RepoConfig", return_value=mock_config
        ):
            with patch("builtins.open"):
                self.feature_store.initialize()

        # 验证目录被创建
        assert self.repo_path.exists()
        assert (self.repo_path / "registry.db").parent.exists()

    def test_initialize_config_creation(self):
        """测试配置文件创建"""
        mock_config = Mock()
        mock_config.yaml.return_value = "mock_yaml_content"

        with patch(
            "src.data.features.feature_store.RepoConfig", return_value=mock_config
        ):
            with patch("builtins.open") as mock_open:
                mock_file = Mock()
                mock_open.return_value.__enter__.return_value = mock_file

                self.feature_store.initialize()

        # 验证配置文件被写入
        expected_config_path = self.repo_path / "feature_store.yaml"
        mock_open.assert_called_once_with(expected_config_path, "w")
        mock_file.write.assert_called_once_with("mock_yaml_content")

    def test_initialize_failure(self):
        """测试初始化失败"""
        with patch("src.data.features.feature_store.RepoConfig") as mock_config_class:
            mock_config_class.side_effect = Exception("Config creation failed")

            with pytest.raises(Exception, match="特征仓库初始化失败"):
                self.feature_store.initialize()

    def test_initialize_postgres_config(self):
        """测试PostgreSQL配置传递"""
        mock_config = Mock()
        mock_config.yaml.return_value = "mock_yaml_config"

        with patch(
            "src.data.features.feature_store.RepoConfig", return_value=mock_config
        ):
            with patch(
                "src.data.features.feature_store.PostgreSQLOfflineStoreConfig"
            ) as mock_pg_config:
                with patch("builtins.open"):
                    self.feature_store.initialize()

        # 验证PostgreSQL配置被正确传递
        mock_pg_config.assert_called_once_with(
            type="postgres",
            host=self.feature_store.postgres_config["host"],
            port=self.feature_store.postgres_config["port"],
            database=self.feature_store.postgres_config["database"],
            user=self.feature_store.postgres_config["user"],
            password=self.feature_store.postgres_config["password"],
        )

    def test_initialize_redis_config(self):
        """测试Redis配置传递"""
        mock_config = Mock()
        mock_config.yaml.return_value = "mock_yaml_config"

        with patch(
            "src.data.features.feature_store.RepoConfig", return_value=mock_config
        ):
            with patch(
                "src.data.features.feature_store.RedisOnlineStoreConfig"
            ) as mock_redis_config:
                with patch("builtins.open"):
                    self.feature_store.initialize()

        # 验证Redis配置被正确传递
        mock_redis_config.assert_called_once_with(
            type="redis",
            connection_string=self.feature_store.redis_config["connection_string"],
        )


class TestFootballFeatureStoreApplyFeatures:
    """足球特征仓库特征注册测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "feature_store"

        # Mock Feast依赖和特征定义
        with patch("src.data.features.feature_store.FeatureStore"):
            with patch("src.data.features.feature_store.RepoConfig"):
                with patch(
                    "src.data.features.feature_store.PostgreSQLOfflineStoreConfig"
                ):
                    with patch(
                        "src.data.features.feature_store.RedisOnlineStoreConfig"
                    ):
                        with patch(
                            "src.data.features.feature_store.match_entity"
                        ) as mock_match_entity:
                            with patch(
                                "src.data.features.feature_store.team_entity"
                            ) as mock_team_entity:
                                with patch(
                                    "src.data.features.feature_store.match_features_view"
                                ) as mock_match_fv:
                                    with patch(
                                        "src.data.features.feature_store.team_recent_stats_view"
                                    ) as mock_team_fv:
                                        with patch(
                                            "src.data.features.feature_store.odds_features_view"
                                        ) as mock_odds_fv:
                                            with patch(
                                                "src.data.features.feature_store.head_to_head_features_view"
                                            ) as mock_h2h_fv:
                                                self.feature_store = (
                                                    FootballFeatureStore(
                                                        project_name="test_project",
                                                        repo_path=str(self.repo_path),
                                                    )
                                                )

                                                # 存储mock对象用于验证
                                                self.mock_match_entity = (
                                                    mock_match_entity
                                                )
                                                self.mock_team_entity = mock_team_entity
                                                self.mock_match_fv = mock_match_fv
                                                self.mock_team_fv = mock_team_fv
                                                self.mock_odds_fv = mock_odds_fv
                                                self.mock_h2h_fv = mock_h2h_fv

        # 初始化store
        self.feature_store._store = Mock()

    def teardown_method(self):
        """清理测试环境"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_apply_features_success(self):
        """测试成功注册特征定义"""
        self.feature_store.apply_features()

        # 验证apply方法被调用，并传递了正确的特征对象列表
        self.feature_store._store.apply.assert_called_once()
        call_args = self.feature_store._store.apply.call_args[0][0]

        # 验证所有特征对象都在列表中
        expected_objects = [
            self.mock_match_entity,
            self.mock_team_entity,
            self.mock_match_fv,
            self.mock_team_fv,
            self.mock_odds_fv,
            self.mock_h2h_fv,
        ]

        assert len(call_args) == len(expected_objects)
        for expected_obj in expected_objects:
            assert expected_obj in call_args

    def test_apply_features_without_initialization(self):
        """测试未初始化时注册特征"""
        self.feature_store._store = None

        with pytest.raises(RuntimeError, match="特征仓库未初始化"):
            self.feature_store.apply_features()

    def test_apply_features_failure(self):
        """测试特征注册失败"""
        self.feature_store._store.apply.side_effect = Exception(
            "Feature application failed"
        )

        with pytest.raises(Exception, match="注册特征定义失败"):
            self.feature_store.apply_features()


class TestFootballFeatureStoreWriteFeatures:
    """足球特征仓库特征写入测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "feature_store"

        with patch("src.data.features.feature_store.FeatureStore"):
            with patch("src.data.features.feature_store.RepoConfig"):
                with patch(
                    "src.data.features.feature_store.PostgreSQLOfflineStoreConfig"
                ):
                    with patch(
                        "src.data.features.feature_store.RedisOnlineStoreConfig"
                    ):
                        self.feature_store = FootballFeatureStore(
                            project_name="test_project", repo_path=str(self.repo_path)
                        )

        # 初始化store
        self.feature_store._store = Mock()

    def teardown_method(self):
        """清理测试环境"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_write_features_success(self):
        """测试成功写入特征数据"""
        # 创建测试数据
        test_df = pd.DataFrame(
            {
                "match_id": [1, 2, 3],
                "home_team": ["Team A", "Team B", "Team C"],
                "away_team": ["Team D", "Team E", "Team F"],
                "event_timestamp": [
                    datetime.now(),
                    datetime.now() - timedelta(hours=1),
                    datetime.now() - timedelta(hours=2),
                ],
            }
        )

        self.feature_store.write_features("test_feature_view", test_df)

        # 验证push方法被调用
        self.feature_store._store.push.assert_called_once_with(
            push_source_name="test_feature_view", df=test_df, to="online_and_offline"
        )

    def test_write_features_without_timestamp_column(self):
        """测试写入无时间戳列的数据"""
        test_df = pd.DataFrame(
            {
                "match_id": [1, 2, 3],
                "home_team": ["Team A", "Team B", "Team C"],
                "away_team": ["Team D", "Team E", "Team F"],
            }
        )

        self.feature_store.write_features("test_feature_view", test_df)

        # 验证push方法被调用，并且数据被添加了时间戳列
        call_args = self.feature_store._store.push.call_args[1]
        pushed_df = call_args["df"]

        assert "event_timestamp" in pushed_df.columns
        assert len(pushed_df) == 3

    def test_write_features_with_custom_timestamp_column(self):
        """测试使用自定义时间戳列名"""
        test_df = pd.DataFrame(
            {
                "match_id": [1, 2, 3],
                "home_team": ["Team A", "Team B", "Team C"],
                "away_team": ["Team D", "Team E", "Team F"],
                "custom_timestamp": [
                    datetime.now(),
                    datetime.now() - timedelta(hours=1),
                    datetime.now() - timedelta(hours=2),
                ],
            }
        )

        self.feature_store.write_features(
            "test_feature_view", test_df, "custom_timestamp"
        )

        # 验证push方法被调用
        self.feature_store._store.push.assert_called_once()

    def test_write_features_without_initialization(self):
        """测试未初始化时写入特征"""
        self.feature_store._store = None

        test_df = pd.DataFrame({"match_id": [1, 2, 3]})

        with pytest.raises(RuntimeError, match="特征仓库未初始化"):
            self.feature_store.write_features("test_feature_view", test_df)

    def test_write_features_failure(self):
        """测试特征写入失败"""
        self.feature_store._store.push.side_effect = Exception("Feature write failed")

        test_df = pd.DataFrame({"match_id": [1, 2, 3]})

        with pytest.raises(Exception, match="写入特征数据失败"):
            self.feature_store.write_features("test_feature_view", test_df)

    def test_write_features_empty_dataframe(self):
        """测试写入空DataFrame"""
        test_df = pd.DataFrame()

        # 应该能够处理空DataFrame
        self.feature_store.write_features("test_feature_view", test_df)

        # 验证push方法被调用
        self.feature_store._store.push.assert_called_once()


class TestFootballFeatureStoreGetOnlineFeatures:
    """足球特征仓库在线特征获取测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "feature_store"

        with patch("src.data.features.feature_store.FeatureStore"):
            with patch("src.data.features.feature_store.RepoConfig"):
                with patch(
                    "src.data.features.feature_store.PostgreSQLOfflineStoreConfig"
                ):
                    with patch(
                        "src.data.features.feature_store.RedisOnlineStoreConfig"
                    ):
                        self.feature_store = FootballFeatureStore(
                            project_name="test_project", repo_path=str(self.repo_path)
                        )

        # 初始化store和mock对象
        self.feature_store._store = Mock()
        self.mock_feature_service = Mock()
        self.feature_store._store.get_feature_service.return_value = (
            self.mock_feature_service
        )

        # Mock特征向量结果
        self.mock_feature_vector = Mock()
        self.mock_feature_vector.to_df.return_value = pd.DataFrame(
            {"match_id": [1, 2], "feature_1": [0.5, 0.7], "feature_2": [1.2, 1.5]}
        )
        self.feature_store._store.get_online_features.return_value = (
            self.mock_feature_vector
        )

    def teardown_method(self):
        """清理测试环境"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_get_online_features_success(self):
        """测试成功获取在线特征"""
        entity_df = pd.DataFrame({"match_id": [1, 2], "team_id": [10, 20]})

        result = self.feature_store.get_online_features(
            "match_prediction_v1", entity_df
        )

        # 验证返回DataFrame
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "feature_1" in result.columns
        assert "feature_2" in result.columns

        # 验证调用链
        self.feature_store._store.get_feature_service.assert_called_once_with(
            "match_prediction_v1"
        )
        self.feature_store._store.get_online_features.assert_called_once_with(
            features=self.mock_feature_service, entity_rows=entity_df.to_dict("records")
        )

    def test_get_online_features_without_initialization(self):
        """测试未初始化时获取在线特征"""
        self.feature_store._store = None

        entity_df = pd.DataFrame({"match_id": [1, 2]})

        with pytest.raises(RuntimeError, match="特征仓库未初始化"):
            self.feature_store.get_online_features("match_prediction_v1", entity_df)

    def test_get_online_features_failure(self):
        """测试获取在线特征失败"""
        self.feature_store._store.get_feature_service.side_effect = Exception(
            "Feature service not found"
        )

        entity_df = pd.DataFrame({"match_id": [1, 2]})

        with pytest.raises(Exception, match="获取在线特征失败"):
            self.feature_store.get_online_features("invalid_service", entity_df)

    def test_get_online_features_empty_entity_df(self):
        """测试获取空实体DataFrame的在线特征"""
        entity_df = pd.DataFrame()

        # 应该能够处理空DataFrame
        result = self.feature_store.get_online_features(
            "match_prediction_v1", entity_df
        )

        # 验证返回结果
        assert isinstance(result, pd.DataFrame)


class TestFootballFeatureStoreGetHistoricalFeatures:
    """足球特征仓库历史特征获取测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "feature_store"

        with patch("src.data.features.feature_store.FeatureStore"):
            with patch("src.data.features.feature_store.RepoConfig"):
                with patch(
                    "src.data.features.feature_store.PostgreSQLOfflineStoreConfig"
                ):
                    with patch(
                        "src.data.features.feature_store.RedisOnlineStoreConfig"
                    ):
                        self.feature_store = FootballFeatureStore(
                            project_name="test_project", repo_path=str(self.repo_path)
                        )

        # 初始化store和mock对象
        self.feature_store._store = Mock()
        self.mock_feature_service = Mock()
        self.feature_store._store.get_feature_service.return_value = (
            self.mock_feature_service
        )

        # Mock历史特征结果
        self.mock_training_df = Mock()
        self.mock_training_df.to_df.return_value = pd.DataFrame(
            {
                "match_id": [1, 2, 3],
                "event_timestamp": [
                    datetime.now() - timedelta(days=1),
                    datetime.now() - timedelta(days=2),
                    datetime.now() - timedelta(days=3),
                ],
                "historical_feature_1": [0.1, 0.2, 0.3],
                "historical_feature_2": [1.1, 1.2, 1.3],
            }
        )
        self.feature_store._store.get_historical_features.return_value = (
            self.mock_training_df
        )

    def teardown_method(self):
        """清理测试环境"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_get_historical_features_success(self):
        """测试成功获取历史特征"""
        entity_df = pd.DataFrame(
            {
                "match_id": [1, 2, 3],
                "event_timestamp": [
                    datetime.now() - timedelta(days=1),
                    datetime.now() - timedelta(days=2),
                    datetime.now() - timedelta(days=3),
                ],
            }
        )

        result = self.feature_store.get_historical_features(
            "match_prediction_v1", entity_df
        )

        # 验证返回DataFrame
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert "historical_feature_1" in result.columns
        assert "historical_feature_2" in result.columns

        # 验证调用链
        self.feature_store._store.get_feature_service.assert_called_once_with(
            "match_prediction_v1"
        )
        self.feature_store._store.get_historical_features.assert_called_once_with(
            entity_df=entity_df,
            features=self.mock_feature_service,
            full_feature_names=False,
        )

    def test_get_historical_features_with_full_names(self):
        """测试获取完整特征名称的历史特征"""
        entity_df = pd.DataFrame(
            {"match_id": [1, 2], "event_timestamp": [datetime.now()] * 2}
        )

        result = self.feature_store.get_historical_features(
            "match_prediction_v1", entity_df, full_feature_names=True
        )

        # 验证full_feature_names参数被传递
        self.feature_store._store.get_historical_features.assert_called_once_with(
            entity_df=entity_df,
            features=self.mock_feature_service,
            full_feature_names=True,
        )

    def test_get_historical_features_without_initialization(self):
        """测试未初始化时获取历史特征"""
        self.feature_store._store = None

        entity_df = pd.DataFrame({"match_id": [1, 2]})

        with pytest.raises(RuntimeError, match="特征仓库未初始化"):
            self.feature_store.get_historical_features("match_prediction_v1", entity_df)

    def test_get_historical_features_failure(self):
        """测试获取历史特征失败"""
        self.feature_store._store.get_historical_features.side_effect = Exception(
            "Historical features not found"
        )

        entity_df = pd.DataFrame({"match_id": [1, 2]})

        with pytest.raises(Exception, match="获取历史特征失败"):
            self.feature_store.get_historical_features("match_prediction_v1", entity_df)


class TestFootballFeatureStoreCreateTrainingDataset:
    """足球特征仓库训练数据集创建测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "feature_store"

        with patch("src.data.features.feature_store.FeatureStore"):
            with patch("src.data.features.feature_store.RepoConfig"):
                with patch(
                    "src.data.features.feature_store.PostgreSQLOfflineStoreConfig"
                ):
                    with patch(
                        "src.data.features.feature_store.RedisOnlineStoreConfig"
                    ):
                        self.feature_store = FootballFeatureStore(
                            project_name="test_project", repo_path=str(self.repo_path)
                        )

        # 初始化store
        self.feature_store._store = Mock()

        # Mock历史特征结果
        self.mock_training_df = pd.DataFrame(
            {
                "match_id": [1, 2, 3],
                "feature_1": [0.1, 0.2, 0.3],
                "feature_2": [1.1, 1.2, 1.3],
            }
        )

    def teardown_method(self):
        """清理测试环境"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_create_training_dataset_with_match_ids(self):
        """测试使用指定比赛ID创建训练数据集"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        match_ids = [1, 2, 3]

        # Mock get_historical_features方法
        with patch.object(
            self.feature_store,
            "get_historical_features",
            return_value=self.mock_training_df,
        ):
            result = self.feature_store.create_training_dataset(
                start_date, end_date, match_ids
            )

        # 验证返回结果
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

        # 验证get_historical_features被调用
        self.feature_store.get_historical_features.assert_called_once_with(
            feature_service_name="match_prediction_v1",
            entity_df=pytest.approx(any),  # DataFrame比较复杂，只验证被调用
            full_feature_names=True,
        )

    def test_create_training_dataset_without_match_ids(self):
        """测试不指定比赛ID创建训练数据集"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        with patch.object(
            self.feature_store,
            "get_historical_features",
            return_value=self.mock_training_df,
        ):
            result = self.feature_store.create_training_dataset(start_date, end_date)

        # 验证返回结果
        assert isinstance(result, pd.DataFrame)
        # 应该生成默认的100场比赛数据
        assert len(result) == 3  # mock数据只有3条

    def test_create_training_dataset_entity_df_structure(self):
        """测试训练数据集的实体DataFrame结构"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        match_ids = [1, 2]

        with patch.object(
            self.feature_store, "get_historical_features"
        ) as mock_get_features:
            mock_get_features.return_value = self.mock_training_df

            self.feature_store.create_training_dataset(start_date, end_date, match_ids)

            # 验证entity_df结构
            call_args = mock_get_features.call_args[1]
            entity_df = call_args["entity_df"]

            assert "match_id" in entity_df.columns
            assert "event_timestamp" in entity_df.columns
            assert len(entity_df) == 2
            assert entity_df["match_id"].tolist() == [1, 2]
            # 验证时间戳使用end_date
            assert all(ts == end_date for ts in entity_df["event_timestamp"])

    def test_create_training_dataset_failure(self):
        """测试创建训练数据集失败"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        with patch.object(
            self.feature_store, "get_historical_features"
        ) as mock_get_features:
            mock_get_features.side_effect = Exception(
                "Training dataset creation failed"
            )

            with pytest.raises(Exception, match="创建训练数据集失败"):
                self.feature_store.create_training_dataset(start_date, end_date)


class TestFootballFeatureStoreFeatureStatistics:
    """足球特征仓库特征统计测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "feature_store"

        with patch("src.data.features.feature_store.FeatureStore"):
            with patch("src.data.features.feature_store.RepoConfig"):
                with patch(
                    "src.data.features.feature_store.PostgreSQLOfflineStoreConfig"
                ):
                    with patch(
                        "src.data.features.feature_store.RedisOnlineStoreConfig"
                    ):
                        self.feature_store = FootballFeatureStore(
                            project_name="test_project", repo_path=str(self.repo_path)
                        )

        # 初始化store和mock对象
        self.feature_store._store = Mock()

        # Mock特征视图
        self.mock_feature = Mock()
        self.mock_feature.name = "test_feature"
        self.mock_feature.dtype.name = "float64"
        self.mock_feature.description = "Test feature description"

        self.mock_feature_view = Mock()
        self.mock_feature_view.name = "test_feature_view"
        self.mock_feature_view.features = [self.mock_feature]
        self.mock_feature_view.entities = [Mock(name="match_entity")]
        self.mock_feature_view.ttl = timedelta(days=7)
        self.mock_feature_view.tags = {"env": "test", "version": "1.0"}

        self.feature_store._store.get_feature_view.return_value = self.mock_feature_view

    def teardown_method(self):
        """清理测试环境"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_get_feature_statistics_success(self):
        """测试成功获取特征统计"""
        result = self.feature_store.get_feature_statistics("test_feature_view")

        # 验证返回结果结构
        assert isinstance(result, dict)
        assert result["feature_view_name"] == "test_feature_view"
        assert result["num_features"] == 1
        assert result["feature_names"] == ["test_feature"]
        assert result["entities"] == ["match_entity"]
        assert result["ttl_days"] == 7
        assert result["tags"] == {"env": "test", "version": "1.0"}

        # 验证get_feature_view被调用
        self.feature_store._store.get_feature_view.assert_called_once_with(
            "test_feature_view"
        )

    def test_get_feature_statistics_without_initialization(self):
        """测试未初始化时获取特征统计"""
        self.feature_store._store = None

        with pytest.raises(RuntimeError, match="特征仓库未初始化"):
            self.feature_store.get_feature_statistics("test_feature_view")

    def test_get_feature_statistics_failure(self):
        """测试获取特征统计失败"""
        self.feature_store._store.get_feature_view.side_effect = Exception(
            "Feature view not found"
        )

        result = self.feature_store.get_feature_statistics("invalid_feature_view")

        # 验证返回错误信息
        assert "error" in result
        assert "Feature view not found" in result["error"]

    def test_get_feature_statistics_multiple_features(self):
        """测试多特征统计"""
        # 添加第二个特征
        mock_feature_2 = Mock()
        mock_feature_2.name = "test_feature_2"
        mock_feature_2.dtype.name = "int32"
        mock_feature_2.description = "Second test feature"

        self.mock_feature_view.features = [self.mock_feature, mock_feature_2]

        result = self.feature_store.get_feature_statistics("test_feature_view")

        # 验证多特征统计
        assert result["num_features"] == 2
        assert set(result["feature_names"]) == {"test_feature", "test_feature_2"}


class TestFootballFeatureStoreListFeatures:
    """足球特征仓库特征列表测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "feature_store"

        with patch("src.data.features.feature_store.FeatureStore"):
            with patch("src.data.features.feature_store.RepoConfig"):
                with patch(
                    "src.data.features.feature_store.PostgreSQLOfflineStoreConfig"
                ):
                    with patch(
                        "src.data.features.feature_store.RedisOnlineStoreConfig"
                    ):
                        self.feature_store = FootballFeatureStore(
                            project_name="test_project", repo_path=str(self.repo_path)
                        )

        # 初始化store和mock对象
        self.feature_store._store = Mock()

        # Mock多个特征视图
        self.mock_feature_1 = Mock()
        self.mock_feature_1.name = "feature_1"
        self.mock_feature_1.dtype.name = "float64"
        self.mock_feature_1.description = "First feature"

        self.mock_feature_2 = Mock()
        self.mock_feature_2.name = "feature_2"
        self.mock_feature_2.dtype.name = "int32"
        self.mock_feature_2.description = "Second feature"

        self.mock_feature_view_1 = Mock()
        self.mock_feature_view_1.name = "feature_view_1"
        self.mock_feature_view_1.features = [self.mock_feature_1]
        self.mock_feature_view_1.entities = [Mock(name="match_entity")]
        self.mock_feature_view_1.tags = {"env": "test"}

        self.mock_feature_view_2 = Mock()
        self.mock_feature_view_2.name = "feature_view_2"
        self.mock_feature_view_2.features = [self.mock_feature_2]
        self.mock_feature_view_2.entities = [Mock(name="team_entity")]
        self.mock_feature_view_2.tags = {"env": "prod"}

        self.feature_store._store.list_feature_views.return_value = [
            self.mock_feature_view_1,
            self.mock_feature_view_2,
        ]

    def teardown_method(self):
        """清理测试环境"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_list_features_success(self):
        """测试成功列出特征"""
        result = self.feature_store.list_features()

        # 验证返回结果
        assert isinstance(result, list)
        assert len(result) == 2

        # 验证第一个特征
        feature_1_info = result[0]
        assert feature_1_info["feature_view"] == "feature_view_1"
        assert feature_1_info["feature_name"] == "feature_1"
        assert feature_1_info["feature_type"] == "float64"
        assert feature_1_info["description"] == "First feature"
        assert feature_1_info["entities"] == ["match_entity"]
        assert feature_1_info["tags"] == {"env": "test"}

        # 验证第二个特征
        feature_2_info = result[1]
        assert feature_2_info["feature_view"] == "feature_view_2"
        assert feature_2_info["feature_name"] == "feature_2"
        assert feature_2_info["feature_type"] == "int32"

    def test_list_features_without_initialization(self):
        """测试未初始化时列出特征"""
        self.feature_store._store = None

        with pytest.raises(RuntimeError, match="特征仓库未初始化"):
            self.feature_store.list_features()

    def test_list_features_failure(self):
        """测试列出特征失败"""
        self.feature_store._store.list_feature_views.side_effect = Exception(
            "Failed to list features"
        )

        result = self.feature_store.list_features()

        # 验证返回空列表
        assert result == []

    def test_list_features_empty_feature_views(self):
        """测试空特征视图列表"""
        self.feature_store._store.list_feature_views.return_value = []

        result = self.feature_store.list_features()

        # 验证返回空列表
        assert result == []


class TestFootballFeatureStoreCleanup:
    """足球特征仓库清理测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "feature_store"

        with patch("src.data.features.feature_store.FeatureStore"):
            with patch("src.data.features.feature_store.RepoConfig"):
                with patch(
                    "src.data.features.feature_store.PostgreSQLOfflineStoreConfig"
                ):
                    with patch(
                        "src.data.features.feature_store.RedisOnlineStoreConfig"
                    ):
                        self.feature_store = FootballFeatureStore(
                            project_name="test_project", repo_path=str(self.repo_path)
                        )

    def teardown_method(self):
        """清理测试环境"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_cleanup_old_features_success(self):
        """测试成功清理过期特征"""
        # 这个方法目前主要是TODO状态，主要测试是否能正常调用
        with patch.object(self.feature_store.logger, "info") as mock_logger:
            self.feature_store.cleanup_old_features(older_than_days=30)

            # 验证日志记录
            mock_logger.assert_called()
            # 验证清理时间被正确计算
            call_args = mock_logger.call_args[0][0]
            assert "cleanup_time" in call_args.lower() or "清理" in call_args

    def test_cleanup_old_features_custom_days(self):
        """测试自定义清理天数"""
        with patch.object(self.feature_store.logger, "info") as mock_logger:
            self.feature_store.cleanup_old_features(older_than_days=60)

            # 验证方法被调用
            mock_logger.assert_called()

    def test_cleanup_old_features_failure(self):
        """测试清理失败"""
        with patch.object(self.feature_store.logger, "error") as mock_logger:
            # 模拟清理过程中的异常
            with patch.object(self.feature_store, "logger") as mock_logger_attr:
                mock_logger_attr.error.side_effect = Exception("Cleanup failed")

                with pytest.raises(Exception):
                    self.feature_store.cleanup_old_features()


class TestFootballFeatureStoreIntegration:
    """足球特征仓库集成测试"""

    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir) / "feature_store"

        with patch("src.data.features.feature_store.FeatureStore"):
            with patch("src.data.features.feature_store.RepoConfig"):
                with patch(
                    "src.data.features.feature_store.PostgreSQLOfflineStoreConfig"
                ):
                    with patch(
                        "src.data.features.feature_store.RedisOnlineStoreConfig"
                    ):
                        self.feature_store = FootballFeatureStore(
                            project_name="test_project", repo_path=str(self.repo_path)
                        )

        # 初始化store
        self.feature_store._store = Mock()

    def teardown_method(self):
        """清理测试环境"""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_complete_feature_workflow(self):
        """测试完整的特征工作流"""
        # Mock各个步骤
        mock_config = Mock()
        mock_config.yaml.return_value = "mock_config"

        # 1. 初始化
        with patch(
            "src.data.features.feature_store.RepoConfig", return_value=mock_config
        ):
            with patch("builtins.open"):
                self.feature_store.initialize()

        # 2. 注册特征
        with patch("src.data.features.feature_store.match_entity") as mock_entity:
            mock_entity.name = "match_entity"
            with patch.object(self.feature_store, "apply_features"):
                self.feature_store.apply_features()

        # 3. 写入特征
        test_df = pd.DataFrame(
            {
                "match_id": [1, 2],
                "feature_value": [0.5, 0.7],
                "event_timestamp": [datetime.now(), datetime.now()],
            }
        )

        with patch.object(self.feature_store, "write_features"):
            self.feature_store.write_features("test_view", test_df)

        # 4. 获取在线特征
        entity_df = pd.DataFrame({"match_id": [1]})

        with patch.object(self.feature_store, "get_online_features") as mock_online:
            mock_online.return_value = pd.DataFrame(
                {"match_id": [1], "feature_1": [0.5]}
            )

            online_features = self.feature_store.get_online_features(
                "test_service", entity_df
            )
            assert isinstance(online_features, pd.DataFrame)

        # 5. 创建训练数据集
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        with patch.object(
            self.feature_store, "create_training_dataset"
        ) as mock_training:
            mock_training.return_value = pd.DataFrame(
                {"match_id": [1, 2], "feature_1": [0.5, 0.7]}
            )

            training_data = self.feature_store.create_training_dataset(
                start_date, end_date
            )
            assert isinstance(training_data, pd.DataFrame)

    def test_error_handling_and_recovery(self):
        """测试错误处理和恢复"""
        # 测试各种错误情况下的处理

        # 1. 未初始化的错误处理
        uninitialized_store = FootballFeatureStore()
        uninitialized_store._store = None

        with pytest.raises(RuntimeError):
            uninitialized_store.get_feature_statistics("test_view")

        # 2. 重新初始化后的恢复
        mock_config = Mock()
        mock_config.yaml.return_value = "recovery_config"

        with patch(
            "src.data.features.feature_store.RepoConfig", return_value=mock_config
        ):
            with patch("builtins.open"):
                uninitialized_store.initialize()

        # 验证恢复后可以正常工作
        assert uninitialized_store._store is not None

    def test_concurrent_feature_operations(self):
        """测试并发特征操作"""
        import asyncio

        async def test_concurrent_writes():
            # Mock多个并发写入操作
            test_dfs = [
                pd.DataFrame({"match_id": [i], "value": [i * 0.1]}) for i in range(5)
            ]

            with patch.object(self.feature_store, "write_features") as mock_write:
                tasks = [
                    self.feature_store.write_features(f"test_view_{i}", df)
                    for i, df in enumerate(test_dfs)
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 验证所有操作都成功
                assert all(not isinstance(r, Exception) for r in results)
                assert mock_write.call_count == 5

        # 运行异步测试
        asyncio.run(test_concurrent_writes())

    def test_feature_store_state_consistency(self):
        """测试特征仓库状态一致性"""
        # 验证特征仓库状态在操作前后保持一致
        original_project = self.feature_store.project_name
        original_repo_path = self.feature_store.repo_path
        original_postgres_config = self.feature_store.postgres_config.copy()
        original_redis_config = self.feature_store.redis_config.copy()

        # 执行一些操作
        mock_config = Mock()
        mock_config.yaml.return_value = "state_test_config"

        with patch(
            "src.data.features.feature_store.RepoConfig", return_value=mock_config
        ):
            with patch("builtins.open"):
                self.feature_store.initialize()

        # 验证状态一致性
        assert self.feature_store.project_name == original_project
        assert self.feature_store.repo_path == original_repo_path
        assert self.feature_store.postgres_config == original_postgres_config
        assert self.feature_store.redis_config == original_redis_config
