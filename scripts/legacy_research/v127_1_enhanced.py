#!/usr/bin/env python3
"""V127.1 增强版 - 多 URL 格式尝试 + 增强反检测."""

import asyncio
import logging
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                  'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY']:
    os.environ.pop(proxy_var, None)

import psycopg2
from playwright.async_api import async_playwright, Page
from thefuzz import fuzz

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings
from src.utils.text_processor import TeamNameNormalizer

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.oddsportal.com"

# 增强版浏览器配置
STEALTH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

STEALTH_BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--disable-dev-shm-usage",
    "--disable-setuid-sandbox",
    "--no-sandbox",
    "--disable-web-security",
    "--disable-features=VizDisplayCompositor",
    "--disable-gpu",
]


async def test_url_format(
    page: Page,
    league_name: str,
    season: str
) -> str | None:
    """测试多种 URL 格式，找到有效的那个."""

    # 多种可能的 URL 格式
    url_formats = [
        # 格式 1: 完整年份 2023-2024
        f"{BASE_URL}/football/england/premier-league-2023-2024/results/",
        # 格式 2: 压缩年份 2324
        f"{BASE_URL}/football/england/premier-league-2324/results/",
        # 格式 3: 带斜杠 23/24
        f"{BASE_URL}/football/england/premier-league-23/24/results/",
        # 格式 4: 不带 results
        f"{BASE_URL}/football/england/premier-league-2023-2024/",
        # 格式 5: 使用 archive
        f"{BASE_URL}/football/england/premier-league-2023-2024/archive/",
    ]

    logger.info(f"  🔍 测试 {len(url_formats)} 种 URL 格式...")

    for i, url in enumerate(url_formats, 1):
        logger.info(f"    [{i}/{len(url_formats)}] {url}")

        try:
            # 使用较短的超时时间
            response = await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            status = response.status

            if status == 200:
                # 检查页面标题
                title = await page.title()
                logger.info(f"       ✅ 状态: {status}, 标题: {title[:60]}")

                # 检查是否有 match 链接
                try:
                    await page.wait_for_selector("a[href*='/match/']", timeout=10000)
                    logger.info(f"       ✅ 找到 match 链接!")
                    return url
                except:
                    logger.info(f"       ⚠️  无 match 链接，继续尝试...")

            elif status == 404:
                logger.info(f"       ❌ 404 Not Found")
            else:
                logger.info(f"       ⚠️  状态: {status}")

        except Exception as e:
            logger.info(f"       ❌ 错误: {str(e)[:50]}")

        # 短暂延迟
        await asyncio.sleep(1)

    logger.warning(f"  ❌ 所有 URL 格式都失败了")
    return None


async def extract_match_links_from_page(
    page: Page,
    max_links: int = 500
) -> list[dict[str, Any]]:
    """从页面提取 match 链接."""
    logger.info(f"  🎯 提取 match 链接（最多 {max_links} 个）...")

    try:
        # 滚动触发懒加载
        logger.info(f"  📜 滚动触发懒加载...")
        for i in range(30):
            await page.mouse.wheel(0, 600)
            await asyncio.sleep(0.3)

        # 等待 DOM 稳定
        await asyncio.sleep(5)

        # 提取所有 match 链接
        logger.info(f"  🔍 提取链接...")
        match_data = await page.evaluate(f"""() => {{
            const links = document.querySelectorAll('a[href*="/match/"]');
            const results = [];
            const seen = new Set();

            for (const link of links) {{
                const href = link.href;
                const text = link.textContent?.trim() || '';

                // 提取哈希值
                const hashMatch = href.match(/([a-z0-9]{{8}})/);
                const hash = hashMatch ? hashMatch[1] : null;

                // 只保留带哈希的链接，并去重
                if (hash && !seen.has(hash) && results.length < {max_links}) {{
                    seen.add(hash);
                    results.push({{
                        url: href,
                        text: text,
                        hash: hash
                    }});
                }}
            }}

            return results;
        }}""")

        logger.info(f"  ✅ 提取到 {len(match_data)} 个唯一链接")

        return match_data

    except Exception as e:
        logger.error(f"  ❌ 提取失败: {e}")
        return []


def get_pending_matches(conn, league_name: str, season: str) -> list[dict[str, Any]]:
    """获取待处理比赛."""
    # 支持多种赛季格式
    possible_seasons = [season]
    if "/" in season:
        parts = season.split("/")
        if len(parts) == 2:
            possible_seasons.append(f"20{parts[0]}-20{parts[1]}")
            possible_seasons.append(f"{parts[0]}{parts[1]}")

    season_placeholders = ",".join(["%s"] * len(possible_seasons))
    query = f"""
        SELECT match_id, home_team, away_team, match_date
        FROM matches
        WHERE league_name = %s
          AND (season IN ({season_placeholders}) OR season IS NULL)
          AND oddsportal_url IS NULL
        ORDER BY match_date DESC;
    """

    with conn.cursor() as cur:
        cur.execute(query, [league_name] + possible_seasons)
        rows = cur.fetchall()

    return [
        {"match_id": r[0], "home_team": r[1], "away_team": r[2], "match_date": r[3]}
        for r in rows
    ]


