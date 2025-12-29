#!/usr/bin/env python3
"""
V38.0 Lineup 深度探索脚本
==========================

专门用于深入分析 lineup 数据结构，定位球员评分字段
"""

import asyncio
import json
import sys
from pathlib import Path

import asyncpg

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


async def get_db_pool():
    """获取数据库连接池"""
    import subprocess

    result = subprocess.run(
        ["docker", "exec", "football_prediction_db", "printenv", "POSTGRES_PASSWORD"],
        capture_output=True,
        text=True,
    )
    db_password = result.stdout.strip() or "football123"

    return await asyncpg.create_pool(
        host="localhost",
        port=5432,
        database="football_prediction_dev",
        user="football_user",
        password=db_password,
        min_size=1,
        max_size=3,
    )


async def deep_lineup_exploration():
    """深度探索 lineup 结构"""

    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            # 获取最近一场比赛
            row = await conn.fetchrow(
                """
                SELECT r.raw_data, m.home_team, m.away_team, m.match_date
                FROM raw_match_data r
                JOIN matches m ON r.match_id = m.match_id
                WHERE m.league_id = 47
                ORDER BY m.match_date DESC NULLS LAST
                LIMIT 1
                """
            )

            if not row:
                print("❌ 未找到任何比赛数据")
                return

            raw_data = row["raw_data"]
            if isinstance(raw_data, str):
                raw_data = json.loads(raw_data)

            raw_api = raw_data.get("raw_data", {})
            content = raw_api.get("content", {})

            print("=" * 100)
            print(f"比赛: {row['home_team']} vs {row['away_team']} on {row['match_date']}")
            print("=" * 100)

            # 1. 列出 content 下的所有顶级键
            print("\n📋 Content 顶级键:")
            print("  ", list(content.keys()))

            # 2. 查找所有包含 "lineup" 或 "lineup" 的键
            print("\n🔍 查找 lineup 相关键:")
            for key in content.keys():
                if "lineup" in key.lower() or "line" in key.lower():
                    print(f"  - {key}")

            # 3. 深度探索 lineup 结构
            print("\n🧬 深度探索 lineup 结构:")

            # 尝试不同的路径
            lineup_paths = [
                ("lineup", content.get("lineup")),
                ("lineUps", content.get("lineUps")),
                ("lineUp", content.get("lineUp")),
            ]

            for path_name, lineup_data in lineup_paths:
                if lineup_data:
                    print(f"\n✅ 找到路径: content -> {path_name}")
                    print(f"   类型: {type(lineup_data)}")
                    print(f"   顶级键: {list(lineup_data.keys()) if isinstance(lineup_data, dict) else 'N/A'}")

                    # 如果是字典，继续探索
                    if isinstance(lineup_data, dict):
                        # 检查常见子键
                        for sub_key in ["starters", "home", "away", "players", "substitutes"]:
                            if sub_key in lineup_data:
                                sub_data = lineup_data[sub_key]
                                print(f"\n   → {sub_key}:")
                                print(f"      类型: {type(sub_data)}")

                                if isinstance(sub_data, dict):
                                    print(f"      顶级键: {list(sub_data.keys())[:15]}")

                                    # 查找 players
                                    if "players" in sub_data:
                                        players = sub_data["players"]
                                        if isinstance(players, list) and len(players) > 0:
                                            print("\n      📌 球员数据样本 (第1个球员):")
                                            sample_player = players[0]
                                            print(f"         所有字段 ({len(sample_player)} 个):")
                                            for k, v in list(sample_player.items())[:20]:
                                                v_str = str(v)
                                                if len(v_str) > 50:
                                                    v_str = v_str[:50] + "..."
                                                print(f"           - {k}: {v_str}")

                                            # 查找评分相关字段
                                            rating_keywords = ["rating", "score", "points", "stats", "grade", "mark"]
                                            rating_fields = []
                                            for k in sample_player.keys():
                                                if any(kw in k.lower() for kw in rating_keywords):
                                                    rating_fields.append((k, sample_player[k]))

                                            if rating_fields:
                                                print("\n      🎯 评分相关字段:")
                                                for k, v in rating_fields:
                                                    print(f"           - {k}: {v}")
                                            else:
                                                print("\n      ❌ 未找到评分相关字段")

                                elif isinstance(sub_data, list) and len(sub_data) > 0:
                                    print(f"      数组长度: {len(sub_data)}")
                                    print(
                                        f"      第一个元素: {list(sub_data[0].keys())[:15] if isinstance(sub_data[0], dict) else type(sub_data[0])}"
                                    )

            # 4. 尝试直接在 content 下查找评分
            print("\n🔎 在 content 顶层查找评分相关字段:")
            rating_keywords = ["rating", "score", "points", "stats"]
            for key in content.keys():
                if any(kw in key.lower() for kw in rating_keywords):
                    print(f"  - {key}: {type(content[key])}")

            # 5. 检查是否存在全局球员统计
            if "stats" in content:
                stats = content["stats"]
                print("\n📊 content.stats 结构分析:")
                print(f"   顶级键: {list(stats.keys())}")

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(deep_lineup_exploration())
