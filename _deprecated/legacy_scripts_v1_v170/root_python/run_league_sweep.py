#!/usr/bin/env python3
"""V125.0 Mimicry Rendering Sweep Engine - React Container Extraction.

This script implements a React-focused extraction strategy based on the
OddsHarvester open-source project audit conclusions.

V125.0 Features:
    - Deep Stealth: --disable-blink-features=AutomationControlled
    - React Container: Extract from #react-event-header data attribute
    - JSON Parsing: Parse eventBody for match URLs with 8-char hash
    - Zero Decryption: No API decryption needed, use rendered DOM

Usage:
    # Run league sweep for all leagues
    python scripts/run_league_sweep.py

    # Run for specific league
    python scripts/run_league_sweep.py --league "Premier League" --season "23/24"

    # Dry run (no database updates)
    python scripts/run_league_sweep.py --dry-run

    # Limit number of leagues to process
    python scripts/run_league_sweep.py --limit 5
"""

import argparse
import asyncio
import json
import logging
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

# V123.0: Disable proxy to fix WSL2 network issues
for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                  'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY']:
    os.environ.pop(proxy_var, None)

import psycopg2
from playwright.async_api import async_playwright, Page
from thefuzz import fuzz

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings
from src.utils.text_processor import TeamNameNormalizer, LeagueUrlMapper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://www.oddsportal.com"
FUZZY_THRESHOLD = 60  # Fuzzy matching threshold for team names
MAX_RETRIES = 3

# V125.0 React Container Extraction Constants
PAGE_LOAD_TIMEOUT = 60000  # 60 seconds for page load
REACT_CONTAINER_TIMEOUT = 30000  # 30 seconds for React container to appear
REACT_DATA_ATTRIBUTE = "data"  # Attribute containing JSON data

# V125.0 Deep Stealth User-Agent - Chrome 120 on Windows
STEALTH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# V125.0 Deep Stealth Browser Args
STEALTH_BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",  # V125.0: Critical!
    "--disable-dev-shm-usage",
    "--disable-setuid-sandbox",
    "--no-sandbox",
    "--disable-web-security",
    "--disable-features=VizDisplayCompositor",
    "--disable-gpu",
]

# Anti-detection JavaScript
STEALTH_SCRIPTS = [
    # Remove navigator.webdriver
    """() => {
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    }""",
    # Fake Chrome object
    """() => {
        window.chrome = {
            runtime: {}
        };
    }""",
    # Fake plugins
    """() => {
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
    }""",
    # Fake languages
    """() => {
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
    }""",
]


class LeagueSweepStats:
    """Statistics tracking for league sweep."""

    def __init__(self) -> None:
        """Initialize statistics tracker."""
        self.leagues_processed = 0
        self.matches_extracted = 0
        self.matches_matched = 0
        self.urls_updated = 0
        self.leagues_failed = 0
        self.start_time = datetime.now()

    def summary(self) -> str:
        """Generate summary statistics."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return f"""
