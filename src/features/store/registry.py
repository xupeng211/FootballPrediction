"""
特征注册器
Feature Registry

负责将实体和特征视图注册到 Feast 存储。
"""

from typing import Optional

from .mock_feast import FeatureStore


class FeatureRegistry:
    """特征注册器"""

    def __init__(self, store: Optional[FeatureStore] = None):
        """
        初始化特征注册器

        Args:
            store: Feast 特征存储实例
        """
        self.store = store

    async def register_all(self) -> bool:
        """
        注册所有实体和特征视图

        Returns:
            bool: 注册是否成功
        """
        if not self.store:
            print("Feast 存储未初始化")
            return False

        try:
            # 注册实体
            from .entities import get_entity_definitions

            entities = get_entity_definitions()
            for entity in entities.values():
                self.store.apply(entity)

            # 注册特征视图
            from .feature_views import get_feature_view_definitions

            feature_views = get_feature_view_definitions()
            for fv in feature_views.values():
                self.store.apply(fv)

            print("特征注册成功")
            return True

        except Exception as e:
            print(f"特征注册失败: {e}")
            return False

    async def register_entity(self, entity_name: str) -> bool:
        """
        注册单个实体

        Args:
            entity_name: 实体名称

        Returns:
            bool: 注册是否成功
        """
        if not self.store:
            print("Feast 存储未初始化")
            return False

        try:
            from .entities import get_entity_definitions

            entities = get_entity_definitions()
            if entity_name not in entities:
                print(f"实体 {entity_name} 不存在")
                return False

            self.store.apply(entities[entity_name])
            print(f"实体 {entity_name} 注册成功")
            return True

        except Exception as e:
            print(f"注册实体 {entity_name} 失败: {e}")
            return False

    async def register_feature_view(self, feature_view_name: str) -> bool:
        """
        注册单个特征视图

        Args:
            feature_view_name: 特征视图名称

        Returns:
            bool: 注册是否成功
        """
        if not self.store:
            print("Feast 存储未初始化")
            return False

        try:
            from .feature_views import get_feature_view_definitions

            feature_views = get_feature_view_definitions()
            if feature_view_name not in feature_views:
                print(f"特征视图 {feature_view_name} 不存在")
                return False

            self.store.apply(feature_views[feature_view_name])
            print(f"特征视图 {feature_view_name} 注册成功")
            return True

        except Exception as e:
            print(f"注册特征视图 {feature_view_name} 失败: {e}")
            return False