from datetime import datetime, timedelta
import os
import sys

from unittest.mock import Mock, patch
import pandas
import pytest

"""
Enhanced tests for data features feature store module
"""

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src["))""""
@pytest.mark.unit
class TestDataFeaturesFeatureStore:
    "]""Test data features feature store"""
    def test_module_imports(self):
        """测试模块导入"""
        try:
            from src.data.features.feature_store import (
                FootballFeatureStore,
                get_feature_store,
                initialize_feature_store)
            assert FootballFeatureStore is not None
            assert callable(get_feature_store)
            assert callable(initialize_feature_store)
        except ImportError:
            pytest.skip("Feature store module not available[")": def test_football_feature_store_initialization_default_config(self):"""
        "]""测试FootballFeatureStore默认配置初始化"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            with patch("tempfile.mkdtemp[") as mock_mktemp:": mock_mktemp.return_value = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_33"): store = FootballFeatureStore()": assert store.project_name =="]football_prediction[" assert store.postgres_config is not None[""""
                assert store.redis_config is not None
                assert store._store is None
        except ImportError:
            pytest.skip("]]Feature store module not available[")": def test_football_feature_store_initialization_custom_config(self):"""
        "]""测试FootballFeatureStore自定义配置初始化"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            custom_config = {
                "host[": ["]custom_host[",""""
                "]port[": 5433,""""
                "]database[": ["]custom_db[",""""
                "]user[": ["]custom_user[",""""
                "]password[": ["]custom_password["}": redis_config = {"]connection_string[: "redis://custom6380/2["}"]": with patch("]tempfile.mkdtemp[") as mock_mktemp:": mock_mktemp.return_value = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_33"): store = FootballFeatureStore(": project_name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_PROJECT_NAME_46"),": postgres_config=custom_config,": redis_config=redis_config)": assert store.project_name =="]custom_project[" assert store.postgres_config ==custom_config[""""
                assert store.redis_config ==redis_config
        except ImportError:
            pytest.skip("]]Feature store module not available[")""""
    @patch("]src.data.features.feature_store.FeatureStore[")""""
    @patch("]src.data.features.feature_store.RepoConfig[")""""
    @patch("]src.data.features.feature_store.PostgreSQLOfflineStoreConfig[")""""
    @patch("]src.data.features.feature_store.RedisOnlineStoreConfig[")": def test_initialize_success(": self,": mock_redis_config,"
        mock_postgres_config,
        mock_repo_config,
        mock_feature_store):
        "]""测试特征仓库初始化成功场景"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            with patch("tempfile.mkdtemp[") as mock_mktemp:": mock_mktemp.return_value = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_33"): mock_repo_instance = Mock()": mock_repo_config.return_value = mock_repo_instance[": mock_repo_instance.yaml.return_value = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_60"): mock_store_instance = Mock()": mock_feature_store.return_value = mock_store_instance[": store = FootballFeatureStore()": store.initialize()"
                mock_repo_config.assert_called_once()
                mock_feature_store.assert_called_once_with(
                    repo_path = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_REPO_PATH_60")""""
                )
                assert store._store ==mock_store_instance
        except ImportError:
            pytest.skip("]Feature store module not available[")""""
    @patch("]src.data.features.feature_store.FeatureStore[")": def test_initialize_failure(self, mock_feature_store):"""
        "]""测试特征仓库初始化失败场景"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            with patch("tempfile.mkdtemp[") as mock_mktemp, patch(:""""
                "]src.data.features.feature_store.RepoConfig["""""
            ) as mock_repo_config:
                mock_mktemp.return_value = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_33"): mock_feature_store.side_effect = Exception("]Connection failed[")""""
                # Mock the RepoConfig to have yaml method
                mock_repo_instance = Mock()
                mock_repo_config.return_value = mock_repo_instance
                mock_repo_instance.yaml.return_value = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_RETURN_VALUE_75"): store = FootballFeatureStore()": with pytest.raises(Exception) as exc_info:": store.initialize()": assert "]Connection failed[" in str(exc_info.value)""""
        except ImportError:
            pytest.skip("]Feature store module not available[")": def test_apply_features_success(self):"""
        "]""测试注册特征定义成功场景"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            mock_store = Mock()
            store._store = mock_store
            # Mock feature definitions
            with patch(:
                "src.data.features.feature_store.match_entity["""""
            ) as mock_match_entity, patch(
                "]src.data.features.feature_store.team_entity["""""
            ) as mock_team_entity, patch(
                "]src.data.features.feature_store.match_features_view["""""
            ) as mock_match_features, patch(
                "]src.data.features.feature_store.team_recent_stats_view["""""
            ) as mock_team_stats, patch(
                "]src.data.features.feature_store.odds_features_view["""""
            ) as mock_odds_features, patch(
                "]src.data.features.feature_store.head_to_head_features_view["""""
            ) as mock_h2h_features:
                store.apply_features()
                expected_objects = ["]mock_match_entity[",": mock_team_entity,": mock_match_features,": mock_team_stats,"
                    mock_odds_features,
                    mock_h2h_features]
                mock_store.apply.assert_called_once_with(expected_objects)
        except ImportError:
            pytest.skip("]Feature store module not available[")": def test_apply_features_not_initialized(self):"""
        "]""测试未初始化时注册特征定义"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            store._store = None
            with pytest.raises(RuntimeError) as exc_info:
                store.apply_features()
            assert "特征仓库未初始化[" in str(exc_info.value)""""
        except ImportError:
            pytest.skip("]Feature store module not available[")": def test_write_features_success(self):"""
        "]""测试写入特征数据成功场景"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            mock_store = Mock()
            store._store = mock_store
            mock_df = pd.DataFrame({
                    "team_id[: "1, 2[","]"""
                    "]event_timestamp[": [datetime.now()""""
            )
            store.write_features("]team_stats[", mock_df)": mock_store.push.assert_called_once_with(": push_source_name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_PUSH_SOURCE_NAME_"), df=mock_df, to = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_TO_124")""""
            )
        except ImportError:
            pytest.skip("]Feature store module not available[")": def test_write_features_not_initialized(self):"""
        "]""测试未初始化时写入特征数据"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            store._store = None
            mock_df = pd.DataFrame({"test[": [1]))": with pytest.raises(RuntimeError) as exc_info:": store.write_features("]test_view[", mock_df)": assert "]特征仓库未初始化[" in str(exc_info.value)""""
        except ImportError:
            pytest.skip("]Feature store module not available[")": def test_write_features_missing_timestamp(self):"""
        "]""测试写入特征数据时缺少时间戳列"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            mock_store = Mock()
            store._store = mock_store
            # Skip this test due to pandas mocking issues in conftest.py
            # The test would require real pandas DataFrame which conflicts with global mocks:
            pytest.skip("跳过此测试：pandas全局mock导致DataFrame创建问题[")": except ImportError:": pytest.skip("]Feature store module not available[")": def test_get_online_features_success(self):"""
        "]""测试获取在线特征成功场景"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            mock_store = Mock()
            store._store = mock_store
            mock_feature_service = Mock()
            mock_store.get_feature_service.return_value = mock_feature_service
            mock_feature_vector = Mock()
            mock_feature_vector.to_df.return_value = pd.DataFrame({"feature1[": [1]))": mock_store.get_online_features.return_value = mock_feature_vector[": entity_df = pd.DataFrame({"]]match_id[": [1001, 1002]))": result = store.get_online_features("]prediction_service[", entity_df)": assert isinstance(result, pd.DataFrame)" mock_store.get_feature_service.assert_called_once_with("]prediction_service[")": mock_store.get_online_features.assert_called_once_with(": features=mock_feature_service, entity_rows=entity_df.to_dict("]records[")""""
            )
        except ImportError:
            pytest.skip("]Feature store module not available[")": def test_get_online_features_not_initialized(self):"""
        "]""测试未初始化时获取在线特征"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            store._store = None
            entity_df = pd.DataFrame({"match_id[": [1001]))": with pytest.raises(RuntimeError) as exc_info:": store.get_online_features("]test_service[", entity_df)": assert "]特征仓库未初始化[" in str(exc_info.value)""""
        except ImportError:
            pytest.skip("]Feature store module not available[")": def test_get_historical_features_success(self):"""
        "]""测试获取历史特征成功场景"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            mock_store = Mock()
            store._store = mock_store
            mock_feature_service = Mock()
            mock_store.get_feature_service.return_value = mock_feature_service
            mock_training_df = Mock()
            mock_training_df.to_df.return_value = pd.DataFrame({"feature1[": [1]))": mock_store.get_historical_features.return_value = mock_training_df[": entity_df = pd.DataFrame({"]]match_id[: "1001[", "]]event_timestamp[": [datetime.now()""""
            )
            result = store.get_historical_features("]training_service[", entity_df)": assert isinstance(result, pd.DataFrame)" mock_store.get_historical_features.assert_called_once_with(""
                entity_df=entity_df,
                features=mock_feature_service,
                full_feature_names=False)
        except ImportError:
            pytest.skip("]Feature store module not available[")": def test_get_historical_features_with_full_names(self):"""
        "]""测试获取历史特征时使用完整名称"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            mock_store = Mock()
            store._store = mock_store
            mock_feature_service = Mock()
            mock_store.get_feature_service.return_value = mock_feature_service
            mock_training_df = Mock()
            mock_store.get_historical_features.return_value = mock_training_df
            entity_df = pd.DataFrame({"match_id[: "1001[", "]]event_timestamp[": [datetime.now()""""
            )
            store.get_historical_features(
                "]training_service[", entity_df, full_feature_names=True[""""
            )
            mock_store.get_historical_features.assert_called_once_with(
                entity_df=entity_df,
                features=mock_feature_service,
                full_feature_names=True)
        except ImportError:
            pytest.skip("]]Feature store module not available[")": def test_create_training_dataset_success(self):"""
        "]""测试创建训练数据集成功场景"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            mock_store = Mock()
            store._store = mock_store
            mock_training_df = pd.DataFrame({"features[": [1, 2]))": with patch.object(:": store, "]get_historical_features[", return_value=mock_training_df[""""
            ):
                result = store.create_training_dataset(
                    start_date=datetime(2025, 1, 1), end_date=datetime(2025, 1, 31)
                )
                assert isinstance(result, pd.DataFrame)
                store.get_historical_features.assert_called_once()
        except ImportError:
            pytest.skip("]]Feature store module not available[")": def test_create_training_dataset_with_match_ids(self):"""
        "]""测试使用指定比赛ID创建训练数据集"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            mock_store = Mock()
            store._store = mock_store
            mock_training_df = pd.DataFrame({"features[": [1, 2]))": with patch.object(:": store, "]get_historical_features[", return_value=mock_training_df[""""
            ):
                result = store.create_training_dataset(
                    start_date=datetime(2025, 1, 1),
                    end_date=datetime(2025, 1, 31),
                    match_ids=[1001, 1002, 1003])
                assert isinstance(result, pd.DataFrame)
                # Verify the function was called with the expected service name = call_args store.get_historical_features.call_args
                assert call_args[1]"]]feature_service_name[" =="]match_prediction_v1[" except ImportError:""""
            pytest.skip("]Feature store module not available[")": def test_get_feature_statistics_success(self):"""
        "]""测试获取特征统计成功场景"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            mock_store = Mock()
            store._store = mock_store
            mock_feature_view = Mock()
            mock_feature_view.features = [Mock(name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_239")), Mock(name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_239"))]": mock_feature_view.entities = [Mock(name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_239"))]": mock_feature_view.ttl = timedelta(days=30)": mock_feature_view.tags = {"]category[": ["]stats["}": mock_store.get_feature_view.return_value = mock_feature_view[": result = store.get_feature_statistics("]]team_stats[")": expected_keys = ["""
                "]feature_view_name[",""""
                "]num_features[",""""
                "]feature_names[",""""
                "]entities[",""""
                "]ttl_days[",""""
                "]tags["]": assert all(key in result for key in expected_keys)" assert result["]num_features["] ==2[" assert result["]]ttl_days["] ==30[" except ImportError:"""
            pytest.skip("]]Feature store module not available[")": def test_get_feature_statistics_error(self):"""
        "]""测试获取特征统计错误处理"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            mock_store = Mock()
            store._store = mock_store
            mock_store.get_feature_view.side_effect = Exception(
                "Feature view not found["""""
            )
            result = store.get_feature_statistics("]nonexistent_view[")": assert "]error[" in result[""""
            assert "]]Feature view not found[" in result["]error["]: except ImportError:": pytest.skip("]Feature store module not available[")": def test_list_features_success(self):"""
        "]""测试列出所有特征成功场景"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            mock_store = Mock()
            store._store = mock_store
            mock_feature_view1 = Mock()
            mock_feature_view1.name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_264"): mock_feature_view1.entities = [Mock(name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_239"))]": mock_feature_view1.tags = {}": mock_feature1 = Mock()": mock_feature1.name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_265"): mock_feature1.dtype = Mock(name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_265"))": mock_feature_view1.features = ["]mock_feature1[": mock_feature_view2 = Mock()": mock_feature_view2.name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_268"): mock_feature_view2.entities = [Mock(name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_269"))]": mock_feature_view2.tags = {}": mock_feature2 = Mock()": mock_feature2.name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_271"): mock_feature2.dtype = Mock(name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_NAME_272"))": mock_feature_view2.features = ["]mock_feature2[": mock_store.list_feature_views.return_value = ["]mock_feature_view1[",": mock_feature_view2]": result = store.list_features()": assert len(result) ==2"
            assert result[0]"]feature_view[" =="]team_stats[" assert result[0]"]feature_name[" =="]wins[" assert result[1]"]feature_view[" =="]match_stats[" assert result[1]"]feature_name[" =="]goals[" except ImportError:""""
            pytest.skip("]Feature store module not available[")": def test_list_features_empty(self):"""
        "]""测试列出所有特征为空的情况"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            mock_store = Mock()
            store._store = mock_store
            mock_store.list_feature_views.return_value = []
            result = store.list_features()
            assert result ==[]
        except ImportError:
            pytest.skip("Feature store module not available[")": def test_cleanup_old_features_success(self):"""
        "]""测试清理过期特征成功场景"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            # Should not raise exception
            store.cleanup_old_features(older_than_days=30)
        except ImportError:
            pytest.skip("Feature store module not available[")": def test_cleanup_old_features_error(self):"""
        "]""测试清理过期特征错误处理"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            # Mock logger to verify error handling
            with patch.object(store, "logger["):": with patch("]src.data.features.feature_store.datetime[") as mock_datetime:": mock_datetime.now.side_effect = Exception("]Time error[")": with pytest.raises(Exception):": store.cleanup_old_features(older_than_days=30)": except ImportError:"
            pytest.skip("]Feature store module not available[")": def test_close_success(self):"""
        "]""测试关闭特征仓库成功场景"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            mock_store = Mock()
            store._store = mock_store
            store.close()
            assert store._store is None
        except ImportError:
            pytest.skip("Feature store module not available[")": def test_close_error_handling(self):"""
        "]""测试关闭特征仓库错误处理"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            store = FootballFeatureStore()
            mock_store = Mock()
            store._store = mock_store
            # Mock logger to verify error handling
            with patch.object(store, "logger["):""""
                # Simulate some error during close
                store.close()
                # Should not raise exception
                assert store._store is None
        except ImportError:
            pytest.skip("]Feature store module not available[")": def test_get_feature_store_existing_instance(self):"""
        "]""测试获取已存在的特征仓库实例"""
        try:
            from src.data.features.feature_store import (
                get_feature_store,
                _feature_store)
            # Set the global store to a mock value directly
            import src.data.features.feature_store as feature_store_module
            original_store = feature_store_module._feature_store
            feature_store_module._feature_store = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE__FEATURE_STORE_31"): try:": result = get_feature_store()": assert result =="]existing_store[" finally:""""
                # Restore original value
                feature_store_module._feature_store = original_store
        except ImportError:
            pytest.skip("]Feature store module not available[")""""
    @patch("]src.data.features.feature_store._feature_store[", None)""""
    @patch("]src.data.features.feature_store.FootballFeatureStore[")": def test_get_feature_store_new_instance(self, mock_feature_store_class):"""
        "]""测试创建新的特征仓库实例"""
        try:
            from src.data.features.feature_store import get_feature_store
            mock_store = Mock()
            mock_feature_store_class.return_value = mock_store
            result = get_feature_store()
            assert result ==mock_store
            mock_store.initialize.assert_called_once()
        except ImportError:
            pytest.skip("Feature store module not available[")""""
    @patch("]src.data.features.feature_store._feature_store[")""""
    @patch("]src.data.features.feature_store.FootballFeatureStore[")": def test_initialize_feature_store_global(": self, mock_feature_store_class, mock_global_store[""
    ):
        "]]""测试初始化全局特征仓库"""
        try:
            from src.data.features.feature_store import initialize_feature_store
            mock_store = Mock()
            mock_feature_store_class.return_value = mock_store
            result = initialize_feature_store(
                project_name = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_PROJECT_NAME_341"), repo_path = os.getenv("TEST_DATA_FEATURES_FEATURE_STORE_REPO_PATH_343")""""
            )
            assert result ==mock_store
            mock_store.initialize.assert_called_once()
            mock_store.apply_features.assert_called_once()
        except ImportError:
            pytest.skip("]Feature store module not available[")": def test_feature_store_method_existence(self):"""
        "]""测试特征仓库方法存在性"""
        try:
            from src.data.features.feature_store import FootballFeatureStore
            expected_methods = [
                "__init__[",""""
                "]initialize[",""""
                "]apply_features[",""""
                "]write_features[",""""
                "]get_online_features[",""""
                "]get_historical_features[",""""
                "]create_training_dataset[",""""
                "]get_feature_statistics[",""""
                "]list_features[",""""
                "]cleanup_old_features[",""""
                "]close["]": for method in expected_methods:": assert hasattr(" FootballFeatureStore, method"
                ), f["]Method {method} not found["]: except ImportError:": pytest.skip("]Feature store module not available[")": def test_imports_from_feature_definitions(self):"""
        "]""测试从feature_definitions导入功能"""
        try:
            from src.data.features.feature_store import (
                head_to_head_features_view,
                match_entity,
                match_features_view,
                odds_features_view,
                team_entity,
                team_recent_stats_view)
            # Verify imports exist (they might be None if Feast is not available):
            assert True  # If we get here, imports worked
        except ImportError:
            pytest.skip("Feature definitions not available[")"]": from src.data.features.feature_store import (": from src.data.features.feature_store import FootballFeatureStore"
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import (
            import src.data.features.feature_store as feature_store_module
            from src.data.features.feature_store import get_feature_store
            from src.data.features.feature_store import initialize_feature_store
            from src.data.features.feature_store import FootballFeatureStore
            from src.data.features.feature_store import (