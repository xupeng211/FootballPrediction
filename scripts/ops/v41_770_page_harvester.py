#!/usr/bin/env python3
"""V41.770 Sovereign Pagination - 抽屉式批量收割系统.

核心战略:
    针对 OddsPortal 历史归档页面的数字分页结构（1, 2, 3...），
    重构抓取逻辑。通过 TDD 确保能够稳定识别总页数并完成逐页扫描。

主要功能:
    1. 分页控制器: 识别总页数，支持逐页扫描
    2. 抽屉式批量提取: for page in range(1, N+1) 循环
    3. 内存级双源缝合: 全量哈希池与缺失 MatchID 匹配
    4. 补刀审计模块: 1% 漏网之鱼深度定位

Author: Senior Lead Data Systems Architect (TDD Specialist)
Version: V41.770
Date: 2026-01-22
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import logging
import random
import re
import sys
from typing import Any
from pathlib import Path

from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import RealDictCursor

# 延迟导入 Playwright
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
from src.services.harvest_config import AntiScrapingConfig

# 配置日志
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "v41_770_page_harvester.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# Constants & Config
# ============================================================================

# 五大联赛 2024/25 赛季配置
SEASON_CONFIGS = {
    "2024/2025": {
        "Premier League": {"start_date": "2024-08-17"},
        "La Liga": {"start_date": "2024-08-15"},
        "Bundesliga": {"start_date": "2024-08-23"},
        "Serie A": {"start_date": "2024-08-18"},
        "Ligue 1": {"start_date": "2024-08-16"},
    }
}

# OddsPortal URL 配置
LEAGUE_URLS = {
    "Premier League": "https://www.oddsportal.com/football/england/premier-league/results/",
    "La Liga": "https://www.oddsportal.com/football/spain/laliga/results/",
    "Bundesliga": "https://www.oddsportal.com/football/germany/bundesliga/results/",
    "Serie A": "https://www.oddsportal.com/football/italy/serie-a/results/",
    "Ligue 1": "https://www.oddsportal.com/football/france/ligue-1/results/",
}

# 哈希提取模式
HASH_PATTERNS = [
    re.compile(r"-([A-Za-z0-9]{8})/?$"),
    re.compile(r"-([0-9]{7}[A-Za-z0-9]{3})/?$"),
]

# 队名提取模式
TEAM_PATTERN = re.compile(r"/football/[^/]+/[^/]+/([^/]+)-([^/]+)-[A-Za-z0-9]{8,10}/")

# 模糊匹配阈值
FUZZY_THRESHOLD = 80.0
EXACT_THRESHOLD = 100.0

# 日期容错（±48 小时）- V41.780: 扩展时间窗口以捕获跨洋/跨天比赛
DATE_TOLERANCE_HOURS = 48


# ============================================================================
# Pagination Controller
# ============================================================================


class PaginationController:
    """V41.770: 分页控制器 - 识别总页数和当前页"""

    def __init__(self, html_content: str):
        """初始化分页控制器

        Args:
            html_content: HTML 内容
        """
        self.soup = BeautifulSoup(html_content, "html.parser")

    def get_total_pages(self) -> int:
        """获取总页数

        Returns:
            总页数，如果无法识别则返回 1
        """
        # 查找分页容器
        pagination = self.soup.find("div", class_=re.compile(r"pagination"))
        if not pagination:
            pagination = self.soup.find("ul", class_=re.compile(r"pagination"))

        if not pagination:
            return 1

        # 查找所有页码链接
        page_links = pagination.find_all("a", href=re.compile(r"#\d+"))

        if not page_links:
            return 1

        # 提取最大页码
        max_page = 1
        for link in page_links:
            href = link.get("href", "")
            match = re.search(r"#(\d+)", href)
            if match:
                page_num = int(match.group(1))
                if page_num > max_page:
                    max_page = page_num

        return max_page

    def get_current_page(self) -> int:
        """获取当前页码

        Returns:
            当前页码，如果无法识别则返回 1
        """
        # 查找激活的页码
        active_link = self.soup.find("li", class_="active")
        if active_link:
            span = active_link.find("span")
            if span:
                try:
                    return int(span.get_text().strip())
                except ValueError:
                    pass

        # 查找包含当前页码的链接
        active_link = self.soup.find("a", class_="active")
        if active_link:
            try:
                return int(active_link.get_text().strip())
            except ValueError:
                pass

        return 1

    def get_pagination_links(self) -> list[str]:
        """获取所有分页链接

        Returns:
            分页链接列表（如 ["#2", "#3", ...]）
        """
        pagination = self.soup.find("div", class_=re.compile(r"pagination"))
        if not pagination:
            pagination = self.soup.find("ul", class_=re.compile(r"pagination"))

        if not pagination:
            return []

        links = []
        for link in pagination.find_all("a", href=True):
            href = link.get("href", "")
            if re.match(r"#\d+$", href):
                links.append(href)

        return links


# ============================================================================
# Hash Extraction Functions
# ============================================================================


def extract_hashes_from_html(html_content: str) -> list[dict[str, Any]]:
    """从 HTML 内容提取所有哈希值

    Args:
        html_content: HTML 内容

    Returns:
        哈希条目列表，每个条目包含 hash_value, home_team, away_team, url
    """
    soup = BeautifulSoup(html_content, "html.parser")
    matches = []
    seen_hashes = set()

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

            matches.append({
                "home_team": home_team,
                "away_team": away_team,
                "hash_value": hash_value,
                "url": f"https://www.oddsportal.com{href}",
                "match_date": None,  # 需要从页面或数据库获取
            })

    return matches


def construct_page_url(base_url: str, page_num: int) -> str:
    """构造分页 URL

    Args:
        base_url: 基础 URL
        page_num: 页码

    Returns:
        分页 URL
    """
    if page_num == 1:
        return base_url

    # 添加页码参数（OddsPortal 格式：#page/N/）
    if base_url.endswith("/"):
        return base_url + f"#page/{page_num}/"
    else:
        return base_url + f"/#page/{page_num}/"


def generate_page_range(start: int, end: int):
    """生成页码范围

    Args:
        start: 起始页码
        end: 结束页码

    Yields:
        页码
    """
    for page in range(start, end + 1):
        yield page


# ============================================================================
# In-Memory Stitching
# ============================================================================


def stitch_matches_with_fuzzy(
    harvested_hashes: list[dict[str, Any]],
    missing_matches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """内存级双源缝合 - 使用模糊匹配将采集哈希与缺失记录配对

    Args:
        harvested_hashes: 采集的哈希池
        missing_matches: 数据库缺失记录

    Returns:
        匹配结果列表
    """
    alignments = []

    for missing in missing_matches:
        best_match = None
        best_similarity = 0.0
        best_confidence = "low"

        for harvested in harvested_hashes:
            # 队名相似度
            team_similarity = calculate_match_similarity(
                missing["home_team"],
                missing["away_team"],
                harvested["home_team"],
                harvested["away_team"],
            )

            # 日期检查
            date_match = True
            if missing.get("match_date") and harvested.get("match_date"):
                date_diff = _calculate_date_diff_hours(
                    missing["match_date"],
                    harvested["match_date"]
                )
                date_match = abs(date_diff) <= DATE_TOLERANCE_HOURS

            # 综合判断
            if team_similarity >= EXACT_THRESHOLD:
                if date_match:
                    best_match = harvested
                    best_similarity = team_similarity
                    best_confidence = "high"
                    break  # 精确匹配，无需继续查找
            elif team_similarity >= FUZZY_THRESHOLD:
                if date_match and team_similarity > best_similarity:
                    best_match = harvested
                    best_similarity = team_similarity
                    best_confidence = "medium"

        if best_match:
            alignments.append({
                "fotmob_id": missing["match_id"],
                "oddsportal_hash": best_match["hash_value"],
                "oddsportal_url": best_match["url"],
                "similarity": best_similarity,
                "confidence": best_confidence,
                "match_date": missing.get("match_date"),
                "league_name": missing.get("league_name"),
            })

    return alignments


def _calculate_date_diff_hours(date1_str: str, date2_str: str) -> float:
    """计算两个日期之间的小时差

    Args:
        date1_str: 日期字符串 1
        date2_str: 日期字符串 2

    Returns:
        小时差（带符号）
    """
    try:
        date1 = datetime.strptime(date1_str.split()[0], "%Y-%m-%d")
        date2 = datetime.strptime(date2_str.split()[0], "%Y-%m-%d")
        return (date1 - date2).total_seconds() / 3600
    except:
        return 0.0


# ============================================================================
# Audit Finisher
# ============================================================================


def identify_orphan_matches(
    all_match_ids: list[str],
    matched_ids: list[str],
) -> list[str]:
    """识别未匹配的孤儿记录

    Args:
        all_match_ids: 所有比赛 ID
        matched_ids: 已匹配的比赛 ID

    Returns:
        孤儿比赛 ID 列表
    """
    matched_set = set(matched_ids)
    return [mid for mid in all_match_ids if mid not in matched_set]


def calculate_completion_rate(total: int, matched: int) -> float:
    """计算完成率

    Args:
        total: 总数
        matched: 已匹配数

    Returns:
        完成率（百分比）
    """
    if total == 0:
        return 0.0
    return (matched / total) * 100


def should_trigger_deep_mining(total: int, matched: int) -> bool:
    """判断是否触发深度挖掘（补刀模式）

    Args:
        total: 总数
        matched: 已匹配数

    Returns:
        是否触发深度挖掘
    """
    completion_rate = calculate_completion_rate(total, matched)
    return completion_rate < 99.0


# ============================================================================
# Main Harvester Class
# ============================================================================


class PageHarvestController:
    """V41.770: 抽屉式批量收割控制器"""

    def __init__(
        self,
        league_name: str,
        season: str,
        test_page: int | None = None,
        headless: bool = True,
    ):
        """初始化控制器

        Args:
            league_name: 联赛名称
            season: 赛季（如 "2024/2025"）
            test_page: 测试模式：只抓取指定页码
            headless: 是否无头模式
        """
        self.league_name = league_name
        self.season = season
        self.test_page = test_page
        self.headless = headless

        # 初始化 BaseExtractor
        self.extractor = BaseExtractor(auto_proxy=True)

        # 数据库配置
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
            "pages_processed": 0,
            "total_pages": 0,
            "matches_harvested": 0,
            "matches_aligned": 0,
            "matches_updated": 0,
            "orphan_count": 0,
            "start_time": None,
            "end_time": None,
        }

        # 哈希池
        self.harvested_hashes: list[dict[str, Any]] = []

        # 推导 URL
        self.base_url = LEAGUE_URLS.get(league_name)
        if not self.base_url:
            raise ValueError(f"❌ 联赛 [{league_name}] 没有配置 URL")

    async def harvest(self) -> dict[str, Any]:
        """执行抽屉式批量收割

        Returns:
            采集统计信息
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright 未安装")

        self.stats["start_time"] = datetime.now()

        logger.info("=" * 60)
        logger.info("🏰 V41.770 Sovereign Pagination - 抽屉式批量收割")
        logger.info("=" * 60)
        logger.info(f"🚀 开始采集联赛 [{self.league_name}] {self.season}")
        logger.info(f"   URL: {self.base_url}")
        if self.test_page:
            logger.info(f"   测试模式: 只抓取第 {self.test_page} 页")
        logger.info("")

        async with async_playwright() as p:
            # 获取代理配置
            wsl2_host = self.extractor._get_wsl2_host_ip()
            proxy_config = None
            if wsl2_host:
                proxy_config = {"server": f"http://{wsl2_host}:7892"}

            # 启动浏览器
            browser = await p.chromium.launch(
                headless=self.headless,
                proxy=proxy_config,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )

            context = await browser.new_context(
                user_agent=self.extractor.get_random_user_agent(),
                viewport=self.extractor.get_random_viewport(),
            )

            page = await context.new_page()

            try:
                # 测试模式：只抓取指定页码
                if self.test_page:
                    await self._harvest_single_page(page, self.test_page)
                else:
                    # 正常模式：执行抽屉式批量收割
                    await self._harvest_all_pages(page)

                # 执行数据库对齐
                await self._align_with_database()

                # 补刀审计
                if self.stats["orphan_count"] > 0:
                    await self._audit_finisher()

                self.stats["end_time"] = datetime.now()
                duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()

                logger.info("")
                logger.info("=" * 60)
                logger.info("✅ V41.770 采集完成:")
                logger.info("=" * 60)
                logger.info(f"   - 总耗时: {duration:.1f} 秒")
                logger.info(f"   - 处理页数: {self.stats['pages_processed']}")
                logger.info(f"   - 采集哈希: {self.stats['matches_harvested']}")
                logger.info(f"   - 对齐记录: {self.stats['matches_aligned']}")
                logger.info(f"   - 更新记录: {self.stats['matches_updated']}")
                logger.info(f"   - 孤儿记录: {self.stats['orphan_count']}")
                logger.info("=" * 60)

                return self.stats

            finally:
                await context.close()
                await browser.close()

    async def _harvest_all_pages(self, page: Page) -> None:
        """抽屉式批量收割所有页面

        Args:
            page: Playwright 页面对象
        """
        # 访问第一页，获取总页数
        await page.goto(self.base_url, wait_until="networkidle")

        content = await page.content()
        controller = PaginationController(content)
        total_pages = controller.get_total_pages()

        self.stats["total_pages"] = total_pages
        logger.info(f"📊 检测到总页数: {total_pages}")

        # 提取第一页哈希
        hashes = extract_hashes_from_html(content)
        self.harvested_hashes.extend(hashes)
        logger.info(f"   第 1 页: 提取 {len(hashes)} 个哈希")
        self.stats["pages_processed"] = 1

        # 抽屉式遍历剩余页面
        for page_num in range(2, total_pages + 1):
            page_url = construct_page_url(self.base_url, page_num)
            await page.goto(page_url, wait_until="networkidle")
            await asyncio.sleep(random.uniform(1.0, 2.0))  # 人类延迟

            content = await page.content()
            hashes = extract_hashes_from_html(content)
            self.harvested_hashes.extend(hashes)

            self.stats["pages_processed"] = page_num
            logger.info(f"   第 {page_num} 页: 提取 {len(hashes)} 个哈希")

            # 避免过于频繁的请求
            if page_num % 10 == 0:
                logger.info(f"   进度: {page_num}/{total_pages} ({page_num*100//total_pages}%)")

        self.stats["matches_harvested"] = len(self.harvested_hashes)

    async def _harvest_single_page(self, page: Page, page_num: int) -> None:
        """收割单页（测试模式）

        Args:
            page: Playwright 页面对象
            page_num: 页码
        """
        page_url = construct_page_url(self.base_url, page_num)
        logger.info(f"🧪 测试模式: 访问第 {page_num} 页")
        logger.info(f"   URL: {page_url}")

        await page.goto(page_url, wait_until="networkidle")
        await asyncio.sleep(2.0)  # 等待加载

        content = await page.content()
        hashes = extract_hashes_from_html(content)

        self.harvested_hashes.extend(hashes)
        self.stats["pages_processed"] = 1
        self.stats["matches_harvested"] = len(hashes)

        logger.info(f"📊 第 {page_num} 页: 提取 {len(hashes)} 个哈希")

    async def _align_with_database(self) -> None:
        """与数据库进行对齐"""
        missing_matches = self._get_missing_matches()

        if not missing_matches:
            logger.info("✅ 数据库无缺失记录")
            return

        logger.info(f"🔍 数据库缺失 {len(missing_matches)} 场比赛，开始对齐...")

        # 使用模糊匹配进行缝合
        alignments = stitch_matches_with_fuzzy(self.harvested_hashes, missing_matches)

        self.stats["matches_aligned"] = len(alignments)

        # 执行数据库更新
        with psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor) as conn:
            cursor = conn.cursor()

            for alignment in alignments:
                self._upsert_match(cursor, alignment)

            conn.commit()

    async def _audit_finisher(self) -> None:
        """补刀审计模块"""
        logger.info("")
        logger.info("🔍 V41.770 补刀审计模块:")

        # 获取所有需要处理的比赛 ID
        all_missing = self._get_missing_matches()
        all_match_ids = [m["match_id"] for m in all_missing]

        # 已处理的比赛 ID
        matched_ids = [
            a["fotmob_id"]
            for a in stitch_matches_with_fuzzy(self.harvested_hashes, all_missing)
        ]

        # 识别孤儿记录
        orphans = identify_orphan_matches(all_match_ids, matched_ids)
        self.stats["orphan_count"] = len(orphans)

        if orphans:
            logger.info(f"   发现 {len(orphans)} 条孤儿记录")
            logger.info("   建议执行深度定位模式")
        else:
            logger.info("   ✅ 无孤儿记录，100% 完成！")

    def _get_missing_matches(self) -> list[dict[str, Any]]:
        """查询数据库缺失记录"""
        with psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor) as conn:
            cursor = conn.cursor()

            query = """
                SELECT m.match_id, m.home_team, m.away_team, m.match_date, m.league_name
                FROM matches m
                LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
                WHERE m.league_name = %s
                  AND m.season = %s
                  AND mm.oddsportal_hash IS NULL
                ORDER BY m.match_date DESC
            """

            cursor.execute(query, (self.league_name, self.season))
            return cursor.fetchall()

    def _upsert_match(self, cursor, alignment: dict[str, Any]) -> None:
        """执行 UPSERT 操作（带重复哈希检查）"""
        fotmob_id = alignment["fotmob_id"]
        hash_value = alignment["oddsportal_hash"]

        # 检查哈希是否已存在
        check_query = """
            SELECT fotmob_id FROM matches_mapping
            WHERE oddsportal_hash = %s AND fotmob_id != %s
            LIMIT 1
        """
        cursor.execute(check_query, (hash_value, fotmob_id))
        existing = cursor.fetchone()

        if existing:
            logger.debug(f"⏭️ 哈希 {hash_value} 已存在，跳过")
            return

        # 执行 UPSERT
        upsert_query = """
            INSERT INTO matches_mapping (fotmob_id, oddsportal_hash, oddsportal_url, match_date, league_name, mapping_method)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (fotmob_id)
            DO UPDATE SET
                oddsportal_hash = EXCLUDED.oddsportal_hash,
                oddsportal_url = EXCLUDED.oddsportal_url,
                match_date = EXCLUDED.match_date,
                league_name = EXCLUDED.league_name,
                mapping_method = EXCLUDED.mapping_method,
                updated_at = CURRENT_TIMESTAMP
        """

        cursor.execute(upsert_query, (
            fotmob_id,
            hash_value,
            alignment["oddsportal_url"],
            alignment["match_date"],
            alignment["league_name"],
            "v41.770_page_harvest",
        ))

        self.stats["matches_updated"] += 1


