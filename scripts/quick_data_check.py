#!/usr/bin/env python3
"""
快速检查数据库中的数据质量
"""

import asyncio
import asyncpg
import json


async def check_data():
    conn = await asyncpg.connect("postgresql://postgres:postgres-dev-password@db:5432/football_prediction")

    # 检查基础数据
    result = await conn.fetchrow("""
        SELECT
            COUNT(*) as total_matches,
            COUNT(CASE WHEN stats IS NOT NULL AND stats != 'null' THEN 1 END) as has_stats,
            COUNT(CASE WHEN odds IS NOT NULL AND odds != 'null' THEN 1 END) as has_odds,
            COUNT(CASE WHEN home_score IS NOT NULL AND away_score IS NOT NULL THEN 1 END) as has_scores
        FROM matches
        WHERE status IN ('completed', 'finished')
    """)

    print(f"📊 数据质量总览:")
    print(f"   总比赛数: {result['total_matches']:,}")
    print(f"   有stats数据: {result['has_stats']:,}")
    print(f"   有odds数据: {result['has_odds']:,}")
    print(f"   有比分数据: {result['has_scores']:,}")

    # 检查xG数据样本
    sample_stats = await conn.fetchrow("""
        SELECT stats FROM matches
        WHERE stats IS NOT NULL AND stats != 'null'
        LIMIT 1
    """)

    if sample_stats:
        stats_data = json.loads(sample_stats['stats'])
        print(f"\n🔍 样本stats字段:")
        for key, value in list(stats_data.items())[:10]:
            print(f"   {key}: {value}")

    # 检查odds数据样本
    sample_odds = await conn.fetchrow("""
        SELECT odds FROM matches
        WHERE odds IS NOT NULL AND odds != 'null'
        LIMIT 1
    """)

    if sample_odds:
        odds_data = json.loads(sample_odds['odds'])
        print(f"\n💰 样本odds字段:")
        for key, value in list(odds_data.items())[:10]:
            print(f"   {key}: {value}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(check_data())