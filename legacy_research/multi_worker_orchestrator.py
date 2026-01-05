#!/usr/bin/env python3
"""V62.0 Multi-Worker Orchestrator - Distributed Queue Management.

This module implements distributed parallel harvesting using Python's multiprocessing
to spawn 5 independent workers, each with its own Playwright instance.

Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │              V62.0 Multi-Worker Orchestrator                    │
    │  ┌───────────────────────────────────────────────────────────┐  │
    │  │  Main Process (Orchestrator)                              │  │
    │  │    ├─ Query DB for matches needing extraction             │  │
    │  │    ├─ Split into 5 chunks                                 │  │
    │  │    ├─ Spawn 5 workers (multiprocessing)                   │  │
    │  │    ├─ Monitor worker health                               │  │
    │  │    ├─ Trigger cluster cooldown if 2+ workers error       │  │
    │  │    └─ Merge results without primary key conflicts         │  │
    │  └───────────────────────────────────────────────────────────┘  │
    │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────┐│
    │  │  Worker 1 │ │  Worker 2 │ │  Worker 3 │ │  Worker 4 │ │Worker5││
    │  │Port:9001  │ │Port:9002  │ │Port:9003  │ │Port:9004  │ │Port:5 ││
    │  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────┘│
    │  ┌───────────────────────────────────────────────────────────┐  │
    │  │  Anti-Ban Dynamic Cooldown                                │  │
    │  │    ├─ Error detection: 2+ workers with errors            │  │
    │  │    ├─ Cluster cooldown: 10-minute silence period         │  │
    │  │    └─ IP protection: Prevents cluster-wide ban           │  │
    │  └───────────────────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────────────────┘

Performance Improvement:
    - V58.0 (Single): ~18s per match (15s load + 3s hover)
    - V62.0 (5 Workers): ~3.6s per match (18s / 5 workers)
    - Speedup: 5x improvement through parallelization

Example:
    >>> from scripts.multi_worker_orchestrator import MultiWorkerOrchestrator
    >>> orchestrator = MultiWorkerOrchestrator(num_workers=5)
    >>> stats = orchestrator.run()
    >>> print(f"Processed: {stats.total_processed} matches")
    >>> print(f"Cooldowns: {stats.cooldowns_triggered}")
"""

from __future__ import annotations

import logging
import multiprocessing as mp
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Anti-Ban Dynamic Cooldown
# ============================================================================

class ClusterState(Enum):
    """Cluster state for anti-ban cooldown mechanism."""
    NORMAL = "normal"          # All workers healthy
    DEGRADED = "degraded"      # 1 worker error
    COOLDOWN = "cooldown"      # 2+ workers error, cluster paused


@dataclass
class CooldownConfig:
    """Configuration for cluster-level cooldown mechanism.

    Attributes:
        error_threshold: Number of worker errors to trigger cooldown (default: 2)
        cooldown_duration_seconds: Duration of cooldown period (default: 600s = 10min)
        health_check_interval_seconds: How often to check worker health (default: 5s)
    """
    error_threshold: int = 2
    cooldown_duration_seconds: int = 600  # 10 minutes
    health_check_interval_seconds: int = 5


