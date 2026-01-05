#!/usr/bin/env python3
"""
V66.0 Chameleon Radar - 使用 V64.0 变色龙协议进行 URL 发现

关键改进：
1. 使用有状态浏览器（headless=False）
2. 随机指纹和延迟
3. Referer 伪造
4. 更宽松的球队名称匹配
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
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v66_chameleon_radar.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 球队名称映射（更宽松）
# ============================================================================

TEAM_MAP = {
    # 德甲
    "leverkusen": ["Bayer Leverkusen", "Leverkusen"],
    "bayern": ["Bayern München", "Bayern Munich"],
    "munchen": ["Bayern München", "Bayern Munich"],
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
    "kolkata": ["1. FC Köln"],  # 拼写错误
    "freiburg": ["SC Freiburg"],
    "bochum": ["VfL Bochum"],
    "darmstadt": ["Darmstadt 98"],
    "augsburg": ["FC Augsburg"],

    # 英超
    "city": ["Manchester City"],
    "united": ["Manchester United"],
    "liverpool": ["Liverpool"],
    "chelsea": ["Chelsea"],
    "arsenal": ["Arsenal"],
    "tottenham": ["Tottenham Hotspur"],
    "spurs": ["Tottenham Hotspur"],
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
}


def fuzzy_match_team(team_raw: str, db_team: str) -> bool:
    """模糊匹配球队名称"""
    team_lower = team_raw.lower()

    for key, possible_names in TEAM_MAP.items():
        if key in team_lower:
            for possible in possible_names:
                if possible.lower() in db_team.lower() or db_team.lower() in possible.lower():
                    return True

    # 直接匹配
    if team_raw.lower() in db_team.lower() or db_team.lower() in team_raw.lower():
        return True

    return False


async def scan_with_chameleon():
    """使用变色龙协议扫描"""
    logger.info("=" * 80)
    logger.info("V66.0 Chameleon Radar - URL Discovery")
    logger.info("=" * 80)

    conn = psycopg2.connect(
        host="127.0.0.1",
        port="5432",
        database="football_prediction_dev",
        user="football_user",
        password="football_pass",
    )
    cursor = conn.cursor()

    # 先检查当前状态
    cursor.execute("SELECT COUNT(*) FROM matches WHERE oddsportal_url IS NOT NULL")
    initial_count = cursor.fetchone()[0]
    logger.info(f"📊 初始 URL 数: {initial_count}")

    # 目标联赛
    targets = [
        ("Premier League", "2023-2024", "23/24", "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"),
        ("Bundesliga", "2023-2024", "23/24", "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/"),
    ]

    total_persisted = 0

    async with async_playwright() as p:
        # 使用变色龙配置
        browser = await p.chromium.launch(
            headless=False,  # 可见模式
            slow_mo=100
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        # 设置 Referer
        await context.set_extra_http_headers({
            "Referer": "https://www.oddsportal.com/"
        })

        for league, url_season, db_season, results_url in targets:
            logger.info(f"\n[扫描] {league} {url_season}")
            logger.info(f"  URL: {results_url}")

            page = await context.new_page()

            try:
                # 访问页面
                await page.goto(results_url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(5)

                # 截图保存
                screenshot_path = f"logs/v66_chameleon_{league.replace(' ', '_')}_{url_season}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"  截图: {screenshot_path}")

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

                for item in url_data[:100]:  # 限制前 100 场
                    url_path = item['href']
                    full_url = f"https://www.oddsportal.com{url_path}"

                    # 解析球队名称
                    match_part = url_path.strip('/').split('/')[-1]
                    match_part = re.sub(r'-[A-Z]{7,}$', '', match_part)
                    teams = match_part.split('-')

                    if len(teams) < 2:
                        continue

                    # 尝试多种分割方式
                    for split_idx in range(1, min(len(teams), 4)):
                        home_raw = '-'.join(teams[:split_idx])
                        away_raw = '-'.join(teams[split_idx:])

                        # 查询数据库
                        cursor.execute("""
                            SELECT match_id, home_team, away_team
                            FROM matches
                            WHERE league_name = %s
                              AND season = %s
                              AND oddsportal_url IS NULL
                            LIMIT 20
                        """, (league, db_season))

                        for match_id, db_home, db_away in cursor.fetchall():
                            # 模糊匹配
                            home_match = fuzzy_match_team(home_raw, db_home)
                            away_match = fuzzy_match_team(away_raw, db_away)

                            if home_match and away_match:
                                # 存储 URL
                                cursor.execute("""
                                    UPDATE matches
                                    SET oddsportal_url = %s,
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE match_id = %s
                                """, (full_url, match_id))

                                conn.commit()
                                persisted += 1
                                total_persisted += 1

                                logger.info(f"  ✅ {db_home} vs {db_away}")
                                break

                logger.info(f"  持久化: {persisted} 个 URL")

            except Exception as e:
                logger.error(f"  ❌ 错误: {e}")

            finally:
                await page.close()

        await browser.close()

    # 最终报告
    cursor.execute("SELECT COUNT(*) FROM matches WHERE oddsportal_url IS NOT NULL")
    final_count = cursor.fetchone()[0]

    logger.info("\n" + "=" * 80)
    logger.info("V66.0 Chameleon Radar - 最终报告")
    logger.info("=" * 80)
    logger.info(f"📊 初始 URL: {initial_count}")
    logger.info(f"📈 最终 URL: {final_count}")
    logger.info(f"✨ 新增: {total_persisted}")

    if final_count >= 1000:
        logger.info("\n🎉 目标达成！可以启动全量并行收割！")
    else:
        logger.info(f"\n⚠️  当前 {final_count} 个 URL，距离目标 1000 还差 {1000 - final_count}")

    logger.info("=" * 80)

    cursor.close()
    conn.close()


if __name__ == "__main__":
    asyncio.run(scan_with_chameleon())
