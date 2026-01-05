#!/usr/bin/env python3
"""
V65.0 URL Persistence V3 - 简化版，直接处理所有操作
"""

import asyncio
import logging
import re
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v65_url_persistence_v3.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TEAM_NAME_MAP = {
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


async def main():
    """主程序"""
    logger.info("=" * 80)
    logger.info("V65.0 URL Persistence V3 - 简化版")
    logger.info("=" * 80)

    import psycopg2

    # 直接连接数据库（使用 Docker 端口映射）
    conn = psycopg2.connect(
        host="127.0.0.1",  # 强制使用 TCP 而不是 Unix socket
        port="5432",
        database="football_prediction_dev",
        user="football_user",
        password="football_pass",
    )
    logger.info(f"[DB] 已连接到: football_prediction_dev @ 127.0.0.1:5432")

    cursor = conn.cursor()

    # 检查已有的 URL
    cursor.execute("""
        SELECT COUNT(*) FROM matches
        WHERE oddsportal_url IS NOT NULL
    """)
    existing_count = cursor.fetchone()[0]
    logger.info(f"[DB] 已有 URL: {existing_count} 条")

    # 启动浏览器
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        results_url = "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/"

        logger.info(f"[Discovery] 访问: {results_url}")

        await page.goto(results_url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(5)

        # 提取 URL
        url_list = await page.evaluate("""
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
                            results.push('https://www.oddsportal.com' + href);
                        }
                    }
                }

                return results;
            }
        """)

        logger.info(f"[Discovery] 找到 {len(url_list)} 场比赛")

        persisted_count = 0

        for full_url in url_list:
            # 解析 URL
            # 格式: https://www.oddsportal.com/football/germany/bundesliga-2023-2024/team1-team2-XXXXXX/

            # 提取比赛部分
            parts = full_url.strip('/').split('/')
            match_part = parts[-1]

            # 移除 hash
            match_part = re.sub(r'-[A-Z]{7,}$', '', match_part)

            # 简单解析：取前两部分作为球队
            team_parts = match_part.split('-')

            if len(team_parts) < 2:
                continue

            # 尝试多种分割方式
            found = False

            # 方式1：直接取前两个
            for i in range(2, min(len(team_parts), 6)):
                home_raw = '-'.join(team_parts[:i])
                away_raw = '-'.join(team_parts[i:])

                home_team = TEAM_NAME_MAP.get(home_raw.lower(), home_raw.title())
                away_team = TEAM_NAME_MAP.get(away_raw.lower(), away_raw.title())

                # 查询数据库
                cursor.execute("""
                    SELECT match_id, home_team, away_team
                    FROM matches
                    WHERE league_name = 'Bundesliga'
                      AND season = '23/24'
                      AND (
                          (home_team ILIKE %s AND away_team ILIKE %s) OR
                          (home_team ILIKE %s AND away_team ILIKE %s)
                      )
                    LIMIT 1
                """, (
                    f"%{home_team}%", f"%{away_team}%",
                    f"%{away_team}%", f"%{home_team}%"
                ))

                result = cursor.fetchone()

                if result:
                    match_id, db_home, db_away = result

                    # 存储 URL
                    cursor.execute("""
                        UPDATE matches
                        SET oddsportal_url = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE match_id = %s
                    """, (full_url, match_id))

                    conn.commit()
                    persisted_count += 1

                    logger.info(f"[Persist] {db_home} vs {db_away}")
                    found = True
                    break

            if not found:
                logger.debug(f"[Skip] 无法匹配: {full_url}")

        await browser.close()

    cursor.close()
    conn.close()

    logger.info("")
    logger.info("=" * 80)
    logger.info(f"✅ 完成！总计持久化: {persisted_count} 场比赛")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
