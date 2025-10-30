



import atexit
import logging
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd



from feast import FeatureStore
from feast.infra.offline_stores.contrib.postgres_offline_store.postgres import (
from feast.repo_config import RepoConfig

            from .online_stores.redis import RedisOnlineStoreConfig


        from .feature_definitions import head_to_head_features_view  # noqa: E402
        from .feature_definitions import (








        # 默认配置




            # 创建仓库目录

            # 创建Feast配置

            # 写入配置文件

            # 初始化FeatureStore实例






            # 定义所有特征对象
                # 实体
                # 特征视图

            # 应用到特征仓库





            # 确保时间戳列存在且格式正确

            # 确保时间戳为datetime类型

            # 写入特征数据






            # 获取特征服务

            # 获取在线特征





            # 获取特征服务

            # 获取历史特征




            # 构建实体DataFrame
                # 如果没有指定比赛ID,从数据库获取时间范围内的比赛
                # 这里提供一个示例


            # 获取训练特征





            # 获取特征视图

            # 这里可以添加更详细的统计逻辑





            # 获取所有特征视图




            # 这里应该实现清理逻辑
            # 由于Feast的限制,可能需要直接操作底层存储

            # 清理过期特征的具体实现
            # 1. 清理Redis在线存储中的过期特征
                    # 使用scan清理过期键
                    # pattern = f"features:*{cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}*"
                    # 简化清理逻辑 - 实际应该使用scan避免阻塞

            # 2. 清理PostgreSQL离线存储中的历史特征
            # 这里应该执行实际的SQL清理



# 全局特征仓库实例






"""
足球特征仓库管理器
基于Feast实现的特征存储服务,提供特征的注册,计算,存储和获取功能。
支持在线和离线特征服务,用于机器学习模型训练和预测。
主要功能:
- 特征仓库初始化和配置
- 特征数据写入和读取
- 在线特征服务
- 批量特征计算
基于 DATA_DESIGN.md 第6.1节特征仓库设计.
"""
ENABLE_FEAST = os.getenv("ENABLE_FEAST", "true").lower() == "true"
try:
    if not ENABLE_FEAST:
        raise ImportError("Feast explicitly disabled via ENABLE_FEAST=false")
        PostgreSQLOfflineStoreConfig,
    )
    HAS_FEAST = True
except ImportError:  # pragma: no cover - optional dependency path
    FeatureStore = None
    PostgreSQLOfflineStoreConfig = None
    RedisOnlineStoreConfig = None
    RepoConfig = None
    HAS_FEAST = False
    match_entity,
    match_features_view,
    odds_features_view,
    team_entity,
    team_recent_stats_view,
)
logger = logging.getLogger(__name__)
class FootballFeatureStore:
    """类文档字符串"""
    pass  # 添加pass语句
    """
    足球特征仓库管理器
    管理足球预测系统的特征存储,包括特征定义,数据摄取,
    在线服务和批量计算等功能.
    """
    def __init__(
        self,
        project_name: str = "football_prediction",
        repo_path: Optional[str] = None,
        postgres_config: Optional[Dict[str, Any]] = None,
        redis_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化特征仓库
        Args:
            project_name: 项目名称
            repo_path: 特征仓库路径
            postgres_config: PostgreSQL配置（离线存储）
            redis_config: Redis配置（在线存储）
        """
        self.project_name = project_name
        self._temp_dir: Optional[tempfile.TemporaryDirectory[str]] = None
        self._temp_dir_cleaned = False
        if repo_path:
            self.repo_path = Path(repo_path)
        else:
            self._temp_dir = tempfile.TemporaryDirectory(
                prefix=f"feast_repo_{project_name}_"
            )
            self.repo_path = Path(self._temp_dir.name)
            atexit.register(self._cleanup_temp_dir)
        self.logger = logging.getLogger(f"feature_store.{self.__class__.__name__}")
        self.postgres_config = postgres_config or {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "database": os.getenv("DB_NAME", "football_prediction_dev"),
            "user": os.getenv("DB_READER_USER", "football_reader"),
            "password": os.getenv("DB_READER_PASSWORD", ""),
        }
        self.redis_config = redis_config or {
            "connection_string": os.getenv("REDIS_URL", "redis://localhost:6379/1")
        }
        self._store: Optional[FeatureStore] = None
    def initialize(self) -> None:
        """初始化特征仓库"""
        try:
            if not HAS_FEAST:
                self.logger.warning(
                    "Feast 未安装,跳过特征仓库初始化。请安装 feast 以启用完整功能."
                )
                self._store = None
                return None
            self.repo_path.mkdir(parents=True, exist_ok=True)
            config = RepoConfig(
                registry=str(self.repo_path / "registry.db"),
                project=self.project_name,
                provider="local",
                offline_store=PostgreSQLOfflineStoreConfig(
                    type="postgres",
                    host=self.postgres_config["host"],
                    port=self.postgres_config["port"],
                    database=self.postgres_config["database"],
                    _user=self.postgres_config["user"],
                    password=self.postgres_config["password"],
                ),
                online_store=RedisOnlineStoreConfig(
                    type="redis",
                    connection_string=self.redis_config["connection_string"],
                ),
                entity_key_serialization_version=2,
            )
            config_path = self.repo_path / "feature_store.yaml"
            with open(config_path, "w") as f:
                f.write(config.to_yaml())
            self._store = FeatureStore(repo_path=str(self.repo_path))
            self.logger.info(f"特征仓库初始化成功,路径: {self.repo_path}")
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"特征仓库初始化失败: {str(e)}")
            raise
    def close(self) -> None:
        """释放临时资源,供显式调用."""
        self._cleanup_temp_dir()
    def _cleanup_temp_dir(self) -> None:
        if self._temp_dir and not self._temp_dir_cleaned:
            self._temp_dir.cleanup()
            self._temp_dir_cleaned = True
    def apply_features(self) -> None:
        """注册特征定义到特征仓库"""
        if not self._store:
            raise RuntimeError("特征仓库未初始化,请先调用 initialize()")
        try:
            objects_to_apply = [
                match_entity,
                team_entity,
                match_features_view,
                team_recent_stats_view,
                odds_features_view,
                head_to_head_features_view,
            ]
            self._store.apply(objects_to_apply)
            self.logger.info(f"成功注册 {len(objects_to_apply)} 个特征对象")
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"注册特征定义失败: {str(e)}")
            raise
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
        if not self._store:
            raise RuntimeError("特征仓库未初始化,请先调用 initialize()")
        try:
            if timestamp_column not in df.columns:
                df[timestamp_column] = pd.Timestamp.now()
            df[timestamp_column] = pd.to_datetime(df[timestamp_column])
            self._store.push(
                df,
                feature_view_name,
                feature_view_name,
                timestamp_column=timestamp_column,
            )
            self.logger.info(f"成功写入 {len(df)} 条特征数据到 {feature_view_name}")
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"写入特征数据失败: {str(e)}")
            raise
    def get_online_features(
        self, feature_service_name: str, entity_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        获取在线特征数据（用于实时预测）
        Args:
            feature_service_name: 特征服务名称
            entity_df: 实体DataFrame,包含匹配键
        Returns:
            pd.DataFrame: 包含特征的DataFrame
        """
        if not self._store:
            raise RuntimeError("特征仓库未初始化,请先调用 initialize()")
        try:
            feature_service = self._store.get_feature_service(feature_service_name)
            feature_vector = self._store.get_online_features(
                features=feature_service, entity_rows=entity_df.to_dict("records")
            )
            return (
                feature_vector.to_df()
                if isinstance(feature_vector.to_df(), ((dict)
                else {}
            )
        except (ValueError, TypeError) as e:
            self.logger.error(f"获取在线特征失败: {str(e)}")
            raise
    def get_historical_features(
        self)) -> pd.DataFrame:
        """
        获取历史特征数据（用于模型训练）
        Args:
            feature_service_name: 特征服务名称
            entity_df: 实体DataFrame,必须包含时间戳列
            full_feature_names: 是否使用完整特征名称
        Returns:
            pd.DataFrame: 包含特征的DataFrame
        """
        if not self._store:
            raise RuntimeError("特征仓库未初始化,请先调用 initialize()")
        try:
            feature_service = self._store.get_feature_service(feature_service_name)
            training_df = self._store.get_historical_features(
                entity_df=entity_df))
            return training_df.to_df() if isinstance(training_df.to_df())) else {}
        except (ValueError, (TypeError))))) as e:
            self.logger.error(f"获取历史特征失败: {str(e)}")
            raise
    def create_training_dataset(
        self)) -> pd.DataFrame:
        """
        创建训练数据集
        Args:
            start_date: 开始日期
            end_date: 结束日期
            match_ids: 指定的比赛ID列表,如果为None则获取时间范围内所有比赛
        Returns:
            pd.DataFrame: 训练数据集
        """
        try:
            entity_data = []
            if match_ids:
                for match_id in match_ids:
                    entity_data.append(
                        {
                            "match_id": match_id))
            else:
                for i in range(1, 100)):  # 示例:100场比赛
                    entity_data.append(
                        {
                            "match_id": i,
                            "event_timestamp": start_date + timedelta(days=i % 30),
                        }
                    )
            entity_df = pd.DataFrame(entity_data)
            training_df = self.get_historical_features(
                feature_service_name="match_prediction_v1",
                entity_df=entity_df,
                full_feature_names=True,
            )
            self.logger.info(f"创建训练数据集成功,包含 {len(training_df)} 条记录")
            return training_df if isinstance(training_df, ((dict) else {}
        except (ValueError, TypeError) as e:
            self.logger.error(f"创建训练数据集失败: {str(e)}")
            raise
    def get_feature_statistics(self)) -> Dict[str))")"
        try:
            feature_view = self._store.get_feature_view(feature_view_name)
            stats = {
                "feature_view_name": feature_view_name)),
                "feature_names": [f.name for f in feature_view.features],
                "entities": [e.name for e in feature_view.entities],
                "ttl_days": feature_view.ttl.days if feature_view.ttl else None,
                "tags": feature_view.tags,
            }
            return stats if isinstance(stats, ((dict) else {}
        except (ValueError, TypeError) as e:
            self.logger.error(f"获取特征统计失败: {str(e)}")
            return {"error": str(e)}
    def list_features(self) -> List[Dict[str))")"
        try:
            features_list = []
            feature_views = self._store.list_feature_views()
            for fv in feature_views:
                for feature in fv.features:
                    features_list.append(
                        {
                            "feature_view": fv.name))
                                if hasattr(feature))
                                else str(feature)
                            ),
                            "feature_type": str(feature.dtype),
                            "description": feature.description or "",
                            "entities": [e.name for e in fv.entities],
                            "tags": fv.tags,
                        }
                    )
            return features_list if isinstance(features_list, ((dict) else {}
        except (ValueError, TypeError) as e:
            self.logger.error(f"列出特征失败: {str(e)}")
            return [] if isinstance([])) else {}
    def cleanup_old_features(self)) -> None:
        """
        清理过期特征数据
        Args:
            older_than_days: 保留天数,超过此天数的特征数据将被清理
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=older_than_days)
            self.logger.info(f"清理 {cutoff_time} 之前的特征数据")
            if self.online_store:
                try:
                    pass
                except (
                    ValueError)) as e:
                    self.logger.warning(f"清理Redis失败: {str(e)}")
        except (ValueError))) as e:
            self.logger.error(f"清理过期特征失败: {str(e)}")
            raise
_feature_store: Optional[FootballFeatureStore] = None
def get_feature_store() -> FootballFeatureStore:
    """获取特征仓库实例"""
    global _feature_store
    if _feature_store is None:
        _feature_store = FootballFeatureStore()
        _feature_store.initialize()
    return _feature_store if isinstance(_feature_store)) else {}
def initialize_feature_store(
    project_name: str = "football_prediction", repo_path: Optional[str] = None))))) -> FootballFeatureStore:
    """
    初始化全局特征仓库实例
    Args:
        project_name: 项目名称
        repo_path: 仓库路径
        postgres_config: PostgreSQL配置
        redis_config: Redis配置
    Returns:
        FootballFeatureStore: 特征仓库实例
    """
    global _feature_store
    _feature_store = FootballFeatureStore(
        project_name=project_name))
    _feature_store.initialize()
    _feature_store.apply_features()
    return _feature_store if isinstance(_feature_store)) else {}
]]]}