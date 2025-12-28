#!/usr/bin/env python3
"""
V26.1 全量特征提取流水线（支持增量模式）
==========================================

Usage:
    python scripts/run_v26_full_pipeline.py --mode incremental  # 增量采集
    python scripts/run_v26_full_pipeline.py --mode full          # 全量采集
    python scripts/run_v26_full_pipeline.py --mode extract       # 仅特征提取

Author: Senior Backend Architect
Version: V26.1
Date: 2025-12-28
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings
from src.processors import ExtractorRegistry
from src.ops.performance_engine import ParallelFeatureExtractor

# V51.0: 使用官方核心采集器
from src.api.collectors.v51_incremental_collector import IncrementalCollector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/v26_full_pipeline.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# 步骤 1: 增量/全量采集
# ============================================================================

async def step_1_collect_data(mode: str = "incremental", target_count: int = 50):
    """
    步骤 1: 数据采集

    Args:
        mode: 采集模式 (incremental | full)
        target_count: 目标采集数量
    """
    print("=" * 70)
    print(f"📡 步骤 1: 数据采集 ({mode} 模式)")
    print("=" * 70)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标数量: {target_count}")
    print()

    collector = IncrementalCollector(target_count=target_count)

    incremental = (mode == "incremental")
    stats = await collector.collect(incremental=incremental)

    print("\n" + "=" * 70)
    print("✅ 数据采集完成")
    print("=" * 70)
    print(f"获取 L1: {stats.fetched_l1}")
    print(f"下载完整: {stats.fetched_full}")
    print(f"入库 matches: {stats.saved_matches}")
    print(f"入库 raw_data: {stats.saved_raw_data}")
    print(f"耗时: {stats.elapsed_seconds:.2f} 秒")
    print(f"HTTP 200: {stats.http_200}")
    print(f"HTTP 错误: {stats.http_errors}")
    print("=" * 70)

    return stats


# ============================================================================
# 步骤 2: 特征提取
# ============================================================================

def step_2_extract_features():
    """
    步骤 2: 特征提取 - V26.2 自适应引擎
    """
    print("\n" + "=" * 70)
    print("🔬 步骤 2: 特征提取 - V26.2 自适应引擎")
    print("=" * 70)

    settings = get_settings()
    db = settings.database

    conn = psycopg2.connect(
        host=db.host, port=db.port, database=db.name, user=db.user, password=db.password.get_secret_value()
    )

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 获取所有有 raw_data 的比赛（未提取或需要重新提取的）
        cur.execute("""
            SELECT external_id
            FROM raw_match_data
            ORDER BY created_at DESC
        """)

        matches = cur.fetchall()

        if not matches:
            print("\n⚠️  没有找到原始数据！请先运行数据采集。")
            return 0

        print(f"\n📊 找到 {len(matches)} 场有原始数据的比赛")
        print("🔧 开始提取特征...\n")

        # 获取提取器
        extractor = ExtractorRegistry.get("V25.1")

        # 并行提取
        match_list = []
        for match in matches:
            match_list.append({
                "match_id": match["external_id"],
            })

        parallel_extractor = ParallelFeatureExtractor(
            max_workers=3,
            batch_size=50,
            memory_limit_mb=2000,
        )

        print("📊 开始并行提取特征...")
        start_time = datetime.now()

        results = parallel_extractor.extract_batch_parallel(
            matches=match_list,
            extractor_class_path="src.processors.v25_production_extractor.V25ProductionExtractor",
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        # 统计结果
        success_count = sum(1 for r in results if r[1] is not None)
        failed_count = len(results) - success_count

        print(f"\n✅ 提取完成")
        print(f"   耗时: {elapsed:.2f} 秒")
        print(f"   吞吐量: {len(match_list) / elapsed:.1f} 条/秒")
        print(f"   成功: {success_count}")
        print(f"   失败: {failed_count}")

        # 特征维度统计
        feature_counts = [len(r[1]) if r[1] else 0 for r in results if r[1] is not None]
        if feature_counts:
            import statistics

            print(f"\n📊 特征维度统计:")
            print(f"   平均: {statistics.mean(feature_counts):.1f} 维")
            print(f"   最小: {min(feature_counts)} 维")
            print(f"   最大: {max(feature_counts)} 维")
            print(f"   中位数: {statistics.median(feature_counts):.1f} 维")

            # 目标是 6000 维左右
            avg_dims = statistics.mean(feature_counts)
            if 5000 <= avg_dims <= 7000:
                print("   ✅ 维度符合预期 (5000-7000)")
            else:
                print("   ⚠️  维度偏离预期 (目标: ~6000)")

        # TODO: 写入 match_features_training 表
        print("\n📝 特征提取完成，待写入数据库...")

        print("\n" + "=" * 70)
        print("📊 特征提取完成统计")
        print("=" * 70)
        print(f"总处理: {len(results)} 场")
        print(f"成功: {success_count} 场")
        print(f"成功率: {success_count / len(results) * 100:.1f}%")
        if feature_counts:
            print(f"平均维度: {sum(feature_counts) / len(feature_counts):.0f}")
        print("=" * 70)

        return success_count

    finally:
        cur.close()
        conn.close()


# ============================================================================
# 步骤 3: 数据审计
# ============================================================================

def step_3_audit_data():
    """
    步骤 3: 数据审计
    """
    print("\n" + "=" * 70)
    print("🔍 步骤 3: 数据审计")
    print("=" * 70)

    settings = get_settings()
    db = settings.database

    conn = psycopg2.connect(
        host=db.host, port=db.port, database=db.name, user=db.user, password=db.password.get_secret_value()
    )

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 按数据源统计
        cur.execute("""
            SELECT api_source, COUNT(*) as count
            FROM raw_match_data
            GROUP BY api_source
            ORDER BY count DESC
        """)

        print("\n📡 数据源分布:")
        for row in cur.fetchall():
            print(f"  {row['api_source']:20s}: {row['count']:5d} 场")

        # 最新比赛
        cur.execute("""
            SELECT external_id, home_team, away_team, match_time::date as match_date, status
            FROM matches
            ORDER BY match_time DESC
            LIMIT 10
        """)

        print("\n📅 最新比赛 (前 10 场):")
        for row in cur.fetchall():
            print(f"  {row['external_id']}: {row['home_team']:20s} vs {row['away_team']:20s} | {row['match_date']} | {row['status']}")

        # 总计
        cur.execute("SELECT COUNT(*) as total FROM matches")
        total = cur.fetchone()["total"]
        print(f"\n总计: {total:,} 场比赛")

    finally:
        cur.close()
        conn.close()


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """主流程"""
    parser = argparse.ArgumentParser(description="V26.1 全量特征提取流水线")
    parser.add_argument(
        "--mode",
        choices=["incremental", "full", "extract"],
        default="incremental",
        help="运行模式: incremental(增量采集), full(全量采集), extract(仅特征提取)",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=50,
        help="目标采集数量（默认: 50）",
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="跳过特征提取步骤",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("🚀 V26.1 全量特征提取流水线")
    print("=" * 70)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"运行模式: {args.mode}")
    print(f"目标数量: {args.target}")
    print("=" * 70)

    # 步骤 1: 数据采集（如果不是 extract 模式）
    if args.mode != "extract":
        await step_1_collect_data(mode=args.mode, target_count=args.target)

    # 步骤 2: 特征提取
    if not args.skip_extract:
        step_2_extract_features()

    # 步骤 3: 数据审计
    step_3_audit_data()

    print("\n" + "=" * 70)
    print("✅ V26.1 流水线完成!")
    print("=" * 70)
    print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
