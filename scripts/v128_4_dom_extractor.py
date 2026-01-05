#!/usr/bin/env python3
"""V128.4 DOM 渲染提取 - 从页面中直接提取 match URL.

核心策略：
1. 访问 OddsPortal 结果页面
2. 等待页面完全渲染
3. 从 DOM 中提取所有 match 链接
4. 模糊匹配并更新数据库
"""

import asyncio
import json
import logging
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                  'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY']:
    os.environ.pop(proxy_var, None)

import psycopg2
from playwright.async_api import async_playwright, Page

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings
from src.utils.text_processor import TeamNameNormalizer, LeagueUrlMapper
from thefuzz import fuzz

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.oddsportal.com"

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
]


async def extract_match_links_from_dom(
    page: Page,
    max_scroll: int = 50
) -> list[dict[str, Any]]:
    """从 DOM 中提取 match 链接."""
    logger.info(f"  🎯 从 DOM 提取 match 链接...")

    # 执行滚动触发懒加载
    for i in range(max_scroll):
        await page.mouse.wheel(0, 500)
        if i % 10 == 0:
            logger.info(f"    滚动进度: {i}/{max_scroll}")
        await asyncio.sleep(0.2)

    # 额外等待
    await asyncio.sleep(3)

    # 提取所有 match 链接
    logger.info(f"  🔍 提取链接...")
    match_data = await page.evaluate("""() => {
        const results = [];
        const seen = new Set();

        // 查找所有包含 /match/ 的链接
        const links = document.querySelectorAll('a[href*="/match/"]');
        for (const link of links) {
            const href = link.href;
            const text = link.textContent?.trim() || '';

            // 提取哈希值
            const hashMatch = href.match(/([a-z0-9]{8})/);
            const hash = hashMatch ? hashMatch[1] : null;

            if (hash && !seen.has(hash)) {
                seen.add(hash);
                results.push({
                    url: href,
                    text: text,
                    hash: hash
                });
            }
        }

        return results;
    }""")

    logger.info(f"  ✅ 提取到 {len(match_data)} 个唯一链接")
    return match_data


def get_pending_matches(conn, league_name: str, season: str) -> list[dict[str, Any]]:
    """获取待处理比赛."""
    possible_seasons = [season]
    if "/" in season:
        parts = season.split("/")
        if len(parts) == 2:
            possible_seasons.append(f"20{parts[0]}-20{parts[1]}")

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
    """V128.4 主函数."""
    logger.info("=" * 80)
    logger.info("V128.4 DOM 渲染提取")
    logger.info("=" * 80)

    settings = get_settings()
    normalizer = TeamNameNormalizer()
    mapper = LeagueUrlMapper()

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

    # 构造 URL
    results_url = mapper.construct_results_url(league, season)
    if not results_url:
        logger.error(f"  ❌ 无 URL 映射: {league}")
        conn.close()
        return

    # 修正赛季格式
    if "/" in season:
        parts = season.split("/")
        if len(parts) == 2:
            import re
            pattern = r'-([0-9]{2})/([0-9]{2})(/|$)'
            match = re.search(pattern, results_url)
            if match:
                year1 = int(match.group(1))
                year2 = int(match.group(2))
                if year1 < 100:
                    year1 += 2000
                if year2 < 100:
                    year2 += 2000
                new_season = f"{year1}-{year2}"
                new_url = re.sub(pattern, f'-{new_season}{match.group(3)}', results_url)
                if new_url != results_url:
                    logger.info(f"  🔄 URL 赛季修正: {season} -> {new_season}")
                    results_url = new_url

    logger.info(f"  📍 URL: {results_url}")

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

        # 导航到页面
        logger.info(f"\n🌐 导航到页面...")
        try:
            await page.goto(results_url, timeout=90000, wait_until="domcontentloaded")
            logger.info(f"  ✅ 页面加载成功")

            # 等待 match 链接出现
            try:
                await page.wait_for_selector("a[href*='/match/']", timeout=30000)
                logger.info(f"  ✅ 检测到 match 链接")
            except:
                logger.warning(f"  ⚠️  未检测到 match 链接，继续尝试...")

        except Exception as e:
            logger.error(f"  ❌ 页面加载失败: {e}")
            await context.close()
            await browser.close()
            conn.close()
            return

        # 提取 match 链接
        extracted_matches = await extract_match_links_from_dom(page, max_scroll=50)

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

        # 保存提取结果
        output_file = Path("logs") / f"v128_4_extracted_{league.replace(' ', '_')}_{season.replace('/', '-')}.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, "w") as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'league': league,
                'season': season,
                'url': results_url,
                'extracted_count': len(extracted_matches),
                'updated_count': updated,
                'matches': extracted_matches
            }, f, indent=2)
        logger.info(f"  💾 保存结果到: {output_file}")

        await context.close()
        await browser.close()

    conn.close()

    logger.info("\n" + "=" * 80)
    logger.info("V128.4 执行完成")
    logger.info("=" * 80)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="V128.4 DOM 渲染提取")
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
