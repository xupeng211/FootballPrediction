#!/usr/bin/env python3
"""
V54.8 批量 URL 修复工具 - 从 HTML 提取链接并更新数据库
======================================================

Author: V54.8
Date: 2026-01-01
"""

import asyncio
import logging
import re
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


async def batch_update_urls():
    """批量提取 URL 并更新数据库"""

    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    conn.autocommit = True
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    logger.info("")
    logger.info("=" * 60)
    logger.info("V54.8 批量 URL 修复工具")
    logger.info("=" * 60)
    logger.info("")

    # 启动浏览器
    p = await async_playwright().start()
    ctx = await p.chromium.launch_persistent_context(
        user_data_dir=str(Path('.playwright_stealth_profile')),
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )
    stealth = Stealth()
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    await stealth.apply_stealth_async(page)

    # 访问页面
    logger.info("访问 Results 页面...")
    await page.goto("https://www.oddsportal.com", timeout=60000)
    await asyncio.sleep(5)
    await page.goto("https://www.oddsportal.com/football/england/premier-league-2023-2024/results/",
                    timeout=90000, wait_until="domcontentloaded")
    await asyncio.sleep(8)

    logger.info("滚动触发加载...")
    for i in range(30):
        await page.evaluate("window.scrollBy(0, 400)")
        await asyncio.sleep(0.4)
    await asyncio.sleep(15)

    # 获取 HTML 并提取链接
    html = await page.content()
    await ctx.close()
    await p.stop()

    logger.info(f"HTML 大小: {len(html):,} 字节")

    # 提取所有比赛链接
    pattern = r'href=\"(/football/england/premier-league-2023-2024/[a-z0-9-]+-[a-zA-Z0-9]{8}/)\"'
    match_links = re.findall(pattern, html)

    logger.info(f"提取链接: {len(match_links)} 个")

    # 解析链接
    url_map = {}
    for link in match_links:
        # /football/england/premier-league-2023-2024/team1-team2-xxxxx/
        parts = link.strip("/").split("/")
        if len(parts) >= 4:
            match_part = parts[3]  # team1-team2-xxxxx

            # 移除加密 ID (8 位字母数字)
            teams_part = re.sub(r'-[a-zA-Z0-9]{8}$', '', match_part)

            # 构建完整 URL
            full_url = f"https://www.oddsportal.com{link}"

            # 直接使用 teams_part 作为 key
            url_map[teams_part] = full_url

    logger.info(f"解析后唯一 URL: {len(url_map)} 个")

    # 获取数据库中的比赛
    logger.info("查询数据库...")
    cursor.execute("""
        SELECT m.match_id, m.home_team, m.away_team, m.league_name
        FROM matches m
        JOIN prematch_features pf ON m.match_id = pf.match_id
        WHERE m.league_name = 'Premier League'
          AND m.match_date >= '2023-08-01'
          AND m.match_date <= '2024-05-31'
        ORDER BY m.match_date
    """)

    db_matches = cursor.fetchall()
    logger.info(f"数据库英超 23-24: {len(db_matches)} 场")

    # 匹配并更新
    updated = 0
    for match in db_matches:
        match_id = match["match_id"]
        home_team = match["home_team"]
        away_team = match["away_team"]

        # 构建搜索 key
        home_slug = home_team.lower().replace(" ", "-").replace(".", "")
        away_slug = away_team.lower().replace(" ", "-").replace(".", "")

        patterns = [
            f"{home_slug}-{away_slug}",
            f"{away_slug}-{home_slug}",
        ]

        for pattern in patterns:
            if pattern in url_map:
                real_url = url_map[pattern]

                cursor.execute("""
                    UPDATE prematch_features
                    SET source_url = %s,
                        is_processed = FALSE
                    WHERE match_id = %s
                """, (real_url, match_id))

                if cursor.rowcount > 0:
                    updated += 1
                    if updated <= 10:
                        logger.info(f"✓ {home_team} vs {away_team}")
                        logger.info(f"  {real_url}")
                break

    logger.info("")
    logger.info("=" * 60)
    logger.info("【批量更新完成】")
    logger.info("=" * 60)
    logger.info(f"总匹配: {updated} 场")
    logger.info("=" * 60)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    asyncio.run(batch_update_urls())
