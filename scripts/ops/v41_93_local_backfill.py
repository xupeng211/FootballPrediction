#!/usr/bin/env python3
"""
V41.93 "内爆解析" - 存量数据本地回填引擎
==============================================

任务：不联网！直接从数据库读取 l2_raw_json，提取高级特征并回填

核心逻辑：
1. 应用 V41.91 修复的嵌套解析算法（处理 type="text" 的 stats 数组）
2. 遍历所有存量 JSON，提取 xG、进球、红黄牌、控球率等 20+ 核心生产指标
3. UPDATE 指令回填到 l2_extracted_features 字段

作者：Claude Code
日期：2026-01-16
"""

import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from tqdm import tqdm

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/v41_93_local_backfill.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# V41.91 修复的嵌套解析算法
# ============================================================================

def safe_parse_stat(stats_values: list, index: int) -> float | None:
    """安全解析统计值

    Args:
        stats_values: 统计值数组
        index: 索引位置 (0=home, 1=away)

    Returns:
        浮点数或 None
    """
    if not isinstance(stats_values, list) or len(stats_values) <= index:
        return None

    value = stats_values[index]
    if value is None:
        return None

    # 处理字符串格式的数值 (如 "202 (72%)")
    if isinstance(value, str):
        # 提取数字部分
        match = re.search(r'([0-9]+\.?[0-9]*)', value)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, IndexError):
                return None
        return None

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def extract_stat_from_group(stat_group: dict, stat_key: str) -> tuple[float | None, float | None]:
    """从统计组中提取指定键的值

    Args:
        stat_group: 统计组字典
        stat_key: 要提取的键 (如 "expected_goals")

    Returns:
        Tuple[home_value, away_value]
    """
    if not isinstance(stat_group, dict):
        return None, None

    stats_list = stat_group.get("stats", [])
    if not isinstance(stats_list, list):
        return None, None

    for stat_item in stats_list:
        if not isinstance(stat_item, dict):
            continue

        key = stat_item.get("key", "")
        if key != stat_key:
            continue

        stats_values = stat_item.get("stats", [])
        if not isinstance(stats_values, list):
            continue

        # V41.91: 处理嵌套结构 - stats_values 可能是字典数组
        # 需要找到 type="text" 的元素（实际数据）
        actual_values = None
        if len(stats_values) > 0 and isinstance(stats_values[0], dict):
            # 嵌套结构: 找到 type="text" 的元素
            for item in stats_values:
                if isinstance(item, dict) and item.get("type") == "text":
                    actual_values = item.get("stats", [])
                    break
        elif len(stats_values) >= 2:
            # 直接结构: [home, away] 格式
            actual_values = stats_values

        if actual_values is None or len(actual_values) < 2:
            continue

        home_value = safe_parse_stat(actual_values, 0)
        away_value = safe_parse_stat(actual_values, 1)

        return home_value, away_value

    return None, None


