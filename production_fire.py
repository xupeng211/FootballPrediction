#!/usr/bin/env python3
"""
Production Fire - Golden One-Click Script
==========================================

基于 GoldenDataMerger 的一键数据采集入口脚本

执行流程：
[NetworkShield 初始化] -> [选择比赛] -> [L2 采集] -> [L3 采集] -> [融合入库]

Usage:
    python production_fire.py --match_id 12345
    python production_fire.py --match_id 12345 --league "Premier League"
    python production_fire.py --match_id 12345 --force
    python production_fire.py --batch matches.txt

Author: [Genesis.SmokeTest]
Version: V1.0.0
Date: 2026-02-03
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("ProductionFire")


# ============================================================================
# ENTRY POINT
# ============================================================================


async def main() -> int:
    """主入口函数"""
    parser = argparse.ArgumentParser(
        description="Production Fire - Golden One-Click Data Harvest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python production_fire.py --match_id 404148650
  python production_fire.py --match_id 404148650 --league "Premier League" --season "2024-2025"
  python production_fire.py --match_id 404148650 --force
  python production_fire.py --batch matches.txt
  python production_fire.py --recent 10
        """
    )

    # Single match mode
    parser.add_argument(
        "--match-id",
        type=str,
        help="Single match ID to harvest"
    )
    parser.add_argument(
        "--league",
        type=str,
        help="League name (e.g., 'Premier League')"
    )
    parser.add_argument(
        "--season",
        type=str,
        default="2024-2025",
        help="Season (default: 2024-2025)"
    )
    parser.add_argument(
        "--home-team",
        type=str,
        help="Home team name"
    )
    parser.add_argument(
        "--away-team",
        type=str,
        help="Away team name"
    )

    # Batch mode
    parser.add_argument(
        "--batch",
        type=str,
        help="File containing match IDs (one per line)"
    )
    parser.add_argument(
        "--recent",
        type=int,
        help="Harvest N most recent matches from database"
    )

    # Options
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-harvest (ignore existing data)"
    )
    parser.add_argument(
        "--skip-l2",
        action="store_true",
        help="Skip L2 (FotMob) data collection"
    )
    parser.add_argument(
        "--skip-l3",
        action="store_true",
        help="Skip L3 (OddsPortal) data collection"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Concurrency for batch mode (default: 3)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without executing"
    )

    args = parser.parse_args()

    # Validate arguments
    if not any([args.match_id, args.batch, args.recent]):
        parser.print_help()
        logger.error("Please specify --match-id, --batch, or --recent")
        return 1

    # Import GoldenDataMerger
    try:
        from src.infrastructure.merger.GoldenDataMerger import GoldenDataMerger
    except ImportError as e:
        logger.error(f"Failed to import GoldenDataMerger: {e}")
        return 1

    # Initialize merger
    merger = GoldenDataMerger(
        enable_network_shield=True,
    )

    try:
        # ====================================================================
        # BANNER
        # ====================================================================
        print()
        print("=" * 70)
        print("  PRODUCTION FIRE - GOLDEN ONE-CLICK DATA HARVEST")
        print("=" * 70)
        print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print()

        # ====================================================================
        # SINGLE MATCH MODE
        # ====================================================================
        if args.match_id:
            team_names = None
            if args.home_team and args.away_team:
                team_names = (args.home_team, args.away_team)

            logger.info(f"[SINGLE MATCH] Mode: {args.match_id}")
            logger.info(f"  League: {args.league or 'Auto-detect'}")
            logger.info(f"  Season: {args.season}")
            logger.info(f"  Teams: {team_names or 'Auto-detect'}")
            logger.info(f"  Force: {args.force}")
            print()

            if args.dry_run:
                logger.info("[DRY RUN] Would harvest match")
                return 0

            summary = await merger.merge_match(
                match_id=args.match_id,
                league_name=args.league,
                season=args.season,
                team_names=team_names,
                force=args.force,
                skip_l2=args.skip_l2,
                skip_l3=args.skip_l3,
            )

            # Print summary
            print()
            print("=" * 70)
            print("  HARVEST SUMMARY")
            print("=" * 70)
            print(f"  Match ID: {summary.match_id}")
            print(f"  L1 Status: {summary.l1_result.status.value}")
            if summary.l2_result:
                print(f"  L2 Status: {summary.l2_result.status.value}")
            if summary.l3_result:
                print(f"  L3 Status: {summary.l3_result.status.value}")
            print(f"  Total Latency: {summary.total_latency_ms}ms")
            print(f"  Success: {summary.is_complete_success}")
            print("=" * 70)
            print()

            return 0 if summary.is_complete_success else 1

        # ====================================================================
        # BATCH MODE
        # ====================================================================
        elif args.batch:
            batch_file = Path(args.batch)
            if not batch_file.exists():
                logger.error(f"Batch file not found: {args.batch}")
                return 1

            match_ids = [
                line.strip() for line in batch_file.read_text().splitlines()
                if line.strip() and not line.startswith('#')
            ]

            logger.info(f"[BATCH] Mode: {len(match_ids)} matches")
            logger.info(f"  Concurrency: {args.concurrency}")
            logger.info(f"  Force: {args.force}")
            print()

            if args.dry_run:
                logger.info(f"[DRY RUN] Would harvest {len(match_ids)} matches")
                return 0

            summaries = await merger.merge_batch(
                match_ids=match_ids,
                force=args.force,
                skip_l2=args.skip_l2,
                skip_l3=args.skip_l3,
                concurrency=args.concurrency,
            )

            # Print summary
            success_count = sum(1 for s in summaries if s.is_complete_success)
            print()
            print("=" * 70)
            print("  BATCH HARVEST SUMMARY")
            print("=" * 70)
            print(f"  Total: {len(summaries)}")
            print(f"  Success: {success_count}")
            print(f"  Failed: {len(summaries) - success_count}")
            print("=" * 70)
            print()

            return 0 if success_count == len(summaries) else 1

        # ====================================================================
        # RECENT MODE
        # ====================================================================
        elif args.recent:
            logger.info(f"[RECENT] Mode: {args.recent} most recent matches")
            logger.info("  (Querying database for recent matches)")
            print()

            if args.dry_run:
                logger.info(f"[DRY RUN] Would harvest {args.recent} recent matches")
                return 0

            # Query recent matches
            conn = merger._get_connection()
            cur = conn.cursor()

            cur.execute("""
                SELECT match_id, league_name, season, home_team, away_team
                FROM matches
                ORDER BY match_date DESC
                LIMIT %s
            """, (args.recent,))

            recent_matches = cur.fetchall()
            cur.close()

            if not recent_matches:
                logger.warning("No recent matches found")
                return 0

            match_ids = [row[0] for row in recent_matches]

            summaries = await merger.merge_batch(
                match_ids=match_ids,
                force=args.force,
                skip_l2=args.skip_l2,
                skip_l3=args.skip_l3,
                concurrency=args.concurrency,
            )

            # Print summary
            success_count = sum(1 for s in summaries if s.is_complete_success)
            print()
            print("=" * 70)
            print("  RECENT MATCHES SUMMARY")
            print("=" * 70)
            print(f"  Total: {len(summaries)}")
            print(f"  Success: {success_count}")
            print(f"  Failed: {len(summaries) - success_count}")
            print("=" * 70)
            print()

            return 0 if success_count == len(summaries) else 1

    finally:
        merger.close()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        logger.info("\n[INTERRUPTED] User cancelled")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"[FATAL] {e}")
        sys.exit(1)
