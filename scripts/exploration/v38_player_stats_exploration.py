#!/usr/bin/env python3
"""
V38.0 PlayerStats 深度探索脚本
===============================

专门探索 content.playerStats 结构，查找球员评分
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


def print_dict_structure(data, prefix="", max_depth=5, current_depth=0):
    """递归打印字典结构"""
    if current_depth >= max_depth:
        return

    if isinstance(data, dict):
        for key, value in list(data.items())[:20]:  # 最多显示20个键
            if isinstance(value, dict):
                print(f"{prefix}+ {key}: [dict] ({len(value)} keys)")
                print_dict_structure(value, prefix + "  ", max_depth, current_depth + 1)
            elif isinstance(value, list):
                print(f"{prefix}+ {key}: [list] (length: {len(value)})")
                if len(value) > 0 and isinstance(value[0], dict):
                    print_dict_structure(value[0], prefix + "  ", max_depth, current_depth + 1)
            else:
                v_str = str(value)
                if len(v_str) > 60:
                    v_str = v_str[:60] + "..."
                print(f"{prefix}+ {key}: {v_str}")
    elif isinstance(data, list) and len(data) > 0:
        print(f"{prefix}[list of {len(data)} items]")
        if isinstance(data[0], dict):
            print_dict_structure(data[0], prefix + "  ", max_depth, current_depth + 1)


async def explore_player_stats():
    """探索 playerStats 结构"""

    pool = await get_db_pool()

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT r.raw_data, m.home_team, m.away_team
                FROM raw_match_data r
                JOIN matches m ON r.match_id = m.match_id
                WHERE m.league_id = 47
                ORDER BY m.match_date DESC NULLS LAST
                LIMIT 1
                """
            )

            if not row:
                print("❌ 未找到数据")
                return

            raw_data = row["raw_data"]
            if isinstance(raw_data, str):
                raw_data = json.loads(raw_data)

            raw_api = raw_data.get("raw_data", {})
            content = raw_api.get("content", {})

            print("=" * 100)
            print(f"比赛: {row['home_team']} vs {row['away_team']}")
            print("=" * 100)

            # 1. 探索 playerStats
            print("\n📊 content.playerStats 结构:")
            player_stats = content.get("playerStats")
            if player_stats:
                print_dict_structure(player_stats, max_depth=4)

            # 2. 检查是否有 rating 字段
            print("\n" + "=" * 100)
            print("🔍 深度搜索 'rating' 字段:")

            def find_rating_path(obj, path=""):
                """递归查找 rating 字段"""
                results = []
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        new_path = f"{path} -> {key}" if path else key
                        if "rating" in key.lower():
                            results.append((new_path, value))
                        if isinstance(value, (dict, list)):
                            results.extend(find_rating_path(value, new_path))
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        if isinstance(item, (dict, list)):
                            results.extend(find_rating_path(item, f"{path}[{i}]"))
                return results

            rating_paths = find_rating_path(content)
            if rating_paths:
                print(f"\n✅ 找到 {len(rating_paths)} 个 rating 相关字段:")
                for path, value in rating_paths[:10]:  # 只显示前10个
                    v_str = str(value)
                    if len(v_str) > 80:
                        v_str = v_str[:80] + "..."
                    print(f"  content{path}: {v_str}")
            else:
                print("\n❌ 未找到 rating 字段")

            # 3. 搜索其他可能的评分字段
            print("\n" + "=" * 100)
            print("🔍 搜索其他评分相关字段:")

            score_keywords = ["score", "points", "grade", "mark", "rating", "average"]
            all_score_fields = []

            def find_score_fields(obj, path=""):
                """递归查找评分相关字段"""
                results = []
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        new_path = f"{path} -> {key}" if path else key
                        if any(kw in key.lower() for kw in score_keywords):
                            results.append((new_path, key, value))
                        if isinstance(value, (dict, list)):
                            results.extend(find_score_fields(value, new_path))
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        if isinstance(item, (dict, list)):
                            results.extend(find_score_fields(item, f"{path}[{i}]"))
                return results

            score_fields = find_score_fields(content)
            if score_fields:
                print(f"\n✅ 找到 {len(score_fields)} 个评分相关字段:")
                for path, key, value in score_fields[:15]:
                    v_str = str(value)
                    if len(v_str) > 60:
                        v_str = v_str[:60] + "..."
                    print(f"  {key}: {v_str}")
            else:
                print("\n❌ 未找到评分相关字段")

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(explore_player_stats())
