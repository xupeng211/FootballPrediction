#!/usr/bin/env python3
"""V63.0 Pre-flight Audit Script - Production Readiness Gate.

This script implements strict pre-flight testing before allowing production deployment:
1. Single Worker Serial Test - Validates basic extraction functionality
2. Dual Worker Parallel Test - Validates concurrent operation stability
3. Only passes if 100% success rate AND performance targets met

Usage:
    python scripts/v63_preflight_check.py

Exit Codes:
    0 - READY FOR PRODUCTION (all tests passed)
    1 - FAILED (one or more tests failed)
"""

import asyncio
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Test Data - 10 Sample Matches
# ============================================================================

TEST_MATCHES = [
    {
        "match_id": "test-001",
        "url": "https://www.oddsportal.com/football/england/premier-league-2024-2025/chelsea-arsenal-CEnSxfJ0/",
        "home_team": "Chelsea",
        "away_team": "Arsenal",
        "match_date": datetime(2024, 12, 22, 17, 30),
    },
    {
        "match_id": "test-002",
        "url": "https://www.oddsportal.com/football/england/premier-league-2024-2025/liverpool-manchester-city-gB8rQ2Z0/",
        "home_team": "Liverpool",
        "away_team": "Manchester City",
        "match_date": datetime(2024, 12, 22, 17, 0),
    },
    {
        "match_id": "test-003",
        "url": "https://www.oddsportal.com/football/england/premier-league-2024-2025/tottenham-hotspur-newcastle-9sK5xP8/",
        "home_team": "Tottenham",
        "away_team": "Newcastle",
        "match_date": datetime(2024, 12, 21, 15, 0),
    },
    {
        "match_id": "test-004",
        "url": "https://www.oddsportal.com/football/england/premier-league-2024-2025/manchester-united-everton-5mN3qL9/",
        "home_team": "Manchester United",
        "away_team": "Everton",
        "match_date": datetime(2024, 12, 21, 15, 0),
    },
    {
        "match_id": "test-005",
        "url": "https://www.oddsportal.com/football/england/premier-league-2024-2025/leicester-west-ham-2bH7rJ6/",
        "home_team": "Leicester",
        "away_team": "West Ham",
        "match_date": datetime(2024, 12, 20, 20, 0),
    },
    {
        "match_id": "test-006",
        "url": "https://www.oddsportal.com/football/england/premier-league-2024-2025/bournemouth-brighton-wK6nL8d/",
        "home_team": "Bournemouth",
        "away_team": "Brighton",
        "match_date": datetime(2024, 12, 20, 17, 30),
    },
    {
        "match_id": "test-007",
        "url": "https://www.oddsportal.com/football/england/premier-league-2024-2025/wolves-southampton-3fR8mK5/",
        "home_team": "Wolves",
        "away_team": "Southampton",
        "match_date": datetime(2024, 12, 20, 15, 0),
    },
    {
        "match_id": "test-008",
        "url": "https://www.oddsportal.com/football/england/premier-league-2024-2025/crystal-palace-fulham-7hN2jP9/",
        "home_team": "Crystal Palace",
        "away_team": "Fulham",
        "match_date": datetime(2024, 12, 19, 20, 0),
    },
    {
        "match_id": "test-009",
        "url": "https://www.oddsportal.com/football/england/premier-league-2024-2025/aston-villa-brentford-1mK9pQ4/",
        "home_team": "Aston Villa",
        "away_team": "Brentford",
        "match_date": datetime(2024, 12, 19, 17, 30),
    },
    {
        "match_id": "test-010",
        "url": "https://www.oddsportal.com/football/england/premier-league-2024-2025/nottingham-forest-ipswich-8rT5bW7/",
        "home_team": "Nottingham Forest",
        "away_team": "Ipswich",
        "match_date": datetime(2024, 12, 19, 15, 0),
    },
]


# ============================================================================
# Test Result Models
# ============================================================================

@dataclass
class TestResult:
    """Result from a single test phase."""
    phase_name: str
    total_matches: int = 0
    successful: int = 0
    failed: int = 0
    duration_seconds: float = 0.0
    avg_per_match_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
    debug_artifacts: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_matches == 0:
            return 0.0
        return (self.successful / self.total_matches) * 100


