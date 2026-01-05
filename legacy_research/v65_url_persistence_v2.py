#!/usr/bin/env python3
"""
V65.0 URL Persistence V2 - 改进的 URL 解析与持久化

关键改进：
1. 使用更智能的球队名称解析（处理多连字符情况）
2. 使用模糊匹配来匹配数据库记录
3. 直接从 URL 中提取完整的球队信息
"""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path

import psycopg2
from playwright.async_api import async_playwright

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v65_url_persistence_v2.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 球队名称映射（OddsPortal → 数据库）
# ============================================================================

TEAM_NAME_MAP = {
    # 德甲球队
    "bayer leverkusen": "Bayer Leverkusen",
    "bayern munich": "Bayern München",
    "borussia dortmund": "Borussia Dortmund",
    "borussia monchengladbach": "Borussia Mönchengladbach",
    "b. monchengladbach": "Borussia Mönchengladbach",
    "eintracht frankfurt": "Eintracht Frankfurt",
    "fc heidenheim": "FC Heidenheim",
    "heidenheim": "FC Heidenheim",
    "hoffenheim": "TSG Hoffenheim",
    "rb leipzig": "RB Leipzig",
    "union berlin": "Union Berlin",
    "vfb stuttgart": "VfB Stuttgart",
    "stuttgart": "VfB Stuttgart",
    "werder bremen": "Werder Bremen",
    "wolfsburg": "VfL Wolfsburg",
    "mainz": "Mainz 05",
    "1. fc koln": "1. FC Köln",
    "fc koln": "1. FC Köln",
    "freiburg": "SC Freiburg",
    "bochum": "VfL Bochum",
    "darmstadt": "Darmstadt 98",
    "augsburg": "FC Augsburg",
}


def parse_match_url(url_path: str) -> dict | None:
    """解析 OddsPortal match URL，提取球队信息

    URL 格式: /football/germany/bundesliga-2023-2024/home-team-away-team-XXXXXX/

    Args:
        url_path: URL 路径

    Returns:
        包含 home_team, away_team, full_url 的字典，或 None
    """
    try:
        # 提取比赛部分
        parts = url_path.strip('/').split('/')
        if len(parts) < 2:
            return None

        match_part = parts[-1]

        # 移除 hash 部分（7位大写字母）
        match_part = re.sub(r'-[A-Z]{7,}$', '', match_part)

        # 解析球队名称
        # 策略：使用已知的球队名称列表来智能分割
        teams = []
        current_team = []

        for part in match_part.split('-'):
            possible_team = '-'.join(current_team + [part]).lower()

            # 检查是否是已知球队
            is_known_team = any(
                possible_team == known.lower() or
                possible_team in known.lower() or
                known.lower() in possible_team
                for known in TEAM_NAME_MAP.values()
            )

            if is_known_team or len(current_team) == 0:
                current_team.append(part)
            else:
                # 当前的 team 组合完成，保存并开始新的
                if current_team:
                    teams.append('-'.join(current_team))
                current_team = [part]

        # 添加最后一个球队
        if current_team:
            teams.append('-'.join(current_team))

        if len(teams) >= 2:
            home_raw = teams[0]
            away_raw = '-'.join(teams[1:])

            # 标准化球队名称
            home_team = TEAM_NAME_MAP.get(home_raw.lower(), home_raw.title())
            away_team = TEAM_NAME_MAP.get(away_raw.lower(), away_raw.title())

            return {
                'home_team': home_team,
                'away_team': away_team,
                'url_path': url_path,
                'full_url': f"https://www.oddsportal.com{url_path}"
            }

    except Exception as e:
        logger.debug(f"URL 解析失败: {url_path}, 错误: {e}")

    return None


def find_match_in_db(conn, league: str, season: str, home_team: str, away_team: str) -> list:
    """在数据库中查找匹配的比赛

    使用模糊匹配策略
    """
    cursor = conn.cursor()

    # 调试：检查连接的数据库
    cursor.execute("SELECT current_database()")
    db_name = cursor.fetchone()[0]
    logger.debug(f"[DB] Current database: {db_name}")

    # 尝试多种匹配模式
    patterns = [
        # 精确匹配
        (home_team, away_team),
        # 模糊匹配（包含关系）
        (f"%{home_team}%", f"%{away_team}%"),
    ]

    for ht_pattern, at_pattern in patterns:
        cursor.execute("""
            SELECT match_id, home_team, away_team, match_date
            FROM public.matches
            WHERE league_name = %s
              AND season = %s
              AND home_team ILIKE %s
              AND away_team ILIKE %s
            LIMIT 3
        """, (league, season, ht_pattern, at_pattern))

        results = cursor.fetchall()
        if results:
            cursor.close()
            return results

    cursor.close()
    return []


async def persist_urls_for_season(results_url: str, league: str, season: str):
    """为指定赛季发现并持久化 URL"""
    logger.info("")
    logger.info("-" * 60)
    logger.info(f"目标: {league} {season}")
    logger.info(f"Results URL: {results_url}")
    logger.info("-" * 60)

    # 直接连接到正确的数据库
    conn = psycopg2.connect(
        host="localhost",
        port="5432",
        database="football_prediction_dev",
        user="football_user",
        password="football_pass",
    )
    logger.info(f"[DB] Connected to: football_prediction_dev")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        page = await context.new_page()

        try:
            await page.goto(results_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(5)

            # 提取所有比赛 URL
            url_data = await page.evaluate("""
                () => {
                    const results = [];
                    const links = document.querySelectorAll('a[href]');

                    for (const link of links) {
                        const href = link.getAttribute('href');

                        if (href &&
                            href.includes('bundesliga-2023-2024') &&
                            !href.includes('/standings') &&
                            !href.includes('/outrights')) {

                            const text = link.textContent || '';
                            if (text.match(/\\d+\\s*[–:-]\\s*\\d+/)) {
                                results.push(href);
                            }
                        }
                    }

                    return results;
                }
            """)

            logger.info(f"[Discovery] 找到 {len(url_data)} 场比赛")

            persisted_count = 0

            for url_path in url_data:
                # 解析 URL
                match_info = parse_match_url(url_path)

                if not match_info:
                    continue

                # 查找数据库中的比赛
                db_matches = find_match_in_db(
                    conn, league, season,
                    match_info['home_team'],
                    match_info['away_team']
                )

                if db_matches:
                    for match_id, db_home, db_away, match_date in db_matches:
                        # 验证匹配
                        if (match_info['home_team'].lower() in db_home.lower() and
                            match_info['away_team'].lower() in db_away.lower()):

                            # 存储 URL
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE matches
                                SET oddsportal_url = %s,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE match_id = %s
                            """, (match_info['full_url'], match_id))

                            conn.commit()
                            cursor.close()

                            persisted_count += 1
                            logger.info(f"[Persist] {db_home} vs {db_away}")
                            break

            logger.info(f"[Summary] 持久化成功: {persisted_count} 场")

        finally:
            await page.close()
            await browser.close()

    conn.close()

    return persisted_count


async def main():
    """主程序"""
    logger.info("=" * 80)
    logger.info("V65.0 URL Persistence V2 - 改进版")
    logger.info("=" * 80)

    total_persisted = 0

    # 德甲 23/24 赛季
    persisted = await persist_urls_for_season(
        results_url="https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/",
        league="Bundesliga",
        season="23/24"
    )
    total_persisted += persisted

    logger.info("")
    logger.info("=" * 80)
    logger.info(f"✅ 完成！总计持久化: {total_persisted} 场比赛")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
