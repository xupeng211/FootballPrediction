#!/usr/bin/env python3
"""
V68.0 Real Address Radar - 真实寻址雷达

核心原则：
1. ✅ 有头模式 (headless=False)
2. ✅ 真实提取页面 href 链接
3. ❌ 严禁使用 random_hash
4. ✅ 只保存真实抓到的 URL
"""

import asyncio
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict

import psycopg2
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s]',
    handlers=[
        logging.FileHandler('logs/v68_real_radar.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 球队名称映射（用于数据库匹配）
# ============================================================================

TEAM_MAP = {
    # 德甲
    "leverkusen": "Bayer Leverkusen",
    "bayern": "Bayern München",
    "munchen": "Bayern München",
    "dortmund": "Borussia Dortmund",
    "monchengladbach": "Borussia Mönchengladbach",
    "frankfurt": "Eintracht Frankfurt",
    "heidenheim": "FC Heidenheim",
    "hoffenheim": "TSG Hoffenheim",
    "leipzig": "RB Leipzig",
    "union": "Union Berlin",
    "stuttgart": "VfB Stuttgart",
    "bremen": "Werder Bremen",
    "wolfsburg": "VfL Wolfsburg",
    "mainz": "Mainz 05",
    "koln": "1. FC Köln",
    "freiburg": "SC Freiburg",
    "bochum": "VfL Bochum",
    "darmstadt": "Darmstadt 98",
    "augsburg": "FC Augsburg",

    # 英超
    "city": "Manchester City",
    "manchester": "Manchester City",
    "united": "Manchester United",
    "liverpool": "Liverpool",
    "chelsea": "Chelsea",
    "arsenal": "Arsenal",
    "tottenham": "Tottenham Hotspur",
    "spurs": "Tottenham Hotspur",
    "west": "West Ham United",
    "west ham": "West Ham United",
    "leicester": "Leicester City",
    "everton": "Everton",
    "newcastle": "Newcastle United",
    "aston": "Aston Villa",
    "villa": "Aston Villa",
    "wolves": "Wolverhampton Wanderers",
    "palace": "Crystal Palace",
    "bournemouth": "AFC Bournemouth",
    "fulham": "Fulham",
    "brighton": "Brighton & Hove Albion",
    "leeds": "Leeds United",
    "southampton": "Southampton",
    "nottingham": "Nottingham Forest",
    "luton": "Luton Town",
    "burnley": "Burnley",
    "sheffield": "Sheffield United",
    "watford": "Watford",
    "norwich": "Norwich City",
    "brentford": "Brentford",
}


def fuzzy_match(team_url_part: str, db_team: str) -> bool:
    """模糊匹配球队名称"""
    team_lower = team_url_part.lower().replace('-', ' ')

    for key, possible_name in TEAM_MAP.items():
        if key in team_lower:
            if possible_name.lower() in db_team.lower():
                return True

    # 直接匹配
    if team_url_part.lower() in db_team.lower():
        return True

    return False


class RealAddressRadar:
    """真实寻址雷达"""

    def __init__(self):
        self.conn = psycopg2.connect(
            host="127.0.0.1",
            port="5432",
            database="football_prediction_dev",
            user="football_user",
            password="football_pass",
        )
        self.cursor = self.conn.cursor()

        self.stats = {
            "pages_scanned": 0,
            "urls_discovered": 0,
            "urls_matched": 0,
            "urls_persisted": 0
        }

    async def scan_results_page(self, league: str, url_season: str, db_season: str, results_url: str):
        """扫描单个 results 页面"""
        logger.info(f"\n[扫描] {league} {url_season}")
        logger.info(f"  URL: {results_url}")

        async with async_playwright() as p:
            # 有头模式
            browser = await p.chromium.launch(
                headless=False,
                slow_mo=100
            )

            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            page = await context.new_page()

            try:
                # 访问页面
                await page.goto(results_url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(5)

                # 保存截图
                screenshot = f"logs/v68_scan_{league.replace(' ', '_')}_{url_season}.png"
                await page.screenshot(path=screenshot)
                logger.info(f"  截图: {screenshot}")

                # 真实提取链接
                url_data = await page.evaluate("""
                    () => {
                        const results = [];
                        const links = document.querySelectorAll('a[href*="/football/"]');

                        for (const link of links) {
                            const href = link.getAttribute('href');
                            const text = link.textContent || '';

                            // 只提取包含比分的链接
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
                self.stats["urls_discovered"] += len(url_data)

                persisted = 0

                # 获取该联赛该赛季未匹配的比赛
                self.cursor.execute("""
                    SELECT match_id, home_team, away_team
                    FROM matches
                    WHERE league_name = %s
                      AND season = %s
                      AND oddsportal_url IS NULL
                    LIMIT 100
                """, (league, db_season))

                unmatched = self.cursor.fetchall()
                logger.info(f"  数据库中未匹配: {len(unmatched)} 场")

                for item in url_data:
                    href = item['href']
                    full_url = f"https://www.oddsportal.com{href}"

                    # 解析球队名称
                    match_part = href.strip('/').split('/')[-1]
                    # 移除哈希
                    match_part = re.sub(r'-[A-Z]{7,}$', '', match_part)
                    teams = match_part.split('-')

                    if len(teams) < 2:
                        continue

                    # 尝试匹配
                    for match_id, db_home, db_away in unmatched:
                        match_found = False

                        for split_idx in range(1, min(len(teams), 4)):
                            home_raw = '-'.join(teams[:split_idx])
                            away_raw = '-'.join(teams[split_idx:])

                            if fuzzy_match(home_raw, db_home) and fuzzy_match(away_raw, db_away):
                                # 保存真实 URL
                                self.cursor.execute("""
                                    UPDATE matches
                                    SET oddsportal_url = %s,
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE match_id = %s
                                """, (full_url, match_id))

                                self.conn.commit()
                                persisted += 1
                                self.stats["urls_persisted"] += 1
                                match_found = True

                                if persisted % 5 == 0:
                                    logger.info(f"  已保存: {persisted} 个 URL")

                                break

                        if match_found:
                            # 从列表移除
                            unmatched = [(m, h, a) for m, h, a in unmatched if m != match_id]
                            break

                logger.info(f"  ✅ 本轮保存: {persisted} 个真实 URL")

            except Exception as e:
                logger.error(f"  ❌ 错误: {e}")

            finally:
                await page.close()
                await browser.close()

        self.stats["pages_scanned"] += 1

    async def run_campaign(self):
        """执行真实寻址行动"""
        logger.info("=" * 80)
        logger.info("V68.0 Real Address Radar - 真实寻址雷达")
        logger.info("=" * 80)
        logger.info("⚠️  严禁使用 random_hash")
        logger.info("✅ 只保存真实抓取的 URL")
        logger.info("=" * 80)

        # 检查初始状态
        self.cursor.execute("SELECT COUNT(*) FROM matches WHERE oddsportal_url IS NOT NULL")
        initial_count = self.cursor.fetchone()[0]
        logger.info(f"📊 初始 URL: {initial_count}")

        # 目标联赛和赛季
        targets = [
            # 优先扫描当前赛季
            ("Premier League", "2024-2025", "24/25", "https://www.oddsportal.com/football/england/premier-league-2024-2025/results/"),
            ("Bundesliga", "2024-2025", "24/25", "https://www.oddsportal.com/football/germany/bundesliga-2024-2025/results/"),

            # 往季赛季
            ("Premier League", "2023-2024", "23/24", "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"),
            ("Bundesliga", "2023-2024", "23/24", "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/"),
        ]

        for league, url_season, db_season, results_url in targets:
            await self.scan_results_page(league, url_season, db_season, results_url)

            # 检查进度
            self.cursor.execute("SELECT COUNT(*) FROM matches WHERE oddsportal_url IS NOT NULL")
            current = self.cursor.fetchone()[0]
            logger.info(f"📊 当前进度: {current} 个 URL")

            if current >= 50:  # 先获取 50 个真实 URL
                logger.info("\n✅ 已获取 50+ 真实 URL，可以开始验证测试")
                break

        # 最终报告
        self.cursor.execute("SELECT COUNT(*) FROM matches WHERE oddsportal_url IS NOT NULL")
        final_count = self.cursor.fetchone()[0]

        logger.info("\n" + "=" * 80)
        logger.info("V68.0 Real Address Radar - 最终报告")
        logger.info("=" * 80)
        logger.info(f"📊 初始 URL: {initial_count}")
        logger.info(f"📈 最终 URL: {final_count}")
        logger.info(f"✨ 新增真实 URL: {final_count - initial_count}")
        logger.info(f"📄 扫描页面数: {self.stats['pages_scanned']}")
        logger.info(f"🔗 发现链接数: {self.stats['urls_discovered']}")
        logger.info("=" * 80)

        self.cursor.close()
        self.conn.close()


async def main():
    """主程序入口"""
    radar = RealAddressRadar()
    await radar.run_campaign()


if __name__ == "__main__":
    asyncio.run(main())
