#!/usr/bin/env python3
"""
[Genesis.OddsStealth] Gap Filling Runner
==========================================

专项补救收割 - 填补 L2 数据存在但 L3 数据缺失的比赛

Usage:
    # 标准补缺（每批 10 场，场次间 8 秒延迟）
    python scripts/production/gap_filling_runner.py

    # 激进模式（每批 20 场，场次间 5 秒延迟）
    python scripts/production/gap_filling_runner.py --batch-size 20 --delay 5

    # 单场测试
    python scripts/production/gap_filling_runner.py --single 4506600

Author: Genesis.StealthTeam
Version: V1.0
Date: 2026-01-31
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.bridge.adapters.odds_stealth_adapter import GapFillingOrchestrator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/ops/gap_filling.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="[Genesis.OddsStealth] Gap Filling Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Standard gap filling (10 matches per batch, 8s delay)
  python scripts/production/gap_filling_runner.py

  # Aggressive mode (20 matches per batch, 5s delay)
  python scripts/production/gap_filling_runner.py --batch-size 20 --delay 5

  # Single match test
  python scripts/production/gap_filling_runner.py --single 4506600

  # Continuous mode (runs until no gaps remain)
  python scripts/production/gap_filling_runner.py --continuous
        """
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of matches per batch (default: 10)"
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=8,
        help="Delay between matches in seconds (default: 8)"
    )
    parser.add_argument(
        "--single",
        type=str,
        metavar="MATCH_ID",
        help="Process a single match by ID"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuously until no gaps remain"
    )
    parser.add_argument(
        "--worker-id",
        type=int,
        metavar="ID",
        help="[Genesis.Shielding] Worker ID for IP isolation (0-4)"
    )

    args = parser.parse_args()

    # 确保 log 目录存在
    Path("logs/ops").mkdir(parents=True, exist_ok=True)

    # 打印 Banner
    banner = """
    ╔══════════════════════════════════════════════════════════════════╗
    ║     [Genesis.OddsStealth] Gap Filling Runner - V1.0             ║
    ║                                                                ║
    ║  专项补救收割 - 填补 L2 存在但 L3 缺失的比赛                 ║
    ║                                                                ║
    ║  特性：                                                         ║
    ║  • 指数退避重试 (30s → 2min → 8min)                             ║
    ║  • 自愈逻辑 (识别 403/429)                                      ║
    ║  • UA 随机轮换 + Jitter 延迟                                      ║
    ║  • [Genesis.Shielding] 代理池 + IP 物理隔离                      ║
    ║  • 极低频、极稳的抓取节奏                                       ║
    ╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)
    logger.info("=" * 60)
    logger.info("[Genesis.OddsStealth] Gap Filling Started")
    logger.info("=" * 60)
    logger.info(f"Batch Size: {args.batch_size}")
    logger.info(f"Delay: {args.delay}s")
    logger.info(f"Single Match: {args.single if args.single else 'N/A'}")
    logger.info(f"Continuous: {args.continuous}")
    logger.info(f"Worker ID: {args.worker_id if args.worker_id is not None else 'N/A'}")
    logger.info("=" * 60)

    # [Genesis.Shielding] 创建编排器时传入 worker_id
    orchestrator = GapFillingOrchestrator(worker_id=args.worker_id)

    try:
        if args.single:
            # 单场测试模式 - [Genesis.ReLink] 从 matches_mapping 查找真实 URL
            logger.info(f"[SingleMatch] Testing match: {args.single}")

            # 从 matches_mapping 查找真实 URL
            import psycopg2
            from src.config_unified import get_settings

            settings = get_settings()
            conn = psycopg2.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value()
            )
            cursor = conn.cursor()
            cursor.execute(
                "SELECT oddsportal_url FROM matches_mapping WHERE fotmob_id = %s",
                (args.single,)
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if not row or not row[0]:
                logger.error(f"[SingleMatch] {args.single}: No oddsportal_url found in matches_mapping")
                logger.error("[SingleMatch] Please run discovery first: python scripts/run_discovery.py")
                return 1

            odds_url = row[0]
            logger.info(f"[SingleMatch] Using URL: {odds_url}")

            # 使用编排器的引擎（已配置代理）
            result = orchestrator.engine.extract_with_retry(
                args.single,
                odds_url
            )

            logger.info("=" * 60)
            if result.success:
                logger.info(f"[SUCCESS] Match {args.single} extracted successfully!")
                logger.info(f"  Attempts: {result.attempts}")
                logger.info(f"  Time: {result.total_time:.1f}s")
            else:
                logger.warning(f"[FAILED] Match {args.single} extraction failed")
                logger.info(f"  Attempts: {result.attempts}")
                logger.info(f"  Block Type: {result.block_type}")
                logger.info(f"  Error: {result.error}")
            logger.info("=" * 60)

            return 0 if result.success else 1

        else:
            # 批量补缺模式
            if args.continuous:
                # 连续模式 - 循环直到没有缺口
                cycle_count = 0
                while True:
                    cycle_count += 1
                    logger.info(f"\n[Continuous] Starting cycle #{cycle_count}...")

                    stats = orchestrator.run_gap_filling_cycle(
                        batch_size=args.batch_size,
                        delay_between_matches=args.delay
                    )

                    if stats["total_processed"] == 0:
                        logger.info("\n[Continuous] No more gaps to fill. Job complete!")
                        break

                    success_rate = 100 * stats["successful"] / stats["total_processed"]
                    logger.info(f"\n[Continuous] Cycle #{cycle_count} Summary:")
                    logger.info(f"  Success Rate: {success_rate:.1f}%")
                    logger.info(f"  Processed: {stats['successful']}/{stats['total_processed']}")

                    # 如果成功率太低，增加延迟
                    if success_rate < 30:
                        new_delay = args.delay * 2
                        logger.warning(f"[Continuous] Low success rate ({success_rate:.1f}%), increasing delay to {new_delay}s")
                        args.delay = new_delay
            else:
                # 单轮模式
                stats = orchestrator.run_gap_filling_cycle(
                    batch_size=args.batch_size,
                    delay_between_matches=args.delay
                )

                logger.info("\n" + "=" * 60)
                logger.info("[FINAL REPORT]")
                logger.info("=" * 60)
                logger.info(f"Total Processed: {stats['total_processed']}")
                logger.info(f"Successful: {stats['successful']}")
                logger.info(f"Failed: {stats['failed']}")
                logger.info(f"Blocked: {stats['blocked']}")
                logger.info(f"Success Rate: {100 * stats['successful'] / stats['total_processed']:.1f}%")
                logger.info("=" * 60)

                return 0 if stats["successful"] > 0 else 1

    except KeyboardInterrupt:
        logger.info("\n[INTERRUPTED] Gap filling stopped by user")
        return 130

    except Exception as e:
        logger.exception(f"[FATAL] Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
