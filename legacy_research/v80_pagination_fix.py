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


async def fixed_pagination_scan():
    logger.info("=" * 60)
    logger.info("V80.0 Fixed Pagination Scan")
    logger.info("=" * 60)

    url = "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)

            all_matches = []
            page_num = 1
            max_pages = 20

            while page_num <= max_pages:
                logger.info(f"--- Page {page_num} ---")

                # 等待页面加载
                await asyncio.sleep(2)

                html = await page.content()
                count, matches = extract_match_rows_from_html(html)
                logger.info(f"  Extracted: {count} matches")

                if count == 0:
                    logger.info("  No matches, stopping")
                    break

                # 检查重复
                if all_matches and matches == all_matches[-len(matches):]:
                    logger.info("  Duplicate detected, last page")
                    break

                all_matches.extend(matches)

                # 尝试点击 Next 按钮
                try:
                    # 方法1：直接查找 Next 链接
                    next_btn = await page.query_selector('div.pagination a:has-text("Next")')
                    if next_btn:
                        logger.info("  Found Next button (method 1)")
                        await next_btn.click()
                        await asyncio.sleep(2)
                        page_num += 1
                        continue

                    # 方法2：点击下一个数字页码
                    current_page_selector = f'div.pagination a:has-text("{page_num + 1}")'
                    next_page = await page.query_selector(current_page_selector)
                    if next_page:
                        logger.info(f"  Found page {page_num + 1}")
                        await next_page.click()
                        await asyncio.sleep(2)
                        page_num += 1
                        continue

                    logger.info("  No more pages")
                    break

                except Exception as e:
                    logger.info(f"  Error: {e}")
                    break

            logger.info(f"\n{'=' * 60}")
            logger.info(f"Scan Complete")
            logger.info(f"{'=' * 60}")
            logger.info(f"Total pages: {page_num}")
            logger.info(f"Total matches: {len(all_matches)}")
            logger.info(f"Expected: 380 (EPL)")
            logger.info(f"Coverage: {100 * len(all_matches) / 380:.1f}%")

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(fixed_pagination_scan())
