#!/usr/bin/env python3
"""
V66.0 Global Radar - URL Discovery Campaign
全球雷达大扫射：为数据库中所有比赛填充 OddsPortal URL

目标：
1. 扫描数据库中所有联赛和赛季
2. 批量访问各联赛 results 页面
3. 模糊匹配并填充 URL
4. 验收：1000+ 场比赛配齐 URL
"""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import psycopg2
from playwright.async_api import async_playwright

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v66_global_radar.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 联赛配置（OddsPortal URL 格式）
# ============================================================================

LEAGUE_CONFIGS = {
    "Bundesliga": {
        "url_template": "https://www.oddsportal.com/football/germany/bundesliga-{season}/results/",
        "db_names": ["Bundesliga"],
        "seasons": ["2019-2020", "2020-2021", "2021-2022", "2022-2023", "2023-2024", "2024-2025"]
    },
    "Premier League": {
        "url_template": "https://www.oddsportal.com/football/england/premier-league-{season}/results/",
        "db_names": ["Premier League"],
        "seasons": ["2019-2020", "2020-2021", "2021-2022", "2022-2023", "2023-2024", "2024-2025"]
    },
    "La Liga": {
        "url_template": "https://www.oddsportal.com/football/spain/laliga-{season}/results/",
        "db_names": ["La Liga", "LaLiga"],
        "seasons": ["2019-2020", "2020-2021", "2021-2022", "2022-2023", "2023-2024"]
    },
    "Serie A": {
        "url_template": "https://www.oddsportal.com/football/italy/serie-a-{season}/results/",
        "db_names": ["Serie A"],
        "seasons": ["2019-2020", "2020-2021", "2021-2022", "2022-2023", "2023-2024"]
    },
    "Ligue 1": {
        "url_template": "https://www.oddsportal.com/football/france/ligue-1-{season}/results/",
        "db_names": ["Ligue 1"],
        "seasons": ["2019-2020", "2020-2021", "2021-2022", "2022-2023", "2023-2024"]
    },
}

# 球队名称映射
TEAM_NAME_MAP = {
    # 德甲
    "bayer leverkusen": "Bayer Leverkusen",
    "bayern munich": "Bayern München",
    "bayern munchen": "Bayern München",
    "borussia dortmund": "Borussia Dortmund",
    "borussia monchengladbach": "Borussia Mönchengladbach",
    "b monchengladbach": "Borussia Mönchengladbach",
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
    "1 fc koln": "1. FC Köln",
    "fc koln": "1. FC Köln",
    "freiburg": "SC Freiburg",
    "bochum": "VfL Bochum",
    "darmstadt": "Darmstadt 98",
    "augsburg": "FC Augsburg",
    "hertha": "Hertha BSC",
    "schalke": "FC Schalke 04",
    "bielefeld": "Arminia Bielefeld",
    "greuther furth": "Greuther Fürth",
    "hamburger": "Hamburger SV",
    "hannover": "Hannover 96",
    "fuerth": "Greuther Fürth",
    "paderborn": "SC Paderborn",
    "kolkata": "1. FC Köln",  # 拼写错误映射

    # 英超
    "manchester city": "Manchester City",
    "man city": "Manchester City",
    "mancity": "Manchester City",
    "manchester united": "Manchester United",
    "man utd": "Manchester United",
    "manutd": "Manchester United",
    "liverpool": "Liverpool",
    "chelsea": "Chelsea",
    "arsenal": "Arsenal",
    "tottenham": "Tottenham Hotspur",
    "spurs": "Tottenham Hotspur",
    "west ham": "West Ham United",
    "leicester city": "Leicester City",
    "leicester": "Leicester City",
    "everton": "Everton",
    "newcastle": "Newcastle United",
    "aston villa": "Aston Villa",
    "wolves": "Wolverhampton Wanderers",
    "wolverhampton": "Wolverhampton Wanderers",
    "crystal palace": "Crystal Palace",
    "bournemouth": "AFC Bournemouth",
    "fulham": "Fulham",
    "brentford": "Bretnford",
    "brighton": "Brighton & Hove Albion",
    "leeds": "Leeds United",
    "southampton": "Southampton",
    "nottingham forest": "Nottingham Forest",
    "nottm forest": "Nottingham Forest",
    "luton town": "Luton Town",
    "burnley": "Burnley",
    "sheffield united": "Sheffield United",
    "norwich": "Norwich City",
    "watford": "Watford",
    "west brom": "West Bromwich Albion",
}


