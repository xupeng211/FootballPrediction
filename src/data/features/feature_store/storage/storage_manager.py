"""
特征仓库存储管理模块
Feature Store Storage Management Module
"""



logger = get_logger(__name__)


class FeatureStorageManager:
    """特征存储管理器"""

    def __init__(self, store):
        """
        初始化存储管理器

        Args:
            store: Feast FeatureStore 实例
        """
        self.store = store
        self.logger = logger

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
        try:
            # 确保时间戳列存在且格式正确
            if timestamp_column not in df.columns:
                df[timestamp_column] = pd.Timestamp.now()

            # 确保时间戳为datetime类型
            df[timestamp_column] = pd.to_datetime(df[timestamp_column])

            # 写入特征数据
            self.store.push(
                df,
                feature_view_name,
                feature_view_name,
                timestamp_column=timestamp_column,
            )

            self.logger.info(f"成功写入 {len(df)} 条特征数据到 {feature_view_name}")

        except Exception as e:
            self.logger.error(f"写入特征数据失败: {str(e)}")
            raise

    def apply_feature_definitions(self, feature_objects: List[Any]) -> None:
        """
        应用特征定义到特征仓库

        Args:
            feature_objects: 特征对象列表
        """
        try:
            # 应用到特征仓库
            self.store.apply(feature_objects)

            self.logger.info(f"成功注册 {len(feature_objects)} 个特征对象")

        except Exception as e:
            self.logger.error(f"注册特征定义失败: {str(e)}")
            raise

    def cleanup_old_features(self, older_than_days: int = 30) -> None:
        """
        清理过期特征数据

        Args:
            older_than_days: 保留天数，超过此天数的特征数据将被清理
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=older_than_days)

            # 这里应该实现清理逻辑
            # 由于Feast的限制，可能需要直接操作底层存储
            self.logger.info(f"清理 {cutoff_time} 之前的特征数据")

            # TODO: 实现具体的清理逻辑
            # 1. 清理Redis在线存储中的过期特征
            # 2. 清理PostgreSQL离线存储中的历史特征

        except Exception as e:
            self.logger.error(f"清理过期特征失败: {str(e)}")
            raise

    def get_feature_view(self, feature_view_name: str):
        """
        获取特征视图

        Args:
            feature_view_name: 特征视图名称

        Returns:
            FeatureView: 特征视图对象
        """
        try:
            return self.store.get_feature_view(feature_view_name)
        except Exception as e:
            self.logger.error(f"获取特征视图失败: {str(e)}")
            raise

    def list_feature_views(self) -> List[Any]:
        """
        列出所有特征视图

        Returns:
            List[FeatureView]: 特征视图列表
        """
        try:
            return self.store.list_feature_views()
        except Exception as e:
            self.logger.error(f"列出特征视图失败: {str(e)}")
            return []

    def get_feature_service(self, feature_service_name: str):
        """
        获取特征服务

        Args:
            feature_service_name: 特征服务名称

        Returns:
            FeatureService: 特征服务对象
        """
        try:
            return self.store.get_feature_service(feature_service_name)
        except Exception as e:
            self.logger.error(f"获取特征服务失败: {str(e)}")



            raise