# ============================================================================
# Test Functions
# ============================================================================

async def test_single_worker_serial() -> TestResult:
    """Phase 1: Single Worker Serial Test.

    Tests basic extraction functionality with V63.0 anti-bot protections.
    This is the baseline test - must pass 100% to proceed.
    """
    logger.info("=" * 70)
    logger.info("PHASE 1: Single Worker Serial Test")
    logger.info("=" * 70)

    result = TestResult(phase_name="Single Worker Serial")
    result.total_matches = len(TEST_MATCHES)

    from src.api.collectors.odds_pooled_extractor import PooledOddsExtractor

    start_time = time.time()

    try:
        # V64.0 Chameleon Protocol: Enable anti-bot protections
        # Use default ultra-long random delays (15-45s) for stealth
        async with PooledOddsExtractor(
            headless=True,
            slow_mo=100,  # Slow down operations by 100ms
            # random_delay_range uses V64.0 default (15, 45) for ultra-stealth
        ) as extractor:

            for i, match in enumerate(TEST_MATCHES, 1):
                try:
                    logger.info(f"[{i}/{len(TEST_MATCHES)}] Testing: {match['home_team']} vs {match['away_team']}")

                    page = await extractor.get_new_page()

                    extraction_result = await extractor.extract_match(
                        page=page,
                        url=match['url'],
                        entity_code="Entity_P",
                        match_date=match['match_date']
                    )

                    await extractor.close_page(page)

                    if extraction_result and not extraction_result.get('hover_failed'):
                        result.successful += 1
                        logger.info(f"  ✓ Success: init_h={extraction_result.get('init_h')}")
                    else:
                        result.failed += 1
                        error_msg = extraction_result.get('hover_error', 'Unknown error')
                        result.errors.append(f"{match['match_id']}: {error_msg}")
                        logger.error(f"  ✗ Failed: {error_msg}")

                        # Track debug artifacts if available
                        if extraction_result.get('debug_screenshot'):
                            result.debug_artifacts.append(extraction_result['debug_screenshot'])
                        if extraction_result.get('debug_html'):
                            result.debug_artifacts.append(extraction_result['debug_html'])

                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"{match['match_id']}: Exception - {e}")
                    logger.error(f"  ✗ Exception: {e}")

    except Exception as e:
        logger.error(f"Phase 1 fatal error: {e}")
        result.errors.append(f"Fatal error: {e}")

    result.duration_seconds = time.time() - start_time
    result.avg_per_match_seconds = result.duration_seconds / result.total_matches if result.total_matches > 0 else 0

    logger.info("-" * 70)
    logger.info(f"Phase 1 Complete:")
    logger.info(f"  Success Rate: {result.success_rate:.1f}% ({result.successful}/{result.total_matches})")
    logger.info(f"  Duration: {result.duration_seconds:.2f}s")
    logger.info(f"  Avg per match: {result.avg_per_match_seconds:.2f}s")
    if result.errors:
        logger.error(f"  Errors: {len(result.errors)}")
        for err in result.errors[:3]:
            logger.error(f"    - {err}")

    return result


