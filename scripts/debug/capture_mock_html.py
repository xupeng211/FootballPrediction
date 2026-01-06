#!/usr/bin/env python3
"""V142.4: Capture HTML mock data for testing.

This script captures the raw HTML from OddsPortal results page
for use in offline testing.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from src.api.collectors.base_extractor import BaseExtractor


async def capture_html():
    """Capture HTML from OddsPortal Premier League results page."""
    url = "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"
    output_path = Path("tests/mocks/premier_league_results.html")

    print(f"📸 Capturing HTML from: {url}")
    print(f"📁 Output: {output_path}")

    async with async_playwright() as pw:
        # Use BaseExtractor for proxy and stealth
        extractor = BaseExtractor(enable_ghost_protocol=True, auto_proxy=True)

        browser = await pw.chromium.launch(
            headless=True,
            proxy=extractor.get_proxy_config(),
        )

        # Create context with Ghost Protocol
        context, page = await extractor.create_ghost_context(browser)

        try:
            # Navigate to results page
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Wait for page to load
            await asyncio.sleep(5)

            # Get HTML content
            html = await page.content()

            # Save to file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html, encoding="utf-8")

            print(f"✅ Captured {len(html)} bytes")
            print(f"✅ Saved to: {output_path}")

        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    asyncio.run(capture_html())
