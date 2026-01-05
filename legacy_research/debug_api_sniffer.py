#!/usr/bin/env python3
"""V59.0 API Sniffer - Endpoint Discovery Tool.

This module captures and analyzes raw network traffic from OddsPortal to identify
the backend JSON endpoints containing opening odds and timestamp data.

Phase 1 of V59.0 API Interceptor Development:
    - Monitors XHR/Fetch requests for /ajax-match-odds/ or /feed/ patterns
    - Captures complete JSON responses for offline analysis
    - Identifies field names for opening_time/timestamp data

Usage:
    python scripts/debug_api_sniffer.py --match-url "https://www.oddsportal.com/match/..."

Output:
    Raw JSON samples saved to logs/api_samples/ for analysis
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Browser, Page, Response
from typer import Option, run

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/api_sniffer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

# Target URL patterns to sniff (扩大范围以捕获所有可能的 JSON)
TARGET_PATTERNS = [
    re.compile(r'/ajax-match-odds/', re.IGNORECASE),     # Primary: XHR odds data
    re.compile(r'/ajax.*odds', re.IGNORECASE),            # Fallback: ajax with odds
    re.compile(r'/feed.*odds', re.IGNORECASE),             # Fallback: feed with odds
    re.compile(r'/api/'),                                # Catch-all: any API call
]

# Output directory for captured samples
SAMPLES_DIR = Path("logs/api_samples")

# User-Agent to avoid detection
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class CapturedRequest:
    """Represents a captured network request/response pair."""
    timestamp: datetime
    method: str
    url: str
    status: int
    content_type: str
    response_size: int
    json_preview: dict | None
    has_odds_data: bool
    has_timestamp_data: bool
    entity_names: list[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d


@dataclass
class SniffReport:
    """Summary report of sniffing session."""
    total_requests: int
    captured_requests: int
    odds_api_calls: int
    unique_endpoints: set[str]
    captured_entities: set[str]
    timestamp_fields_found: list[str]
    opening_fields_found: list[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_requests": self.total_requests,
            "captured_requests": self.captured_requests,
            "odds_api_calls": self.odds_api_calls,
            "unique_endpoints": list(self.unique_endpoints),
            "captured_entities": list(self.captured_entities),
            "timestamp_fields_found": self.timestamp_fields_found,
            "opening_fields_found": self.opening_fields_found,
        }


# ============================================================================
# Main API Sniffer
# ============================================================================

class APISniffer:
    """Network traffic sniffer for API endpoint discovery.

    This class monitors browser network traffic to capture XHR/Fetch requests
    containing odds data. It filters responses by URL patterns and content
    characteristics to identify relevant API endpoints.

    Attributes:
        captured_requests: List of captured request/response pairs
        report: Session summary report
    """

    def __init__(self, samples_dir: Path = SAMPLES_DIR):
        """Initialize the sniffer.

        Args:
            samples_dir: Directory to save captured JSON samples
        """
        self.samples_dir = samples_dir
        self.captured_requests: list[CapturedRequest] = []
        self.report = SniffReport(
            total_requests=0,
            captured_requests=0,
            odds_api_calls=0,
            unique_endpoints=set(),
            captured_entities=set(),
            timestamp_fields_found=[],
            opening_fields_found=[]
        )

        # Create output directory
        self.samples_dir.mkdir(parents=True, exist_ok=True)

    def _should_capture(self, url: str) -> bool:
        """Check if URL matches target patterns.

        Args:
            url: Request URL to check

        Returns:
            True if URL should be captured
        """
        return any(pattern.search(url) for pattern in TARGET_PATTERNS)

    def _extract_entity_names(self, json_data: dict) -> list[str]:
        """Extract bookmaker entity names from JSON data.

        Searches for common entity codes like Entity_P, Entity_B3, etc.

        Args:
            json_data: Parsed JSON response

        Returns:
            List of found entity names
        """
        entities = []

        # Common entity patterns
        entity_patterns = [
            r'Entity_P', r'Entity_B3', r'Entity_WH', r'Entity_LB', r'Entity_AVG',
            r'Pinnacle', r'1xBet', r'William.?Hill', r'Ladbrokes',
            r'pinnacle', r'1xbet', r'williamhill', r'ladbrokes'
        ]

        json_str = json.dumps(json_data)

        for pattern in entity_patterns:
            if re.search(pattern, json_str, re.IGNORECASE):
                entities.append(pattern)

        return list(set(entities))

    def _find_timestamp_fields(self, json_data: dict) -> list[str]:
        """Identify fields containing timestamp data.

        Recursively searches JSON for fields with timestamp-like names or values.

        Args:
            json_data: Parsed JSON response

        Returns:
            List of field names containing timestamp data
        """
        timestamp_fields = []
        timestamp_keywords = [
            'timestamp', 'time', 'opening_time', 'opening', 'init_time',
            'created_at', 'updated_at', 'published_at', 'first_seen'
        ]

        def search_recursive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key

                    # Check if key looks like a timestamp field
                    if any(keyword in key.lower() for keyword in timestamp_keywords):
                        timestamp_fields.append(current_path)

                    # Check if value looks like a timestamp
                    if isinstance(value, (int, str)):
                        # Unix timestamp (seconds or milliseconds)
                        if isinstance(value, int) and 1000000000 < value < 9999999999999:
                            timestamp_fields.append(current_path)
                        # ISO format timestamp
                        if isinstance(value, str) and re.match(r'\d{4}-\d{2}-\d{2}', value):
                            timestamp_fields.append(current_path)

                    search_recursive(value, current_path)
            elif isinstance(obj, list) and obj:
                search_recursive(obj[0], path)

        search_recursive(json_data)
        return list(set(timestamp_fields))

    async def _handle_response(self, response: Response) -> None:
        """Handle network response event.

        Args:
            response: Playwright Response object
        """
        self.report.total_requests += 1

        try:
            url = response.url
            request = response.request

            # Check if URL matches target patterns
            if not self._should_capture(url):
                return

            # Only capture successful JSON responses
            content_type = await response.header_value('content-type') or ''
            if content_type and 'json' not in content_type.lower():
                return

            # Parse JSON response
            try:
                json_data = await response.json()
            except Exception:
                return

            self.report.captured_requests += 1
            self.report.odds_api_calls += 1

            # Extract metadata
            parsed_url = urlparse(url)
            endpoint = f"{parsed_url.path}?{parsed_url.query}"
            self.report.unique_endpoints.add(endpoint)

            # Extract entities and timestamp fields
            entities = self._extract_entity_names(json_data)
            timestamp_fields = self._find_timestamp_fields(json_data)

            self.report.captured_entities.update(entities)
            self.report.timestamp_fields_found.extend(
                [f for f in timestamp_fields if f not in self.report.timestamp_fields_found]
            )

            # Detect opening-related fields
            json_str = json.dumps(json_data)
            if re.search(r'opening', json_str, re.IGNORECASE):
                opening_fields = [k for k in json_data.keys() if 'opening' in k.lower()]
                self.report.opening_fields_found.extend(opening_fields)

            # Create captured request record
            captured = CapturedRequest(
                timestamp=datetime.now(),
                method=request.method,
                url=url,
                status=response.status,
                content_type=content_type,
                response_size=len(json.dumps(json_data)),
                json_preview=json_data,
                has_odds_data=len(entities) > 0,
                has_timestamp_data=len(timestamp_fields) > 0,
                entity_names=entities
            )
            self.captured_requests.append(captured)

            # Save raw JSON sample
            filename = (
                f"sample_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
                f"_{response.status}.json"
            )
            sample_path = self.samples_dir / filename

            with open(sample_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'metadata': captured.to_dict(),
                    'response_data': json_data
                }, f, indent=2, ensure_ascii=False)

            logger.info(f"✓ Captured: {response.status} {url}")
            logger.info(f"  Entities: {entities}")
            logger.info(f"  Timestamp fields: {timestamp_fields[:3]}...")  # Show first 3

        except Exception as e:
            logger.error(f"Error handling response: {e}")

    async def sniff_url(self, url: str, wait_seconds: int = 10) -> SniffReport:
        """Sniff network traffic from given URL.

        Args:
            url: URL to sniff
            wait_seconds: How long to wait for network traffic

        Returns:
            SniffReport containing session summary
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Visible for debugging
            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()

            # Attach response listener
            page.on('response', self._handle_response)

            logger.info(f"Navigating to: {url}")

            try:
                await page.goto(url, wait_until='networkidle', timeout=60000)
                logger.info(f"Waiting {wait_seconds}s for network traffic...")
                await asyncio.sleep(wait_seconds)

            except Exception as e:
                logger.error(f"Navigation error: {e}")
            finally:
                await browser.close()

        # Save sniffing report
        report_path = self.samples_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.report.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"\n{'='*60}")
        logger.info(f"Sniffing Report:")
        logger.info(f"  Total requests: {self.report.total_requests}")
        logger.info(f"  Captured: {self.report.captured_requests}")
        logger.info(f"  Odds API calls: {self.report.odds_api_calls}")
        logger.info(f"  Unique endpoints: {len(self.report.unique_endpoints)}")
        logger.info(f"  Entities found: {self.report.captured_entities}")
        logger.info(f"  Timestamp fields: {self.report.timestamp_fields_found[:5]}...")
        logger.info(f"  Opening fields: {self.report.opening_fields_found[:5]}...")
        logger.info(f"{'='*60}\n")

        return self.report