class ClusterCooldownManager:
    """Manages cluster-level cooldown for anti-ban protection.

    This class monitors worker health and triggers cluster-wide cooldown
    when too many workers encounter errors.

    Usage:
        manager = ClusterCooldownManager()
        manager.record_error(worker_id=0)
        if manager.should_trigger_cooldown():
            manager.enter_cooldown()
    """

    def __init__(self, config: CooldownConfig | None = None):
        """Initialize cooldown manager.

        Args:
            config: Cooldown configuration (uses defaults if None)
        """
        self.config = config or CooldownConfig()
        self.state = ClusterState.NORMAL

        # Track worker errors
        self.worker_errors: dict[int, int] = {}

        # Cooldown state
        self._cooldown_start_time: float | None = None
        self._cooldown_end_time: float | None = None

    def record_error(self, worker_id: int) -> None:
        """Records an error for a specific worker.

        Args:
            worker_id: Worker that encountered an error
        """
        self.worker_errors[worker_id] = self.worker_errors.get(worker_id, 0) + 1
        logger.warning(
            f"[CooldownManager] Worker {worker_id} error recorded "
            f"(total: {self.worker_errors[worker_id]})"
        )

    def get_error_count(self) -> int:
        """Returns the number of workers with at least one error.

        Returns:
            Count of workers that have encountered errors
        """
        return len(self.worker_errors)

    def should_trigger_cooldown(self) -> bool:
        """Checks if cooldown should be triggered.

        Returns:
            True if error threshold reached
        """
        return self.get_error_count() >= self.config.error_threshold

    def enter_cooldown(self) -> None:
        """Enters cooldown state and waits for cooldown period.

        This method blocks for the duration of the cooldown.
        """
        if self.state == ClusterState.COOLDOWN:
            logger.warning("[CooldownManager] Already in cooldown, skipping")
            return

        self.state = ClusterState.COOLDOWN
        self._cooldown_start_time = time.time()
        self._cooldown_end_time = (
            self._cooldown_start_time + self.config.cooldown_duration_seconds
        )

        logger.warning("=" * 60)
        logger.warning(
            f"[CooldownManager] ⚠️  CLUSTER COOLDOWN TRIGGERED ⚠️"
        )
        logger.warning(
            f"[CooldownManager] {self.get_error_count()} workers encountered errors"
        )
        logger.warning(
            f"[CooldownManager] Entering {self.config.cooldown_duration_seconds}s "
            f"cooldown period to protect IP reputation"
        )
        logger.warning("=" * 60)

        # Wait for cooldown duration
        remaining = self.config.cooldown_duration_seconds
        while remaining > 0:
            mins, secs = divmod(int(remaining), 60)
            logger.info(
                f"[CooldownManager] Cooldown: {mins:02d}:{secs:02d} remaining"
            )
            time.sleep(min(30, remaining))  # Log every 30 seconds
            remaining = self._cooldown_end_time - time.time()

        # Exit cooldown
        self.state = ClusterState.NORMAL
        self.worker_errors.clear()
        self._cooldown_start_time = None
        self._cooldown_end_time = None

        logger.info("=" * 60)
        logger.info("[CooldownManager] ✓ Cooldown complete, resuming operations")
        logger.info("=" * 60)

    def get_status(self) -> dict[str, Any]:
        """Returns current cooldown status.

        Returns:
            Dictionary with cooldown state information
        """
        status = {
            "state": self.state.value,
            "error_count": self.get_error_count(),
            "worker_errors": self.worker_errors.copy(),
        }

        if self.state == ClusterState.COOLDOWN and self._cooldown_end_time:
            remaining = self._cooldown_end_time - time.time()
            mins, secs = divmod(int(remaining), 60)
            status["cooldown_remaining_seconds"] = int(remaining)
            status["cooldown_remaining_formatted"] = f"{mins:02d}:{secs:02d}"

        return status


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class MatchToHarvest:
    """Represents a match that needs odds extraction.

    Attributes:
        match_id: Unique match identifier
        url: Full URL to the match page
        home_team: Home team name
        away_team: Away team name
        match_date: Datetime of the match
    """
    match_id: str
    url: str
    home_team: str
    away_team: str
    match_date: datetime


@dataclass
class WorkerResult:
    """Result from a single worker process.

    Attributes:
        worker_id: Worker identifier (0-4)
        processed: Number of matches processed
        successful: Number of successful extractions
        failed: Number of failed extractions
        results: List of extraction results
        duration_seconds: Time taken by the worker
        has_error: Whether this worker encountered a fatal error
    """
    worker_id: int
    processed: int = 0
    successful: int = 0
    failed: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0.0
    has_error: bool = False


@dataclass
class OrchestratorStats:
    """Aggregated statistics from all workers.

    Attributes:
        total_workers: Number of workers spawned
        total_processed: Total matches processed
        total_successful: Total successful extractions
        total_failed: Total failed extractions
        total_duration_seconds: Total time taken
        avg_per_match_seconds: Average time per match
        cooldowns_triggered: Number of cooldowns triggered
        total_cooldown_time_seconds: Total time spent in cooldown
    """
    total_workers: int = 0
    total_processed: int = 0
    total_successful: int = 0
    total_failed: int = 0
    total_duration_seconds: float = 0.0
    avg_per_match_seconds: float = 0.0
    cooldowns_triggered: int = 0
    total_cooldown_time_seconds: float = 0.0


