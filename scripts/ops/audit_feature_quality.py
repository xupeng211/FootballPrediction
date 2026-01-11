#!/usr/bin/env python3
"""
V29.1 Feature Quality Audit - 特征含金量报告

功能：审计 match_features 表的数据质量，识别问题记录

指标：
1. 各联赛变盘次数（Odds Movements）平均值
2. 僵尸记录标记（只有一条赔率记录）
3. 特征完整性统计
4. 联赛覆盖情况

Author: 资深数据科学家 & SRE
Date: 2026-01-11
Version: V29.1 (Feature Quality Audit)
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# ============================================================================
# 数据库连接
# ============================================================================

def get_db_connection():
    """获取数据库连接"""
    settings = get_settings()
    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor
    )


# ============================================================================
# 特征质量审计
# ============================================================================

def audit_odds_movement_by_league() -> List[Dict[str, Any]]:
    """审计各联赛的变盘情况

    变盘定义：opening != closing 或存在 high_24h/low_24h

    Returns:
        各联赛的变盘统计
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 计算各联赛的变盘次数
            cur.execute("""
                SELECT
                    m.league_name,
                    COUNT(f.match_id) as total_matches,
                    -- 有 opening 和 closing 的记录
                    COUNT(f.opening_home) as with_opening,
                    COUNT(f.closing_home) as with_closing,
                    -- 变盘次数：opening != closing
                    COUNT(CASE
                        WHEN f.opening_home IS NOT NULL
                            AND f.closing_home IS NOT NULL
                            AND ABS(f.opening_home - f.closing_home) > 0.01
                        THEN 1
                    END) as home_movement_count,
                    COUNT(CASE
                        WHEN f.opening_draw IS NOT NULL
                            AND f.closing_draw IS NOT NULL
                            AND ABS(f.opening_draw - f.closing_draw) > 0.01
                        THEN 1
                    END) as draw_movement_count,
                    COUNT(CASE
                        WHEN f.opening_away IS NOT NULL
                            AND f.closing_away IS NOT NULL
                            AND ABS(f.opening_away - f.closing_away) > 0.01
                        THEN 1
                    END) as away_movement_count,
                    -- 24h 波动范围
                    COUNT(f.high_24h_home) as with_high_24h,
                    COUNT(f.low_24h_home) as with_low_24h
                FROM match_features f
                JOIN matches m ON f.match_id = m.match_id
                GROUP BY m.league_name
                ORDER BY total_matches DESC
            """)

            results = []
            for row in cur.fetchall():
                # 计算变盘率
                total_with_both = row['with_opening']  # 有 opening 的记录数

                if total_with_both > 0:
                    movement_count = (
                        row['home_movement_count'] +
                        row['draw_movement_count'] +
                        row['away_movement_count']
                    )
                    avg_movements_per_match = movement_count / total_with_both
                    movement_rate = (movement_count / (total_with_both * 3)) * 100  # 3 个赔率项
                else:
                    avg_movements_per_match = 0
                    movement_rate = 0

                results.append({
                    "league": row['league_name'],
                    "total_matches": row['total_matches'],
                    "with_opening": row['with_opening'],
                    "with_closing": row['with_closing'],
                    "movements_detected": (
                        row['home_movement_count'] +
                        row['draw_movement_count'] +
                        row['away_movement_count']
                    ),
                    "avg_movements_per_match": round(avg_movements_per_match, 2),
                    "movement_rate": round(movement_rate, 2),
                    "with_high_24h": row['with_high_24h'],
                    "with_low_24h": row['with_low_24h'],
                })

            return results

    finally:
        conn.close()


