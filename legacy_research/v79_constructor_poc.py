#!/usr/bin/env python3
"""
V79.0 Constructor Engine - 构造与校验引擎

核心思路：不再依赖 HTML 提取，直接基于球队名称构造 URL
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

sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v79_constructor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 第一阶段：球队名称翻译官
# ============================================================================

def normalize_team_name_v2(team_name: str) -> str:
    """
    V2.0 球队名称标准化 - 升级版

    处理逻辑：
    1. 移除常见干扰词 (FC, Utd, CF, St, etc.)
    2. 变音符号转义 (ö -> o)
    3. 连字符替换空格
    4. 特殊队名映射
    """
    if not team_name:
        return ""

    # 移除常见干扰词
    prefixes_to_remove = ['FC ', 'CF ', 'RCD ', 'SS ', 'US ', 'SD ', 'AJA ', 'SK ']
    suffixes_to_remove = [' FC', ' CF', ' Utd', ' United', ' City', ' Town',
                          ' Albion', ' Rovers', ' Wanderers', ' Athletic',
                          ' Hotspur', ' Hammers', ' Villa', ' Palace']

    normalized = team_name

    # 移除前缀
    for prefix in prefixes_to_remove:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break

    # 移除后缀
    for suffix in suffixes_to_remove:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
            break

    # 移除变音符号
    normalized = unicodedata.normalize('NFKD', normalized)
    normalized = normalized.encode('ASCII', 'ignore').decode('ASCII')

    # 转小写
    normalized = normalized.lower()

    # 替换特殊字符为连字符
    normalized = re.sub(r'[\s.]+', '-', normalized)

    # 移除开头/结尾的连字符
    normalized = normalized.strip('-')

    return normalized


# 特殊队名映射表
SPECIAL_TEAM_MAPPINGS = {
    # 德语特殊处理
    "Bayern München": "bayern-munich",
    "Borussia Mönchengladbach": "borussia-monchengladbach",
    "1. FC Union Berlin": "union-berlin",
    "1. FC Köln": "koln",
    "FSV Mainz 05": "mainz",
    "SC Freiburg": "freiburg",
    "VfB Stuttgart": "stuttgart",
    "VfL Bochum": "bochum",
    "VfL Wolfsburg": "wolfsburg",

    # 意大利特殊处理
    "AC Milan": "ac-milan",
    "Inter Milan": "inter",
    "AS Roma": "roma",
    "SS Lazio": "lazio",
    "SSC Napoli": "napoli",
    "Hellas Verona": "verona",
    "Atalanta BC": "atalanta",

    # 西班牙特殊处理
    "Real Madrid": "real-madrid",
    "Atlético Madrid": "atletico-madrid",
    "Athletic Bilbao": "athletic-bilbao",
    "Real Betis": "real-betis",
    "Real Sociedad": "real-sociedad",
    "RC Celta": "celta",
    "CD Leganés": "leganes",
    "Rayo Vallecano": "rayo-vallecano",
    "UD Las Palmas": "las-palmas",

    # 法国特殊处理
    "Paris Saint-Germain": "psg",
    "AS Monaco": "monaco",
    "Saint-Étienne": "st-etienne",
    "FC Metz": "metz",

    # 英格兰特殊处理
    "Manchester United": "man-utd",
    "Manchester City": "man-city",
    "Tottenham Hotspur": "spurs",
    "West Ham United": "west-ham",
    "Newcastle United": "newcastle",
    "Brighton & Hove Albion": "brighton",
    "Wolverhampton Wanderers": "wolves",
    "Nottingham Forest": "nottm-forest",
    "Sheffield United": "sheffield-utd",
}


def normalize_team_name_advanced(team_name: str) -> str:
    """
    高级球队名称标准化 - 使用映射表

    Args:
        team_name: 原始球队名称

    Returns:
        标准化后的球队名称（用于 URL 构造）
    """
    # 先检查映射表
    if team_name in SPECIAL_TEAM_MAPPINGS:
        return SPECIAL_TEAM_MAPPINGS[team_name]

    # 使用 V2.0 标准化
    return normalize_team_name_v2(team_name)


# ============================================================================
# 联赛配置
# ============================================================================

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
        "laliga": "laliga",
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


def construct_url_directly(league: str, season: str, home_team: str, away_team: str) -> str:
    """
    直接构造 URL（不含哈希 ID）

    Args:
        league: 联赛名称
        season: 赛季 (如 "20/21")
        home_team: 主队名称
        away_team: 客队名称

    Returns:
        完整的 OddsPortal URL
    """
    if league not in LEAGUE_CONFIG:
        logger.warning(f"未知联赛: {league}")
        return ""

    config = LEAGUE_CONFIG[league]
    country = config["country"]
    league_slug = config["slug"]

    # 赛季格式转换: 20/21 -> 2020-2021
    season_parts = season.split('/')
    season_url = f"20{season_parts[0]}-20{season_parts[1]}"

    # 标准化球队名称
    home_norm = normalize_team_name_advanced(home_team)
    away_norm = normalize_team_name_advanced(away_team)

    # 构造 URL（不含哈希 ID）
    url = f"https://www.oddsportal.com/football/{country}/{league_slug}-{season_url}/{home_norm}-{away_norm}/"

    return url


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


def get_sample_matches(limit: int = 5) -> List[Tuple]:
    """
    获取样本比赛用于 PoC 测试

    Returns:
        List of (match_id, league_name, season, home_team, away_team)
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT match_id, league_name, season, home_team, away_team
        FROM matches
        WHERE league_name IN ('Premier League', 'Bundesliga')
          AND oddsportal_url IS NULL
          AND is_finished = true
        ORDER BY RANDOM()
        LIMIT %s
    """, (limit,))

    results = cur.fetchall()

    cur.close()
    conn.close()

    return results


def update_match_url_batch(updates: List[Dict]) -> int:
    """批量更新比赛 URL"""
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
# 第一阶段：PoC 测试
# ============================================================================

async def test_url_accessibility_playwright(url: str) -> Dict:
    """
    使用 Playwright 测试 URL 可访问性

    Args:
        url: 待测试的 URL

    Returns:
        {'url': str, 'accessible': bool, 'final_url': str, 'status_code': int}
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        try:
            # 设置响应监听
            final_url = url
            status_code = None

            async def handle_response(response):
                nonlocal status_code
                if response.status:
                    status_code = response.status

            page.on('response', handle_response)

            # 导航到页面
            response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)

            if response:
                final_url = page.url
                status_code = response.status

            accessible = status_code in [200, 301, 302]

            return {
                'url': url,
                'accessible': accessible,
                'final_url': final_url,
                'status_code': status_code
            }

        except Exception as e:
            return {
                'url': url,
                'accessible': False,
                'final_url': url,
                'status_code': None,
                'error': str(e)
            }

        finally:
            await browser.close()


