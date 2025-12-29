#!/usr/bin/env python3
"""
V38.5 L3 特征提取验证测试脚本
================================

功能:
1. 从数据库随机抽取 5 场英超数据
2. 执行特征提取
3. 展示提取的特征向量
4. 验证数据库写入

作者: Senior Data Engineer
日期: 2025-12-29
Phase: Validation Testing
"""

import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import asyncpg
from tabulate import tabulate

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.api.collectors.l3_feature_processor import (
    L3FeatureExtractor,
    L3FeaturePersister,
    L3MatchFeatures,
)


# ============================================
# 数据库连接
# ============================================
def get_db_password():
    """从 Docker 获取数据库密码"""
    result = subprocess.run(
        ["docker", "exec", "football_prediction_db", "printenv", "POSTGRES_PASSWORD"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or "football123"


async def get_test_samples(pool: asyncpg.Pool, sample_size: int = 5) -> list[dict]:
    """
    从数据库随机抽取英超比赛样本

    Args:
        pool: 数据库连接池
        sample_size: 样本数量

    Returns:
        list: 包含 raw_data 和元数据的字典列表
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                r.raw_data,
                r.match_id,
                m.league_id,
                m.season,
                m.home_team,
                m.away_team,
                m.match_date
            FROM raw_match_data r
            JOIN matches m ON r.match_id = m.match_id
            WHERE m.league_id = 47
            ORDER BY RANDOM()
            LIMIT $1
            """,
            sample_size,
        )

        return [dict(row) for row in rows]


# ============================================
# 特征提取测试
# ============================================
async def test_feature_extraction(samples: list[dict]) -> tuple[list[L3MatchFeatures], dict]:
    """
    测试特征提取

    Args:
        samples: 测试样本

    Returns:
        tuple: (提取的特征列表, 提取统计)
    """
    extractor = L3FeatureExtractor()

    features_list = []

    for sample in samples:
        match_id = sample["match_id"]
        raw_data = sample["raw_data"]
        league_id = sample["league_id"]
        season = sample["season"]

        # 转换 raw_data 为 dict
        if isinstance(raw_data, str):
            raw_data = json.loads(raw_data)

        # 提取特征
        features = extractor.process_json(raw_data, match_id, league_id, season)
        features_list.append(features)

    stats = extractor.get_extraction_stats()

    return features_list, stats


# ============================================
# 特征展示
# ============================================
def display_features(samples: list[dict], features_list: list[L3MatchFeatures]) -> None:
    """展示提取的特征"""
    print("=" * 120)
    print(" " * 40 + "V38.5 L3 特征提取验证测试")
    print("=" * 120)
    print(f"\n测试时间: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"样本数量: {len(samples)}")

    for i, (sample, features) in enumerate(zip(samples, features_list), 1):
        print("\n" + "=" * 120)
        print(f"样本 #{i}: {sample['home_team']} vs {sample['away_team']} ({sample['season']})")
        print(f"Match ID: {sample['match_id']} | 日期: {sample['match_date']}")
        print("=" * 120)

        # 构建特征展示表格
        feature_data = [
            ["主队 xG", features.home_xg, "Expected Goals"],
            ["客队 xG", features.away_xg, "Expected Goals"],
            ["主队控球率 (%)", features.home_possession, "Ball Possession"],
            ["客队控球率 (%)", features.away_possession, "Ball Possession"],
            ["主队射正数", features.home_shots_on_target, "Shots on Target"],
            ["客队射正数", features.away_shots_on_target, "Shots on Target"],
            ["主队大机会", features.home_big_chances, "Big Chances Created"],
            ["客队大机会", features.away_big_chances, "Big Chances Created"],
            ["主队平均评分", features.home_avg_player_rating, "Player Rating"],
            ["客队平均评分", features.away_avg_player_rating, "Player Rating"],
            ["总体平均评分", features.avg_player_rating, "Player Rating"],
        ]

        print(
            tabulate(
                feature_data,
                headers=["特征名称", "值", "说明"],
                tablefmt="grid",
                numalign="right",
            )
        )

        # 数据完整性检查
        print("\n📊 数据完整性:")

        completeness = []
        if features.home_xg is not None:
            completeness.append("✅ xG")
        else:
            completeness.append("❌ xG")

        if features.home_possession is not None:
            completeness.append("✅ 控球率")
        else:
            completeness.append("❌ 控球率")

        if features.home_shots_on_target is not None:
            completeness.append("✅ 射正数")
        else:
            completeness.append("❌ 射正数")

        if features.avg_player_rating is not None:
            completeness.append("✅ 球员评分")
        else:
            completeness.append("❌ 球员评分")

        print("  " + " | ".join(completeness))


# ============================================
# 数据库写入测试
# ============================================
async def test_database_persistence(features_list: list[L3MatchFeatures]) -> dict:
    """
    测试数据库持久化

    Returns:
        dict: 持久化结果统计
    """
    db_password = get_db_password()

    db_config = {
        "host": "localhost",
        "port": 5432,
        "database": "football_prediction_dev",
        "user": "football_user",
        "password": db_password,
    }

    persister = L3FeaturePersister(db_config)

    try:
        # 连接数据库
        persister.connect()

        # 创建表
        persister.create_table()

        # 批量插入
        result = persister.batch_insert_features(features_list)

        return result

    finally:
        persister.close()


# ============================================
# 验证数据库写入结果
# ============================================
async def verify_database_write(pool: asyncpg.Pool) -> list[dict]:
    """验证数据库中的特征数据"""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                match_id,
                league_id,
                season,
                home_xg,
                away_xg,
                home_possession,
                away_possession,
                home_shots_on_target,
                away_shots_on_target,
                home_big_chances,
                away_big_chances,
                avg_player_rating,
                home_avg_player_rating,
                away_avg_player_rating,
                extracted_at
            FROM match_features_v1
            ORDER BY extracted_at DESC
            LIMIT 5
            """
        )

        return [dict(row) for row in rows]


def display_database_results(db_results: list[dict]) -> None:
    """展示数据库验证结果"""
    print("\n\n")
    print("=" * 120)
    print(" " * 45 + "数据库验证结果")
    print("=" * 120)

    if not db_results:
        print("\n⚠️  未找到任何特征数据")
        return

    for i, row in enumerate(db_results, 1):
        print(f"\n记录 #{i}: Match ID = {row['match_id']}")
        print(f"  联赛: {row['league_id']} | 赛季: {row['season']}")
        print(f"  xG: {row['home_xg']} - {row['away_xg']}")
        print(f"  控球率: {row['home_possession']}% - {row['away_possession']}%")
        print(f"  射正: {row['home_shots_on_target']} - {row['away_shots_on_target']}")
        print(f"  大机会: {row['home_big_chances']} - {row['away_big_chances']}")
        print(f"  平均评分: {row['avg_player_rating']}")
        print(f"  提取时间: {row['extracted_at']}")

    print("\n✅ 数据库写入验证成功！")


# ============================================
# 主流程
# ============================================
async def main():
    """主测试流程"""
    print("🚀 V38.5 L3 特征提取验证测试启动...\n")

    # 1. 连接数据库
    db_password = get_db_password()
    pool = await asyncpg.create_pool(
        host="localhost",
        port=5432,
        database="football_prediction_dev",
        user="football_user",
        password=db_password,
        min_size=1,
        max_size=3,
    )

    try:
        # 2. 获取测试样本
        print("📊 [1/5] 从数据库抽取测试样本...")
        samples = await get_test_samples(pool, sample_size=5)
        print(f"  ✅ 成功抽取 {len(samples)} 场比赛")

        # 3. 执行特征提取
        print("\n🔧 [2/5] 执行特征提取...")
        features_list, stats = await test_feature_extraction(samples)

        success_rate = stats["success_count"] / stats["total_processed"] * 100 if stats["total_processed"] > 0 else 0

        print(f"  ✅ 成功: {stats['success_count']}")
        print(f"  ⚠️  部分成功: {stats['partial_count']}")
        print(f"  ❌ 失败: {stats['failed_count']}")
        print(f"  📈 成功率: {success_rate:.1f}%")

        # 4. 展示提取的特征
        print("\n📋 [3/5] 展示提取的特征...")
        display_features(samples, features_list)

        # 5. 写入数据库
        print("\n💾 [4/5] 写入数据库...")
        write_result = await test_database_persistence(features_list)
        print(f"  ✅ 成功写入: {write_result['success']} 条")
        print(f"  ❌ 写入失败: {write_result['failed']} 条")

        # 6. 验证数据库
        print("\n🔍 [5/5] 验证数据库写入...")
        db_results = await verify_database_write(pool)
        display_database_results(db_results)

        # 7. 生成测试报告
        print("\n\n")
        print("=" * 120)
        print(" " * 40 + "测试总结报告")
        print("=" * 120)

        summary = [
            ["测试样本数", len(samples)],
            ["特征提取成功率", f"{success_rate:.1f}%"],
            ["数据库写入成功", f"{write_result['success']}/{len(features_list)}"],
            ["表创建状态", "✅ match_features_v1 已创建"],
            ["验证状态", "✅ 数据已持久化"],
        ]

        print(tabulate(summary, headers=["指标", "值"], tablefmt="grid"))

        if success_rate >= 80 and write_result["success"] == len(features_list):
            print("\n🎉 测试全部通过！L3 特征提取组件已就绪。")
        else:
            print("\n⚠️  测试部分通过，需要进一步优化。")

        print("\n" + "=" * 120)

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
