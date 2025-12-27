#!/usr/bin/env python3
"""
V26.0 冒烟测试脚本 (Smokescreen Test)
=====================================
单场比赛验证流程 - 确保 ID 生成和 L2 保存链路正确

验证步骤:
1. 清理环境 (TRUNCATE matches, raw_match_data CASCADE)
2. 采集单场比赛 (ID=4813374)
3. SQL 验证 (match_id 格式, raw_match_data 写入)

作者: FootballPrediction Team
版本: V26.0
日期: 2025-12-27
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncpg
from scripts.collectors.fotmob_collector_l1_l2 import FotMobL1L2Collector

from src.config_unified import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def cleanup_database():
    """步骤 1: 清理环境"""
    print("\n" + "=" * 60)
    print("🧹 步骤 1: 清理数据库环境")
    print("=" * 60)

    pool = await asyncpg.create_pool(settings.database.get_connection_string())

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                # TRUNCATE 所有相关表（按依赖关系排序）
                await conn.execute("""
                    TRUNCATE TABLE
                        match_features_training,
                        raw_match_data,
                        matches
                    CASCADE
                """)
                print("✅ 数据库清理完成: 所有表已清空")

                # 验证清理结果
                matches_count = await conn.fetchval("SELECT COUNT(*) FROM matches")
                raw_data_count = await conn.fetchval("SELECT COUNT(*) FROM raw_match_data")

                print(f"   - matches 表: {matches_count} 行")
                print(f"   - raw_match_data 表: {raw_data_count} 行")

    finally:
        await pool.close()


async def run_smoke_test():
    """冒烟测试主流程"""
    print("\n" + "=" * 60)
    print("🔥 V26.0 冒烟测试 (Smokescreen Test)")
    print("=" * 60)
    print("测试目标: 单场比赛 ID=4813374")
    print("=" * 60)

    # 步骤 1: 清理环境
    await cleanup_database()

    # 步骤 2: 采集单场比赛
    print("\n" + "=" * 60)
    print("📡 步骤 2: 采集单场比赛")
    print("=" * 60)

    async with FotMobL1L2Collector(
        max_l2_concurrency=1,
        delay_between_requests=3.0,
        silent_mode=False,  # 冒烟测试使用详细日志
    ) as collector:
        # L1 采集: 使用赛季 23/24
        print("\n📋 L1 采集: Premier League 23/24 赛季...")
        matches = await collector.collect_season_matches(
            league_id=47, season_code="2324", league_name="Premier League", season_display="23/24"
        )

        if not matches:
            print("❌ L1 采集失败，无比赛数据")
            return False

        print(f"✅ L1 采集成功: {len(matches)} 场比赛")

        # 查找目标比赛 (ID=4813374)
        target_match = None
        for match in matches:
            external_id = match.get("id") or match.get("external_id")
            if external_id == "4813374":
                target_match = match
                break

        if not target_match:
            print("❌ 未找到目标比赛 ID=4813374")
            print(f"   搜索了 {len(matches)} 场比赛")
            return False

        print(f"✅ 找到目标比赛: {target_match['home_team']} vs {target_match['away_team']}")

        # 保存 L1 数据
        print("\n💾 保存 L1 数据...")
        saved = await collector.save_all_l1_matches([target_match])
        if saved != 1:
            print(f"❌ L1 保存失败: 保存了 {saved} 场")
            return False
        print("✅ L1 保存成功")

        # 构建 match_id (使用 {external_id}_{season} 格式)
        season = target_match.get("season", "2324")
        external_id = target_match.get("id") or target_match.get("external_id")
        unique_match_id = f"{external_id}_{season}"

        print(f"\n📋 L2 采集: {unique_match_id}")

        # L2 采集并保存
        data = await collector.collect_l2_match_data(unique_match_id)
        if not data:
            print(f"❌ L2 采集失败: {unique_match_id}")
            return False
        print("✅ L2 采集成功")

        # L2 保存
        saved = await collector._save_l2_raw_data(unique_match_id, data)
        if not saved:
            print(f"❌ L2 保存失败: {unique_match_id}")
            return False
        print("✅ L2 保存成功")

    # 步骤 3: SQL 验证
    print("\n" + "=" * 60)
    print("🔍 步骤 3: SQL 验证")
    print("=" * 60)

    pool = await asyncpg.create_pool(settings.database.get_connection_string())

    try:
        async with pool.acquire() as conn:
            # 验证 1: matches 表
            print("\n1️⃣ 验证 matches 表...")
            match_row = await conn.fetchrow(
                """
                SELECT
                    match_id,
                    external_id,
                    league_name,
                    season,
                    home_team,
                    away_team,
                    collection_status,
                    l1_collected_at,
                    l2_collected_at
                FROM matches
                WHERE external_id = $1
            """,
                external_id,
            )

            if not match_row:
                print(f"   ❌ matches 表中未找到 external_id={external_id}")
                return False

            print("   ✅ 找到比赛记录:")
            print(f"      - match_id: {match_row['match_id']}")
            print(f"      - external_id: {match_row['external_id']}")
            print(f"      - league: {match_row['league_name']} {match_row['season']}")
            print(f"      - 比赛: {match_row['home_team']} vs {match_row['away_team']}")
            print(f"      - collection_status: {match_row['collection_status']}")
            print(f"      - l1_collected_at: {match_row['l1_collected_at']}")
            print(f"      - l2_collected_at: {match_row['l2_collected_at']}")

            # 验证 match_id 格式
            expected_match_id = f"{external_id}_{season}"
            if match_row["match_id"] != expected_match_id:
                print("   ❌ match_id 格式错误!")
                print(f"      期望: {expected_match_id}")
                print(f"      实际: {match_row['match_id']}")
                return False
            print(f"   ✅ match_id 格式正确: {expected_match_id}")

            # 验证 2: raw_match_data 表
            print("\n2️⃣ 验证 raw_match_data 表...")
            raw_row = await conn.fetchrow(
                """
                SELECT
                    match_id,
                    external_id,
                    source,
                    data_version,
                    length(raw_data::text) as data_size,
                    collected_at
                FROM raw_match_data
                WHERE match_id = $1
            """,
                unique_match_id,
            )

            if not raw_row:
                print(f"   ❌ raw_match_data 表中未找到 match_id={unique_match_id}")
                return False

            print("   ✅ 找到原始数据:")
            print(f"      - match_id: {raw_row['match_id']}")
            print(f"      - external_id: {raw_row['external_id']}")
            print(f"      - source: {raw_row['source']}")
            print(f"      - data_version: {raw_row['data_version']}")
            print(f"      - data_size: {raw_row['data_size']} 字节")
            print(f"      - collected_at: {raw_row['collected_at']}")

            # 验证 raw_match_data.match_id 格式
            if raw_row["match_id"] != unique_match_id:
                print("   ❌ raw_match_data.match_id 格式错误!")
                print(f"      期望: {unique_match_id}")
                print(f"      实际: {raw_row['match_id']}")
                return False
            print(f"   ✅ raw_match_data.match_id 格式正确: {unique_match_id}")

            # 验证 3: 数据完整性
            print("\n3️⃣ 验证数据完整性...")
            data = await conn.fetchval("SELECT raw_data FROM raw_match_data WHERE match_id = $1", unique_match_id)
            if data:
                import json

                parsed = json.loads(data)
                print("   ✅ JSON 数据解析成功")
                print(f"      - 包含键: {list(parsed.keys())[:10]}...")  # 显示前 10 个键

    finally:
        await pool.close()

    # 冒烟测试通过
    print("\n" + "=" * 60)
    print("🎉 冒烟测试通过!")
    print("=" * 60)
    print("✅ 所有验证步骤通过")
    print("✅ ID 生成逻辑正确")
    print("✅ L2 保存链路完整")
    print("✅ 可以开始全量采集")
    print("=" * 60)

    return True


if __name__ == "__main__":
    exit_code = asyncio.run(run_smoke_test())
    sys.exit(0 if exit_code else 1)
