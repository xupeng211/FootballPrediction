#!/usr/bin/env python3
"""
V65.0 URL Discovery & Persistence - URL 自动化发现与持久化

功能：
1. 访问德甲 23/24 results 页面
2. 使用 JavaScript 提取所有比赛 URL
3. 匹配数据库中的比赛（按球队名称和赛季）
4. 将 URL 存入 matches 表的 oddsportal_url 字段

目标：建立永久的"藏宝图"，不再依赖动态扫描
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
        logging.FileHandler('logs/v65_url_persistence.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 配置
# ============================================================================

TARGETS = [
    {
        "league": "Bundesliga",
        "season": "23/24",
        "url_season": "2023-2024",
        "results_url": "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/",
        "db_league": "Bundesliga"
    },
]

# 球队名称映射（OddsPortal → 数据库）
TEAM_MAPPINGS = {
    "Dortmund": "Borussia Dortmund",
    "Bayern Munich": "Bayern München",
    "Bayern Munchen": "Bayern München",
    "B. Monchengladbach": "Borussia Mönchengladbach",
    "FC Koln": "1. FC Köln",
    "Stuttgart": "VfB Stuttgart",
    "Mainz": "Mainz 05",
    "Heidenheim": "FC Heidenheim",
    "Darmstadt": "Darmstadt 98",
    "Leverkusen": "Bayer Leverkusen",
    "Monchengladbach": "Borussia Mönchengladbach",
    "Bochum": "VfL Bochum",
}


def normalize_team_name(name: str) -> str:
    """标准化球队名称"""
    name = name.strip()
    return TEAM_MAPPINGS.get(name, name)


def get_db_connection():
    """获取数据库连接"""
    settings = get_settings()
    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )


async def discover_and_persist_urls():
    """发现 URL 并持久化到数据库"""
    logger.info("=" * 80)
    logger.info("V65.0 URL Discovery & Persistence - 启动")
    logger.info("=" * 80)

    async with async_playwright() as p:
        # 启动浏览器（使用 V64.0 变色龙配置）
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=100
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        total_discovered = 0
        total_matched = 0
        total_persisted = 0

        for target in TARGETS:
            logger.info("")
            logger.info("-" * 60)
            logger.info(f"目标: {target['league']} {target['season']}")
            logger.info(f"Results URL: {target['results_url']}")
            logger.info("-" * 60)

            page = await context.new_page()

            try:
                # 访问 results 页面
                await page.goto(
                    target['results_url'],
                    wait_until='networkidle',
                    timeout=30000
                )

                # 等待页面加载
                await asyncio.sleep(5)

                # 使用 JavaScript 提取所有比赛 URL
                discovery_script = """
                    () => {
                        const results = [];
                        const links = document.querySelectorAll('a[href]');

                        for (const link of links) {
                            const href = link.getAttribute('href');
                            const text = link.textContent || '';

                            // 过滤：只提取比赛链接
                            // URL 格式: /football/germany/bundesliga-2023-2024/team1-team2-XXXXXX/
                            if (href &&
                                href.includes('/football/') &&
                                href.includes('bundesliga-2023-2024') &&
                                !href.includes('/standings') &&
                                !href.includes('/outrights') &&
                                text.match(/\\d+\\s*[–:-]\\s*\\d+/)) {

                                // 提取球队名称
                                const parts = href.split('/');
                                const matchPart = parts[parts.length - 2] || parts[parts.length - 1];

                                results.push({
                                    urlPath: href,
                                    fullUrl: 'https://www.oddsportal.com' + href,
                                    matchPart: matchPart,
                                    text: text.trim()
                                });
                            }
                        }

                        return results;
                    }
                """

                discovered = await page.evaluate(discovery_script)
                logger.info(f"[Discovery] 找到 {len(discovered)} 场比赛")

                total_discovered += len(discovered)

                # 匹配数据库并持久化
                for item in discovered:
                    try:
                        # 解析球队名称
                        match_part = item['matchPart']

                        # URL 格式: mainz-bayern-munich-pOYHWCAL
                        # 移除 hash 部分
                        teams_part = re.sub(r'-[A-Z]{7,}$', '', match_part)

                        # 分离主客队
                        teams = teams_part.split('-')
                        if len(teams) < 2:
                            continue

                        # 第一部分是主队，剩余部分是客队
                        home_raw = teams[0]
                        away_raw = '-'.join(teams[1:])

                        # 标准化球队名称
                        home_team = normalize_team_name(home_raw.replace('-', ' ').title())
                        away_team = normalize_team_name(away_raw.replace('-', ' ').title())

                        # 查询数据库
                        conn = get_db_connection()
                        cursor = conn.cursor()

                        cursor.execute("""
                            SELECT match_id, home_team, away_team, match_date
                            FROM matches
                            WHERE league_name = %s
                              AND season = %s
                              AND (home_team ILIKE %s OR away_team ILIKE %s)
                              AND (home_team ILIKE %s OR away_team ILIKE %s)
                            LIMIT 5
                        """, (
                            target['db_league'],
                            target['season'],
                            f"%{home_team}%", f"%{home_team}%",
                            f"%{away_team}%", f"%{away_team}%"
                        ))

                        db_matches = cursor.fetchall()

                        if db_matches:
                            total_matched += 1

                            for match in db_matches:
                                match_id, db_home, db_away, match_date = match

                                # 验证球队匹配
                                is_valid_match = (
                                    (home_team.lower() in db_home.lower() or db_home.lower() in home_team.lower()) and
                                    (away_team.lower() in db_away.lower() or db_away.lower() in away_team.lower())
                                )

                                if is_valid_match:
                                    # 存储 URL
                                    cursor.execute("""
                                        UPDATE matches
                                        SET oddsportal_url = %s,
                                            updated_at = CURRENT_TIMESTAMP
                                        WHERE match_id = %s
                                    """, (item['fullUrl'], match_id))

                                    conn.commit()
                                    total_persisted += 1

                                    logger.info(f"[Persist] {db_home} vs {db_away} → URL 已保存")
                                    break  # 每场比赛只保存一次

                        cursor.close()
                        conn.close()

                    except Exception as e:
                        logger.debug(f"[Match] 匹配失败: {e}")
                        continue

            except Exception as e:
                logger.error(f"[Discovery] 错误: {e}")
                continue

            finally:
                await page.close()

        await browser.close()

    # 生成报告
    logger.info("")
    logger.info("=" * 80)
    logger.info("V65.0 URL Persistence - 最终报告")
    logger.info("=" * 80)
    logger.info(f"📊 发现 URL: {total_discovered}")
    logger.info(f"🎯 匹配数据库: {total_matched}")
    logger.info(f"💾 持久化成功: {total_persisted}")
    logger.info("=" * 80)

    return {
        "discovered": total_discovered,
        "matched": total_matched,
        "persisted": total_persisted
    }


async def main():
    """主程序入口"""
    result = await discover_and_persist_urls()

    if result['persisted'] > 0:
        logger.info("✅ URL 持久化完成！藏宝图已建立。")
    else:
        logger.warning("⚠️  未能持久化任何 URL，请检查日志。")


if __name__ == "__main__":
    asyncio.run(main())
