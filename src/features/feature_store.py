import os
"""
Feast 特征存储集成

集成 Feast 特征存储，支持：
- 在线特征服务（快速查询）
- 离线特征服务（批量训练）
- 特征视图定义和管理
- 特征注册和更新
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# 处理可选依赖
try:
    from feast import Entity, FeatureStore, FeatureView, Field
    from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import (
        PostgreSQLSource,
    )
    from feast.types import Float64, Int64

    HAS_FEAST = True
except ImportError:
    HAS_FEAST = False

    # 创建模拟类（使用Mock前缀避免命名冲突）
    class MockEntity:
        def __init__(self, *args, **kwargs):
            pass

    class MockFeatureStore:
        def __init__(self, *args, **kwargs):
            pass

        def get_online_features(self, *args, **kwargs):
            return {"features": {}}

        def get_historical_features(self, *args, **kwargs):
            return {}

    class MockFeatureView:
        def __init__(self, *args, **kwargs):
            pass

    class MockField:
        def __init__(self, *args, **kwargs):
            pass

    class MockFloat64:
        pass

    class MockInt64:
        pass

    class MockPostgreSQLSource:
        def __init__(self, *args, **kwargs):
            pass

    # 将模拟类赋值给原名称，保持向后兼容
    Entity = MockEntity
    FeatureStore = MockFeatureStore
    FeatureView = MockFeatureView
    Field = MockField
    Float64 = MockFloat64
    Int64 = MockInt64
    PostgreSQLSource = MockPostgreSQLSource


import pandas as pd

from src.cache import CacheKeyManager, RedisManager
from src.database.connection import DatabaseManager

from .entities import MatchEntity
from .feature_calculator import FeatureCalculator


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
        self.calculator = FeatureCalculator()
        self.db_manager = DatabaseManager()
        self.cache_manager = RedisManager()

        # 初始化 Feast 存储
        self._initialize_feast_store()

    def _initialize_feast_store(self):
        """初始化 Feast 特征存储"""
        try:
            self.store = FeatureStore(repo_path=self.feature_store_path)
        except Exception as e:
            print(f"Feast 存储初始化失败: {e}")
            self.store = None

    def get_entity_definitions(self) -> Dict[str, Entity]:
        """
        获取实体定义

        Returns:
            Dict[str, Entity]: 实体名称到实体对象的映射
        """
        from feast import ValueType

        return {
            "match": Entity(
                name="match",
                value_type=ValueType.INT64,
                description = os.getenv("FEATURE_STORE_DESCRIPTION_126"),
            ),
            "team": Entity(
                name="team",
                value_type=ValueType.INT64,
                description = os.getenv("FEATURE_STORE_DESCRIPTION_130"),
            ),
        }

    def get_feature_view_definitions(self) -> Dict[str, FeatureView]:
        """
        获取特征视图定义

        Returns:
            Dict[str, FeatureView]: 特征视图名称到视图对象的映射
        """
        # PostgreSQL 数据源配置
        postgres_source = PostgreSQLSource(
            name = os.getenv("FEATURE_STORE_NAME_143"),
            query="""
                SELECT
                    team_id,
                    recent_5_wins,
                    recent_5_draws,
                    recent_5_losses,
                    recent_5_goals_for,
                    recent_5_goals_against,
                    recent_5_points,
                    recent_5_home_wins,
                    recent_5_away_wins,
                    recent_5_home_goals_for,
                    recent_5_away_goals_for,
                    calculation_date as event_timestamp
                FROM team_recent_performance_features
            """,
            timestamp_field = os.getenv("FEATURE_STORE_TIMESTAMP_FIELD_159"),
        )

        match_postgres_source = PostgreSQLSource(
            name = os.getenv("FEATURE_STORE_NAME_161"),
            query="""
                SELECT
                    match_id,
                    home_team_id,
                    away_team_id,
                    h2h_total_matches,
                    h2h_home_wins,
                    h2h_away_wins,
                    h2h_draws,
                    h2h_home_goals_total,
                    h2h_away_goals_total,
                    calculation_date as event_timestamp
                FROM historical_matchup_features
            """,
            timestamp_field = os.getenv("FEATURE_STORE_TIMESTAMP_FIELD_159"),
        )

        odds_postgres_source = PostgreSQLSource(
            name = os.getenv("FEATURE_STORE_NAME_180"),
            query="""
                SELECT
                    match_id,
                    home_odds_avg,
                    draw_odds_avg,
                    away_odds_avg,
                    home_implied_probability,
                    draw_implied_probability,
                    away_implied_probability,
                    bookmaker_count,
                    bookmaker_consensus,
                    calculation_date as event_timestamp
                FROM odds_features
            """,
            timestamp_field = os.getenv("FEATURE_STORE_TIMESTAMP_FIELD_159"),
        )

        entities = self.get_entity_definitions()

        return {
            "team_recent_performance": FeatureView(
                name = os.getenv("FEATURE_STORE_NAME_199"),
                entities=[entities["team"]],
                ttl=timedelta(days=7),
                schema=[
                    Field(name = os.getenv("FEATURE_STORE_NAME_205"), dtype=Int64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_206"), dtype=Int64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_208"), dtype=Int64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_210"), dtype=Int64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_210"), dtype=Int64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_211"), dtype=Int64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_212"), dtype=Int64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_213"), dtype=Int64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_214"), dtype=Int64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_214"), dtype=Int64),
                ],
                source=postgres_source,
                description = os.getenv("FEATURE_STORE_DESCRIPTION_216"),
            ),
            "historical_matchup": FeatureView(
                name = os.getenv("FEATURE_STORE_NAME_217"),
                entities=[entities["match"]],
                ttl=timedelta(days=30),
                schema=[
                    Field(name = os.getenv("FEATURE_STORE_NAME_219"), dtype=Int64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_221"), dtype=Int64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_222"), dtype=Int64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_224"), dtype=Int64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_225"), dtype=Int64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_226"), dtype=Int64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_228"), dtype=Int64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_229"), dtype=Int64),
                ],
                source=match_postgres_source,
                description = os.getenv("FEATURE_STORE_DESCRIPTION_231"),
            ),
            "odds_features": FeatureView(
                name = os.getenv("FEATURE_STORE_NAME_232"),
                entities=[entities["match"]],
                ttl=timedelta(hours=6),
                schema=[
                    Field(name = os.getenv("FEATURE_STORE_NAME_234"), dtype=Float64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_234"), dtype=Float64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_235"), dtype=Float64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_236"), dtype=Float64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_238"), dtype=Float64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_239"), dtype=Float64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_241"), dtype=Int64),
                    Field(name = os.getenv("FEATURE_STORE_NAME_242"), dtype=Float64),
                ],
                source=odds_postgres_source,
                description = os.getenv("FEATURE_STORE_DESCRIPTION_245"),
            ),
        }

    async def register_features(self) -> bool:
        """
        注册特征到 Feast 存储

        Returns:
            bool: 注册是否成功
        """
        if not self.store:
            print("Feast 存储未初始化")
            return False

        try:
            # 注册实体
            entities = self.get_entity_definitions()
            for entity in entities.values():
                self.store.apply(entity)

            # 注册特征视图
            feature_views = self.get_feature_view_definitions()
            for fv in feature_views.values():
                self.store.apply(fv)

            print("特征注册成功")
            return True

        except Exception as e:
            print(f"特征注册失败: {e}")
            return False

    async def get_online_features(
        self, feature_refs: List[str], entity_rows: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        获取在线特征（实时查询）

        Args:
            feature_refs: 特征引用列表，如 ["team_recent_performance:recent_5_wins"]
            entity_rows: 实体行数据，如 [{"team_id": 1}, {"team_id": 2}]

        Returns:
            pd.DataFrame: 特征数据
        """
        if not self.store:
            raise ValueError("Feast 存储未初始化")

        try:
            # 获取在线特征
            result = self.store.get_online_features(
                features=feature_refs, entity_rows=entity_rows
            )

            return result.to_df()

        except Exception as e:
            print(f"获取在线特征失败: {e}")
            return pd.DataFrame()

    async def get_historical_features(
        self,
        entity_df: pd.DataFrame,
        feature_refs: List[str],
        full_feature_names: bool = False,
    ) -> pd.DataFrame:
        """
        获取历史特征（离线批量查询）

        Args:
            entity_df: 实体数据框，必须包含 entity_id 和 event_timestamp
            feature_refs: 特征引用列表
            full_feature_names: 是否返回完整特征名称

        Returns:
            pd.DataFrame: 历史特征数据
        """
        if not self.store:
            raise ValueError("Feast 存储未初始化")

        try:
            # 获取历史特征
            training_df = self.store.get_historical_features(
                entity_df=entity_df,
                features=feature_refs,
                full_feature_names=full_feature_names,
            ).to_df()

            return training_df

        except Exception as e:
            print(f"获取历史特征失败: {e}")
            return pd.DataFrame()

    async def push_features_to_online_store(
        self, feature_view_name: str, df: pd.DataFrame
    ) -> bool:
        """
        推送特征到在线存储

        Args:
            feature_view_name: 特征视图名称
            df: 特征数据框

        Returns:
            bool: 推送是否成功
        """
        if not self.store:
            print("Feast 存储未初始化")
            return False

        try:
            # 获取特征视图
            feature_views = self.get_feature_view_definitions()
            if feature_view_name not in feature_views:
                print(f"特征视图 {feature_view_name} 不存在")
                return False

            # 推送到在线存储
            self.store.push(push_source_name=f"{feature_view_name}_push_source", df=df)

            print(f"特征推送到在线存储成功: {feature_view_name}")
            return True

        except Exception as e:
            print(f"推送特征失败: {e}")
            return False

    async def calculate_and_store_team_features(
        self, team_id: int, calculation_date: Optional[datetime] = None
    ) -> bool:
        """
        计算并存储球队特征

        Args:
            team_id: 球队ID
            calculation_date: 计算日期

        Returns:
            bool: 存储是否成功
        """
        if calculation_date is None:
            calculation_date = datetime.now()

        try:
            # 计算特征
            features = await self.calculator.calculate_recent_performance_features(
                team_id, calculation_date
            )

            # 转换为 DataFrame
            df = pd.DataFrame(
                [
                    {
                        "team_id": features.team_id,
                        "recent_5_wins": features.recent_5_wins,
                        "recent_5_draws": features.recent_5_draws,
                        "recent_5_losses": features.recent_5_losses,
                        "recent_5_goals_for": features.recent_5_goals_for,
                        "recent_5_goals_against": features.recent_5_goals_against,
                        "recent_5_points": features.recent_5_points,
                        "recent_5_home_wins": features.recent_5_home_wins,
                        "recent_5_away_wins": features.recent_5_away_wins,
                        "recent_5_home_goals_for": features.recent_5_home_goals_for,
                        "recent_5_away_goals_for": features.recent_5_away_goals_for,
                        "event_timestamp": calculation_date,
                    }
                ]
            )

            # 推送到在线存储
            return await self.push_features_to_online_store(
                "team_recent_performance", df
            )

        except Exception as e:
            print(f"计算并存储球队特征失败: {e}")
            return False

    async def calculate_and_store_match_features(
        self, match_entity: MatchEntity, calculation_date: Optional[datetime] = None
    ) -> bool:
        """
        计算并存储比赛特征

        Args:
            match_entity: 比赛实体
            calculation_date: 计算日期

        Returns:
            bool: 存储是否成功
        """
        if calculation_date is None:
            calculation_date = match_entity.match_time

        try:
            # 计算历史对战特征
            h2h_features = await self.calculator.calculate_historical_matchup_features(
                match_entity.home_team_id, match_entity.away_team_id, calculation_date
            )

            # 计算赔率特征
            odds_features = await self.calculator.calculate_odds_features(
                match_entity.match_id, calculation_date
            )

            # 存储历史对战特征
            h2h_df = pd.DataFrame(
                [
                    {
                        "match_id": match_entity.match_id,
                        "home_team_id": h2h_features.home_team_id,
                        "away_team_id": h2h_features.away_team_id,
                        "h2h_total_matches": h2h_features.h2h_total_matches,
                        "h2h_home_wins": h2h_features.h2h_home_wins,
                        "h2h_away_wins": h2h_features.h2h_away_wins,
                        "h2h_draws": h2h_features.h2h_draws,
                        "h2h_home_goals_total": h2h_features.h2h_home_goals_total,
                        "h2h_away_goals_total": h2h_features.h2h_away_goals_total,
                        "event_timestamp": calculation_date,
                    }
                ]
            )

            # 存储赔率特征
            odds_df = pd.DataFrame(
                [
                    {
                        "match_id": odds_features.match_id,
                        "home_odds_avg": (
                            float(odds_features.home_odds_avg)
                            if odds_features.home_odds_avg
                            else None
                        ),
                        "draw_odds_avg": (
                            float(odds_features.draw_odds_avg)
                            if odds_features.draw_odds_avg
                            else None
                        ),
                        "away_odds_avg": (
                            float(odds_features.away_odds_avg)
                            if odds_features.away_odds_avg
                            else None
                        ),
                        "home_implied_probability": odds_features.home_implied_probability,
                        "draw_implied_probability": odds_features.draw_implied_probability,
                        "away_implied_probability": odds_features.away_implied_probability,
                        "bookmaker_count": odds_features.bookmaker_count,
                        "bookmaker_consensus": odds_features.bookmaker_consensus,
                        "event_timestamp": calculation_date,
                    }
                ]
            )

            # 推送到在线存储
            h2h_success = await self.push_features_to_online_store(
                "historical_matchup", h2h_df
            )
            odds_success = await self.push_features_to_online_store(
                "odds_features", odds_df
            )

            return h2h_success and odds_success

        except Exception as e:
            print(f"计算并存储比赛特征失败: {e}")
            return False

    async def get_match_features_for_prediction(
        self, match_id: int, home_team_id: int, away_team_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取用于预测的比赛特征

        Args:
            match_id: 比赛ID
            home_team_id: 主队ID
            away_team_id: 客队ID

        Returns:
            Optional[Dict[str, Any]]: 特征字典
        """
        try:
            # 生成缓存Key
            cache_key = CacheKeyManager.match_features_key(match_id)

            # 尝试从缓存获取特征数据
            cached_features = await self.cache_manager.aget(cache_key)
            if cached_features:
                print(f"从缓存获取比赛 {match_id} 的预测特征")
                return cached_features

            # 获取球队近期表现特征
            team_features = await self.get_online_features(
                feature_refs=[
                    "team_recent_performance:recent_5_wins",
                    "team_recent_performance:recent_5_draws",
                    "team_recent_performance:recent_5_losses",
                    "team_recent_performance:recent_5_goals_for",
                    "team_recent_performance:recent_5_goals_against",
                    "team_recent_performance:recent_5_points",
                ],
                entity_rows=[{"team_id": home_team_id}, {"team_id": away_team_id}],
            )

            # 获取历史对战特征
            h2h_features = await self.get_online_features(
                feature_refs=[
                    "historical_matchup:h2h_total_matches",
                    "historical_matchup:h2h_home_wins",
                    "historical_matchup:h2h_away_wins",
                    "historical_matchup:h2h_draws",
                ],
                entity_rows=[{"match_id": match_id}],
            )

            # 获取赔率特征
            odds_features = await self.get_online_features(
                feature_refs=[
                    "odds_features:home_implied_probability",
                    "odds_features:draw_implied_probability",
                    "odds_features:away_implied_probability",
                    "odds_features:bookmaker_consensus",
                ],
                entity_rows=[{"match_id": match_id}],
            )

            # 合并特征
            features = {
                "team_features": team_features.to_dict("records"),
                "h2h_features": (
                    h2h_features.to_dict("records")[0] if not h2h_features.empty else {}
                ),
                "odds_features": (
                    odds_features.to_dict("records")[0]
                    if not odds_features.empty
                    else {}
                ),
            }

            # 将特征数据存入缓存
            await self.cache_manager.aset(
                cache_key, features, cache_type = os.getenv("FEATURE_STORE_CACHE_TYPE_577")
            )

            return features

        except Exception as e:
            print(f"获取预测特征失败: {e}")
            return None

    async def batch_calculate_features(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, int]:
        """
        批量计算特征

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            Dict[str, int]: 处理统计
        """
        stats = {
            "matches_processed": 0,
            "teams_processed": 0,
            "features_stored": 0,
            "errors": 0,
        }

        try:
            async with self.db_manager.get_async_session() as session:
                # 获取时间范围内的比赛
                from sqlalchemy import select

                from ..database.models.match import Match

                matches_query = select(Match).where(
                    Match.match_time.between(start_date, end_date)
                )
                result = await session.execute(matches_query)
                matches = result.scalars().all()

                for match in matches:
                    try:
                        match_entity = MatchEntity(
                            match_id=match.id,
                            home_team_id=match.home_team_id,
                            away_team_id=match.away_team_id,
                            league_id=match.league_id,
                            match_time=match.match_time,
                            season=match.season or "2024-25",
                        )

                        # 计算并存储比赛特征
                        success = await self.calculate_and_store_match_features(
                            match_entity
                        )
                        if success:
                            stats["features_stored"] += 1

                        stats["matches_processed"] += 1

                        # 计算并存储球队特征
                        for team_id in [match.home_team_id, match.away_team_id]:
                            team_success = await self.calculate_and_store_team_features(
                                team_id, match.match_time
                            )
                            if team_success:
                                stats["teams_processed"] += 1

                    except Exception as e:
                        print(f"处理比赛 {match.id} 失败: {e}")
                        stats["errors"] += 1
                        continue

            return stats

        except Exception as e:
            print(f"批量计算特征失败: {e}")
            stats["errors"] += 1
            return stats
