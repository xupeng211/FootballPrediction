#!/usr/bin/env python3
"""
V26.1 特征固化脚本 (Feature Hardening)
将 adaptive_features 中的球员级数据聚合为球队级特征，并回填到基础列
"""

import subprocess
import json
from typing import Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from tqdm import tqdm

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings


def get_db_connection():
    """获取数据库连接"""
    settings = get_settings()
    db = settings.database

    return psycopg2.connect(
        host=db.host,
        port=db.port,
        database=db.name,
        user=db.user,
        password=db.password.get_secret_value()
    )


def extract_team_rating(adaptive_features: dict) -> tuple:
    """
    提取球队评分
    Returns: (home_rating, away_rating)
    """
    home_rating = adaptive_features.get('content_lineup_hometeam_rating')
    away_rating = adaptive_features.get('content_lineup_awayteam_rating')

    return home_rating, away_rating


def aggregate_team_xg(adaptive_features: dict) -> tuple:
    """
    聚合球队 xG（从球员统计数据中）
    Returns: (home_xg, away_xg)
    """
    home_xg = 0.0
    away_xg = 0.0

    # 获取球队 ID
    home_team_id = adaptive_features.get('general_hometeam_id')
    away_team_id = adaptive_features.get('general_awayteam_id')

    # 遍历所有球员统计
    for key, value in adaptive_features.items():
        if not key.startswith('content_playerstats_'):
            continue

        # 提取球员 xG
        if 'stats_attack_stats_xg_non_penalty_stat_value' in key or 'stats_top_stats_stats_expected_goals_xg_stat_value' in key:
            if isinstance(value, (int, float)) and value > 0:
                # 尝试从键中推断球队（这需要 lineup 数据，暂时简化处理）
                # 简化：所有球员 xG 加总，然后按主场/客场划分
                pass

    # 使用事件 xG 作为备选
    # header_events_hometeamgoals_*_shotmapevent_expectedgoals
    home_event_xg = 0.0
    away_event_xg = 0.0

    for key, value in adaptive_features.items():
        if 'header_events_hometeamgoals' in key and 'shotmapevent_expectedgoals' in key:
            if isinstance(value, (int, float)):
                home_event_xg += value
        elif 'header_events_awayteamgoals' in key and 'shotmapevent_expectedgoals' in key:
            if isinstance(value, (int, float)):
                away_event_xg += value

    return home_event_xg, away_event_xg


def extract_possession(adaptive_features: dict) -> tuple:
    """
    提取控球率（如果有）
    Returns: (home_possession, away_possession)
    """
    # 尝试从不同位置获取控球率
    home_poss = adaptive_features.get('content_matchfacts_stats_stats_possession')
    away_poss = None

    if isinstance(home_poss, (int, float)):
        # 如果只有一个值，可能需要推断客场
        away_poss = 100 - home_poss if home_poss <= 100 else None

    return home_poss, away_poss


def extract_shots_on_target(adaptive_features: dict) -> tuple:
    """
    提取射正次数（从 shotmap 中统计）
    Returns: (home_sot, away_sot)
    """
    home_sot = 0
    away_sot = 0

    # content_shotmap_shots_* 中有 x, y 坐标
    # 需要判断哪些是主队的射门
    home_team_id = adaptive_features.get('general_hometeam_id')

    for key, value in adaptive_features.items():
        if key.startswith('content_shotmap_shots_') and key.endswith('_teamid'):
            shot_idx = key.split('_')[3]
            team_id = value

            # 检查是否射正（这需要更复杂的逻辑，简化处理）
            # 统计射门数量作为代理
            if team_id == home_team_id:
                home_sot += 1
            else:
                away_sot += 1

    return home_sot, away_sot


