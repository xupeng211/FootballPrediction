#!/usr/bin/env python3
"""
V26.7 对齐训练集生成器
======================

遍历数据库中的所有历史比赛，使用 SchemaManager 的真实 SQL 方法
为每场比赛重新生成 19 维赛前特征，确保训练-推理完全对齐。

核心原则：模拟真实"赛前一刻"的数据状态。

Author: ML Ops Engineer
Date: 2025-12-28
Phase: 5.5 - 全动态特征流
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

from src.config_unified import get_settings
from src.database.schema_manager import SchemaManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_aligned_dataset():
    """
    生成完全对齐的训练数据集

    过程：
    1. 从数据库查询所有已完成的比赛
    2. 对每场比赛，使用 before_match_time 模拟赛前状态
    3. 调用 SchemaManager 方法计算所有特征
    4. 生成新的 DataFrame 保存到磁盘
    """
    logger.info("=" * 70)
    logger.info("V26.7 对齐训练集生成器")
    logger.info("=" * 70)

    # 1. 获取数据库连接
    settings = get_settings()
    import psycopg2

    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    cur = conn.cursor()

    # 2. 查询所有已完成的比赛（按时间排序，确保时序正确）
    logger.info("查询数据库中的历史比赛...")
    cur.execute("""
        SELECT
            m.id,
            m.home_team,
            m.away_team,
            m.home_score,
            m.away_score,
            m.match_time,
            m.league_name
        FROM matches m
        WHERE m.home_score IS NOT NULL
            AND m.away_score IS NOT NULL
            AND m.is_finished = true
        ORDER BY m.match_time ASC
    """)

    matches = cur.fetchall()
    logger.info(f"✅ 找到 {len(matches)} 场已完成比赛")

    cur.close()
    conn.close()

    # 3. 为每场比赛生成动态特征
    logger.info("\n开始生成动态特征（模拟赛前状态）...")
    logger.info("⚠️  这可能需要几分钟，请耐心等待...")

    records = []
    errors = []

    start_time = time.time()

    for idx, match in enumerate(tqdm(matches, desc="生成特征"), 1):
        match_id, home_team, away_team, home_score, away_score, match_time, league = match

        try:
            # 确定比赛结果
            if home_score > away_score:
                result = "home"
            elif away_score > home_score:
                result = "away"
            else:
                result = "draw"

            # 传入 match_time 作为 before_match_time，模拟赛前状态
            match_time_str = str(match_time)

            # 获取滚动特征
            home_stats = SchemaManager.get_team_rolling_stats(
                team_name=home_team,
                n_matches=5,
                before_match_time=match_time_str
            )
            away_stats = SchemaManager.get_team_rolling_stats(
                team_name=away_team,
                n_matches=5,
                before_match_time=match_time_str
            )

            # 获取积分榜特征
            home_standings = SchemaManager.get_team_standings(
                team_name=home_team,
                before_match_time=match_time_str
            )
            away_standings = SchemaManager.get_team_standings(
                team_name=away_team,
                before_match_time=match_time_str
            )

            # 获取 ELO 评分
            elo_ratings = SchemaManager.get_elo_ratings(
                team_names=[home_team, away_team],
                before_match_time=match_time_str
            )
            home_elo = elo_ratings.get(home_team, 1500.0)
            away_elo = elo_ratings.get(away_team, 1500.0)

            # 获取疲劳度
            home_fatigue = SchemaManager.get_team_fatigue_index(
                team_name=home_team,
                match_time=match_time_str,
                lookback_days=7
            )
            away_fatigue = SchemaManager.get_team_fatigue_index(
                team_name=away_team,
                match_time=match_time_str,
                lookback_days=7
            )

            # 计算 rolling_team_rating
            home_rating = (
                home_stats["rolling_xg"] * 0.4 +
                home_stats["rolling_possession"] / 100 * 0.3 +
                home_stats["rolling_shots_on_target"] / 10 * 0.3
            ) * 2
            away_rating = (
                away_stats["rolling_xg"] * 0.4 +
                away_stats["rolling_possession"] / 100 * 0.3 +
                away_stats["rolling_shots_on_target"] / 10 * 0.3
            ) * 2

            # 构建特征记录
            record = {
                # 标识
                "match_id": match_id,
                "home_team": home_team,
                "away_team": away_team,
                "match_time": match_time,
                "result": result,
                # 滚动特征 (8个)
                "rolling_xg_home": home_stats["rolling_xg"],
                "rolling_xg_away": away_stats["rolling_xg"],
                "rolling_shots_on_target_home": home_stats["rolling_shots_on_target"],
                "rolling_shots_on_target_away": away_stats["rolling_shots_on_target"],
                "rolling_possession_home": home_stats["rolling_possession"],
                "rolling_possession_away": away_stats["rolling_possession"],
                "rolling_team_rating_home": min(10.0, max(0.0, home_rating)),
                "rolling_team_rating_away": min(10.0, max(0.0, away_rating)),
                # 积分榜特征 (7个)
                "home_table_position": home_standings["position"],
                "away_table_position": away_standings["position"],
                "table_position_diff": home_standings["position"] - away_standings["position"],
                "home_points": home_standings["points"],
                "away_points": away_standings["points"],
                "points_diff": home_standings["points"] - away_standings["points"],
                "home_recent_form_points": home_standings["recent_form_points"],
                # 高级特征 (4个)
                "raw_elo_gap": home_elo - away_elo,
                "adjusted_elo_gap": (home_elo - away_elo) * 0.1,
                "home_fatigue_index": home_fatigue,
                "away_fatigue_index": away_fatigue,
                "fatigue_diff": home_fatigue - away_fatigue,
            }

            records.append(record)

        except Exception as e:
            errors.append({
                "match_id": match_id,
                "home_team": home_team,
                "away_team": away_team,
                "error": str(e),
            })
            if len(errors) <= 5:
                logger.warning(f"⚠️  处理失败 {home_team} vs {away_team}: {e}")

    elapsed = time.time() - start_time

    logger.info(f"\n✅ 特征生成完成!")
    logger.info(f"  成功: {len(records)} 场")
    logger.info(f"  失败: {len(errors)} 场")
    logger.info(f"  耗时: {elapsed:.1f} 秒")

    # 4. 构建 DataFrame 并保存
    df = pd.DataFrame(records)

    # 数据质量检查
    logger.info("\n数据质量检查:")
    logger.info(f"  总记录数: {len(df)}")
    logger.info(f"  标签分布: {df['result'].value_counts().to_dict()}")

    # 检查缺失值
    missing = df.isnull().sum()
    if missing.sum() > 0:
        logger.warning(f"  缺失值: {missing[missing > 0].to_dict()}")
        df = df.fillna(0)  # 填充缺失值
    else:
        logger.info("  ✅ 无缺失值")

    # 保存数据集
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "V26_7_ALIGNED_TRAINING.parquet"
    df.to_parquet(output_path, index=False)
    logger.info(f"\n✅ 数据集已保存: {output_path}")

    # 保存元数据
    metadata = {
        "version": "26.7",
        "description": "Fully aligned training set using dynamic SQL methods",
        "total_matches": len(df),
        "label_distribution": df["result"].value_counts().to_dict(),
        "feature_columns": [
            "rolling_xg_home", "rolling_xg_away",
            "rolling_shots_on_target_home", "rolling_shots_on_target_away",
            "rolling_possession_home", "rolling_possession_away",
            "rolling_team_rating_home", "rolling_team_rating_away",
            "home_table_position", "away_table_position", "table_position_diff",
            "home_points", "away_points", "points_diff", "home_recent_form_points",
            "raw_elo_gap", "adjusted_elo_gap",
            "home_fatigue_index", "away_fatigue_index", "fatigue_diff",
        ],
        "generation_time": datetime.now().isoformat(),
        "generation_duration_seconds": elapsed,
        "errors": errors[:10],  # 只保存前10个错误
    }

    metadata_path = output_dir / "V26_7_ALIGNED_TRAINING_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    logger.info(f"✅ 元数据已保存: {metadata_path}")

    logger.info("\n" + "=" * 70)
    logger.info("✅ V26.7 对齐训练集生成完成！")
    logger.info("=" * 70)

    return df, metadata


if __name__ == "__main__":
    df, metadata = generate_aligned_dataset()
