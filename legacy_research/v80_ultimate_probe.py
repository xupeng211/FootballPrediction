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


async def ultimate_probe():
    logger.info("=" * 60)
    logger.info("V80.0 Ultimate Probe - Extended Wait")
    logger.info("=" * 60)

    url = "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 非无头模式便于观察
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)

            all_matches = []
            page_num = 1
            max_pages = 15

            while page_num <= max_pages:
                logger.info(f"\n=== Page {page_num} ===")

                # 等待比赛数据加载
                await asyncio.sleep(5)  # 初始等待

                # 尝试多次提取
                for attempt in range(3):
                    html = await page.content()
                    count, matches = extract_match_rows_from_html(html)
                    logger.info(f"  Attempt {attempt + 1}: {count} matches")
                    
                    if count > 0:
                        break
                    
                    if attempt < 2:
                        await asyncio.sleep(3)

                if count == 0:
                    logger.info("  No matches after retries, stopping")
                    break

                all_matches.extend(matches)

                # 点击下一页
                try:
                    # 查找 Next 按钮并点击
                    next_btn = await page.query_selector('div.pagination a:has-text("Next")')
                    if next_btn:
                        logger.info(f"  Clicking Next...")
                        await next_btn.click()
                        
                        # 等待导航和页面更新
                        await page.wait_for_load_state('domcontentloaded', timeout=30000)
                        await asyncio.sleep(5)
                        page_num += 1
                    else:
                        logger.info("  No Next button found")
                        break

                except Exception as e:
                    logger.info(f"  Error: {e}")
                    break

            logger.info(f"\n{'=' * 60}")
            logger.info(f"Final Results")
            logger.info(f"{'=' * 60}")
            logger.info(f"Pages scanned: {page_num}")
            logger.info(f"Total matches: {len(all_matches)}")
            logger.info(f"Expected: 380")
            logger.info(f"Coverage: {100 * len(all_matches) / 380:.1f}%")

            # 显示前 10 条
            if all_matches:
                logger.info(f"\nFirst 10 matches:")
                for i, match in enumerate(all_matches[:10]):
                    logger.info(f"  {i + 1}. {match[3]} vs {match[4]} (hash: {match[5]})")

            # 保持浏览器打开 5 秒
            await asyncio.sleep(5)

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(ultimate_probe())
