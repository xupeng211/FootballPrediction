#!/usr/bin/env python3
import asyncio
import logging
import re
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def extract_match_rows_from_html(html_content: str):
    pattern = r'"/football/([^/]+)/([^/]+)-([^/]+)/([^/-]+)-([^/-]+)-([a-zA-Z0-9]{7,8})/"'
    matches = re.findall(pattern, html_content)
    return len(matches), matches


async def probe_with_enhanced_waiting():
    logger.info("=" * 60)
    logger.info("V80.0 Enhanced Pagination Probe")
    logger.info("=" * 60)

    url = "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)

            all_matches = []
            page_num = 1

            while page_num <= 10:
                logger.info(f"Page {page_num}")
                await asyncio.sleep(3)
                
                html = await page.content()
                count, matches = extract_match_rows_from_html(html)
                logger.info(f"  Extracted: {count} matches")

                if count == 0:
                    logger.info("  No matches, stopping")
                    break

                if all_matches and matches[0] == all_matches[0]:
                    logger.info("  Duplicate detected, last page")
                    break

                all_matches.extend(matches)

                try:
                    btn = await page.wait_for_selector('a.pagination-next', timeout=5000)
                    if btn:
                        await btn.click()
                        await asyncio.sleep(3)
                        page_num += 1
                except:
                    logger.info("  No Next button found")
                    break

            logger.info(f"Total pages: {page_num}")
            logger.info(f"Total matches: {len(all_matches)}")

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(probe_with_enhanced_waiting())
