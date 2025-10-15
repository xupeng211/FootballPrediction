from typing import Any

"""
特征仓库使用示例

演示如何使用足球预测系统的特征仓库进行特征存储、查询和模型训练。

主要示例：
- 初始化特征仓库
- 写入特征数据
- 获取在线特征（实时预测）
- 获取历史特征（模型训练）
- 特征统计和管理

基于 DATA_DESIGN.md 第6.1节特征仓库设计。
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta

import pandas as pd

from .feature_store import (
    FootballFeatureStore,
    get_feature_store,
    initialize_feature_store,
)

logger = logging.getLogger(__name__)


def example_initialize_feature_store() -> FootballFeatureStore:
    """
    示例：初始化特征仓库

    Returns:
        FootballFeatureStore: 特征仓库实例
    """
    logger.info("🚀 初始化特征仓库...")

    # 配置PostgreSQL离线存储 - 使用环境变量
    postgres_config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "database": os.getenv("DB_NAME", "football_prediction_dev"),
        "user": os.getenv("DB_READER_USER", "football_reader"),
        "password": os.getenv("DB_READER_PASSWORD", ""),
    }

    # 配置Redis在线存储
    redis_config = {"connection_string": "redis://localhost:6379/1"}

    # 初始化特征仓库
    feature_store = initialize_feature_store(
        project_name="football_prediction_demo",
        postgres_config=postgres_config,
        redis_config=redis_config,
    )

    logger.info("✅ 特征仓库初始化成功！")
    return feature_store


def example_write_team_features(feature_store: FootballFeatureStore) -> None:
    """
    示例：写入球队特征数据

    Args:
        feature_store: 特征仓库实例
    """
    logger.info("📝 写入球队近期统计特征...")

    # 创建示例球队统计数据
    team_stats_data = [
        {
            "team_id": 1,
            "event_timestamp": datetime(2025, 9, 10),
            "recent_5_wins": 3,
            "recent_5_draws": 1,
            "recent_5_losses": 1,
            "recent_5_goals_for": 8,
            "recent_5_goals_against": 4,
            "recent_5_goal_difference": 4,
            "recent_5_points": 10,
            "recent_5_avg_rating": 7.2,
            "recent_10_wins": 6,
            "recent_10_draws": 2,
            "recent_10_losses": 2,
            "recent_10_goals_for": 15,
            "recent_10_goals_against": 8,
            "recent_10_win_rate": 0.6,
            "home_wins": 8,
            "home_goals_avg": 2.1,
            "away_wins": 4,
            "away_goals_avg": 1.3,
            "team_value_millions": 150.5,
            "avg_player_age": 26.8,
            "league_position": 3,
            "points_per_game": 2.1,
        },
        {
            "team_id": 2,
            "event_timestamp": datetime(2025, 9, 10),
            "recent_5_wins": 2,
            "recent_5_draws": 2,
            "recent_5_losses": 1,
            "recent_5_goals_for": 6,
            "recent_5_goals_against": 5,
            "recent_5_goal_difference": 1,
            "recent_5_points": 8,
            "recent_5_avg_rating": 6.8,
            "recent_10_wins": 5,
            "recent_10_draws": 3,
            "recent_10_losses": 2,
            "recent_10_goals_for": 12,
            "recent_10_goals_against": 10,
            "recent_10_win_rate": 0.5,
            "home_wins": 6,
            "home_goals_avg": 1.8,
            "away_wins": 3,
            "away_goals_avg": 1.1,
            "team_value_millions": 120.3,
            "avg_player_age": 28.2,
            "league_position": 7,
            "points_per_game": 1.7,
        },
    ]

    df = pd.DataFrame(team_stats_data)

    # 写入特征数据
    feature_store.write_features(feature_view_name="team_recent_stats", df=df)

    logger.info(f"✅ 成功写入 {len(df)} 条球队统计特征！")


def example_write_odds_features(feature_store: FootballFeatureStore) -> None:
    """
    示例：写入赔率特征数据

    Args:
        feature_store: 特征仓库实例
    """
    logger.info("📝 写入赔率特征数据...")

    # 创建示例赔率数据
    odds_data = [
        {
            "match_id": 1001,
            "event_timestamp": datetime(2025, 9, 10, 14, 0, 0),
            "home_odds": 1.85,
            "draw_odds": 3.40,
            "away_odds": 4.20,
            "home_implied_prob": 0.541,
            "draw_implied_prob": 0.294,
            "away_implied_prob": 0.238,
            "consensus_home_odds": 1.88,
            "consensus_draw_odds": 3.35,
            "consensus_away_odds": 4.10,
            "home_odds_movement": -0.03,
            "draw_odds_movement": 0.05,
            "away_odds_movement": 0.10,
            "over_under_line": 2.5,
            "over_odds": 1.90,
            "under_odds": 1.95,
            "handicap_line": -0.5,
            "handicap_home_odds": 1.95,
            "handicap_away_odds": 1.90,
            "bookmaker_margin": 0.073,
            "market_efficiency": 0.92,
        },
        {
            "match_id": 1002,
            "event_timestamp": datetime(2025, 9, 10, 16, 30, 0),
            "home_odds": 2.10,
            "draw_odds": 3.20,
            "away_odds": 3.60,
            "home_implied_prob": 0.476,
            "draw_implied_prob": 0.313,
            "away_implied_prob": 0.278,
            "consensus_home_odds": 2.15,
            "consensus_draw_odds": 3.15,
            "consensus_away_odds": 3.55,
            "home_odds_movement": 0.05,
            "draw_odds_movement": -0.05,
            "away_odds_movement": -0.05,
            "over_under_line": 2.5,
            "over_odds": 2.05,
            "under_odds": 1.80,
            "handicap_line": 0.0,
            "handicap_home_odds": 1.85,
            "handicap_away_odds": 2.00,
            "bookmaker_margin": 0.067,
            "market_efficiency": 0.94,
        },
    ]

    df = pd.DataFrame(odds_data)

    # 写入赔率特征
    feature_store.write_features(feature_view_name="odds_features", df=df)

    logger.info(f"✅ 成功写入 {len(df)} 条赔率特征！")


def example_get_online_features(feature_store: FootballFeatureStore) -> pd.DataFrame:
    """
    示例：获取在线特征（用于实时预测）

    Args:
        feature_store: 特征仓库实例

    Returns:
        pd.DataFrame: 在线特征数据
    """
    logger.info("🔍 获取在线特征数据...")

    # 构建实体数据（要预测的比赛）
    entity_data = [{"match_id": 1001}, {"match_id": 1002}]
    entity_df = pd.DataFrame(entity_data)

    # 获取实时预测特征
    features_df = feature_store.get_online_features(
        feature_service_name="real_time_prediction_v1", entity_df=entity_df
    )

    logger.info("✅ 成功获取在线特征！")
    logger.info("\n📊 在线特征数据预览：")
    logger.info(features_df.head())

    return features_df


def example_get_historical_features(
    feature_store: FootballFeatureStore,
) -> pd.DataFrame:
    """
    示例：获取历史特征（用于模型训练）

    Args:
        feature_store: 特征仓库实例

    Returns:
        pd.DataFrame: 历史特征数据
    """
    logger.info("📈 获取历史特征数据...")

    # 构建训练数据实体（历史比赛）
    training_entities = []
    base_date = datetime(2025, 8, 1)

    for i in range(10):  # 10场历史比赛
        training_entities.append(
            {"match_id": 2000 + i, "event_timestamp": base_date + timedelta(days=i * 3)}
        )

    entity_df = pd.DataFrame(training_entities)

    # 获取完整的比赛预测特征
    training_df = feature_store.get_historical_features(
        feature_service_name="match_prediction_v1",
        entity_df=entity_df,
        full_feature_names=True,
    )

    logger.info("✅ 成功获取历史特征！")
    logger.info(f"\n📊 训练数据集大小: {training_df.shape}")
    logger.info("\n🔍 特征列预览：")
    logger.info(list(training_df.columns))

    return training_df


def example_create_training_dataset(
    feature_store: FootballFeatureStore,
) -> pd.DataFrame:
    """
    示例：创建机器学习训练数据集

    Args:
        feature_store: 特征仓库实例

    Returns:
        pd.DataFrame: 训练数据集
    """
    logger.info("🎯 创建机器学习训练数据集...")

    # 指定训练数据的时间范围
    start_date = datetime(2025, 7, 1)
    end_date = datetime(2025, 9, 1)

    # 创建训练数据集
    training_df = feature_store.create_training_dataset(
        start_date=start_date, end_date=end_date
    )

    logger.info("✅ 训练数据集创建成功！")
    logger.info(f"📊 数据集包含 {len(training_df)} 条记录")
    logger.info(f"🔢 特征数量: {len(training_df.columns)}")

    return training_df


def example_feature_statistics(feature_store: FootballFeatureStore) -> None:
    """
    示例：获取特征统计信息

    Args:
        feature_store: 特征仓库实例
    """
    logger.info("📊 获取特征统计信息...")

    # 获取不同特征视图的统计
    feature_views = ["team_recent_stats", "odds_features", "match_features"]

    for fv_name in feature_views:
        try:
            _stats = feature_store.get_feature_statistics(fv_name)
            logger.info(f"\n🔍 特征视图: {fv_name}")
            logger.info(f"  📈 特征数量: {stats.get('num_features', 'N/A')}")
            logger.info(f"  🏷️  实体: {', '.join(stats.get('entities', []))}")
            logger.info(f"  ⏰ TTL: {stats.get('ttl_days', 'N/A')} 天")
            logger.info(f"  🏷️  标签: {stats.get('tags', {})}")
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.info(f"❌ 获取 {fv_name} 统计失败: {str(e)}")


def example_list_all_features(feature_store: FootballFeatureStore) -> None:
    """
    示例：列出所有特征

    Args:
        feature_store: 特征仓库实例
    """
    logger.info("📋 列出所有特征...")

    features_list = feature_store.list_features()

    if features_list:
        logger.info(f"✅ 发现 {len(features_list)} 个特征：\n")

        for i, feature in enumerate(features_list[:10]):  # 只显示前10个
            print(
                f"{i + 1:2d}. {feature['feature_view']:20s} | {feature['feature_name']:25s} | {feature['feature_type']}"
            )

        if len(features_list) > 10:
            logger.info(f"    ... 还有 {len(features_list) - 10} 个特征")
    else:
        logger.info("❌ 未找到任何特征")


async def run_complete_example() -> None:
    """
    运行完整的特征仓库示例
    """
    logger.info("🌟 足球特征仓库完整示例")
    logger.info("=" * 50)

    try:
        # 1. 初始化特征仓库
        feature_store = example_initialize_feature_store()

        # 2. 写入特征数据
        example_write_team_features(feature_store)
        example_write_odds_features(feature_store)

        logger.info("\n" + "=" * 50)

        # 3. 获取在线特征（实时预测场景）
        example_get_online_features(feature_store)

        logger.info("\n" + "=" * 50)

        # 4. 获取历史特征（模型训练场景）
        example_get_historical_features(feature_store)

        logger.info("\n" + "=" * 50)

        # 5. 创建训练数据集
        example_create_training_dataset(feature_store)

        logger.info("\n" + "=" * 50)

        # 6. 特征管理和统计
        example_feature_statistics(feature_store)
        example_list_all_features(feature_store)

        logger.info("\n" + "=" * 50)
        logger.info("✅ 所有示例运行成功！")

        # 7. 清理资源
        feature_store.close()
        logger.info("🔒 资源清理完成")

    except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
        logger.info(f"❌ 示例运行失败: {str(e)}")
        logger.error(f"Feature store example failed: {str(e)}", exc_info=True)


def example_integration_with_ml_pipeline() -> dict[str, Any]:
    """
    示例：与机器学习流水线集成

    展示如何在ML训练和预测流程中使用特征仓库。

    Returns:
        Dict[str, Any]: 集成示例结果
    """
    logger.info("🤖 特征仓库与ML流水线集成示例...")

    # 模拟ML训练流程
    def train_model_with_features():
        """模拟模型训练"""
        logger.info("  🎯 使用特征仓库数据训练模型...")

        # 获取特征仓库实例
        feature_store = get_feature_store()

        # 创建训练数据集
        training_df = feature_store.create_training_dataset(
            start_date=datetime(2025, 6, 1), end_date=datetime(2025, 8, 31)
        )

        logger.info(f"  📊 训练数据: {len(training_df)} 条记录")
        return {"model_trained": True, "training_samples": len(training_df)}

    # 模拟实时预测流程
    def predict_with_online_features():
        """模拟实时预测"""
        logger.info("  🔮 使用在线特征进行实时预测...")

        feature_store = get_feature_store()

        # 构建预测请求
        prediction_entities = pd.DataFrame([{"match_id": 3001}, {"match_id": 3002}])

        # 获取实时特征
        features_df = feature_store.get_online_features(
            feature_service_name="real_time_prediction_v1",
            entity_df=prediction_entities,
        )

        logger.info(f"  📈 预测特征: {len(features_df)} 条记录")
        return {"predictions_made": len(features_df)}

    # 执行集成示例
    results = {
        "training_result": train_model_with_features(),
        "prediction_result": predict_with_online_features(),
        "integration_status": "success",
    }

    logger.info("✅ ML流水线集成示例完成！")
    return results


if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)

    # 运行完整示例
    asyncio.run(run_complete_example())

    # 运行ML集成示例
    ml_results = example_integration_with_ml_pipeline()
    logger.info(f"\n🎉 ML集成结果: {ml_results}")