def extract_advanced_features(l2_raw_json: dict) -> dict:
    """从 l2_raw_json 中提取高级特征

    Args:
        l2_raw_json: FotMob API 返回的原始 JSON

    Returns:
        特征字典
    """
    features = {}

    try:
        content = l2_raw_json.get("content", {})
        stats = content.get("stats", {})
        periods = stats.get("Periods", {})
        all_period = periods.get("All", {})
        all_stats = all_period.get("stats", [])

        if not isinstance(all_stats, list):
            return features

        # 定义要提取的特征映射
        # 格式: (API键, 特征键, 描述)
        feature_mappings = [
            # === xG 相关 (最重要) ===
            ("expected_goals", "home_xg", "away_xg", "Expected goals"),
            ("expected_goals_open_play", "home_xg_open_play", "away_xg_open_play", "xG open play"),
            ("expected_goals_set_play", "home_xg_set_play", "away_xg_set_play", "xG set play"),
            ("expected_goals_non_penalty", "home_xg_non_penalty", "away_xg_non_penalty", "xG non-penalty"),
            ("expected_goals_on_target", "home_xgot", "away_xgot", "xG on target"),

            # === 射门相关 ===
            ("total_shots", "home_shots_total", "away_shots_total", "Total shots"),
            ("ShotsOnTarget", "home_shots_on_target", "away_shots_on_target", "Shots on target"),
            ("ShotsOffTarget", "home_shots_off_target", "away_shots_off_target", "Shots off target"),
            ("blocked_shots", "home_shots_blocked", "away_shots_blocked", "Blocked shots"),
            ("shots_woodwork", "home_shots_woodwork", "away_shots_woodwork", "Hit woodwork"),
            ("shots_inside_box", "home_shots_inside_box", "away_shots_inside_box", "Shots inside box"),
            ("shots_outside_box", "home_shots_outside_box", "away_shots_outside_box", "Shots outside box"),
            ("big_chance", "home_big_chances", "away_big_chances", "Big chances"),
            ("big_chance_missed_title", "home_big_chances_missed", "away_big_chances_missed", "Big chances missed"),

            # === 传球相关 ===
            ("passes", "home_passes", "away_passes", "Passes"),
            ("accurate_passes", "home_passes_accurate", "away_passes_accurate", "Accurate passes"),
            ("own_half_passes", "home_passes_own_half", "away_passes_own_half", "Own half passes"),
            ("opposition_half_passes", "home_passes_opp_half", "away_passes_opp_half", "Opposition half passes"),
            ("long_balls_accurate", "home_long_balls_accurate", "away_long_balls_accurate", "Accurate long balls"),
            ("accurate_crosses", "home_crosses_accurate", "away_crosses_accurate", "Accurate crosses"),
            ("player_throws", "home_throws", "away_throws", "Throws"),
            ("touches_opp_box", "home_touches_opp_box", "away_touches_opp_box", "Touches in opposition box"),

            # === 防守相关 ===
            ("matchstats.headers.tackles", "home_tackles", "away_tackles", "Tackles"),
            ("interceptions", "home_interceptions", "away_interceptions", "Interceptions"),
            ("shot_blocks", "home_blocks", "away_blocks", "Blocks"),
            ("clearances", "home_clearances", "away_clearances", "Clearances"),
            ("keeper_saves", "home_keeper_saves", "away_keeper_saves", "Keeper saves"),

            # === 对抗相关 ===
            ("duel_won", "home_duels_won", "away_duels_won", "Duels won"),
            ("ground_duels_won", "home_ground_duels_won", "away_ground_duels_won", "Ground duels won"),
            ("aerials_won", "home_aerials_won", "away_aerials_won", "Aerial duels won"),
            ("dribbles_succeeded", "home_dribbles_succeeded", "away_dribbles_succeeded", "Successful dribbles"),

            # === 纪律相关 ===
            ("yellow_cards", "home_yellow_cards", "away_yellow_cards", "Yellow cards"),
            ("red_cards", "home_red_cards", "away_red_cards", "Red cards"),

            # === 其他 ===
            ("BallPossesion", "home_possession", "away_possession", "Ball possession"),
            ("fouls", "home_fouls", "away_fouls", "Fouls committed"),
            ("corners", "home_corners", "away_corners", "Corners"),
            ("Offsides", "home_offsides", "away_offsides", "Offsides"),
        ]

        # 遍历所有统计组（如 top_stats, shots, expected_goals 等）
        for stat_group in all_stats:
            if not isinstance(stat_group, dict):
                continue

            # 遍历所有特征映射并提取
            for stat_key, home_key, away_key, description in feature_mappings:
                # 检查是否已经提取过（避免重复）
                if home_key in features and away_key in features:
                    continue

                home_value, away_value = extract_stat_from_group(stat_group, stat_key)

                if home_value is not None:
                    features[home_key] = home_value
                if away_value is not None:
                    features[away_key] = away_value

    except Exception as e:
        logger.warning(f"⚠️ 特征提取失败: {e}")

    return features


# ============================================================================
# 数据库操作
# ============================================================================

def get_db_connection():
    """获取数据库连接"""
    import os
    from dotenv import load_dotenv

    # 加载环境变量
    load_dotenv()

    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="football_db",
        user="football_user",
        password=os.getenv("DB_PASSWORD", "football_pass"),
        cursor_factory=RealDictCursor
    )