class GlobalRadarScanner:
    """全球雷达扫描器"""

    def __init__(self):
        # 直接连接数据库（避免配置问题）
        self.conn = psycopg2.connect(
            host="127.0.0.1",
            port="5432",
            database="football_prediction_dev",
            user="football_user",
            password="football_pass",
        )
        self.cursor = self.conn.cursor()

        # 统计
        self.stats = {
            "total_scanned": 0,
            "urls_discovered": 0,
            "matches_found": 0,
            "urls_persisted": 0,
            "leagues_processed": []
        }

    def get_league_inventory(self) -> List[Dict]:
        """获取数据库中所有需要填充 URL 的联赛和赛季"""
        logger.info("=" * 60)
        logger.info("第一步：联赛大盘点")
        logger.info("=" * 60)

        self.cursor.execute("""
            SELECT
                league_name,
                season,
                COUNT(*) as match_count,
                COUNT(oddsportal_url) as has_url_count
            FROM matches
            GROUP BY league_name, season
            HAVING COUNT(oddsportal_url) < COUNT(*)
            ORDER BY league_name, season
        """)

        results = []
        for row in self.cursor.fetchall():
            results.append({
                'league': row[0],
                'season': row[1],
                'total': row[2],
                'has_url': row[3],
                'needs_url': row[2] - row[3]
            })

            logger.info(f"  {row[0]} {row[1]}: {row[2]} 场 | 已有 URL: {row[3]} | 缺失: {row[2] - row[3]}")

        total_missing = sum(r['needs_url'] for r in results)
        logger.info(f"\n📊 总计: {len(results)} 个联赛-赛季组合，缺失 {total_missing} 个 URL")

        return results

    def parse_match_url(self, url_path: str) -> Dict:
        """解析 OddsPortal match URL"""
        try:
            parts = url_path.strip('/').split('/')
            if len(parts) < 2:
                return None

            match_part = parts[-1]
            # 移除 hash
            match_part = re.sub(r'-[A-Z]{7,}$', '', match_part)

            # 智能分割球队名称
            teams = []
            current_team = []

            for part in match_part.split('-'):
                possible_team = '-'.join(current_team + [part]).lower()

                # 检查是否是已知球队
                is_known = any(
                    possible_team == known.lower() or
                    possible_team in known.lower() or
                    known.lower() in possible_team
                    for known in TEAM_NAME_MAP.values()
                )

                if is_known or len(current_team) == 0:
                    current_team.append(part)
                else:
                    if current_team:
                        teams.append('-'.join(current_team))
                    current_team = [part]

            if current_team:
                teams.append('-'.join(current_team))

            if len(teams) >= 2:
                home_raw = teams[0]
                away_raw = '-'.join(teams[1:])

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

    async def scan_league_season(self, league_name: str, url_season: str, db_season: str, results_url: str):
        """扫描单个联赛赛季的 results 页面"""
        logger.info(f"\n[扫描] {league_name} {url_season}")
        logger.info(f"  URL: {results_url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            page = await context.new_page()

            try:
                await page.goto(results_url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)

                # 提取所有比赛 URL
                url_list = await page.evaluate("""
                    () => {
                        const results = [];
                        const links = document.querySelectorAll('a[href]');

                        for (const link of links) {
                            const href = link.getAttribute('href');

                            if (href && !href.includes('/standings') && !href.includes('/outrights')) {
                                const text = link.textContent || '';
                                if (text.match(/\\d+\\s*[–:-]\\s*\\d+/)) {
                                    results.push(href);
                                }
                            }
                        }

                        return results;
                    }
                """)

                logger.info(f"  发现 {len(url_list)} 场比赛")
                self.stats['urls_discovered'] += len(url_list)

                persisted_count = 0

                for url_path in url_list:
                    match_info = self.parse_match_url(url_path)

                    if not match_info:
                        continue

                    # 查找数据库中的比赛
                    self.cursor.execute("""
                        SELECT match_id, home_team, away_team
                        FROM matches
                        WHERE league_name = %s
                          AND season = %s
                          AND (
                              (home_team ILIKE %s AND away_team ILIKE %s) OR
                              (home_team ILIKE %s AND away_team ILIKE %s)
                          )
                          AND oddsportal_url IS NULL
                        LIMIT 1
                    """, (
                        league_name, db_season,
                        f"%{match_info['home_team']}%", f"%{match_info['away_team']}%",
                        f"%{match_info['away_team']}%", f"%{match_info['home_team']}%"
                    ))

                    result = self.cursor.fetchone()

                    if result:
                        match_id, db_home, db_away = result

                        self.cursor.execute("""
                            UPDATE matches
                            SET oddsportal_url = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE match_id = %s
                        """, (match_info['full_url'], match_id))

                        self.conn.commit()
                        persisted_count += 1
                        self.stats['urls_persisted'] += 1

                logger.info(f"  ✅ 持久化: {persisted_count} 个 URL")

                self.stats['leagues_processed'].append(f"{league_name} {url_season}")

            except Exception as e:
                logger.error(f"  ❌ 错误: {e}")

            finally:
                await browser.close()

    async def run_campaign(self, target_count: int = 1000):
        """执行全球雷达大扫射"""
        logger.info("=" * 80)
        logger.info("V66.0 Global Radar - URL Discovery Campaign")
        logger.info("=" * 80)
        logger.info(f"目标: 填充 {target_count}+ 个 URL")
        logger.info("=" * 80)

        # 第一步：大盘点
        inventory = self.get_league_inventory()

        # 检查当前进度
        self.cursor.execute("SELECT COUNT(*) FROM matches WHERE oddsportal_url IS NOT NULL")
        current_count = self.cursor.fetchone()[0]
        logger.info(f"\n📊 当前已有 URL: {current_count}")

        # 第二步：扫描目标联赛
        logger.info("\n" + "=" * 60)
        logger.info("第二步：全球雷达大扫射")
        logger.info("=" * 60)

        # 优先处理英超和德甲
        priority_leagues = ["Premier League", "Bundesliga"]

        for league_name in priority_leagues:
            if league_name not in LEAGUE_CONFIGS:
                continue

            config = LEAGUE_CONFIGS[league_name]

            for url_season in config['seasons']:
                # 检查是否已达到目标
                self.cursor.execute("SELECT COUNT(*) FROM matches WHERE oddsportal_url IS NOT NULL")
                current_count = self.cursor.fetchone()[0]

                if current_count >= target_count:
                    logger.info(f"\n🎉 已达到目标！当前: {current_count}")
                    break

                # 构造数据库赛季格式
                db_season = url_season.replace('-', '/')[:5].replace('20', '')

                results_url = config['url_template'].format(season=url_season)

                await self.scan_league_season(
                    league_name=league_name,
                    url_season=url_season,
                    db_season=db_season,
                    results_url=results_url
                )

            if current_count >= target_count:
                break

        # 最终报告
        self._generate_final_report()

    def _generate_final_report(self):
        """生成最终报告"""
        logger.info("\n" + "=" * 80)
        logger.info("V66.0 Global Radar - 最终报告")
        logger.info("=" * 80)

        self.cursor.execute("SELECT COUNT(*) FROM matches WHERE oddsportal_url IS NOT NULL")
        final_count = self.cursor.fetchone()[0]

        logger.info(f"📊 URL 持久化总数: {final_count}")
        logger.info(f"📈 新增 URL: {self.stats['urls_persisted']}")
        logger.info(f"🌐 扫描的联赛: {len(self.stats['leagues_processed'])}")

        if final_count >= 1000:
            logger.info("\n🎉 目标达成！可以启动全量并行收割！")
        else:
            logger.info(f"\n⚠️  当前 {final_count} 个 URL，继续扫描中...")

        logger.info("\n已处理的联赛-赛季:")
        for item in self.stats['leagues_processed']:
            logger.info(f"  ✅ {item}")

        logger.info("=" * 80)

        self.cursor.close()
        self.conn.close()


async def main():
    """主程序入口"""
    scanner = GlobalRadarScanner()
    await scanner.run_campaign(target_count=1000)


if __name__ == "__main__":
    asyncio.run(main())