# ============================================================================
# Worker Process Function
# ============================================================================

def worker_process(
    worker_id: int,
    matches: list[MatchToHarvest],
    proxy_port: int,
    result_queue: mp.Queue
) -> None:
    """Worker process that harvests odds for a chunk of matches.

    Each worker runs independently with its own Playwright instance
    and proxy port to avoid conflicts.

    Args:
        worker_id: Worker identifier (0-4)
        matches: List of matches to harvest
        proxy_port: Proxy port for this worker
        result_queue: Queue to send results back to orchestrator
    """
    import asyncio
    from playwright.async_api import async_playwright

    worker_logger = logging.getLogger(f"Worker-{worker_id}")
    worker_logger.info(f"[Worker-{worker_id}] Starting with {len(matches)} matches on port {proxy_port}")

    result = WorkerResult(worker_id=worker_id)
    start_time = datetime.now()

    try:
        # Import here to avoid issues with multiprocessing
        from src.api.collectors.odds_pooled_extractor import PooledOddsExtractor

        async def harvest_matches():
            """Async harvesting function."""
            async with PooledOddsExtractor(headless=True) as extractor:
                for i, match in enumerate(matches, 1):
                    try:
                        worker_logger.info(
                            f"[Worker-{worker_id}] Processing {i}/{len(matches)}: "
                            f"{match.home_team} vs {match.away_team}"
                        )

                        # Create new page for this match
                        page = await extractor.get_new_page()

                        # Extract odds
                        extraction_result = await extractor.extract_match(
                            page=page,
                            url=match.url,
                            entity_code="Entity_P",
                            match_date=match.match_date
                        )

                        # Close page to free resources
                        await extractor.close_page(page)

                        # Store result
                        result.processed += 1
                        if extraction_result and not extraction_result.get('hover_failed'):
                            result.successful += 1
                            result.results.append({
                                'match_id': match.match_id,
                                'url': match.url,
                                'home_team': match.home_team,
                                'away_team': match.away_team,
                                'init_h': extraction_result.get('init_h'),
                                'init_d': extraction_result.get('init_d'),
                                'init_a': extraction_result.get('init_a'),
                                'opening_time_h': extraction_result.get('opening_time_h'),
                                'opening_time_d': extraction_result.get('opening_time_d'),
                                'opening_time_a': extraction_result.get('opening_time_a'),
                            })
                        else:
                            result.failed += 1
                            worker_logger.warning(
                                f"[Worker-{worker_id}] Failed to extract: {match.url}"
                            )

                    except Exception as e:
                        result.failed += 1
                        worker_logger.error(
                            f"[Worker-{worker_id}] Error processing {match.url}: {e}"
                        )

                    # Small delay between matches to avoid detection
                    if i < len(matches):
                        await asyncio.sleep(1)

        # Run async function
        asyncio.run(harvest_matches())

    except Exception as e:
        worker_logger.error(f"[Worker-{worker_id}] Fatal error: {e}")
        result.failed = len(matches) - result.successful
        result.has_error = True

        # Detect Playwright configuration errors
        error_msg = str(e).lower()
        if 'unexpected keyword argument' in error_msg:
            worker_logger.error(
                f"[Worker-{worker_id}] ⚠️  Playwright 配置错误！"
            )
            worker_logger.error(
                f"[Worker-{worker_id}] 常见原因：user_agent 等参数应传给 new_context() "
                f"而非 launch()"
            )
            worker_logger.error(
                f"[Worker-{worker_id}] 正确做法：browser.launch(headless=True) "
                f"→ context = browser.new_context(user_agent=...)"
            )
        elif 'chromium' in error_msg or 'browser' in error_msg:
            worker_logger.error(
                f"[Worker-{worker_id}] ⚠️  浏览器启动失败！"
            )
            worker_logger.error(
                f"[Worker-{worker_id}] 可能原因：Playwright 未安装或依赖缺失"
            )
            worker_logger.error(
                f"[Worker-{worker_id}] 修复命令：playwright install chromium"
            )

    # Calculate duration
    result.duration_seconds = (datetime.now() - start_time).total_seconds()

    worker_logger.info(
        f"[Worker-{worker_id}] Completed: {result.successful}/{result.processed} successful "
        f"in {result.duration_seconds:.2f}s"
    )

    # Send result to main process
    result_queue.put(result)