async def test_url_accessibility_http(url: str, session: aiohttp.ClientSession) -> Dict:
    """
    使用 HTTP HEAD 请求测试 URL 可访问性（更快）

    Args:
        url: 待测试的 URL
        session: aiohttp 会话

    Returns:
        {'url': str, 'accessible': bool, 'final_url': str, 'status_code': int}
    """
    try:
        async with session.head(url, timeout=aiohttp.ClientTimeout(total=15),
                               allow_redirects=True) as response:
            return {
                'url': url,
                'accessible': response.status in [200, 301, 302],
                'final_url': str(response.url),
                'status_code': response.status
            }
    except asyncio.TimeoutError:
        return {
            'url': url,
            'accessible': False,
            'final_url': url,
            'status_code': None,
            'error': 'timeout'
        }
    except Exception as e:
        return {
            'url': url,
            'accessible': False,
            'final_url': url,
            'status_code': None,
            'error': str(e)
        }


async def run_poc_test():
    """运行 PoC 测试"""
    logger.info("=" * 60)
    logger.info("V79.0 第一阶段：PoC 生存探测")
    logger.info("=" * 60)

    # 获取样本比赛
    samples = get_sample_matches(limit=5)

    if not samples:
        logger.error("未找到样本比赛")
        return

    logger.info(f"\n获取到 {len(samples)} 个样本比赛：\n")

    # 构造 URL 并测试
    test_results = []

    async with aiohttp.ClientSession() as session:
        for match_id, league, season, home, away in samples:
            url = construct_url_directly(league, season, home, away)

            logger.info(f"比赛: {home} vs {away}")
            logger.info(f"  联赛: {league} {season}")
            logger.info(f"  构造 URL: {url}")

            # 测试可访问性
            result = await test_url_accessibility_http(url, session)
            test_results.append({
                'match_id': match_id,
                'home': home,
                'away': away,
                'league': league,
                'season': season,
                'url': url,
                'result': result
            })

            if result['accessible']:
                logger.info(f"  ✅ 可访问 (状态码: {result['status_code']})")
                if result['final_url'] != url:
                    logger.info(f"  最终 URL: {result['final_url']}")
            else:
                logger.info(f"  ❌ 不可访问 ({result.get('error', 'N/A')})")

            logger.info("")

    # 统计结果
    accessible_count = sum(1 for r in test_results if r['result']['accessible'])

    logger.info("=" * 60)
    logger.info("PoC 测试结果汇总")
    logger.info("=" * 60)
    logger.info(f"测试样本: {len(test_results)}")
    logger.info(f"可访问: {accessible_count}")
    logger.info(f"成功率: {100 * accessible_count / len(test_results):.1f}%")

    return test_results