async def test_dual_worker_parallel() -> TestResult:
    """Phase 2: Dual Worker Parallel Test.

    Tests concurrent extraction with two workers running in parallel.
    Validates that the system can handle concurrent operations without conflicts.
    """
    logger.info("=" * 70)
    logger.info("PHASE 2: Dual Worker Parallel Test")
    logger.info("=" * 70)

    result = TestResult(phase_name="Dual Worker Parallel")
    result.total_matches = len(TEST_MATCHES)

    # Split matches into two groups
    mid_point = len(TEST_MATCHES) // 2
    group_a = TEST_MATCHES[:mid_point]
    group_b = TEST_MATCHES[mid_point:]

    logger.info(f"Worker A: {len(group_a)} matches")
    logger.info(f"Worker B: {len(group_b)} matches")

    start_time = time.time()

    async def worker_task(worker_name: str, matches: list[dict]) -> dict:
        """Worker task for parallel execution."""
        from src.api.collectors.odds_pooled_extractor import PooledOddsExtractor

        worker_result = {
            'successful': 0,
            'failed': 0,
            'errors': [],
            'artifacts': []
        }

        try:
            async with PooledOddsExtractor(
                headless=True,
                slow_mo=100,
                # V64.0: Use default (15, 45) for ultra-stealth
            ) as extractor:

                for match in matches:
                    try:
                        page = await extractor.get_new_page()

                        extraction_result = await extractor.extract_match(
                            page=page,
                            url=match['url'],
                            entity_code="Entity_P",
                            match_date=match['match_date']
                        )

                        await extractor.close_page(page)

                        if extraction_result and not extraction_result.get('hover_failed'):
                            worker_result['successful'] += 1
                            logger.info(f"[{worker_name}] ✓ {match['home_team']} vs {match['away_team']}")
                        else:
                            worker_result['failed'] += 1
                            error_msg = extraction_result.get('hover_error', 'Unknown error')
                            worker_result['errors'].append(f"{match['match_id']}: {error_msg}")
                            logger.error(f"[{worker_name}] ✗ {error_msg}")

                            if extraction_result.get('debug_screenshot'):
                                worker_result['artifacts'].append(extraction_result['debug_screenshot'])

                    except Exception as e:
                        worker_result['failed'] += 1
                        worker_result['errors'].append(f"{match['match_id']}: {e}")
                        logger.error(f"[{worker_name}] Exception: {e}")

        except Exception as e:
            logger.error(f"[{worker_name}] Fatal error: {e}")
            worker_result['errors'].append(f"Fatal: {e}")

        return worker_result

    try:
        # Run workers in parallel
        results_a, results_b = await asyncio.gather(
            worker_task("Worker-A", group_a),
            worker_task("Worker-B", group_b)
        )

        # Aggregate results
        result.successful = results_a['successful'] + results_b['successful']
        result.failed = results_a['failed'] + results_b['failed']
        result.errors = results_a['errors'] + results_b['errors']
        result.debug_artifacts = results_a['artifacts'] + results_b['artifacts']

    except Exception as e:
        logger.error(f"Phase 2 fatal error: {e}")
        result.errors.append(f"Fatal error: {e}")

    result.duration_seconds = time.time() - start_time
    result.avg_per_match_seconds = result.duration_seconds / result.total_matches if result.total_matches > 0 else 0

    logger.info("-" * 70)
    logger.info(f"Phase 2 Complete:")
    logger.info(f"  Success Rate: {result.success_rate:.1f}% ({result.successful}/{result.total_matches})")
    logger.info(f"  Duration: {result.duration_seconds:.2f}s")
    logger.info(f"  Avg per match: {result.avg_per_match_seconds:.2f}s")
    logger.info(f"  Parallel Speedup: ~{result.duration_seconds / (result.avg_per_match_seconds * len(TEST_MATCHES)):.1f}x")

    if result.errors:
        logger.error(f"  Errors: {len(result.errors)}")
        for err in result.errors[:3]:
            logger.error(f"    - {err}")

    return result


