"""
特征仓库查询管理模块
Feature Store Query Management Module
"""



logger = get_logger(__name__)


class FeatureQueryManager:
    """特征查询管理器"""

    def __init__(self, store, storage_manager):
        """
        初始化查询管理器

        Args:
            store: Feast FeatureStore 实例
            storage_manager: 存储管理器实例
        """
        self.store = store
        self.storage_manager = storage_manager
        self.logger = logger

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
        try:
            # 获取特征服务
            feature_service = self.storage_manager.get_feature_service(feature_service_name)

            # 获取在线特征
            feature_vector = self.store.get_online_features(
                features=feature_service, entity_rows=entity_df.to_dict("records")
            )

            return (
                feature_vector.to_df()
                if isinstance(feature_vector.to_df(), dict)
                else {}
            )
        except Exception as e:
            self.logger.error(f"获取在线特征失败: {str(e)}")
            raise

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
        try:
            # 获取特征服务
            feature_service = self.storage_manager.get_feature_service(feature_service_name)

            # 获取历史特征
            training_df = self.store.get_historical_features(
                entity_df=entity_df,
                features=feature_service,
                full_feature_names=full_feature_names,
            )

            return training_df.to_df() if isinstance(training_df.to_df(), dict) else {}
        except Exception as e:
            self.logger.error(f"获取历史特征失败: {str(e)}")
            raise

    def get_feature_statistics(self, feature_view_name: str) -> Dict[str, Any]:
        """
        获取特征统计信息

        Args:
            feature_view_name: 特征视图名称

        Returns:
            Dict: 特征统计信息
        """
        try:
            # 获取特征视图
            feature_view = self.storage_manager.get_feature_view(feature_view_name)

            # 这里可以添加更详细的统计逻辑
            stats = {
                "feature_view_name": feature_view_name,
                "num_features": len(feature_view.features),
                "feature_names": [f.name for f in feature_view.features],
                "entities": [e.name for e in feature_view.entities],
                "ttl_days": feature_view.ttl.days if feature_view.ttl else None,
                "tags": feature_view.tags,
            }

            return stats if isinstance(stats, dict) else {}
        except Exception as e:
            self.logger.error(f"获取特征统计失败: {str(e)}")
            return {"error": str(e)}

    def list_features(self) -> List[Dict[str, Any]]:
        """
        列出所有特征

        Returns:
            List[Dict]: 特征列表信息
        """
        try:
            features_list = []




            # 获取所有特征视图
            feature_views = self.storage_manager.list_feature_views()
            for fv in feature_views:
                for feature in fv.features:
                    features_list.append(
                        {
                            "feature_view": fv.name,
                            "feature_name": (
                                str(feature.name)
                                if hasattr(feature, "name")
                                else str(feature)
                            ),
                            "feature_type": str(feature.dtype),
                            "description": feature.description or "",
                            "entities": [e.name for e in fv.entities],
                            "tags": fv.tags,
                        }
                    )

            return features_list if isinstance(features_list, dict) else {}
        except Exception as e:
            self.logger.error(f"列出特征失败: {str(e)}")
            return [] if isinstance([], dict) else {}