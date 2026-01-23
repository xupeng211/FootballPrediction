#!/usr/bin/env python3
"""
V41.390 Quality Spot Check - 黄金特征质量抽检
===================================================

随机抽取 3 场比赛，验证新特征是否有真实数值。
"""

import json
import psycopg2
from src.config_unified import get_settings


def main():
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=psycopg2.extras.RealDictCursor
    )

    print("=" * 70)
    print("V41.390 质量抽检报告")
    print("=" * 70)
    print()

    cursor = conn.cursor()

    # 随机抽取 3 场比赛
    cursor.execute("""
        SELECT match_id, l2_raw_json, home_team, away_team
        FROM matches
        WHERE l2_raw_json IS NOT NULL
        ORDER BY RANDOM()
        LIMIT 3
    """)

    samples = cursor.fetchall()

    for i, sample in enumerate(samples, 1):
        match_id = sample["match_id"]
        l2_raw = sample["l2_raw_json"]

        print(f"[样本 {i}] {match_id}")
        print(f"  比赛: {sample['home_team']} vs {sample['away_team']}")

        # 解析 L2 数据
        if isinstance(l2_raw, str):
            l2_data = json.loads(l2_raw)
        else:
            l2_data = l2_raw

        # 检查数据结构
        content = l2_data.get("content", {})
        lineup = content.get("lineup", {})

        has_home_team = "homeTeam" in lineup
        has_away_team = "awayTeam" in lineup

        print(f"  数据结构检查:")
        print(f"    - content.lineup 存在: {bool(lineup)}")
        print(f"    - homeTeam 存在: {has_home_team}")
        print(f"    - awayTeam 存在: {has_away_team}")

        # 检查身价特征
        if has_home_team:
            home_team = lineup["homeTeam"]
            starters = home_team.get("starters", [])
            print(f"    - 首发球员数: {len(starters)}")

            mv_values = []
            for player in starters[:3]:
                mv = player.get("marketValue")
                if mv:
                    mv_values.append(mv)

            if mv_values:
                print(f"    - 身份数据示例: {mv_values[:3]}")
                print(f"    ✓ 身价特征: 有真实数值")
            else:
                print(f"    ✗ 身价特征: 无数据或全为0")

        print()

    cursor.close()
    conn.close()

    print("=" * 70)
    print("✅ 质量抽检完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
