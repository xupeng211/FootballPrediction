#!/usr/bin/env python3
"""V59.0 Performance Benchmark - API vs UI Comparison.

This script benchmarks the performance difference between:
    - V58.0: UI-based extraction (hover + DOM parsing)
    - V59.0: API-based extraction (direct JSON interception)

Metrics:
    - Extraction time per entity
    - Total time for all entities
    - Success rate
    - Memory overhead

Usage:
    python scripts/performance_benchmark_v59.py --url "https://www.oddsportal.com/..."

Output:
    - Performance report (JSON)
    - Comparison chart (if matplotlib available)
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import typer
from playwright.async_api import async_playwright, Browser, Page

# Import V58.0 UI extractor
from src.api.collectors.odds_production_extractor import (
    OddsProductionExtractor,
    TARGET_ENTITIES,
)

# Import V59.0 API interceptor
from src.api.collectors.odds_api_interceptor import (
    OddsAPIInterceptor,
    extract_all_entities_via_api,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/performance_benchmark.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""
    method: str  # "UI" or "API"
    entity_code: str
    success: bool
    time_ms: float
    init_h: float | None
    opening_time_h: datetime | None
    error: str | None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        d = asdict(self)
        d['opening_time_h'] = self.opening_time_h.isoformat() if self.opening_time_h else None
        return d


@dataclass
class PerformanceReport:
    """Summary performance report."""
    url: str
    timestamp: datetime
    ui_results: list[BenchmarkResult]
    api_results: list[BenchmarkResult]
    summary: dict[str, Any]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'url': self.url,
            'timestamp': self.timestamp.isoformat(),
            'ui_results': [r.to_dict() for r in self.ui_results],
            'api_results': [r.to_dict() for r in self.api_results],
            'summary': self.summary
        }


# ============================================================================
# Performance Benchmarker
# ============================================================================

class PerformanceBenchmarker:
    """Benchmarks UI vs API extraction performance."""

    def __init__(self, url: str):
        """Initialize benchmarker.

        Args:
            url: OddsPortal match URL to benchmark
        """
        self.url = url
        self.ui_results: list[BenchmarkResult] = []
        self.api_results: list[BenchmarkResult] = []

    async def benchmark_ui_extraction(
        self,
        page: Page,
        entity_code: str,
        match_date: datetime
    ) -> BenchmarkResult:
        """Benchmark V58.0 UI-based extraction.

        Args:
            page: Playwright page
            entity_code: Target entity code
            match_date: Match date

        Returns:
            BenchmarkResult
        """
        extractor = OddsProductionExtractor()

        start_time = time.time()

        try:
            result = await extractor.extract_opening_via_hover(
                page=page,
                entity_code=entity_code,
                match_date=match_date
            )

            elapsed_ms = (time.time() - start_time) * 1000

            if result and not result.get('hover_failed'):
                return BenchmarkResult(
                    method="UI",
                    entity_code=entity_code,
                    success=True,
                    time_ms=elapsed_ms,
                    init_h=result.get('init_h'),
                    opening_time_h=result.get('opening_time_h'),
                    error=None
                )
            else:
                return BenchmarkResult(
                    method="UI",
                    entity_code=entity_code,
                    success=False,
                    time_ms=elapsed_ms,
                    init_h=None,
                    opening_time_h=None,
                    error=result.get('error', 'Hover failed') if result else 'No result'
                )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return BenchmarkResult(
                method="UI",
                entity_code=entity_code,
                success=False,
                time_ms=elapsed_ms,
                init_h=None,
                opening_time_h=None,
                error=str(e)
            )

    async def benchmark_api_extraction(
        self,
        page: Page,
        entity_code: str,
        match_id: str
    ) -> BenchmarkResult:
        """Benchmark V59.0 API-based extraction.

        Args:
            page: Playwright page
            entity_code: Target entity code
            match_id: Match ID

        Returns:
            BenchmarkResult
        """
        interceptor = OddsAPIInterceptor()

        start_time = time.time()

        try:
            result = await interceptor.extract_via_api(
                page=page,
                entity_code=entity_code,
                match_id=match_id
            )

            elapsed_ms = result.extraction_time_ms

            if result.success:
                return BenchmarkResult(
                    method="API",
                    entity_code=entity_code,
                    success=True,
                    time_ms=elapsed_ms,
                    init_h=result.data.init_h if result.data else None,
                    opening_time_h=result.data.opening_time_h if result.data else None,
                    error=None
                )
            else:
                return BenchmarkResult(
                    method="API",
                    entity_code=entity_code,
                    success=False,
                    time_ms=elapsed_ms,
                    init_h=None,
                    opening_time_h=None,
                    error=result.error
                )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return BenchmarkResult(
                method="API",
                entity_code=entity_code,
                success=False,
                time_ms=elapsed_ms,
                init_h=None,
                opening_time_h=None,
                error=str(e)
            )

    async def run_full_benchmark(
        self,
        match_id: str,
        match_date: datetime
    ) -> PerformanceReport:
        """Run complete benchmark comparing both methods.

        Args:
            match_id: Match ID
            match_date: Match date

        Returns:
            PerformanceReport with all results
        """
        logger.info("="*60)
        logger.info("V59.0 Performance Benchmark")
        logger.info("="*60)
        logger.info(f"URL: {self.url}")
        logger.info(f"Match ID: {match_id}")
        logger.info(f"Match Date: {match_date}")
        logger.info("="*60 + "\n")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )

            # Navigate to match page
            page = await context.new_page()
            logger.info(f"Navigating to: {self.url}")
            await page.goto(self.url, wait_until='networkidle', timeout=60000)
            await page.wait_for_timeout(2000)  # Wait for page to fully load

            # Run UI benchmarks (V58.0)
            logger.info("\n--- V58.0 UI Extraction Benchmark ---")
            for entity_code in TARGET_ENTITIES[:2]:  # Test first 2 entities
                logger.info(f"Testing {entity_code} via UI...")
                result = await self.benchmark_ui_extraction(page, entity_code, match_date)
                self.ui_results.append(result)

                if result.success:
                    logger.info(
                        f"  ✓ UI: {result.time_ms:.2f}ms | "
                        f"init_h={result.init_h} @ {result.opening_time_h}"
                    )
                else:
                    logger.warning(f"  ✗ UI failed: {result.error}")

            await page.wait_for_timeout(1000)  # Brief pause between methods

            # Run API benchmarks (V59.0)
            logger.info("\n--- V59.0 API Extraction Benchmark ---")
            for entity_code in TARGET_ENTITIES[:2]:  # Test first 2 entities
                logger.info(f"Testing {entity_code} via API...")
                result = await self.benchmark_api_extraction(page, entity_code, match_id)
                self.api_results.append(result)

                if result.success:
                    logger.info(
                        f"  ✓ API: {result.time_ms:.2f}ms | "
                        f"init_h={result.init_h} @ {result.opening_time_h}"
                    )
                else:
                    logger.warning(f"  ✗ API failed: {result.error}")

            await browser.close()

        # Generate summary
        summary = self._generate_summary()
        report = PerformanceReport(
            url=self.url,
            timestamp=datetime.now(),
            ui_results=self.ui_results,
            api_results=self.api_results,
            summary=summary
        )

        # Print summary
        self._print_summary(report)

        return report

    def _generate_summary(self) -> dict[str, Any]:
        """Generate performance summary statistics."""
        # UI stats
        ui_times = [r.time_ms for r in self.ui_results if r.success]
        ui_success_rate = sum(1 for r in self.ui_results if r.success) / len(self.ui_results) if self.ui_results else 0
        ui_avg_time = sum(ui_times) / len(ui_times) if ui_times else 0

        # API stats
        api_times = [r.time_ms for r in self.api_results if r.success]
        api_success_rate = sum(1 for r in self.api_results if r.success) / len(self.api_results) if self.api_results else 0
        api_avg_time = sum(api_times) / len(api_times) if api_times else 0

        # Speedup
        speedup = ui_avg_time / api_avg_time if api_avg_time > 0 else 0

        return {
            'ui': {
                'avg_time_ms': ui_avg_time,
                'success_rate': ui_success_rate,
                'total_extractions': len(self.ui_results),
                'successful': sum(1 for r in self.ui_results if r.success)
            },
            'api': {
                'avg_time_ms': api_avg_time,
                'success_rate': api_success_rate,
                'total_extractions': len(self.api_results),
                'successful': sum(1 for r in self.api_results if r.success)
            },
            'comparison': {
                'speedup_ratio': speedup,
                'time_saved_ms': ui_avg_time - api_avg_time,
                'time_saved_pct': ((ui_avg_time - api_avg_time) / ui_avg_time * 100) if ui_avg_time > 0 else 0
            }
        }

    def _print_summary(self, report: PerformanceReport) -> None:
        """Print formatted summary."""
        logger.info("\n" + "="*60)
        logger.info("Performance Summary")
        logger.info("="*60)

        ui = report.summary['ui']
        api = report.summary['api']
        cmp = report.summary['comparison']

        logger.info("\nV58.0 UI Extraction:")
        logger.info(f"  Average time: {ui['avg_time_ms']:.2f}ms")
        logger.info(f"  Success rate: {ui['success_rate']*100:.1f}%")
        logger.info(f"  Successful: {ui['successful']}/{ui['total_extractions']}")

        logger.info("\nV59.0 API Extraction:")
        logger.info(f"  Average time: {api['avg_time_ms']:.2f}ms")
        logger.info(f"  Success rate: {api['success_rate']*100:.1f}%")
        logger.info(f"  Successful: {api['successful']}/{api['total_extractions']}")

        logger.info("\nComparison:")
        logger.info(f"  Speedup: {cmp['speedup_ratio']:.2f}x")
        logger.info(f"  Time saved: {cmp['time_saved_ms']:.2f}ms ({cmp['time_saved_pct']:.1f}%)")

        if cmp['speedup_ratio'] >= 3.0:
            logger.info("\n✅ TARGET ACHIEVED: API is 3x+ faster than UI!")
        elif cmp['speedup_ratio'] >= 2.0:
            logger.info("\n⚠️  CLOSE: API is 2x faster, target is 3x")
        else:
            logger.info("\n❌ BELOW TARGET: API is not fast enough")

        logger.info("="*60 + "\n")


# ============================================================================
# CLI Entry Point
# ============================================================================

def main(
    url: str = typer.Option(..., "--url", "-u", help="OddsPortal match URL"),
    match_id: str = typer.Option("test_match", "--match-id", "-m", help="Match ID"),
    match_date: str = typer.Option("2024-04-20", "--date", "-d", help="Match date (YYYY-MM-DD)"),
    output: str = typer.Option("logs/performance_report.json", "--output", "-o", help="Output report path")
) -> None:
    """Run performance benchmark comparing UI vs API extraction.

    Example:
        python scripts/performance_benchmark_v59.py \\
            --url "https://www.oddsportal.com/soccer/england/premier-league/arsenal-chelsea/" \\
            --match-id "arsenal_chelsea_20240420" \\
            --date "2024-04-20"
    """
    # Parse match date
    try:
        match_date_obj = datetime.strptime(match_date, "%Y-%m-%d")
    except ValueError:
        typer.echo(f"Invalid date format: {match_date}. Use YYYY-MM-DD.")
        raise typer.Exit(1)

    # Run benchmark
    benchmarker = PerformanceBenchmarker(url)
    report = asyncio.run(benchmarker.run_full_benchmark(match_id, match_date_obj))

    # Save report
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

    logger.info(f"Report saved to: {output_path.absolute()}")

    # Verify target
    speedup = report.summary['comparison']['speedup_ratio']
    if speedup < 3.0:
        raise typer.Exit(1)
    else:
        raise typer.Exit(0)


if __name__ == "__main__":
    typer.run(main)