# ============================================================================
# CLI Entry Point
# ============================================================================

def main(
    match_url: str = Option(..., "--match-url", "-u", help="OddsPortal match URL to sniff"),
    wait_seconds: int = Option(10, "--wait", "-w", help="Seconds to wait for network traffic"),
    samples_dir: str = Option("logs/api_samples", "--output", "-o", help="Output directory for samples")
) -> None:
    """Run API sniffer on given match URL.

    Example:
        python scripts/debug_api_sniffer.py \\
            --match-url "https://www.oddsportal.com/soccer/england/premier-league/arsenal-chelsea/" \\
            --wait 15
    """
    # Configure output directory
    samples_path = Path(samples_dir)
    samples_path.mkdir(parents=True, exist_ok=True)

    # Create sniffer and run
    sniffer = APISniffer(samples_dir=samples_path)

    logger.info("="*60)
    logger.info("V59.0 API Sniffer - Endpoint Discovery Tool")
    logger.info("="*60)
    logger.info(f"Target URL: {match_url}")
    logger.info(f"Output directory: {samples_path.absolute()}")
    logger.info(f"Wait time: {wait_seconds}s")
    logger.info("="*60 + "\n")

    report = asyncio.run(sniffer.sniff_url(match_url, wait_seconds))

    logger.info(f"\nSamples saved to: {samples_path.absolute()}")
    logger.info("Next step: Analyze captured JSON to identify field names")


if __name__ == "__main__":
    run(main)