def audit_existing_data(conn) -> dict:
    """审计现有数据

    Returns:
        审计结果字典
    """
    logger.info("=" * 70)
    logger.info("步骤 1/3: 深度资产普查")
    logger.info("=" * 70)

    audit_results = {}

    with conn.cursor() as cur:
        # 检查各赛季的数据规模
        logger.info("\n📊 各赛季数据规模:")
        cur.execute("""
            SELECT
                season,
                COUNT(*) as total_matches,
                COUNT(l2_raw_json) as with_l2_data,
                COUNT(l2_raw_json->'technical_features') as with_technical_features,
                COUNT(l2_raw_json->'technical_features'->'home_xg') as with_xg_data
            FROM matches
            GROUP BY season
            ORDER BY season DESC
        """)

        for row in cur:
            season = row['season']
            audit_results[season] = dict(row)
            logger.info(f"  {season}: {row['total_matches']} 场, "
                       f"L2数据: {row['with_l2_data']}, "
                       f"技术特征: {row['with_technical_features']}, "
                       f"xG数据: {row['with_xg_data']}")

        # 统计总计
        logger.info("\n📈 总计统计:")
        cur.execute("""
            SELECT
                COUNT(*) as total_matches,
                COUNT(l2_raw_json) as with_l2_data,
                COUNT(l2_raw_json->'technical_features') as with_technical_features,
                COUNT(l2_raw_json->'technical_features'->'home_xg') as with_xg_data
            FROM matches
            WHERE l2_raw_json IS NOT NULL
        """)

        row = cur.fetchone()
        audit_results['total'] = dict(row)
        logger.info(f"  总比赛数: {row['total_matches']}")
        logger.info(f"  有 L2 数据: {row['with_l2_data']}")
        logger.info(f"  有技术特征: {row['with_technical_features']}")
        logger.info(f"  有 xG 数据: {row['with_xg_data']}")

        # 统计需要回填的比赛
        logger.info("\n🎯 需要回填的比赛:")
        cur.execute("""
            SELECT
                season,
                COUNT(*) as needs_backfill
            FROM matches
            WHERE l2_raw_json IS NOT NULL
              AND (l2_raw_json->'technical_features' IS NULL
                   OR l2_raw_json->'technical_features' = '{}'::jsonb)
            GROUP BY season
            ORDER BY season DESC
        """)

        for row in cur:
            logger.info(f"  {row['season']}: {row['needs_backfill']} 场需要回fill")

    return audit_results


def backfill_matches(conn, season: str = None, limit: int = None) -> dict:
    """回填比赛的高级特征

    Args:
        conn: 数据库连接
        season: 赛季筛选 (None 表示所有赛季)
        limit: 限制处理数量 (None 表示不限制)

    Returns:
        回填结果统计
    """
    logger.info("\n" + "=" * 70)
    logger.info("步骤 2/3: 存量回填手术")
    logger.info("=" * 70)

    # 构建查询
    where_clauses = ["l2_raw_json IS NOT NULL",
                     "(l2_raw_json->'technical_features' IS NULL "
                     "OR l2_raw_json->'technical_features' = '{}'::jsonb)"]

    if season:
        where_clauses.append(f"season = '{season}'")

    where_sql = " AND ".join(where_clauses)

    limit_sql = f"LIMIT {limit}" if limit else ""

    with conn.cursor() as cur:
        # 获取需要回填的比赛
        query = f"""
            SELECT match_id, home_team, away_team, season, l2_raw_json
            FROM matches
            WHERE {where_sql}
            ORDER BY season, match_date
            {limit_sql}
        """

        logger.info(f"\n🔍 查询需要回fill的比赛...")
        cur.execute(query)
        matches_to_backfill = cur.fetchall()

        total_matches = len(matches_to_backfill)
        logger.info(f"  找到 {total_matches} 场比赛需要回填")

        if total_matches == 0:
            logger.warning("⚠️ 没有需要回填的比赛!")
            return {"total": 0, "success": 0, "failed": 0, "features_extracted": 0}

        # 统计结果
        stats = {
            "total": total_matches,
            "success": 0,
            "failed": 0,
            "features_extracted": 0,
            "failed_match_ids": []
        }

        # 逐个回填
        logger.info(f"\n🔧 开始回填处理...")
        for match in tqdm(matches_to_backfill, desc="回填进度"):
            match_id = match['match_id']
            l2_raw_json = match['l2_raw_json']

            try:
                # 提取高级特征
                features = extract_advanced_features(l2_raw_json)

                if not features:
                    logger.warning(f"  ⚠️ {match_id}: 未提取到任何特征")
                    stats["failed"] += 1
                    stats["failed_match_ids"].append(match_id)
                    continue

                # 更新数据库
                update_query = """
                    UPDATE matches
                    SET l2_raw_json = jsonb_set(l2_raw_json, '{technical_features}', %s::jsonb),
                        updated_at = NOW()
                    WHERE match_id = %s
                """

                cur.execute(update_query, (json.dumps(features), match_id))
                conn.commit()

                stats["success"] += 1
                stats["features_extracted"] += len(features)

                # 打印详细日志（每 100 场）
                if stats["success"] % 100 == 0:
                    home_xg = features.get("home_xg")
                    away_xg = features.get("away_xg")
                    logger.info(f"  ✅ 已处理 {stats['success']}/{total_matches} | "
                               f"最新: {match_id} | xG: {home_xg}-{away_xg}")

            except Exception as e:
                logger.error(f"  ❌ {match_id}: 回填失败 - {e}")
                stats["failed"] += 1
                stats["failed_match_ids"].append(match_id)
                conn.rollback()

    return stats


