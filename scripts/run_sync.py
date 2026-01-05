#!/usr/bin/env python3
"""V117.1 Phase 1 - Direct Harvest Production Engine (Hybrid Mode).

Implements Phase 1 of the data backfill strategy:
- Target: 2,415 matches WITH oddsportal_url but WITHOUT Entity_P data
- Unified 5-provider extraction (E_P, E_B, E_W, E_L, E_AVG)
- V117.1 Hybrid Adaptive Engine (Laser + Gravity dual-mode extraction)
- Network Resilience Protocol (4 workers, 3-7s delays, exponential backoff)
- Data quality validation (integrity score, distribution check)
- Database upsert for multi-source coexistence
- Enhanced progress monitoring (detailed checkpoint every 100 matches)
- Silent logging mode (no raw values, URLs, or brand names)

V117.1 Core Features:
    1. Hybrid Adaptive Engine - Dual-mode extraction with automatic fallback
       - Laser Mode: V117.1 Column Anchor Alignment Algorithm
       - Gravity Mode: V117.1 Geometric Row-Clustering Algorithm
       - Automatic Merge: Deduplicate by Entity ID
    2. Header Resilience Protocol - Enhanced header detection for legacy pages
    3. 100% legacy page compatibility with historical structures

Usage:
    # Test run with 3 matches (silent production test)
    PYTHONPATH=. python scripts/run_sync.py --limit 3 --workers 1 --debug

    # Full Phase 1 harvest (2,415 matches)
    PYTHONPATH=. python scripts/run_sync.py --workers 4

    # Resume from checkpoint
    PYTHONPATH=. python scripts/run_sync.py --resume
"""

import argparse
import asyncio
from datetime import datetime
import json
import logging
import random
from pathlib import Path
import sys
from typing import Any

from playwright.async_api import async_playwright
import psycopg2

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.collectors.market_data_engine import (
    VENDOR_MAPPING,
    V100DatabaseManager,
    V100NetworkResilience,
    extract_multi_vendor_odds,
)
from src.config_unified import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/v100_0_multivendor_harvest.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# V100.0 Network Resilience Implementation
# ============================================================================

