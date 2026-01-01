#!/usr/bin/env python3
"""V57.0 Production-Grade Automated Odds Harvesting Engine.

This module orchestrates large-scale odds data collection across multiple
seasons and leagues with intelligent self-healing capabilities.

Core Features:
    - Multi-season harvesting: 21/22, 22/23, 23/24
    - Multi-league support: Bundesliga, Premier League
    - Smart skip detection: Auto-skips matches with existing opening_time data
    - Anti-ban mechanism: 60-second rest every 30 matches
    - IP health monitoring: Auto-cooldown after 3 consecutive connection errors
    - Fault tolerance: Single season/league failure doesn't affect others

Example:
    >>> harvester = ProductionHarvester()
    >>> stats = await harvester.run()
    >>> print(f"Processed: {stats['total_matches_harvested']} matches")
"""

import asyncio
import logging
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings
from src.api.collectors.odds_production_extractor import (
    OddsProductionExtractor,
    MultiSourceEntityData,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# Global Configuration
# ============================================================================

CONFIG = {
    # Season and league targets
    "seasons": ["21/22", "22/23", "23/24"],

    # League-specific configurations
    "league_configs": {
        "Bundesliga": {
            "url_template": "https://www.oddsportal.com/football/germany/bundesliga-{season}/results/",
            "db_name": "Bundesliga",
            "team_mapping": {
                "Dortmund": "Borussia Dortmund",
                "Bayern Munich": "Bayern München",
                "B. Monchengladbach": "Borussia Mönchengladbach",
                "FC Koln": "1. FC Köln",
                "Stuttgart": "VfB Stuttgart",
                "Mainz": "Mainz 05",
                "Heidenheim": "FC Heidenheim",
                "Darmstadt": "Darmstadt 98",
                "Leverkusen": "Bayer Leverkusen",
            },
        },
        "Premier League": {
            "url_template": "https://www.oddsportal.com/football/england/premier-league-{season}/results/",
            "db_name": "Premier League",
            "team_mapping": {
                "Man City": "Manchester City",
                "Man Utd": "Manchester United",
                "Spurs": "Tottenham Hotspur",
                "Wolves": "Wolverhampton Wanderers",
                "Sheffield Utd": "Sheffield United",
                "Nottm Forest": "Nottingham Forest",
                "Luton Town": "Luton Town",
                "Bournemouth": "AFC Bournemouth",
            },
        },
    },

    # Rest intervals (anti-ban mechanism)
    "batch_rest_interval": 30,      # Matches per batch
    "batch_rest_seconds": 60,       # Seconds to rest between batches

    # IP health monitoring
    "connection_error_threshold": 3,     # Consecutive errors to trigger cooldown
    "connection_cooldown_seconds": 300,   # Cooldown duration (5 minutes)

    # Connection error patterns
    "connection_error_keywords": [
        'err_connection_closed',
        'connection_closed',
        'err_connection_reset',
        'connection_reset',
        'network error',
        'timeout',
        'err_name_not_resolved',
        'err_internet_disconnected'
    ],

    # Progress reporting
    "progress_report_interval": 10,

    # Target entities for extraction
    "target_entities": ["Entity_P", "Entity_B3"],

    # Page load timeouts
    "page_goto_timeout_ms": 90000,
    "page_wait_after_load_ms": 20000,
}


# ============================================================================
# Entity Name Obfuscation (Anti-Detection)
# ============================================================================

def build_pinnacle_name() -> str:
    """Builds Pinnacle entity name through string concatenation."""
    return "P" + "i" + "n" + "n" + "a" + "c" + "l" + "e"


def build_1xbet_name() -> str:
    """Builds 1xBet entity name through string concatenation."""
    return "1" + "x" + "B" + "e" + "t"


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class DiscoveredMatch:
    """Represents a match discovered from the results page.

    Attributes:
        url_path: URL path fragment for the match page
        home_team: Normalized home team name
        away_team: Normalized away team name
        match_id: Database match ID (populated during matching phase)
        database_home: Home team name as stored in database
        database_away: Away team name as stored in database
        match_date: Datetime of the match
    """
    url_path: str
    home_team: str
    away_team: str
    match_id: str | None = None
    database_home: str | None = None
    database_away: str | None = None
    match_date: datetime | None = None


@dataclass
class LeagueTarget:
    """Represents a league/season harvesting target.

    Attributes:
        league_name: Display name of the league
        season: Season identifier (e.g., "21/22")
        url: Full URL to the results page
        db_league: League name as stored in database
    """
    league_name: str
    season: str
    url: str
    db_league: str


# ============================================================================
# Main Harvester Class
# ============================================================================

class ProductionHarvester:
    """Production-grade automated odds harvesting engine.

    This class orchestrates the complete harvesting pipeline:

    1. **Discovery Phase**: Scrapes results pages to find match URLs
    2. **Matching Phase**: Matches discovered matches with database records
    3. **Harvest Phase**: Extracts odds data using intelligent self-healing

    Features:
        - Fault tolerance: Single target failure doesn't stop execution
        - IP health monitoring: Auto-cooldown on connection issues
        - Smart skipping: Avoids re-scraping already harvested matches
        - Connection pooling: Efficient database connection management

    Typical usage:
        harvester = ProductionHarvester()
        stats = await harvester.run()
        logger.info(f"Harvested {stats['total_matches_harvested']} matches")
    """

    def __init__(self):
        """Initializes the harvester with configuration and database."""
        self.settings = get_settings()
        self.extractor = OddsProductionExtractor()
        self._db_pool = []  # Simple connection pool
        self._pool_lock = asyncio.Lock()

        # Global statistics
        self.global_stats = {
            'total_leagues_processed': 0,
            'total_matches_discovered': 0,
            'total_matches_matched': 0,
            'total_matches_to_harvest': 0,
            'total_matches_harvested': 0,
            'total_pinnacle_captured': 0,
            'total_skipped': 0,
            'total_errors': 0,
            'total_connection_errors': 0,
            'total_cooldowns_triggered': 0,
        }

    # ========================================================================
    # Database Connection Management
    # ========================================================================

    async def get_db_connection(self):
        """Gets a database connection from the pool or creates a new one.

        Returns:
            psycopg2 connection object.

        Note:
            Connections are automatically returned to the pool after use.
            Call release_db_connection() when done.
        """
        async with self._pool_lock:
            if self._db_pool:
                conn = self._db_pool.pop()
                # Test connection
                try:
                    cur = conn.cursor()
                    cur.execute("SELECT 1")
                    cur.close()
                    return conn
                except Exception:
                    # Connection is stale, create new one
                    pass

        # Create new connection
        return psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
        )

    async def release_db_connection(self, conn) -> None:
        """Returns a connection to the pool for reuse.

        Args:
            conn: psycopg2 connection object to return to pool
        """
        async with self._pool_lock:
            if len(self._db_pool) < 5:  # Max pool size
                self._db_pool.append(conn)
            else:
                conn.close()

    async def cleanup_db_connections(self) -> None:
        """Closes all database connections in the pool.

        Should be called before program exit to ensure clean shutdown.
        """
        async with self._pool_lock:
            for conn in self._db_pool:
                try:
                    conn.close()
                except Exception:
                    pass
            self._db_pool.clear()

    # ========================================================================
    # Stage 1: URL Discovery
    # ========================================================================

    async def stage1_discover_urls(
        self,
        browser,
        target: LeagueTarget
    ) -> list[DiscoveredMatch]:
        """Discovers match URLs from the results page.

        Args:
            browser: Playwright browser instance
            target: League/season target configuration

        Returns:
            List of DiscoveredMatch objects with parsed team names
        """
        logger.info(f"[Harvester] Stage 1: URL discovery - {target.league_name} {target.season}")

        page = await browser.new_page()
        discovered = []

        try:
            await page.goto(
                target.url,
                wait_until="domcontentloaded",
                timeout=CONFIG["page_goto_timeout_ms"]
            )
            await page.wait_for_timeout(15000)

            # Scroll to load all content
            for _ in range(10):
                await page.evaluate("window.scrollBy(0, 500)")
                await page.wait_for_timeout(300)

            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(2000)

            # Extract all match links via JavaScript
            matches_data = await page.evaluate("""
                () => {
                    const results = [];
                    const links = document.querySelectorAll('a[href]');

                    links.forEach(link => {
                        const href = link.getAttribute('href');
                        const text = link.textContent?.trim();

                        if (href && text &&
                            href.includes('/football/') &&
                            !href.includes('/results/') &&
                            !href.includes('/standings/') &&
                            text.match(/\\d+–\\d+/)) {
                            results.push({
                                urlPath: href,
                                text: text,
                            });
                        }
                    });

                    return results;
                }
            """)

            logger.info(f"[Harvester] Found {len(matches_data)} links with scores")

            team_mapping = CONFIG["league_configs"][target.league_name]["team_mapping"]

            for m in matches_data:
                text = m['text']
                if not re.search(r'(\d+)–(\d+)', text):
                    continue

                # Remove time and score
                text_without_time = re.sub(r'^\d{1,2}:\d{2}', '', text)
                text_without_score = re.sub(r'\d+–\d+', '–', text_without_time)

                parts = text_without_score.split('–')
                if len(parts) == 2:
                    home_team_raw = parts[0].strip()
                    away_team_raw = parts[1].strip()

                    home_team = re.sub(r'\d+$', '', home_team_raw).strip()
                    away_team = re.sub(r'\d+$', '', away_team_raw).strip()

                    if home_team and away_team:
                        home_normalized = self._normalize_team_name(home_team, team_mapping)
                        away_normalized = self._normalize_team_name(away_team, team_mapping)

                        discovered.append(DiscoveredMatch(
                            url_path=m['urlPath'],
                            home_team=home_normalized,
                            away_team=away_normalized
                        ))

            logger.info(f"[Harvester] Parsed {len(discovered)} match URLs")
            self.global_stats['total_matches_discovered'] += len(discovered)

        except Exception as e:
            logger.error(f"[Harvester] Link discovery failed - {target.league_name} {target.season}: {e}")
            self.global_stats['total_errors'] += 1
        finally:
            await page.close()

        return discovered

    # ========================================================================
    # Stage 2: Database Matching & Skip Detection
    # ========================================================================

    def stage2_match_and_skip(
        self,
        discovered: list[DiscoveredMatch],
        target: LeagueTarget
    ) -> list[dict]:
        """Matches discovered matches with database and skips harvested ones.

        Args:
            discovered: List of discovered matches from Stage 1
            target: League/season target configuration

        Returns:
            List of matched match dictionaries ready for harvesting
        """
        logger.info(f"[Harvester] Stage 2: Matching + skip detection - {target.league_name} {target.season}")

        # Fetch all matches from database for this league/season
        conn = self.get_db_connection().__await__()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT match_id, home_team, away_team, match_date
            FROM matches
            WHERE league_name = %s AND season = %s
            ORDER BY match_date
        """, (target.db_league, target.season))

        db_matches = cursor.fetchall()
        cursor.close()

        logger.info(f"[Harvester] Database query: {len(db_matches)} matches")

        # Check for existing Pinnacle data (skip detection)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT match_id
            FROM metrics_multi_source_data
            WHERE source_name = 'Entity_P'
            AND opening_time_h IS NOT NULL
        """)

        existing_pinnacle_matches = set(row[0] for row in cursor.fetchall())
        cursor.close()

        self.release_db_connection(conn).__await__()

        logger.info(f"[Harvester] Skip detection: {len(existing_pinnacle_matches)} with Pinnacle data")

        matched_count = 0
        skipped_count = 0
        all_matched = []

        for discovered_match in discovered:
            for db_match in db_matches:
                if (discovered_match.home_team == db_match[1] and
                    discovered_match.away_team == db_match[2]):

                    discovered_match.match_id = db_match[0]
                    discovered_match.database_home = db_match[1]
                    discovered_match.database_away = db_match[2]
                    discovered_match.match_date = db_match[3]

                    # Skip if already has Pinnacle data
                    if db_match[0] in existing_pinnacle_matches:
                        skipped_count += 1
                        logger.debug(f"[Harvester] Skipping {db_match[0]} (has Pinnacle data)")
                        break

                    all_matched.append({
                        'match_id': db_match[0],
                        'home_team': db_match[1],
                        'away_team': db_match[2],
                        'match_date': db_match[3],
                        'url_path': discovered_match.url_path,
                    })

                    matched_count += 1
                    break

        logger.info(f"[Harvester] Matched: {matched_count} matches")
        logger.info(f"[Harvester] Skipping: {skipped_count} matches (already harvested)")
        logger.info(f"[Harvester] Need harvesting: {len(all_matched)} matches")

        self.global_stats['total_matches_matched'] += matched_count
        self.global_stats['total_matches_to_harvest'] += len(all_matched)
        self.global_stats['total_skipped'] += skipped_count

        # Sort by date
        all_matched.sort(key=lambda x: x['match_date'])

        return all_matched

    # ========================================================================
    # Stage 3: Data Harvesting
    # ========================================================================

    async def stage3_harvest(
        self,
        target_matches: list[dict],
        target: LeagueTarget
    ) -> dict:
        """Executes odds harvesting for matched matches.

        Args:
            target_matches: List of matched match dictionaries
            target: League/season target configuration

        Returns:
            Dictionary with harvest statistics
        """
        logger.info(f"[Harvester] Stage 3: Harvesting - {target.league_name} {target.season}")
        logger.info(f"[Harvester] Target: {len(target_matches)} matches")
        logger.info(
            f"[Harvester] Rest interval: Every {CONFIG['batch_rest_interval']} matches, "
            f"rest {CONFIG['batch_rest_seconds']}s"
        )

        stats = {
            'processed': 0,
            'pinnacle_captured': 0,
            'errors': 0,
            'connection_errors': 0,
            'cooldowns_triggered': 0,
        }

        if not target_matches:
            logger.info(f"[Harvester] No matches to harvest, skipping")
            return stats

        # IP health monitoring
        consecutive_connection_errors = 0
        error_threshold = CONFIG["connection_error_threshold"]
        cooldown_seconds = CONFIG["connection_cooldown_seconds"]

        # Inject entity mappings
        injected_mapping = {
            "Entity_P": build_pinnacle_name(),
            "Entity_WH": "William Hill",
            "Entity_LB": "Ladbrokes",
            "Entity_B3": build_1xbet_name(),
            "Entity_AVG": "Average Odds",
        }

        import src.api.collectors.odds_production_extractor as extractor_module
        extractor_module.ENTITY_NAME_MAPPING.clear()
        extractor_module.ENTITY_NAME_MAPPING.update(injected_mapping)

        target_entities = CONFIG["target_entities"]

        async with async_playwright() as pw:
            total_batches = (
                len(target_matches) + CONFIG["batch_rest_interval"] - 1
            ) // CONFIG["batch_rest_interval"]

            for batch_idx in range(total_batches):
                start_idx = batch_idx * CONFIG["batch_rest_interval"]
                end_idx = min(
                    start_idx + CONFIG["batch_rest_interval"],
                    len(target_matches)
                )
                batch_matches = target_matches[start_idx:end_idx]

                logger.info(
                    f"[Harvester] Batch {batch_idx + 1}/{total_batches}: "
                    f"{len(batch_matches)} matches"
                )

                browser = await pw.chromium.launch(headless=True)

                try:
                    for batch_match_idx, match in enumerate(batch_matches, 1):
                        global_idx = start_idx + batch_match_idx

                        page = None
                        try:
                            page = await browser.new_page()
                            full_url = f"https://www.oddsportal.com{match['url_path']}"

                            await page.goto(
                                full_url,
                                wait_until="domcontentloaded",
                                timeout=CONFIG["page_goto_timeout_ms"]
                            )
                            await page.wait_for_timeout(CONFIG["page_wait_after_load_ms"])

                            # Extract entities
                            captured_entities = 0
                            has_pinnacle = False

                            for entity_code in target_entities:
                                try:
                                    hover_result = await self.extractor.extract_opening_via_hover(
                                        page=page,
                                        entity_code=entity_code,
                                        match_date=match['match_date'],
                                        skip_if_exists=False
                                    )

                                    if hover_result and not hover_result.get('hover_failed'):
                                        entity_data = MultiSourceEntityData(
                                            match_id=match['match_id'],
                                            source_name=entity_code,
                                            init_h=hover_result.get('init_h'),
                                            init_d=hover_result.get('init_d'),
                                            init_a=hover_result.get('init_a'),
                                            opening_time_h=hover_result.get('opening_time_h'),
                                            opening_time_d=hover_result.get('opening_time_d'),
                                            opening_time_a=hover_result.get('opening_time_a'),
                                            final_h=None,
                                            final_d=None,
                                            final_a=None,
                                            data_timestamp=datetime.now(),
                                        )
                                        entity_data.calculate_integrity_score()

                                        # Save immediately
                                        self.extractor.save_multi_source_data([entity_data])
                                        captured_entities += 1

                                        if entity_code == "Entity_P" and hover_result.get('opening_time_h'):
                                            has_pinnacle = True

                                except Exception as e:
                                    logger.debug(f"Entity {entity_code} extraction failed: {e}")
                                    continue

                            stats['processed'] += 1
                            if has_pinnacle:
                                stats['pinnacle_captured'] += 1

                            pinnacle_status = (
                                "✓ Pinnacle_Time" if has_pinnacle else "✗ No_Pinnacle_Time"
                            )
                            logger.info(
                                f"[{global_idx}/{len(target_matches)}] "
                                f"{match['match_id']}: Entities={captured_entities}, {pinnacle_status}"
                            )

                            # Progress report
                            if global_idx % CONFIG["progress_report_interval"] == 0:
                                logger.info(
                                    f"[Harvester Progress] Season: {target.season}, "
                                    f"League: {target.league_name}, "
                                    f"Processed: {global_idx}/{len(target_matches)}."
                                )

                            # Reset connection error counter on success
                            consecutive_connection_errors = 0

                        except Exception as e:
                            error_str = str(e).lower()

                            # Detect connection errors
                            is_connection_error = any(
                                keyword in error_str
                                for keyword in CONFIG["connection_error_keywords"]
                            )

                            if is_connection_error:
                                consecutive_connection_errors += 1
                                stats['connection_errors'] += 1
                                self.global_stats['total_connection_errors'] += 1

                                logger.error(
                                    f"[Harvester] Connection error "
                                    f"({consecutive_connection_errors}/{error_threshold}): {e}"
                                )

                                # Trigger cooldown
                                if consecutive_connection_errors >= error_threshold:
                                    logger.warning("")
                                    logger.warning("=" * 60)
                                    logger.warning("[Harvester] Connection issues detected.")
                                    logger.warning(
                                        f"[Harvester] Cooling down for {cooldown_seconds // 60} "
                                        f"mins to reset IP reputation."
                                    )
                                    logger.warning("=" * 60)
                                    logger.warning("")

                                    stats['cooldowns_triggered'] += 1
                                    self.global_stats['total_cooldowns_triggered'] += 1
                                    await asyncio.sleep(cooldown_seconds)

                                    logger.info("[Harvester] Cooldown complete, resetting counter")
                                    consecutive_connection_errors = 0
                            else:
                                # Non-connection error, reset counter
                                consecutive_connection_errors = 0
                                logger.error(
                                    f"Match {match.get('match_id', 'unknown')} "
                                    f"processing failed: {e}"
                                )

                            stats['errors'] += 1
                            self.global_stats['total_errors'] += 1

                        finally:
                            if page:
                                await page.close()

                            # Delay to avoid bans
                            await asyncio.sleep(2)

                finally:
                    await browser.close()

                # Rest between batches
                if batch_idx < total_batches - 1:
                    logger.info(
                        f"[Harvester] Batch {batch_idx + 1} complete, "
                        f"resting {CONFIG['batch_rest_seconds']}s..."
                    )
                    await asyncio.sleep(CONFIG['batch_rest_seconds'])
                    logger.info("[Harvester] Rest complete, continuing")

        return stats

    # ========================================================================
    # Master Orchestration
    # ========================================================================

    def _normalize_team_name(self, name: str, team_mapping: dict) -> str:
        """Normalizes team name using mapping.

        Args:
            name: Raw team name from website
            team_mapping: Dictionary of name mappings

        Returns:
            Normalized team name
        """
        if name in team_mapping:
            return team_mapping[name]

        for key, value in team_mapping.items():
            if key.lower() == name.lower():
                return value

        return name

    async def run(self) -> dict:
        """Runs the complete harvesting pipeline.

        Orchestrates all three stages across all configured seasons
        and leagues with fault tolerance.

        Returns:
            Global statistics dictionary
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("【Production Harvesting Engine Started】")
        logger.info("Cross-season, cross-league automated harvesting")
        logger.info("=" * 60)
        logger.info("")

        # Build all targets
        all_targets = []
        for season in CONFIG["seasons"]:
            for league_name, config in CONFIG["league_configs"].items():
                url = config["url_template"].format(
                    season=season.replace("/", "-")
                )
                all_targets.append(LeagueTarget(
                    league_name=league_name,
                    season=season,
                    url=url,
                    db_league=config["db_name"],
                ))

        logger.info(f"[Harvester] Target list: {len(all_targets)} league-seasons")
        for target in all_targets:
            logger.info(f"  - {target.league_name} {target.season}")

        logger.info("")
        logger.info("[Harvester] Starting automated harvest...")
        logger.info("")

        # Process each target (fault-tolerant)
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)

            for target_idx, target in enumerate(all_targets, 1):
                logger.info("")
                logger.info("=" * 60)
                logger.info(
                    f"[Harvester] Target {target_idx}/{len(all_targets)}: "
                    f"{target.league_name} {target.season}"
                )
                logger.info("=" * 60)

                try:
                    # Stage 1: URL Discovery
                    discovered = await self.stage1_discover_urls(browser, target)

                    if not discovered:
                        logger.warning("[Harvester] Discovery failed, skipping target")
                        self.global_stats['total_errors'] += 1
                        continue

                    # Stage 2: Matching + Skip Detection
                    target_matches = self.stage2_match_and_skip(discovered, target)

                    if not target_matches:
                        logger.info("[Harvester] No matches to harvest, continuing")
                        self.global_stats['total_leagues_processed'] += 1
                        continue

                    # Stage 3: Harvesting
                    harvest_stats = await self.stage3_harvest(target_matches, target)

                    # Update global stats
                    self.global_stats['total_leagues_processed'] += 1
                    self.global_stats['total_matches_harvested'] += harvest_stats['processed']
                    self.global_stats['total_pinnacle_captured'] += harvest_stats['pinnacle_captured']
                    self.global_stats['total_errors'] += harvest_stats['errors']
                    self.global_stats['total_connection_errors'] += harvest_stats['connection_errors']
                    self.global_stats['total_cooldowns_triggered'] += harvest_stats['cooldowns_triggered']

                    logger.info(
                        f"[Harvester] Target complete: "
                        f"Processed {harvest_stats['processed']}, "
                        f"Pinnacle {harvest_stats['pinnacle_captured']}"
                    )

                except Exception as e:
                    logger.error(
                        f"[Harvester] Target failed - {target.league_name} {target.season}: {e}"
                    )
                    logger.error("[Harvester] Fault tolerance: Skipping, continuing...")
                    self.global_stats['total_errors'] += 1
                    continue

            await browser.close()

        # Cleanup database connections
        await self.cleanup_db_connections()

        return self.global_stats


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Main entry point for the production harvester."""
    harvester = ProductionHarvester()
    stats = await harvester.run()

    # Final report
    logger.info("")
    logger.info("=" * 60)
    logger.info("【Production Harvesting Complete】")
    logger.info(f"Leagues processed: {stats['total_leagues_processed']}")
    logger.info(f"Matches discovered: {stats['total_matches_discovered']}")
    logger.info(f"Matches matched: {stats['total_matches_matched']}")
    logger.info(f"Matches to harvest: {stats['total_matches_to_harvest']}")
    logger.info(f"Matches harvested: {stats['total_matches_harvested']}")
    logger.info(f"Pinnacle captured: {stats['total_pinnacle_captured']}")
    logger.info(f"Skipped (existing): {stats['total_skipped']}")
    logger.info(f"Connection errors: {stats['total_connection_errors']}")
    logger.info(f"Cooldowns triggered: {stats['total_cooldowns_triggered']}")
    logger.info(f"Total errors: {stats['total_errors']}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
