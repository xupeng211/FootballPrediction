#!/usr/bin/env python3
"""
V54.6 真实 URL 嗅探器 - Results 页面扫描
==========================================

功能:
1. 访问赛季 Results 页面（使用 Stealth 模式）
2. 提取带加密 ID 的完整详情页 URL
3. 解析球队名并匹配到数据库 match_id
4. 批量修复数据库 source_url

Author: Senior Data Crawler Architect
Version: V54.6
Date: 2026-01-01
"""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# 持久化上下文目录
USER_DATA_DIR = Path(".playwright_stealth_profile")
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)


def fuzzy_match_teams(url_teams: list[str], cursor) -> dict[str, str]:
    """
    从 URL 解析的球队名模糊匹配数据库

    Args:
        url_teams: URL 中的球队名列表 (如 ["manchester-city", "brentford"])

    Returns:
        {match_id: {"home": str, "away": str, "league": str}}
    """
    matches = {}

    # 构建模糊匹配查询
    for url_team in url_teams:
        # URL 格式: manchester-city -> 数据库: Manchester City
        display_name = url_team.replace("-", " ").title()

        cursor.execute("""
            SELECT DISTINCT m.match_id, m.home_team, m.away_team, m.league_name
            FROM matches m
            JOIN prematch_features pf ON m.match_id = pf.match_id
            WHERE m.home_team ILIKE %s
               OR m.away_team ILIKE %s
            LIMIT 50
        """, (f"%{display_name}%", f"%{display_name}%"))

        for row in cursor.fetchall():
            match_id = row["match_id"]
            if match_id not in matches:
                matches[match_id] = {
                    "home": row["home_team"],
                    "away": row["away_team"],
                    "league": row["league_name"],
                }

    return matches


