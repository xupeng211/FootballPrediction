#!/usr/bin/env python3
"""
V76.0 Precision Aligner - 精准对齐收割引擎

核心原则：
1. 1-on-1 精准匹配：每条数据库记录必须与 HTML 中的行完全对齐
2. 严禁批量分配：不匹配的记录留空，不强制分配 ID
3. 双向核验：主队 AND 客队都必须对齐
"""

import asyncio
import logging
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import aiohttp
import psycopg2
from playwright.async_api import async_playwright
from fuzzywuzzy import fuzz

sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入 V69.1 模糊匹配器
from scripts.v69_fuzzy_matcher import AdvancedFuzzyMatcher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v76_precision_aligner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 配置
# ============================================================================

# 24/25 赛季目标联赛
TARGETS_24_25 = [
    ("Premier League", "24/25", "https://www.oddsportal.com/football/england/premier-league-2024-2025/results/"),
    ("Bundesliga", "24/25", "https://www.oddsportal.com/football/germany/bundesliga-2024-2025/results/"),
    ("La Liga", "24/25", "https://www.oddsportal.com/football/spain/laliga-2024-2025/results/"),
    ("Serie A", "24/25", "https://www.oddsportal.com/football/italy/serie-a-2024-2025/results/"),
    ("Ligue 1", "24/25", "https://www.oddsportal.com/football/france/ligue-1-2024-2025/results/"),
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


def get_matches_without_url(league: str, season: str) -> List[Tuple]:
    """
    获取没有 URL 的比赛

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
    """, (league, season))

    results = cur.fetchall()

    cur.close()
    conn.close()

    return results


def update_match_url(match_id: str, url: str) -> bool:
    """更新单条比赛的 URL"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE matches
            SET oddsportal_url = %s, updated_at = CURRENT_TIMESTAMP
            WHERE match_id = %s
        """, (url, match_id))

        conn.commit()
        return True
    except Exception as e:
        logger.warning(f"更新失败 {match_id}: {e}")
        return False
    finally:
        cur.close()
        conn.close()


# ============================================================================
# HTML 精准解析
# ============================================================================

async def extract_match_rows_from_html(html_content: str) -> List[Dict[str, str]]:
    """
    从 HTML 中提取完整的比赛行（包含球队名称和 ID）

    Returns:
        List of {'home': str, 'away': str, 'match_id': str, 'full_url': str}
    """
    results = []

    # 改进的正则：同时提取球队名称和 ID
    # 模式："/football/country/league-season/home-away-xxxxxx/"
    pattern = r'"/football/([^/]+)/([^/]+)-([^/]+)/([^/-]+)-([^/-]+)-([a-z0-9]{7,8})/"'

    matches = re.findall(pattern, html_content, re.IGNORECASE)

    for country, league_slug, season, home, away, match_id in matches:
        # 标准化球队名称（连字符转空格，首字母大写）
        home_normalized = home.replace('-', ' ').title()
        away_normalized = away.replace('-', ' ').title()

        # 构造完整 URL
        full_url = f"https://www.oddsportal.com/football/{country}/{league_slug}-{season}/{home}-{away}-{match_id}/"

        results.append({
            'home': home_normalized,
            'away': away_normalized,
            'match_id': match_id.lower(),
            'full_url': full_url,
            'country': country,
            'league_slug': league_slug,
            'season': season
        })

    return results


async def scrape_results_page(url: str, league: str, season: str) -> List[Dict]:
    """访问 Results 页面并提取比赛行"""
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
            match_rows = await extract_match_rows_from_html(html)

            logger.info(f"  提取到 {len(match_rows)} 个比赛行")
            return match_rows

        finally:
            await browser.close()


# ============================================================================
# 精准对齐
# ============================================================================

def fuzzy_match_teams(db_team: str, html_team: str, threshold: int = 90) -> bool:
    """
    模糊匹配球队名称（提高阈值到 90%）

    Args:
        db_team: 数据库中的球队名称
        html_team: HTML 中提取的球队名称
        threshold: 相似度阈值（默认 90%）

    Returns:
        是否匹配
    """
    # 标准化
    db_norm = unicodedata.normalize('NFKD', db_team).encode('ASCII', 'ignore').decode('ASCII').lower()
    html_norm = unicodedata.normalize('NFKD', html_team).encode('ASCII', 'ignore').decode('ASCII').lower()

    # 计算相似度
    score = fuzz.ratio(db_norm, html_norm) * 100

    return score >= threshold


