#!/usr/bin/env python3
"""
V54.6 最终 URL 嗅探器 - 增强版
================================

功能:
1. 访问 Results 页面并充分滚动触发懒加载
2. 提取比赛详情链接
3. 匹配数据库并更新

Author: Senior Data Crawler Architect
Version: V54.6 Final
Date: 2026-01-01
"""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

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

USER_DATA_DIR = Path(".playwright_stealth_profile")


async def final_sniff_and_update():
    """最终版 URL 嗅探并更新数据库"""

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
    logger.info("V54.6 最终 URL 嗅探器")
    logger.info("=" * 60)
    logger.info("")

    playwright = await async_playwright().start()

    browser_context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(USER_DATA_DIR),
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
        viewport={"width": 1920, "height": 1080},
    )

    stealth = Stealth()
    page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()
    await stealth.apply_stealth_async(page)

    try:
        # 访问主页
        logger.info("访问主页...")
        await page.goto("https://www.oddsportal.com", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # 访问 Results 页面
        target_url = "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"
        logger.info(f"访问 Results 页面...")
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        # 充分滚动触发所有懒加载
        logger.info("触发懒加载（滚动页面）...")
        for i in range(20):
            await page.evaluate("window.scrollBy(0, 300)")
            await asyncio.sleep(0.5)
        await asyncio.sleep(10)

        # 检查页面状态
        page_text = await page.evaluate("() => document.body.textContent")
        logger.info(f"页面文本长度: {len(page_text):,}")

        # 提取所有包含球队对阵的链接
        logger.info("提取比赛链接...")

        match_links = await page.evaluate("""
            () => {
                const results = [];
                const links = document.querySelectorAll('a[href]');

                links.forEach(link => {
                    const href = link.getAttribute('href');
                    const text = link.textContent.trim();

                    // 查找包含球队名的链接（格式: /football/.../team1-team2/ 或 team1-team2-xxxxx/）
                    if (href && href.includes('/football/')) {
                        // 检查是否是比赛详情页（包含两个球队名）
                        const matchPattern = /\\/([a-z-]+)-([a-z-]+)/;
                        if (matchPattern.test(href) && text.length < 100) {
                            results.push({
                                href: href,
                                text: text
                            });
                        }
                    }
                });

                return results;
            }
        """)

        logger.info(f"找到 {len(match_links)} 个链接")

        # 去重并解析
        unique_matches = {}
        for link in match_links:
            href = link["href"]

            # 构建完整 URL
            if href.startswith("/"):
                full_url = f"https://www.oddsportal.com{href}"
            else:
                full_url = href

            # 解析球队名
            # /football/england/premier-league-2023-2024/team1-team2-xxxxx/
            parts = href.split("/")
            if len(parts) >= 5:
                match_part = parts[-1].strip("/")  # 最后一部分: team1-team2-xxxxx

                # 提取加密 ID（如果有）
                id_match = re.search(r'-([a-zA-Z0-9]{3,})$', match_part)

                # 移除加密 ID，提取球队名
                teams_part = re.sub(r'-[a-zA-Z0-9]{3,}$', '', match_part)
                url_teams = teams_part.split("-")[:3]  # 取前 3 部分（可能有 2 或 3 个球队名）

                # 去重 key
                key = "-".join(url_teams[:2])  # 使用前两个球队名作为 key
                if key not in unique_matches:
                    unique_matches[key] = {
                        "url": full_url,
                        "teams": url_teams,
                        "has_id": id_match is not None
                    }

        logger.info(f"去重后: {len(unique_matches)} 场比赛")

        # 匹配数据库
        logger.info("匹配数据库...")
        cursor.execute("""
            SELECT DISTINCT m.match_id, m.home_team, m.away_team, m.league_name
            FROM matches m
            JOIN prematch_features pf ON m.match_id = pf.match_id
            WHERE m.league_name = 'Premier League'
              AND m.match_date >= '2023-08-01'
              AND m.match_date <= '2024-05-31'
            LIMIT 500
        """)

        db_matches = cursor.fetchall()
        logger.info(f"数据库中英超 23-24 赛季: {len(db_matches)} 场")

        # 模糊匹配
        updated = 0
        for db_match in db_matches:
            home_slug = db_match["home_team"].lower().replace(" ", "-")
            away_slug = db_match["away_team"].lower().replace(" ", "-")

            # 尝试多种匹配模式
            patterns = [
                f"{home_slug}-{away_slug}",
                f"{away_slug}-{home_slug}",
            ]

            for pattern in patterns:
                if pattern in unique_matches:
                    real_url = unique_matches[pattern]["url"]

                    # 更新数据库
                    cursor.execute("""
                        UPDATE prematch_features
                        SET source_url = %s,
                            is_processed = FALSE
                        WHERE match_id = %s
                    """, (real_url, db_match["match_id"]))

                    if cursor.rowcount > 0:
                        updated += 1
                        if updated <= 5:
                            logger.info(f"  ✓ {db_match['home_team']} vs {db_match['away_team']}")
                    break

        logger.info("")
        logger.info("=" * 60)
        logger.info("【嗅探完成】")
        logger.info("=" * 60)
        logger.info(f"提取链接: {len(match_links)}")
        logger.info(f"去重后: {len(unique_matches)}")
        logger.info(f"数据库匹配: {len(db_matches)}")
        logger.info(f"成功更新: {updated}")
        logger.info("=" * 60)

        # 保存报告
        report_path = Path("logs/debug_v54_6") / f"final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, "w") as f:
            f.write("V54.6 最终嗅探报告\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"提取链接: {len(match_links)}\n")
            f.write(f"去重后: {len(unique_matches)}\n")
            f.write(f"成功更新: {updated}\n\n")

            if unique_matches:
                f.write("提取的 URL 示例:\n")
                for i, (key, data) in enumerate(list(unique_matches.items())[:10]):
                    f.write(f"{i+1}. {key}\n")
                    f.write(f"   URL: {data['url']}\n")
                    f.write(f"   Teams: {data['teams']}\n")
                    f.write(f"   Has ID: {data['has_id']}\n\n")

        logger.info(f"\n报告已保存: {report_path}")

    except Exception as e:
        logger.error(f"出错: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await browser_context.close()
        await playwright.stop()
        cursor.close()
        conn.close()


if __name__ == "__main__":
    asyncio.run(final_sniff_and_update())
