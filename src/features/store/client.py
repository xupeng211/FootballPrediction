"""
特征存储客户端
Feature Store Client

足球特征存储管理器，基于 Feast 实现。
"""




class FootballFeatureStore:
    """
    足球特征存储管理器

    基于 Feast 实现的特征存储，支持：
    - 在线特征查询（Redis）
    - 离线特征查询（PostgreSQL）
    - 特征注册和版本管理
    - 在线/离线特征同步
    """

    def __init__(self, feature_store_path: str = "."):
        """
        初始化特征存储

        Args:
            feature_store_path: Feast 配置文件路径（默认为当前目录，包含feature_store.yaml）
        """
        self.feature_store_path = feature_store_path
        self.store: Optional[FeatureStore] = None

        # 初始化 Feast 存储
        self._initialize_feast_store()

        # 初始化组件
        self.repository = FeatureRepository(self.store)
        self.registry = FeatureRegistry(self.store)

    def _initialize_feast_store(self):
        """初始化 Feast 特征存储"""
        try:
            self.store = FeatureStore(repo_path=self.feature_store_path)
        except Exception as e:
            print(f"Feast 存储初始化失败: {e}")
            self.store = None

    async def register_features(self) -> bool:
        """
        注册特征到 Feast 存储

        Returns:
            bool: 注册是否成功
        """
        return await self.registry.register_all()

    async def get_online_features(
        self, feature_refs: list[str], entity_rows: list[dict[str, any]]
    ):
        """
        获取在线特征（实时查询）

        Args:
            feature_refs: 特征引用列表，如 ["team_recent_performance:recent_5_wins"]
            entity_rows: 实体行数据，如 [{"team_id": 1}, {"team_id": 2}]

        Returns:
            pd.DataFrame: 特征数据
        """
        return await self.repository.get_online_features(feature_refs, entity_rows)

    async def get_historical_features(
        self,
        entity_df,
        feature_refs: list[str],
        full_feature_names: bool = False,
    ):
        """
        获取历史特征（离线批量查询）

        Args:
            entity_df: 实体数据框，必须包含 entity_id 和 event_timestamp
            feature_refs: 特征引用列表
            full_feature_names: 是否返回完整特征名称

        Returns:
            pd.DataFrame: 历史特征数据
        """
        return await self.repository.get_historical_features(
            entity_df, feature_refs, full_feature_names
        )

    async def push_features_to_online_store(self, feature_view_name: str, df):
        """
        推送特征到在线存储

        Args:
            feature_view_name: 特征视图名称
            df: 特征数据框

        Returns:
            bool: 推送是否成功
        """
        return await self.repository.push_features_to_online_store(
            feature_view_name, df
        )

    async def get_match_features_for_prediction(
        self, match_id: int, home_team_id: int, away_team_id: int
    ) -> Optional[dict[str, any]]:
        """
        获取用于预测的比赛特征

        Args:
            match_id: 比赛ID
            home_team_id: 主队ID
            away_team_id: 客队ID

        Returns:
            Optional[Dict[str, Any]]: 特征字典
        """
        return await self.repository.get_match_features_for_prediction(
            match_id, home_team_id, away_team_id
        )

    async def batch_calculate_features(
        self, start_date, end_date
    ) -> dict[str, int]:
        """
        批量计算特征

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            Dict[str, int]: 处理统计
        """
        return await self.repository.batch_calculate_features(start_date, end_date)
from typing import Optional

from .mock_feast import FeatureStore
from .registry import FeatureRegistry
from .repository import FeatureRepository

