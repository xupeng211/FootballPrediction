#!/usr/bin/env python3
"""V121.0 直接 URL 测试 - 尝试多种 URL 格式."""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("=" * 80)
    logger.info("V121.0 直接 URL 测试")
    logger.info("=" * 80)

    base_url = "https://www.oddsportal.com"

    # 尝试多种 URL 格式
    url_patterns = [
        # 格式 1: /football/league-season/home-away/ (新格式)
        "/football/france/ligue-1-2024-2025/nantes-le-havre/",

        # 格式 2: /match/xxx/ (带 ID)
        "/match/nantes-le-havre/",

        # 格式 3: 搜索页面
        "/search/nantes le havre/",

        # 格式 4: 档案页
        "/football/2024/11/24/",
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        for i, pattern in enumerate(url_patterns):
            full_url = urljoin(base_url, pattern)
            logger.info(f"\n测试 [{i+1}]: {full_url}")

            try:
                await page.goto(full_url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(3)

                # 检查页面内容
                title = await page.title()
                logger.info(f"  标题: {title}")

                # 查找比赛链接
                match_links = await page.query_selector_all("a[href*='/match/']")
                logger.info(f"  找到 {len(match_links)} 个 /match/ 链接")

                if len(match_links) > 0:
                    # 显示前 5 个
                    for j, link in enumerate(match_links[:5]):
                        href = await link.get_attribute("href")
                        text = await link.text_content()
                        logger.info(f"    [{j+1}] {text[:50] if text else '(empty)'} -> {href}")

                    # 检查是否找到目标比赛
                    for link in match_links:
                        text = await link.text_content()
                        if text and any(name in text.lower() for name in ["nantes", "havre"]):
                            logger.info(f"  ✅ 找到匹配: {text}")
                            logger.info(f"  URL: {urljoin(base_url, await link.get_attribute('href'))}")
                            break

            except Exception as e:
                logger.error(f"  ❌ 错误: {e}")

        await context.close()
        await browser.close()

    logger.info("\n" + "=" * 80)
    logger.info("测试完成")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
