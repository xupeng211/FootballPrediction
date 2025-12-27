#!/usr/bin/env python3
"""
V26.0 最终全量特征提取流水线
====================================

流程:
1. L2 数据采集 (获取原始 JSON)
2. L3 特征提取 (V25.1 自适应引擎)
3. 质量监控与统计
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

import asyncpg
import psycopg2

sys.path.insert(0, str(Path(__file__).parent.parent))

from psycopg2.extras import RealDictCursor
from scripts.collectors.fotmob_collector_l1_l2 import FotMobL1L2Collector

from src.config_unified import get_settings
from src.processors import ExtractorRegistry

# 配置日志
logging.basicConfig(
    level=logging.WARNING,  # 静默模式
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def harvest_l2_data(target_matches: int = 9305):
    """
    L2 数据采集 - 获取原始统计数据
    """
    print("=" * 70)
    print("📡 L2 数据采集 - 获取原始统计数据")
    print("=" * 70)

    collector = FotMobL1L2Collector(
        batch_size=50, delay_between_requests=2.0, max_l2_concurrency=3, silent_mode=True, progress_interval=500
    )

    await collector.initialize()

    try:
        # 获取所有 match_id
        settings = get_settings()
        conn = await asyncpg.connect(
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
            database=settings.database.name,
            host=settings.database.host,
        )

        try:
            rows = await conn.fetch("SELECT match_id FROM matches ORDER BY season, match_date")
            match_ids = [row["match_id"] for row in rows]

            print(f"\n📊 找到 {len(match_ids)} 场比赛")
            print(f"🎯 目标: 采集 {target_matches} 场的 L2 数据\n")

            # 执行 L2 批量采集
            result = await collector.batch_collect_l2_concurrent(match_ids[:target_matches])

            print("\n✅ L2 采集完成:")
            print(f"   尝试: {result['attempted']}")
            print(f"   成功: {result['success']}")
            print(f"   失败: {result['failed']}")
            print(f"   成功率: {result['success'] / result['attempted'] * 100:.1f}%")

        finally:
            await conn.close()

    finally:
        await collector.close()


def extract_l3_features():
    """
    L3 特征提取 - V25.1 自适应引擎
    """
    print("\n" + "=" * 70)
    print("🔬 L3 特征提取 - V25.1 自适应引擎")
    print("=" * 70)

    # 获取提取器
    extractor = ExtractorRegistry.get("V25.1")

    settings = get_settings()
    db = settings.database

    conn = psycopg2.connect(
        host=db.host, port=db.port, database=db.name, user=db.user, password=db.password.get_secret_value()
    )

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 获取所有有 L2 数据的比赛
        cur.execute("""
            SELECT match_id, season
            FROM raw_match_data
            ORDER BY season, match_id
        """)

        matches = cur.fetchall()

        if not matches:
            print("\n⚠️  没有找到 L2 数据！请先运行 L2 采集。")
            return 0

        print(f"\n📊 找到 {len(matches)} 场有 L2 数据的比赛")
        print("🔧 开始提取特征...\n")

        batch_size = 200
        total_processed = 0
        total_success = 0
        total_features = 0
        last_progress = 0

        for i in range(0, len(matches), batch_size):
            batch = matches[i : i + batch_size]

            for match in batch:
                match_id = match["match_id"]

                try:
                    # 获取 L2 原始数据
                    cur.execute("SELECT raw_data FROM raw_match_data WHERE match_id = %s", (match_id,))
                    row = cur.fetchone()

                    if not row or not row["raw_data"]:
                        continue

                    raw_data = row["raw_data"]

                    # 提取特征
                    result = extractor.extract(raw_data)

                    if result.status == "success":
                        # 保存特征
                        cur.execute(
                            """
                            INSERT INTO match_features_training (match_id, feature_version, features, extracted_at)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (match_id) DO UPDATE SET
                                features = EXCLUDED.features,
                                feature_version = EXCLUDED.feature_version,
                                extracted_at = EXCLUDED.extracted_at
                        """,
                            (match_id, "V26.0", result.features, datetime.now()),
                        )

                        total_success += 1
                        total_features += len(result.features)

                except Exception as e:
                    logger.warning(f"处理比赛 {match_id} 失败: {e}")
                    continue

            conn.commit()
            total_processed += len(batch)

            # 每 1000 场输出进度
            if total_processed - last_progress >= 1000 or total_processed == len(matches):
                success_rate = total_success / total_processed * 100 if total_processed > 0 else 0
                avg_dims = total_features / total_success if total_success > 0 else 0
                print(
                    f"  [{total_processed:,}/{len(matches):,}] 成功率: {success_rate:.1f}% | 平均维度: {avg_dims:.0f}"
                )
                last_progress = total_processed

        # 最终统计
        print("\n" + "=" * 70)
        print("📊 提取完成统计")
        print("=" * 70)
        print(f"总处理: {total_processed:,} 场")
        print(f"成功: {total_success:,} 场")
        print(f"成功率: {total_success / total_processed * 100:.1f}%")
        print(f"平均维度: {total_features / total_success:.0f}")
        print("=" * 70)

        return total_success

    finally:
        cur.close()
        conn.close()


def audit_features():
    """
    特征维度审计
    """
    print("\n" + "=" * 70)
    print("🔍 特征维度审计 (前 100 场)")
    print("=" * 70)

    settings = get_settings()
    db = settings.database

    conn = psycopg2.connect(
        host=db.host, port=db.port, database=db.name, user=db.user, password=db.password.get_secret_value()
    )

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT match_id, features
            FROM match_features_training
            WHERE feature_version = 'V26.0'
            ORDER BY match_id
            LIMIT 100
        """)

        rows = cur.fetchall()

        if not rows:
            print("⚠️  没有找到特征数据！")
            return

        dimensions = []
        for row in rows:
            if row["features"]:
                dims = len(row["features"])
                dimensions.append(dims)

        if dimensions:
            import statistics

            avg_dims = statistics.mean(dimensions)
            min_dims = min(dimensions)
            max_dims = max(dimensions)

            print(f"样本数量: {len(dimensions)} 场")
            print(f"平均维度: {avg_dims:.0f}")
            print(f"最小维度: {min_dims}")
            print(f"最大维度: {max_dims}")

            # 目标是 6000 维左右
            if 5000 <= avg_dims <= 7000:
                print("✅ 维度符合预期 (5000-7000)")
            else:
                print("⚠️  维度偏离预期 (目标: ~6000)")

    finally:
        cur.close()
        conn.close()


