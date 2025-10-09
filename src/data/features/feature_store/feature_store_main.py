"""
足球特征商店主类
Football Feature Store Main Class
"""

from typing import Any, Dict, List, Optional
import pandas as pd
from datetime import datetime

from src.core.logging_system import get_logger
from .config import FeatureStoreConfigManager, FeatureStoreConfig
from .storage import FeatureStorageManager
from .query import FeatureQueryManager
from .computation import FeatureDatasetManager
from .utils import (
    HAS_FEAST,
    match_entity,
    team_entity,
    match_features_view,
    team_recent_stats_view,
    odds_features_view,
    head_to_head_features_view,
)

logger = get_logger(__name__)


class FootballFeatureStore:
    """足球特征商店类"""

    def __init__(
        self,
        project_name: str = "football_prediction",
        repo_path: Optional[str] = None,
        postgres_config: Optional[Dict[str, Any]] = None,
        redis_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化特征商店

        Args:
            project_name: 项目名称
            repo_path: 仓库路径
            postgres_config: PostgreSQL配置
            redis_config: Redis配置
        """
        # 创建配置管理器
        config = FeatureStoreConfig(
            project_name=project_name,
            repo_path=repo_path,
            postgres_config=postgres_config,
            redis_config=redis_config,
        )
        self.config_manager = FeatureStoreConfigManager(config)

        # 初始化组件
        self._store = None
        self._storage_manager = None
        self._query_manager = None
        self._dataset_manager = None

    def initialize(self) -> None:
        """初始化特征仓库"""
        try:
            if not HAS_FEAST:
                self.logger.warning(
                    "Feast 未安装，跳过特征仓库初始化。请安装 feast 以启用完整功能。"
                )
                self._store = None
                return

            # 获取Feast配置
            feast_config = self.config_manager.get_feast_config()

            # 保存配置文件
            self.config_manager.save_feast_config()

            # 初始化FeatureStore实例
            try:
                from feast import FeatureStore
                self._store = FeatureStore(repo_path=self.config_manager.repo_path)
            except ImportError:
                logger.error("无法导入 FeatureStore，请确保 Feast 已正确安装")
                return

            # 初始化管理器
            self._storage_manager = FeatureStorageManager(self._store)
            self._query_manager = FeatureQueryManager(self._store, self._storage_manager)
            self._dataset_manager = FeatureDatasetManager(self._query_manager)

            self.logger.info(f"特征仓库初始化成功，路径: {self.config_manager.repo_path}")

        except Exception as e:
            self.logger.error(f"特征仓库初始化失败: {str(e)}")
            raise

    def close(self) -> None:
        """释放临时资源，供显式调用。"""
        self.config_manager.cleanup_temp_repo()

    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._store is not None

    def apply_features(self) -> None:
        """注册特征定义到特征仓库"""
        if not self.is_initialized:
            raise RuntimeError("特征仓库未初始化，请先调用 initialize()")

        # 定义所有特征对象
        objects_to_apply = [
            # 实体
            match_entity,
            team_entity,
            # 特征视图
            match_features_view,
            team_recent_stats_view,
            odds_features_view,
            head_to_head_features_view,
        ]

        self._storage_manager.apply_feature_definitions(objects_to_apply)

    def write_features(
        self,
        feature_view_name: str,
        df: pd.DataFrame,
        timestamp_column: str = "event_timestamp",
    ) -> None:
        """
        写入特征数据到特征仓库

        Args:
            feature_view_name: 特征视图名称
            df: 特征数据DataFrame
            timestamp_column: 时间戳列名
        """
        if not self.is_initialized:
            raise RuntimeError("特征仓库未初始化，请先调用 initialize()")

        self._storage_manager.write_features(
            feature_view_name=feature_view_name,
            df=df,
            timestamp_column=timestamp_column,
        )

    def get_online_features(
        self, feature_service_name: str, entity_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        获取在线特征数据（用于实时预测）

        Args:
            feature_service_name: 特征服务名称
            entity_df: 实体DataFrame，包含匹配键

        Returns:
            pd.DataFrame: 包含特征的DataFrame
        """
        if not self.is_initialized:
            raise RuntimeError("特征仓库未初始化，请先调用 initialize()")

        return self._query_manager.get_online_features(
            feature_service_name=feature_service_name,
            entity_df=entity_df,
        )

    def get_historical_features(
        self,
        feature_service_name: str,
        entity_df: pd.DataFrame,
        full_feature_names: bool = False,
    ) -> pd.DataFrame:
        """
        获取历史特征数据（用于模型训练）

        Args:
            feature_service_name: 特征服务名称
            entity_df: 实体DataFrame，必须包含时间戳列
            full_feature_names: 是否使用完整特征名称

        Returns:
            pd.DataFrame: 包含特征的DataFrame
        """
        if not self.is_initialized:
            raise RuntimeError("特征仓库未初始化，请先调用 initialize()")

        return self._query_manager.get_historical_features(
            feature_service_name=feature_service_name,
            entity_df=entity_df,
            full_feature_names=full_feature_names,
        )

    def create_training_dataset(
        self,
        start_date: datetime,
        end_date: datetime,
        match_ids: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """
        创建训练数据集

        Args:
            start_date: 开始日期
            end_date: 结束日期
            match_ids: 指定的比赛ID列表，如果为None则获取时间范围内所有比赛

        Returns:
            pd.DataFrame: 训练数据集
        """
        if not self.is_initialized:
            raise RuntimeError("特征仓库未初始化，请先调用 initialize()")

        return self._dataset_manager.create_training_dataset(
            start_date=start_date,
            end_date=end_date,
            match_ids=match_ids,
        )

    def get_feature_statistics(self, feature_view_name: str) -> Dict[str, Any]:
        """
        获取特征统计信息

        Args:
            feature_view_name: 特征视图名称

        Returns:
            Dict: 特征统计信息
        """
        if not self.is_initialized:
            raise RuntimeError("特征仓库未初始化，请先调用 initialize()")

        return self._query_manager.get_feature_statistics(
            feature_view_name=feature_view_name
        )

    def list_features(self) -> List[Dict[str, Any]]:
        """
        列出所有特征

        Returns:
            List[Dict]: 特征列表信息
        """
        if not self.is_initialized:
            raise RuntimeError("特征仓库未初始化，请先调用 initialize()")

        return self._query_manager.list_features()

    def cleanup_old_features(self, older_than_days: int = 30) -> None:
        """
        清理过期特征数据

        Args:
            older_than_days: 保留天数，超过此天数的特征数据将被清理
        """
        if not self.is_initialized:
            raise RuntimeError("特征仓库未初始化，请先调用 initialize()")

        self._storage_manager.cleanup_old_features(older_than_days=older_than_days)