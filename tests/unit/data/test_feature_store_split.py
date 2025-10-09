"""
测试拆分后的特征仓库
Test Split Feature Store
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

# 测试导入
def test_import_feature_store():
    """测试能否正常导入特征仓库模块"""
    from src.data.features.feature_store import FootballFeatureStore

    assert FootballFeatureStore is not None


def test_import_config_manager():
    """测试能否正常导入配置管理器"""
    from src.data.features.feature_store.config import FeatureStoreConfig, FeatureStoreConfigManager

    assert FeatureStoreConfig is not None
    assert FeatureStoreConfigManager is not None


def test_import_storage_manager():
    """测试能否正常导入存储管理器"""
    from src.data.features.feature_store.storage import FeatureStorageManager

    assert FeatureStorageManager is not None


def test_import_query_manager():
    """测试能否正常导入查询管理器"""
    from src.data.features.feature_store.query import FeatureQueryManager

    assert FeatureQueryManager is not None


def test_import_dataset_manager():
    """测试能否正常导入数据集管理器"""
    from src.data.features.feature_store.computation import FeatureDatasetManager

    assert FeatureDatasetManager is not None


def test_import_feature_definitions():
    """测试能否正常导入特征定义"""
    from src.data.features.feature_store.utils import (
        match_entity,
        team_entity,
        match_features_view,
        team_recent_stats_view,
        odds_features_view,
        head_to_head_features_view,
    )

    assert match_entity is not None
    assert team_entity is not None
    assert match_features_view is not None
    assert team_recent_stats_view is not None
    assert odds_features_view is not None
    assert head_to_head_features_view is not None


# 测试配置管理器
def test_feature_store_config():
    """测试特征仓库配置"""
    from src.data.features.feature_store.config import FeatureStoreConfig

    config = FeatureStoreConfig(
        project_name="test_project",
        repo_path="/tmp/test_repo"
    )

    assert config.project_name == "test_project"
    assert config.repo_path == "/tmp/test_repo"
    assert config.postgres_config is not None
    assert config.redis_config is not None


def test_feature_store_config_manager():
    """测试特征仓库配置管理器"""
    from src.data.features.feature_store.config import FeatureStoreConfigManager

    config_manager = FeatureStoreConfigManager()

    assert config_manager.config is not None
    assert config_manager.repo_path is not None
    assert not config_manager.is_temp_repo


def test_create_temp_repo():
    """测试创建临时仓库"""
    from src.data.features.feature_store.config import FeatureStoreConfigManager

    config_manager = FeatureStoreConfigManager()
    temp_repo = config_manager.create_temp_repo()

    assert temp_repo.exists()
    assert config_manager.is_temp_repo

    config_manager.cleanup_temp_repo()
    assert not temp_repo.exists()


# 测试主类
@patch('src.data.features.feature_store.feature_store.HAS_FEAST', False)
def test_football_feature_store_without_feast():
    """测试没有Feast时的特征仓库初始化"""
    from src.data.features.feature_store import FootballFeatureStore

    store = FootballFeatureStore(project_name="test")

    # 应该能够创建实例
    assert store is not None
    assert store.config_manager.config.project_name == "test"

    # 初始化应该成功但store为None
    store.initialize()
    assert not store.is_initialized


@patch('src.data.features.feature_store.feature_store.HAS_FEAST', True)
@patch('src.data.features.feature_store.feature_store.FeatureStore')
def test_football_feature_store_with_feast(mock_feature_store):
    """测试有Feast时的特征仓库初始化"""
    from src.data.features.feature_store import FootballFeatureStore

    # 模拟FeatureStore
    mock_store_instance = MagicMock()
    mock_feature_store.return_value = mock_store_instance

    store = FootballFeatureStore(project_name="test")

    # 初始化
    store.initialize()

    assert store.is_initialized
    assert store._storage_manager is not None
    assert store._query_manager is not None
    assert store._dataset_manager is not None


# 测试全局函数
def test_get_feature_store():
    """测试获取全局特征仓库"""
    from src.data.features.feature_store import get_feature_store

    with patch('src.data.features.feature_store.feature_store.HAS_FEAST', False):
        store = get_feature_store()

        assert store is not None
        assert isinstance(store, type(get_feature_store()))


def test_initialize_feature_store():
    """测试初始化全局特征仓库"""
    from src.data.features.feature_store import initialize_feature_store

    with patch('src.data.features.feature_store.feature_store.HAS_FEAST', False):
        store = initialize_feature_store(
            project_name="test_init",
            repo_path="/tmp/test_init"
        )

        assert store is not None
        assert store.config_manager.config.project_name == "test_init"


# 测试数据写入
def test_write_features():
    """测试写入特征数据"""
    import pandas as pd
    from src.data.features.feature_store.storage import FeatureStorageManager

    # 创建模拟的store
    mock_store = MagicMock()
    storage_manager = FeatureStorageManager(mock_store)

    # 创建测试数据
    df = pd.DataFrame({
        "match_id": [1, 2, 3],
        "feature_1": [0.1, 0.2, 0.3],
        "feature_2": [1, 2, 3],
    })

    # 写入特征
    storage_manager.write_features("test_view", df)

    # 验证调用
    mock_store.push.assert_called_once()


# 测试查询功能
def test_get_online_features():
    """测试获取在线特征"""
    import pandas as pd
    from src.data.features.feature_store.query import FeatureQueryManager

    # 创建模拟的store和storage_manager
    mock_store = MagicMock()
    mock_storage_manager = MagicMock()
    query_manager = FeatureQueryManager(mock_store, mock_storage_manager)

    # 模拟特征服务
    mock_feature_service = MagicMock()
    mock_storage_manager.get_feature_service.return_value = mock_feature_service

    # 模拟返回
    mock_feature_vector = MagicMock()
    mock_feature_vector.to_df.return_value = pd.DataFrame({"feature": [1, 2, 3]})
    mock_store.get_online_features.return_value = mock_feature_vector

    # 创建实体数据
    entity_df = pd.DataFrame({
        "match_id": [1, 2, 3],
    })

    # 获取在线特征
    result = query_manager.get_online_features("test_service", entity_df)

    assert isinstance(result, pd.DataFrame)
    mock_store.get_online_features.assert_called_once()


# 测试数据集创建
def test_create_training_dataset():
    """测试创建训练数据集"""
    from datetime import datetime
    from src.data.features.feature_store.computation import FeatureDatasetManager

    # 创建模拟的query_manager
    mock_query_manager = MagicMock()
    mock_query_manager.get_historical_features.return_value = pd.DataFrame({
        "feature_1": [0.1, 0.2, 0.3],
        "feature_2": [1, 2, 3],
    })

    dataset_manager = FeatureDatasetManager(mock_query_manager)

    # 创建训练数据集
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 12, 31)

    result = dataset_manager.create_training_dataset(
        start_date=start_date,
        end_date=end_date,
        match_ids=[1, 2, 3]
    )

    assert isinstance(result, pd.DataFrame)
    mock_query_manager.get_historical_features.assert_called_once()