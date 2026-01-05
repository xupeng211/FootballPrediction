#!/usr/bin/env python3
"""V127.0 DOM 截胡策略 - 金矿 API 捕获 + DOM 提取.

核心策略：
1. 定向拦截金矿 API (ajax-sport-country-tournament-archive_)
2. 确认 API 加载完成后，立即从 DOM 提取 match 链接
3. 批量更新数据库

Usage:
    python scripts/v127_0_dom_interceptor.py --league "Premier League" --season "23/24"
    python scripts/v127_0_dom_interceptor.py --dry-run
"""

import argparse
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

# Disable proxy
for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY',
                  'all_proxy', 'ALL_PROXY', 'no_proxy', 'NO_PROXY']:
    os.environ.pop(proxy_var, None)

import psycopg2
from playwright.async_api import async_playwright, Page
from thefuzz import fuzz

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings
from src.utils.text_processor import TeamNameNormalizer, LeagueUrlMapper

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://www.oddsportal.com"
MIN_PAYLOAD_SIZE = 500 * 1024  # 500KB
TARGET_API_KEYWORD = "ajax-sport-country-tournament-archive_"

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


class DOMInterceptorStats:
    """统计追踪."""

    def __init__(self) -> None:
        self.leagues_processed = 0
        self.api_captures = 0
        self.matches_extracted = 0
        self.matches_matched = 0
        self.urls_updated = 0
        self.start_time = datetime.now()

    def summary(self) -> str:
        """生成执行摘要."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        capture_rate = (self.api_captures / self.leagues_processed * 100) if self.leagues_processed > 0 else 0

        return f"""