# ============================================================================
# CLI Entry Point
# ============================================================================


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="V41.770 Sovereign Pagination - 抽屉式批量收割系统"
    )

    parser.add_argument(
        "--league",
        type=str,
        choices=list(LEAGUE_URLS.keys()),
        help="指定联赛",
    )

    parser.add_argument(
        "--season",
        type=str,
        default="2024/2025",
        help="赛季（默认: 2024/2025）",
    )

    parser.add_argument(
        "--test-page",
        type=int,
        help="测试模式：只抓取指定页码",
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="无头模式（默认: True）",
    )

    return parser.parse_args()


async def main() -> int:
    """主入口点"""
    args = parse_args()

    controller = PageHarvestController(
        league_name=args.league,
        season=args.season,
        test_page=args.test_page,
        headless=args.headless,
    )

    stats = await controller.harvest()

    # 验收标准
    if args.test_page:
        # 测试模式：至少提取 10 个哈希
        if stats["matches_harvested"] >= 10:
            logger.info(f"✅ 测试通过: 提取 {stats['matches_harvested']} 个哈希 >= 10")
            return 0
        else:
            logger.warning(f"⚠️ 测试未通过: 提取 {stats['matches_harvested']} 个哈希 < 10")
            return 1
    else:
        # 正常模式：检查完成率
        total = 380  # 预估总比赛数
        completion_rate = (stats["matches_updated"] / total * 100) if total > 0 else 0

        if completion_rate >= 20.0:  # 20% 作为初步验收标准
            logger.info(f"✅ 验收通过: 完成率 {completion_rate:.1f}% >= 20%")
            return 0
        else:
            logger.warning(f"⚠️ 验收未通过: 完成率 {completion_rate:.1f}% < 20%")
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