# ============================================================================
# 第三阶段：高并发探测
# ============================================================================

async def batch_validate_urls(match_list: List[Tuple], concurrency: int = 12) -> List[Dict]:
    """
    批量验证 URL 可访问性

    Args:
        match_list: List of (match_id, league, season, home, away)
        concurrency: 并发数

    Returns:
        List of {'match_id': str, 'url': str, 'accessible': bool}
    """
    results = []
    semaphore = asyncio.Semaphore(concurrency)

    async def validate_single(session: aiohttp.ClientSession, match_data: Tuple):
        async with semaphore:
            match_id, league, season, home, away = match_data
            url = construct_url_directly(league, season, home, away)

            validation = await test_url_accessibility_http(url, session)

            return {
                'match_id': match_id,
                'url': url,
                'accessible': validation['accessible'],
                'final_url': validation.get('final_url', url),
                'status_code': validation.get('status_code')
            }

    async with aiohttp.ClientSession() as session:
        tasks = []

        for i, match_data in enumerate(match_list):
            tasks.append(validate_single(session, match_data))

            # 每 100 场休息 3-5 秒
            if (i + 1) % 100 == 0:
                logger.info(f"已提交 {i + 1} 个验证任务，休息 3 秒...")
                await asyncio.sleep(3)

        # 执行并发验证
        logger.info(f"开始并发验证 {len(tasks)} 个 URL...")
        results = await asyncio.gather(*tasks)

    return results


async def main_full_scan():
    """完整扫描流程"""
    logger.info("=" * 60)
    logger.info("V79.0 Constructor Engine - 完整扫描")
    logger.info("=" * 60)

    # 获取所有无 URL 的比赛
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT match_id, league_name, season, home_team, away_team
        FROM matches
        WHERE oddsportal_url IS NULL
          AND league_name IN ('Premier League', 'Bundesliga', 'La Liga', 'Serie A', 'Ligue 1')
        ORDER BY league_name, season
    """)

    all_matches = cur.fetchall()

    cur.close()
    conn.close()

    logger.info(f"\n待处理比赛数: {len(all_matches)}")

    if not all_matches:
        logger.info("所有比赛已有 URL，无需处理")
        return

    # 批量验证
    validation_results = await batch_validate_urls(all_matches, concurrency=12)

    # 统计结果
    accessible = [r for r in validation_results if r['accessible']]
    inaccessible = [r for r in validation_results if not r['accessible']]

    logger.info(f"\n{'=' * 60}")
    logger.info("验证结果汇总")
    logger.info(f"{'=' * 60}")
    logger.info(f"总验证数: {len(validation_results)}")
    logger.info(f"可访问: {len(accessible)} ({100 * len(accessible) / len(validation_results):.1f}%)")
    logger.info(f"不可访问: {len(inaccessible)} ({100 * len(inaccessible) / len(validation_results):.1f}%)")

    # 批量更新可访问的 URL
    updates = [
        {'match_id': r['match_id'], 'url': r['final_url']}
        for r in accessible
    ]

    if updates:
        logger.info(f"\n开始批量更新 {len(updates)} 条记录...")
        updated = update_match_url_batch(updates)
        logger.info(f"成功更新: {updated} 条")

    # 最终统计
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

    logger.info(f"\n{'=' * 60}")
    logger.info("最终填充率")
    logger.info(f"{'=' * 60}")
    logger.info(f"总比赛: {result[0]}")
    logger.info(f"有 URL: {result[1]}")
    logger.info(f"填充率: {result[2]}%")


# ============================================================================
# 主入口
# ============================================================================

async def main():
    """主函数"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--poc':
        # PoC 测试模式
        await run_poc_test()
    else:
        # 完整扫描模式
        await main_full_scan()


if __name__ == "__main__":
    asyncio.run(main())