# ============================================================================
# Main Orchestrator Class
# ============================================================================

class MultiWorkerOrchestrator:
    """V62.0 Multi-Worker Orchestrator for distributed harvesting.

    This class manages the complete distributed harvesting pipeline:

    1. **Query Phase**: Fetches matches needing extraction from database
    2. **Distribution Phase**: Splits matches into chunks for each worker
    3. **Execution Phase**: Spawns and monitors worker processes
    4. **Merge Phase**: Aggregates results and saves to database

    Typical usage:
        orchestrator = MultiWorkerOrchestrator(num_workers=5)
        results = orchestrator.query_and_distribute()
        orchestrator.spawn_workers(results)
        orchestrator.merge_results()
    """

    def __init__(self, num_workers: int = 5, cooldown_config: CooldownConfig | None = None):
        """Initializes the orchestrator.

        Args:
            num_workers: Number of worker processes to spawn (default: 5)
            cooldown_config: Cooldown configuration (uses defaults if None)
        """
        self.num_workers = num_workers
        self.settings = get_settings()

        # Start proxy ports from 9001
        self.base_proxy_port = 9001

        # Statistics
        self.stats = OrchestratorStats()
        self.worker_results: list[WorkerResult] = []

        # Cooldown manager
        self.cooldown_manager = ClusterCooldownManager(cooldown_config)

    def query_matches_needing_extraction(self) -> list[MatchToHarvest]:
        """Queries database for matches that need odds extraction.

        Returns:
            List of MatchToHarvest objects

        Query Logic:
            SELECT match_id, url FROM matches
            LEFT JOIN metrics_multi_source_data ON match_id
            WHERE opening_time_h IS NULL
        """
        logger.info("[Orchestrator] Querying database for matches needing extraction...")

        conn = psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
            cursor_factory=RealDictCursor
        )

        cursor = conn.cursor()

        # Query matches without Pinnacle opening odds
        cursor.execute("""
            SELECT
                m.match_id,
                m.home_team,
                m.away_team,
                m.match_date,
                m.season,
                m.league_name
            FROM matches m
            LEFT JOIN metrics_multi_source_data msd
                ON m.match_id = msd.match_id
                AND msd.source_name = 'Entity_P'
            WHERE msd.opening_time_h IS NULL
            AND m.league_name IN ('Bundesliga', 'Premier League', 'La Liga', 'Serie A', 'Ligue 1')
            AND m.match_date > '2020-01-01'
            ORDER BY m.match_date DESC
        """)

        matches = []
        for row in cursor.fetchall():
            # Build URL from match data
            season = row['season']  # e.g., "21/22"
            # Convert to URL season format
            url_season = season.replace('/', '-')  # "21-22"
            url_season = f"20{url_season}"  # "2021-22"

            # Build URL (template from production_harvester.py)
            league_slug = self._get_league_slug(row['league_name'])
            url = f"https://www.oddsportal.com/football/{league_slug}/{url_season}/{row['match_id']}/"

            matches.append(MatchToHarvest(
                match_id=row['match_id'],
                url=url,
                home_team=row['home_team'],
                away_team=row['away_team'],
                match_date=row['match_date']
            ))

        cursor.close()
        conn.close()

        logger.info(f"[Orchestrator] Found {len(matches)} matches needing extraction")

        return matches

    def _get_league_slug(self, league_name: str) -> str:
        """Converts league name to URL slug.

        Args:
            league_name: Display name of the league

        Returns:
            URL-safe slug for the league
        """
        mapping = {
            'Bundesliga': 'germany/bundesliga',
            'Premier League': 'england/premier-league',
            'La Liga': 'spain/laliga',
            'Serie A': 'italy/serie-a',
            'Ligue 1': 'france/ligue-1'
        }
        return mapping.get(league_name, 'england/premier-league')

    def distribute_matches(
        self,
        matches: list[MatchToHarvest]
    ) -> list[list[MatchToHarvest]]:
        """Distributes matches across workers.

        Args:
            matches: List of all matches to harvest

        Returns:
            List of match chunks, one per worker
        """
        logger.info(
            f"[Orchestrator] Distributing {len(matches)} matches "
            f"across {self.num_workers} workers"
        )

        # Split matches into chunks
        chunk_size = (len(matches) + self.num_workers - 1) // self.num_workers
        chunks = []

        for i in range(self.num_workers):
            start_idx = i * chunk_size
            end_idx = min(start_idx + chunk_size, len(matches))
            chunk = matches[start_idx:end_idx]
            chunks.append(chunk)
            logger.info(f"[Orchestrator] Worker {i}: {len(chunk)} matches")

        return chunks

    def spawn_workers(
        self,
        match_chunks: list[list[MatchToHarvest]]
    ) -> list[WorkerResult]:
        """Spawns worker processes and waits for completion with cooldown monitoring.

        Args:
            match_chunks: List of match chunks, one per worker

        Returns:
            List of WorkerResult objects from all workers
        """
        logger.info(f"[Orchestrator] Spawning {len(match_chunks)} worker processes...")

        # Create result queue
        result_queue: mp.Queue[WorkerResult] = mp.Queue()

        # Create and start processes
        processes = []
        for worker_id, chunk in enumerate(match_chunks):
            if not chunk:
                logger.info(f"[Orchestrator] Worker {worker_id}: No matches, skipping")
                continue

            proxy_port = self.base_proxy_port + worker_id

            p = mp.Process(
                target=worker_process,
                args=(worker_id, chunk, proxy_port, result_queue)
            )
            processes.append(p)
            p.start()

            logger.info(f"[Orchestrator] Worker {worker_id} started (PID: {p.pid})")

        # Monitor workers and check for errors
        completed_workers = 0
        active_processes = len(processes)

        while completed_workers < active_processes:
            # Check if any process has exited
            for p in processes[:]:  # Copy list to modify during iteration
                if not p.is_alive() and p.exitcode is not None:
                    processes.remove(p)
                    completed_workers += 1
                    logger.info(
                        f"[Orchestrator] Worker completed "
                        f"({completed_workers}/{active_processes} done)"
                    )

            # Collect available results
            while not result_queue.empty():
                result = result_queue.get()
                if result.has_error:
                    self.cooldown_manager.record_error(result.worker_id)

            # Check if cooldown should be triggered
            if self.cooldown_manager.should_trigger_cooldown():
                logger.warning(
                    f"[Orchestrator] {self.cooldown_manager.get_error_count()} workers "
                    f"encountered errors, triggering cluster cooldown"
                )

                # Terminate remaining processes before cooldown
                for p in processes:
                    if p.is_alive():
                        logger.warning(f"[Orchestrator] Terminating worker PID {p.pid}")
                        p.terminate()

                # Enter cooldown
                cooldown_start = time.time()
                self.cooldown_manager.enter_cooldown()
                cooldown_duration = time.time() - cooldown_start

                # Update stats
                self.stats.total_cooldown_time_seconds += cooldown_duration
                self.stats.cooldowns_triggered += 1

                # After cooldown, remaining workers need to be respawned
                # For now, we'll just collect partial results
                break

            # Small sleep to avoid busy waiting
            time.sleep(0.5)

        # Wait for any remaining processes
        for p in processes:
            if p.is_alive():
                p.join(timeout=5)
                if p.is_alive():
                    logger.warning(f"[Orchestrator] Force terminating worker PID {p.pid}")
                    p.terminate()

        logger.info("[Orchestrator] All workers completed")

        # Collect remaining results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        self.worker_results = results
        return results

    def aggregate_results(self) -> OrchestratorStats:
        """Aggregates results from all workers.

        Returns:
            OrchestratorStats with aggregated statistics
        """
        stats = OrchestratorStats()
        stats.total_workers = len(self.worker_results)

        for result in self.worker_results:
            stats.total_processed += result.processed
            stats.total_successful += result.successful
            stats.total_failed += result.failed
            stats.total_duration_seconds = max(
                stats.total_duration_seconds,
                result.duration_seconds
            )

        # Calculate average time per match (amortized across workers)
        if stats.total_processed > 0:
            stats.avg_per_match_seconds = (
                stats.total_duration_seconds / stats.total_processed
            )

        self.stats = stats
        return stats

    def save_results_to_db(self) -> None:
        """Saves extraction results to database.

        Uses INSERT ... ON CONFLICT DO NOTHING to avoid primary key conflicts.
        """
        logger.info("[Orchestrator] Saving results to database...")

        if not self.worker_results:
            logger.warning("[Orchestrator] No results to save")
            return

        conn = psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
        )

        cursor = conn.cursor()

        saved_count = 0
        for result in self.worker_results:
            for extraction in result.results:
                try:
                    cursor.execute("""
                        INSERT INTO metrics_multi_source_data (
                            match_id,
                            source_name,
                            init_h,
                            init_d,
                            init_a,
                            opening_time_h,
                            opening_time_d,
                            opening_time_a,
                            final_h,
                            final_d,
                            final_a,
                            created_at
                        ) VALUES (
                            %s, 'Entity_P', %s, %s, %s, %s, %s, %s, NULL, NULL, NULL, NOW()
                        )
                        ON CONFLICT (match_id, source_name) DO NOTHING
                    """, (
                        extraction['match_id'],
                        extraction['init_h'],
                        extraction['init_d'],
                        extraction['init_a'],
                        extraction['opening_time_h'],
                        extraction['opening_time_d'],
                        extraction['opening_time_a'],
                    ))
                    saved_count += 1

                except Exception as e:
                    logger.error(f"[Orchestrator] Error saving {extraction['match_id']}: {e}")

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"[Orchestrator] Saved {saved_count} results to database")

    def run(self) -> OrchestratorStats:
        """Executes the complete distributed harvesting pipeline.

        Returns:
            OrchestratorStats with aggregated statistics

        Pipeline:
            1. Query matches needing extraction
            2. Distribute across workers
            3. Spawn workers and wait
            4. Aggregate and save results
        """
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("[Orchestrator] V62.0 Multi-Worker Orchestrator Starting")
        logger.info("=" * 60)

        # Phase 1: Query
        matches = self.query_matches_needing_extraction()

        if not matches:
            logger.info("[Orchestrator] No matches need extraction")
            return OrchestratorStats()

        # Phase 2: Distribute
        match_chunks = self.distribute_matches(matches)

        # Phase 3: Spawn workers
        self.spawn_workers(match_chunks)

        # Phase 4: Aggregate
        stats = self.aggregate_results()

        # Phase 5: Save to database
        self.save_results_to_db()

        # Log final statistics
        duration = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info("[Orchestrator] V62.0 Harvest Complete")
        logger.info(f"  Total Workers: {stats.total_workers}")
        logger.info(f"  Total Processed: {stats.total_processed}")
        logger.info(f"  Successful: {stats.total_successful}")
        logger.info(f"  Failed: {stats.total_failed}")
        logger.info(f"  Duration: {stats.total_duration_seconds:.2f}s")
        logger.info(f"  Avg per match: {stats.avg_per_match_seconds:.2f}s")
        logger.info(f"  Total time: {duration:.2f}s")
        if stats.cooldowns_triggered > 0:
            logger.info(f"  Cooldowns triggered: {stats.cooldowns_triggered}")
            logger.info(f"  Total cooldown time: {stats.total_cooldown_time_seconds:.2f}s")
        logger.info("=" * 60)

        return stats


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for the multi-worker orchestrator."""
    orchestrator = MultiWorkerOrchestrator(num_workers=5)
    stats = orchestrator.run()

    # Exit with appropriate code
    sys.exit(0 if stats.total_failed == 0 else 1)


if __name__ == '__main__':
    # Fix for multiprocessing on Windows
    mp.set_start_method('spawn', force=True)

    main()
