#!/usr/bin/env python3
"""V41.730 Smart Bulk Pagination - 批量化翻页补全方案.

核心设计：
    放弃对 API 接口的死磕，重构基于 Playwright 的分页抓取逻辑。
    目标：单次页面加载、全量哈希提取、批量数据库对齐。

主要功能：
    1. 单次加载-批量匹配：启动 Playwright 访问联赛 Results 页面
    2. 持续点击"Load More"直到页面日期跨过目标赛季起点
    3. 采集页面所有 <a> 标签，用正则提取 [队名 + 哈希]
    4. 内存中与数据库 matches_mapping 的缺失项进行模糊匹配
    5. ON CONFLICT UPDATE 冲突解决逻辑

Author: Senior Data Systems Architect (TDD Specialist)
Version: V41.730
Date: 2026-01-22
"""

from __future__ import annotations

import asyncio
import argparse
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import os
import random
import re
from typing import Any

from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import RealDictCursor

# V41.730: 延迟导入 Playwright (避免环境不支持时失败)
try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None

from src.config_unified import get_settings
from src.core.team_name_normalizer import (
    normalize_team_name,
    calculate_match_similarity,
)
from src.api.collectors.base_extractor import BaseExtractor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/v41_730_bulk_harvest.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# Constants & Config
# ============================================================================

# 五大联赛 2024-25 赛季起点配置
SEASON_START_DATES = {
    "Premier League": datetime(2024, 8, 17),
    "La Liga": datetime(2024, 8, 15),
    "Bundesliga": datetime(2024, 8, 23),
    "Serie A": datetime(2024, 8, 18),
    "Ligue 1": datetime(2024, 8, 16),
}

# OddsPortal URL 配置
LEAGUE_URLS = {
    "Premier League": "https://www.oddsportal.com/football/england/premier-league-2024-2025/results/",
    "La Liga": "https://www.oddsportal.com/football/spain/laliga-2024-2025/results/",
    "Bundesliga": "https://www.oddsportal.com/football/germany/bundesliga-2024-2025/results/",
    "Serie A": "https://www.oddsportal.com/football/italy/serie-a-2024-2025/results/",
    "Ligue 1": "https://www.oddsportal.com/football/france/ligue-1-2024-2025/results/",
}

# 哈希提取模式（新旧两种格式）
HASH_PATTERNS = [
    # 新格式：8 位字母数字
    re.compile(r"-([A-Za-z0-9]{8})/?$"),
    # 旧格式：7位ID + 3位字母数字 (10位)
    re.compile(r"-([0-9]{7}[A-Za-z0-9]{3})/?$"),
]

# 队名提取模式
TEAM_PATTERN = re.compile(r"/football/[^/]+/[^/]+/([^/]+)-([^/]+)-[A-Za-z0-9]{8,10}/")

# 分页配置
MAX_ITERATIONS = 100  # 最大分页次数（防止无限循环）
SCROLL_DELAY = (1.0, 2.0)  # 滚动延迟范围（秒）
CLICK_DELAY = (0.5, 1.5)  # 点击延迟范围（秒）


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class HarvestedMatch:
    """采集到的比赛记录"""
    home_team: str
    away_team: str
    hash_value: str
    url: str
    league_name: str
    match_date: str | None = None


@dataclass
class MissingMatch:
    """数据库缺失的比赛记录"""
    match_id: str
    home_team: str
    away_team: str
    match_date: str
    league_name: str


@dataclass
class MatchAlignment:
    """匹配结果"""
    fotmob_id: str
    oddsportal_hash: str
    oddsportal_url: str
    similarity: float
    match_date: str
    league_name: str


# ============================================================================
# Core: BulkPaginationController
# ============================================================================


