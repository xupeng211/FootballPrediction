from datetime import datetime, timedelta

from src.data.features.feature_store import (
from unittest.mock import Mock, patch
import pandas
import pytest

"""
Test suite for data features modules
"""

    FootballFeatureStore,
    get_feature_store,
    initialize_feature_store)
@pytest.fixture
def feature_store():
    """Create a feature store instance for testing"""
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix="feast_repo_test_[")": store = FootballFeatureStore(project_name="]test_project[", repo_path=temp_dir)": return store[": def test_feature_store_initialization():""
    "]]""Test initialization of FootballFeatureStore"""
    store = FootballFeatureStore(project_name="test_project[")": assert store is not None[" assert store.project_name =="]]test_project[" assert store.repo_path is not None[""""
def test_feature_store_initialize(feature_store):
    "]]""Test feature store initialization"""
    # Mock the Feast configuration and FeatureStore
    with patch("src.data.features.feature_store.RepoConfig[") as mock_config, patch(:""""
        "]src.data.features.feature_store.FeatureStore["""""
    ) as mock_store, patch("]builtins.open[", create = True) as mock_open[""""
        # Create a mock config object that behaves like the newer Feast API
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        # Mock the FeatureStore constructor
        mock_store_instance = Mock()
        mock_store.return_value = mock_store_instance
        # Mock file operations
        mock_open.return_value.__enter__.return_value = Mock()
        # This should not raise any exceptions
        feature_store.initialize()
        # Check that the required methods were called
        assert mock_config.called
        assert mock_store.called
        assert mock_open.called
def test_feature_store_apply_features(feature_store):
    "]]""Test applying features to the store"""
    # Create a mock store that has been initialized
    with patch.object(feature_store, "_store[") as mock_store:": feature_store.apply_features()": mock_store.apply.assert_called_once()": def test_feature_store_apply_features_not_initialized(feature_store):"
    "]""Test applying features without initialization"""
    feature_store._store = None
    with pytest.raises(RuntimeError, match = "特征仓库未初始化[")": feature_store.apply_features()": def test_write_features(feature_store):""
    "]""Test writing features to the store"""
    # Create sample data
    sample_data = pd.DataFrame({
            "match_id[: "1, 2, 3[","]"""
            "]feature_value[: "10, 20, 30[","]"""
            "]event_timestamp[": [datetime.now()""""
    )
    with patch.object(feature_store, "]_store[") as mock_store:": feature_store.write_features("]test_feature_view[", sample_data)": mock_store.push.assert_called_once()": def test_write_features_not_initialized(feature_store):""
    "]""Test writing features without initialization"""
    sample_data = pd.DataFrame({"match_id[: "1, 2, 3[", "]]feature_value[": [10, 20, 30]))": feature_store._store = None[": with pytest.raises(RuntimeError, match = "]]特征仓库未初始化[")": feature_store.write_features("]test_feature_view[", sample_data)": def test_get_online_features(feature_store):"""
    "]""Test getting online features"""
    # Create sample entity data
    entity_data = pd.DataFrame({"match_id[: "1, 2, 3[", "]]team_id[": [10, 20, 30]))": with patch.object(feature_store, "]_store[") as mock_store:": mock_feature_service = Mock()": mock_store.get_feature_service.return_value = mock_feature_service[": mock_feature_vector = Mock()"
        mock_store.get_online_features.return_value = mock_feature_vector
        mock_feature_vector.to_df.return_value = pd.DataFrame({"]]feature1[": [1, 2, 3]))": result = feature_store.get_online_features("]test_service[", entity_data)": assert isinstance(result, pd.DataFrame)" def test_get_online_features_not_initialized(feature_store):""
    "]""Test getting online features without initialization"""
    entity_data = pd.DataFrame({"match_id[": [1, 2, 3]))": feature_store._store = None[": with pytest.raises(RuntimeError, match = "]]特征仓库未初始化[")": feature_store.get_online_features("]test_service[", entity_data)": def test_get_historical_features(feature_store):"""
    "]""Test getting historical features"""
    # Create sample entity data with timestamp = entity_data pd.DataFrame({
            "match_id[: "1, 2, 3[","]"""
            "]event_timestamp[": [datetime.now()""""
    )
    with patch.object(feature_store, "]_store[") as mock_store:": mock_feature_service = Mock()": mock_store.get_feature_service.return_value = mock_feature_service[": mock_training_df = Mock()"
        mock_store.get_historical_features.return_value = mock_training_df
        mock_training_df.to_df.return_value = pd.DataFrame({"]]feature1[": [1, 2, 3]))": result = feature_store.get_historical_features("]test_service[", entity_data)": assert isinstance(result, pd.DataFrame)" def test_get_historical_features_not_initialized(feature_store):""
    "]""Test getting historical features without initialization"""
    entity_data = pd.DataFrame({"match_id[: "1, 2, 3[", "]]event_timestamp[": [datetime.now()""""
    )
    feature_store._store = None
    with pytest.raises(RuntimeError, match = "]特征仓库未初始化[")": feature_store.get_historical_features("]test_service[", entity_data)": def test_create_training_dataset(feature_store):"""
    "]""Test creating a training dataset"""
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    with patch.object(feature_store, "_store["), patch.object(:": feature_store, "]get_historical_features["""""
    ) as mock_get_hist:
        mock_get_hist.return_value = pd.DataFrame({"]feature1[": [1, 2, 3]))": result = feature_store.create_training_dataset(start_date, end_date)": assert isinstance(result, pd.DataFrame)" def test_get_feature_statistics(feature_store):"
    "]""Test getting feature statistics"""
    with patch.object(feature_store, "_store[") as mock_store:": mock_feature_view = Mock()": mock_feature_view.features = [Mock(), Mock()]  # 2 features[": mock_feature_view.entities = [Mock(), Mock()]  # 2 entities"
        mock_feature_view.ttl = timedelta(days=30)
        mock_feature_view.tags = {"]]team[": ["]data["}": mock_store.get_feature_view.return_value = mock_feature_view[": stats = feature_store.get_feature_statistics("]]test_view[")": assert "]feature_view_name[" in stats[""""
        assert stats["]]num_features["] ==2[" def test_get_feature_statistics_not_initialized(feature_store):"""
    "]]""Test getting feature statistics without initialization"""
    feature_store._store = None
    with pytest.raises(RuntimeError, match = "特征仓库未初始化[")": feature_store.get_feature_statistics("]test_view[")": def test_list_features(feature_store):"""
    "]""Test listing all features"""
    with patch.object(feature_store, "_store[") as mock_store:""""
        # Mock feature views
        mock_feature_view1 = Mock()
        mock_feature_view1.name = "]view1[": mock_feature_view1.features = [Mock(), Mock()]": mock_feature_view1.entities = [Mock()]": mock_feature_view1.tags = {"]team[": ["]data["}": mock_feature_view1.features[0].name = "]feature1[": mock_feature_view1.features[0].dtype.name = "]INT32[": mock_feature_view1.features[0].description = "]First feature[": mock_feature_view1.features[1].name = "]feature2[": mock_feature_view1.features[1].dtype.name = "]FLOAT[": mock_feature_view1.features[1].description = "]Second feature[": mock_store.list_feature_views.return_value = ["]mock_feature_view1[": features_list = feature_store.list_features()": assert isinstance(features_list, list)" assert len(features_list) ==2  # 2 features from 1 view[""
def test_list_features_not_initialized(feature_store):
    "]]""Test listing features without initialization"""
    feature_store._store = None
    with pytest.raises(RuntimeError, match = "特征仓库未初始化[")": feature_store.list_features()": def test_cleanup_old_features(feature_store):""
    "]""Test cleaning up old features"""
    # This method currently has a TODO but should not raise exceptions
    feature_store.cleanup_old_features(older_than_days=30)
def test_close_feature_store(feature_store):
    """Test closing the feature store"""
    feature_store._store = Mock()
    feature_store.close()
    assert feature_store._store is None
def test_close_feature_store_with_none(feature_store):
    """Test closing a feature store that is already closed"""
    feature_store._store = None
    feature_store.close()  # Should not raise any exceptions
def test_get_feature_store_singleton():
    """Test the singleton pattern of get_feature_store"""
    store1 = get_feature_store()
    store2 = get_feature_store()
    # They should be the same instance
    assert store1 is store2
def test_initialize_feature_store():
    """Test initialization of feature store with specific parameters"""
    with patch("src.data.features.feature_store.FootballFeatureStore[") as mock_class:": mock_instance = Mock()": mock_class.return_value = mock_instance[": result = initialize_feature_store(project_name="]]test_project[",": postgres_config = {"]host[" "]localhost["},": redis_config = {"]connection_string[": [redis://localhost6379]))""""
        # Verify the instance methods were called
        assert mock_instance.initialize.called
        assert mock_instance.apply_features.called
        assert result is mock_instance
def test_write_features_with_auto_timestamp(feature_store):
    "]""Test writing features with automatic timestamp generation"""
    # Create a properly mocked DataFrame
    mock_df = Mock()
    mock_df.columns = ["match_id[", "]feature_value["]  # No timestamp column initially[": mock_df.__contains__ = Mock(return_value=False)  # timestamp_column not in df[": with patch.object(feature_store, "]]]_store[") as mock_store:": feature_store.write_features("]test_feature_view[", mock_df)""""
        # Should have added a timestamp column
        mock_df.__setitem__.assert_called()
        mock_store.push.assert_called_once()
def test_get_feature_statistics_with_error_handling(feature_store):
    "]""Test getting feature statistics with error handling"""
    with patch.object(feature_store, "_store[") as mock_store:": mock_store.get_feature_view.side_effect = Exception("]Feature view not found[")": stats = feature_store.get_feature_statistics("]nonexistent_view[")": assert "]error[" in stats[""""
def test_list_features_with_error_handling(feature_store):
    "]]""Test listing features with error handling"""
    with patch.object(feature_store, "_store[") as mock_store:": mock_store.list_feature_views.side_effect = Exception("]List features failed[")": features_list = feature_store.list_features()": assert features_list ==[]" def test_create_training_dataset_with_match_ids(feature_store):"
    "]""Test creating training dataset with specific match IDs"""
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    match_ids = [1, 2, 3, 4, 5]
    with patch.object(feature_store, "_store["), patch.object(:": feature_store, "]get_historical_features["""""
    ) as mock_get_hist:
        mock_get_hist.return_value = pd.DataFrame({"]feature1[": [1, 2, 3, 4, 5]))": result = feature_store.create_training_dataset(": start_date, end_date, match_ids=match_ids[""
        )
        assert isinstance(result, pd.DataFrame)
def test_feature_store_initialization_with_custom_config():
    "]]""Test feature store initialization with custom configuration"""
    custom_postgres = {
        "host[": ["]custom_host[",""""
        "]port[": 5433,""""
        "]database[": ["]custom_db[",""""
        "]user[": ["]custom_user[",""""
        "]password[": ["]custom_password["}": custom_redis = {"]connection_string[: "redis://custom_host6380/1["}"]": store = FootballFeatureStore(": project_name="]custom_project[","]": postgres_config=custom_postgres,": redis_config=custom_redis)"
    assert store.postgres_config ==custom_postgres
    assert store.redis_config ==custom_redis
    import tempfile