def identify_zombie_records() -> List[Dict[str, Any]]:
    """识别僵尸记录（只有 opening，没有 closing/high_24h/low_24h）

    Returns:
        僵尸记录列表
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 查找僵尸记录
            cur.execute("""
                SELECT
                    f.match_id,
                    m.league_name,
                    m.home_team,
                    m.away_team,
                    f.opening_home,
                    f.closing_home IS NULL as missing_closing,
                    f.high_24h_home IS NULL as missing_high_24h,
                    f.low_24h_home IS NULL as missing_low_24h,
                    f.created_at
                FROM match_features f
                JOIN matches m ON f.match_id = m.match_id
                WHERE f.opening_home IS NOT NULL
                    AND f.closing_home IS NULL
                    AND f.high_24h_home IS NULL
                    AND f.low_24h_home IS NULL
                ORDER BY m.league_name, f.created_at DESC
                LIMIT 100
            """)

            results = []
            for row in cur.fetchall():
                results.append({
                    "match_id": row['match_id'],
                    "league": row['league_name'],
                    "home_team": row['home_team'],
                    "away_team": row['away_team'],
                    "opening_home": row['opening_home'],
                    "missing_closing": row['missing_closing'],
                    "missing_high_24h": row['missing_high_24h'],
                    "missing_low_24h": row['missing_low_24h'],
                    "created_at": row['created_at'],
                })

            return results

    finally:
        conn.close()


def audit_feature_completeness() -> Dict[str, Any]:
    """审计特征完整性

    Returns:
        特征完整性统计
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 完整性统计
            cur.execute("""
                SELECT
                    COUNT(*) as total_features,
                    COUNT(opening_home) as with_opening,
                    COUNT(closing_home) as with_closing,
                    COUNT(high_24h_home) as with_high_24h,
                    COUNT(low_24h_home) as with_low_24h,
                    -- 完整记录（所有 12 个字段都有值）
                    COUNT(CASE
                        WHEN opening_home IS NOT NULL
                            AND opening_draw IS NOT NULL
                            AND opening_away IS NOT NULL
                            AND closing_home IS NOT NULL
                            AND closing_draw IS NOT NULL
                            AND closing_away IS NOT NULL
                            AND high_24h_home IS NOT NULL
                            AND high_24h_draw IS NOT NULL
                            AND high_24h_away IS NOT NULL
                            AND low_24h_home IS NOT NULL
                            AND low_24h_draw IS NOT NULL
                            AND low_24h_away IS NOT NULL
                        THEN 1
                    END) as complete_records
                FROM match_features
            """)

            row = cur.fetchone()

            total = row['total_features']
            if total > 0:
                completeness = {
                    "total_features": total,
                    "with_opening": row['with_opening'],
                    "with_closing": row['with_closing'],
                    "with_high_24h": row['with_high_24h'],
                    "with_low_24h": row['with_low_24h'],
                    "complete_records": row['complete_records'],
                    "opening_pct": round(row['with_opening'] / total * 100, 2),
                    "closing_pct": round(row['with_closing'] / total * 100, 2),
                    "high_24h_pct": round(row['with_high_24h'] / total * 100, 2),
                    "low_24h_pct": round(row['with_low_24h'] / total * 100, 2),
                    "complete_pct": round(row['complete_records'] / total * 100, 2),
                }
            else:
                completeness = {
                    "total_features": 0,
                    "message": "No features found"
                }

            return completeness

    finally:
        conn.close()


def audit_league_coverage() -> List[Dict[str, Any]]:
    """审计联赛覆盖情况

    Returns:
        各联赛的特征提取覆盖率
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    m.league_name,
                    COUNT(DISTINCT m.match_id) as total_matches_in_view,
                    COUNT(DISTINCT f.match_id) as matches_with_features,
                    ROUND(
                        100.0 * COUNT(DISTINCT f.match_id) /
                        NULLIF(COUNT(DISTINCT m.match_id), 0),
                        2
                    ) as coverage_pct
                FROM v_matches_clean m
                LEFT JOIN match_features f ON m.match_id = f.match_id
                GROUP BY m.league_name
                ORDER BY total_matches_in_view DESC
            """)

            results = []
            for row in cur.fetchall():
                results.append({
                    "league": row['league_name'],
                    "total_matches": row['total_matches_in_view'],
                    "with_features": row['matches_with_features'],
                    "coverage_pct": row['coverage_pct'],
                })

            return results

    finally:
        conn.close()


# ============================================================================
# 报告生成
# ============================================================================

