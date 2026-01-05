#!/usr/bin/env python3
"""V121.0 复活测试 - 针对 Match ID 4514070 (Nantes vs Le Havre).

Goal: 验证 V121.0 天眼搜索引擎能否找到 2024 年法甲比赛。

Usage:
    python scripts/v121_resurrection_test.py
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote, urljoin

from playwright.async_api import async_playwright, Page
from thefuzz import fuzz

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.text_processor import TeamNameNormalizer

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """复活测试主函数."""
    logger.info("=" * 80)
    logger.info("V121.0 复活测试 - Nantes vs Le Havre (2024-11-24)")
    logger.info("=" * 80)

    # 目标比赛信息
    home_team = "Nantes"
    away_team = "Le Havre"
    match_date = datetime(2024, 11, 24, 16, 0, 0)

    logger.info(f"\n目标比赛:")
    logger.info(f"  对阵: {home_team} vs {away_team}")
    logger.info(f"  日期: {match_date}")
    logger.info(f"  联赛: Ligue 1 (法甲)")
    logger.info("")

    base_url = "https://www.oddsportal.com"
    normalizer = TeamNameNormalizer()
    result_url = None  # 初始化

    # 规范化球队名
    home_core = normalizer.normalize(home_team)
    away_core = normalizer.normalize(away_team)

    logger.info(f"规范化球队名:")
    logger.info(f"  Home: {home_team} -> {home_core}")
    logger.info(f"  Away: {away_team} -> {away_core}")
    logger.info("")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        # 测试 1: 直接搜索
        search_query = f"{home_core} {away_core}"
        search_url = f"{base_url}/search/{quote(search_query)}/"

        logger.info(f"测试 1: 直接搜索")
        logger.info(f"  URL: {search_url}")

        try:
            # 使用 networkidle 等待所有网络请求完成
            await page.goto(search_url, timeout=60000, wait_until="networkidle")
            await asyncio.sleep(5)  # 额外等待 JavaScript 渲染

            current_url = page.url
            logger.info(f"  当前 URL: {current_url}")

            # 获取页面标题
            title = await page.title()
            logger.info(f"  页面标题: {title}")

            # 截图保存（调试用）
            await page.screenshot(path="logs/search_page_debug.png")
            logger.info(f"  已保存截图: logs/search_page_debug.png")

            # 获取完整的 HTML 内容
            html_content = await page.content()
            logger.info(f"  HTML 长度: {len(html_content)} 字符")

            # 检查是否有"No results"或类似消息
            page_text = await page.evaluate("() => document.body.innerText")
            if "no result" in page_text.lower() or "not found" in page_text.lower():
                logger.info(f"  ❌ 页面显示无结果")

            # 尝试所有可能的链接
            all_links = await page.query_selector_all("a[href]")
            logger.info(f"  总共找到 {len(all_links)} 个链接")

            # 显示前 20 个链接以调试
            match_count = 0
            for i, link in enumerate(all_links[:30]):
                href = await link.get_attribute("href")
                text = await link.text_content()

                if not text:
                    continue

                # 只显示包含球队名的链接
                if any(name in text.lower() for name in ["nantes", "havre"]):
                    logger.info(f"  [{match_count+1}] {text[:80]}")
                    logger.info(f"       -> {href}")

                    # 检查是否是比赛链接
                    if "/match/" in href:
                        logger.info(f"  ✅ 找到比赛链接！")
                        result_url = urljoin(base_url, href)
                        break

                    match_count += 1

            if not result_url:
                # 检查 /football/ 链接
                football_links = await page.query_selector_all("a[href*='/football/']")
                logger.info(f"  找到 {len(football_links)} 个 /football/ 链接")

                for link in football_links[:15]:
                    href = await link.get_attribute("href")
                    text = await link.text_content()

                    if text and any(name in text.lower() for name in ["nantes", "havre"]):
                        logger.info(f"  足球链接: {text[:60]} -> {href}")

                        # 尝试访问这个链接
                        logger.info(f"  -> 尝试访问此链接...")
                        await page.goto(urljoin(base_url, href), timeout=30000, wait_until="domcontentloaded")
                        await asyncio.sleep(2)

                        # 检查新页面是否有 /match/ 链接
                        match_links = await page.query_selector_all("a[href*='/match/']")
                        logger.info(f"     找到 {len(match_links)} 个比赛链接")

                        if match_links:
                            for ml in match_links[:5]:
                                ml_href = await ml.get_attribute("href")
                                ml_text = await ml.text_content()
                                logger.info(f"       - {ml_text[:50]} -> {ml_href}")

                                # 检查相似度
                                if ml_text:
                                    text_core = normalizer.normalize(ml_text)
                                    home_sim = fuzz.partial_ratio(home_core, text_core)
                                    away_sim = fuzz.partial_ratio(away_core, text_core)

                                    if home_sim >= 60 and away_sim >= 60:
                                        result_url = urljoin(base_url, ml_href)
                                        logger.info(f"  ✅ 找到匹配！")
                                        break

                            if result_url:
                                break

                        # 回到搜索页面
                        await page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                        await asyncio.sleep(2)

                if not result_url:
                    result_url = None

        except Exception as e:
            logger.error(f"  ❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            result_url = None

        logger.info("")
        logger.info("=" * 80)
        logger.info("V121.0 复活测试结果")
        logger.info("=" * 80)

        if result_url:
            logger.info(f"✅ 成功: {result_url}")
        else:
            logger.error("❌ 未找到比赛")
            logger.info("")
            logger.info("可能原因:")
            logger.info("  1. OddsPortal 上没有这场比赛")
            logger.info("  2. 比赛日期不匹配")
            logger.info("  3. 球队名译名差异过大")

        logger.info("=" * 80)

        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
