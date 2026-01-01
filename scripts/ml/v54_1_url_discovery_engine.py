#!/usr/bin/env python3
"""
V54.1 URL 发现引擎 - 第一阶段
============================

功能:
1. 扫描五大联赛赛季结果页
2. 提取所有比赛详情页 URL
3. 持久化到 prematch_features.source_url
4. 支持 match_name 自动匹配

Author: Senior Distributed Crawler Architect
Version: V54.1
Date: 2026-01-01
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys

import psycopg2
from psycopg2.extras import RealDictCursor
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================
# 赛季 URL 配置
# ============================================================

SEASON_URLS = {
    "Premier League": [
        "https://www.oddsportal.com/football/england/premier-league-2020-2021/results/",
        "https://www.oddsportal.com/football/england/premier-league-2021-2022/results/",
        "https://www.oddsportal.com/football/england/premier-league-2022-2023/results/",
        "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/",
        "https://www.oddsportal.com/football/england/premier-league-2024-2025/results/",
    ],
    "La Liga": [
        "https://www.oddsportal.com/football/spain/la-liga-2020-2021/results/",
        "https://www.oddsportal.com/football/spain/la-liga-2021-2022/results/",
        "https://www.oddsportal.com/football/spain/la-liga-2022-2023/results/",
        "https://www.oddsportal.com/football/spain/la-liga-2023-2024/results/",
        "https://www.oddsportal.com/football/spain/la-liga-2024-2025/results/",
    ],
    "Bundesliga": [
        "https://www.oddsportal.com/football/germany/bundesliga-2020-2021/results/",
        "https://www.oddsportal.com/football/germany/bundesliga-2021-2022/results/",
        "https://www.oddsportal.com/football/germany/bundesliga-2022-2023/results/",
        "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/",
        "https://www.oddsportal.com/football/germany/bundesliga-2024-2025/results/",
    ],
    "Serie A": [
        "https://www.oddsportal.com/football/italy/serie-a-2020-2021/results/",
        "https://www.oddsportal.com/football/italy/serie-a-2021-2022/results/",
        "https://www.oddsportal.com/football/italy/serie-a-2022-2023/results/",
        "https://www.oddsportal.com/football/italy/serie-a-2023-2024/results/",
        "https://www.oddsportal.com/football/italy/serie-a-2024-2025/results/",
    ],
    "Ligue 1": [
        "https://www.oddsportal.com/football/france/ligue-1-2020-2021/results/",
        "https://www.oddsportal.com/football/france/ligue-1-2021-2022/results/",
        "https://www.oddsportal.com/football/france/ligue-1-2022-2023/results/",
        "https://www.oddsportal.com/football/france/ligue-1-2023-2024/results/",
        "https://www.oddsportal.com/football/france/ligue-1-2024-2025/results/",
    ],
}


@dataclass
class DiscoveredURL:
    """发现的 URL"""
    match_id: str | None = None
    relative_path: str | None = None
    home_team: str | None = None
    away_team: str | None = None


class URLDiscoveryEngine:
    """V54.1 URL 发现引擎 - 第一阶段"""

    def __init__(self):
        self.settings = get_settings()
        self.discovered_urls: list[DiscoveredURL] = []

    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

    def normalize_team_name(self, name: str) -> str:
        """标准化球队名称用于匹配"""
        return (name
                .lower()
                .replace(" ", "-")
                .replace("&", "and")
                .replace("fc", "")
                .replace("united", "utd")
                .strip("-"))

    async def discover_urls_from_page(self, page, league: str) -> list[DiscoveredURL]:
        """
        【核心】从赛季结果页提取所有比赛详情页 URL

        关键逻辑：
        1. 查找所有指向比赛详情的链接
        2. 提取相对路径
        3. 尝试从 URL 或父元素解析球队名
        """
        await asyncio.sleep(3)  # 等待 Vue.js 渲染

        # JavaScript 提取所有比赛链接
        urls_data = await page.evaluate("""
            () => {
                const results = [];

                // 查找所有包含比赛链接的元素
                const links = document.querySelectorAll('a[href*="/football/"]');

                links.forEach(link => {
                    const href = link.getAttribute('href');
                    // 过滤：只保留比赛详情页（排除列表页）
                    if (href && href.includes('/football/') &&
                        !href.includes('/results/') &&
                        !href.includes('/standings/') &&
                        !href.includes('/fixtures/') &&
                        !href.includes('/live/')) {

                        // 提取相对路径: /football/england/premier-league/team1-team2-xyz/
                        const match = href.match(/\\/football\\/[^/]+\\/[^/]+\\/[^/]+-[^/]+-[^/]+/);
                        if (match) {
                            results.push({
                                relativePath: match[0],
                                fullHref: href,
                                text: link.textContent.trim()
                            });
                        }
                    }
                });

                return results;
            }
        """)

        discovered = []
        for url_data in urls_data:
            item = DiscoveredURL(relative_path=url_data["relativePath"])
            discovered.append(item)

        logger.debug(f"从 {league} 页面发现 {len(discovered)} 个比赛 URL")
        return discovered

    async def scan_season_page(
        self,
        browser,
        league: str,
        season_url: str
    ) -> list[DiscoveredURL]:
        """
        扫描单个赛季页面
        """
        logger.info(f"扫描: {league} - {season_url}")

        page = await browser.new_page()

        try:
            await page.goto(
                season_url,
                wait_until="networkidle",
                timeout=30000
            )

            urls = await self.discover_urls_from_page(page, league)

            await page.close()
            return urls

        except Exception as e:
            logger.error(f"扫描失败 [{season_url}]: {e}")
            await page.close()
            return []

    def save_urls_to_database(
        self,
        league: str,
        urls: list[DiscoveredURL],
        batch_id: str
    ) -> dict:
        """
        将发现的 URL 持久化到数据库

        匹配逻辑：
        1. 从相对路径解析球队名
        2. 在 matches 表中查找对应的 match_id
        3. 更新 prematch_features.source_url
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()

        stats = {
            "total": len(urls),
            "matched": 0,
            "unmatched": 0,
        }

        for url_item in urls:
            if not url_item.relative_path:
                continue

            # 尝试从 URL 解析球队名
            # 格式: /football/england/premier-league/team1-team2-xyz/
            path_parts = url_item.relative_path.split("/")
            if len(path_parts) >= 5:
                # 提取比赛标识部分
                match_part = path_parts[4]  # team1-team2-xyz

                # 尝试按连字符分割获取球队名
                teams = match_part.split("-")

                if len(teams) >= 2:
                    # 尝试在数据库中匹配
                    cursor.execute("""
                        UPDATE prematch_features pf
                        SET source_url = %s,
                            url_discovered_at = CURRENT_TIMESTAMP
                        FROM matches m
                        WHERE pf.match_id = m.match_id
                          AND m.league_name = %s
                          AND pf.source_url IS NULL
                          AND (
                              LOWER(m.home_team) LIKE %s
                              OR LOWER(m.away_team) LIKE %s
                              OR %s LIKE '%' || LOWER(REPLACE(m.home_team, ' ', '-')) || '%'
                              OR %s LIKE '%' || LOWER(REPLACE(m.away_team, ' ', '-')) || '%'
                          )
                        RETURNING pf.match_id
                    """, (
                        f"/{url_item.relative_path}",
                        league,
                        f"{teams[0]}%",
                        f"{teams[-1]}%",
                        match_part,
                        match_part
                    ))

                    if cursor.rowcount > 0:
                        stats["matched"] += 1
                    else:
                        stats["unmatched"] += 1

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"批次 {batch_id}: 匹配 {stats['matched']}/{stats['total']}")

        return stats

    async def run_discovery(self) -> dict:
        """
        运行完整的 URL 发现流程
        """
        logger.info("=" * 60)
        logger.info("【V54.1 URL 发现引擎】")
        logger.info("=" * 60)
        logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)

            all_stats = {
                "total_scanned": 0,
                "total_matched": 0,
                "total_unmatched": 0,
                "by_league": {},
            }

            batch_id = 0

            for league, season_urls in SEASON_URLS.items():
                logger.info(f"")
                logger.info(f"【{league}】")

                league_stats = {
                    "scanned": 0,
                    "matched": 0,
                    "unmatched": 0,
                }

                for season_url in season_urls:
                    batch_id += 1

                    # 扫描页面
                    urls = await self.scan_season_page(browser, league, season_url)
                    league_stats["scanned"] += len(urls)

                    # 保存到数据库
                    save_stats = self.save_urls_to_database(league, urls, f"{league}-{batch_id}")
                    league_stats["matched"] += save_stats["matched"]
                    league_stats["unmatched"] += save_stats["unmatched"]

                    # 随机延迟
                    await asyncio.sleep(2)

                all_stats["by_league"][league] = league_stats
                all_stats["total_scanned"] += league_stats["scanned"]
                all_stats["total_matched"] += league_stats["matched"]
                all_stats["total_unmatched"] += league_stats["unmatched"]

            await browser.close()

        return all_stats


# ============================================================
# 主函数
# ============================================================

async def main():
    """主函数"""
    engine = URLDiscoveryEngine()

    result = await engine.run_discovery()

    # 输出报告
    print()
    print("=" * 60)
    print("【V54.1 URL 发现报告】")
    print("=" * 60)
    print()

    for league, stats in result["by_league"].items():
        print(f"{league}:")
        print(f"  扫描: {stats['scanned']} 个 URL")
        print(f"  匹配: {stats['matched']} 场比赛")
        print(f"  未匹配: {stats['unmatched']}")
        print()

    print("=" * 60)
    print(f"总计扫描: {result['total_scanned']} 个 URL")
    print(f"总计匹配: {result['total_matched']} 场比赛")
    print(f"匹配率: {result['total_matched']/result['total_scanned']*100 if result['total_scanned'] > 0 else 0:.1f}%")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