def verify_backfill_results(conn, season: str = None) -> dict:
    """验证回填结果

    Args:
        conn: 数据库连接
        season: 赛季筛选

    Returns:
        验证结果
    """
    logger.info("\n" + "=" * 70)
    logger.info("步骤 3/3: 验证与统计")
    logger.info("=" * 70)

    with conn.cursor() as cur:
        # 检查回填后的数据情况
        where_sql = f"WHERE season = '{season}'" if season else "WHERE l2_raw_json IS NOT NULL"

        logger.info("\n📊 回填后数据统计:")
        cur.execute(f"""
            SELECT
                season,
                COUNT(*) as total_matches,
                COUNT(l2_raw_json) as with_l2_data,
                COUNT(l2_raw_json->'technical_features') as with_technical_features,
                COUNT(l2_raw_json->'technical_features'->'home_xg') as with_xg_data,
                ROUND(100.0 * COUNT(l2_raw_json->'technical_features'->'home_xg') /
                      NULLIF(COUNT(l2_raw_json), 0), 2) as xg_coverage_rate
            FROM matches
            {where_sql}
            GROUP BY season
            ORDER BY season DESC
        """)

        verification_results = {}

        for row in cur:
            season_key = row['season']
            verification_results[season_key] = dict(row)
            logger.info(f"  {season_key}:")
            logger.info(f"    总比赛: {row['total_matches']}")
            logger.info(f"    有 L2 数据: {row['with_l2_data']}")
            logger.info(f"    有技术特征: {row['with_technical_features']}")
            logger.info(f"    有 xG 数据: {row['with_xg_data']}")
            logger.info(f"    xG 覆盖率: {row['xg_coverage_rate']}%")

        # 抽样检查几场比赛
        logger.info("\n🎲 抽样检查 (最近 5 场):")
        cur.execute(f"""
            SELECT
                match_id,
                home_team,
                away_team,
                (l2_raw_json->'technical_features'->'home_xg')::text::numeric as home_xg,
                (l2_raw_json->'technical_features'->'away_xg')::text::numeric as away_xg,
                updated_at
            FROM matches
            WHERE l2_raw_json->'technical_features'->'home_xg' IS NOT NULL
            ORDER BY updated_at DESC
            LIMIT 5
        """)

        for row in cur:
            logger.info(f"  ✅ {row['match_id']}: {row['home_team']} vs {row['away_team']} | "
                       f"xG: {row['home_xg']}-{row['away_xg']} | "
                       f"更新时间: {row['updated_at']}")

    return verification_results


def main():
    """主函数"""
    logger.info("=" * 70)
    logger.info("V41.93 \"内爆解析\" - 存量数据本地回填引擎")
    logger.info("=" * 70)
    logger.info(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(" ")

    # 创建日志目录
    Path("logs").mkdir(exist_ok=True)

    # 获取数据库连接
    conn = get_db_connection()

    try:
        # 步骤 1: 深度资产普查
        audit_results = audit_existing_data(conn)

        # 步骤 2: 存量回填手术
        # 先处理 2023/2024 赛季
        stats = backfill_matches(conn, season="2023/2024", limit=None)

        # 步骤 3: 验证与统计
        verification_results = verify_backfill_results(conn, season="2023/2024")

        # 输出最终统计
        logger.info(" ")
        logger.info("=" * 70)
        logger.info("📊 最终统计报告")
        logger.info("=" * 70)
        logger.info(f"总处理: {stats['total']} 场")
        logger.info(f"成功: {stats['success']} 场")
        logger.info(f"失败: {stats['failed']} 场")
        if stats['total'] > 0:
            logger.info(f"成功率: {100.0 * stats['success'] / stats['total']:.2f}%")
        logger.info(f"提取特征总数: {stats['features_extracted']} 个")
        if stats['success'] > 0:
            logger.info(f"平均每场: {stats['features_extracted'] / stats['success']:.1f} 个特征")

        if stats['failed_match_ids']:
            logger.warning(f"⚠️ 失败的比赛 ({len(stats['failed_match_ids'])} 场):")
            for match_id in stats['failed_match_ids'][:10]:
                logger.warning(f"  - {match_id}")
            if len(stats['failed_match_ids']) > 10:
                logger.warning(f"  ... 还有 {len(stats['failed_match_ids']) - 10} 场")

        logger.info(" ")
        logger.info("=" * 70)
        logger.info("🎉 V41.93 任务完成!")
        logger.info("=" * 70)
        logger.info(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return 0 if stats['failed'] == 0 else 1

    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