class V117HarvestOrchestrator:
    """V117.1 Multi-provider harvest orchestrator with hybrid engine.

    Features:
        - V117.1 Hybrid Adaptive Engine (Laser + Gravity dual-mode)
        - Header Resilience Protocol for legacy pages
        - Controlled parallelism (max 4 workers)
        - Random request delays (3-7 seconds)
        - Exponential backoff retry
        - Progress tracking and checkpointing
        - Silent logging mode (no raw values, URLs, or brand names)
    """

    def __init__(self, max_workers: int = 4):
        """Initialize the orchestrator.

        Args:
            max_workers: Maximum parallel workers (default: 4)
        """
        self.max_workers = max_workers
        self.resilience = V100NetworkResilience(max_workers=max_workers)
        self.db_manager = V100DatabaseManager()
        # Phase 1: Use dedicated checkpoint file
        self.checkpoint_file = Path("logs/phase1_checkpoint.txt")

        # V110.1: Sanitized entity identifiers (E_X format)
        self.stats = {
            "total_matches": 0,
            "successful_matches": 0,
            "failed_matches": 0,
            "total_vendor_data": 0,
            "network_retries": 0,
            "circuit_breaker_trips": 0,
            "vendor_counts": {
                "E_P": 0,    # Entity_P (ID 18)
                "E_W": 0,    # Entity_W (ID 7)
                "E_B": 0,    # Entity_B (ID 16)
                "E_L": 0,    # Entity_L (ID 2)
                "E_AVG": 0,  # Entity_AVG
            },
            "start_time": None,
            "end_time": None,
        }

    def get_pending_matches(self, limit: int | None = None) -> list[tuple[str, str, datetime]]:
        """Get pending matches from database for Phase 1 direct harvest.

        Phase 1 Target Criteria:
            - oddsportal_url IS NOT NULL (已有 URL)
            - No Entity_P (ID 18) data in metrics_multi_source_data
            - Ordered by match_date DESC (最近的比赛优先)

        Args:
            limit: Maximum number of matches to retrieve

        Returns:
            List of (match_id, oddsportal_url, match_date) tuples
        """
        settings = get_settings()
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
        )

        cursor = conn.cursor()

        limit_clause = f"LIMIT {limit}" if limit else ""

        # V106.8 Phase 1: Target matches WITH oddsportal_url but WITHOUT Entity_P data
        # 针对审计中发现的 2,415 场已有 URL 的比赛
        # 只选择已完成的比赛（is_finished = true），因为未来比赛没有赔率数据
        query = f"""
            SELECT m.match_id, m.oddsportal_url, m.match_date
            FROM matches m
            WHERE m.oddsportal_url IS NOT NULL
              AND m.oddsportal_url != ''
              AND m.oddsportal_url LIKE '%oddsportal.com%'
              AND m.is_finished = true
              -- Phase 1: 仅收割有 URL 但无 Entity_P 数据的比赛
              AND NOT EXISTS (
                  SELECT 1
                  FROM metrics_multi_source_data msd
                  WHERE msd.match_id = m.match_id
                    AND msd.source_name = 'Entity_P'
                    AND msd.final_h IS NOT NULL
              )
            ORDER BY m.match_date DESC
            {limit_clause}
        """

        cursor.execute(query)
        matches = cursor.fetchall()

        cursor.close()
        conn.close()

        logger.info(f"Phase 1: Retrieved {len(matches)} pending matches with URLs but no Entity_P data")
        return [(row[0], row[1], row[2]) for row in matches]

    def load_checkpoint(self) -> set:
        """Load processed match IDs from checkpoint file."""
        if not self.checkpoint_file.exists():
            return set()

        with open(self.checkpoint_file) as f:
            return set(line.strip() for line in f if line.strip())

    def save_checkpoint(self, match_id: str) -> None:
        """Append match ID to checkpoint file."""
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_file, "a") as f:
            f.write(f"{match_id}\n")

    async def extract_single_match(
        self,
        match_id: str,
        url: str,
        match_date: datetime
    ) -> dict[str, Any]:
        """Extract multi-provider metrics for a single match.

        Args:
            match_id: Match ID
            url: OddsPortal URL
            match_date: Match date

        Returns:
            Result dictionary with extraction status
        """
        result = {
            "match_id": match_id,
            "url": url,
            "match_date": match_date,
            "success": False,
            "vendors_extracted": 0,
            "vendor_data": {},
            "error": None
        }

        async with async_playwright() as p:
            browser = None
            try:
                # Acquire network slot
                await self.resilience.acquire_slot()

                # Launch browser
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-dev-shm-usage", "--no-sandbox"]
                )
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = await context.new_page()

                # Navigate with retry
                await self.resilience.execute_with_retry(
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                )

                # Simulate user behavior - random smooth scroll
                await self._simulate_user_scroll(page)

                # Extract all vendors
                extraction_result = await extract_multi_vendor_odds(
                    page=page,
                    match_id=match_id,
                    match_date=match_date,
                    save_to_db=True
                )

                result["vendors_extracted"] = extraction_result.get("vendors_extracted", 0)
                result["vendor_data"] = extraction_result.get("vendor_data", {})
                result["success"] = extraction_result.get("success", False)

                # V110.2: Track entity-specific counts (E_X format)
                if result["success"] and result["vendor_data"]:
                    for vendor_name in result["vendor_data"].keys():
                        # Map Entity_* to E_* format
                        mapped_key = self._map_to_e_format(vendor_name)
                        if mapped_key and mapped_key in self.stats["vendor_counts"]:
                            self.stats["vendor_counts"][mapped_key] += 1

                if result["success"]:
                    logger.info(
                        f"[{match_id}] ✅ SUCCESS: "
                        f"{result['vendors_extracted']} providers extracted"
                    )
                else:
                    result["error"] = "No providers extracted"

            except Exception as e:
                result["error"] = f"Exception: {e!s}"
                logger.warning(f"[{match_id}] ❌ FAILED: {e}")

            finally:
                # Release network slot
                self.resilience.release_slot()

                if browser:
                    await browser.close()

        return result

    async def _simulate_user_scroll(self, page) -> None:
        """Simulate human-like scrolling behavior.

        Random smooth scroll to mimic real user interaction.
        """
        try:
            # Random scroll offset
            scroll_y = random.randint(100, 500)

            await page.evaluate(f"window.scrollBy(0, {scroll_y})")
            await asyncio.sleep(random.uniform(0.5, 1.5))

            # Scroll back
            await page.evaluate(f"window.scrollBy(0, -{scroll_y})")
            await asyncio.sleep(random.uniform(0.3, 0.8))

        except Exception:
            # Scroll simulation is optional, don't fail on error
            pass

    def _map_to_e_format(self, vendor_name: str) -> str | None:
        """V110.2: Map Entity_* source names to E_* format.

        Args:
            vendor_name: Source name from extraction (e.g., "Entity_P")

        Returns:
            E_X format key (e.g., "E_P") or None if not found
        """
        mapping = {
            "Entity_P": "E_P",
            "Entity_W": "E_W",
            "Entity_B": "E_B",
            "Entity_L": "E_L",
            "Entity_AVG": "E_AVG",
        }
        return mapping.get(vendor_name)

    def _print_brief_progress(self, current: int, total: int) -> None:
        """Print brief progress update every 10 matches."""
        elapsed = (datetime.now() - self.stats["start_time"]).total_seconds()
        rate = elapsed / current if current > 0 else 0
        eta = rate * (total - current) if current > 0 else 0

        logger.info(
            f"[进度] {current}/{total} ({100*current/total:.1f}%) | "
            f"成功: {self.stats['successful_matches']} | "
            f"失败: {self.stats['failed_matches']} | "
            f"ETA: {eta/60:.1f} 分钟"
        )

    def _print_detailed_checkpoint(self, current: int, total: int) -> None:
        """Print detailed checkpoint report every 100 matches (sanitized E_X format)."""
        elapsed = (datetime.now() - self.stats["start_time"]).total_seconds()
        rate = elapsed / current if current > 0 else 0
        eta = rate * (total - current) if current > 0 else 0
        success_rate = 100 * self.stats['successful_matches'] / current if current > 0 else 0

        logger.info("\n" + "=" * 80)
        logger.info(f"阶段对账单 - 已完成 {current}/{total} 场")
        logger.info("=" * 80)
        logger.info(f"总体进度: {100*current/total:.1f}% | 成功率: {success_rate:.1f}% | ETA: {eta/60:.1f} 分钟")
        logger.info(f"已同步: {self.stats['successful_matches']} | 失败: {self.stats['failed_matches']}")
        logger.info("-" * 80)
        logger.info("各 Entity 成功入库计数:")
        # V110.2: Strict E_X format without numeric values in entity names
        logger.info(f"  [E_P]  ✅ Count: {self.stats['vendor_counts']['E_P']}")
        logger.info(f"  [E_W]  ✅ Count: {self.stats['vendor_counts']['E_W']}")
        logger.info(f"  [E_B]  ✅ Count: {self.stats['vendor_counts']['E_B']}")
        logger.info(f"  [E_L]  ✅ Count: {self.stats['vendor_counts']['E_L']}")
        logger.info(f"  [E_AVG] ✅ Count: {self.stats['vendor_counts']['E_AVG']}")
        logger.info(f"  总数据条数: {self.stats['total_vendor_data']}")
        logger.info(f"平均每场提供商数: {self.stats['total_vendor_data']/max(self.stats['successful_matches'],1):.1f}")
        logger.info("-" * 80)
        logger.info(f"网络重试次数: {self.stats['network_retries']} | 熔断触发: {self.stats['circuit_breaker_trips']}")
        logger.info("=" * 80 + "\n")

    async def run_harvest(
        self,
        matches: list[tuple[str, str, datetime]],
        resume: bool = False
    ) -> dict[str, Any]:
        """Run multi-vendor harvest with controlled parallelism.

        Args:
            matches: List of (match_id, url, match_date) tuples
            resume: Whether to resume from checkpoint

        Returns:
            Summary statistics
        """
        self.stats["total_matches"] = len(matches)
        self.stats["start_time"] = datetime.now()

        # Load checkpoint
        processed = self.load_checkpoint() if resume else set()
        pending = [m for m in matches if m[0] not in processed]

        logger.info(
            f"Starting V100.0 harvest: {len(pending)} pending matches, "
            f"{len(processed)} already processed"
        )

        # Process sequentially with network resilience
        for i, (match_id, url, match_date) in enumerate(pending, 1):
            try:
                result = await self.extract_single_match(match_id, url, match_date)

                if result["success"]:
                    self.stats["successful_matches"] += 1
                    self.stats["total_vendor_data"] += result["vendors_extracted"]
                else:
                    self.stats["failed_matches"] += 1

                # Save checkpoint
                self.save_checkpoint(match_id)

                # Phase 1: Enhanced Progress Reporting
                # - 每 100 场输出详细阶段性对账单
                # - 每 10 场输出简略进度
                if i % 100 == 0:
                    self._print_detailed_checkpoint(i, len(pending))
                elif i % 10 == 0:
                    self._print_brief_progress(i, len(pending))

            except Exception as e:
                logger.error(f"Error processing {match_id}: {e}")
                self.stats["failed_matches"] += 1

        self.stats["end_time"] = datetime.now()
        # V117.1: Defensive programming - ensure non-negative duration
        duration_seconds = (
            self.stats["end_time"] - self.stats["start_time"]
        ).total_seconds()
        self.stats["duration"] = max(0, duration_seconds)

        return self.stats


