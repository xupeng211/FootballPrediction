#!/usr/bin/env python3
"""V62.0 Pooled Odds Extractor - Browser Pooling for High-Performance Harvesting.

This module implements browser pooling to eliminate the overhead of starting
a new browser instance for each match. Instead, we launch one browser and harvest
multiple matches before closing it.

Performance Improvement:
    - V58.0 (Single): ~18s per match (15s load + 3s hover)
    - V62.0 (Pooled): ~3s per match (only hover, browser already loaded)
    - Speedup: 6x improvement

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │              V62.0 Browser Pool                       │
    │  ┌──────────────────────────────────────────────────┐  │
    │  │  BrowserContext (Persistent)                   │  │
    │  │    ├─ Page 1 → Extract Match A                  │  │
    │  │    ├─ Page 2 → Extract Match B                  │  │
    │  │    ├─ Page 3 → Extract Match C                  │  │
    │  │    └─ Page N → Extract Match N                  │  │
    │  └──────────────────────────────────────────────────┘  │
    │  Harvest N matches → Close browser → Save results    │
    └─────────────────────────────────────────────────────────┘

Example:
    >>> async with PooledOddsExtractor() as extractor:
    ...     # Browser launched once
    ...     async for match in matches:
    ...         result = await extractor.extract_match(
    ...             page=extractor.get_new_page(),
    ...             match_id=match['match_id']
    ...         )
    ...     # Browser closed automatically on exit
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
import logging
from pathlib import Path
import random
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from src.api.collectors.odds_production_extractor import (
    POLLING_TOOLTIP_ATTEMPTS,
    POLLING_TOOLTIP_DELAY_MS,
    TOOLTIP_OPENING_PATTERN,
)
from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# ============================================================================
# V64.0 Chameleon Protocol - Anti-Detection Configuration
# ============================================================================

# Random Viewport sizes to avoid fingerprinting
VIEWPORT_SIZES = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
    {"width": 1600, "height": 900},
]

# Random User-Agents (Chrome versions)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

# Referer headers to simulate organic traffic
REFERERS = [
    "https://www.google.com/",
    "https://www.oddsportal.com/football/england/premier-league/results/",
    "https://www.oddsportal.com/football/england/premier-league-2024-2025/",
    "https://www.oddsportal.com/",
]


@dataclass
class PooledExtractionResult:
    """Result from pooled extraction session."""
    total_matches: int = 0
    successful: int = 0
    failed: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)
    browser_launch_time: float = 0.0
    total_session_time: float = 0.0


class PooledOddsExtractor:
    """V62.0 Pooled Odds Extractor with browser reuse.

    This extractor maintains a persistent browser instance across multiple
    match extractions, dramatically reducing per-match overhead.

    Usage:
        ```python
        async with PooledOddsExtractor() as extractor:
            # Get pages for parallel extraction
            page1 = extractor.get_new_page()
            page2 = extractor.get_new_page()

            # Extract matches
            result1 = await extractor.extract_match(page1, match_id_1)
            result2 = await extractor.extract_match(page2, match_id_2)

            # Browser automatically closed on exit
        ```
    """

    def __init__(self, headless: bool = False, slow_mo: int = 0, random_delay_range: tuple[int, int] = (15, 45)):
        """Initialize the pooled extractor with V64.0 Chameleon Protocol.

        Args:
            headless: Whether to run browser in headless mode
            slow_mo: Slow down operations by N milliseconds (anti-detection)
            random_delay_range: Random delay range in seconds between requests (V64.0: 15-45s default)
        """
        self.headless = headless
        self.slow_mo = slow_mo
        self.random_delay_range = random_delay_range
        self.settings = get_settings()

        # Browser instances (managed by async context manager)
        self._playwright = None  # V41.67: Store playwright for proper cleanup
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._pages: dict[str, Page] = {}

        # V64.0: Random fingerprint for this session
        self._current_viewport = random.choice(VIEWPORT_SIZES)
        self._current_user_agent = random.choice(USER_AGENTS)

        # V64.0: Semi-persistent pool - track context usage
        self._context_match_count = 0
        self._matches_per_context = 5  # Reset every 5 matches

        # Performance tracking
        self._browser_launched_at: float = 0.0
        self._session_started_at: float = 0.0
        self._stats = {
            "total_pages_created": 0,
            "total_extractions": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "context_resets": 0,  # V64.0: Track context resets
        }

        # Debug output directory
        self._debug_dir = Path("logs/v64_debug")
        self._debug_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_browser_active(self) -> bool:
        """Check if browser is currently active."""
        return self._browser is not None

    async def _launch_browser(self) -> None:
        """Launch a new browser instance."""
        if self._browser is not None:
            logger.warning("[PooledExtractor] Browser already active, skipping launch")
            return

        logger.info("[PooledExtractor] Launching browser...")
        self._browser_launched_at = datetime.now().timestamp()

        # V41.67: Store playwright for proper cleanup
        self._playwright = await async_playwright().start()
        launch_options = {
            "headless": self.headless,
        }
        if self.slow_mo > 0:
            launch_options["slow_mo"] = self.slow_mo
            logger.info(f"[PooledExtractor] Slow_mo enabled: {self.slow_mo}ms")

        self._browser = await self._playwright.chromium.launch(**launch_options)

        # V64.0: Use random fingerprint for each session
        logger.info(f"[PooledExtractor] Fingerprint: viewport={self._current_viewport}, "
                   f"UA=Chrome/{'.'.join(self._current_user_agent.split('Chrome/')[1].split('.')[0:2])}")

        self._context = await self._browser.new_context(
            viewport=self._current_viewport,
            user_agent=self._current_user_agent
        )

        logger.info(f"[PooledExtractor] ✓ Browser launched in {datetime.now().timestamp() - self._browser_launched_at:.2f}s")

    async def _close_browser(self) -> None:
        """Close the browser instance."""
        if self._browser is None:
            return

        logger.info("[PooledExtractor] Closing browser...")

        # V41.67: Stop playwright object to prevent resource leak
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

        await self._browser.close()
        self._browser = None
        self._context = None
        self._pages.clear()
        logger.info("[PooledExtractor] ✓ Browser closed")

    async def _reset_context(self) -> None:
        """V64.0: Reset browser context after N matches to clear cookies and state.

        This is the semi-persistent pool strategy - maintain the browser
        but periodically refresh the context to avoid detection.
        """
        if self._browser is None:
            return

        logger.info(f"[PooledExtractor] Resetting context (after {self._context_match_count} matches)...")
        await self._context.close()

        # Generate new fingerprint
        self._current_viewport = random.choice(VIEWPORT_SIZES)
        self._current_user_agent = random.choice(USER_AGENTS)

        self._context = await self._browser.new_context(
            viewport=self._current_viewport,
            user_agent=self._current_user_agent
        )

        self._context_match_count = 0
        self._stats["context_resets"] += 1

        logger.info("[PooledExtractor] ✓ Context reset with new fingerprint")

    async def _simulate_human_behavior(self, page: Page) -> None:
        """V64.0: Simulate human-like mouse movements to bypass WAF detection.

        Random mouse movements make the browser appear less like a bot.
        """
        try:
            # Random mouse movements
            for _ in range(random.randint(2, 5)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))

            logger.debug("[PooledExtractor] Human-like mouse movements simulated")
        except Exception as e:
            logger.debug(f"[PooledExtractor] Mouse movement failed (non-critical): {e}")

    async def get_new_page(self) -> Page:
        """Create a new page in the active browser context.

        Returns:
            Playwright Page object

        Raises:
            RuntimeError: If browser is not active
        """
        if not self.is_browser_active:
            raise RuntimeError("Browser not active. Use async context manager.")

        page = await self._context.new_page()
        page_id = f"page_{self._stats['total_pages_created']}"
        self._pages[page_id] = page
        self._stats["total_pages_created"] += 1

        logger.debug(f"[PooledExtractor] Created page {page_id}")
        return page

    async def close_page(self, page: Page) -> None:
        """Close a specific page.

        Args:
            page: Playwright Page object to close
        """
        try:
            await page.close()
            # Remove from tracking dict
            for page_id, p in list(self._pages.items()):
                if p == page:
                    del self._pages[page_id]
                    break
            logger.debug("[PooledExtractor] Closed page")
        except Exception as e:
            logger.error(f"[PooledExtractor] Error closing page: {e}")

    async def extract_match(
        self,
        page: Page,
        url: str,
        entity_code: str = "Entity_P",
        match_date: datetime | None = None
    ) -> dict[str, Any] | None:
        """Extract odds data for a single match with V64.0 Chameleon Protocol.

        This method uses the same V58.0 hover extraction logic, with enhanced
        anti-detection measures:
        - Referer spoofing (simulate organic traffic)
        - Human-like mouse movements
        - Context reset every 5 matches
        - Ultra-long random delays (15-45s)

        Args:
            page: Playwright Page object (from get_new_page())
            url: Match URL
            entity_code: Entity code (e.g., "Entity_P")
            match_date: Match date for timestamp construction

        Returns:
            Extraction result dictionary with keys:
                - init_h/d/a: Initial odds
                - opening_time_h/d/a: Timestamps
                - hover_failed: Boolean indicating failure
                - method: "hover"
        """
        self._stats["total_extractions"] += 1
        self._context_match_count += 1

        try:
            logger.info(f"[PooledExtractor] Extracting: {url}")

            # V64.0: Simulate human behavior before navigation
            await self._simulate_human_behavior(page)

            # V64.0: Add random referer to simulate organic traffic
            referer = random.choice(REFERERS)
            logger.debug(f"[PooledExtractor] Referer: {referer}")

            # Navigate to match URL with referer
            start_time = datetime.now().timestamp()
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000,
                referer=referer
            )
            nav_time = datetime.now().timestamp() - start_time

            logger.info(f"[PooledExtractor] Page loaded in {nav_time:.2f}s")

            # Use V58.0 hover extraction (reused logic)
            result = await self._hover_extract(page, entity_code, match_date)

            if result and not result.get("hover_failed"):
                self._stats["successful_extractions"] += 1
            else:
                self._stats["failed_extractions"] += 1

            # V64.0: Ultra-long random delay between requests (15-45 seconds)
            if self.random_delay_range:
                delay = random.uniform(*self.random_delay_range)
                logger.info(f"[PooledExtractor] Chameleon delay: {delay:.1f}s")
                await asyncio.sleep(delay)

            # V64.0: Reset context every 5 matches (semi-persistent pool)
            if self._context_match_count >= self._matches_per_context:
                await self._reset_context()

            return result

        except Exception as e:
            logger.error(f"[PooledExtractor] Extraction error: {e}")
            self._stats["failed_extractions"] += 1

            # V63.0 Visual Debugging: Capture failure state
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_base = self._debug_dir / f"error_{timestamp}"

            try:
                # Save screenshot
                screenshot_path = str(debug_base) + ".png"
                await page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"[PooledExtractor] Screenshot saved: {screenshot_path}")

                # Save HTML content
                html_path = str(debug_base) + ".html"
                html_content = await page.content()
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info(f"[PooledExtractor] HTML saved: {html_path}")

                # Check for Cloudflare / CAPTCHA indicators
                if "challenge-platform" in html_content.lower() or "cf-challenge" in html_content.lower():
                    logger.warning("[PooledExtractor] ⚠️  Cloudflare challenge detected!")
                elif "captcha" in html_content.lower():
                    logger.warning("[PooledExtractor] ⚠️  CAPTCHA detected!")

            except Exception as debug_error:
                logger.error(f"[PooledExtractor] Failed to save debug artifacts: {debug_error}")

            return {
                "hover_failed": True,
                "hover_error": str(e),
                "init_h": None,
                "init_d": None,
                "init_a": None,
                "opening_time_h": None,
                "opening_time_d": None,
                "opening_time_a": None,
                "debug_screenshot": screenshot_path if "screenshot_path" in locals() else None,
                "debug_html": html_path if "html_path" in locals() else None,
            }

    async def _hover_extract(
        self,
        page: Page,
        entity_code: str,
        match_date: datetime | None
    ) -> dict[str, Any] | None:
        """Perform hover extraction (V58.0 logic)."""
        real_name = "Pinnacle"  # Hardcoded for Entity_P

        if match_date is None:
            match_date = datetime.now()
            match_year = match_date.year
        else:
            match_year = match_date.year

        try:
            # Wait for odd-container
            await page.wait_for_selector("div[data-testid='odd-container']", timeout=30000)

            # Find bookmaker container
            all_containers = page.locator("div[data-testid='odd-container']")
            count = await all_containers.count()

            for i in range(min(count, 100)):
                container = all_containers.nth(i)

                try:
                    bookmaker = await container.evaluate("""
                        (elem) => {
                            let parent = elem;
                            for (let i = 0; i < 10; i++) {
                                if (parent && parent.parentElement) {
                                    parent = parent.parentElement;
                                    const nameElem = parent.querySelector(
                                        '[data-testid="outrights-expanded-bookmaker-name"]'
                                    );
                                    if (nameElem) {
                                        return nameElem.textContent;
                                    }
                                }
                            }
                            return null;
                        }
                    """)

                    if bookmaker and real_name.lower() in bookmaker.lower():
                        # Hover and extract
                        await container.hover()
                        await asyncio.sleep(POLLING_TOOLTIP_DELAY_MS / 1000)

                        # Poll for tooltip
                        for _ in range(POLLING_TOOLTIP_ATTEMPTS):
                            tooltip_data = await page.evaluate("""
                                () => {
                                    const allElements = document.querySelectorAll('*');
                                    for (let el of allElements) {
                                        const text = el.textContent || '';
                                        if (text.includes('Opening odds:') &&
                                            text.length < 1000 &&
                                            text.length > 50) {
                                            return { text: text };
                                        }
                                    }
                                    return null;
                                }
                            """)

                            if tooltip_data:
                                return self._parse_tooltip(tooltip_data["text"], match_year)

                            await asyncio.sleep(POLLING_TOOLTIP_DELAY_MS / 1000)

                        return {
                            "hover_failed": True,
                            "hover_error": "No tooltip found"
                        }

                except Exception:
                    continue

            return {
                "hover_failed": True,
                "hover_error": f"Bookmaker {real_name} not found"
            }

        except Exception as e:
            logger.error(f"[PooledExtractor] Hover extraction error: {e}")
            return {
                "hover_failed": True,
                "hover_error": f"Exception: {e!s}"
            }

    def _parse_tooltip(self, tooltip_text: str, match_year: int) -> dict[str, Any]:
        """Parse tooltip text to extract opening odds."""
        match = TOOLTIP_OPENING_PATTERN.search(tooltip_text)

        if not match:
            return {
                "hover_failed": True,
                "hover_error": "Cannot parse tooltip"
            }

        day, month_str, hour, minute, odd_value = match.groups()
        month = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}[month_str]

        if not month:
            return {
                "hover_failed": True,
                "hover_error": f"Invalid month: {month_str}"
            }

        try:
            timestamp = datetime(match_year, month, int(day), int(hour), int(minute))
        except ValueError as e:
            return {
                "hover_failed": True,
                "hover_error": f"Invalid timestamp: {e}"
            }

        return {
            "hover_failed": False,
            "init_h": float(odd_value),
            "init_d": None,
            "init_a": None,
            "opening_time_h": timestamp,
            "opening_time_d": None,
            "opening_time_a": None,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get extraction statistics."""
        return self._stats.copy()

    async def __aenter__(self):
        """Enter async context manager - launch browser."""
        await self._launch_browser()
        self._session_started_at = datetime.now().timestamp()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager - close browser."""
        await self._close_browser()


@asynccontextmanager
async def create_pooled_extractor(headless: bool = False) -> AsyncGenerator[PooledOddsExtractor, None]:
    """Convenience function to create a pooled extractor.

    Example:
        ```python
        async with create_pooled_extractor() as extractor:
            page = extractor.get_new_page()
            result = await extractor.extract_match(page, url, entity_code, match_date)
        ```
    """
    extractor = PooledOddsExtractor(headless=headless)
    await extractor._launch_browser()
    try:
        yield extractor
    finally:
        await extractor._close_browser()


async def extract_batch_pooled(
    matches: list[dict[str, Any]],
    headless: bool = False,
    batch_size: int = 10
) -> PooledExtractionResult:
    """Extract a batch of matches using browser pooling.

    Args:
        matches: List of match dictionaries with 'url' and 'match_date' keys
        headless: Whether to run browser in headless mode
        batch_size: Number of matches to harvest per browser session

    Returns:
        PooledExtractionResult with statistics and all results
    """
    result = PooledExtractionResult()
    result.total_matches = len(matches)

    async with PooledOddsExtractor(headless=headless) as extractor:
        result.browser_launch_time = datetime.now().timestamp() - extractor._browser_launched_at

        for i, match in enumerate(matches):
            try:
                page = await extractor.get_new_page()

                extraction_result = await extractor.extract_match(
                    page=page,
                    url=match["url"],
                    entity_code="Entity_P",
                    match_date=match.get("match_date")
                )

                result.results.append({
                    "match_id": match.get("match_id"),
                    "url": match["url"],
                    "result": extraction_result
                })

                await extractor.close_page(page)

                # Every batch_size matches, take a short break
                if (i + 1) % batch_size == 0:
                    logger.info(f"[PooledExtractor] Processed {i + 1}/{len(matches)} matches, taking a short break...")
                    await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"[PooledExtractor] Error processing match {match.get('match_id')}: {e}")
                result.failed += 1

    result.session_time = datetime.now().timestamp() - result._session_started_at
    result.successful = result.total_matches - result.failed

    logger.info(f"[PooledExtractor] Batch complete: {result.successful}/{result.total_matches} successful")
    logger.info(f"[PooledExtractor] Total time: {result.session_time:.2f}s")
    logger.info(f"[PooledExtractor] Avg per match: {result.session_time / result.total_matches:.2f}s")

    return result