class BulkPaginationController:
    """V41.730 批量分页控制器 - 核心引擎

    功能：
        1. 持续触发"加载更多"直到目标日期出现
        2. 批量提取页面所有哈希
        3. 执行数据库对齐
    """

    def __init__(
        self,
        league_name: str,
        target_date: datetime,
        proxy_port: int | None = None,
        headless: bool = True,
    ):
        """初始化控制器

        Args:
            league_name: 联赛名称
            target_date: 目标日期（赛季起点）
            proxy_port: 代理端口
            headless: 是否无头模式
        """
        self.league_name = league_name
        self.target_date = target_date
        self.target_date_str = target_date.strftime("%Y-%m-%d")
        self.proxy_port = proxy_port
        self.headless = headless

        # 初始化 BaseExtractor 获取代理配置
        self.extractor = BaseExtractor(auto_proxy=True)

        # 数据库连接
        settings = get_settings()
        self.db_config = {
            "host": settings.database.host,
            "port": settings.database.port,
            "database": settings.database.name,
            "user": settings.database.user,
            "password": settings.database.password.get_secret_value(),
        }

        # 统计信息
        self.stats = {
            "iterations": 0,
            "matches_harvested": 0,
            "matches_aligned": 0,
            "matches_updated": 0,
            "start_time": None,
            "end_time": None,
        }

    async def harvest_league(self) -> dict[str, Any]:
        """执行联赛批量采集

        Returns:
            采集统计信息
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright 未安装，请运行: pip install playwright")

        self.stats["start_time"] = datetime.now()
        logger.info(f"🚀 V41.730: 开始采集联赛 [{self.league_name}]")
        logger.info(f"   目标日期: {self.target_date_str}")
        logger.info(f"   URL: {LEAGUE_URLS[self.league_name]}")

        async with async_playwright() as p:
            # 获取代理配置
            proxy_config = None
            if self.proxy_port:
                proxy_config = {
                    "server": f"http://{self.extractor.proxy.wsl2_bridge_host}:{self.proxy_port}"
                }

            # 启动浏览器
            browser = await p.chromium.launch(
                headless=self.headless,
                proxy=proxy_config,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )

            # 创建上下文（使用 Ghost Protocol）
            context = await browser.new_context(
                user_agent=self.extractor.get_random_user_agent(),
                viewport=self.extractor.get_random_viewport(),
            )

            page = await context.new_page()

            try:
                # 访问目标页面
                await page.goto(LEAGUE_URLS[self.league_name], wait_until="networkidle")

                # 持续加载直到目标日期出现
                await self._load_until_target_date(page)

                # 提取所有哈希
                harvested_matches = await self._extract_all_hashes(page)

                self.stats["matches_harvested"] = len(harvested_matches)
                logger.info(f"📊 采集到 {len(harvested_matches)} 场比赛")

                # 执行数据库对齐
                alignments = await self._align_with_database(harvested_matches)

                self.stats["end_time"] = datetime.now()
                duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()

                logger.info(f"✅ 采集完成:")
                logger.info(f"   - 总耗时: {duration:.1f} 秒")
                logger.info(f"   - 采集: {self.stats['matches_harvested']} 场")
                logger.info(f"   - 对齐: {self.stats['matches_aligned']} 场")
                logger.info(f"   - 更新: {self.stats['matches_updated']} 场")

                return self.stats

            finally:
                await context.close()
                await browser.close()

    async def _load_until_target_date(self, page: Page) -> None:
        """持续加载直到目标日期出现

        Args:
            page: Playwright 页面对象
        """
        iteration = 0
        target_found = False

        logger.info("🔄 开始分页加载...")

        while not target_found and iteration < MAX_ITERATIONS:
            iteration += 1
            self.stats["iterations"] = iteration

            # 检查目标日期是否已出现
            content = await page.content()
            if self._has_target_date(content):
                target_found = True
                logger.info(f"✅ 目标日期 {self.target_date_str} 已出现 (迭代 {iteration} 次)")
                break

            # 点击"Load More"按钮或滚动到底部
            try:
                # 尝试点击"Load More"按钮
                load_more_btn = await page.query_selector("a.pagination-next, button[data-load-more], .load-more")
                if load_more_btn:
                    await load_more_btn.click()
                    await asyncio.sleep(random.uniform(*CLICK_DELAY))
                else:
                    # 滚动到底部触发懒加载
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(random.uniform(*SCROLL_DELAY))

            except Exception as e:
                logger.warning(f"⚠️ 分页操作失败: {e}")

            # 人类行为模拟：随机滚动
            await self._human_scroll(page)

        if iteration >= MAX_ITERATIONS:
            logger.warning(f"⚠️ 达到最大迭代次数 ({MAX_ITERATIONS})，可能未加载到目标日期")

    async def _extract_all_hashes(self, page: Page) -> list[HarvestedMatch]:
        """从页面提取所有哈希

        Args:
            page: Playwright 页面对象

        Returns:
            采集到的比赛列表
        """
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")

        matches = []
        seen_hashes = set()  # 去重

        # 查找所有包含比赛链接的 <a> 标签
        links = soup.find_all("a", href=re.compile(r"/football/"))

        for link in links:
            href = link.get("href", "")

            # 提取哈希
            hash_value = None
            for pattern in HASH_PATTERNS:
                match = pattern.search(href)
                if match:
                    hash_value = match.group(1)
                    break

            if not hash_value or hash_value in seen_hashes:
                continue

            seen_hashes.add(hash_value)

            # 提取队名
            team_match = TEAM_PATTERN.search(href)
            if team_match:
                home_team = normalize_team_name(team_match.group(1).replace("-", " "))
                away_team = normalize_team_name(team_match.group(2).replace("-", " "))

                matches.append(HarvestedMatch(
                    home_team=home_team,
                    away_team=away_team,
                    hash_value=hash_value,
                    url=f"https://www.oddsportal.com{href}",
                    league_name=self.league_name,
                ))

        return matches

    async def _align_with_database(
        self,
        harvested_matches: list[HarvestedMatch],
    ) -> list[MatchAlignment]:
        """与数据库进行对齐

        Args:
            harvested_matches: 采集到的比赛列表

        Returns:
            匹配结果列表
        """
        # 查询数据库缺失记录
        missing_matches = self._get_missing_matches()

        if not missing_matches:
            logger.info("✅ 数据库无缺失记录，无需对齐")
            return []

        logger.info(f"🔍 数据库缺失 {len(missing_matches)} 场比赛，开始对齐...")

        alignments = []

        with psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor) as conn:
            cursor = conn.cursor()

            for missing in missing_matches:
                # 查找最佳匹配
                best_match = None
                best_similarity = 0.0

                for harvested in harvested_matches:
                    similarity = calculate_match_similarity(
                        missing["home_team"],
                        missing["away_team"],
                        harvested.home_team,
                        harvested.away_team,
                    )

                    if similarity >= 80.0 and similarity > best_similarity:
                        best_similarity = similarity
                        best_match = harvested

                if best_match:
                    alignment = MatchAlignment(
                        fotmob_id=missing["match_id"],
                        oddsportal_hash=best_match.hash_value,
                        oddsportal_url=best_match.url,
                        similarity=best_similarity,
                        match_date=missing["match_date"],
                        league_name=self.league_name,
                    )
                    alignments.append(alignment)

                    # 执行 UPSERT
                    self._upsert_match(cursor, alignment)

            conn.commit()

        self.stats["matches_aligned"] = len(alignments)
        return alignments

    def _get_missing_matches(self) -> list[dict[str, Any]]:
        """查询数据库缺失的哈希记录

        Returns:
            缺失记录列表
        """
        with psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor) as conn:
            cursor = conn.cursor()

            query = """
                SELECT m.match_id, m.home_team, m.away_team, m.match_date, m.league_name
                FROM matches m
                LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
                WHERE m.league_name = %s
                  AND m.season = '2024-2025'
                  AND mm.oddsportal_hash IS NULL
                ORDER BY m.match_date DESC
            """

            cursor.execute(query, (self.league_name,))
            return cursor.fetchall()

    def _upsert_match(self, cursor, alignment: MatchAlignment) -> None:
        """执行 UPSERT 操作

        Args:
            cursor: 数据库游标
            alignment: 匹配结果
        """
        upsert_query = """
            INSERT INTO matches_mapping (fotmob_id, oddsportal_hash, oddsportal_url, match_date, league_name)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (fotmob_id)
            DO UPDATE SET
                oddsportal_hash = EXCLUDED.oddsportal_hash,
                oddsportal_url = EXCLUDED.oddsportal_url,
                match_date = EXCLUDED.match_date,
                league_name = EXCLUDED.league_name,
                updated_at = CURRENT_TIMESTAMP
        """

        cursor.execute(upsert_query, (
            alignment.fotmob_id,
            alignment.oddsportal_hash,
            alignment.oddsportal_url,
            alignment.match_date,
            alignment.league_name,
        ))

        self.stats["matches_updated"] += 1

    def _has_target_date(self, html_content: str) -> bool:
        """检查 HTML 中是否包含目标日期

        Args:
            html_content: HTML 内容

        Returns:
            是否包含目标日期
        """
        # 检查多种日期格式
        date_patterns = [
            self.target_date_str,  # 2024-08-17
            self.target_date.strftime("%d.%m.%Y"),  # 17.08.2024
            self.target_date.strftime("%d/%m/%Y"),  # 17/08/2024
        ]

        for pattern in date_patterns:
            if pattern in html_content:
                return True

        return False

    async def _human_scroll(self, page: Page, max_scrolls: int = 3) -> None:
        """人类行为模拟：随机滚动

        Args:
            page: Playwright 页面对象
            max_scrolls: 最大滚动次数
        """
        for _ in range(random.randint(1, max_scrolls)):
            scroll_distance = random.randint(300, 800)
            direction = random.choices(["down", "up"], weights=[80, 20])[0]

            if direction == "down":
                await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            else:
                await page.evaluate(f"window.scrollBy(0, -{scroll_distance})")

            await asyncio.sleep(random.uniform(0.5, 2.0))


# ============================================================================
# Concurrent Harvest Manager
# ============================================================================


async def harvest_all_leagues(
    concurrent_limit: int = 3,
    headless: bool = True,
) -> dict[str, Any]:
    """并发采集所有五大联赛

    Args:
        concurrent_limit: 并发限制
        headless: 是否无头模式

    Returns:
        总体统计信息
    """
    overall_stats = {
        "leagues_harvested": 0,
        "total_matches_aligned": 0,
        "total_duration": 0,
        "leagues": {},
    }

    start_time = datetime.now()

    # 创建信号量控制并发
    semaphore = asyncio.Semaphore(concurrent_limit)

    async def harvest_with_semaphore(league_name: str) -> tuple[str, dict[str, Any]]:
        async with semaphore:
            controller = BulkPaginationController(
                league_name=league_name,
                target_date=SEASON_START_DATES[league_name],
                headless=headless,
            )
            stats = await controller.harvest_league()
            return league_name, stats

    # 并发执行所有联赛
    tasks = [harvest_with_semaphore(league) for league in SEASON_START_DATES.keys()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 汇总结果
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"❌ 采集失败: {result}")
            continue

        league_name, stats = result
        overall_stats["leagues"][league_name] = stats
        overall_stats["leagues_harvested"] += 1
        overall_stats["total_matches_aligned"] += stats.get("matches_aligned", 0)

    end_time = datetime.now()
    overall_stats["total_duration"] = (end_time - start_time).total_seconds()

    return overall_stats


# ============================================================================
# CLI Entry Point
# ============================================================================


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="V41.730 Smart Bulk Pagination - 批量化翻页补全方案"
    )

    parser.add_argument(
        "--league",
        type=str,
        choices=list(SEASON_START_DATES.keys()),
        help="指定联赛（不指定则采集所有五大联赛）",
    )

    parser.add_argument(
        "--concurrent",
        type=int,
        default=3,
        help="并发数量（默认: 3）",
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="无头模式（默认: True）",
    )

    parser.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        help="显示浏览器窗口",
    )

    return parser.parse_args()


async def main() -> int:
    """主入口点

    Returns:
        退出码
    """
    args = parse_args()

    logger.info("=" * 60)
    logger.info("V41.730 Smart Bulk Pagination - 批量化翻页补全方案")
    logger.info("=" * 60)

    if args.league:
        # 单个联赛采集
        controller = BulkPaginationController(
            league_name=args.league,
            target_date=SEASON_START_DATES[args.league],
            headless=args.headless,
        )
        stats = await controller.harvest_league()
        return 0 if stats.get("matches_aligned", 0) > 0 else 1
    else:
        # 并发采集所有联赛
        stats = await harvest_all_leagues(
            concurrent_limit=args.concurrent,
            headless=args.headless,
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info("📊 V41.730 总体统计:")
        logger.info("=" * 60)
        logger.info(f"   采集联赛: {stats['leagues_harvested']}/5")
        logger.info(f"   总对齐数: {stats['total_matches_aligned']}")
        logger.info(f"   总耗时: {stats['total_duration']:.1f} 秒")
        logger.info("=" * 60)

        return 0 if stats["total_matches_aligned"] > 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