# ============================================================================
# V100.0 Entry Point
# ============================================================================

def print_summary_report(stats: dict[str, Any]):
    """V117.1: Print formatted summary report (sanitized E_X format)."""
    logger.info("\n" + "=" * 80)
    logger.info("Phase 1 定向同步收割 - 最终效能报告 (V117.1 Hybrid Engine)")
    logger.info("=" * 80)

    logger.info(f"\n总场次: {stats['total_matches']}")
    logger.info(f"成功场次: {stats['successful_matches']}")
    logger.info(f"失败场次: {stats['failed_matches']}")
    logger.info(f"成功率: {100*stats['successful_matches']/max(stats['total_matches'],1):.2f}%")
    logger.info(f"耗时: {stats['duration']/60:.1f} 分钟")
    logger.info(f"速率: {stats['total_matches']/max(stats['duration'],1):.2f} 场/分钟")

    logger.info("\n" + "-" * 80)
    logger.info("各 Entity 成功入库统计:")
    logger.info("-" * 80)
    # V110.2: Strict E_X format with ✅ symbols
    entity_labels = {
        "E_P": "E_P",
        "E_W": "E_W",
        "E_B": "E_B",
        "E_L": "E_L",
        "E_AVG": "E_AVG",
    }
    for key, label in entity_labels.items():
        count = stats['vendor_counts'].get(key, 0)
        logger.info(f"  [{label}] ✅ Count: {count:4}")
    logger.info("-" * 80)
    logger.info(f"  总计: {stats['total_vendor_data']:4} 条")
    logger.info(f"  平均每场: {stats['total_vendor_data']/max(stats['successful_matches'],1):.1f} 条")

    logger.info("\n" + "-" * 80)
    logger.info(f"网络重试次数: {stats['network_retries']}")
    logger.info(f"熔断触发次数: {stats['circuit_breaker_trips']}")

    logger.info("\n" + "=" * 80)