def print_quality_report():
    """打印特征含金量报告"""
    print("=" * 70)
    print("📊 V29.1 特征含金量报告 (Feature Quality Audit)")
    print("=" * 70)
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")

    # 1. 特征完整性
    print("📈 1. 特征完整性统计")
    print("-" * 70)
    completeness = audit_feature_completeness()

    if completeness.get("total_features", 0) > 0:
        print(f"总特征记录数: {completeness['total_features']}")
        print(f"完整记录数 (12/12 字段): {completeness['complete_records']} ({completeness['complete_pct']}%)")
        print("")
        print("字段覆盖率:")
        print(f"  - Opening (初盘): {completeness['with_opening']} ({completeness['opening_pct']}%)")
        print(f"  - Closing (终盘): {completeness['with_closing']} ({completeness['closing_pct']}%)")
        print(f"  - High 24h: {completeness['with_high_24h']} ({completeness['high_24h_pct']}%)")
        print(f"  - Low 24h: {completeness['with_low_24h']} ({completeness['low_24h_pct']}%)")
    else:
        print("⚠️ 未找到特征记录")
    print("")

    # 2. 各联赛变盘情况
    print("📊 2. 各联赛变盘情况 (Odds Movements)")
    print("-" * 70)
    movements = audit_odds_movement_by_league()

    if movements:
        print(f"{'联赛':<20} {'总场次':<10} {'变盘次数':<12} {'平均变盘/场':<15} {'变盘率':<10}")
        print("-" * 70)
        for item in movements[:10]:  # 显示前 10 个联赛
            print(f"{item['league']:<20} {item['total_matches']:<10} "
                  f"{item['movements_detected']:<12} "
                  f"{item['avg_movements_per_match']:<15} "
                  f"{item['movement_rate']}%")
    else:
        print("⚠️ 未找到变盘数据")
    print("")

    # 3. 僵尸记录
    print("🧟 3. 僵尸记录 (只有 Opening，缺少 Closing/High_24h/Low_24h)")
    print("-" * 70)
    zombies = identify_zombie_records()

    if zombies:
        print(f"发现 {len(zombies)} 条僵尸记录（显示前 20 条）:")
        print("")
        for i, zombie in enumerate(zombies[:20], 1):
            print(f"{i}. [{zombie['league']}] {zombie['home_team']} vs {zombie['away_team']}")
            print(f"   Match ID: {zombie['match_id']}")
            print(f"   Opening: {zombie['opening_home']}, Missing: "
                  f"Closing={zombie['missing_closing']}, "
                  f"High_24h={zombie['missing_high_24h']}, "
                  f"Low_24h={zombie['missing_low_24h']}")
            print(f"   Created: {zombie['created_at']}")
            print("")

        if len(zombies) >= 100:
            print(f"... 还有 {len(zombies) - 20} 条僵尸记录未显示")
    else:
        print("✅ 未发现僵尸记录")
    print("")

    # 4. 联赛覆盖情况
    print("🌍 4. 联赛覆盖情况")
    print("-" * 70)
    coverage = audit_league_coverage()

    if coverage:
        print(f"{'联赛':<20} {'总场次':<12} {'已提取特征':<15} {'覆盖率':<10}")
        print("-" * 70)
        for item in coverage:
            status = "✅" if item['coverage_pct'] >= 80 else "⚠️" if item['coverage_pct'] >= 50 else "❌"
            print(f"{status} {item['league']:<18} {item['total_matches']:<12} "
                  f"{item['with_features']:<15} {item['coverage_pct']}%")
    else:
        print("⚠️ 未找到覆盖数据")
    print("")

    print("=" * 70)
    print("💡 改进建议:")
    print("  1. 僵尸记录：需要重新采集赔率数据或标记为低质量")
    print("  2. 覆盖率 < 80%：运行增量提取补充特征")
    print("  3. 变盘率过低：检查赔率源是否正常工作")
    print("=" * 70)


# ============================================================================
# 主入口
# ============================================================================

def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description="V29.1 Feature Quality Audit")
    parser.add_argument("--json", action="store_true",
                        help="输出 JSON 格式报告")

    args = parser.parse_args()

    if args.json:
        # JSON 输出
        import json
        report = {
            "timestamp": datetime.now().isoformat(),
            "completeness": audit_feature_completeness(),
            "movements_by_league": audit_odds_movement_by_league(),
            "zombie_records": identify_zombie_records(),
            "league_coverage": audit_league_coverage(),
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        # 文本输出
        print_quality_report()


if __name__ == "__main__":
    main()