def precision_align(db_matches: List[Tuple], html_matches: List[Dict]) -> List[Dict]:
    """
    精准对齐：1-on-1 匹配

    规则：
    1. 主队 AND 客队都必须对齐（相似度 >= 90%）
    2. 不匹配的记录不分配 URL
    3. 严禁批量分配

    Returns:
        List of {'match_id': str, 'url': str, 'db_home': str, 'db_away': str, 'html_home': str, 'html_away': str}
    """
    aligned = []
    matcher = AdvancedFuzzyMatcher(similarity_threshold=0.90)

    logger.info(f"  开始精准对齐...")
    logger.info(f"    数据库记录: {len(db_matches)}")
    logger.info(f"    HTML 比赛: {len(html_matches)}")

    for db_match_id, db_home, db_away, db_date in db_matches:
        best_match = None
        best_score = 0

        for html_match in html_matches:
            # 使用 V69.1 模糊匹配器
            home_score = matcher.calculate_similarity(db_home, html_match['home'])
            away_score = matcher.calculate_similarity(db_away, html_match['away'])

            # 只有两队都高相似度才算匹配
            if home_score >= 0.90 and away_score >= 0.90:
                avg_score = (home_score + away_score) / 2

                if avg_score > best_score:
                    best_score = avg_score
                    best_match = {
                        'match_id': db_match_id,
                        'url': html_match['full_url'],
                        'db_home': db_home,
                        'db_away': db_away,
                        'html_home': html_match['home'],
                        'html_away': html_match['away'],
                        'home_score': home_score,
                        'away_score': away_score
                    }

        if best_match:
            aligned.append(best_match)

    logger.info(f"  精准对齐完成: {len(aligned)}/{len(db_matches)} 条匹配")

    return aligned


# ============================================================================
# 并发验证
# ============================================================================

async def validate_urls_batch(urls: List[str], concurrency: int = 8) -> Dict[str, bool]:
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
    logger.info("V76.0 精准对齐收割引擎")
    logger.info("=" * 60)

    total_aligned = 0
    total_updated = 0
    all_aligned_records = []

    # 处理每个目标联赛
    for league, season, url in TARGETS_24_25:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"处理: {league} {season}")
        logger.info(f"{'=' * 60}")

        # 1. 获取没有 URL 的比赛
        db_matches = get_matches_without_url(league, season)
        logger.info(f"数据库未匹配: {len(db_matches)} 场")

        if not db_matches:
            logger.info(f"  跳过（无需匹配）")
            continue

        # 2. 抓取 HTML 并提取比赛行
        html_matches = await scrape_results_page(url, league, season)

        if not html_matches:
            logger.warning(f"  HTML 中未找到比赛，跳过")
            continue

        # 3. 精准对齐
        aligned = precision_align(db_matches, html_matches)

        if not aligned:
            logger.info(f"  无匹配结果")
            continue

        # 4. 验证 URL
        urls = [a['url'] for a in aligned]
        logger.info(f"  验证 {len(urls)} 个 URL...")

        validation_results = await validate_urls_batch(urls)
        valid_count = sum(1 for v in validation_results.values() if v)
        logger.info(f"  有效 URL: {valid_count}/{len(validation_results)}")

        # 5. 更新数据库（只更新有效的）
        updated = 0
        for align_record in aligned:
            if validation_results.get(align_record['url'], False):
                if update_match_url(align_record['match_id'], align_record['url']):
                    updated += 1
                    all_aligned_records.append(align_record)

        logger.info(f"  数据库更新: {updated} 条")
        total_aligned += len(aligned)
        total_updated += updated

        # 避免过载
        await asyncio.sleep(2)

    # 输出汇总
    logger.info(f"\n{'=' * 60}")
    logger.info("V76.0 精准对齐完成 - 汇总报告")
    logger.info(f"{'=' * 60}")
    logger.info(f"总对齐: {total_aligned} 条")
    logger.info(f"总更新: {total_updated} 条")

    # 检查最终状态
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

    logger.info(f"\n最终填充率:")
    logger.info(f"  总比赛: {result[0]}")
    logger.info(f"  有 URL: {result[1]}")
    logger.info(f"  填充率: {result[2]}%")

    # 保存对齐记录用于验证
    if all_aligned_records:
        with open('audit_temp/v76_aligned_records.json', 'w') as f:
            import json
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_aligned': len(all_aligned_records),
                'records': all_aligned_records[:100]  # 保存前 100 条
            }, f, indent=2)
        logger.info(f"\n对齐记录已保存: audit_temp/v76_aligned_records.json")


if __name__ == "__main__":
    asyncio.run(main())