╔═══════════════════════════════════════════════════════════════╗
║              V127.0 DOM 截胡引擎 - 执行摘要                      ║
╠═══════════════════════════════════════════════════════════════╣
║ 处理联赛数:       {self.leagues_processed:>5}                                      ║
║ 成功捕获金矿:     {self.api_captures:>5}  ({capture_rate:>5.1f}%)                         ║
║ 提取比赛数:       {self.matches_extracted:>5}                                      ║
║ 匹配数据库数:     {self.matches_matched:>5}                                      ║
║ 更新 URL 数:      {self.urls_updated:>5}                                      ║
║ 执行时间:         {elapsed:>8.1f} 秒                                ║
║ 提取速率:         {self.matches_matched / elapsed if elapsed > 0 else 0:>8.2f} 场/秒                          ║
╚═══════════════════════════════════════════════════════════════╝"""


async def capture_api_and_extract_from_dom(
    page: Page,
    results_url: str,
) -> dict[str, Any] | None:
    """V127.0 Phase 2: 捕获 API 并从 DOM 提取 match 链接.

    核心逻辑：
    1. 设置网络拦截器，检测金矿 API
    2. 一旦检测到金矿 API 加载完成（大小 > 500KB）
    3. 立即从 DOM 提取所有 match 链接

    Args:
        page: Playwright 页面实例
        results_url: 目标联赛结果页 URL

    Returns:
        提取结果字典
    """
    logger.info(f"  🎯 DOM 截胡模式启动")

    # 存储捕获状态
    api_detected = False
    api_loaded_event = asyncio.Event()

    async def handle_response(response):
        nonlocal api_detected
        try:
            url = response.url
            status = response.status

            # 只关注金矿 API
            if TARGET_API_KEYWORD not in url:
                return

            logger.info(f"  📡 检测到金矿 API: {url[:80]}...")

            if status == 200:
                api_detected = True

                # 尝试获取响应体大小
                try:
                    body = await response.text(timeout=60000)
                    body_size = len(body)

                    logger.info(f"  📦 响应体大小: {body_size:,} 字节")

                    if body_size >= MIN_PAYLOAD_SIZE:
                        logger.info(f"  ✅ 金矿已加载！准备 DOM 截胡...")
                        api_loaded_event.set()
                    else:
                        logger.warning(f"  ⚠️  响应体 {body_size:,} < {MIN_PAYLOAD_SIZE:,}")

                except Exception as e:
                    logger.warning(f"  ⚠️  读取响应体失败: {e}")
                    # 即使读取失败，也标记为已检测到
                    api_loaded_event.set()

        except Exception:
            pass

    # 注册响应处理器
    page.on('response', handle_response)

    # 导航到目标页面
    logger.info(f"  🌐 导航到结果页...")
    try:
        await page.goto(results_url, timeout=60000, wait_until="domcontentloaded")
    except Exception as e:
        logger.warning(f"  ⚠️  导航超时（继续）: {e}")

    # 执行滚屏触发 API 调用
    logger.info(f"  📜 执行滚屏触发...")
    for i in range(25):
        if api_loaded_event.is_set():
            logger.info(f"  🎉 在第 {i} 次滚动时触发金矿！")
            break

        await page.mouse.wheel(0, 600)
        await asyncio.sleep(0.4)

    # 等待 API 加载
    if not api_loaded_event.is_set():
        logger.info(f"  ⏳ 等待 API 加载...")
        await asyncio.sleep(15)

    # 额外等待让 DOM 渲染
    logger.info(f"  ⏳ 等待 DOM 渲染...")
    await asyncio.sleep(5)

    # 注销响应处理器
    page.remove_listener('response', handle_response)

    if not api_detected:
        logger.warning(f"  ❌ 未检测到金矿 API")
        return None

    # V127.0: DOM 截胡 - 提取所有 match 链接
    logger.info(f"\n  🎯 DOM 截胡：提取 match 链接...")

    try:
        # 等待 match 链接出现
        await page.wait_for_selector("a[href*='/match/']", timeout=10000)

        # 提取所有 match 链接
        dom_urls = await page.evaluate("""() => {
            const links = document.querySelectorAll('a[href*="/match/"]');
            const results = [];

            for (const link of links) {
                const href = link.href;
                const text = link.textContent?.trim() || '';

                // 只保留带 8 位哈希的链接
                if (/[a-z0-9]{8}/.test(href)) {
                    results.push({
                        url: href,
                        text: text
                    });
                }
            }

            return results;
        }""")

        logger.info(f"  📋 找到 {len(dom_urls)} 个 match 链接")

        if not dom_urls:
            logger.warning(f"  ❌ 未找到 match 链接")
            return None

        # 提取 URL 并去重
        unique_urls = {}
        for item in dom_urls:
            url = item['url']
            text = item['text']

            # 提取哈希值
            hash_match = re.search(r'/match/[^/]+-([a-z0-9]{8})', url.lower())
            hash_str = hash_match.group(1) if hash_match else "NO_HASH"

            # 去重（基于哈希值）
            if hash_str != "NO_HASH" and hash_str not in unique_urls:
                unique_urls[hash_str] = {
                    'url': url,
                    'text': text,
                    'hash': hash_str
                }

        logger.info(f"  🔄 去重后: {len(unique_urls)} 个唯一 URL")

        # 显示前 20 个
        logger.info(f"\n  📋 提取的 URL（前 20 个）:")
        for i, (hash_val, data) in enumerate(list(unique_urls.items())[:20], 1):
            logger.info(f"     [{i:2d}] {hash_val} -> {data['text'][:40]}")

        if len(unique_urls) > 20:
            logger.info(f"     ... 还有 {len(unique_urls) - 20} 个 URL")

        return {
            'success': True,
            'matches': list(unique_urls.values()),
            'count': len(unique_urls)
        }

    except Exception as e:
        logger.error(f"  ❌ DOM 提取失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def normalize_season_for_url(season_str: str) -> str:
    """将数据库赛季格式转换为 URL 格式."""
    season_str = season_str.strip()
    if "/" in season_str:
        parts = season_str.split("/")
        if len(parts) == 2:
            try:
                year1 = int(parts[0])
                year2 = int(parts[1])
                if year1 < 100:
                    year1 += 2000
                if year2 < 100:
                    year2 += 2000 if year2 < 50 else 1900
                if year2 < year1:
                    year2 += 100
                return f"{year1}-{year2}"
            except ValueError:
                pass
    return season_str


def get_pending_matches_for_league(
    conn,
    league_name: str,
    season: str
) -> list[dict[str, Any]]:
    """获取待处理比赛."""
    possible_seasons = [season]

    if "-" in season and len(season) >= 4:
        parts = season.split("-")
        if len(parts) == 2 and len(parts[0]) == 4:
            short1 = parts[0][2:]
            short2 = parts[1][2:] if len(parts[1]) == 4 else parts[1]
            possible_seasons.append(f"{short1}/{short2}")
            possible_seasons.append(f"{short1}-{short2}")

    season_placeholders = ",".join(["%s"] * len(possible_seasons))
    query = f"""
        SELECT
            m.match_id,
            m.home_team,
            m.away_team,
            m.match_date,
            m.oddsportal_url
        FROM matches m
        WHERE m.league_name = %s
          AND (m.season IN ({season_placeholders}) OR m.season IS NULL)
          AND m.oddsportal_url IS NULL
        ORDER BY m.match_date DESC;
    """

    params = [league_name] + possible_seasons

    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    matches = []
    for row in rows:
        matches.append({
            "match_id": row[0],
            "home_team": row[1],
            "away_team": row[2],
            "match_date": row[3],
            "oddsportal_url": row[4]
        })

    return matches


def fuzzy_match_and_update(
    conn,
    extracted_matches: list[dict[str, Any]],
    db_matches: list[dict[str, Any]],
    normalizer: TeamNameNormalizer,
    dry_run: bool = False
) -> int:
    """V127.0 Phase 3: 模糊匹配并批量更新数据库."""
    updates = []

    for db_match in db_matches:
        match_id = db_match["match_id"]
        home_team = normalizer.normalize(db_match["home_team"])
        away_team = normalizer.normalize(db_match["away_team"])

        # 寻找最佳匹配
        best_match = None
        best_score = 0

        for extracted in extracted_matches:
            extracted_text = extracted.get('text', '')
            extracted_normalized = normalizer.normalize(extracted_text)

            # 拆分主客队
            parts = extracted_normalized.split(' - ')
            if len(parts) == 2:
                extracted_home = parts[0].strip()
                extracted_away = parts[1].strip()

                # 计算相似度
                home_sim = fuzz.partial_ratio(home_team, extracted_home)
                away_sim = fuzz.partial_ratio(away_team, extracted_away)

                # 双向匹配
                if home_sim >= 70 and away_sim >= 70:
                    avg_score = (home_sim + away_sim) / 2
                    if avg_score > best_score:
                        best_score = avg_score
                        best_match = extracted

        if best_match:
            updates.append((match_id, best_match['url']))

    # 批量更新
    if updates:
        if dry_run:
            logger.info(f"  [DRY RUN] 将更新 {len(updates)} 个比赛 URL")
        else:
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

        logger.info(f"  ✅ 更新了 {len(updates)} 个比赛 URL")

    return len(updates)


async def main_async(
    league_filter: str | None = None,
    season_filter: str | None = None,
    dry_run: bool = False,
) -> None:
    """V127.0: 主异步函数."""
    logger.info("=" * 80)
    logger.info("V127.0 DOM 截胡引擎 - 金矿捕获 + DOM 提取")
    logger.info("=" * 80)

    settings = get_settings()
    mapper = LeagueUrlMapper()
    normalizer = TeamNameNormalizer()
    stats = DOMInterceptorStats()

    # 连接数据库
    logger.info("\n📡 连接数据库...")
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )
    logger.info("  ✅ 数据库已连接")

    # 获取待处理联赛
    logger.info("\n🔍 查询待处理联赛...")
    query = """
        SELECT
            m.league_name,
            COALESCE(m.season, '23/24') as season,
            COUNT(*) as match_count
        FROM matches m
        WHERE m.oddsportal_url IS NULL
        GROUP BY m.league_name, COALESCE(m.season, '23/24')
        ORDER BY match_count DESC
        LIMIT 10;
    """

    with conn.cursor() as cur:
        cur.execute(query)
        leagues = cur.fetchall()

    # 应用过滤器
    if league_filter:
        leagues = [(l, s, c) for l, s, c in leagues if league_filter.lower() in l.lower()]

    if season_filter:
        leagues = [(l, s, c) for l, s, c in leagues if season_filter in s]

    logger.info(f"\n📋 处理 {len(leagues)} 个联赛...")

    # 启动浏览器
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=STEALTH_BROWSER_ARGS
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=STEALTH_USER_AGENT,
        )

        page = await context.new_page()

        # 处理每个联赛
        for i, (league_name, season, _) in enumerate(leagues, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"[{i}/{len(leagues)}] 处理: {league_name} {season}")
            logger.info(f"{'='*80}")

            stats.leagues_processed += 1

            # 构造 URL
            results_url = mapper.construct_results_url(league_name, season)
            if not results_url:
                logger.warning(f"  ❌ 无 URL 映射")
                continue

            # 修正 URL 格式
            normalized_season = normalize_season_for_url(season)
            if "/" in results_url:
                import re
                pattern = r'-([0-9]{2})/([0-9]{2})(/|$)'
                match = re.search(pattern, results_url)
                if match:
                    year1 = int(match.group(1))
                    year2 = int(match.group(2))
                    if year1 < 100:
                        year1 += 2000
                    if year2 < 100:
                        year2 += 2000 if year2 < 50 else 1900
                    if year2 < year1:
                        year2 += 100
                    new_season = f"{year1}-{year2}"
                    new_url = re.sub(pattern, f'-{new_season}{match.group(3)}', results_url)
                    results_url = new_url
                    logger.info(f"  📍 修正 URL: {results_url}")

            # 获取待处理比赛
            db_matches = get_pending_matches_for_league(conn, league_name, season)
            if not db_matches:
                logger.info(f"  ⏭️  无待处理比赛")
                continue

            # V127.0: DOM 截胡
            result = await capture_api_and_extract_from_dom(page, results_url)

            if result and result['success']:
                stats.api_captures += 1
                stats.matches_extracted += result['count']

                # 模糊匹配更新
                updated = fuzzy_match_and_update(
                    conn,
                    result['matches'],
                    db_matches,
                    normalizer,
                    dry_run
                )

                stats.urls_updated += updated
                stats.matches_matched += updated

            # 延迟
            await asyncio.sleep(random.uniform(3, 6))

        await context.close()
        await browser.close()

    conn.close()

    # 打印摘要
    logger.info(stats.summary())


def main():
    parser = argparse.ArgumentParser(description="V127.0 DOM 截胡引擎")
    parser.add_argument("--league", type=str, help="过滤联赛名称")
    parser.add_argument("--season", type=str, help="过滤赛季")
    parser.add_argument("--dry-run", action="store_true", help="干运行")

    args = parser.parse_args()

    asyncio.run(main_async(
        league_filter=args.league,
        season_filter=args.season,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()
