"""
数据工程集成示例
将 data-engineering Skill 应用于现有的足球预测系统
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../.."))

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any

# 导入现有系统组件
try:
    from src.config_unified import get_settings
    from src.database.connection import get_connection
    from src.ml.data.postgres_loader import PostgreSQLDataLoader
except ImportError:
    print("⚠️  无法导入现有系统组件，使用模拟组件")

    # 创建模拟配置
    class MockSettings:
        def __init__(self):
            self.database = {
                "host": "localhost",
                "port": 5432,
                "name": "football_prediction_dev",
                "user": "football_user",
                "password": "football_pass",
            }

    def get_settings():
        return MockSettings()


# 导入我们的数据工程组件
from ..scripts.cache_strategy_manager import CACHE_CONFIGS, CacheStrategyManager
from ..scripts.database_connection_optimizer import DatabaseConnectionOptimizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedDataLayer:
    """增强的数据层"""

    def __init__(self):
        self.settings = get_settings()
        self.db_optimizer = None
        self.cache_manager = None
        self.is_initialized = False

    async def initialize(self):
        """初始化增强数据层"""
        logger.info("🔧 初始化增强数据层...")

        # 构建数据库URL
        db_url = (
            f"postgresql://{self.settings.database['user']}:"
            f"{self.settings.database['password']}@"
            f"{self.settings.database['host']}:"
            f"{self.settings.database['port']}/"
            f"{self.settings.database['name']}"
        )

        # 初始化数据库优化器
        self.db_optimizer = DatabaseConnectionOptimizer(
            database_url=db_url, redis_url="redis://localhost:6379", pool_size=20, max_overflow=30
        )
        await self.db_optimizer.initialize()

        # 初始化缓存管理器
        self.cache_manager = CacheStrategyManager("redis://localhost:6379")
        await self.cache_manager.initialize()

        # 注册缓存配置
        for cache_type, config in CACHE_CONFIGS.items():
            self.cache_manager.register_cache_type(cache_type, config)

        # 创建数据库索引
        await self.db_optimizer.create_performance_indexes()

        self.is_initialized = True
        logger.info("✅ 增强数据层初始化完成")

    async def get_match_data(self, match_id: int) -> dict[str, Any] | None:
        """获取比赛数据（带缓存）"""

        async def fetch_from_db(match_id: int):
            """从数据库获取比赛数据"""
            query = """
            SELECT
                m.id,
                m.home_team_id,
                m.away_team_id,
                m.home_score,
                m.away_score,
                m.date,
                ht.name as home_team_name,
                at.name as away_team_name,
                l.name as league_name
            FROM matches m
            JOIN teams ht ON m.home_team_id = ht.id
            JOIN teams at ON m.away_team_id = at.id
            JOIN leagues l ON m.league_id = l.id
            WHERE m.id = $1
            """
            results = await self.db_optimizer.execute_query(query, {"match_id": match_id})
            return dict(results[0]) if results else None

        return await self.cache_manager.get(
            "match_data", {"match_id": match_id}, fallback_func=fetch_from_db, match_id=match_id
        )

    async def get_team_statistics(self, team_id: int, last_n_matches: int = 10) -> dict[str, Any] | None:
        """获取球队统计信息（带缓存）"""

        async def fetch_from_db(team_id: int, last_n_matches: int):
            """从数据库获取球队统计"""
            stats = await self.db_optimizer.get_team_statistics(team_id, last_n_matches)
            return dict(stats[0]) if stats else None

        return await self.cache_manager.get(
            "team_stats",
            {"team_id": team_id, "last_n_matches": last_n_matches},
            fallback_func=fetch_from_db,
            team_id=team_id,
            last_n_matches=last_n_matches,
        )

    async def get_match_features(self, match_id: int) -> list[dict[str, Any]]:
        """获取比赛特征（带缓存）"""

        async def fetch_from_db(match_id: int):
            """从数据库获取比赛特征"""
            query = """
            SELECT feature_type, feature_value
            FROM match_features
            WHERE match_id = $1
            ORDER BY feature_type
            """
            results = await self.db_optimizer.execute_query(query, {"match_id": match_id})
            return [dict(row) for row in results]

        return (
            await self.cache_manager.get(
                "features", {"match_id": match_id}, fallback_func=fetch_from_db, match_id=match_id
            )
            or []
        )

    async def save_prediction(self, prediction_data: dict[str, Any]) -> bool:
        """保存预测结果"""
        try:
            # 插入预测记录
            insert_query = """
            INSERT INTO predictions (match_id, prediction, confidence, created_at)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """
            result = await self.db_optimizer.execute_query(
                insert_query,
                {
                    "match_id": prediction_data["match_id"],
                    "prediction": prediction_data["prediction"],
                    "confidence": prediction_data["confidence"],
                    "created_at": datetime.now(),
                },
            )

            # 缓存预测结果
            if result:
                prediction_id = result[0]["id"]
                prediction_data["id"] = prediction_id
                await self.cache_manager.set("predictions", {"prediction_id": prediction_id}, prediction_data)

            return True

        except Exception as e:
            logger.error(f"保存预测失败: {e}")
            return False

    async def batch_update_features(self, features_data: list[dict[str, Any]]) -> int:
        """批量更新特征数据"""
        try:
            # 先清理旧特征
            match_ids = list(set(f["match_id"] for f in features_data))
            await self.db_optimizer.execute_query(
                "DELETE FROM match_features WHERE match_id = ANY($1::int[])", {"match_ids": match_ids}
            )

            # 批量插入新特征
            inserted_count = await self.db_optimizer.batch_insert("match_features", features_data, batch_size=1000)

            # 清理相关缓存
            for match_id in match_ids:
                await self.cache_manager.delete("features", {"match_id": match_id})
                await self.cache_manager.delete("match_data", {"match_id": match_id})

            logger.info(f"批量更新特征完成: {inserted_count} 条记录")
            return inserted_count

        except Exception as e:
            logger.error(f"批量更新特征失败: {e}")
            return 0

    async def get_upcoming_matches(self, hours_ahead: int = 48) -> list[dict[str, Any]]:
        """获取即将到来的比赛"""

        async def fetch_from_db():
            """从数据库获取即将到来的比赛"""
            query = f"""
            SELECT
                m.id,
                m.home_team_id,
                m.away_team_id,
                m.date,
                ht.name as home_team_name,
                at.name as away_team_name
            FROM matches m
            JOIN teams ht ON m.home_team_id = ht.id
            JOIN teams at ON m.away_team_id = at.id
            WHERE m.date BETWEEN NOW() AND NOW() + INTERVAL '{hours_ahead} hours'
            AND (m.home_score IS NULL OR m.away_score IS NULL)
            ORDER BY m.date
            """

            results = await self.db_optimizer.execute_query(query, use_cache=True, cache_ttl=300)
            return [dict(row) for row in results]

        return (
            await self.cache_manager.get("match_data", {"upcoming_matches": hours_ahead}, fallback_func=fetch_from_db)
            or []
        )

    async def warm_up_cache(self):
        """缓存预热"""
        logger.info("🔥 开始缓存预热...")

        # 预热即将到来的比赛
        upcoming_matches = await self.get_upcoming_matches(hours_ahead=24)
        warm_up_data = []

        for match in upcoming_matches:
            warm_up_data.append({"key": {"match_id": match["id"]}, "value": match})

            # 预热球队统计
            for team_id in [match["home_team_id"], match["away_team_id"]]:
                team_stats = await self.get_team_statistics(team_id)
                if team_stats:
                    warm_up_data.append({"key": {"team_id": team_id, "last_n_matches": 10}, "value": team_stats})

        # 执行预热
        await self.cache_manager.warm_up_cache("match_data", warm_up_data[:10])
        logger.info(f"缓存预热完成: {len(warm_up_data)} 个条目")

    async def get_performance_metrics(self) -> dict[str, Any]:
        """获取性能指标"""
        metrics = {
            "database": {
                "health": await self.db_optimizer.health_check(),
                "stats": self.db_optimizer.get_performance_report(),
                "connection_pools": await self.db_optimizer.get_connection_pool_stats(),
            },
            "cache": {
                "health": await self.cache_manager.health_check(),
                "stats": self.cache_manager.get_cache_stats(),
                "redis_info": await self.cache_manager.get_redis_info(),
            },
        }

        return metrics

    async def cleanup_old_data(self, days_to_keep: int = 90):
        """清理旧数据"""
        logger.info(f"🧹 清理 {days_to_keep} 天前的旧数据...")

        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        # 清理旧的比赛特征
        await self.db_optimizer.execute_query(
            """
            DELETE FROM match_features
            WHERE match_id IN (
                SELECT id FROM matches
                WHERE date < $1
            )
            """,
            {"cutoff_date": cutoff_date},
        )

        # 清理旧的预测记录
        await self.db_optimizer.execute_query(
            """
            DELETE FROM predictions
            WHERE created_at < $1
            """,
            {"cutoff_date": cutoff_date},
        )

        logger.info("旧数据清理完成")

    async def demonstrate_optimization(self):
        """演示优化效果"""
        logger.info("📊 演示数据层优化效果...")

        # 模拟数据加载
        test_match_ids = [1, 2, 3, 4, 5]  # 测试比赛ID

        print("\n🏈 获取比赛数据性能测试:")
        for match_id in test_match_ids:
            start_time = datetime.now()
            match_data = await self.get_match_data(match_id)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            if match_data:
                print(f"  比赛 {match_id}: {duration:.4f}s (缓存: {'命中' if duration < 0.01 else '未命中'})")

        print("\n📈 缓存统计:")
        cache_stats = self.cache_manager.get_cache_stats()
        print(f"  总请求: {cache_stats['global']['total_requests']}")
        print(f"  命中率: {cache_stats['global']['hit_rate']:.2%}")
        print(f"  L1命中率: {cache_stats['global']['l1_hit_rate']:.2%}")
        print(f"  L2命中率: {cache_stats['global']['l2_hit_rate']:.2%}")

        print("\n🐘 数据库统计:")
        db_report = self.db_optimizer.get_performance_report()
        print(f"  查询统计: {json.dumps(db_report, indent=2)}")

        return {"cache_stats": cache_stats, "db_stats": db_report}

    async def integrate_with_existing_system(self):
        """与现有系统集成"""
        logger.info("🔗 与现有系统集成...")

        # 这里可以包装现有的数据加载器
        class EnhancedPostgresLoader:
            """增强的PostgreSQL数据加载器"""

            def __init__(self, data_layer: EnhancedDataLayer):
                self.data_layer = data_layer

            async def load_training_data(self) -> dict[str, Any]:
                """加载训练数据（优化版）"""
                # 使用优化后的方法获取数据
                upcoming_matches = await self.data_layer.get_upcoming_matches(hours_ahead=168)  # 一周

                training_data = {"matches": [], "features": [], "teams": set()}

                for match in upcoming_matches:
                    match_data = await self.data_layer.get_match_data(match["id"])
                    if match_data:
                        training_data["matches"].append(match_data)
                        training_data["teams"].update([match["home_team_id"], match["away_team_id"]])

                    features = await self.data_layer.get_match_features(match["id"])
                    if features:
                        training_data["features"].extend(features)

                training_data["teams"] = list(training_data["teams"])
                return training_data

            async def save_predictions_batch(self, predictions: list[dict[str, Any]]) -> int:
                """批量保存预测"""
                success_count = 0
                for prediction in predictions:
                    if await self.data_layer.save_prediction(prediction):
                        success_count += 1
                return success_count

        # 创建增强的数据加载器实例
        enhanced_loader = EnhancedPostgresLoader(self)

        logger.info("✅ 系统集成完成")
        return enhanced_loader

    async def cleanup(self):
        """清理资源"""
        logger.info("🧹 清理增强数据层...")

        if self.cache_manager:
            await self.cache_manager.cleanup()

        if self.db_optimizer:
            await self.db_optimizer.cleanup()

        logger.info("✅ 数据层清理完成")


# 全局实例
enhanced_data_layer = None


async def get_enhanced_data_layer() -> EnhancedDataLayer:
    """获取增强数据层实例"""
    global enhanced_data_layer
    if enhanced_data_layer is None or not enhanced_data_layer.is_initialized:
        enhanced_data_layer = EnhancedDataLayer()
        await enhanced_data_layer.initialize()
    return enhanced_data_layer


async def main():
    """主函数示例"""
    print("🗄️ 增强数据层集成演示")
    print("=" * 50)

    data_layer = EnhancedDataLayer()

    try:
        # 初始化
        await data_layer.initialize()

        # 演示优化效果
        results = await data_layer.demonstrate_optimization()

        # 缓存预热
        await data_layer.warm_up_cache()

        # 与现有系统集成
        enhanced_loader = await data_layer.integrate_with_existing_system()

        # 获取性能指标
        metrics = await data_layer.get_performance_metrics()
        print("\n📊 系统性能指标:")
        print(json.dumps(metrics, indent=2))

        # 清理旧数据（可选）
        # await data_layer.cleanup_old_data(days_to_keep=30)

    finally:
        await data_layer.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
