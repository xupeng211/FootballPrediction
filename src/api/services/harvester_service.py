#!/usr/bin/env python3
"""V144.2 Harvester Service - Production-Grade Data Harvesting Service (Stable Baseline).

This module provides the core harvesting service that integrates all components
from Phase 1 (BaseExtractor V141.0, TeamNameNormalizer V140.0) into a
unified service layer.

Core Features:
    - Queue-driven architecture (match_search_queue)
    - Ghost Protocol integration (BaseExtractor V141.0)
    - Full-path trial matching (TeamNameNormalizer V140.0)
    - Real-time monitoring dashboard
    - Signal handling (SIGINT/SIGTERM)
    - Graceful shutdown mechanism

Example:
    >>> from src.api.services.harvester_service import HarvesterService
    >>> service = HarvesterService(mode="single", dry_run=True)
    >>> await service.run()
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
import random
import signal
from typing import Any

from playwright.async_api import Browser, async_playwright
import psycopg2

from src.collectors.base_extractor import BaseExtractor
from src.collectors.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from src.collectors.collection_sentry import CollectionSentry
from src.collectors.odds_production_extractor import OddsProductionExtractor
from src.config_unified import get_settings
from src.utils.text_processor import TeamNameNormalizer

logger = logging.getLogger(__name__)

# Global running flag for cruise mode
running = True


# ============================================================================
# V142.5: Traffic Resilience Utilities
# ============================================================================

# V144.0: Aggressive Delay Configuration for "Full Attack" Mode
# These settings are designed for maximum stealth during high-volume harvesting
AGGRESSIVE_DELAY_CONFIG = {
    # Normal pagination delays (increased for survival)
    "pagination_min": 120,  # seconds (2 min) - V144.0: Increased for maximum safety
    "pagination_max": 240,  # seconds (4 min)
    # Long rest delays (every N pages)
    "long_rest_interval": 2,  # pages
    "long_rest_min": 300,  # seconds (5 min)
    "long_rest_max": 600,  # seconds (10 min)
    # Burst protection (prevent rapid-fire requests)
    "burst_protection_delay": 20,  # seconds between page navigations (increased)
    # High-risk operation delays (after detection events)
    "after_block_delay": 900,  # seconds (15 min) after IP ban detection
    "after_cloudflare_delay": 600,  # seconds (10 min) after Cloudflare
    # Random "human reading" delays
    "reading_delay_min": 5,  # seconds
    "reading_delay_max": 15,  # seconds
}


def calculate_backoff_delay(retry_count: int, base_delay: int = 60, max_retries: int = 5) -> int:
    """V142.5: Calculate exponential backoff delay for retry attempts.

    Uses exponential backoff with jitter:
    delay = base_delay * (2 ^ min(retry_count - 1, max_retries - 1)) + random_jitter

    Args:
        retry_count: Current retry attempt (1-indexed)
        base_delay: Base delay in seconds (default: 60s)
        max_retries: Maximum number of retries (default: 5)

    Returns:
        Delay in seconds

    Examples:
        >>> calculate_backoff_delay(1)
        60
        >>> calculate_backoff_delay(2)
        120
        >>> calculate_backoff_delay(3)
        240
    """
    # Calculate exponential delay: base_delay * 2^(retry_count-1)
    exponent = min(retry_count - 1, max_retries - 1)
    exponential_delay = base_delay * (2**exponent)

    # Add small jitter (±10%) to avoid thundering herd
    jitter = random.uniform(-0.1, 0.1) * exponential_delay

    return int(exponential_delay + jitter)


def get_aggressive_pagination_delay(page_num: int, config: dict[str, int] | None = None) -> int:
    """V144.0: Calculate aggressive pagination delay for stealth mode.

    Args:
        page_num: Current page number (1-indexed)
        config: Optional delay configuration dict (uses AGGRESSIVE_DELAY_CONFIG if None)

    Returns:
        Delay in seconds

    Examples:
        >>> get_aggressive_pagination_delay(1)
        120
        >>> get_aggressive_pagination_delay(2)  # Long rest after 2 pages
        450
    """
    if config is None:
        config = AGGRESSIVE_DELAY_CONFIG

    # Check if we need a long rest
    if page_num > 1 and page_num % config["long_rest_interval"] == 0:
        # Long rest delay
        delay = random.uniform(config["long_rest_min"], config["long_rest_max"])
        logger.info(f"[V144.0] 🔕 长休息模式: {delay / 60:.1f} 分钟")
        return int(delay)

    # Normal pagination delay
    delay = random.uniform(config["pagination_min"], config["pagination_max"])
    return int(delay)


def get_human_reading_delay(config: dict[str, int] | None = None) -> int:
    """V144.0: Calculate random "human reading" delay.

    Simulates the time a human would spend reading/scanning a page.

    Args:
        config: Optional delay configuration dict (uses AGGRESSIVE_DELAY_CONFIG if None)

    Returns:
        Delay in seconds

    Examples:
        >>> get_human_reading_delay()
        8
    """
    if config is None:
        config = AGGRESSIVE_DELAY_CONFIG

    return random.randint(config["reading_delay_min"], config["reading_delay_max"])


def get_burst_protection_delay(config: dict[str, int] | None = None) -> int:
    """V144.0: Get burst protection delay to prevent rapid-fire requests.

    Args:
        config: Optional delay configuration dict (uses AGGRESSIVE_DELAY_CONFIG if None)

    Returns:
        Delay in seconds

    Examples:
        >>> get_burst_protection_delay()
        15
    """
    if config is None:
        config = AGGRESSIVE_DELAY_CONFIG

    return config["burst_protection_delay"]


# ============================================================================
# V142.9: Context Resilience - Execution Context Self-Healing
# ============================================================================


def is_context_destroyed_error(error: Exception) -> bool:
    """V142.9: Check if an error is an "Execution context was destroyed" error.

    Playwright raises this error when the page navigates or redirects during
    script execution, causing the execution context to be destroyed.

    Args:
        error: The exception to check

    Returns:
        True if this is a context destroyed error, False otherwise

    Examples:
        >>> error = Exception("Execution context was destroyed")
        >>> is_context_destroyed_error(error)
        True
        >>> error = Exception("Network error")
        >>> is_context_destroyed_error(error)
        False
    """
    if not isinstance(error, Exception):
        return False

    error_message = str(error).lower()
    return "execution context was destroyed" in error_message


async def wait_for_page_stable(page) -> None:
    """V142.9: Wait for the page to reach a stable state.

    This replaces the fixed 3-second sleep with a more robust wait strategy
    that ensures the page has finished all network activity.

    Args:
        page: Playwright Page object

    Note:
        This function handles timeout gracefully - if the page doesn't reach
        networkidle within 30 seconds, it logs a warning but continues, allowing
        the harvester to proceed with best-effort extraction.
    """
    try:
        await page.wait_for_load_state("networkidle", timeout=30000)
    except Exception as e:
        logger.warning(f"[V142.9] ⚠️ 页面稳定等待超时或失败: {e}，继续执行最佳努力提取")


async def evaluate_with_retry(page: Any, script: str, max_retries: int = 3) -> Any:
    """V142.9: Evaluate JavaScript on page with automatic retry on context destruction.

    This function wraps page.evaluate with automatic retry logic specifically
    for handling "Execution context was destroyed" errors that occur when
    pages navigate or redirect during script execution.

    Args:
        page: Playwright Page object
        script: JavaScript script to evaluate
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        The result of the script evaluation

    Raises:
        Exception: If all retry attempts fail

    Examples:
        >>> result = await evaluate_with_retry(page, "() => { return [...]; }")
        >>> print(result)
        [{"match_id": "123", ...}]
    """
    retry_count = 0
    last_error = None

    while retry_count < max_retries:
        try:
            # Try to evaluate the script
            return await page.evaluate(script)

        except Exception as e:
            last_error = e

            # Check if this is a context destroyed error
            if is_context_destroyed_error(e):
                retry_count += 1

                if retry_count < max_retries:
                    logger.warning(
                        f"[V142.9] ⚠️ 执行上下文已销毁 (尝试 {retry_count}/{max_retries})，"
                        f"等待页面稳定后重试..."
                    )

                    # Wait for page to stabilize before retry
                    await wait_for_page_stable(page)

                    # Retry the evaluation
                    continue
                logger.exception(f"[V142.9] ❌ 所有 {max_retries} 次重试均失败，放弃执行上下文恢复")
            else:
                # Not a context destroyed error, raise immediately
                raise

    # All retries exhausted, raise the last error
    raise last_error


# ============================================================================
# V142.6: Proxy Pool Management for IP Self-Healing
# ============================================================================


class ProxyPool:
    """V142.6: Proxy Pool Manager for automatic IP rotation on failure.

    This class manages a pool of proxy servers with automatic rotation when
    the current proxy fails (e.g., IP ban, connection errors).

    Features:
        - Auto-rotate after 3 consecutive failures
        - Skip DIRTY proxies when selecting current
        - Track statistics per proxy
        - Support pool reset for next run
        - Resume from failed page after proxy switch

    Example:
        >>> proxies = ["http://proxy1.example.com:7890", "http://proxy2.example.com:7890"]
        >>> pool = ProxyPool(proxies)
        >>> pool.get_current()
        'http://proxy1.example.com:7890'
        >>> # After 3 failures, automatically rotates to proxy2
    """

    def __init__(self, proxies: list[str]) -> None:
        """Initialize the proxy pool.

        Args:
            proxies: List of proxy URLs (e.g., ["http://proxy1.com:7890", ...])
        """
        self._proxies: list[dict[str, Any]] = []
        for proxy_url in proxies:
            self._proxies.append(
                {
                    "url": proxy_url,
                    "status": "ACTIVE",  # ACTIVE or DIRTY
                    "failure_count": 0,
                    "success_count": 0,
                }
            )
        self._current_index: int = 0

    @property
    def proxies(self) -> list[dict[str, Any]]:
        """Get the list of proxy dictionaries."""
        return self._proxies

    @property
    def current_index(self) -> int:
        """Get the current proxy index."""
        return self._current_index

    def get_current(self) -> str | None:
        """Get the current active proxy URL.

        Skips DIRTY proxies and returns the next ACTIVE one.
        Returns None if all proxies are DIRTY (pool exhausted).

        Returns:
            Current active proxy URL or None if pool is exhausted
        """
        # Start from current index and find the first ACTIVE proxy
        for i in range(self._current_index, len(self._proxies)):
            if self._proxies[i]["status"] == "ACTIVE":
                self._current_index = i
                return self._proxies[i]["url"]

        # If no ACTIVE proxy found from current_index, check from beginning
        for i in range(len(self._proxies)):
            if self._proxies[i]["status"] == "ACTIVE":
                self._current_index = i
                return self._proxies[i]["url"]

        # All proxies are DIRTY
        return None

    def mark_current_dirty(self) -> None:
        """Mark the current proxy as DIRTY and advance to next proxy.

        This is used when a proxy has permanently failed (e.g., IP banned).
        """
        if self._current_index < len(self._proxies):
            self._proxies[self._current_index]["status"] = "DIRTY"
            # Advance to next proxy
            self._current_index += 1

    def record_failure(self) -> None:
        """Record a failure for the current proxy.

        After 3 consecutive failures, the proxy is marked as DIRTY
        and the system rotates to the next proxy, automatically skipping
        any proxies that are already DIRTY.
        """
        if self._current_index < len(self._proxies):
            self._proxies[self._current_index]["failure_count"] += 1
            failure_count = self._proxies[self._current_index]["failure_count"]

            # Auto-rotate after 3 failures
            if failure_count >= 3:
                self.mark_current_dirty()
                # After marking dirty, find the next ACTIVE proxy
                self.get_current()  # This updates current_index to skip DIRTY proxies

    def record_success(self) -> None:
        """Record a successful request for the current proxy.

        This can be used for statistics tracking and potentially
        for resetting failure counts in the future.
        """
        if self._current_index < len(self._proxies):
            self._proxies[self._current_index]["success_count"] += 1

    def is_exhausted(self) -> bool:
        """Check if all proxies in the pool are DIRTY.

        Returns:
            True if all proxies are DIRTY, False otherwise
        """
        return all(proxy["status"] == "DIRTY" for proxy in self._proxies)

    def reset(self) -> None:
        """Reset all proxies to ACTIVE status for the next run.

        This allows the system to retry with the same proxies after
        a cooldown period (e.g., after 6-24 hours for IP bans to expire).
        """
        for proxy in self._proxies:
            proxy["status"] = "ACTIVE"
            proxy["failure_count"] = 0
        self._current_index = 0

    def get_proxy_stats(self, proxy_url: str) -> dict[str, int]:
        """Get statistics for a specific proxy.

        Args:
            proxy_url: The proxy URL to get stats for

        Returns:
            Dictionary with success_count and failure_count

        Raises:
            ValueError: If proxy_url is not found in the pool
        """
        for proxy in self._proxies:
            if proxy["url"] == proxy_url:
                return {
                    "success_count": proxy["success_count"],
                    "failure_count": proxy["failure_count"],
                }
        raise ValueError(f"Proxy {proxy_url} not found in pool")

    def get_current_failure_count(self) -> int:
        """Get the failure count for the current proxy.

        This is used to verify that the failure count resets
        when switching to a new proxy.

        Returns:
            Current proxy's failure count
        """
        if self._current_index < len(self._proxies):
            return self._proxies[self._current_index]["failure_count"]
        return 0


class ProxyLoader:
    """V142.7: Proxy Loader for loading proxy IPs from external files.

    This class provides the "ammunition depot" functionality, loading
    proxy configurations from external files with robust validation
    and cleaning.

    Features:
        - Load proxies from text files (one per line)
        - Strip whitespace and skip empty lines
        - Validate proxy URL format (scheme://host:port)
        - Graceful fallback when file is missing (enables WSL2 auto-detection)
        - Support http, https, and socks5 schemes

    Example:
        >>> loader = ProxyLoader(Path("proxies.txt"))
        >>> proxies = loader.load()
        >>> pool = ProxyPool(proxies)
    """

    # Valid proxy schemes
    VALID_SCHEMES = {"http", "https", "socks5"}

    def __init__(self, file_path: Path) -> None:
        """Initialize the proxy loader.

        Args:
            file_path: Path to the proxy configuration file
        """
        self.file_path = file_path

    def load(self) -> list[str]:
        """Load and validate proxies from the configuration file.

        Performs the following operations:
        1. Check if file exists
        2. Read file content
        3. Strip whitespace from each line
        4. Skip empty lines
        5. Validate proxy URL format

        Returns:
            List of valid proxy URLs. Empty list if file doesn't exist
            or contains no valid proxies.
        """
        # Check if file exists
        if not self.file_path.exists():
            logger.warning(f"[V142.7] ⚠️ 代理文件未找到: {self.file_path}，将使用 WSL2 自动探测模式")
            return []

        # Read file content
        try:
            content = self.file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.exception(f"[V142.7] ❌ 读取代理文件失败: {e}")
            return []

        # Parse and validate proxies
        proxies = []
        for line in content.splitlines():
            # Strip whitespace
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Validate proxy URL format
            if self._is_valid_proxy_url(line):
                proxies.append(line)
            else:
                logger.debug(f"[V142.7] ⚠️ 跳过无效代理: {line}")

        if proxies:
            logger.info(f"[V142.7] ✅ 成功加载 {len(proxies)} 个代理")
        else:
            logger.warning("[V142.7] ⚠️ 代理文件中未找到有效代理，将使用 WSL2 自动探测模式")

        return proxies

    def _is_valid_proxy_url(self, url: str) -> bool:
        """Validate proxy URL format.

        Valid format: scheme://host:port
        - scheme must be http, https, or socks5
        - host must be present
        - port must be present and numeric

        Args:
            url: Proxy URL to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            # Basic format check: must contain :// and : for port
            if "://" not in url:
                return False

            # Split scheme and rest
            parts = url.split("://", 1)
            if len(parts) != 2:
                return False

            scheme, rest = parts

            # Validate scheme
            if scheme.lower() not in self.VALID_SCHEMES:
                return False

            # Check if host and port are present
            # Format after scheme:// should be host:port
            if ":" not in rest:
                return False

            # Split host and port
            host_part = rest.rsplit(":", 1)
            if len(host_part) != 2:
                return False

            host, port = host_part

            # Host must not be empty
            if not host:
                return False

            # Port must be numeric
            if not port.isdigit():
                return False

            # Port must be in valid range (1-65535)
            port_num = int(port)
            return 1 <= port_num <= 65535

        except Exception:
            # Any parsing error means invalid format
            return False


# ============================================================================
# Signal Handling
# ============================================================================


def signal_handler(signum: int, frame) -> None:
    """Signal handler for graceful shutdown.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    global running
    logger.info("🛑 收到关闭信号，正在优雅关闭...")
    logger.info("⏳ 完成当前任务后退出...")
    running = False


# ============================================================================
# Queue Manager (from V140.0)
# ============================================================================


class QueueManager:
    """V142.0: Queue Manager for match_search_queue operations.

    Manages database connections and provides async methods for queue operations.
    """

    def __init__(self, settings) -> None:
        """Initialize the queue manager.

        Args:
            settings: Application settings from config_unified
        """
        self.settings = settings
        self._conn_pool: list = []
        self._pool_lock = asyncio.Lock()

    async def get_connection(self) -> psycopg2.extensions.connection:
        """Get a database connection from the pool.

        Returns:
            psycopg2 connection
        """
        async with self._pool_lock:
            if self._conn_pool:
                conn = self._conn_pool.pop()
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                    cur.close()
                    return conn
                except Exception:
                    pass

        return psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
        )

    async def release_connection(self, conn: psycopg2.extensions.connection) -> None:
        """Release a connection back to the pool.

        Args:
            conn: Database connection to release
        """
        async with self._pool_lock:
            if len(self._conn_pool) < 5:
                self._conn_pool.append(conn)
            else:
                conn.close()

    async def get_pending_matches(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get pending matches from the queue.

        Args:
            limit: Maximum number of matches to retrieve

        Returns:
            List of match dictionaries
        """
        conn = await self.get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT m.match_id, m.home_team, m.away_team, m.match_date, m.league_name, m.season
            FROM match_search_queue q
            JOIN matches m ON q.match_id = m.match_id
            WHERE q.status = 'PENDING'
            ORDER BY q.updated_at ASC
            LIMIT %s
        """,
            (limit,),
        )

        rows = cur.fetchall()
        cur.close()
        await self.release_connection(conn)

        return [
            {
                "match_id": row[0],
                "home_team": row[1],
                "away_team": row[2],
                "match_date": row[3],
                "league_name": row[4],
                "season": row[5],
            }
            for row in rows
        ]

    async def update_status(
        self,
        match_id: int,
        status: str,
        url: str | None = None,
        error: str | None = None,
    ) -> None:
        """Update queue status for a match.

        Args:
            match_id: Match ID
            status: New status (SUCCESS/FAILED)
            url: Discovered URL (for SUCCESS)
            error: Error message (for FAILED)
        """
        conn = await self.get_connection()
        cur = conn.cursor()

        if status == "SUCCESS":
            cur.execute(
                """
                UPDATE match_search_queue
                SET status = %s, discovered_url = %s, updated_at = NOW()
                WHERE match_id = %s
            """,
                (status, url, match_id),
            )
        elif status == "FAILED":
            cur.execute(
                """
                UPDATE match_search_queue
                SET status = %s, last_error = %s,
                    retry_count = retry_count + 1, updated_at = NOW()
                WHERE match_id = %s
            """,
                (status, error, match_id),
            )

        conn.commit()
        cur.close()
        await self.release_connection(conn)

    async def get_queue_stats(self) -> dict[str, int]:
        """Get queue statistics.

        Returns:
            Dictionary with pending, success, failed counts
        """
        conn = await self.get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM match_search_queue WHERE status = 'PENDING'")
        pending = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM match_search_queue WHERE status = 'SUCCESS'")
        success = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM match_search_queue WHERE status = 'FAILED'")
        failed = cur.fetchone()[0]

        cur.close()
        await self.release_connection(conn)

        return {"pending": pending, "success": success, "failed": failed}

    async def cleanup(self) -> None:
        """Clean up connection pool."""
        async with self._pool_lock:
            for conn in self._conn_pool:
                with contextlib.suppress(Exception):
                    conn.close()
            self._conn_pool.clear()


# ============================================================================
# Harvester Statistics
# ============================================================================


@dataclass
class HarvesterStats:
    """Statistics for harvester operations."""

    total_discovered: int = 0
    total_matched: int = 0
    total_harvested: int = 0
    total_errors: int = 0
    cloudflare_blocks: int = 0
    ip_bans: int = 0


# ============================================================================
# Main Harvester Service
# ============================================================================


class HarvesterService:
    """V144.0: Production-Grade Data Harvesting Service with Aggressive Stealth.

    This service integrates:
    - BaseExtractor V141.0 (Ghost Protocol + V144.0 Fingerprint Randomization)
    - TeamNameNormalizer V140.0 (Full-path trial matching)
    - QueueManager (Queue-driven architecture)
    - OddsProductionExtractor (V83.0 L1/L2/L3 extraction)
    - V144.0 Aggressive Delay Strategy (for "full attack" mode)

    Attributes:
        settings: Application settings
        mode: Running mode (single/cruise)
        enable_ghost_protocol: Enable Ghost Protocol features
        enable_queue: Enable queue system
        enable_aggressive_delays: Enable V144.0 aggressive delay strategy
        dry_run: Dry run mode (no actual data collection)
        limit: Maximum number of matches to process
    """

    def __init__(
        self,
        mode: str = "single",
        enable_ghost_protocol: bool = True,
        enable_queue: bool = True,
        enable_aggressive_delays: bool = True,
        limit: int | None = None,
        dry_run: bool = False,
        proxy_pool: ProxyPool | None = None,
        proxy_file: str | Path | None = None,
    ) -> None:
        """Initialize the HarvesterService.

        Args:
            mode: Running mode ("single" or "cruise")
            enable_ghost_protocol: Enable Ghost Protocol (BaseExtractor features)
            enable_queue: Enable queue system
            enable_aggressive_delays: Enable V144.0 aggressive delay strategy (default: True)
            limit: Maximum number of matches to process
            dry_run: Dry run mode (no actual collection)
            proxy_pool: Optional ProxyPool for automatic IP rotation on failure
            proxy_file: Optional path to proxy file (V142.7). If provided, loads
                       proxies from file and creates ProxyPool automatically.
                       Default: "proxies.txt" in project root.
        """
        self.settings = get_settings()
        self.mode = mode
        self.enable_ghost_protocol = enable_ghost_protocol
        self.enable_queue = enable_queue
        self.enable_aggressive_delays = enable_aggressive_delays
        self.limit = limit
        self.dry_run = dry_run

        # V142.7: Auto-load proxies from file if provided
        if proxy_pool is None and proxy_file is not None:
            proxy_file_path = Path(proxy_file) if isinstance(proxy_file, str) else proxy_file
            loader = ProxyLoader(proxy_file_path)
            loaded_proxies = loader.load()

            if loaded_proxies:
                proxy_pool = ProxyPool(loaded_proxies)
                logger.info(f"[V142.7] ✅ 代理池已加载 {len(loaded_proxies)} 个代理")
            else:
                logger.info("[V142.7] ℹ️ 代理文件为空或不存在，将使用 WSL2 自动探测模式")
                proxy_pool = ProxyPool([])  # Empty pool for WSL2 auto-detection
        elif proxy_pool is None and proxy_file is None:
            # No proxy pool specified, create empty pool for WSL2 auto-detection
            proxy_pool = ProxyPool([])

        self.proxy_pool = proxy_pool

        # V149.0: 集成 CircuitBreaker 熔断器
        circuit_breaker_config = CircuitBreakerConfig(
            failure_threshold=5,
            cooldown_seconds=600,  # 10 分钟冷却
        )
        self.circuit_breaker = CircuitBreaker("oddsportal_harvester", circuit_breaker_config)
        logger.info("[V149.0] ✅ CircuitBreaker 熔断器已集成（阈值: 5 次，冷却: 600 秒）")

        # V142.9: Context resilience enabled by default
        self.enable_context_resilience = True

        # Initialize components (Phase 1 upgrades)
        self.extractor = OddsProductionExtractor()
        self.normalizer = TeamNameNormalizer()
        self.base_extractor = BaseExtractor(
            enable_ghost_protocol=enable_ghost_protocol,
            auto_proxy=True,
        )

        # Queue manager
        if enable_queue:
            self.queue_manager = QueueManager(self.settings)

        # Statistics
        self.start_time = datetime.now()
        self.stats = HarvesterStats()
        self.last_report_time = datetime.now()

        # V26.5: 自动巡航哨兵（仅在 cruise 模式下启用）
        self.collection_sentry: CollectionSentry | None = None
        if mode == "cruise":
            self.collection_sentry = CollectionSentry(
                window_size=100,
                success_rate_threshold=0.7,
                consecutive_failure_threshold=5,
                pause_duration_hours=12,
            )
            logger.info(
                "[V26.5] 🤖 自动巡航哨兵已启用（窗口: 100, 成功率阈值: 70%, 连续失败阈值: 5）"
            )

    async def stage1_fixtures_scan(
        self,
        browser: Browser,
        league_name: str,
        season_url: str,
        db_league: str,
        db_season: str,
    ) -> list[dict[str, Any]]:
        """V58.0: Fixtures scanning (replaces lost V138.2).

        Args:
            browser: Playwright browser instance
            league_name: Display league name
            season_url: Season URL format
            db_league: Database league name
            db_season: Database season format

        Returns:
            List of discovered match dictionaries
        """
        logger.info(f"[V142.0] Fixtures 扫描: {league_name} {season_url}")

        # Use BaseExtractor to create context with Ghost Protocol (V142.2: returns tuple)
        context, page = await self.base_extractor.create_ghost_context(browser)
        discovered = []

        try:
            # V142.2: Pagination support - scan all result pages
            # Page 1: /results/, Page 2+: /results/page/N/
            base_url = (
                f"https://www.oddsportal.com/football/england/premier-league-{season_url}/results/"
            )
            page_num = 1
            max_pages = 20  # Safety limit (380 matches / ~20 per page = ~20 pages)
            all_matches_processed = set()  # Track processed match URLs to avoid duplicates
            # V143.6 FIX: Initialize db_team_names outside the while loop to ensure
            # it's available for all pages, not just page 1
            db_team_names: set[str] = set()

            while page_num <= max_pages:
                # Build URL for current page
                url = base_url if page_num == 1 else f"{base_url}page/{page_num}/"

                logger.info(f"[V142.2] 扫描第 {page_num} 页: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)

                # Detect blocking using BaseExtractor
                content = await page.content()
                is_blocked, block_reason = self.base_extractor.detect_blocking_method(content)

                if is_blocked:
                    logger.error(f"🔴 拦截检测: {block_reason}")
                    await self.base_extractor.save_error_screenshot(page, block_reason)
                    if "Cloudflare" in block_reason:
                        self.stats.cloudflare_blocks += 1
                    else:
                        self.stats.ip_bans += 1

                    # V143.7: Special handling for "39 bytes" error (IP Hard Ban)
                    # Skip retry and force proxy rotation immediately
                    is_hard_ban = "39 bytes" in block_reason

                    if is_hard_ban:
                        # V149.0: 硬接线 CircuitBreaker 熔断器
                        self.circuit_breaker.record_failure(
                            reason=f"IP Hard Ban: {block_reason}", is_critical=True
                        )

                    if is_hard_ban and self.proxy_pool and not self.proxy_pool.is_exhausted():
                        logger.error(f"[V143.7] ⛔ 检测到 IP 硬封禁 ({block_reason})")
                        logger.warning("[V143.7] 🚨 跳过重试，立即更换代理")
                        # Mark current proxy as failed
                        self.proxy_pool.record_failure()
                        # Force proxy rotation
                        next_proxy = self.proxy_pool.get_current()
                        if next_proxy:
                            logger.warning(
                                f"[V143.7] 🔄 强制代理轮换: 切换到下一个代理: {next_proxy}"
                            )
                            # Update BaseExtractor's proxy configuration
                            self.base_extractor.set_proxy_config(next_proxy)
                            logger.info("[V143.7] ✅ BaseExtractor 代理配置已更新")
                            # Recreate context with new proxy
                            try:
                                await page.close()
                                await context.close()
                            except Exception:
                                pass  # Ignore close errors
                            context, page = await self.base_extractor.create_ghost_context(browser)
                            logger.info("[V143.7] ✅ 新 context 已创建（使用新代理）")
                            logger.info(f"[V143.7] 📄 将从第 {page_num} 页继续任务")
                            continue
                        logger.error("[V143.7] ❌ 代理池已耗尽，无法切换到新代理")

                    # V142.5: Implement exponential backoff retry mechanism
                    # V142.6: Integrate ProxyPool for automatic IP rotation
                    # (Skipped for hard bans, handled above)
                    retry_count = 1
                    max_retries = 3
                    base_delay = 60  # Start with 60 seconds

                    while retry_count <= max_retries and not is_hard_ban:
                        # Calculate backoff delay
                        backoff_delay = calculate_backoff_delay(
                            retry_count, base_delay, max_retries
                        )
                        logger.warning(
                            f"[V142.5] 指数退避重试 #{retry_count}/{max_retries}: "
                            f"等待 {backoff_delay} 秒后重试..."
                        )
                        await asyncio.sleep(backoff_delay)

                        # Retry: reload the page
                        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                        content = await page.content()
                        is_blocked, block_reason = self.base_extractor.detect_blocking_method(
                            content
                        )

                        if not is_blocked:
                            logger.info(f"[V142.5] ✅ 重试 #{retry_count} 成功！继续扫描...")
                            # V142.6: Record success for current proxy
                            if self.proxy_pool:
                                self.proxy_pool.record_success()
                            break
                        logger.warning(f"[V142.5] 重试 #{retry_count} 仍然被拦截: {block_reason}")
                        # V142.6: Record failure for current proxy
                        if self.proxy_pool:
                            self.proxy_pool.record_failure()
                        retry_count += 1

                    # V142.6: If all retries exhausted, try proxy rotation instead of stopping
                    if is_blocked and self.proxy_pool:
                        # Check if we have more proxies available
                        if not self.proxy_pool.is_exhausted():
                            next_proxy = self.proxy_pool.get_current()
                            if next_proxy:
                                logger.warning(
                                    f"[V143.7] 🔄 代理轮换: 切换到下一个代理: {next_proxy}"
                                )
                                # V143.7: Update BaseExtractor's proxy configuration
                                self.base_extractor.set_proxy_config(next_proxy)
                                logger.info("[V143.7] ✅ BaseExtractor 代理配置已更新")
                                # V143.7: Recreate context with new proxy
                                try:
                                    await page.close()
                                    await context.close()
                                except Exception:
                                    pass  # Ignore close errors
                                context, page = await self.base_extractor.create_ghost_context(
                                    browser
                                )
                                logger.info("[V143.7] ✅ 新 context 已创建（使用新代理）")
                                logger.info(
                                    f"[V142.6] 📄 将从第 {page_num} 页继续任务（而非重新开始）"
                                )
                                # Continue to next iteration with same page_num
                                # This implements "resume from failed page" requirement
                                continue
                            logger.error("[V142.6] ❌ 代理池已耗尽，无法切换到新代理")
                        # Fall through to stop pagination if pool is exhausted

                    # If all retries exhausted and no proxy rotation available, stop pagination
                    if is_blocked:
                        logger.error(
                            f"[V142.5] ❌ 所有 {max_retries} 次重试均失败，停止分页。"
                            f"已成功保存第 {page_num - 1} 页之前的 {len(discovered)} 场比赛。"
                        )
                        break

                # Human behavior simulation (Ghost Protocol)
                if self.enable_ghost_protocol:
                    await self.base_extractor.human_scroll(page, max_scrolls=3)
                    await self.base_extractor.human_click_noise(page)

                # V142.9: Wait for page to stabilize before extraction
                await wait_for_page_stable(page)

                # Extract links with deep filtering (V142.4: Regex-based URL filtering)
                # V142.9: Use evaluate_with_retry for automatic context recovery
                matches_data = await self.evaluate_with_retry(
                    page,
                    """
                    () => {
                        const results = [];
                        const links = document.querySelectorAll('a[href]');

                        // V142.4: Build regex pattern for blocked leagues
                        // This ensures blocked keywords are caught at ANY position in URL
                        const blockedLeagues = ['premier-league', 'laliga', 'serie-a', 'bundesliga',
                                                'ligue-1', 'eredivisie', 'champions-league',
                                                'europa-league', 'conference-league'];
                        const blockedPattern = new RegExp('\\\\b(' + blockedLeagues.join('|') + ')\\\\b', 'i');

                        links.forEach(link => {
                            const href = link.getAttribute('href');

                            // Base check: must be /football/ link
                            if (!href || !href.includes('/football/')) {
                                return;
                            }

                            // Exclude fixtures/results directories (already processed)
                            if (href.includes('/fixtures/') || href.includes('/results/')) {
                                return;
                            }

                            // V142.4: Regex-based filtering for non-match pages
                            // 1. Outrights (冠军投注页面)
                            if (/\\boutrights\\b/i.test(href)) {
                                return;
                            }

                            // 2. Standings/Tables (积分榜页面)
                            if (/\\b(standings|table)\\b/i.test(href)) {
                                return;
                            }

                            // 3. Blocked leagues - regex pattern catches at ANY position
                            // This is more comprehensive than checking only the last part
                            const pathParts = href.trim('/').split('/');
                            const lastPart = pathParts[pathParts.length - 1];

                            // If last part is EXACTLY a blocked league (standalone league page)
                            if (blockedLeagues.includes(lastPart)) {
                                return;
                            }

                            // 4. League-only pages without team patterns
                            // Match pages should have: /country/league-season/team1-team2/
                            // League-only pages have: /country/league-season/ or /country/league/
                            const hasTeamPattern = pathParts.some(part =>
                                /-vs-/i.test(part) ||
                                (part.includes('-') &&
                                 !/league/i.test(part) &&
                                 !/20\\d{2}/.test(part) &&
                                 part.split('-').length >= 2)  // At least 2 words with hyphens
                            );

                            // If no team pattern AND path is too short, likely a league page
                            if (!hasTeamPattern && pathParts.length < 5) {
                                return;
                            }

                            results.push({urlPath: href});
                        });
                        return results;
                    }
                """,
                )

                logger.info(f"[V142.2] 第 {page_num} 页发现 {len(matches_data)} 个链接")

                # Parse team names and match IDs
                if self.enable_queue:
                    # Load database team names (once, before loop)
                    # V143.6 FIX: db_team_names is now initialized outside the while loop
                    if page_num == 1:
                        conn = await self.queue_manager.get_connection()
                        cur = conn.cursor()
                        cur.execute(
                            """
                            SELECT DISTINCT home_team FROM matches WHERE league_name = %s AND season = %s
                            UNION
                            SELECT DISTINCT away_team FROM matches WHERE league_name = %s AND season = %s
                        """,
                            (db_league, db_season, db_league, db_season),
                        )
                        db_team_names = {row[0] for row in cur.fetchall()}
                        cur.close()
                        logger.info(f"[V143.6] 已加载 {len(db_team_names)} 个数据库队名")

                    # Parse team names using TeamNameNormalizer V140.0
                    new_matches_this_page = 0
                    for m in matches_data:
                        url_path = m["urlPath"]

                        # Skip already processed matches (deduplication)
                        if url_path in all_matches_processed:
                            continue

                        # V142.2 FIX: Extract team slug from URL path
                        path_parts = url_path.rstrip("/").split("/")
                        teams_part = path_parts[-1] if len(path_parts) > 1 else url_path

                        # Remove hash and query parameters
                        teams_part = teams_part.split("#")[0].split("?")[0]

                        # V142.2 FIX: Strip the URL hash suffix (7-8 char alphanumeric)
                        slug_parts = teams_part.split("-")
                        if len(slug_parts) > 2:
                            last_part = slug_parts[-1]
                            is_hash = False
                            if 7 <= len(last_part) <= 8:
                                has_lower = any(c.islower() for c in last_part)
                                has_upper = any(c.isupper() for c in last_part)
                                has_digit = any(c.isdigit() for c in last_part)

                                common_team_words = {
                                    "fc",
                                    "utd",
                                    "city",
                                    "united",
                                    "academy",
                                    "bilbao",
                                    "real",
                                    "de",
                                    "la",
                                    "al",
                                    "inter",
                                    "ac",
                                    "roma",
                                    "palace",
                                    "bvb",
                                    "rbl",
                                    "ssc",
                                    "afc",
                                    "cfc",
                                }

                                if (
                                    (has_lower and has_upper)
                                    or (has_lower and has_digit)
                                    or (
                                        last_part.islower()
                                        and last_part not in common_team_words
                                        and len(last_part) >= 7
                                    )
                                ):
                                    is_hash = True

                            if is_hash:
                                teams_part = "-".join(slug_parts[:-1])

                        # Use TeamNameNormalizer.parse_team_slug_full_path() method
                        team_slugs = self.normalizer.parse_team_slug_full_path(
                            teams_part, db_team_names, threshold=85.0
                        )

                        if team_slugs:
                            home_team = " ".join(word.title() for word in team_slugs[0].split("-"))
                            away_team = " ".join(word.title() for word in team_slugs[1].split("-"))

                            # Find match_id
                            cur = conn.cursor()
                            cur.execute(
                                """
                                SELECT match_id FROM matches
                                WHERE league_name = %s AND season = %s
                                AND home_team = %s AND away_team = %s
                            """,
                                (db_league, db_season, home_team, away_team),
                            )
                            row = cur.fetchone()
                            cur.close()

                            if row:
                                discovered.append(
                                    {
                                        "match_id": row[0],
                                        "home_team": home_team,
                                        "away_team": away_team,
                                        "url_path": url_path,
                                    }
                                )
                                all_matches_processed.add(url_path)
                                new_matches_this_page += 1

                    logger.info(
                        f"[V142.2] 第 {page_num} 页新增 {new_matches_this_page} 场比赛 | 累计 {len(discovered)} 场"
                    )

                    # Release connection on last page
                    if page_num == max_pages or new_matches_this_page == 0:
                        await self.queue_manager.release_connection(conn)

                # Pagination check: if no new matches found, we've reached the end
                if len(matches_data) == 0:
                    logger.info(f"[V142.2] 第 {page_num} 页无链接，停止分页")
                    break

                # V144.0: Aggressive delay strategy for "full attack" mode
                # Don't sleep after the last page
                if page_num < max_pages:
                    # Use aggressive pagination delay with long rest support
                    delay = get_aggressive_pagination_delay(page_num)

                    # Add burst protection delay before navigation
                    burst_delay = get_burst_protection_delay()
                    total_delay = delay + burst_delay

                    logger.info(
                        f"[V144.0] ⏱️ 激进延迟策略: 分页延迟 {delay / 60:.1f} 分钟 + "
                        f"突发保护 {burst_delay} 秒 = 总计 {total_delay / 60:.1f} 分钟"
                    )
                    await asyncio.sleep(total_delay)

                # Check if we should continue to next page
                page_num += 1

            self.stats.total_discovered += len(discovered)
            logger.info(f"[V144.0] 分页扫描完成，共 {len(discovered)} 场比赛")

        except Exception as e:
            logger.exception(f"[V142.0] Fixtures 扫描失败: {e}")
            self.stats.total_errors += 1
        finally:
            await page.close()
            await context.close()

        return discovered

    async def stage2_harvest_odds(self, matches: list[dict[str, Any]]) -> dict[str, int]:
        """V41.541: Multi-source odds extraction (Quad Engine Integration).

        Args:
            matches: List of match dictionaries to harvest

        Returns:
            Dictionary with processed count and multi-source statistics
        """
        logger.info(f"[V41.541 Quad Engine] 赔率提取: {len(matches)} 场")

        stats = {
            "processed": 0,
            "multi_source_captured": 0,
            "total_sources": 0,
            "errors": 0
        }

        if self.dry_run:
            logger.info("🏃 干跑模式 - 跳过实际采集")
            for m in matches[:5]:
                logger.info(f"  [{m['match_id']}] {m['home_team']} vs {m['away_team']}")
            return {"processed": len(matches), "dry_run": True}

        for match in matches:
            try:
                url = f"https://www.oddsportal.com{match['url_path']}"
                match_id = match["match_id"]

                logger.info(
                    f"[V41.541] Processing: {match_id} - "
                    f"{match['home_team']} vs {match['away_team']}"
                )

                # V41.541: Use new multi-source extraction method
                multi_source_data = await self.extractor.extract_all_entities_final_odds(
                    url=url,
                    match_id=match_id,
                    match_date=match.get("match_date")
                )

                if multi_source_data:
                    # Save all captured sources to database
                    save_stats = self.extractor.save_multi_source_data(multi_source_data)

                    stats["multi_source_captured"] += 1
                    stats["total_sources"] += save_stats.get("valid", 0)

                    logger.info(
                        f"[V41.541] ✅ {match_id}: "
                        f"{save_stats.get('valid', 0)} sources saved "
                        f"({save_stats.get('fully_captured', 0)} fully captured)"
                    )
                    self.stats.total_harvested += 1

                    # V26.5: 记录成功到哨兵
                    if self.collection_sentry:
                        self.collection_sentry.record_result(True)
                else:
                    logger.warning(f"[V41.541] ⚠️ {match_id}: No sources captured")
                    stats["errors"] += 1

                    # V26.5: 记录失败到哨兵
                    if self.collection_sentry:
                        self.collection_sentry.record_result(False)

                stats["processed"] += 1

                # Rate limiting: sleep between matches to avoid IP bans
                await asyncio.sleep(random.uniform(5, 10))

            except Exception as e:
                logger.exception(f"❌ {match.get('match_id', 'unknown')} 处理失败: {e}")
                stats["errors"] += 1
                self.stats.total_errors += 1

                # V26.5: 记录失败到哨兵
                if self.collection_sentry:
                    self.collection_sentry.record_result(False)

        # Log summary statistics
        logger.info("[V41.541 Quad Engine] Summary:")
        logger.info(f"  Processed: {stats['processed']} matches")
        logger.info(f"  Multi-source captured: {stats['multi_source_captured']} matches")
        logger.info(f"  Total sources: {stats['total_sources']} bookmakers")
        logger.info(f"  Errors: {stats['errors']}")

        return stats

    def print_hourly_report(self) -> None:
        """V139.0: Hourly summary report."""
        now = datetime.now()
        elapsed = (now - self.last_report_time).total_seconds() / 3600
        total_elapsed = (now - self.start_time).total_seconds() / 3600

        if elapsed < 1.0:
            return

        logger.info("")
        logger.info("=" * 80)
        logger.info(f"🕰️ [小时报告] 运行时长: {total_elapsed:.1f} 小时")
        logger.info("=" * 80)
        logger.info("📊 [统计]")
        logger.info(f"  发现: {self.stats.total_discovered}")
        logger.info(f"  匹配: {self.stats.total_matched}")
        logger.info(f"  采集: {self.stats.total_harvested}")
        logger.info(f"  错误: {self.stats.total_errors}")
        logger.info(f"  Cloudflare 拦截: {self.stats.cloudflare_blocks}")
        logger.info(f"  IP 封禁: {self.stats.ip_bans}")

        if self.enable_queue:
            # Note: This would need to be async in a real implementation
            logger.info("📊 [队列统计]")
            logger.info("  (队列统计需要异步上下文)")

        logger.info("=" * 80)
        logger.info("")
        self.last_report_time = now

    async def evaluate_with_retry(self, page: Any, script: str, max_retries: int = 3) -> Any:
        """V142.9: Instance method wrapper for evaluate_with_retry.

        This provides access to the context resilience functionality from
        within HarvesterService instances.

        Args:
            page: Playwright Page object
            script: JavaScript script to evaluate
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            The result of the script evaluation

        Raises:
            Exception: If all retry attempts fail
        """
        return await evaluate_with_retry(page, script, max_retries)

    async def run_single(self) -> None:
        """Single execution mode."""
        logger.info("")
        logger.info("=" * 80)
        logger.info("【V142.0 单次执行模式】")
        logger.info("=" * 80)
        logger.info("")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                proxy=self.base_extractor.get_proxy_config(),
            )

            # Fixtures scan
            discovered = await self.stage1_fixtures_scan(
                browser,
                "Premier League",
                "2023-2024",
                "Premier League",
                "23/24",
            )

            if discovered and not self.dry_run:
                # Odds extraction
                await self.stage2_harvest_odds(
                    discovered[: self.limit] if self.limit else discovered
                )

            await browser.close()

        self.print_hourly_report()

    async def run_cruise(self) -> None:
        """24h cruise mode (V139 skeleton)."""
        logger.info("")
        logger.info("=" * 80)
        logger.info("【V142.0 24h 全自动巡航模式】")
        logger.info("=" * 80)
        logger.info("⚙️ 运行配置:")
        logger.info("  - 模式: 24h 巡航")
        logger.info("  - 幽灵协议: " + ("启用" if self.enable_ghost_protocol else "禁用"))
        logger.info("  - 队列系统: " + ("启用" if self.enable_queue else "禁用"))
        logger.info("  - 冷却时间: 5-10 分钟")
        logger.info("")

        cycle_count = 0

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        global running
        while running:
            cycle_count += 1
            logger.info("")
            logger.info("🔄" * 40)
            logger.info(f"🚁 巡航周期 #{cycle_count}")
            logger.info("🔄" * 40)
            logger.info("")

            # V26.5: 哨兵健康检查（在每次循环前）
            if self.collection_sentry:
                try:
                    logger.info("[V26.5] 🔍 哨兵健康检查...")
                    is_healthy = self.collection_sentry.check_health()
                    success_rate = self.collection_sentry.get_success_rate()
                    consecutive_failures = self.collection_sentry.get_consecutive_failures()

                    logger.info(
                        f"[V26.5] 📊 哨兵状态: 成功率={success_rate:.1%}, 连续失败={consecutive_failures}, 健康状态={'✅ 健康' if is_healthy else '❌ 不健康'}"
                    )

                    # 如果不健康，触发停机保护
                    if not is_healthy:
                        logger.warning("[V26.5] ⚠️ 哨兵检测到系统不健康，即将触发停机保护")
                        self.collection_sentry.check_health_or_stop()

                except Exception as e:
                    # 捕获 SecurityInterrupt 异常，优雅退出
                    if "SecurityInterrupt" in type(e).__name__:
                        logger.exception(f"[V26.5] 🛑 哨兵触发停机保护: {e}")
                        logger.exception("[V26.5] 💡 系统已进入冷却期，请等待 12 小时后自动恢复")
                        break
                    logger.exception(f"[V26.5] ❌ 哨兵健康检查异常: {e}")

            try:
                # Stage 1: Single execution
                await self.run_single()

                # Stage 2: Hourly report
                self.print_hourly_report()

                # Stage 3: Cooldown
                if running:
                    cooldown = random.randint(300, 600)
                    logger.info(f"⏱️ 冷却: {cooldown / 60:.1f} 分钟，避免 IP 封禁...")
                    await asyncio.sleep(cooldown)

            except Exception as e:
                logger.exception(f"❌ 周期执行异常: {e}")
                logger.info("⏳ 等待 5 分钟后重试...")
                await asyncio.sleep(300)

        logger.info("")
        logger.info("=" * 80)
        logger.info("🏁 24h 巡航模式已关闭")
        logger.info("=" * 80)

    async def run(self) -> None:
        """Main entry point for the service.

        Routes to the appropriate mode based on initialization.
        """
        if self.mode == "cruise":
            await self.run_cruise()
        else:
            await self.run_single()
