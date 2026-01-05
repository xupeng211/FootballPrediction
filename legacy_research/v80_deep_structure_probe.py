#!/usr/bin/env python3
import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


async def deep_structure_probe():
    logger.info("=" * 60)
    logger.info("V80.0 Deep Structure Probe")
    logger.info("=" * 60)

    url = "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={'width': 1920, 'height': 1080}
        )

        page = await context.new_page()

        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(5)

            # 检查页面结构
            logger.info("\n检查分页组件...")
            
            pagination_selectors = [
                'nav.pagination',
                'ul.pagination',
                'div.pagination',
                '[class*="pagination"]',
                '[class*="paging"]',
            ]

            for sel in pagination_selectors:
                elements = await page.query_selector_all(sel)
                if elements:
                    logger.info(f"  Found: {sel} ({len(elements)} elements)")
                    for elem in elements[:3]:
                        text = await elem.inner_text()
                        logger.info(f"    Text: {text[:100]}")

            # 检查表格行数
            logger.info("\n检查表格结构...")
            tables = await page.query_selector_all('table')
            logger.info(f"  Total tables: {len(tables)}")

            for i, table in enumerate(tables):
                rows = await table.query_selector_all('tr')
                logger.info(f"  Table {i}: {len(rows)} rows")

            # 检查是否有"加载更多"按钮
            logger.info("\n检查加载更多按钮...")
            load_more_selectors = [
                'button:has-text("Load")',
                'button:has-text("Show")',
                'button:has-text("More")',
                '[class*="load-more"]',
                '[class*="show-more"]',
            ]

            for sel in load_more_selectors:
                elements = await page.query_selector_all(sel)
                if elements:
                    logger.info(f"  Found: {sel}")

            # 尝试滚动到底部
            logger.info("\n尝试滚动到底部...")
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(5)

            html_after = await page.content()
            
            # 统计比赛链接数量
            import re
            pattern = r'"/football/[^/]+/[^/]+-[^/]+/[^/-]+-[^/-]+-[a-zA-Z0-9]{7,8}/"'
            matches_before = len(re.findall(pattern, await page.content()))
            
            # 等待
            await asyncio.sleep(5)
            
            matches_after = len(re.findall(pattern, await page.content()))
            
            logger.info(f"  Matches before scroll: {matches_before}")
            logger.info(f"  Matches after scroll: {matches_after}")

            # 保持浏览器打开 10 秒用于手动检查
            logger.info("\n浏览器保持打开 10 秒用于手动检查...")
            await asyncio.sleep(10)

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(deep_structure_probe())