def fuzzy_match_and_update(
    conn,
    extracted_matches: list[dict[str, Any]],
    db_matches: list[dict[str, Any]],
    normalizer: TeamNameNormalizer,
    dry_run: bool = False
) -> int:
    """模糊匹配并更新数据库."""
    updates = []

    for db_match in db_matches:
        match_id = db_match["match_id"]
        home_team = normalizer.normalize(db_match["home_team"])
        away_team = normalizer.normalize(db_match["away_team"])

        best_match = None
        best_score = 0

        for extracted in extracted_matches:
            text = extracted.get('text', '')
            normalized = normalizer.normalize(text)

            # 尝试多种分割方式
            separators = [' - ', ' v ', ' vs ', ' @ ']
            for sep in separators:
                if sep in normalized:
                    parts = normalized.split(sep)
                    if len(parts) == 2:
                        ext_home, ext_away = parts[0].strip(), parts[1].strip()

                        home_sim = fuzz.partial_ratio(home_team, ext_home)
                        away_sim = fuzz.partial_ratio(away_team, ext_away)

                        if home_sim >= 65 and away_sim >= 65:
                            avg_score = (home_sim + away_sim) / 2
                            if avg_score > best_score:
                                best_score = avg_score
                                best_match = extracted
                                # logger.info(f"    匹配: {db_match['home_team']} vs {db_match['away_team']} -> {text[:40]} (相似度: {avg_score:.1f}%)")
                            break

        if best_match:
            updates.append((match_id, best_match['url']))

    # 批量更新
    if updates and not dry_run:
        update_query = """
            UPDATE matches
            SET oddsportal_url = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE match_id = %s;
        """

        with conn.cursor() as cur:
            for match_id, url in updates:
                try:
                    cur.execute(update_query, (url, match_id))
                except Exception as e:
                    logger.error(f"    ❌ 更新失败 {match_id}: {e}")

            conn.commit()

    return len(updates)


async def main_async(
    league: str = "Premier League",
    season: str = "23/24",
    dry_run: bool = False,
) -> None:
    """V127.1 主函数."""
    logger.info("=" * 80)
    logger.info("V127.1 增强版 - 多 URL 格式尝试")
    logger.info("=" * 80)

    settings = get_settings()
    normalizer = TeamNameNormalizer()

    # 连接数据库
    logger.info("\n📡 连接数据库...")
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )

    # 获取待处理比赛
    db_matches = get_pending_matches(conn, league, season)
    logger.info(f"  ✅ 找到 {len(db_matches)} 个待处理比赛")

    if not db_matches:
        logger.info("  ⏭️  无待处理比赛")
        conn.close()
        return

    # 显示前 10 个待处理比赛
    logger.info("\n  📋 待处理比赛（前 10 个）:")
    for i, m in enumerate(db_matches[:10], 1):
        logger.info(f"     [{i}] {m['home_team']} vs {m['away_team']} - {m['match_date']}")

    # 启动浏览器
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=STEALTH_BROWSER_ARGS
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=STEALTH_USER_AGENT,
            locale="en-US",
            timezone_id="America/New_York",
        )

        # 隐身脚本
        stealth_script = """() => {
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = {
                runtime: {}
            };
        }"""

        page = await context.new_page()
        await page.add_init_script(stealth_script)

        # V127.1: 测试多种 URL 格式
        working_url = await test_url_format(page, league, season)

        if not working_url:
            logger.error("\n❌ 无法找到有效的 URL 格式")
            await context.close()
            await browser.close()
            conn.close()
            return

        logger.info(f"\n✅ 使用 URL: {working_url}")

        # 提取 match 链接
        extracted_matches = await extract_match_links_from_page(page, max_links=500)

        if not extracted_matches:
            logger.error("\n❌ 未提取到 match 链接")
            await context.close()
            await browser.close()
            conn.close()
            return

        # 显示提取的链接
        logger.info(f"\n  📋 提取的链接（前 20 个）:")
        for i, m in enumerate(extracted_matches[:20], 1):
            logger.info(f"     [{i:2d}] {m['hash']} -> {m['text'][:50]}")

        # 模糊匹配并更新
        logger.info(f"\n🔄 模糊匹配并更新数据库...")
        updated = fuzzy_match_and_update(
            conn,
            extracted_matches,
            db_matches,
            normalizer,
            dry_run
        )

        logger.info(f"\n✅ 更新了 {updated} 个比赛 URL")

        await context.close()
        await browser.close()

    conn.close()

    logger.info("\n" + "=" * 80)
    logger.info("V127.1 执行完成")
    logger.info("=" * 80)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="V127.1 增强版")
    parser.add_argument("--league", default="Premier League", help="联赛名称")
    parser.add_argument("--season", default="23/24", help="赛季")
    parser.add_argument("--dry-run", action="store_true", help="干运行")

    args = parser.parse_args()

    asyncio.run(main_async(
        league=args.league,
        season=args.season,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()
