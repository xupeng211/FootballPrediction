"""
"""




    """获取特征仓库实例"""


    """


    """




特征仓库模块
Feature Store Module
# 全局特征仓库实例
_feature_store: Optional[FootballFeatureStore] = None
def get_feature_store() -> FootballFeatureStore:
    global _feature_store
    if _feature_store is None:
        _feature_store = FootballFeatureStore()
        _feature_store.initialize()
    return _feature_store
def initialize_feature_store(
    project_name: str = "football_prediction",
    repo_path: Optional[str] = None,
    postgres_config: Optional[Dict[str, Any]] = None,
    redis_config: Optional[Dict[str, Any]] = None,
) -> FootballFeatureStore:
    初始化全局特征仓库实例
    Args:
        project_name: 项目名称
        repo_path: 仓库路径
        postgres_config: PostgreSQL配置
        redis_config: Redis配置
    Returns:
        FootballFeatureStore: 特征仓库实例
    global _feature_store
    _feature_store = FootballFeatureStore(
        project_name=project_name,
        repo_path=repo_path,
        postgres_config=postgres_config,
        redis_config=redis_config, Dict, Any
    )
    _feature_store.initialize()
    _feature_store.apply_features()
    return _feature_store
__all__ = [
    "FootballFeatureStore",
    "FeatureStoreConfig",
    "FeatureStoreConfigManager",
    "FeatureStorageManager",
    "FeatureQueryManager",
    "FeatureDatasetManager",
    "get_feature_store",
    "initialize_feature_store",
]