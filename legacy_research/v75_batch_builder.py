#!/usr/bin/env python3
"""
V75.1 Batch Builder - 完整批量构建引擎

功能：
1. 从数据库读取未匹配的比赛
2. 批量提取 OddsPortal HTML 中的哈希 ID
3. 构造完整 URL
4. 并发验证（12 协程）
5. 批量更新数据库
"""

import asyncio
import logging
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Tuple

import aiohttp
import psycopg2
from playwright.async_api import async_playwright
from fuzzywuzzy import fuzz

sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v75_batch_builder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 配置
# ============================================================================

# 目标联赛和赛季
TARGETS = [
    ("Premier League", "20-21", "2020-2021", "https://www.oddsportal.com/football/england/premier-league-2020-2021/results/"),
    ("Premier League", "21-22", "2021-2022", "https://www.oddsportal.com/football/england/premier-league-2021-2022/results/"),
    ("Premier League", "22-23", "2022-2023", "https://www.oddsportal.com/football/england/premier-league-2022-2023/results/"),
    ("Premier League", "23-24", "2023-2024", "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"),
    ("Premier League", "24/25", "2024-2025", "https://www.oddsportal.com/football/england/premier-league-2024-2025/results/"),

    ("Bundesliga", "20-21", "2020-2021", "https://www.oddsportal.com/football/germany/bundesliga-2020-2021/results/"),
    ("Bundesliga", "21-22", "2021-2022", "https://www.oddsportal.com/football/germany/bundesliga-2021-2022/results/"),
    ("Bundesliga", "22-23", "2022-2023", "https://www.oddsportal.com/football/germany/bundesliga-2022-2023/results/"),
    ("Bundesliga", "23-24", "2023-2024", "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/"),
    ("Bundesliga", "24/25", "2024-2025", "https://www.oddsportal.com/football/germany/bundesliga-2024-2025/results/"),

    ("La Liga", "20-21", "2020-2021", "https://www.oddsportal.com/football/spain/laliga-2020-2021/results/"),
    ("La Liga", "21-22", "2021-2022", "https://www.oddsportal.com/football/spain/laliga-2021-2022/results/"),
    ("La Liga", "22-23", "2022-2023", "https://www.oddsportal.com/football/spain/laliga-2022-2023/results/"),
    ("La Liga", "23-24", "2023-2024", "https://www.oddsportal.com/football/spain/laliga-2023-2024/results/"),
    ("La Liga", "24/25", "2024-2025", "https://www.oddsportal.com/football/spain/laliga-2024-2025/results/"),

    ("Serie A", "20-21", "2020-2021", "https://www.oddsportal.com/football/italy/serie-a-2020-2021/results/"),
    ("Serie A", "21-22", "2021-2022", "https://www.oddsportal.com/football/italy/serie-a-2021-2022/results/"),
    ("Serie A", "22-23", "2022-2023", "https://www.oddsportal.com/football/italy/serie-a-2022-2023/results/"),
    ("Serie A", "23-24", "2023-2024", "https://www.oddsportal.com/football/italy/serie-a-2023-2024/results/"),
    ("Serie A", "24/25", "2024-2025", "https://www.oddsportal.com/football/italy/serie-a-2024-2025/results/"),

    ("Ligue 1", "20-21", "2020-2021", "https://www.oddsportal.com/football/france/ligue-1-2020-2021/results/"),
    ("Ligue 1", "21-22", "2021-2022", "https://www.oddsportal.com/football/france/ligue-1-2021-2022/results/"),
    ("Ligue 1", "22-23", "2022-2023", "https://www.oddsportal.com/football/france/ligue-1-2022-2023/results/"),
    ("Ligue 1", "23-24", "2023-2024", "https://www.oddsportal.com/football/france/ligue-1-2023-2024/results/"),
    ("Ligue 1", "24/25", "2024-2025", "https://www.oddsportal.com/football/france/ligue-1-2024-2025/results/"),
]


# ============================================================================
# 数据库操作
# ============================================================================

def get_db_connection():
    """获取数据库连接"""
    from src.config_unified import get_settings
    settings = get_settings()

    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )


def get_unmatched_matches(league: str, season: str, limit: int = 500) -> List[Tuple]:
    """
    获取未匹配的比赛

    Returns:
        List of (match_id, home_team, away_team, match_date)
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT match_id, home_team, away_team, match_date
        FROM matches
        WHERE league_name = %s
          AND season = %s
          AND oddsportal_url IS NULL
        ORDER BY match_date DESC
        LIMIT %s
    """, (league, season, limit))

    results = cur.fetchall()

    cur.close()
    conn.close()

    return results


