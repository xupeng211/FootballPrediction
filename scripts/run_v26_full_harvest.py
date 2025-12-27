#!/usr/bin/env python3
"""
V26.1 全量收割脚本 - "零缺陷"生产流水线
=========================================

功能:
    1. 4 进程并行提取特征
    2. 动态批次大小（内存自适应）
    3. 特征剪枝（控制在 8000 维）
    4. 幂等性保证（可重启不重不漏）

使用方法:
    python scripts/run_v26_full_harvest.py [--limit N] [--workers N]

Author: Principal Architect & Performance Expert
Version: V26.1 (Production)
Date: 2025-12-27
"""

import argparse
import gc
import logging
import signal
import sys
import time
from pathlib import Path

import psycopg2

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config_unified import get_settings
from src.ops.performance_engine import PerformancePipeline

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(message)s",
    handlers=[logging.FileHandler("logs/pipeline.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ============================================================================
# 全局标志
# ============================================================================

_shutdown_requested = False


def signal_handler(signum, frame):
    """信号处理器"""
    global _shutdown_requested
    logger.info(f"收到信号 {signum}，请求优雅关闭...")
    _shutdown_requested = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# ============================================================================
# 数据库操作
# ============================================================================


def get_candidates(
    limit: int | None = None,
    settings=None,
) -> list[dict]:
    """
    获取待处理的候选比赛

    Args:
        limit: 最大数量（None = 全部）
        settings: 配置对象

    Returns:
        候选比赛列表
    """
    if settings is None:
        settings = get_settings()

    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    cur = conn.cursor()

    # 构建查询 - 排除已有特征的比赛
    limit_clause = f"LIMIT {limit}" if limit else ""

    cur.execute(f"""
        SELECT
            m.match_id,
            m.season,
            m.match_date,
            m.home_team,
            m.away_team,
            r.raw_data
        FROM matches m
        INNER JOIN raw_match_data r ON r.match_id = m.match_id
        WHERE UPPER(m.status) = 'FINISHED'
        AND NOT EXISTS (
            SELECT 1 FROM match_features_training f WHERE f.match_id = m.match_id
        )
        ORDER BY m.match_date DESC
        {limit_clause};
    """)

    candidates = []
    for row in cur.fetchall():
        candidates.append(
            {
                "match_id": row[0],
                "season": row[1],
                "match_date": row[2].isoformat() if row[2] else None,
                "home_team": row[3],
                "away_team": row[4],
                "raw_data": row[5],
            }
        )

    conn.close()
    return candidates


def get_progress(settings) -> dict:
    """获取当前进度"""
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    cur = conn.cursor()

    # 已处理数量（有特征数据的比赛）
    cur.execute("""
        SELECT COUNT(DISTINCT match_id) as count
        FROM match_features_training;
    """)
    processed = cur.fetchone()[0]

    # 总数量
    cur.execute("""
        SELECT COUNT(*) as count
        FROM matches
        WHERE UPPER(status) = 'FINISHED';
    """)
    total = cur.fetchone()[0]

    conn.close()

    return {
        "processed": processed,
        "total": total,
        "percent": (processed / total * 100) if total > 0 else 0,
    }


# ============================================================================
# 主函数
# ============================================================================


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="V26.1 全量特征收割",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理所有比赛
  python scripts/run_v26_full_harvest.py

  # 试运行 100 场
  python scripts/run_v26_full_harvest.py --limit 100

  # 使用 2 个 worker
  python scripts/run_v26_full_harvest.py --workers 2
        """,
    )
    parser.add_argument("--limit", type=int, default=None, help="最大处理数量（默认：全部）")
    parser.add_argument("--workers", type=int, default=4, help="Worker 进程数（默认：4）")
    parser.add_argument("--batch-size", type=int, default=50, help="初始批次大小（默认：50，会动态调整）")
    parser.add_argument("--resume", action="store_true", help="继续之前的进度（跳过已处理的）")

    args = parser.parse_args()

    # 获取配置
    settings = get_settings()

    logger.info("=" * 60)
    logger.info("V26.1 全量特征收割启动")
    logger.info("=" * 60)
    logger.info(f"目标数量: {args.limit or '全部'}")
    logger.info(f"Worker 数: {args.workers}")
    logger.info(f"批次大小: {args.batch_size}（动态调整）")
    logger.info(f"继续模式: {args.resume}")
    logger.info("")

    # 获取初始进度
    progress = get_progress(settings)
    logger.info(f"初始进度: {progress['processed']}/{progress['total']} ({progress['percent']:.1f}%)")

    # 获取候选
    logger.info("获取候选比赛...")
    candidates = get_candidates(args.limit, settings)
    logger.info(f"候选数量: {len(candidates)}")

    if not candidates:
        logger.info("没有待处理的比赛")
        return

    # 创建流水线
    pipeline = PerformancePipeline(
        settings.database,
        max_workers=args.workers,
        batch_size=args.batch_size,
    )

    # 分批处理（每批 200 场）
    batch_size = 200
    total_batches = (len(candidates) + batch_size - 1) // batch_size

    start_time = time.time()
    total_processed = 0

    for i in range(0, len(candidates), batch_size):
        if _shutdown_requested:
            logger.info("收到关闭信号，停止处理...")
            break

        batch = candidates[i : i + batch_size]
        batch_num = i // batch_size + 1

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"批次 {batch_num}/{total_batches}")
        logger.info("=" * 60)

        # 处理批次
        stats = pipeline.process_candidates(
            batch,
            "src.processors.v25_production_extractor.V25ProductionExtractor",
        )

        total_processed += stats["inserted"]
        elapsed = time.time() - start_time
        throughput = stats["total_candidates"] / elapsed * 60 if elapsed > 0 else 0

        logger.info("")
        logger.info("批次统计:")
        logger.info(f"  处理: {stats['total_candidates']} 场")
        logger.info(f"  提取: {stats['extraction_success']} 场")
        logger.info(f"  入库: {stats['inserted']} 场")
        logger.info(f"  耗时: {stats['elapsed_seconds']:.1f} 秒")
        logger.info(f"  吞吐量: {throughput:.0f} 场/分钟")

        # 更新进度
        progress = get_progress(settings)
        logger.info("")
        logger.info(f"总体进度: {progress['processed']}/{progress['total']} ({progress['percent']:.1f}%)")
        logger.info(f"已处理: {total_processed} 场")

        # 强制 GC
        gc.collect()

    # 最终报告
    total_elapsed = time.time() - start_time
    final_throughput = total_processed / total_elapsed * 60 if total_elapsed > 0 else 0

    logger.info("")
    logger.info("=" * 60)
    logger.info("收割完成！")
    logger.info("=" * 60)
    logger.info(f"总处理: {total_processed} 场")
    logger.info(f"总耗时: {total_elapsed:.1f} 秒 ({total_elapsed / 60:.1f} 分钟)")
    logger.info(f"平均吞吐: {final_throughput:.0f} 场/分钟")

    progress = get_progress(settings)
    logger.info(f"最终进度: {progress['processed']}/{progress['total']} ({progress['percent']:.1f}%)")


if __name__ == "__main__":
    main()
