#!/usr/bin/env python3
"""
V75.0 URL Builder - 工业化构建系统

核心策略：
1. 标准化映射 - 球队名称归一化
2. HTML 源码提取 - 正则暴力提取哈希 ID
3. 并发生命校验 - 12 协程验证 URL
"""

import asyncio
import logging
import re
import sys
import unicodedata
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from urllib.parse import quote

import aiohttp
import psycopg2
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v75_url_builder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 第一阶段：标准化映射
# ============================================================================

# 联赛标准化映射
LEAGUE_MAPPING = {
    "Premier League": {
        "country": "england",
        "slug": "premier-league"
    },
    "Bundesliga": {
        "country": "germany",
        "slug": "bundesliga"
    },
    "La Liga": {
        "country": "spain",
        "slug": "laliga"
    },
    "Serie A": {
        "country": "italy",
        "slug": "serie-a"
    },
    "Ligue 1": {
        "country": "france",
        "slug": "ligue-1"
    }
}

# 球队名称标准化映射（常见缩写、变音符号处理）
TEAM_NORMALIZATION = {
    # 德甲
    "Bayern Munich": "bayern-munich",
    "Bayern München": "bayern-munich",
    "Bayer Leverkusen": "bayer-leverkusen",
    "Borussia Dortmund": "borussia-dortmund",
    "Borussia Mönchengladbach": "borussia-moenchengladbach",
    "Union Berlin": "union-berlin",
    "RB Leipzig": "rb-leipzig",
    "VfB Stuttgart": "vfb-stuttgart",
    "Eintracht Frankfurt": "eintracht-frankfurt",
    "Werder Bremen": "werder-bremen",
    "VfL Wolfsburg": "vfl-wolfsburg",
    "SC Freiburg": "sc-freiburg",
    "Mainz": "mainz-05",
    "Mainz 05": "mainz-05",
    "1. FC Köln": "fc-koeln",
    "FC Koln": "fc-koeln",
    "TSG Hoffenheim": "tsg-hoffenheim",
    "VfL Bochum": "vfl-bochum",
    "FC Augsburg": "fc-augsburg",
    "Heidenheim": "fc-heidenheim",
    "Darmstadt": "darmstadt",

    # 英超
    "Manchester City": "manchester-city",
    "Manchester United": "manchester-united",
    "Man United": "manchester-united",
    "Liverpool": "liverpool",
    "Chelsea": "chelsea",
    "Arsenal": "arsenal",
    "Tottenham": "tottenham",
    "Tottenham Hotspur": "tottenham",
    "West Ham": "west-ham",
    "Newcastle": "newcastle",
    "Aston Villa": "aston-villa",
    "Brighton": "brighton",
    "Wolves": "wolves",
    "Wolverhampton": "wolves",
    "Crystal Palace": "crystal-palace",
    "Bournemouth": "bournemouth",
    "Fulham": "fulham",
    "Leeds": "leeds",
    "Southampton": "southampton",
    "Nottingham Forest": "nottingham-forest",
    "Leicester": "leicester",
    "Everton": "everton",
    "Luton": "luton",
    "Burnley": "burnley",
    "Sheffield United": "sheffield-united",
    "West Brom": "west-brom",

    # 西甲
    "Real Madrid": "real-madrid",
    "Barcelona": "barcelona",
    "FC Barcelona": "barcelona",
    "Atletico Madrid": "atletico-madrid",
    "Atletico": "atletico-madrid",
    "Sevilla": "sevilla",
    "Real Betis": "real-betis",
    "Valencia": "valencia",
    "Athletic Bilbao": "athletic-bilbao",
    "Real Sociedad": "real-sociedad",
    "Villarreal": "villarreal",
    "Real Valladolid": "real-valladolid",
    "Getafe": "getafe",
    "Mallorca": "mallorca",
    "Rayo Vallecano": "rayo-vallecano",
    "Osasuna": "osasuna",
    "Almeria": "almeria",
    "Espanyol": "espanyol",
    "Leganes": "leganes",
    "Cádiz": "cadiz",

    # 意甲
    "Juventus": "juventus",
    "Inter": "inter",
    "Inter Milan": "inter",
    "AC Milan": "milan",
    "Milan": "milan",
    "Napoli": "napoli",
    "Roma": "roma",
    "AS Roma": "roma",
    "Lazio": "lazio",
    "Atalanta": "atalanta",
    "Fiorentina": "fiorentina",
    "Torino": "torino",
    "Bologna": "bologna",
    "Sassuolo": "sassuolo",
    "Udinese": "udinese",
    "Genoa": "genoa",
    "Verona": "verona",
    "Hellas Verona": "verona",
    "Cremonese": "cremonese",
    "Monza": "monza",
    "Lecce": "lecce",
    "Cagliari": "cagliari",
    "Empoli": "empoli",
    "Salernitana": "salernitana",

    # 法甲
    "PSG": "psg",
    "Paris Saint-Germain": "psg",
    "Monaco": "monaco",
    "Marseille": "marseille",
    "Olympique Marseille": "marseille",
    "Lyon": "lyon",
    "Olympique Lyon": "lyon",
    "Rennes": "rennes",
    "Lorient": "lorient",
    "Nice": "nice",
    "Saint-Etienne": "saint-etienne",
    "Nantes": "nantes",
    "Montpellier": "montpellier",
    "Strasbourg": "strasbourg",
    "Brest": "brest",
    "Reims": "reims",
    "Toulouse": "toulouse",
    "Metz": "metz",
    "Lille": "lille",
    "Lens": "lens",
}


