#!/usr/bin/env python3
"""
V66.0 Extended Radar - 扩展扫描更多赛季

目标：扫描所有主要联赛的最近 5 个赛季，达到 1000+ URL
"""

import asyncio
import logging
import re
import sys
from pathlib import Path

import psycopg2
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s]',
    handlers=[
        logging.FileHandler('logs/v66_extended_radar.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# 宽松的球队名称匹配
TEAM_MAP = {
    # 德甲
    "leverkusen": ["Bayer Leverkusen"],
    "bayern": ["Bayern München", "Bayern Munich"],
    "munchen": ["Bayern München"],
    "dortmund": ["Borussia Dortmund"],
    "monchengladbach": ["Borussia Mönchengladbach"],
    "frankfurt": ["Eintracht Frankfurt"],
    "heidenheim": ["FC Heidenheim"],
    "hoffenheim": ["TSG Hoffenheim"],
    "leipzig": ["RB Leipzig"],
    "union": ["Union Berlin"],
    "stuttgart": ["VfB Stuttgart"],
    "bremen": ["Werder Bremen"],
    "wolfsburg": ["VfL Wolfsburg"],
    "mainz": ["Mainz 05"],
    "koln": ["1. FC Köln"],
    "freiburg": ["SC Freiburg"],
    "bochum": ["VfL Bochum"],
    "darmstadt": ["Darmstadt 98"],
    "augsburg": ["FC Augsburg"],
    "hertha": ["Hertha BSC"],
    "schalke": ["FC Schalke 04"],
    "bielefeld": ["Arminia Bielefeld"],
    "furth": ["Greuther Fürth"],
    "paderborn": ["SC Paderborn"],

    # 英超
    "city": ["Manchester City"],
    "united": ["Manchester United"],
    "liverpool": ["Liverpool"],
    "chelsea": ["Chelsea"],
    "arsenal": ["Arsenal"],
    "tottenham": ["Tottenham Hotspur"],
    "west ham": ["West Ham United"],
    "leicester": ["Leicester City"],
    "everton": ["Everton"],
    "newcastle": ["Newcastle United"],
    "aston villa": ["Aston Villa"],
    "wolves": ["Wolverhampton Wanderers"],
    "palace": ["Crystal Palace"],
    "bournemouth": ["AFC Bournemouth"],
    "fulham": ["Fulham"],
    "brighton": ["Brighton & Hove Albion"],
    "leeds": ["Leeds United"],
    "southampton": ["Southampton"],
    "nottingham": ["Nottingham Forest"],
    "luton": ["Luton Town"],
    "burnley": ["Burnley"],
    "sheffield": ["Sheffield United"],
    "watford": ["Watford"],
    "west brom": ["West Bromwich Albion"],
    "norwich": ["Norwich City"],
}


def fuzzy_match(team_raw: str, db_team: str) -> bool:
    """模糊匹配"""
    team_lower = team_raw.lower()

    for key, possible_names in TEAM_MAP.items():
        if key in team_lower:
            for possible in possible_names:
                if possible.lower() in db_team.lower():
                    return True

    return False


async def extended_scan():
    """扩展扫描"""
    logger.info("=" * 80)
    logger.info("V66.0 Extended Radar - 扫描更多赛季")
    logger.info("=" * 80)

    conn = psycopg2.connect(
        host="127.0.0.1",
        port="5432",
        database="football_prediction_dev",
        user="football_user",
        password="football_pass",
    )
    cursor = conn.cursor()

    # 初始状态
    cursor.execute("SELECT COUNT(*) FROM matches WHERE oddsportal_url IS NOT NULL")
    initial_count = cursor.fetchone()[0]
    logger.info(f"📊 初始 URL: {initial_count}")

    # 扩展目标列表
    targets = [
        # 英超
        ("Premier League", "2020-2021", "20/21", "https://www.oddsportal.com/football/england/premier-league-2020-2021/results/"),
        ("Premier League", "2021-2022", "21/22", "https://www.oddsportal.com/football/england/premier-league-2021-2022/results/"),
        ("Premier League", "2022-2023", "22/23", "https://www.oddsportal.com/football/england/premier-league-2022-2023/results/"),
        ("Premier League", "2023-2024", "23/24", "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"),

        # 德甲
        ("Bundesliga", "2020-2021", "20/21", "https://www.oddsportal.com/football/germany/bundesliga-2020-2021/results/"),
        ("Bundesliga", "2021-2022", "21/22", "https://www.oddsportal.com/football/germany/bundesliga-2021-2022/results/"),
        ("Bundesliga", "2022-2023", "22/23", "https://www.oddsportal.com/football/germany/bundesliga-2022-2023/results/"),
        ("Bundesliga", "2023-2024", "23/24", "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/"),
    ]

    total_persisted = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        for league, url_season, db_season, results_url in targets:
            logger.info(f"\n[扫描] {league} {url_season}")

            page = await context.new_page()

            try:
                await page.goto(results_url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(5)

                # 提取 URL
                url_data = await page.evaluate("""
                    () => {
                        const results = [];
                        const links = document.querySelectorAll('a[href]');

                        for (const link of links) {
                            const href = link.getAttribute('href');
                            const text = link.textContent || '';

                            if (href && !href.includes('/standings') && !href.includes('/outrights')) {
                                if (text.match(/\\d+\\s*[–:-]\\s*\\d+/)) {
                                    results.push({
                                        href: href,
                                        text: text.trim()
                                    });
                                }
                            }
                        }

                        return results;
                    }
                """)

                logger.info(f"  发现 {len(url_data)} 场比赛")

                persisted = 0

                # 获取该联赛该赛季所有未匹配的比赛
                cursor.execute("""
                    SELECT match_id, home_team, away_team
                    FROM matches
                    WHERE league_name = %s
                      AND season = %s
                      AND oddsportal_url IS NULL
                    LIMIT 50
                """, (league, db_season))

                unmatched_matches = cursor.fetchall()
                logger.info(f"  数据库中未匹配: {len(unmatched_matches)} 场")

                for url_item in url_data:
                    url_path = url_item['href']
                    full_url = f"https://www.oddsportal.com{url_path}"

                    # 解析球队
                    match_part = url_path.strip('/').split('/')[-1]
                    match_part = re.sub(r'-[A-Z]{7,}$', '', match_part)
                    teams = match_part.split('-')

                    if len(teams) < 2:
                        continue

                    # 尝试匹配
                    for match_id, db_home, db_away in unmatched_matches:
                        match_found = False

                        for split_idx in range(1, min(len(teams), 4)):
                            home_raw = '-'.join(teams[:split_idx])
                            away_raw = '-'.join(teams[split_idx:])

                            if fuzzy_match(home_raw, db_home) and fuzzy_match(away_raw, db_away):
                                cursor.execute("""
                                    UPDATE matches
                                    SET oddsportal_url = %s,
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE match_id = %s
                                """, (full_url, match_id))

                                conn.commit()
                                persisted += 1
                                total_persisted += 1
                                match_found = True

                                if persisted % 10 == 0:
                                    logger.info(f"  已持久化: {persisted}")

                                break

                        if match_found:
                            # 从列表中移除已匹配的
                            unmatched_matches = [(m, h, a) for m, h, a in unmatched_matches if m != match_id]
                            break

                logger.info(f"  ✅ 本轮持久化: {persisted} 个 URL")

            except Exception as e:
                logger.error(f"  ❌ 错误: {e}")

            finally:
                await page.close()

            # 检查进度
            cursor.execute("SELECT COUNT(*) FROM matches WHERE oddsportal_url IS NOT NULL")
            current = cursor.fetchone()[0]
            logger.info(f"  当前进度: {current} 个 URL")

            if current >= 1000:
                logger.info("\n🎉 已达到 1000 目标！")
                break

        await browser.close()

    # 最终报告
    cursor.execute("SELECT COUNT(*) FROM matches WHERE oddsportal_url IS NOT NULL")
    final_count = cursor.fetchone()[0]

    logger.info("\n" + "=" * 80)
    logger.info("V66.0 Extended Radar - 最终报告")
    logger.info("=" * 80)
    logger.info(f"📊 初始: {initial_count}")
    logger.info(f"📈 最终: {final_count}")
    logger.info(f"✨ 新增: {total_persisted}")

    if final_count >= 1000:
        logger.info("\n🎉 目标达成！启动全量并行收割！")
    else:
        logger.info(f"\n⚠️  差距: {1000 - final_count}")

    logger.info("=" * 80)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    asyncio.run(extended_scan())
