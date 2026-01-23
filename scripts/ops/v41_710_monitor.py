#!/usr/bin/env python3
"""V41.710 进度监控脚本.

用于监控英超哈希补全进度.
"""

import psycopg2
from src.config_unified import get_settings
from psycopg2.extras import RealDictCursor


def check_progress():
    """检查英超 2024/2025 赛季哈希补全进度."""
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )

    cur = conn.cursor()

    # 查询总比赛数
    cur.execute("""
        SELECT COUNT(*) as total
        FROM matches
        WHERE league_name = 'Premier League'
        AND season = '2024/2025'
    """)
    total = cur.fetchone()["total"]

    # 查询有哈希的比赛数
    cur.execute("""
        SELECT COUNT(*) as with_hash
        FROM matches m
        JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
        WHERE m.league_name = 'Premier League'
        AND m.season = '2024/2025'
        AND mm.oddsportal_hash IS NOT NULL
        AND mm.oddsportal_hash != ''
    """)
    with_hash = cur.fetchone()["with_hash"]

    # 计算覆盖率
    coverage = (with_hash / total * 100) if total > 0 else 0

    print("=" * 60)
    print("V41.710 英超哈希补全进度")
    print("=" * 60)
    print(f"总比赛数: {total}")
    print(f"已有哈希: {with_hash}")
    print(f"缺失哈希: {total - with_hash}")
    print(f"覆盖率: {coverage:.1f}%")
    print("=" * 60)

    # 检查最近的采集记录
    cur.execute("""
        SELECT mm.*, m.home_team, m.away_team, m.match_date
        FROM matches_mapping mm
        JOIN matches m ON mm.fotmob_id = m.match_id
        WHERE m.league_name = 'Premier League'
        AND m.season = '2024/2025'
        ORDER BY mm.updated_at DESC
        LIMIT 5
    """)
    recent = cur.fetchall()

    print("\n最近 5 条采集记录:")
    print("-" * 60)
    for i, r in enumerate(recent, 1):
        print(f"{i}. {r['home_team']} vs {r['away_team']}")
        print(f"   哈希: {r['oddsportal_hash']} | 置信度: {r['confidence']:.2f}")
        print(f"   更新时间: {r['updated_at']}")

    conn.close()

    return {
        "total": total,
        "with_hash": with_hash,
        "coverage": coverage,
    }


if __name__ == "__main__":
    check_progress()