async def sniff_results_page():
    """嗅探 Results 页面并提取真实 URL"""

    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    conn.autocommit = True
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    logger.info("")
    logger.info("=" * 60)
    logger.info("V54.6 真实 URL 嗅探器启动")
    logger.info("=" * 60)
    logger.info("")

    # 目标赛季页面
    target_url = "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"

    logger.info(f"目标赛季: Premier League 2023-2024")
    logger.info(f"目标 URL: {target_url}")
    logger.info("")

    # 启动 Stealth 浏览器
    playwright = await async_playwright().start()

    browser_context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(USER_DATA_DIR),
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
        ],
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    )

    stealth = Stealth()
    page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()
    await stealth.apply_stealth_async(page)

    try:
        # 步骤 1: 访问主页建立会话
        logger.info("步骤 1: 访问 OddsPortal 主页...")
        await page.goto("https://www.oddsportal.com", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        logger.info("  ✓ 主页访问成功")

        # 步骤 2: 访问 Results 页面
        logger.info("")
        logger.info("步骤 2: 访问赛季 Results 页面...")
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        # 检查页面状态
        page_html = await page.content()
        page_title = await page.title()

        logger.info(f"  页面标题: {page_title}")
        logger.info(f"  HTML 长度: {len(page_html):,} 字节")

        if len(page_html) < 10000:
            logger.warning("  ✗ 页面内容过少，可能被拦截")
            return

        logger.info("  ✓ Results 页面加载成功")

        # 步骤 3: 提取所有比赛链接
        logger.info("")
        logger.info("步骤 3: 提取带加密 ID 的比赛链接...")

        # JavaScript 提取所有比赛详情链接
        match_links = await page.evaluate("""
            () => {
                const results = [];

                // 查找所有指向比赛详情页的链接
                const links = document.querySelectorAll('a[href*="/football/"]');

                links.forEach(link => {
                    const href = link.getAttribute('href');
                    const text = link.textContent.trim();

                    // 过滤: 必须包含完整的比赛路径格式
                    // /football/england/premier-league/team1-team2-xxxxx/
                    if (href && href.includes('/football/') &&
                        href.match(/-\\w{3,}\\/$/) &&  // 以 -xxx/ 结尾（加密 ID）
                        text.length > 5 && text.length < 100) {

                        results.push({
                            href: href,
                            text: text
                        });
                    }
                });

                return results;
            }
        """)

        logger.info(f"  找到 {len(match_links)} 个潜在链接")

        # 步骤 4: 解析并去重
        logger.info("")
        logger.info("步骤 4: 解析 URL 并去重...")

        unique_urls = {}
        for link in match_links:
            href = link["href"]

            # 确保是完整 URL
            if href.startswith("/"):
                full_url = f"https://www.oddsportal.com{href}"
            else:
                full_url = href

            # 解析球队名
            # /football/england/premier-league/team1-team2-xxxxx/
            parts = href.split("/")
            if len(parts) >= 5:
                # parts[4] = "team1-team2-xxxxx"
                match_part = parts[4]

                # 提取加密 ID（最后一部分）
                id_match = re.search(r'-([a-zA-Z0-9]{3,})/$', match_part)
                if id_match:
                    encrypted_id = id_match.group(1)

                    # 提取球队名（移除加密 ID）
                    teams_part = match_part.rsplit('-', 1)[0]  # 移除最后的 -xxxxx
                    url_teams = teams_part.split('-')[:2]  # 取前两部分

                    # 存储唯一 URL
                    key = f"{url_teams[0]}-{url_teams[1]}"
                    if key not in unique_urls:
                        unique_urls[key] = {
                            "url": full_url,
                            "teams": url_teams,
                            "encrypted_id": encrypted_id,
                        }

        logger.info(f"  去重后: {len(unique_urls)} 场比赛")

        # 步骤 5: 匹配数据库
        logger.info("")
        logger.info("步骤 5: 匹配数据库 match_id...")

        all_url_teams = []
        for key, data in unique_urls.items():
            all_url_teams.extend(data["teams"])

        # 去重球队名
        all_url_teams = list(set(all_url_teams))
        logger.info(f"  待匹配球队: {len(all_url_teams)} 支")

        # 批量模糊匹配
        match_map = fuzzy_match_teams(all_url_teams, cursor)
        logger.info(f"  找到匹配: {len(match_map)} 场比赛")

        # 步骤 6: 更新数据库
        logger.info("")
        logger.info("步骤 6: 更新数据库 source_url...")

        updated_count = 0
        for match_id, match_info in match_map.items():
            # 构建对应的 URL key
            home_slug = match_info["home"].lower().replace(" ", "-").replace(".", "")
            away_slug = match_info["away"].lower().replace(" ", "-").replace(".", "")
            key = f"{home_slug}-{away_slug}"

            if key in unique_urls:
                real_url = unique_urls[key]["url"]

                # 更新数据库
                cursor.execute("""
                    UPDATE prematch_features
                    SET source_url = %s,
                        is_processed = FALSE
                    WHERE match_id = %s
                """, (real_url, match_id))

                if cursor.rowcount > 0:
                    updated_count += 1
                    if updated_count <= 5:  # 只显示前 5 个
                        logger.info(f"  ✓ {match_info['home']} vs {match_info['away']}")
                        logger.info(f"    URL: ...{real_url[-60:]}")

        logger.info("")
        logger.info("=" * 60)
        logger.info("【V54.6 嗅探任务完成】")
        logger.info("=" * 60)
        logger.info(f"总扫描链接: {len(match_links)}")
        logger.info(f"去重后比赛: {len(unique_urls)}")
        logger.info(f"数据库匹配: {len(match_map)}")
        logger.info(f"成功更新: {updated_count}")
        logger.info("=" * 60)

        # 保存嗅探报告
        report_path = Path("logs/debug_v54_6") / f"sniff_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("V54.6 URL 嗅探报告\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"目标赛季: Premier League 2023-2024\n")
            f.write(f"扫描时间: {datetime.now()}\n\n")
            f.write(f"总扫描链接: {len(match_links)}\n")
            f.write(f"去重后比赛: {len(unique_urls)}\n")
            f.write(f"数据库匹配: {len(match_map)}\n")
            f.write(f"成功更新: {updated_count}\n\n")
            f.write("更新的 URL 示例:\n")
            f.write("-" * 60 + "\n")

            for match_id, match_info in list(match_map.items())[:10]:
                home_slug = match_info["home"].lower().replace(" ", "-").replace(".", "")
                away_slug = match_info["away"].lower().replace(" ", "-").replace(".", "")
                key = f"{home_slug}-{away_slug}"
                if key in unique_urls:
                    f.write(f"{match_info['home']} vs {match_info['away']}\n")
                    f.write(f"  {unique_urls[key]['url']}\n\n")

        logger.info(f"\n报告已保存: {report_path}")

    except Exception as e:
        logger.error(f"嗅探过程出错: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await browser_context.close()
        await playwright.stop()
        cursor.close()
        conn.close()
        logger.info("")
        logger.info("浏览器已关闭，数据库连接已释放")


if __name__ == "__main__":
    asyncio.run(sniff_results_page())