def final_statistics():
    """
    最终统计
    """
    print("\n" + "=" * 70)
    print("📋 最终统计")
    print("=" * 70)

    settings = get_settings()
    db = settings.database

    conn = psycopg2.connect(
        host=db.host, port=db.port, database=db.name, user=db.user, password=db.password.get_secret_value()
    )

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 按特征版本统计
        cur.execute("""
            SELECT feature_version, COUNT(*) as count
            FROM match_features_training
            GROUP BY feature_version
            ORDER BY feature_version
        """)

        print("\n特征版本分布:")
        for row in cur.fetchall():
            print(f"  {row['feature_version']}: {row['count']:,} 场")

        # 总计
        cur.execute("SELECT COUNT(*) as total FROM match_features_training")
        total = cur.fetchone()["total"]
        print(f"\n总计: {total:,} 场")

        # 目标检查
        target = 9305
        if total >= target:
            print(f"✅ 达成目标! ({total:,}/{target:,})")
        else:
            print(f"⚠️  未达成目标 ({total:,}/{target:,}, 还需 {target - total:,} 场)")

    finally:
        cur.close()
        conn.close()


async def main():
    """主流程"""
    print("=" * 70)
    print("🚀 V26.0 最终全量特征提取流水线")
    print("=" * 70)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 1: L2 数据采集
    await harvest_l2_data(target_matches=9305)

    # Step 2: L3 特征提取
    extract_l3_features()

    # Step 3: 维度审计
    audit_features()

    # Step 4: 最终统计
    final_statistics()

    print("\n" + "=" * 70)
    print("✅ V26.0 流水线完成!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