═══════════════════════════════════════════════════════════════
V125.0 Mimicry Rendering Engine - Execution Summary
═══════════════════════════════════════════════════════════════
Leagues Processed:     {self.leagues_processed}
Matches Extracted:     {self.matches_extracted}
Matches Matched:       {self.matches_matched}
URLs Updated:          {self.urls_updated}
Leagues Failed:        {self.leagues_failed}
Execution Time:        {elapsed:.1f}s
Match Rate:            {self.matches_matched / elapsed:.2f} matches/s
═══════════════════════════════════════════════════════════════"""


async def extract_from_react_container(
    page: Page,
    league_name: str,
    season: str
) -> list[dict[str, Any]]:
    """V125.0 Phase 2: Extract match URLs using network interception.

    This function captures API responses that contain match data:
    1. Intercept all network requests
    2. Capture JSON responses with match URLs
    3. Extract URLs with 8-char hash

    Args:
        page: Playwright page instance
        league_name: League name
        season: Season string

    Returns:
        List of extracted match data with URLs
    """
    extracted_matches = []

    # Store captured API responses
    captured_responses = []

    # V125.0: Set up network interception
    async def handle_response(response):
        """Capture API responses containing match data."""
        try:
            # Only capture JSON responses
            content_type = response.header.get('content-type', '')
            if 'application/json' not in content_type:
                return

            url = response.url
            # Only capture relevant API endpoints
            if any(keyword in url for keyword in ['ajax', 'api', 'data', 'match', 'event']):
                try:
                    body = await response.text()
                    if body and ('/match/' in body.lower() or 'event' in body.lower()):
                        captured_responses.append({
                            'url': url,
                            'body': body
                        })
                        logger.debug(f"  🎣 Captured response from: {url[:80]}")
                except Exception as e:
                    logger.debug(f"  ⚠️  Failed to capture response: {e}")
        except Exception as e:
            pass  # Ignore response handling errors

    # Register response handler
    page.on('response', handle_response)

    logger.info(f"  🎯 Network interception enabled")

    # Wait for page to load and API calls to complete
    logger.info(f"  ⏳ Waiting for API data to load...")
    await asyncio.sleep(10)

    # Scroll to trigger lazy loading and API calls
    for i in range(10):
        await page.mouse.wheel(0, 800)
        await asyncio.sleep(1)

    # Wait for final API calls to complete
    await asyncio.sleep(10)

    # Unregister response handler
    page.remove_listener('response', handle_response)

    logger.info(f"  📊 Captured {len(captured_responses)} API responses")

    # Process captured responses
    all_json_data = []
    for resp in captured_responses:
        try:
            data = json.loads(resp['body'])
            all_json_data.append(data)
            logger.info(f"  ✅ Parsed JSON from: {resp['url'][:80]}")
        except json.JSONDecodeError:
            # Not valid JSON, skip
            continue
        except Exception as e:
            logger.debug(f"  ⚠️  Parse error: {e}")
            continue

    if not all_json_data:
        logger.warning(f"  ❌ No valid JSON data captured from API responses")

        # Fallback: Query DOM for rendered match links
        logger.info(f"  🔍 Fallback: Querying DOM for rendered match links...")
        try:
            dom_urls = await page.evaluate("""() => {
                const links = document.querySelectorAll('a[href*="/match/"]');
                return Array.from(links).map(a => a.href);
            }""")

            logger.info(f"  📋 Found {len(dom_urls)} match links in DOM")

            for url in dom_urls:
                hash_match = re.search(r'/match/[^/]+-([a-z0-9]{8})', url.lower())
                if hash_match:
                    extracted_matches.append({
                        "url": url,
                        "raw_text": "DOM Extracted",
                        "home_normalized": None,
                        "away_normalized": None,
                    })

            logger.info(f"  ✅ Extracted {len(extracted_matches)} URLs from DOM")
        except Exception as e:
            logger.error(f"  ❌ DOM query failed: {e}")

        return extracted_matches

    # Extract URLs from JSON data
    logger.info(f"  🔍 Extracting URLs from {len(all_json_data)} JSON responses...")
    for data in all_json_data:
        data_str = json.dumps(data).lower()

        # Find all /match/ URLs with 8-char hash
        for match in re.finditer(r'"/match/[^"]+-([a-z0-9]{8})"', data_str):
            full_url = f"{BASE_URL}{match.group(0)}"
            extracted_matches.append({
                "url": full_url,
                "raw_text": "API Extracted",
                "home_normalized": None,
                "away_normalized": None,
            })

    logger.info(f"  ✅ Extracted {len(extracted_matches)} match URLs from API")

    # Validate hash format
    hash_pattern = re.compile(r'/match/[^/]+-([a-z0-9]{8})')
    hashed_count = sum(1 for m in extracted_matches if hash_pattern.search(m["url"]))

    logger.info(f"  🔒 URLs with valid 8-char hash: {hashed_count}/{len(extracted_matches)}")

    # Log sample matches
    if len(extracted_matches) > 0:
        logger.info(f"  📋 Sample URLs (first 10):")
        for i, match in enumerate(extracted_matches[:10], 1):
            hash_match = hash_pattern.search(match["url"])
            hash_str = hash_match.group(1) if hash_match else "NO HASH"
            logger.info(f"     [{i}] {hash_str} -> {match['url']}")
    else:
        logger.warning(f"  ⚠️  No URLs extracted")

    # Deduplicate URLs
    seen_urls = set()
    unique_matches = []
    for match in extracted_matches:
        if match["url"] not in seen_urls:
            seen_urls.add(match["url"])
            unique_matches.append(match)

    logger.info(f"  ✅ Deduplicated to {len(unique_matches)} unique URLs")

    return unique_matches


async def apply_stealth_armor(page: Page) -> None:
    """V123.0 Phase 1: Apply anti-fingerprinting stealth armor.

    This function removes automation traces and spoofs browser features
    to avoid detection by anti-scraping systems.

    Args:
        page: Playwright page instance
    """
    logger.debug("  🛡️  Applying stealth armor...")

    # Apply all stealth scripts
    for script in STEALTH_SCRIPTS:
        try:
            await page.add_init_script(script)
        except Exception as e:
            logger.debug(f"    ⚠️  Failed to apply stealth script: {e}")

    # Additional stealth: override navigator.webdriver in context
    await page.evaluate("""() => {
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    }""")

    logger.debug("  ✅ Stealth armor applied")


def normalize_season_format(season: str) -> str:
    """Normalize season format from database to URL format.

    Args:
        season: Season string (e.g., "23/24", "2023-2024")

    Returns:
        Normalized season string (e.g., "2023-2024")
    """
    if not season:
        return "2023-2024"

    # Handle "23/24" format -> "2023-2024"
    if "/" in season:
        parts = season.split("/")
        if len(parts) == 2:
            try:
                year1 = int(parts[0])
                year2 = int(parts[1])

                # Handle 23/24 -> 2023-2024
                if year1 < 100:
                    year1 += 2000 if year1 < 50 else 1900
                if year2 < 100:
                    year2 += 2000 if year2 < 50 else 1900

                # Handle cross-year season (23/24 -> 2023-2024)
                if year2 < year1:
                    year2 += 100

                return f"{year1}-{year2}"
            except ValueError:
                pass

    # Already in correct format or unknown, return as-is
    return season


def get_unique_leagues_from_db(conn) -> list[tuple[str, str, int]]:
    """Query database for unique (league_name, season) combinations.

    Args:
        conn: Database connection

    Returns:
        List of tuples (league_name, season, match_count)
    """
    query = """
        SELECT
            m.league_name,
            COALESCE(m.season, '23/24') as season,
            COUNT(*) as match_count
        FROM matches m
        LEFT JOIN match_search_queue q ON m.match_id = q.match_id
        WHERE m.oddsportal_url IS NULL
           OR q.status = 'PENDING'
        GROUP BY m.league_name, COALESCE(m.season, '23/24')
        ORDER BY match_count DESC;
    """

    with conn.cursor() as cur:
        cur.execute(query)
        results = cur.fetchall()

    # Normalize season format
    normalized_results = []
    for league_name, season, count in results:
        normalized_season = normalize_season_format(season)
        normalized_results.append((league_name, normalized_season, count))

    logger.info(f"Found {len(normalized_results)} unique league-season combinations")
    return normalized_results


def get_pending_matches_for_league(
    conn,
    league_name: str,
    season: str
) -> list[dict[str, Any]]:
    """Get pending matches for a specific league and season.

    Args:
        conn: Database connection
        league_name: League name
        season: Season string (normalized format e.g., "2023-2024")

    Returns:
        List of match dictionaries
    """
    # Convert normalized season to possible database formats
    # e.g., "2023-2024" -> "23/24", "23-24", etc.
    possible_seasons = [season]

    if "-" in season and len(season) >= 4:
        # Convert "2023-2024" to "23/24"
        parts = season.split("-")
        if len(parts) == 2 and len(parts[0]) == 4:
            short1 = parts[0][2:]  # "23"
            short2 = parts[1][2:] if len(parts[1]) == 4 else parts[1]  # "24"
            possible_seasons.append(f"{short1}/{short2}")
            possible_seasons.append(f"{short1}-{short2}")

    # Build dynamic query with multiple season possibilities
    season_placeholders = ",".join(["%s"] * len(possible_seasons))
    query = f"""
        SELECT
            m.match_id,
            m.home_team,
            m.away_team,
            m.match_date,
            m.oddsportal_url
        FROM matches m
        LEFT JOIN match_search_queue q ON m.match_id = q.match_id
        WHERE m.league_name = %s
          AND (m.season IN ({season_placeholders}) OR m.season IS NULL)
          AND (m.oddsportal_url IS NULL OR q.status = 'PENDING')
        ORDER BY m.match_date DESC;
    """

    params = [league_name] + possible_seasons

    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    matches = []
    for row in rows:
        matches.append({
            "match_id": row[0],
            "home_team": row[1],
            "away_team": row[2],
            "match_date": row[3],
            "oddsportal_url": row[4]
        })

    logger.info(f"  Found {len(matches)} pending matches for {league_name} {season}")
    return matches


async def sweep_league_results_page(
    page: Page,
    league_name: str,
    season: str,
    mapper: LeagueUrlMapper,
    normalizer: TeamNameNormalizer
) -> list[dict[str, Any]]:
    """V125.0: Sweep a league results page using network interception.

    This function implements API response interception:
    1. Set up network handler BEFORE navigation
    2. Navigate to the results page
    3. Capture JSON API responses
    4. Extract match URLs from captured data

    Args:
        page: Playwright page instance (with stealth armor already applied)
        league_name: League name
        season: Season string
        mapper: LeagueUrlMapper instance
        normalizer: TeamNameNormalizer instance (unused in V125.0, kept for compatibility)

    Returns:
        List of extracted match data with URLs
    """
    logger.info(f"  🎯 V125.0 Network Interception Extractor: {league_name} {season}")

    # Construct URL
    results_url = mapper.construct_results_url(league_name, season)
    if not results_url:
        logger.warning(f"  ❌ No URL mapping for league: {league_name}")
        return []

    logger.info(f"  📍 URL: {results_url}")

    # V125.0: Set up network interception BEFORE navigation
    captured_responses = []
    all_requests = []

    async def handle_request(request):
        """Log all outgoing requests for debugging."""
        all_requests.append({
            'url': request.url,
            'method': request.method,
            'resource_type': request.resource_type
        })

    async def handle_response(response):
        """Capture API responses containing match data."""
        try:
            url = response.url
            status = response.status

            # Log ALL responses
            logger.debug(f"  📡 [{status}] {url[:100]}")

            # Capture relevant responses
            if status == 200:
                try:
                    body = await response.text()
                    if body and len(body) > 10:  # Lower threshold
                        captured_responses.append({
                            'url': url,
                            'body': body,
                            'status': status,
                        })
                        # Log interesting responses
                        if any(keyword in url.lower() for keyword in ['ajax', 'api', 'data']):
                            logger.info(f"  🎣 Captured API ({len(body)} chars): {url[:80]}")
                        # Log if it contains match data
                        elif '/match/' in body.lower():
                            logger.info(f"  🎣 Captured match data ({len(body)} chars): {url[:80]}")
                except Exception as e:
                    logger.debug(f"  ⚠️  Failed to read body: {e}")
        except Exception:
            pass

    # Register handlers BEFORE navigation
    page.on('request', handle_request)
    page.on('response', handle_response)
    logger.info(f"  🎣 Network interceptor registered")

    # Navigate to page
    logger.info(f"  🌐 Navigating to results page...")
    try:
        await page.goto(results_url, timeout=PAGE_LOAD_TIMEOUT, wait_until="domcontentloaded")
        logger.info(f"  ✅ Navigation complete")
    except Exception as e:
        logger.warning(f"  ⚠️  Navigation timeout (continuing anyway): {e}")

    # Wait for initial page load
    await asyncio.sleep(3)

    # Scroll to trigger lazy loading and API calls - MORE aggressive
    logger.info(f"  📜 Scrolling to trigger lazy loading...")
    for i in range(30):
        await page.mouse.wheel(0, 500)
        await asyncio.sleep(0.3)

    # Wait for additional API calls to complete
    await asyncio.sleep(10)

    # Unregister handlers
    page.remove_listener('request', handle_request)
    page.remove_listener('response', handle_response)
    logger.info(f"  📊 Made {len(all_requests)} requests, captured {len(captured_responses)} responses")

    # Log all request URLs for debugging
    logger.info(f"  🔍 Request URLs (first 20):")
    for i, req in enumerate(all_requests[:20], 1):
        logger.info(f"     [{i}] {req['resource_type']}: {req['url'][:80]}")

    # Process captured responses
    extracted_matches = []
    all_json_data = []

    # Save ajax-user-data response for debugging
    for resp in captured_responses:
        if 'ajax-user-data' in resp['url']:
            debug_path = Path("logs") / "v125_0_ajax_user_data.txt"
            debug_path.parent.mkdir(exist_ok=True)
            with open(debug_path, "w") as f:
                f.write(resp['body'])
            logger.info(f"  💾 Saved ajax-user-data to: {debug_path}")

    # V125.0: Save tournament archive response - THIS IS THE GOLD MINE!
    for resp in captured_responses:
        if 'ajax-sport-country-tournament-archive' in resp['url']:
            debug_path = Path("logs") / "v125_0_tournament_archive.json"
            debug_path.parent.mkdir(exist_ok=True)
            with open(debug_path, "w") as f:
                f.write(resp['body'])
            logger.info(f"  💾 Saved tournament archive ({len(resp['body'])} chars) to: {debug_path}")
            logger.info(f"  ⚠️  URL pattern: {resp['url'][:100]}")

    # V125.0: Try to manually trigger tournament archive API
    logger.info(f"  🔍 Attempting to manually trigger tournament archive API...")
    try:
        api_response = await page.evaluate("""() => {
            // Try to manually trigger the API call by calling the same function the page uses
            if (window.pageVar && window.pageVar.encodedTurnamentId) {
                const tournamentId = window.pageVar.encodedTurnamentId;
                const sportId = window.pageVar['sport-id'] || 1;

                // Try to find and call the API loading function
                if (window.$nuxt) {
                    return {nuxt: true, tournamentId};
                }
            }
            return {error: 'pageVar not found'};
        }""")
        logger.info(f"  📊 API trigger response: {api_response}")
    except Exception as e:
        logger.warning(f"  ⚠️  API trigger failed: {e}")

    # V125.0: Try to query Vue.js/React app data store
    logger.info(f"  🔍 Querying JavaScript app data store...")
    try:
        app_data = await page.evaluate("""() => {
            // Try multiple ways to get app data
            const results = {};

            // Check for Nuxt.js data
            if (window.__NUXT__) {
                results.nuxt = window.__NUXT__;
            }

            // Check for Vue app data
            if (window.__VUE__) {
                results.vue = 'Vue detected';
            }

            // Check for React data
            const reactElements = document.querySelectorAll('[data-reactroot]');
            if (reactElements.length > 0) {
                results.reactElements = reactElements.length;
            }

            // Check all script tags for JSON data
            const scripts = document.querySelectorAll('script');
            for (let i = 0; i < scripts.length; i++) {
                const text = scripts[i].textContent;
                if (text.includes('/match/') || text.includes('eventBody')) {
                    results.scriptWithMatchData = i;
                    break;
                }
            }

            // Check all elements with data-* attributes
            const allElements = document.querySelectorAll('*');
            let foundDataAttr = false;
            for (let el of allElements) {
                for (let attr of el.attributes) {
                    if (attr.name.startsWith('data-') && attr.value && attr.value.length > 100) {
                        if (!foundDataAttr) {
                            results.firstDataAttr = {name: attr.name, length: attr.value.length};
                            foundDataAttr = true;
                            break;
                        }
                    }
                }
            }

            return results;
        }""")

        logger.info(f"  📊 App data query results: {app_data}")
    except Exception as e:
        logger.warning(f"  ⚠️  App data query failed: {e}")

    for resp in captured_responses:
        try:
            data = json.loads(resp['body'])
            all_json_data.append(data)
            logger.info(f"  ✅ Parsed JSON from: {resp['url'][:80]}")
        except json.JSONDecodeError:
            continue
        except Exception as e:
            logger.debug(f"  ⚠️  Parse error: {e}")
            continue

    # Extract URLs from JSON data
    if all_json_data:
        logger.info(f"  🔍 Extracting URLs from {len(all_json_data)} JSON responses...")
        for data in all_json_data:
            data_str = json.dumps(data).lower()
            for match in re.finditer(r'"/match/[^"]+-([a-z0-9]{8})"', data_str):
                full_url = f"{BASE_URL}{match.group(0)}"
                extracted_matches.append({
                    "url": full_url,
                    "raw_text": "API Extracted",
                    "home_normalized": None,
                    "away_normalized": None,
                })
        logger.info(f"  ✅ Extracted {len(extracted_matches)} match URLs from API")
    else:
        logger.warning(f"  ❌ No valid JSON data captured")

        # Fallback: Query DOM for rendered match links
        logger.info(f"  🔍 Fallback: Querying DOM for rendered match links...")
        try:
            dom_urls = await page.evaluate("""() => {
                const links = document.querySelectorAll('a[href*="/match/"]');
                return Array.from(links).map(a => a.href);
            }""")
            logger.info(f"  📋 Found {len(dom_urls)} match links in DOM")

            for url in dom_urls:
                hash_match = re.search(r'/match/[^/]+-([a-z0-9]{8})', url.lower())
                if hash_match:
                    extracted_matches.append({
                        "url": url,
                        "raw_text": "DOM Extracted",
                        "home_normalized": None,
                        "away_normalized": None,
                    })
            logger.info(f"  ✅ Extracted {len(extracted_matches)} URLs from DOM")
        except Exception as e:
            logger.error(f"  ❌ DOM query failed: {e}")

    # Deduplicate and return
    seen_urls = set()
    unique_matches = []
    for match in extracted_matches:
        if match["url"] not in seen_urls:
            seen_urls.add(match["url"])
            unique_matches.append(match)

    # Log sample matches
    if len(unique_matches) > 0:
        hash_pattern = re.compile(r'/match/[^/]+-([a-z0-9]{8})')
        logger.info(f"  📋 Sample URLs (first 10):")
        for i, match in enumerate(unique_matches[:10], 1):
            hash_match = hash_pattern.search(match["url"])
            hash_str = hash_match.group(1) if hash_match else "NO HASH"
            logger.info(f"     [{i}] {hash_str} -> {match['url']}")

    logger.info(f"  ✅ Deduplicated to {len(unique_matches)} unique URLs")

    return unique_matches


def match_urls_to_database(
    extracted_matches: list[dict[str, Any]],
    db_matches: list[dict[str, Any]],
    normalizer: TeamNameNormalizer,
    stats: LeagueSweepStats
) -> list[tuple[str, str]]:
    """V122.2: Match extracted URLs to database matches using fuzzy matching.

    Args:
        extracted_matches: Matches extracted from OddsPortal DOM
        db_matches: Matches from database
        normalizer: TeamNameNormalizer instance
        stats: Statistics tracker

    Returns:
        List of (match_id, url) tuples to update
    """
    updates = []

    for db_match in db_matches:
        match_id = db_match["match_id"]
        home_team = normalizer.normalize(db_match["home_team"])
        away_team = normalizer.normalize(db_match["away_team"])
        match_date = db_match["match_date"]

        # Find best match in extracted matches
        best_match = None
        best_score = 0

        for extracted in extracted_matches:
            # DOM data has home_normalized/away_normalized
            extracted_home = extracted.get("home_normalized")
            extracted_away = extracted.get("away_normalized")

            if not extracted_home or not extracted_away:
                continue

            # Direct fuzzy matching
            home_sim = fuzz.partial_ratio(home_team, extracted_home)
            away_sim = fuzz.partial_ratio(away_team, extracted_away)

            # Both teams must meet threshold
            if home_sim >= FUZZY_THRESHOLD and away_sim >= FUZZY_THRESHOLD:
                avg_score = (home_sim + away_sim) / 2
                if avg_score > best_score:
                    best_score = avg_score
                    best_match = extracted

        if best_match:
            updates.append((match_id, best_match["url"]))
            stats.matches_matched += 1
            logger.debug(
                f"    ✅ Match {match_id}: "
                f"{db_match['home_team']} vs {db_match['away_team']} -> {best_match['url']}"
            )

    stats.matches_extracted += len(extracted_matches)
    return updates


def update_database_with_urls(
    conn,
    updates: list[tuple[str, str]],
    dry_run: bool = False
) -> int:
    """Update database with discovered URLs.

    Args:
        conn: Database connection
        updates: List of (match_id, url) tuples
        dry_run: If True, don't actually update

    Returns:
        Number of updates performed
    """
    if dry_run:
        logger.info(f"  [DRY RUN] Would update {len(updates)} match URLs")
        return len(updates)

    update_matches_query = """
        UPDATE matches
        SET oddsportal_url = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE match_id = %s;
    """

    update_queue_query = """
        UPDATE match_search_queue
        SET status = 'SUCCESS',
            discovered_url = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE match_id = %s;
    """

    updated_count = 0

    with conn.cursor() as cur:
        for match_id, url in updates:
            try:
                # Update matches table
                cur.execute(update_matches_query, (url, match_id))
                # Update queue table
                cur.execute(update_queue_query, (url, match_id))
                updated_count += 1
            except Exception as e:
                logger.error(f"    ❌ Failed to update {match_id}: {e}")

        conn.commit()

    logger.info(f"  ✅ Updated {updated_count} match URLs in database")
    return updated_count


async def worker(
    worker_id: int,
    leagues: list[tuple[str, str, int]],
    conn,
    mapper: LeagueUrlMapper,
    normalizer: TeamNameNormalizer,
    stats: LeagueSweepStats,
    dry_run: bool,
    stop_event: asyncio.Event
) -> None:
    """V125.0: Worker coroutine with deep stealth browser for processing leagues.

    Args:
        worker_id: Worker ID for logging
        leagues: List of (league_name, season, count) tuples
        conn: Database connection
        mapper: LeagueUrlMapper instance
        normalizer: TeamNameNormalizer instance
        stats: Statistics tracker
        dry_run: If True, don't update database
        stop_event: Event to signal graceful shutdown
    """
    async with async_playwright() as p:
        # V125.0 Phase 1: Deep stealth browser with --disable-blink-features=AutomationControlled
        browser = await p.chromium.launch(
            headless=True,
            args=STEALTH_BROWSER_ARGS  # V125.0: Critical!
        )

        # V125.0: Create context with stealth settings
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=STEALTH_USER_AGENT,
            locale="en-US",
            timezone_id="America/New_York",
        )

        # V125.0: Add stealth headers
        await context.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

        page = await context.new_page()

        # V125.0 Phase 1: Apply stealth armor
        await apply_stealth_armor(page)

        for i, (league_name, season, _) in enumerate(leagues):
            if stop_event.is_set():
                logger.info(f"Worker {worker_id}: Stop event received, exiting...")
                break

            logger.info(f"\n[Worker {worker_id}] [{i+1}/{len(leagues)}] Processing: {league_name} {season}")

            # Get pending matches for this league
            db_matches = get_pending_matches_for_league(conn, league_name, season)
            if not db_matches:
                logger.info(f"  ⏭️  No pending matches, skipping...")
                continue

            # Sweep the league results page
            try:
                extracted_matches = await sweep_league_results_page(
                    page, league_name, season, mapper, normalizer
                )

                if not extracted_matches:
                    logger.warning(f"  ⚠️  No matches extracted from page")
                    stats.leagues_failed += 1
                    continue

                # Match URLs to database
                updates = match_urls_to_database(
                    extracted_matches, db_matches, normalizer, stats
                )

                # Update database
                if updates:
                    count = update_database_with_urls(conn, updates, dry_run)
                    stats.urls_updated += count

                stats.leagues_processed += 1

                # Delay between requests
                await asyncio.sleep(3)

            except Exception as e:
                logger.error(f"  ❌ Error processing {league_name}: {e}")
                stats.leagues_failed += 1
                continue

        await context.close()
        await browser.close()


async def main_async(
    limit: int | None = None,
    league_filter: str | None = None,
    season_filter: str | None = None,
    dry_run: bool = False,
    max_workers: int = 1  # V125.0: Single worker for React extraction
) -> None:
    """V125.0: Main async function with Mimicry Rendering mode.

    Args:
        limit: Maximum number of leagues to process
        league_filter: Filter by league name
        season_filter: Filter by season
        dry_run: If True, don't update database
        max_workers: Maximum number of concurrent workers
    """
    logger.info("=" * 80)
    logger.info("V125.0 Mimicry Rendering Engine - React Container Extraction")
    logger.info("=" * 80)

    # Initialize
    settings = get_settings()
    mapper = LeagueUrlMapper()
    normalizer = TeamNameNormalizer()
    stats = LeagueSweepStats()
    stop_event = asyncio.Event()

    # Connect to database
    logger.info("\n📡 Connecting to database...")
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )
    logger.info("  ✅ Database connected")

    # Get unique leagues from database
    logger.info("\n🔍 Querying database for unique leagues...")
    all_leagues = get_unique_leagues_from_db(conn)

    # Apply filters
    if league_filter:
        all_leagues = [
            (l, s, c) for l, s, c in all_leagues
            if league_filter.lower() in l.lower()
        ]
        logger.info(f"  🎯 Filtered by league name: {league_filter}")

    if season_filter:
        # Normalize the filter season too
        normalized_filter = normalize_season_format(season_filter)
        all_leagues = [
            (l, s, c) for l, s, c in all_leagues
            if normalized_filter in s or season_filter in s
        ]
        logger.info(f"  🎯 Filtered by season: {season_filter} (normalized: {normalized_filter})")

    # Apply limit
    if limit:
        all_leagues = all_leagues[:limit]
        logger.info(f"  ⚙️  Limited to {limit} leagues")

    logger.info(f"\n📋 Processing {len(all_leagues)} leagues with {max_workers} worker(s)...")

    # Display top leagues
    logger.info("\nTop 10 leagues to process:")
    for i, (league, season, count) in enumerate(all_leagues[:10], 1):
        logger.info(f"  {i}. {league} {season} - {count} matches")

    if len(all_leagues) > 10:
        logger.info(f"  ... and {len(all_leagues) - 10} more")

    # Split leagues among workers
    leagues_per_worker = len(all_leagues) // max_workers
    worker_tasks = []

    for worker_id in range(max_workers):
        start_idx = worker_id * leagues_per_worker
        if worker_id == max_workers - 1:
            # Last worker takes remaining
            end_idx = len(all_leagues)
        else:
            end_idx = start_idx + leagues_per_worker

        worker_leagues = all_leagues[start_idx:end_idx]

        if not worker_leagues:
            continue

        task = asyncio.create_task(
            worker(
                worker_id,
                worker_leagues,
                conn,
                mapper,
                normalizer,
                stats,
                dry_run,
                stop_event
            )
        )
        worker_tasks.append(task)

    # Wait for all workers to complete
    await asyncio.gather(*worker_tasks, return_exceptions=True)

    # Close database connection
    conn.close()

    # Print summary
    logger.info(stats.summary())


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="V125.0 Mimicry Rendering Engine - React Container Extraction"
    )
    parser.add_argument(
        "--league",
        type=str,
        help="Filter by league name (e.g., 'Premier League')"
    )
    parser.add_argument(
        "--season",
        type=str,
        help="Filter by season (e.g., '23/24')"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of leagues to process"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run (no database updates)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of concurrent workers (default: 1)"
    )

    args = parser.parse_args()

    asyncio.run(main_async(
        limit=args.limit,
        league_filter=args.league,
        season_filter=args.season,
        dry_run=args.dry_run,
        max_workers=args.workers
    ))


if __name__ == "__main__":
    main()
