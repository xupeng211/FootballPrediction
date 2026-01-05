#!/usr/bin/env python3
"""
V78.0 Great Mapping - 五年大巡航引擎

核心任务：通过遍历 25 个历史汇总页，补齐 8,930 个 URL 缺口

架构：
1. 构建 25 个巡航坐标（5 大联赛 x 5 赛季）
2. 8 Worker 并发抓取 + 正则暴力提取
3. 1-on-1 精准映射（相似度 > 0.95）
"""

import asyncio
import logging
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

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
        logging.FileHandler('logs/v78_great_mapping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================

@dataclass
class CruiseCoordinate:
    """巡航坐标"""
    league: str
    season: str
    season_slug: str  # URL 中的赛季格式（如 2020-2021）
    url: str


@dataclass
class ExtractedMatch:
    """从 HTML 提取的比赛"""
    home: str
    away: str
    hash_id: str
    full_url: str
    league: str
    season_slug: str
    country: str


@dataclass
class MappingResult:
    """映射结果"""
    match_id: str
    url: str
    db_home: str
    db_away: str
    html_home: str
    html_away: str
    home_score: float
    away_score: float
    league: str
    season: str


# ============================================================================
# 25 个巡航坐标构建
# ============================================================================

def build_cruise_coordinates() -> List[CruiseCoordinate]:
    """
    构建 25 个巡航坐标

    Returns:
        List of CruiseCoordinate (5 leagues x 5 seasons = 25)
    """
    coordinates = []

    # 联赛配置
    LEAGUE_CONFIG = {
        "Premier League": {
            "country": "england",
            "slug": "premier-league",
        },
        "Bundesliga": {
            "country": "germany",
            "slug": "bundesliga",
        },
        "La Liga": {
            "country": "spain",
            "slug": "laliga",
        },
        "Serie A": {
            "country": "italy",
            "slug": "serie-a",
        },
        "Ligue 1": {
            "country": "france",
            "slug": "ligue-1",
        },
    }

    # 赛季配置（数据库格式 -> URL 格式）
    SEASON_MAPPING = {
        "20/21": "2020-2021",
        "21/22": "2021-2022",
        "22/23": "2022-2023",
        "23/24": "2023-2024",
        "24/25": "2024-2025",
    }

    # 构建所有组合
    for league, config in LEAGUE_CONFIG.items():
        for season_db, season_url in SEASON_MAPPING.items():
            url = f"https://www.oddsportal.com/football/{config['country']}/{config['slug']}-{season_url}/results/"

            coordinates.append(CruiseCoordinate(
                league=league,
                season=season_db,
                season_slug=season_url,
                url=url
            ))

    logger.info(f"=" * 60)
    logger.info(f"V78.0 五年大巡航 - 25 个坐标构建完成")
    logger.info(f"=" * 60)
    logger.info(f"联赛数: {len(LEAGUE_CONFIG)}")
    logger.info(f"赛季数: {len(SEASON_MAPPING)}")
    logger.info(f"总坐标数: {len(coordinates)}")

    return coordinates


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
    获取指定联赛和赛季中没有 URL 的比赛

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


def update_match_url_batch(updates: List[Dict]) -> int:
    """
    批量更新比赛 URL

    Args:
        updates: List of {'match_id': str, 'url': str}

    Returns:
        成功更新的数量
    """
    if not updates:
        return 0

    conn = get_db_connection()
    cur = conn.cursor()

    success_count = 0

    for update in updates:
        try:
            cur.execute("""
                UPDATE matches
                SET oddsportal_url = %s, updated_at = CURRENT_TIMESTAMP
                WHERE match_id = %s
            """, (update['url'], update['match_id']))
            success_count += 1
        except Exception as e:
            logger.warning(f"更新失败 {update['match_id']}: {e}")

    conn.commit()
    cur.close()
    conn.close()

    return success_count


# ============================================================================
# HTML 提取引擎
# ============================================================================

async def extract_match_rows_from_html(html_content: str, league: str, season_slug: str) -> List[ExtractedMatch]:
    """
    从 HTML 中提取完整的比赛行（包含球队名称和哈希 ID）

    Args:
        html_content: 页面 HTML 源码
        league: 联赛名称
        season_slug: 赛季 URL 格式

    Returns:
        List of ExtractedMatch
    """
    results = []

    # 正则模式：提取球队名称和哈希 ID
    # 格式："/football/country/league-season/home-away-hash123/"
    pattern = r'"/football/([^/]+)/([^/]+)-([^/]+)/([^/-]+)-([^/-]+)-([a-z0-9]{7,8})/"'

    matches = re.findall(pattern, html_content, re.IGNORECASE)

    for country, league_slug, season, home, away, hash_id in matches:
        # 标准化球队名称（连字符转空格，首字母大写）
        home_normalized = home.replace('-', ' ').title()
        away_normalized = away.replace('-', ' ').title()

        # 构造完整 URL
        full_url = f"https://www.oddsportal.com/football/{country}/{league_slug}-{season}/{home}-{away}-{hash_id}/"

        results.append(ExtractedMatch(
            home=home_normalized,
            away=away_normalized,
            hash_id=hash_id.lower(),
            full_url=full_url,
            league=league,
            season_slug=season_slug,
            country=country
        ))

    return results


async def scrape_results_page(coordinate: CruiseCoordinate) -> List[ExtractedMatch]:
    """
    抓取单个 results 页面并提取比赛行

    Args:
        coordinate: 巡航坐标

    Returns:
        List of ExtractedMatch
    """
    logger.info(f"正在抓取: {coordinate.league} {coordinate.season}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        try:
            await page.goto(coordinate.url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(2)  # 等待 Vue.js 渲染

            html = await page.content()
            match_rows = await extract_match_rows_from_html(html, coordinate.league, coordinate.season_slug)

            logger.info(f"  提取到 {len(match_rows)} 个比赛 URL")
            return match_rows

        except Exception as e:
            logger.error(f"  抓取失败: {e}")
            return []

        finally:
            await browser.close()


async def scrape_all_pages_concurrent(coordinates: List[CruiseCoordinate], concurrency: int = 8) -> Dict[str, List[ExtractedMatch]]:
    """
    并发抓取所有页面

    Args:
        coordinates: 巡航坐标列表
        concurrency: 并发数

    Returns:
        Dict of {coordinate_key: List[ExtractedMatch]}
    """
    results = {}
    semaphore = asyncio.Semaphore(concurrency)

    async def scrape_with_semaphore(coord: CruiseCoordinate):
        async with semaphore:
            key = f"{coord.league} {coord.season}"
            matches = await scrape_results_page(coord)
            results[key] = matches
            return key, len(matches)

    tasks = [scrape_with_semaphore(coord) for coord in coordinates]

    # 执行并发抓取
    await asyncio.gather(*tasks)

    return results


# ============================================================================
# 1-on-1 精准映射引擎
# ============================================================================

def precision_map(db_matches: List[Tuple], html_matches: List[ExtractedMatch],
                  league: str, season: str) -> List[MappingResult]:
    """
    1-on-1 精准映射

    规则：
    1. 主队 AND 客队相似度都必须 > 0.95
    2. 每个 HTML 最多匹配 1 个数据库记录
    3. 每个数据库记录最多匹配 1 个 HTML

    Args:
        db_matches: 数据库比赛列表
        html_matches: HTML 提取的比赛列表
        league: 联赛名称
        season: 赛季

    Returns:
        List of MappingResult
    """
    matched = []
    matcher = AdvancedFuzzyMatcher(similarity_threshold=0.95)

    logger.info(f"  开始精准映射...")
    logger.info(f"    数据库记录: {len(db_matches)}")
    logger.info(f"    HTML 比赛: {len(html_matches)}")

    # 追踪已匹配的 HTML，避免重复
    matched_html_indices = set()

    for db_match_id, db_home, db_away, db_date in db_matches:
        best_match = None
        best_score = 0
        best_html_idx = -1

        for html_idx, html_match in enumerate(html_matches):
            # 跳过已匹配的 HTML
            if html_idx in matched_html_indices:
                continue

            # 计算主客队相似度
            home_score = matcher.calculate_similarity(db_home, html_match.home)
            away_score = matcher.calculate_similarity(db_away, html_match.away)

            # 必须两队都 > 0.95
            if home_score > 0.95 and away_score > 0.95:
                avg_score = (home_score + away_score) / 2

                if avg_score > best_score:
                    best_score = avg_score
                    best_match = html_match
                    best_html_idx = html_idx

        if best_match:
            matched_html_indices.add(best_html_idx)
            matched.append(MappingResult(
                match_id=db_match_id,
                url=best_match.full_url,
                db_home=db_home,
                db_away=db_away,
                html_home=best_match.home,
                html_away=best_match.away,
                home_score=0,  # 稍后填充
                away_score=0,
                league=league,
                season=season
            ))

    logger.info(f"  精准映射完成: {len(matched)}/{len(db_matches)} 条匹配")

    return matched


# ============================================================================
# 并发 URL 验证
# ============================================================================

async def validate_urls_batch(urls: List[str], concurrency: int = 12) -> Dict[str, bool]:
    """
    批量验证 URL 可访问性

    Args:
        urls: URL 列表
        concurrency: 并发数

    Returns:
        Dict of {url: is_valid}
    """
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
    logger.info("V78.0 Great Mapping - 五年大巡航引擎")
    logger.info("=" * 60)

    # 统计变量
    total_scanned = 0
    total_mapped = 0
    total_updated = 0
    all_mapping_results = []

    # 第一阶段：构建 25 个巡航坐标
    coordinates = build_cruise_coordinates()

    # 第二阶段：工业级 HTML 提取（8 并发）
    logger.info(f"\n{'=' * 60}")
    logger.info(f"第二阶段：工业级 HTML 提取（8 Worker 并发）")
    logger.info(f"{'=' * 60}")

    scrape_results = await scrape_all_pages_concurrent(coordinates, concurrency=8)

    # 统计提取结果
    for key, matches in scrape_results.items():
        logger.info(f"  {key}: {len(matches)} 个 URL")
        total_scanned += len(matches)

    # 第三阶段：1-on-1 精准映射
    logger.info(f"\n{'=' * 60}")
    logger.info(f"第三阶段：1-on-1 精准映射")
    logger.info(f"{'=' * 60}")

    for coord in coordinates:
        key = f"{coord.league} {coord.season}"

        # 获取该联赛赛季的数据库记录
        db_matches = get_matches_without_url(coord.league, coord.season)

        if not db_matches:
            logger.info(f"\n{key}: 无需匹配（全部已有 URL）")
            continue

        html_matches = scrape_results.get(key, [])

        if not html_matches:
            logger.warning(f"\n{key}: HTML 中未找到比赛，跳过")
            continue

        logger.info(f"\n处理: {key}")
        logger.info(f"  数据库未匹配: {len(db_matches)} 场")
        logger.info(f"  HTML 提取: {len(html_matches)} 个")

        # 执行精准映射
        mapped = precision_map(db_matches, html_matches, coord.league, coord.season)

        if not mapped:
            logger.info(f"  无匹配结果")
            continue

        # 验证 URL
        urls = [m.url for m in mapped]
        logger.info(f"  验证 {len(urls)} 个 URL...")

        validation_results = await validate_urls_batch(urls)
        valid_count = sum(1 for v in validation_results.values() if v)
        logger.info(f"  有效 URL: {valid_count}/{len(validation_results)}")

        # 批量更新数据库
        updates = [
            {'match_id': m.match_id, 'url': m.url}
            for m in mapped
            if validation_results.get(m.url, False)
        ]

        if updates:
            updated = update_match_url_batch(updates)
            logger.info(f"  数据库更新: {updated} 条")
            total_updated += updated

        total_mapped += len(mapped)
        all_mapping_results.extend(mapped)

        # 避免过载
        await asyncio.sleep(1)

    # 输出最终报告
    logger.info(f"\n{'=' * 60}")
    logger.info("V78.0 五年大巡航 - 最终报告")
    logger.info(f"{'=' * 60}")
    logger.info(f"扫描页面: {len(coordinates)}")
    logger.info(f"提取 URL: {total_scanned}")
    logger.info(f"成功映射: {total_mapped}")
    logger.info(f"数据库更新: {total_updated}")

    # 检查最终填充率
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

    # 保存映射结果用于验证
    if all_mapping_results:
        with open('audit_temp/v78_mapping_results.json', 'w') as f:
            import json
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_scanned': total_scanned,
                'total_mapped': total_mapped,
                'total_updated': total_updated,
                'records': [
                    {
                        'match_id': m.match_id,
                        'url': m.url,
                        'db_home': m.db_home,
                        'db_away': m.db_away,
                        'html_home': m.html_home,
                        'html_away': m.html_away,
                        'league': m.league,
                        'season': m.season,
                    }
                    for m in all_mapping_results[:100]  # 保存前 100 条
                ]
            }, f, indent=2)
        logger.info(f"\n映射结果已保存: audit_temp/v78_mapping_results.json")


if __name__ == "__main__":
    asyncio.run(main())