def normalize_team_name(team_name: str) -> str:
    """
    标准化球队名称为 OddsPortal URL 格式

    处理步骤：
    1. 移除变音符号 (ü->u, ö->o)
    2. 转小写
    3. 替换空格和特殊字符为连字符
    4. 查找映射表
    """
    if not team_name:
        return "unknown"

    # 1. 查找直接映射
    if team_name in TEAM_NORMALIZATION:
        return TEAM_NORMALIZATION[team_name]

    # 2. 移除变音符号
    normalized = unicodedata.normalize('NFKD', team_name)
    ascii_version = normalized.encode('ASCII', 'ignore').decode('ASCII')

    # 3. 转小写
    ascii_version = ascii_version.lower()

    # 4. 移除特殊字符，替换空格和点为连字符
    ascii_version = re.sub(r'[^\w\s-]', '', ascii_version)
    ascii_version = re.sub(r'[\s.]+', '-', ascii_version)
    ascii_version = re.sub(r'-+', '-', ascii_version).strip('-')

    return ascii_version if ascii_version else "unknown"


def construct_oddsportal_url(league: str, season: str, home_team: str, away_team: str, match_id: str = None) -> str:
    """
    构造 OddsPortal URL

    Args:
        league: 联赛名称
        season: 赛季 (如 "24/25")
        home_team: 主队名称
        away_team: 客队名称
        match_id: 可选的 7-8 位哈希 ID

    Returns:
        完整的 OddsPortal URL
    """
    if league not in LEAGUE_MAPPING:
        logger.warning(f"未知联赛: {league}")
        return None

    # 获取联赛信息
    league_info = LEAGUE_MAPPING[league]

    # 标准化赛季
    season_normalized = season.replace('/', '-')

    # 标准化球队名称
    home_normalized = normalize_team_name(home_team)
    away_normalized = normalize_team_name(away_team)

    # 构造 URL
    base_url = f"https://www.oddsportal.com/football/{league_info['country']}/{league_info['slug']}-{season_normalized}/{home_normalized}-{away_normalized}"

    # 如果有 match_id，添加到 URL 末尾
    if match_id:
        return f"{base_url}-{match_id}/"
    else:
        return f"{base_url}/"


# ============================================================================
# 第二阶段：HTML 源码暴力提取
# ============================================================================

async def extract_match_ids_from_html(html_content: str) -> List[Dict[str, str]]:
    """
    从 HTML 源码中暴力提取比赛 ID

    使用正则表达式直接匹配模式：
    /football/xxxxx/xxxxx/xxxx-xxxx-xxxxxxxx/
    """
    results = []

    # 正则模式：匹配 OddsPortal 比赛页面 URL
    # 模式：/football/country/league-season/home-away-xxxxxxx/
    pattern = r'"/football/[^"]+?/[^"]+?/[^-]+-[^"]+?-([a-z0-9]{7,8})/"'

    matches = re.findall(pattern, html_content, re.IGNORECASE)

    for match_id in matches:
        if match_id not in [r['match_id'] for r in results]:
            results.append({
                'match_id': match_id.lower(),
                'source': 'html_regex'
            })

    return results


async def scrape_results_page(url: str) -> str:
    """访问 Results 页面并返回 HTML 源码"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)  # 等待 JS 渲染

            html = await page.content()
            return html

        finally:
            await browser.close()


# ============================================================================
# 第三阶段：并发生命校验
# ============================================================================

async def validate_url(session: aiohttp.ClientSession, url: str) -> bool:
    """验证 URL 是否有效（HTTP HEAD 请求）"""
    try:
        async with session.head(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            return response.status == 200
    except Exception as e:
        logger.debug(f"URL 验证失败: {url} - {e}")
        return False


async def batch_validate_urls(urls: List[str], concurrency: int = 12) -> Dict[str, bool]:
    """
    批量验证 URL（并发控制）

    Args:
        urls: URL 列表
        concurrency: 并发数（默认 12）

    Returns:
        {url: is_valid} 映射字典
    """
    results = {}
    semaphore = asyncio.Semaphore(concurrency)

    async def validate_with_semaphore(session: aiohttp.ClientSession, url: str):
        async with semaphore:
            is_valid = await validate_url(session, url)
            results[url] = is_valid
            return url, is_valid

    async with aiohttp.ClientSession() as session:
        tasks = [validate_with_semaphore(session, url) for url in urls]
        await asyncio.gather(*tasks)

    return results


# ============================================================================
# 主引擎
# ============================================================================

async def main():
    """主函数 - 执行完整流程"""
    logger.info("=" * 60)
    logger.info("V75.0 工业化构建系统")
    logger.info("=" * 60)

    # 测试标准化函数
    logger.info("\n第一阶段：测试标准化映射")
    test_teams = [
        ("Bundesliga", "24/25", "Bayern Munich", "Mainz"),
        ("Premier League", "23/24", "Manchester United", "Liverpool"),
        ("La Liga", "24/25", "Real Madrid", "Barcelona"),
    ]

    for league, season, home, away in test_teams:
        url = construct_oddsportal_url(league, season, home, away)
        logger.info(f"  {home} vs {away}: {url}")

    # 测试 HTML 提取
    logger.info("\n第二阶段：测试 HTML 提取")
    test_url = "https://www.oddsportal.com/football/germany/bundesliga-2024-2025/results/"

    logger.info(f"正在访问: {test_url}")
    html = await scrape_results_page(test_url)

    logger.info(f"HTML 大小: {len(html)} 字符")

    match_ids = await extract_match_ids_from_html(html)
    logger.info(f"提取到 {len(match_ids)} 个比赛 ID")

    if match_ids:
        logger.info("前 10 个 ID:")
        for i, match_info in enumerate(match_ids[:10], 1):
            logger.info(f"  [{i}] {match_info['match_id']}")

    logger.info("\nV75.0 测试完成")


if __name__ == "__main__":
    asyncio.run(main())
