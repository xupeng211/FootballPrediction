"""
URL Reconnaissance Module - Match URL Discovery

This module provides production-grade URL discovery functionality for finding
and aligning match URLs from external sources (OddsPortal).

Core Features:
    - V151.4 golden regex pattern for hash extraction
    - Async Playwright-based page fetching
    - Fuzzy matching for team names
    - Batch database updates
    - Full type annotations and error handling

Usage:
    from src.core.scrapers.url_recon import UrlReconEngine, LeagueConfig

    recon = UrlReconEngine()
    stats = recon.discover_league_urls("La Liga")
    print(f"Discovered: {stats.discovered}, Updated: {stats.updated}")

Authors: V41.149 -> V41.153 Migration
Version: 1.0.0 (Production)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import logging
import re
from typing import Any
from urllib.parse import urljoin

from playwright.async_api import async_playwright
import psycopg2
from pydantic import BaseModel, field_validator

from src.config_unified import get_settings

# ============================================================================
# V151.4 Golden Regex Pattern
# ============================================================================

class MatchHashPattern:
    """V151.4 Golden regex patterns for URL matching.

    Pattern matches URLs like:
    /football/country/league-season/{home}-{away}-{hash}/
    """

    # Core pattern: Extract 8-12 character alphanumeric hash
    HASH_PATTERN = re.compile(r"/football/[^/]+/[^/]+/[^/]+-[^/]+-([a-zA-Z0-9]{8,12})/")

    @classmethod
    def extract_hash(cls, url: str) -> str | None:
        """Extract match hash from URL.

        Args:
            url: URL string.

        Returns:
            Hash string or None if not found.
        """
        match = cls.HASH_PATTERN.search(url)
        return match.group(1) if match else None

    @classmethod
    def is_match_url(cls, url: str) -> bool:
        """Check if URL matches pattern.

        Args:
            url: URL string.

        Returns:
            True if URL is a match page.
        """
        return cls.HASH_PATTERN.search(url) is not None


# ============================================================================
# Data Models
# ============================================================================

class LeagueConfig(BaseModel):
    """League configuration for URL discovery.

    Attributes:
        name: League display name.
        url: OddsPortal results page URL.
        season_suffix: Season identifier suffix.
    """

    name: str
    url: str
    season_suffix: str = "-2024-2025"

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith("https://www.oddsportal.com/"):
            raise ValueError(f"Invalid OddsPortal URL: {v}")
        return v


@dataclass
class MatchUrlPair:
    """Match and URL pair.

    Attributes:
        match_id: Database match ID.
        page_url: Discovered page URL.
        home_team: Home team name.
        away_team: Away team name.
    """

    match_id: str
    page_url: str
    home_team: str
    away_team: str


@dataclass
class ReconStats:
    """Statistics for reconnaissance operation.

    Attributes:
        total_matches: Total matches in database.
        missing_urls: Matches without URLs.
        discovered: URLs discovered from external source.
        matched: Successful fuzzy matches.
        updated: Database updates performed.
        start_time: Operation start timestamp.
        end_time: Operation end timestamp.
    """

    total_matches: int = 0
    missing_urls: int = 0
    discovered: int = 0
    matched: int = 0
    updated: int = 0
    start_time: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    end_time: float | None = None

    @property
    def duration(self) -> float:
        """Calculate operation duration in seconds."""
        end = self.end_time or datetime.utcnow().timestamp()
        return end - self.start_time

    @property
    def match_rate(self) -> float:
        """Calculate match success rate percentage."""
        if self.discovered == 0:
            return 0.0
        return (self.matched / self.discovered) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_matches": self.total_matches,
            "missing_urls": self.missing_urls,
            "discovered": self.discovered,
            "matched": self.matched,
            "updated": self.updated,
            "duration_seconds": round(self.duration, 2),
            "match_rate": round(self.match_rate, 2),
        }


# ============================================================================
# Main Recon Engine
# ============================================================================

class UrlReconEngine:
    """URL reconnaissance engine for match discovery.

    This engine handles the complete workflow:
    1. Query database for matches missing URLs
    2. Fetch match URLs from external source
    3. Perform fuzzy matching between datasets
    4. Batch update database with discovered URLs

    Attributes:
        settings: Application settings.
        logger: Logger instance.
        proxy_config: Proxy server configuration.
    """

    # Default league configurations
    DEFAULT_LEAGUES = {
        "La Liga": LeagueConfig(
            name="La Liga",
            url="https://www.oddsportal.com/football/spain/laliga/results/",
        ),
        "Ligue 1": LeagueConfig(
            name="Ligue 1",
            url="https://www.oddsportal.com/football/france/ligue-1/results/",
        ),
        "Premier League": LeagueConfig(
            name="Premier League",
            url="https://www.oddsportal.com/football/england/premier-league/results/",
        ),
        "Serie A": LeagueConfig(
            name="Serie A",
            url="https://www.oddsportal.com/football/italy/serie-a/results/",
        ),
        "Bundesliga": LeagueConfig(
            name="Bundesliga",
            url="https://www.oddsportal.com/football/germany/bundesliga/results/",
        ),
    }

    def __init__(
        self,
        logger: logging.Logger | None = None,
        proxy_host: str = "172.25.16.1",
        proxy_port: int = 7890,
    ):
        """Initialize URL recon engine.

        Args:
            logger: Custom logger instance.
            proxy_host: Proxy server host.
            proxy_port: Proxy server port.
        """
        self.settings = get_settings()
        self.logger = logger or logging.getLogger(__name__)
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port

    async def discover_league_urls(
        self,
        league_name: str,
        limit: int | None = None,
    ) -> ReconStats:
        """Discover and update URLs for a league.

        Args:
            league_name: League name to process.
            limit: Optional limit on matches to process.

        Returns:
            Reconnaissance statistics.

        Raises:
            ValueError: If league not supported.
        """
        stats = ReconStats()

        if league_name not in self.DEFAULT_LEAGUES:
            raise ValueError(
                f"Unsupported league: {league_name}. "
                f"Available: {list(self.DEFAULT_LEAGUES.keys())}"
            )

        league_config = self.DEFAULT_LEAGUES[league_name]

        self.logger.info(f"[RECON] Starting URL discovery for: {league_name}")

        # Step 1: Query database for missing URLs
        db_matches = await self._fetch_missing_matches(league_config.name, limit)
        stats.total_matches = len(db_matches)
        stats.missing_urls = len(db_matches)

        if not db_matches:
            self.logger.info("[RECON] No matches missing URLs")
            stats.end_time = datetime.utcnow().timestamp()
            return stats

        # Step 2: Fetch URLs from external source
        external_matches = await self._fetch_external_urls(league_config.url)
        stats.discovered = len(external_matches)

        self.logger.info(f"[RECON] Discovered {stats.discovered} URLs from external source")

        # Step 3: Fuzzy match
        matched_pairs = self._fuzzy_match(db_matches, external_matches)
        stats.matched = len(matched_pairs)

        self.logger.info(f"[RECON] Matched {stats.matched} URLs")

        # Step 4: Batch update database
        stats.updated = await self._batch_update_urls(matched_pairs)

        stats.end_time = datetime.utcnow().timestamp()

        self.logger.info(
            f"[RECON] Complete - "
            f"Updated: {stats.updated}/{stats.matched}"
        )

        return stats

    async def _fetch_missing_matches(
        self,
        league_name: str,
        limit: int | None,
    ) -> list[dict[str, Any]]:
        """Fetch matches missing URLs from database.

        Args:
            league_name: League name.
            limit: Optional result limit.

        Returns:
            List of match dictionaries.
        """
        conn = psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
        )
        cursor = conn.cursor()

        query = """
            SELECT match_id, home_team, away_team
            FROM matches
            WHERE league_name = %s
              AND page_url IS NULL
            ORDER BY match_date DESC
        """
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, (league_name,))
        matches = [
            {"match_id": row[0], "home_team": row[1], "away_team": row[2]}
            for row in cursor.fetchall()
        ]

        cursor.close()
        conn.close()

        return matches

    async def _fetch_external_urls(self, url: str) -> list[dict[str, Any]]:
        """Fetch match URLs from external source using Playwright.

        Args:
            url: Source URL to scrape.

        Returns:
            List of match data with URLs.
        """
        results = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                proxy={"server": f"http://{self.proxy_host}:{self.proxy_port}"},
            )
            context = await browser.new_context(
                locale="en-GB",
                timezone_id="Europe/London",
            )
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(5)  # V151.4: Wait for JS rendering

                # Extract all links
                all_links = await page.locator("a").all()

                for link in all_links:
                    try:
                        href = await link.get_attribute("href")
                        if not href:
                            continue

                        # Check if it's a match URL
                        if not MatchHashPattern.is_match_url(href):
                            continue

                        full_url = urljoin("https://www.oddsportal.com/", href)

                        # Parse team names from URL
                        teams = self._parse_teams_from_url(href)
                        if teams:
                            results.append({
                                "page_url": full_url,
                                "home_team": teams[0],
                                "away_team": teams[1],
                            })

                    except Exception:
                        continue

            finally:
                await browser.close()

        return results

    def _parse_teams_from_url(self, href: str) -> list[str] | None:
        """Parse team names from URL path.

        Args:
            href: URL path segment.

        Returns:
            [home_team, away_team] or None.
        """
        url_parts = href.strip("/").split("/")
        if len(url_parts) >= 4:
            match_part = url_parts[-1]
            name_part = "-".join(match_part.split("-")[:-1])
            teams = name_part.split("-")

            if len(teams) >= 2:
                home_team = " ".join(teams[:-1]).replace("-", " ").title()
                away_team = teams[-1].replace("-", " ").title()
                return [home_team, away_team]

        return None

    def _fuzzy_match(
        self,
        db_matches: list[dict[str, Any]],
        external_matches: list[dict[str, Any]],
    ) -> list[MatchUrlPair]:
        """Perform fuzzy matching between datasets.

        Args:
            db_matches: Matches from database.
            external_matches: Matches from external source.

        Returns:
            List of matched pairs.
        """
        matched_pairs: list[MatchUrlPair] = []
        matched_urls = set()

        for external in external_matches:
            if external["page_url"] in matched_urls:
                continue

            external_home = external["home_team"].lower().strip()
            external_away = external["away_team"].lower().strip()

            best_match = None
            best_score = 0

            for db_match in db_matches:
                db_home = db_match["home_team"].lower().strip()
                db_away = db_match["away_team"].lower().strip()

                score = 0
                if external_home in db_home or db_home in external_home:
                    score += 1
                if external_away in db_away or db_away in external_away:
                    score += 1

                if score > best_score:
                    best_score = score
                    best_match = db_match

            if best_match and best_score >= 2:
                matched_pairs.append(MatchUrlPair(
                    match_id=best_match["match_id"],
                    page_url=external["page_url"],
                    home_team=best_match["home_team"],
                    away_team=best_match["away_team"],
                ))
                matched_urls.add(external["page_url"])

        return matched_pairs

    async def _batch_update_urls(self, pairs: list[MatchUrlPair]) -> int:
        """Batch update database with discovered URLs.

        Args:
            pairs: Match URL pairs to update.

        Returns:
            Number of updated records.
        """
        if not pairs:
            return 0

        conn = psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
        )
        cursor = conn.cursor()

        updated_count = 0

        for pair in pairs:
            try:
                cursor.execute(
                    """
                    UPDATE matches
                    SET page_url = %s,
                        updated_at = NOW()
                    WHERE match_id = %s
                    """,
                    (pair.page_url, pair.match_id),
                )
                updated_count += 1
            except Exception as e:
                self.logger.warning(
                    f"[RECON] Update failed for {pair.match_id}: {e}"
                )

        conn.commit()
        cursor.close()
        conn.close()

        return updated_count


# ============================================================================
# Convenience Functions
# ============================================================================

async def discover_urls(
    league_name: str,
    limit: int | None = None,
) -> ReconStats:
    """Convenience function for URL discovery.

    Args:
        league_name: League to process.
        limit: Optional match limit.

    Returns:
        Reconnaissance statistics.
    """
    recon = UrlReconEngine()
    return await recon.discover_league_urls(league_name, limit)


# Convenience exports
__all__ = [
    "LeagueConfig",
    "MatchHashPattern",
    "MatchUrlPair",
    "ReconStats",
    "UrlReconEngine",
    "discover_urls",
]
