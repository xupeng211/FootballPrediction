#!/usr/bin/env python3
"""Production-Grade Odds Data Extraction Engine.

This module provides a robust, self-healing engine for extracting odds data
from betting websites using Playwright browser automation.

Core Features:
    - Multi-source extraction: Pinnacle, William Hill, Ladbrokes, 1xBet, Average Odds
    - Intelligent polling: Uses wait_for_selector instead of hard sleeps
    - Hover self-healing: Auto-scroll + mouse jitter retry mechanism
    - Data integrity validation: Score-based validation (1.02 < Score < 1.08)
    - Temporal alignment: Preserves match_date for accurate timestamp construction

Example:
    >>> extractor = OddsProductionExtractor()
    >>> result = await extractor.extract_opening_via_hover(
    ...     page=page,
    ...     entity_code="Entity_P",
    ...     match_date=datetime(2024, 4, 20)
    ... )
    >>> if result and not result.get('hover_failed'):
    ...     print(f"Opening time: {result.get('opening_time_h')}")
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg2
from playwright.async_api import Page

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Constants
# ============================================================================

# Priority-ordered list of bookmakers to extract data from
TARGET_ENTITIES = [
    "Entity_P",    # Pinnacle (highest priority)
    "Entity_WH",   # William Hill
    "Entity_LB",   # Ladbrokes
    "Entity_B3",   # 1xBet
    "Entity_AVG",  # Average Odds (market consensus)
]

# Maps internal entity codes to display names on the website
ENTITY_NAME_MAPPING = {
    "Entity_P": "Pinnacle",
    "Entity_WH": "William Hill",
    "Entity_LB": "Ladbrokes",
    "Entity_B3": "1xBet",
    "Entity_AVG": "Average Odds",
}

# Integrity score validation thresholds
# Valid odds should satisfy: 1.02 < 1/P1 + 1/P2 + 1/P3 < 1.08
MIN_INTEGRITY_SCORE = 1.02
MAX_INTEGRITY_SCORE = 1.08

# Smart polling configuration
POLLING_MAX_RETRIES = 2
POLLING_TOOLTIP_ATTEMPTS = 10
POLLING_TOOLTIP_DELAY_MS = 500
SELECTOR_TIMEOUT_MS = 60000

# Regex patterns for data extraction
OPENING_ODDS_REGEX = re.compile(r"(?:opening|initial)[:\s]*([\d.]+)", re.IGNORECASE)

# Tooltip parsing: "Opening odds:22 Dec, 08:131.19"
TOOLTIP_MONTH_MAP = {
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
}
TOOLTIP_OPENING_PATTERN = re.compile(
    r'Opening\s+odds:(\d{1,2})\s+([A-Za-z]{3})\s*,\s+(\d{1,2}):(\d{2})(\d+\.\d+)'
)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class MultiSourceEntityData:
    """Represents odds data from a single bookmaker for a specific match.

    Attributes:
        match_id: Unique identifier for the match
        source_name: Internal entity code (e.g., "Entity_P")
        init_h/d/a: Initial (opening) odds for home/draw/away
        opening_time_h/d/a: Timestamps when initial odds were published
        final_h/d/a: Final odds before match start
        integrity_score: Validation score (1/P1 + 1/P2 + 1/P3)
        is_valid: Whether data passes integrity validation
        validation_error: Error message if validation fails
        fully_captured: True if all three dimensions (init, time, final) are present
        data_timestamp: When this record was created
    """
    match_id: str
    source_name: str

    # Initial (opening) odds
    init_h: float | None = None
    init_d: float | None = None
    init_a: float | None = None

    # Initial odds timestamps
    opening_time_h: datetime | None = None
    opening_time_d: datetime | None = None
    opening_time_a: datetime | None = None

    # Final odds
    final_h: float | None = None
    final_d: float | None = None
    final_a: float | None = None

    # Validation metadata
    integrity_score: float | None = None
    is_valid: bool = False
    validation_error: str | None = None
    fully_captured: bool = False
    data_timestamp: datetime | None = None

    def calculate_integrity_score(self) -> float | None:
        """Calculates and validates the integrity score.

        The integrity score is computed as: Score = 1/P1 + 1/P2 + 1/P3
        Valid data must satisfy: 1.02 < Score < 1.08

        Special case: Data with only init_h + opening_time_h is marked
        as valid (hover capture scenario) but not fully captured.

        Returns:
            The integrity score if final odds are present, None otherwise.
        """
        # Check for initial timestamp only (hover capture scenario)
        has_init = self.init_h is not None
        has_time = any([self.opening_time_h, self.opening_time_d, self.opening_time_a])

        if has_init and has_time:
            self.is_valid = True
            self.validation_error = None
            self.fully_captured = False
            return None

        # Full validation requires all final odds
        if not all([self.final_h, self.final_d, self.final_a]):
            return None

        try:
            self.integrity_score = (
                1.0 / self.final_h +
                1.0 / self.final_d +
                1.0 / self.final_a
            )

            if MIN_INTEGRITY_SCORE < self.integrity_score < MAX_INTEGRITY_SCORE:
                self.is_valid = True
                self.validation_error = None
            else:
                self.is_valid = False
                self.validation_error = (
                    f"Integrity score {self.integrity_score:.4f} "
                    f"outside valid range [{MIN_INTEGRITY_SCORE}, {MAX_INTEGRITY_SCORE}]"
                )

            # Check full capture status
            has_final = all([self.final_h, self.final_d, self.final_a])
            has_initial = all([self.init_h, self.init_d, self.init_a])
            self.fully_captured = has_final and has_initial and has_time

            return self.integrity_score

        except ZeroDivisionError:
            self.is_valid = False
            self.validation_error = "Division by zero in integrity calculation"
            return None

    def to_dict(self) -> dict[str, Any]:
        """Converts the dataclass to a dictionary.

        Returns:
            Dictionary representation of all fields.
        """
        return {
            "match_id": self.match_id,
            "source_name": self.source_name,
            "init_h": self.init_h,
            "init_d": self.init_d,
            "init_a": self.init_a,
            "final_h": self.final_h,
            "final_d": self.final_d,
            "final_a": self.final_a,
            "integrity_score": self.integrity_score,
            "is_valid": self.is_valid,
            "validation_error": self.validation_error,
            "fully_captured": self.fully_captured,
            "opening_time_h": self.opening_time_h,
            "opening_time_d": self.opening_time_d,
            "opening_time_a": self.opening_time_a,
            "data_timestamp": self.data_timestamp,
        }


# ============================================================================
# Main Extraction Engine
# ============================================================================

class OddsProductionExtractor:
    """Production-grade odds data extraction engine.

    This engine provides intelligent, self-healing extraction of odds data
    from betting websites using browser automation. Key features:

    - Smart polling: Uses DOM-ready detection instead of hard sleeps
    - Hover self-healing: Auto-scroll + mouse jitter for tooltip capture
    - Temporal alignment: Preserves match_date context for accuracy
    - Data validation: Integrity score checking

    Typical usage:
        extractor = OddsProductionExtractor()
        result = await extractor.extract_opening_via_hover(
            page=page,
            entity_code="Entity_P",
            match_date=match_date
        )
    """

    def __init__(self):
        """Initializes the extractor with configuration settings."""
        self.settings = get_settings()
        self._stats = {
            "total_entities_processed": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "integrity_failures": 0,
        }

    # ========================================================================
    # Core Extraction Methods
    # ========================================================================

    async def extract_opening_via_hover(
        self,
        page: Page,
        entity_code: str,
        match_date: datetime | None = None,
        skip_if_exists: bool = False
    ) -> dict[str, Any] | None:
        """Extracts opening odds via hover with intelligent self-healing.

        This method implements a sophisticated hover-based extraction strategy:

        1. Smart polling: Waits for odd-container with 60s timeout
        2. Scroll alignment: Ensures element is in viewport before hover
        3. Tooltip polling: Checks for tooltip every 500ms (max 10 attempts)
        4. Mouse jitter: If tooltip fails, performs micro-movement to re-trigger

        Args:
            page: Playwright Page object
            entity_code: Internal entity code (e.g., "Entity_P")
            match_date: Match date for temporal alignment (defaults to now)
            skip_if_exists: If True, skip if data already exists (not implemented)

        Returns:
            Dictionary with keys:
                - init_h/d/a: Initial odds
                - opening_time_h/d/a: Initial odds timestamps
                - hover_failed: Boolean indicating extraction failure
                - hover_error: Error message if failed
                - source: Extraction method identifier

            Returns None only if match_id cannot be determined.
        """
        real_name = ENTITY_NAME_MAPPING.get(entity_code, entity_code)

        # Temporal alignment: Use real match date for accurate timestamps
        if match_date is None:
            logger.warning("[OddsExtractor] match_date not provided, using current date")
            match_date = datetime.now()
            match_year = match_date.year
        else:
            match_year = match_date.year

        try:
            logger.info(f"[OddsExtractor] Hover capture: {real_name} (match_date: {match_date.date()})")

            # Step 1: Smart polling - Wait for odd-container to appear
            await self._wait_for_element_ready(page)

            # Step 2: Find target bookmaker container
            target_container = await self._find_bookmaker_container(page, real_name)
            if not target_container:
                return self._build_hover_failed_result(f'Bookmaker {real_name} not found')

            # Step 3: Scroll into view (hover self-healing)
            await self._scroll_to_element(target_container)

            # Step 4: Execute hover with tooltip polling and retry
            tooltip_data = await self._hover_with_retry(
                page, target_container, POLLING_MAX_RETRIES
            )

            # Step 5: Parse tooltip data
            if not tooltip_data:
                return self._build_hover_failed_result('No tooltip data captured')

            return self._parse_tooltip_data(tooltip_data, match_year)

        except Exception as e:
            logger.error(f"[OddsExtractor] Hover capture exception: {e}")
            return {
                'hover_failed': True,
                'hover_error': f'Exception: {str(e)}',
                'init_h': None,
                'init_d': None,
                'init_a': None,
                'opening_time_h': None,
                'opening_time_d': None,
                'opening_time_a': None,
            }

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    async def _wait_for_element_ready(self, page: Page) -> None:
        """Waits for the odd-container element to be ready.

        Uses smart polling with 60s timeout instead of hard sleep.

        Args:
            page: Playwright Page object
        """
        try:
            logger.debug("[OddsExtractor] Smart polling: waiting for odd-container...")
            await page.wait_for_selector(
                "div[data-testid='odd-container']",
                timeout=SELECTOR_TIMEOUT_MS
            )
            logger.debug("[OddsExtractor] odd-container ready (millisecond response)")
        except Exception as e:
            logger.debug(f"[OddsExtractor] Polling timeout, continuing: {e}")

    async def _find_bookmaker_container(self, page: Page, real_name: str):
        """Finds the odd-container for the target bookmaker.

        Args:
            page: Playwright Page object
            real_name: Display name of the bookmaker

        Returns:
            Playwright Locator for the target container, or None if not found.
        """
        all_containers = page.locator("div[data-testid='odd-container']")
        count = await all_containers.count()

        logger.debug(f"[OddsExtractor] Found {count} odd-container elements")

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
                    logger.debug(f"[OddsExtractor] Found bookmaker: {bookmaker}")
                    return container

            except Exception as e:
                logger.debug(f"[OddsExtractor] Check failed for container {i}: {e}")
                continue

        logger.warning(f"[OddsExtractor] {real_name} container not found")
        return None

    async def _scroll_to_element(self, element) -> None:
        """Scrolls element into view for hover alignment.

        Args:
            element: Playwright Locator object
        """
        try:
            await element.scroll_into_view_if_needed(timeout=5000)
            logger.debug("[OddsExtractor] Element scrolled into view")
        except Exception as e:
            logger.debug(f"[OddsExtractor] Scroll failed, continuing: {e}")

    async def _hover_with_retry(
        self,
        page: Page,
        element,
        max_retries: int
    ) -> dict[str, Any] | None:
        """Executes hover with tooltip polling and mouse jitter retry.

        Args:
            page: Playwright Page object
            element: Playwright Locator to hover on
            max_retries: Maximum number of hover attempts

        Returns:
            Tooltip data dictionary if captured, None otherwise.
        """
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"[OddsExtractor] Retry hover ({attempt + 1}/{max_retries})")

                await element.hover()

                # Poll for tooltip appearance
                tooltip_data = await self._poll_for_tooltip(page)
                if tooltip_data:
                    return tooltip_data

                # Mouse jitter self-healing on first attempt failure
                if attempt == 0:
                    await self._perform_mouse_jitter(page, element)

                # Last attempt failed
                if attempt == max_retries - 1:
                    logger.warning(
                        f"[OddsExtractor] No tooltip detected "
                        f"after {max_retries} retries"
                    )

            except Exception as e:
                logger.error(f"[OddsExtractor] Hover attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return None

        return None

    async def _poll_for_tooltip(self, page: Page) -> dict[str, Any] | None:
        """Polls for tooltip appearance with configurable attempts.

        Args:
            page: Playwright Page object

        Returns:
            Tooltip data dictionary if found, None otherwise.
        """
        for poll_attempt in range(POLLING_TOOLTIP_ATTEMPTS):
            try:
                tooltip_data = await page.evaluate("""
                    () => {
                        const allElements = document.querySelectorAll('*');
                        for (let el of allElements) {
                            const text = el.textContent || '';
                            if (text.includes('Opening odds:') &&
                                text.length < 1000 &&
                                text.length > 50) {
                                return {
                                    tagName: el.tagName,
                                    className: el.className,
                                    text: text,
                                };
                            }
                        }
                        return null;
                    }
                """)

                if tooltip_data:
                    logger.info(
                        f"[OddsExtractor] Tooltip captured "
                        f"(poll {poll_attempt + 1}/{POLLING_TOOLTIP_ATTEMPTS})"
                    )
                    return tooltip_data

            except Exception:
                pass

            await page.wait_for_timeout(POLLING_TOOLTIP_DELAY_MS)

        return None

    async def _perform_mouse_jitter(self, page: Page, element) -> None:
        """Performs mouse jitter to re-trigger tooltip on hover failure.

        Simulates subtle hand movement to awaken dormant tooltips.

        Args:
            page: Playwright Page object
            element: Playwright Locator to jitter on
        """
        logger.debug("[OddsExtractor] Mouse jitter self-healing: executing micro-movement")
        try:
            box = await element.bounding_box()
            await page.mouse.move(box['x'] + 5, box['y'] + 5)
            await page.wait_for_timeout(100)
            await page.mouse.move(box['x'], box['y'])
            await page.wait_for_timeout(100)
            logger.debug("[OddsExtractor] Mouse jitter complete")
        except Exception as e:
            logger.debug(f"[OddsExtractor] Mouse jitter failed: {e}")

    def _parse_tooltip_data(
        self,
        tooltip_data: dict[str, Any],
        match_year: int
    ) -> dict[str, Any]:
        """Parses tooltip data to extract opening odds and timestamp.

        Args:
            tooltip_data: Raw tooltip data from page evaluation
            match_year: Year of the match for temporal alignment

        Returns:
            Parsed result dictionary with init odds and timestamps.
        """
        # Defensive check for missing or None text
        if not tooltip_data or not tooltip_data.get('text'):
            return self._build_hover_failed_result('Missing or null tooltip text')

        match = TOOLTIP_OPENING_PATTERN.search(tooltip_data['text'])

        if not match:
            logger.warning(
                f"[OddsExtractor] Cannot parse tooltip: "
                f"{tooltip_data['text'][:100]}"
            )
            return self._build_hover_failed_result('Cannot parse tooltip format')

        day, month_str, hour, minute, odd_value = match.groups()
        month = TOOLTIP_MONTH_MAP.get(month_str)

        if not month:
            return self._build_hover_failed_result(f'Invalid month: {month_str}')

        try:
            opening_time = datetime(match_year, month, int(day), int(hour), int(minute))
            opening_odd = float(odd_value)

            # Year consistency audit
            if abs(opening_time.year - match_year) > 1:
                logger.warning(
                    f"[OddsExtractor] Year mismatch! match_year={match_year}, "
                    f"opening_time_year={opening_time.year}"
                )

            logger.info(f"[OddsExtractor] Parsed: opening_time={opening_time.isoformat()}")

            return {
                'init_h': opening_odd,
                'init_d': None,
                'init_a': None,
                'opening_time_h': opening_time,
                'opening_time_d': None,
                'opening_time_a': None,
                'hover_failed': False,
                'hover_error': None,
                'source': 'hover_tooltip_production',
            }

        except Exception as e:
            logger.error(f"[OddsExtractor] Date construction failed: {e}")
            return self._build_hover_failed_result(f'Date construction failed: {e}')

    def _build_hover_failed_result(self, error_msg: str) -> dict[str, Any]:
        """Builds a standard failure result dictionary.

        Args:
            error_msg: Description of the failure

        Returns:
            Dictionary with hover_failed=True and error message.
        """
        return {
            'hover_failed': True,
            'hover_error': error_msg,
            'init_h': None,
            'init_d': None,
            'init_a': None,
            'opening_time_h': None,
            'opening_time_d': None,
            'opening_time_a': None,
        }

    # ========================================================================
    # Database Operations
    # ========================================================================

    def get_db_connection(self):
        """Gets a database connection using configured settings.

        Returns:
            psycopg2 connection object.
        """
        return psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
        )

    def save_multi_source_data(self, data_list: list[MultiSourceEntityData]) -> dict[str, int]:
        """Saves multiple source data records to the database.

        Implements upsert logic: updates existing records, inserts new ones.

        Args:
            data_list: List of MultiSourceEntityData objects to save

        Returns:
            Dictionary with statistics:
                - total: Number of records processed
                - inserted: Number of new records inserted
                - updated: Number of existing records updated
                - valid: Number of valid records
                - invalid: Number of invalid records
                - fully_captured: Number of fully captured records
        """
        if not data_list:
            return {
                'total': 0,
                'inserted': 0,
                'updated': 0,
                'valid': 0,
                'invalid': 0,
                'fully_captured': 0,
            }

        stats = {
            'total': len(data_list),
            'inserted': 0,
            'updated': 0,
            'valid': 0,
            'invalid': 0,
            'fully_captured': 0,
        }

        conn = self.get_db_connection()
        cursor = conn.cursor()

        for data in data_list:
            data.calculate_integrity_score()

            if data.is_valid:
                stats['valid'] += 1
            else:
                stats['invalid'] += 1

            if data.fully_captured:
                stats['fully_captured'] += 1

            try:
                cursor.execute("""
                    INSERT INTO metrics_multi_source_data (
                        match_id, source_name,
                        init_h, init_d, init_a,
                        opening_time_h, opening_time_d, opening_time_a,
                        final_h, final_d, final_a,
                        integrity_score, is_valid, validation_error,
                        fully_captured, data_timestamp
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (match_id, source_name)
                    DO UPDATE SET
                        init_h = EXCLUDED.init_h,
                        init_d = EXCLUDED.init_d,
                        init_a = EXCLUDED.init_a,
                        opening_time_h = EXCLUDED.opening_time_h,
                        opening_time_d = EXCLUDED.opening_time_d,
                        opening_time_a = EXCLUDED.opening_time_a,
                        final_h = EXCLUDED.final_h,
                        final_d = EXCLUDED.final_d,
                        final_a = EXCLUDED.final_a,
                        integrity_score = EXCLUDED.integrity_score,
                        is_valid = EXCLUDED.is_valid,
                        validation_error = EXCLUDED.validation_error,
                        fully_captured = EXCLUDED.fully_captured,
                        data_timestamp = EXCLUDED.data_timestamp
                """, (
                    data.match_id, data.source_name,
                    data.init_h, data.init_d, data.init_a,
                    data.opening_time_h, data.opening_time_d, data.opening_time_a,
                    data.final_h, data.final_d, data.final_a,
                    data.integrity_score, data.is_valid, data.validation_error,
                    data.fully_captured, data.data_timestamp,
                ))

                # Check if this was an insert or update
                if cursor.rowcount > 0:
                    stats['inserted'] += 1
                else:
                    stats['updated'] += 1

            except Exception as e:
                logger.error(f"Database error for match {data.match_id}: {e}")
                continue

        conn.commit()
        cursor.close()
        conn.close()

        return stats
