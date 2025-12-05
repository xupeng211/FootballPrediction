#!/usr/bin/env python3
"""
深度分析FotMob数据结构，寻找S-Tier特征
"""

import psycopg2
import json
import sys
from pathlib import Path

# 添加项目根路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

DATABASE_URL = (
    "postgresql://postgres:postgres-dev-password@localhost:5432/football_prediction"
)


def deep_search_json(obj, path="", target_keys=None, results=None):
    """深度搜索JSON中的目标键"""
    if results is None:
        results = []

    if target_keys is None:
        target_keys = [
            "score",
            "homeScore",
            "awayScore",
            "rating",
            "yellowCard",
            "redCard",
            "big chances",
            "weather",
            "venue",
            "attendance",
            "referee",
        ]

    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key

            # 检查是否匹配目标键
            key_lower = key.lower()
            for target in target_keys:
                if target.lower() in key_lower:
                    results.append(
                        {
                            "path": current_path,
                            "key": key,
                            "value": value,
                            "type": type(value).__name__,
                        }
                    )

            # 递归搜索
            if isinstance(value, (dict, list)):
                deep_search_json(value, current_path, target_keys, results)

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, (dict, list)):
                deep_search_json(item, f"{path}[{i}]", target_keys, results)

    return results


def analyze_fotmob_structure():
    """分析FotMob数据结构"""
    try:
        conn = psycopg2.connect(DATABASE_URL)

        # 获取包含完整数据的比赛
        query = """
            SELECT fotmob_id, stats, lineups, match_metadata
            FROM matches
            WHERE data_completeness = 'complete'
            AND stats IS NOT NULL
            LIMIT 3
        """

        cur = conn.cursor()
        cur.execute(query)
        matches = cur.fetchall()

        print("🔍 深度分析FotMob数据结构")
        print("=" * 80)

        target_categories = {
            "比分数据": ["score", "homeScore", "awayScore", "result", "finalScore"],
            "红黄牌": ["yellowCard", "redCard", "card", "booking"],
            "球员评分": ["rating", "average", "score", "performance"],
            "绝佳机会": ["big chances", "big chances created", "clear-cut chances"],
            "比赛环境": ["weather", "venue", "attendance", "referee", "stadium"],
        }

        for i, (fotmob_id, stats, lineups, _match_metadata) in enumerate(matches, 1):
            print(f"\n⚽ 比赛 {i}: ID {fotmob_id}")
            print("-" * 40)

            # 分析stats数据
            if stats:
                try:
                    if isinstance(stats, str):
                        stats_data = json.loads(stats)
                    else:
                        stats_data = stats

                    print(f"📈 Stats字段键: {list(stats_data.keys())}")

                    for category, keywords in target_categories.items():
                        results = deep_search_json(stats_data, "stats", keywords)
                        if results:
                            print(f"\n🎯 {category}:")
                            for result in results[:5]:  # 只显示前5个结果
                                print(
                                    f"   {result['path']}: {result['value']} ({result['type']})"
                                )

                except Exception as e:
                    print(f"❌ Stats解析失败: {e}")

            # 分析lineups数据
            if lineups:
                try:
                    if isinstance(lineups, str):
                        lineups_data = json.loads(lineups)
                    else:
                        lineups_data = lineups

                    print("\n👥 Lineups结构分析:")

                    # 寻找球员评分
                    rating_results = deep_search_json(
                        lineups_data, "lineups", ["rating"]
                    )
                    if rating_results:
                        print(f"   发现评分数据: {len(rating_results)} 个")
                        for result in rating_results[:3]:
                            print(f"   {result['path']}: {result['value']}")

                    # 分析主客队结构
                    home_team = lineups_data.get("homeTeam", {})
                    away_team = lineups_data.get("awayTeam", {})

                    if home_team:
                        print(f"   主队阵容结构: {list(home_team.keys())}")
                        lineup = home_team.get("lineUp", [])
                        if isinstance(lineup, list) and len(lineup) > 0:
                            print(f"   主队首发球员数: {len(lineup)}")
                            if len(lineup) > 0:
                                first_player = lineup[0]
                                print(
                                    f"   球员数据结构: {list(first_player.keys()) if isinstance(first_player, dict) else type(first_player).__name__}"
                                )

                    if away_team:
                        print(f"   客队阵容结构: {list(away_team.keys())}")

                except Exception as e:
                    print(f"❌ Lineups解析失败: {e}")

            print("\n" + "=" * 80)

        conn.close()

    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    analyze_fotmob_structure()