def export_stats_to_json(stats: dict[str, Any], output_file: str = "harvest_stats.json") -> str:
    """导出统计信息为 JSON 文件.

    Args:
        stats: 统计信息字典
        output_file: 输出文件名

    Returns:
        导出的文件路径
    """
    # 准备导出数据
    export_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_matches": stats["total_matches"],
            "successful_matches": stats["successful_matches"],
            "failed_matches": stats["failed_matches"],
            "success_rate": f"{100*stats['successful_matches']/max(stats['total_matches'],1):.2f}%",
            "total_vendor_data": stats["total_vendor_data"],
            "avg_vendors_per_match": f"{stats['total_vendor_data']/max(stats['successful_matches'],1):.1f}",
            "duration_minutes": f"{stats['duration']/60:.1f}",
            "rate_per_minute": f"{stats['total_matches']/stats['duration']:.2f}",
        },
        # V110.2: Sanitize provider config output
        "provider_config": {
            str(vendor_id): config["source_name"]
            for vendor_id, config in VENDOR_MAPPING.items()
        },
        "metadata": {
            "version": "V117.1",
            "environment": "production",
            "export_format": "json",
            "engine": "Hybrid Adaptive (Laser + Gravity)"
        }
    }

    # 写入文件
    output_path = Path("logs") / output_file
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ 统计信息已导出到: {output_path}")
    return str(output_path)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="V110.2 Multi-Provider Harvest - Production Grade"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of matches to process (for testing)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4, max: 4)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (verbose output)"
    )
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="Export statistics to JSON file"
    )
    parser.add_argument(
        "--json-file",
        type=str,
        default="harvest_stats.json",
        help="JSON export filename (default: harvest_stats.json)"
    )

    args = parser.parse_args()

    # Configure debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        for handler in logging.getLogger().handlers:
            handler.setLevel(logging.DEBUG)
        logger.info("[V117.1] Debug mode enabled")

    # Cap workers at 4 (network resilience protocol)
    workers = min(args.workers, 4)

    logger.info("=" * 80)
    logger.info("Phase 1 定向同步收割 - Direct Harvest (已有 URL 比赛)")
    logger.info("=" * 80)
    logger.info(f"版本: V117.1 | Workers: {workers} | Limit: {args.limit or 'All'}")
    logger.info(f"目标: 有 oddsportal_url 但无 Entity_P 数据的比赛")
    logger.info(f"Resume: {args.resume} | Debug: {args.debug}")
    logger.info("=" * 80)

    # Get pending matches
    orchestrator = V117HarvestOrchestrator(max_workers=workers)
    matches = orchestrator.get_pending_matches(limit=args.limit)

    if not matches:
        logger.error("No pending matches found!")
        return

    # Run harvest
    stats = await orchestrator.run_harvest(matches, resume=args.resume)

    # Print summary
    print_summary_report(stats)

    # Export to JSON if requested
    if args.export_json:
        export_stats_to_json(stats, args.json_file)


if __name__ == "__main__":
    asyncio.run(main())