def print_final_report(phase1: TestResult, phase2: TestResult) -> bool:
    """Print final audit report and determine if ready for production.

    Returns:
        True if READY FOR PRODUCTION, False otherwise
    """
    logger.info("")
    logger.info("=" * 70)
    logger.info("V63.0 PRE-FLIGHT AUDIT REPORT")
    logger.info("=" * 70)

    # Phase 1 Results
    logger.info("")
    logger.info("PHASE 1: Single Worker Serial")
    logger.info("-" * 70)
    logger.info(f"  Status: {'✅ PASS' if phase1.success_rate == 100 else '❌ FAIL'}")
    logger.info(f"  Success Rate: {phase1.success_rate:.1f}%")
    logger.info(f"  Avg per Match: {phase1.avg_per_match_seconds:.2f}s")
    logger.info(f"  Target: < 10s per match")
    logger.info(f"  Performance: {'✅ PASS' if phase1.avg_per_match_seconds < 10 else '❌ FAIL'}")

    # Phase 2 Results
    logger.info("")
    logger.info("PHASE 2: Dual Worker Parallel")
    logger.info("-" * 70)
    logger.info(f"  Status: {'✅ PASS' if phase2.success_rate == 100 else '❌ FAIL'}")
    logger.info(f"  Success Rate: {phase2.success_rate:.1f}%")
    logger.info(f"  Avg per Match: {phase2.avg_per_match_seconds:.2f}s")
    logger.info(f"  Target: < 6s per match (parallel speedup)")
    logger.info(f"  Performance: {'✅ PASS' if phase2.avg_per_match_seconds < 6 else '❌ FAIL'}")

    # Overall Assessment
    phase1_pass = phase1.success_rate == 100 and phase1.avg_per_match_seconds < 10
    phase2_pass = phase2.success_rate == 100 and phase2.avg_per_match_seconds < 6

    logger.info("")
    logger.info("=" * 70)
    logger.info("OVERALL ASSESSMENT")
    logger.info("=" * 70)

    if phase1_pass and phase2_pass:
        logger.info("")
        logger.info("  ████████╗██╗   ██╗███████╗███╗   ██╗████████╗██╗   ██╗")
        logger.info("  ██╔════╝██║   ██║██╔════╝████╗  ██║╚══██╔══╝██║   ██║")
        logger.info("  ███████╗██║   ██║█████╗  ██╔██╗ ██║   ██║   ██║   ██║")
        logger.info("  ╚════██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ██║   ██║")
        logger.info("  ███████║╚██████╔╝███████╗██║ ╚████║   ██║   ╚██████╔╝")
        logger.info("  ╚══════╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ")
        logger.info("")
        logger.info("  ✅ READY FOR PRODUCTION")
        logger.info("")
        logger.info("  V63.0 审计完成。")
        logger.info("  已建立可视化排障防线，Pre-flight 测试通过。")
        logger.info("  现在系统已具备受控生产的能力。")
        logger.info("")
        logger.info("=" * 70)
        return True
    else:
        logger.info("")
        logger.info("  ███████╗ █████╗ ██╗██╗     ███████╗██████╗ ")
        logger.info("  ██╔════╝██╔══██╗██║██║     ██╔════╝██╔══██╗")
        logger.info("  █████╗  ███████║██║██║     █████╗  ██████╔╝")
        logger.info("  ██╔══╝  ██╔══██║██║██║     ██╔══╝  ██╔══██╗")
        logger.info("  ██║     ██║  ██║██║███████╗███████╗██║  ██║")
        logger.info("  ╚═╝     ╚═╝  ╚═╝╚═╝╚══════╝╚══════╝╚═╝  ╚═╝")
        logger.info("")
        logger.info("  ❌ NOT READY FOR PRODUCTION")
        logger.info("")

        if not phase1_pass:
            logger.error("  Phase 1 failed - Basic extraction not working correctly")
        if not phase2_pass:
            logger.error("  Phase 2 failed - Parallel execution not stable")

        if phase1.errors or phase2.errors:
            logger.error("")
            logger.error("  Errors detected:")
            for err in (phase1.errors + phase2.errors)[:5]:
                logger.error(f"    - {err}")

        if phase1.debug_artifacts or phase2.debug_artifacts:
            logger.error("")
            logger.error("  Debug artifacts saved to:")
            for artifact in set(phase1.debug_artifacts + phase2.debug_artifacts):
                logger.error(f"    - {artifact}")

        logger.info("")
        logger.info("  请修复问题后重新测试。")
        logger.info("")
        logger.info("=" * 70)
        return False


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Main pre-flight audit function."""
    logger.info("")
    logger.info("╔═══════════════════════════════════════════════════════════════════════╗")
    logger.info("║                    V63.0 PRE-FLIGHT AUDIT                            ║")
    logger.info("║                 Production Readiness Gate                            ║")
    logger.info("╚═══════════════════════════════════════════════════════════════════════╝")
    logger.info("")

    # Run Phase 1
    phase1_result = await test_single_worker_serial()

    # Only proceed to Phase 2 if Phase 1 passed
    if phase1_result.success_rate < 100:
        logger.error("")
        logger.error("Phase 1 failed - cannot proceed to Phase 2")
        print_final_report(phase1_result, TestResult("Phase 2 (Skipped)"))
        return False

    # Small pause between phases
    await asyncio.sleep(2)

    # Run Phase 2
    phase2_result = await test_dual_worker_parallel()

    # Print final report
    return print_final_report(phase1_result, phase2_result)


if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