def harden_features_batch(conn, batch_size: int = 100) -> dict:
    """
    批量固化特征
    Returns: 统计信息
    """
    stats = {
        'processed': 0,
        'home_rating_filled': 0,
        'away_rating_filled': 0,
        'home_xg_filled': 0,
        'away_xg_filled': 0,
    }

    # 获取需要处理的记录
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT match_id, adaptive_features
            FROM match_features_training
            WHERE adaptive_features IS NOT NULL
            AND feature_count > 0
            AND (
                rolling_xg_home IS NULL OR
                rolling_xg_away IS NULL OR
                rolling_team_rating_home IS NULL OR
                rolling_team_rating_away IS NULL
            )
            ORDER BY match_date
        """)

        rows = cur.fetchall()

    print(f"📦 需要处理的记录: {len(rows)}")

    # 批量处理
    for row in tqdm(rows, desc="固化特征"):
        match_id = row['match_id']
        af = row['adaptive_features']

        if not af:
            continue

        # 提取特征
        home_rating, away_rating = extract_team_rating(af)
        home_xg, away_xg = aggregate_team_xg(af)

        # 构建更新
        updates = []
        values = []

        if home_rating is not None and home_rating > 0:
            updates.append("rolling_team_rating_home = %s")
            values.append(home_rating)
            stats['home_rating_filled'] += 1

        if away_rating is not None and away_rating > 0:
            updates.append("rolling_team_rating_away = %s")
            values.append(away_rating)
            stats['away_rating_filled'] += 1

        if home_xg > 0:
            updates.append("rolling_xg_home = %s")
            values.append(home_xg)
            stats['home_xg_filled'] += 1

        if away_xg > 0:
            updates.append("rolling_xg_away = %s")
            values.append(away_xg)
            stats['away_xg_filled'] += 1

        if updates:
            values.append(match_id)
            query = f"""
                UPDATE match_features_training
                SET {', '.join(updates)}
                WHERE match_id = %s
            """

            with conn.cursor() as cur:
                cur.execute(query, values)

            stats['processed'] += 1

        # 定期提交
        if stats['processed'] % batch_size == 0:
            conn.commit()

    conn.commit()
    return stats


def print_fill_rate_report(conn):
    """打印填充率报表"""
    print("\n" + "=" * 60)
    print("📊 特征填充率报表")
    print("=" * 60)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(rolling_xg_home) as has_xg_home,
                COUNT(rolling_xg_away) as has_xg_away,
                COUNT(rolling_team_rating_home) as has_rating_home,
                COUNT(rolling_team_rating_away) as has_rating_away,
                AVG(rolling_xg_home) as avg_xg_home,
                AVG(rolling_xg_away) as avg_xg_away,
                AVG(rolling_team_rating_home) as avg_rating_home,
                AVG(rolling_team_rating_away) as avg_rating_away
            FROM match_features_training
        """)

        row = cur.fetchone()

        print(f"\n总记录数: {row[0]}")
        print(f"\n--- XG 特征 ---")
        print(f"  主队 XG:  {row[1]} / {row[0]} ({row[1]/row[0]*100:.1f}%) | 平均值: {row[5]:.3f}")
        print(f"  客队 XG:  {row[2]} / {row[0]} ({row[2]/row[0]*100:.1f}%) | 平均值: {row[6]:.3f}")
        print(f"\n--- Rating 特征 ---")
        print(f"  主队评分: {row[3]} / {row[0]} ({row[3]/row[0]*100:.1f}%) | 平均值: {row[7]:.3f}")
        print(f"  客队评分: {row[4]} / {row[0]} ({row[4]/row[0]*100:.1f}%) | 平均值: {row[8]:.3f}")


def main():
    """主函数"""
    print("=" * 60)
    print("V26.1 特征固化 (Feature Hardening)")
    print("=" * 60)

    conn = get_db_connection()

    try:
        # 执行固化
        stats = harden_features_batch(conn)

        # 打印统计
        print(f"\n✅ 固化完成:")
        print(f"  处理记录: {stats['processed']}")
        print(f"  主队评分填充: {stats['home_rating_filled']}")
        print(f"  客队评分填充: {stats['away_rating_filled']}")
        print(f"  主队 XG 填充: {stats['home_xg_filled']}")
        print(f"  客队 XG 填充: {stats['away_xg_filled']}")

        # 填充率报表
        print_fill_rate_report(conn)

    finally:
        conn.close()

    print("\n" + "=" * 60)
    print("✅ 特征固化完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
