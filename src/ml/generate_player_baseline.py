#!/usr/bin/env python3
"""
V20.3 球员基准评分生成器
从数据库提取所有球员的历史评分数据，生成基准字典用于阵容实力偏差计算
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

# 数据库连接
host = os.getenv("DB_HOST", "localhost")
port = int(os.getenv("DB_PORT", 5432))
database = os.getenv("DB_NAME", "football_db")
user = os.getenv("DB_USER", "football_user")
password = os.getenv("DB_PASSWORD", "football_pass")

# Docker 主机名处理
if host in ["db", "redis"]:
    import socket
    try:
        socket.create_connection((host, port), timeout=1).close()
    except (socket.timeout, ConnectionRefusedError, OSError):
        host = "localhost"

conn = psycopg2.connect(host=host, port=port, database=database, user=user, password=password)
cursor = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 60)
print("V20.3 球员基准评分生成器")
print("=" * 60)

# 提取所有球员评分数据
query = """
WITH player_ratings AS (
    SELECT
        (player->>'id')::int as player_id,
        player->>'name' as player_name,
        (player->>'rating')::float as rating,
        player->>'position' as position,
        (player->>'is_starter')::boolean as is_starter
    FROM match_features_training,
    jsonb_array_elements(enriched_features->'meta_home_player_assets') as player
    WHERE (player->>'rating') IS NOT NULL

    UNION ALL

    SELECT
        (player->>'id')::int as player_id,
        player->>'name' as player_name,
        (player->>'rating')::float as rating,
        player->>'position' as position,
        (player->>'is_starter')::boolean as is_starter
    FROM match_features_training,
    jsonb_array_elements(enriched_features->'meta_away_player_assets') as player
    WHERE (player->>'rating') IS NOT NULL
)
SELECT
    player_id,
    player_name,
    position,
    COUNT(*) as total_appearances,
    SUM(CASE WHEN is_starter THEN 1 ELSE 0 END) as starter_appearances,
    ROUND(AVG(rating)::numeric, 4) as avg_rating,
    ROUND(MIN(rating)::numeric, 4) as min_rating,
    ROUND(MAX(rating)::numeric, 4) as max_rating,
    ROUND(STDDEV(rating)::numeric, 4) as rating_stddev
FROM player_ratings
GROUP BY player_id, player_name, position
ORDER BY total_appearances DESC, avg_rating DESC
"""

cursor.execute(query)
rows = cursor.fetchall()

print(f"\n提取到 {len(rows)} 名球员的基准评分数据")

# 构建输出数据
players = []
for row in rows:
    players.append({
        "player_id": row["player_id"],
        "name": row["player_name"],
        "position": row["position"],
        "total_appearances": row["total_appearances"],
        "starter_appearances": row["starter_appearances"],
        "avg_rating": float(row["avg_rating"]) if row["avg_rating"] else None,
        "min_rating": float(row["min_rating"]) if row["min_rating"] else None,
        "max_rating": float(row["max_rating"]) if row["max_rating"] else None,
        "rating_stddev": float(row["rating_stddev"]) if row["rating_stddev"] else None
    })

# 按位置统计
position_stats = {}
for p in players:
    pos = p["position"]
    if pos not in position_stats:
        position_stats[pos] = {
            "count": 0,
            "avg_rating": [],
            "top_players": []
        }
    position_stats[pos]["count"] += 1
    if p["avg_rating"]:
        position_stats[pos]["avg_rating"].append(p["avg_rating"])

# 计算位置平均评分
for pos in position_stats:
    ratings = position_stats[pos]["avg_rating"]
    position_stats[pos]["avg_position_rating"] = round(sum(ratings) / len(ratings), 4) if ratings else 0
    position_stats[pos]["avg_rating"] = []
    # 添加该位置 Top 5 球员
    pos_players = [p for p in players if p["position"] == pos]
    position_stats[pos]["top_players"] = [
        {"id": p["player_id"], "name": p["name"], "avg_rating": p["avg_rating"]}
        for p in sorted(pos_players, key=lambda x: x["avg_rating"] or 0, reverse=True)[:5]
    ]

# 构建最终 JSON
output = {
    "metadata": {
        "version": "V20.3",
        "generated_at": datetime.now().isoformat(),
        "total_matches": 760,
        "total_players": len(players),
        "description": "Player baseline ratings aggregated from 22/23 and 23/24 Premier League seasons. Used for computing squad strength deviation when starting lineups are announced for Boxing Day matches."
    },
    "position_summary": {
        "GK": {
            "count": position_stats.get("GK", {}).get("count", 0),
            "avg_rating": position_stats.get("GK", {}).get("avg_position_rating", 0)
        },
        "DF": {
            "count": position_stats.get("DF", {}).get("count", 0),
            "avg_rating": position_stats.get("DF", {}).get("avg_position_rating", 0)
        },
        "MF": {
            "count": position_stats.get("MF", {}).get("count", 0),
            "avg_rating": position_stats.get("MF", {}).get("avg_position_rating", 0)
        },
        "FW": {
            "count": position_stats.get("FW", {}).get("count", 0),
            "avg_rating": position_stats.get("FW", {}).get("avg_position_rating", 0)
        }
    },
    "players": players
}

# 保存到文件
output_dir = "/home/user/projects/FootballPrediction/data"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "player_baseline_ratings.json")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\n保存球员基准评分到: {output_path}")

# 打印摘要
print("\n" + "=" * 60)
print("球员基准评分摘要")
print("=" * 60)
print(f"总球员数: {len(players)}")
print(f"总比赛数: {output['metadata']['total_matches']}")
print("\n按位置统计:")
for pos in ["GK", "DF", "MF", "FW"]:
    stats = output["position_summary"][pos]
    print(f"  {pos}: {stats['count']} 人, 平均评分 {stats['avg_rating']:.4f}")

print("\nTop 10 球员 (按平均评分):")
for i, p in enumerate(sorted(players, key=lambda x: x["avg_rating"] or 0, reverse=True)[:10], 1):
    print(f"  {i:2d}. {p['name']:<25} | {p['position']:<3} | "
          f"出场: {p['total_appearances']:3d} | "
          f"评分: {p['avg_rating']:.4f}")

print("=" * 60)
print("V20.3 球员基准评分生成完成")
print("=" * 60)

cursor.close()
conn.close()
