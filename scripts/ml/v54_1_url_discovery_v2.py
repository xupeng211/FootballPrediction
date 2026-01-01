#!/usr/bin/env python3
"""
V54.1 URL 发现引擎 V2 - 真实扫描版
==================================

功能:
1. 扫描赛季列表页提取真实详情页 URL
2. 匹配数据库中的比赛
3. 限制扫描数量进行测试
4. 支持 User-Agent 轮换和反爬延迟

Author: Senior Crawler Algorithm Engineer
Version: V54.1-V2
Date: 2026-01-01
"""

import asyncio
import logging
import random
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================
# 配置
# ============================================================

SEASON_URLS = {
    "Premier League": "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/",
    "La Liga": "https://www.oddsportal.com/football/spain/la-liga-2023-2024/results/",
    "Bundesliga": "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/",
}

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class URLDiscoveryEngineV2:
    """V54.1 URL 发现引擎 V2"""

    def __init__(self, max_matches: int = 10):
        """
        Args:
            max_matches: 最大提取数量（测试模式）
        """
        self.settings = get_settings()
        self.max_matches = max_matches
        self.discovered_count = 0

    def get_db_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password.get_secret_value(),
        )

    def normalize_name(self, name: str) -> str:
        """标准化球队名用于匹配"""
        return (name.lower()
                .replace(" ", "-")
                .replace("&", "and")
                .replace("'", "")
                .replace("fc", "")
                .strip("-"))

    async def scan_season_page(self, page, league: str, url: str) -> list[dict]:
        """
        扫描赛季列表页，提取真实详情页 URL

        策略：
        1. 查找所有包含球队格式的链接
        2. 提取完整的 href（包含动态 ID）
        3. 返回格式: {url: "/football/.../team1-team2-xyz/", teams: ["team1", "team2"]}
        """
        logger.info(f"扫描: {league}")

        await page.goto(url, wait_until="networkidle", timeout=30000)
        await asyncio.sleep(3)  # 等待 Vue.js 渲染

        # 使用简化的选择器策略
        discovered = await page.evaluate("""
            () => {
                const results = [];
                const links = document.querySelectorAll('a[href*="/football/"]');

                links.forEach(link => {
                    const href = link.getAttribute('href');
                    if (href && href.includes('/football/') &&
                        !href.includes('/results/') &&
                        !href.includes('/standings/') &&
                        !href.includes('/fixtures/')) {

                        // 提取球队名部分
                        const parts = href.split('/');
                        if (parts.length >= 5) {
                            const matchPart = parts[4];  // team1-team2-xyz
                            if (matchPart && matchPart.includes('-')) {
                                results.push({
                                    url: href,
                                    matchPart: matchPart,
                                    text: link.textContent.trim()
                                });
                            }
                        }
                    }
                });

                return results;
            }
        """)

        logger.debug(f"从 {league} 发现 {len(discovered)} 个链接")
        return discovered

    def match_and_save_urls(self, league: str, discovered_urls: list[dict]) -> dict:
        """
        将发现的 URL 匹配到数据库中的比赛

        策略：
        1. 从 URL 中提取可能的球队名
        2. 在数据库中模糊匹配
        3. 更新 prematch_features.source_url
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()

        stats = {
            "scanned": len(discovered_urls),
            "matched": 0,
            "saved": 0,
        }

        for url_data in discovered_urls:
            # 检查是否达到最大数量
            if self.discovered_count >= self.max_matches:
                break

            url = url_data["url"]
            match_part = url_data["matchPart"]

            # 尝试从 match_part 提取球队名
            # 格式: team1-team2-xyz
            parts = match_part.split("-")

            if len(parts) < 2:
                continue

            # 尝试匹配数据库中的比赛
            # 使用 LIKE 模糊匹配
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
                  )
                RETURNING pf.match_id
            """, (
                url,
                league,
                f"{parts[0]}%",
                f"{parts[-1]}%"
            ))

            if cursor.rowcount > 0:
                match_id = cursor.fetchone()[0]
                stats["matched"] += 1
                stats["saved"] += 1
                self.discovered_count += 1
                logger.info(f"  匹配: {match_id} <- {url}")

            # 提交每次更新
            conn.commit()

        cursor.close()
        conn.close()

        return stats

    async def run(self) -> dict:
        """运行扫描流程"""
        logger.info("=" * 60)
        logger.info("【V54.1 URL 发现引擎 V2】")
        logger.info("=" * 60)
        logger.info(f"最大扫描数量: {self.max_matches}")
        logger.info("")

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )

            context = await browser.new_context(
                user_agent=random.choice(UA_POOL),
                viewport={"width": 1920, "height": 1080}
            )

            page = await context.new_page()

            all_stats = {
                "total_scanned": 0,
                "total_matched": 0,
            }

            for league, url in SEASON_URLS.items():
                if self.discovered_count >= self.max_matches:
                    logger.info(f"已达到最大数量 {self.max_matches}，停止扫描")
                    break

                # 扫描页面
                discovered = await self.scan_season_page(page, league, url)

                if not discovered:
                    continue

                # 匹配并保存
                stats = self.match_and_save_urls(league, discovered)

                all_stats["total_scanned"] += stats["scanned"]
                all_stats["total_matched"] += stats["matched"]

                # 随机延迟
                if self.discovered_count < self.max_matches:
                    await asyncio.sleep(random.uniform(3, 5))

            await browser.close()

        return all_stats


# ============================================================
# 主函数
# ============================================================

async def main():
    """主函数"""
    # 测试模式：仅扫描 10 条
    engine = URLDiscoveryEngineV2(max_matches=10)

    result = await engine.run()

    # 输出报告
    print()
    print("=" * 60)
    print("【V54.1 URL 发现报告 V2】")
    print("=" * 60)
    print()
    print(f"[Status] 成功提取带 ID 的真实 URL 数量: {result['total_matched']}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
