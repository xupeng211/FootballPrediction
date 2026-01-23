#!/usr/bin/env python3
"""V41.660 OSS Intelligence Capture - 汲取开源逻辑突破哈希封锁.

核心理念：
    不再扫描 <a> 标签，而是参考 OddsHarvester、Mg30 等开源项目，
    直接从 <script> 中提取 feed URL，解密加密数据。

关键突破 (Stack Overflow 2024/12):
    - Feed URL 格式: /feed/match-event/{version}-{sport}-{unique_id}-1-2-{hash}.dat
    - 加密方式: AES-256-CBC + PBKDF2 密钥派生
    - 密码: "%RtR8AB&\nWsh=AQC+v!=pgAe@dSQG3kQ"
    - 盐值: "orieC_jQQWRmhkPvR6u2kzXeTube6aYupiOddsPortal"

Usage:
    # 单条记录测试
    python scripts/ops/v41_660_oss_capture.py --fotmob-id <MATCH_ID>

    # 批量处理（英超缺失记录）
    python scripts/ops/v41_660_oss_capture.py --league "Premier League" --limit 100

    # 完整回填
    python scripts/ops/v41_660_oss_capture.py --mode recovery
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import logging
from typing import Any

import click
from playwright.async_api import Page, async_playwright
import psycopg2
from psycopg2.extras import RealDictCursor
import requests

from src.config_unified import get_settings
from src.core.oddsportal_decryptor import FeedURLExtractor, OddsPortalDecryptor

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration & Constants
# ============================================================================

# OddsPortal Feed API 基础 URL
ODDSPORTAL_FEED_BASE = "https://www.oddsportal.com/feed"

# 请求头（模拟浏览器 AJAX 请求）
FEED_HEADERS = {
    "authority": "www.oddsportal.com",
    "method": "GET",
    "scheme": "https",
    "accept": "application/json, text/plain, */*",
    "accept-encoding": "deflate",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "referer": "https://www.oddsportal.com/",
    "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "x-requested-with": "XMLHttpRequest",
}

# 并发配置
DEFAULT_CONCURRENT_WORKERS = 18
DEFAULT_PAGE_TIMEOUT = 60000


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class MatchRecord:
    """数据库中的比赛记录."""

    fotmob_id: str
    home_team: str
    away_team: str
    match_date: datetime
    league_name: str
    season: str


@dataclass
class OSSCapturedMatch:
    """OSS 智能捕获的比赛数据."""

    hash: str | None = None
    url: str | None = None
    feed_url: str | None = None
    raw_data: dict[str, Any] | None = None

    # 从解密数据中提取的信息
    home_team: str | None = None
    away_team: str | None = None
    match_date: datetime | None = None

    # 相似度评分
    home_similarity: float = 0.0
    away_similarity: float = 0.0
    overall_similarity: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "hash": self.hash,
            "url": self.url,
            "feed_url": self.feed_url,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "match_date": self.match_date.isoformat() if self.match_date else None,
            "home_similarity": self.home_similarity,
            "away_similarity": self.away_similarity,
            "overall_similarity": self.overall_similarity,
        }


@dataclass
class RecoveryResult:
    """回填结果统计."""

    total_processed: int = 0
    successful_matches: int = 0
    failed_matches: int = 0
    decryption_failures: int = 0
    feed_not_found: int = 0

    # 成功恢复的记录
    recovered_records: list[dict[str, Any]] = field(default_factory=list)


# ============================================================================
# Core Implementation
# ============================================================================


class OSSIntelligenceMapper:
    """V41.660 OSS 智能捕获映射器.

    核心功能：
        1. 从 <script> 中提取 feed URL
        2. 下载并解密加密的 .dat 文件
        3. 解析 JSON 数据提取比赛信息
        4. 通过球队名匹配找到对应记录
    """

    def __init__(self, enable_ghost: bool = True):
        """初始化映射器.

        Args:
            enable_ghost: 是否启用隐身保护
        """
        self.enable_ghost = enable_ghost
        self.settings = get_settings()
        self.feed_extractor = FeedURLExtractor()
        self.decryptor = OddsPortalDecryptor()

    async def find_match_by_oss_capture(
        self,
        record: MatchRecord,
        page: Page,
    ) -> OSSCapturedMatch | None:
        """通过 OSS 智能捕获查找匹配的比赛.

        Args:
            record: 数据库中的比赛记录
            page: Playwright 页面对象

        Returns:
            找到的比赛数据
        """
        logger.info(
            f"[OSSCapture] 查找比赛: {record.home_team} vs {record.away_team} "
            f"({record.match_date.date()})"
        )

        try:
            # Step 1: 构造联赛页面 URL
            league_url = self._build_league_url(record)
            logger.info(f"[OSSCapture] 访问联赛页面: {league_url}")

            # Step 2: 访问页面并拦截网络请求（获取 feed URLs）
            feed_urls = []

            async def capture_feed_url(route):
                """拦截网络请求，捕获 feed URL."""
                request = route.request
                url = request.url

                # 检查是否是 feed URL
                if "/feed/match-event/" in url and ".dat" in url:
                    logger.info(f"[OSSCapture] 拦截到 feed URL: {url}")
                    # 提取相对路径
                    relative_path = url.split("oddsportal.com/")[-1]
                    feed_urls.append(f"/{relative_path}")

                # 继续请求
                await route.continue_()

            # 设置请求拦截
            await page.route("**/*", capture_feed_url)

            await page.goto(league_url, timeout=DEFAULT_PAGE_TIMEOUT, wait_until="domcontentloaded")

            # 等待 Vue.js 应用加载和 XHR 请求
            try:
                await page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                pass

            # 额外等待动态内容
            await asyncio.sleep(10)

            # 移除请求拦截
            await page.unroute("**/*")

            if not feed_urls:
                logger.warning("[OSSCapture] 未找到 feed URLs")
                return None

            logger.info(f"[OSSCapture] 找到 {len(feed_urls)} 个 feed URLs")

            # Step 4: 下载并解密 feed 数据
            best_match = None
            best_score = 0.0

            for feed_url in feed_urls:
                try:
                    # 构造完整的 feed URL
                    full_feed_url = f"{ODDSPORTAL_FEED_BASE}{feed_url}"

                    # 下载加密数据
                    encrypted_data = await self._download_feed_data(full_feed_url)

                    if not encrypted_data:
                        continue

                    # 解密数据
                    decrypted_data = self.decryptor.decrypt_feed(encrypted_data)

                    if not decrypted_data:
                        logger.warning(f"[OSSCapture] 解密失败: {feed_url}")
                        continue

                    # 从解密数据中提取比赛信息
                    captured = self._extract_match_from_decrypted_data(
                        decrypted_data,
                        feed_url,
                        record,
                    )

                    if captured and captured.overall_similarity > best_score:
                        best_score = captured.overall_similarity
                        best_match = captured

                except Exception as e:
                    logger.debug(f"[OSSCapture] 处理 feed 失败: {e}")
                    continue

            if best_match:
                logger.info(
                    f"[OSSCapture] ✓ 找到匹配: {best_match.home_team} vs {best_match.away_team} "
                    f"(similarity: {best_match.overall_similarity:.1f}%)"
                )
                return best_match
            logger.warning("[OSSCapture] ✗ 未找到匹配")
            return None

        except Exception as e:
            logger.exception(f"[OSSCapture] 查找比赛失败: {e}")
            return None

    def _build_league_url(self, record: MatchRecord) -> str:
        """构造联赛页面 URL.

        Args:
            record: 比赛记录

        Returns:
            联赛页面 URL
        """
        # 将联赛名转换为 URL 格式
        league_slug = self._league_to_slug(record.league_name)

        # 转换赛季格式: 2024/2025 -> 2024-2025
        season_slug = record.season.replace("/", "-")

        return f"https://www.oddsportal.com/football/england/{league_slug}-{season_slug}/"

    def _league_to_slug(self, league_name: str) -> str:
        """将联赛名转换为 URL slug.

        Args:
            league_name: 联赛名称

        Returns:
            URL slug
        """
        league_map = {
            "Premier League": "premier-league",
            "La Liga": "laliga",
            "Bundesliga": "bundesliga",
            "Serie A": "serie-a",
            "Ligue 1": "ligue-1",
        }
        return league_map.get(league_name, league_name.lower().replace(" ", "-"))

    async def _download_feed_data(self, feed_url: str) -> str | None:
        """下载加密的 feed 数据.

        Args:
            feed_url: Feed URL

        Returns:
            加密的 Base64 数据
        """
        try:
            logger.debug(f"[OSSCapture] 下载 feed: {feed_url}")

            # 使用同步 requests 下载（因为 Playwright 的 fetch API 对跨域有限制）
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(feed_url, headers=FEED_HEADERS, timeout=30),
            )

            if response.status_code == 200:
                return response.text
            logger.warning(f"[OSSCapture] HTTP {response.status_code}: {feed_url}")
            return None

        except Exception as e:
            logger.debug(f"[OSSCapture] 下载失败: {e}")
            return None

    def _extract_match_from_decrypted_data(
        self,
        decrypted_data: dict[str, Any],
        feed_url: str,
        record: MatchRecord,
    ) -> OSSCapturedMatch | None:
        """从解密数据中提取比赛信息.

        Args:
            decrypted_data: 解密后的 JSON 数据
            feed_url: Feed URL
            record: 数据库中的比赛记录

        Returns:
            捕获的比赛数据
        """
        # 从 feed URL 提取 hash
        unique_id = self.feed_extractor.extract_unique_id_from_url(feed_url)

        if not unique_id:
            return None

        # 尝试从解密数据中提取球队名
        home_team = decrypted_data.get("home", "")
        away_team = decrypted_data.get("away", "")

        # 计算相似度
        from thefuzz import fuzz

        home_sim = fuzz.ratio(
            record.home_team.lower(),
            home_team.lower() if home_team else "",
        )
        away_sim = fuzz.ratio(
            record.away_team.lower(),
            away_team.lower() if away_team else "",
        )
        overall_sim = (home_sim + away_sim) / 2

        # 构造捕获对象
        captured = OSSCapturedMatch(
            hash=unique_id,
            url=f"https://www.oddsportal.com/feed{feed_url}",
            feed_url=feed_url,
            raw_data=decrypted_data,
            home_team=home_team,
            away_team=away_team,
            home_similarity=home_sim,
            away_similarity=away_sim,
            overall_similarity=overall_sim,
        )

        return captured


# ============================================================================
# Batch Processing
# ============================================================================


async def process_single_record(
    mapper: OSSIntelligenceMapper,
    browser,
    record: MatchRecord,
    index: int,
) -> dict[str, Any] | None:
    """处理单条记录.

    Args:
        mapper: 映射器实例
        browser: Playwright 浏览器实例
        record: 比赛记录
        index: 记录索引

    Returns:
        处理结果字典
    """
    logger.info(f"[Process {index}] 处理记录 {index + 1}: {record.fotmob_id}")

    try:
        # 创建新的浏览器上下文和页面
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )

        page = await context.new_page()

        # 查找匹配
        captured = await mapper.find_match_by_oss_capture(record, page)

        await context.close()

        if captured and captured.hash:
            # 保存到数据库
            success = await save_match_to_database(record, captured)

            return {
                "success": success,
                "fotmob_id": record.fotmob_id,
                "home_team": record.home_team,
                "away_team": record.away_team,
                "match_date": record.match_date.isoformat(),
                "captured_hash": captured.hash,
                "captured_url": captured.url,
                "similarity": captured.overall_similarity,
            }
        return {
            "success": False,
            "fotmob_id": record.fotmob_id,
            "reason": "no_match_found",
        }

    except Exception as e:
        logger.exception(f"[Process {index}] 处理失败: {e}")
        return {
            "success": False,
            "fotmob_id": record.fotmob_id,
            "reason": str(e),
        }


async def save_match_to_database(
    record: MatchRecord,
    captured: OSSCapturedMatch,
) -> bool:
    """保存匹配结果到数据库.

    Args:
        record: 数据库中的比赛记录
        captured: 捕获的比赛数据

    Returns:
        是否保存成功
    """
    settings = get_settings()

    try:
        conn = psycopg2.connect(
            host=settings.database.host,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

        cur = conn.cursor()

        # 更新 matches_mapping 表
        cur.execute(
            """
            UPDATE matches_mapping
            SET oddsportal_hash = %s,
                oddsportal_url = %s,
                mapping_method = 'v41_660_oss_capture',
                confidence = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE fotmob_id = %s
        """,
            (
                captured.hash,
                captured.url,
                captured.overall_similarity / 100.0,
                record.fotmob_id,
            ),
        )

        conn.commit()
        conn.close()

        logger.info(f"[Database] ✓ 保存成功: {record.fotmob_id} -> {captured.hash}")
        return True

    except Exception as e:
        logger.exception(f"[Database] ✗ 保存失败: {e}")
        return False


# ============================================================================
# CLI Entry Point
# ============================================================================


@click.command()
@click.option("--fotmob-id", help="指定单条比赛 ID")
@click.option("--league", help="指定联赛名称")
@click.option("--season", help="指定赛季")
@click.option("--limit", type=int, default=100, help="处理记录数量限制")
@click.option("--dry-run", is_flag=True, help="模拟运行，不实际更新数据库")
@click.option("--mode", type=click.Choice(["single", "recovery"]), default="single", help="运行模式")
def main(
    fotmob_id: str | None,
    league: str | None,
    season: str | None,
    limit: int,
    dry_run: bool,
    mode: str,
):
    """V41.660 OSS Intelligence Capture - 汲取开源逻辑突破哈希封锁."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("=" * 80)
    logger.info("V41.660 OSS Intelligence Capture - 启动")
    logger.info("=" * 80)

    if dry_run:
        logger.info("📋 模拟运行模式（不会更新数据库）")

    settings = get_settings()

    # 获取待处理的记录
    conn = psycopg2.connect(
        host=settings.database.host,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor,
    )

    cur = conn.cursor()

    if fotmob_id:
        # 单条记录模式
        cur.execute(
            """
            SELECT fotmob_id, home_team, away_team, match_date, league_name, season
            FROM matches_mapping
            WHERE fotmob_id = %s AND oddsportal_url IS NULL
        """,
            (fotmob_id,),
        )
    elif league:
        # 联赛批量模式
        if season:
            cur.execute(
                """
                SELECT fotmob_id, home_team, away_team, match_date, league_name, season
                FROM matches_mapping
                WHERE league_name = %s AND season = %s AND oddsportal_url IS NULL
                ORDER BY match_date DESC
                LIMIT %s
                """,
                (league, season, limit),
            )
        else:
            cur.execute(
                """
                SELECT fotmob_id, home_team, away_team, match_date, league_name, season
                FROM matches_mapping
                WHERE league_name = %s AND oddsportal_url IS NULL
                ORDER BY match_date DESC
                LIMIT %s
                """,
                (league, limit),
            )
    else:
        # 默认：英超缺失记录（前 100 条）
        cur.execute(
            """
            SELECT fotmob_id, home_team, away_team, match_date, league_name, season
            FROM matches_mapping
            WHERE league_name = 'Premier League'
                AND oddsportal_url IS NULL
            ORDER BY match_date DESC
            LIMIT %s
        """,
            (limit,),
        )

    rows = cur.fetchall()
    conn.close()

    if not rows:
        logger.warning("⚠️  没有找到待处理的记录")
        return

    records = [
        MatchRecord(
            fotmob_id=row["fotmob_id"],
            home_team=row["home_team"],
            away_team=row["away_team"],
            match_date=row["match_date"],
            league_name=row["league_name"],
            season=row["season"],
        )
        for row in rows
    ]

    logger.info(f"📊 找到 {len(records)} 条待处理记录")

    # 创建映射器
    mapper = OSSIntelligenceMapper(enable_ghost=True)

    # 运行处理
    async def run_processing():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            results = []
            for i, record in enumerate(records):
                result = await process_single_record(mapper, browser, record, i)
                results.append(result)

                # 每 10 条记录输出一次进度
                if (i + 1) % 10 == 0:
                    logger.info(f"[Progress] 已处理 {i + 1}/{len(records)} 条记录")

            await browser.close()

            # 生成报告
            successful = sum(1 for r in results if r and r.get("success"))
            logger.info(
                f"""
╔══════════════════════════════════════════════════════════════════════╗
║           V41.660 OSS Intelligence Capture - 回填报告               ║
╚══════════════════════════════════════════════════════════════════════╝

📊 处理统计:
  • 总处理数: {len(results)}
  • 成功匹配: {successful}
  • 匹配失败: {len(results) - successful}
  • 成功率: {(successful / max(1, len(results))) * 100:.2f}%

📋 前 10 条成功记录:
{'-' * 100}
"""
            )

            for i, rec in enumerate(results):
                if rec and rec.get("success"):
                    logger.info(
                        f"""
{i + 1}. {rec['home_team']} vs {rec['away_team']}
   Hash: {rec.get('captured_hash', 'N/A')}
   相似度: {rec.get('similarity', 0):.1f}%
   fotmob_id: {rec['fotmob_id']}
"""
                    )
                    if i >= 9:  # 只显示前 10 条
                        break

    asyncio.run(run_processing())


if __name__ == "__main__":
    main()