def bulk_update_urls(updates: List[Dict[str, str]]) -> int:
    """
    批量更新 URL

    Args:
        updates: List of {'match_id': str, 'url': str}

    Returns:
        更新的记录数
    """
    if not updates:
        return 0

    conn = get_db_connection()
    cur = conn.cursor()

    updated = 0
    for update in updates:
        try:
            cur.execute("""
                UPDATE matches
                SET oddsportal_url = %s, updated_at = CURRENT_TIMESTAMP
                WHERE match_id = %s
            """, (update['url'], update['match_id']))
            updated += cur.rowcount
        except Exception as e:
            logger.warning(f"更新失败 {update['match_id']}: {e}")

    conn.commit()
    cur.close()
    conn.close()

    return updated


# ============================================================================
# HTML 提取
# ============================================================================

async def extract_match_ids_with_context(html_content: str) -> List[Dict[str, str]]:
    """
    从 HTML 中提取比赛 ID 和球队名称

    改进的正则模式：同时提取球队名称和 ID
    """
    results = []

    # 多种模式尝试
    patterns = [
        # 模式 1：完整路径 /football/country/league-season/home-away-xxxxxx/
        r'"/football/([^/]+)/([^/]+)-([^/]+)/([^/-]+)-([^/-]+?)-([a-z0-9]{7,8})/"',
        # 模式 2：简化路径 /football/xxxxx/xxxxx/xxxxx-xxxxx-xxxxx-xxxxxx/
        r'"/football/[^/]+/[^/]+/[^/]+/[^-]+-[^-]+-([a-z0-9]{7,8})/"',
        # 模式 3：任何包含 7-8 位 ID 的路径
        r'"/football/[^"]*?([a-z0-9]{7,8})/"',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        if matches:
            logger.info(f"    模式匹配成功: {len(matches)} 个结果")
            break

    for match in matches:
        if isinstance(match, tuple):
            if len(match) == 6:
                country, league_slug, season, home, away, match_id = match
            elif len(match) == 2:
                home, away, match_id = match
                country = league_slug = season = "unknown"
            else:
                match_id = match[-1]
                home = away = "unknown"
        else:
            match_id = match
            home = away = "unknown"

        # 标准化球队名称
        home_normalized = home.replace('-', ' ').title()
        away_normalized = away.replace('-', ' ').title()

        results.append({
            'match_id': match_id.lower(),
            'home_team': home_normalized,
            'away_team': away_normalized,
            'league_slug': league_slug if league_slug != "unknown" else "premier-league",
            'season': season if season != "unknown" else "2024-2025",
            'country': country if country != "unknown" else "england"
        })

    # 去重
    seen_ids = set()
    unique_results = []
    for result in results:
        if result['match_id'] not in seen_ids:
            seen_ids.add(result['match_id'])
            unique_results.append(result)

    return unique_results


async def scrape_league_results(url: str, league: str, season: str) -> List[Dict]:
    """访问联赛 Results 页面并提取比赛"""
    logger.info(f"正在抓取: {league} {season}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)  # 等待渲染

            html = await page.content()
            matches = await extract_match_ids_with_context(html)

            logger.info(f"  提取到 {len(matches)} 个比赛")
            return matches

        finally:
            await browser.close()


# ============================================================================
# 模糊匹配
# ============================================================================

def fuzzy_match_team(db_team: str, html_team: str, threshold: int = 85) -> bool:
    """模糊匹配球队名称"""
    # 标准化
    db_norm = unicodedata.normalize('NFKD', db_team).encode('ASCII', 'ignore').decode('ASCII').lower()
    html_norm = unicodedata.normalize('NFKD', html_team).encode('ASCII', 'ignore').decode('ASCII').lower()

    # 计算相似度
    score = fuzz.ratio(db_norm, html_norm) * 100

    return score >= threshold


def match_db_to_html(db_matches: List[Tuple], html_matches: List[Dict]) -> List[Dict]:
    """
    将数据库比赛与 HTML 提取的比赛进行匹配

    Returns:
        List of {'match_id': str, 'url': str}
    """
    matched = []

    for db_match_id, db_home, db_away, db_date in db_matches:
        for html_match in html_matches:
            # 尝试匹配主队和客队
            home_match = fuzzy_match_team(db_home, html_match['home_team'])
            away_match = fuzzy_match_team(db_away, html_match['away_team'])

            if home_match and away_match:
                # 构造完整 URL
                url = f"https://www.oddsportal.com/football/{html_match['country']}/{html_match['league_slug']}-{html_match['season']}/{html_match['home_team'].replace(' ', '-')}-{html_match['away_team'].replace(' ', '-')}-{html_match['match_id']}/"

                matched.append({
                    'match_id': db_match_id,
                    'url': url
                })
                break

    return matched


# ============================================================================
# 并发验证
# ============================================================================

async def validate_urls_batch(urls: List[str], concurrency: int = 12) -> Dict[str, bool]:
    """批量验证 URL"""
    results = {}
    semaphore = asyncio.Semaphore(concurrency)

    async def validate(session: aiohttp.ClientSession, url: str):
        async with semaphore:
            try:
                async with session.head(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    results[url] = response.status == 200
            except:
                results[url] = False

    async with aiohttp.ClientSession() as session:
        tasks = [validate(session, url) for url in urls]
        await asyncio.gather(*tasks)

    return results


# ============================================================================
# 主引擎
# ============================================================================

async def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("V75.1 批量构建引擎")
    logger.info("=" * 60)

    total_matches = 0
    total_updated = 0
    all_extracted = 0

    # 统计信息
    stats = {
        'scanned_pages': 0,
        'extracted_matches': 0,
        'db_matches_found': 0,
        'matched': 0,
        'updated': 0
    }

    # 处理每个目标联赛/赛季
    for league, season_abbr, season_full, url in TARGETS:  # 处理所有目标
        logger.info(f"\n{'=' * 60}")
        logger.info(f"处理: {league} {season_abbr}")
        logger.info(f"{'=' * 60}")

        # 1. 从数据库获取未匹配的比赛
        db_matches = get_unmatched_matches(league, season_abbr)
        logger.info(f"数据库未匹配: {len(db_matches)} 场")

        if not db_matches:
            logger.info(f"  跳过（无需匹配）")
            continue

        # 2. 抓取 HTML 并提取比赛
        html_matches = await scrape_league_results(url, league, season_abbr)
        stats['scanned_pages'] += 1
        stats['extracted_matches'] += len(html_matches)

        if not html_matches:
            logger.warning(f"  HTML 中未找到比赛，跳过")
            continue

        # 3. 模糊匹配
        matched = match_db_to_html(db_matches, html_matches)
        stats['db_matches_found'] += len(db_matches)
        stats['matched'] += len(matched)

        logger.info(f"  成功匹配: {len(matched)} 场")

        # 4. 验证 URL
        if matched:
            urls = [m['url'] for m in matched]
            logger.info(f"  验证 {len(urls)} 个 URL...")

            validation_results = await validate_urls_batch(urls[:50])  # 限制 50 个测试

            valid_count = sum(1 for v in validation_results.values() if v)
            logger.info(f"  有效 URL: {valid_count}/{len(validation_results)}")

            # 5. 更新数据库
            updates = [{'match_id': m['match_id'], 'url': m['url']} for m in matched]
            updated = bulk_update_urls(updates)
            stats['updated'] += updated

            logger.info(f"  数据库更新: {updated} 条")

        # 避免过载
        await asyncio.sleep(2)

    # 输出汇总
    logger.info(f"\n{'=' * 60}")
    logger.info("V75.1 批量构建完成 - 汇总报告")
    logger.info(f"{'=' * 60}")
    logger.info(f"扫描页面: {stats['scanned_pages']}")
    logger.info(f"提取比赛: {stats['extracted_matches']}")
    logger.info(f"数据库匹配: {stats['db_matches_found']}")
    logger.info(f"成功匹配: {stats['matched']}")
    logger.info(f"数据库更新: {stats['updated']}")

    # 验证效果
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(oddsportal_url) as with_url,
            ROUND(100.0 * COUNT(oddsportal_url) / COUNT(*), 2) as fill_rate
        FROM matches
    """)
    result = cur.fetchone()
    cur.close()
    conn.close()

    logger.info(f"\n当前填充率:")
    logger.info(f"  总比赛: {result[0]}")
    logger.info(f"  有 URL: {result[1]}")
    logger.info(f"  填充率: {result[2]}%")


if __name__ == "__main__":
    asyncio.run(main())
