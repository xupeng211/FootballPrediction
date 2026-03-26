#!/usr/bin/env python3
"""
V4.46.3 L3 特征熔炼脚本
=======================

将 L2 原始数据转换为 L3 特征向量

使用方式:
    python scripts/ops/smelt_l3.py [--limit N]
"""

import asyncio
import asyncpg
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 数据库配置
DB_CONFIG = {
    'host': 'db',  # Docker 内部使用 db
    'port': 5432,
    'database': 'football_db',
    'user': 'football_user',
    'password': 'football_pass'
}


async def smelt_features(pool, limit=None):
    """熔炼 L2 数据到 L3 特征"""

    # 获取需要熔炼的 L2 数据
    query = """
        SELECT r.match_id, r.raw_data, m.home_team, m.away_team, m.match_date
        FROM raw_match_data r
        JOIN matches m ON r.match_id = m.match_id
        LEFT JOIN l3_features l ON r.match_id = l.match_id
        WHERE l.match_id IS NULL
        ORDER BY r.collected_at DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    async with pool.acquire() as conn:
        rows = await conn.fetch(query)

    print(f"📊 待熔炼数据: {len(rows)} 条")

    success = 0
    failed = 0

    for row in rows:
        try:
            match_id = row['match_id']
            raw_data = json.loads(row['raw_data']) if isinstance(row['raw_data'], str) else row['raw_data']

            # 提取基础特征
            features = extract_basic_features(raw_data, row)

            # 插入 L3 表
            await insert_l3_features(pool, match_id, features)

            success += 1
            if success % 50 == 0:
                print(f"✅ 已熔炼 {success} 条...")

        except Exception as e:
            failed += 1
            print(f"❌ 熔炼失败 {row['match_id']}: {e}")

    return success, failed


def extract_basic_features(raw_data, row):
    """提取基础特征"""
    features = {}

    # 尝试从 raw_data 中提取特征
    content = raw_data.get('content', {})
    general = raw_data.get('general', {})
    header = raw_data.get('header', {})

    # 基础信息
    features['match_id'] = row['match_id']
    features['home_team'] = row['home_team']
    features['away_team'] = row['away_team']

    # 比赛统计
    stats = content.get('stats', {})
    if stats:
        home_stats = stats.get('home', {})
        away_stats = stats.get('away', {})

        features['home_possession'] = home_stats.get('possession', {}).get('percentage', 50)
        features['away_possession'] = away_stats.get('possession', {}).get('percentage', 50)
        features['home_shots'] = home_stats.get('shotsTotal', {}).get('total', 0)
        features['away_shots'] = away_stats.get('shotsTotal', {}).get('total', 0)
        features['home_shots_on_target'] = home_stats.get('shotsOnTarget', {}).get('total', 0)
        features['away_shots_on_target'] = away_stats.get('shotsOnTarget', {}).get('total', 0)
        features['home_corners'] = home_stats.get('corners', 0)
        features['away_corners'] = away_stats.get('corners', 0)
        features['home_fouls'] = home_stats.get('fouls', 0)
        features['away_fouls'] = away_stats.get('fouls', 0)
        features['home_xg'] = home_stats.get('xg', 0)
        features['away_xg'] = away_stats.get('xg', 0)

    # 赔率数据
    odds = content.get('odds', {})
    if odds:
        features['opening_home_odds'] = odds.get('opening', {}).get('home', 0)
        features['opening_draw_odds'] = odds.get('opening', {}).get('draw', 0)
        features['opening_away_odds'] = odds.get('opening', {}).get('away', 0)

    return features


async def insert_l3_features(pool, match_id, features):
    """插入 L3 特征到数据库"""

    query = """
        INSERT INTO l3_features (match_id, golden_features, created_at)
        VALUES ($1, $2, NOW())
        ON CONFLICT (match_id) DO UPDATE SET
            golden_features = EXCLUDED.golden_features,
            updated_at = NOW()
    """

    async with pool.acquire() as conn:
        await conn.execute(query, match_id, json.dumps(features))


async def main():
    """主函数"""
    limit = None
    if len(sys.argv) > 2 and sys.argv[1] == '--limit':
        limit = int(sys.argv[2])

    print("🚀 L3 特征熔炼引擎启动...")
    print(f"📊 数据库连接: {DB_CONFIG['host']}:{DB_CONFIG['port']}")

    pool = await asyncpg.create_pool(**DB_CONFIG, min_size=5, max_size=20)

    try:
        # 检查 L2/L3 状态
        async with pool.acquire() as conn:
            l2_count = await conn.fetchval("SELECT COUNT(*) FROM raw_match_data")
            l3_count = await conn.fetchval("SELECT COUNT(*) FROM l3_features")
            pending = await conn.fetchval("""
                SELECT COUNT(*) FROM raw_match_data r
                LEFT JOIN l3_features l ON r.match_id = l.match_id
                WHERE l.match_id IS NULL
            """)

        print(f"📈 L2 记录: {l2_count}")
        print(f"📈 L3 记录: {l3_count}")
        print(f"⏳ 待熔炼: {pending}")

        # 执行熔炼
        success, failed = await smelt_features(pool, limit)

        print()
        print("=" * 50)
        print(f"✅ 熔炼完成: 成功 {success}, 失败 {failed}")
        print("=" * 50)

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
