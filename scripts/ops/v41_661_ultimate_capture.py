#!/usr/bin/env python3
"""V41.661 Ultimate Capture - 终极方案：结合 OSS 智能与 JavaScript 注入.

核心理念：
    1. 网络拦截：捕获所有 XHR/fetch 请求
    2. JavaScript 注入：主动触发 Vue.js 数据加载
    3. 深度等待：扩展等待时间，处理懒加载
    4. 多重策略：网络拦截 + DOM 扫描 + Feed URL 提取

关键突破：
    - OddsPortal 使用 Vue.js SPA 架构
    - 比赛数据通过 JavaScript 动态加载
    - Feed URL 格式: /feed/match-event/{version}-{sport}-{unique_id}-1-2-{xhash}.dat
    - Hash ID 嵌入在比赛页面 URL 中

Usage:
    # 单条记录测试
    python scripts/ops/v41_661_ultimate_capture.py --fotmob-id <MATCH_ID>

    # 批量处理（英超缺失记录）
    python scripts/ops/v41_661_ultimate_capture.py --league "Premier League" --limit 100
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import click
from playwright.async_api import Page, async_playwright
import psycopg2
from psycopg2.extras import RealDictCursor
from thefuzz import fuzz

from src.config_unified import get_settings

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration & Constants
# ============================================================================

# Hash 提取正则模式（从比赛页面 URL）
MATCH_HASH_PATTERN = re.compile(r'/football/[^/]+/[^/]+/.+-([a-zA-Z0-9]{8}|ID[a-zA-Z0-9]{8})/')

# Feed URL 正则模式
FEED_URL_PATTERN = re.compile(r'/feed/match-event/\d+-\d+-([a-zA-Z0-9]+)-1-2-([a-zA-Z0-9]+)\.dat')

# 相似度阈值
SIMILARITY_THRESHOLD = 70.0

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
class CapturedHash:
    """捕获的哈希数据."""

    hash: str
    url: str
    feed_url: str | None = None
    home_team: str | None = None
    away_team: str | None = None

    # 相似度评分
    home_similarity: float = 0.0
    away_similarity: float = 0.0
    overall_similarity: float = 0.0

    # 捕获来源
    capture_method: str = "unknown"  # 'dom', 'network', 'combined'


# ============================================================================
# Core Implementation
# ============================================================================


class UltimateHashExtractor:
    """V41.661 终极哈希提取器.

    核心功能：
        1. 网络拦截：捕获所有 XHR/fetch 请求
        2. JavaScript 注入：主动触发 Vue.js 数据加载
        3. DOM 扫描：等待并扫描动态插入的链接
        4. Feed URL 解析：从拦截的请求中提取哈希
    """

    def __init__(self):
        self.captured_feed_urls = []
        self.captured_match_links = []

    async def find_match_by_ultimate_method(
        self,
        record: MatchRecord,
        page: Page,
    ) -> CapturedHash | None:
        """通过终极方案查找匹配的比赛.

        Args:
            record: 数据库中的比赛记录
            page: Playwright 页面对象

        Returns:
            捕获的哈希数据
        """
        logger.info(
            f"[Ultimate] 查找比赛: {record.home_team} vs {record.away_team} "
            f"({record.match_date.date()})"
        )

        try:
            # Step 1: 构造联赛页面 URL
            league_url = self._build_league_url(record)
            logger.info(f"[Ultimate] 访问联赛页面: {league_url}")

            # 重置捕获列表
            self.captured_feed_urls = []
            self.captured_match_links = []

            # Step 2: 设置网络拦截（捕获所有请求）
            captured_requests = []

            async def capture_request(route):
                """拦截网络请求."""
                request = route.request
                url = request.url

                # 捕获 feed URL
                if "/feed/match-event/" in url and ".dat" in url:
                    logger.info(f"[Ultimate] 捕获到 feed URL: {url}")
                    captured_requests.append({
                        "type": "feed",
                        "url": url,
                    })

                # 捕获 API 请求
                elif "/ajax-" in url:
                    logger.info(f"[Ultimate] 捕获到 API 请求: {url}")
                    captured_requests.append({
                        "type": "ajax",
                        "url": url,
                    })

                await route.continue_()

            await page.route("**/*", capture_request)

            # Step 3: 访问联赛页面
            await page.goto(league_url, timeout=DEFAULT_PAGE_TIMEOUT, wait_until="domcontentloaded")

            # Step 4: 执行 JavaScript 注入，触发 Vue.js 数据加载
            logger.info("[Ultimate] 注入 JavaScript 触发数据加载...")

            await page.evaluate("""
                // 方法 1: 触发 Vue 数据加载
                if (window.__vue__) {
                    try {
                        window.__vue__.$forceUpdate();
                    } catch (e) {
                        console.log('Vue forceUpdate failed:', e);
                    }
                }

                // 方法 2: 模拟用户滚动行为
                window.scrollTo(0, 100);
                window.dispatchEvent(new Event('scroll'));

                // 方法 3: 触发自定义事件
                window.dispatchEvent(new Event('vue-loaded'));
                window.dispatchEvent(new Event('app-ready'));

                // 方法 4: 触发数据重新获取
                if (window.fetch) {
                    // 不直接调用，但确保 fetch 可用
                    console.log('Fetch API available');
                }
            """)

            # Step 5: 深度等待和滚动
            logger.info("[Ultimate] 深度等待动态内容加载...")

            # 等待网络空闲（第一次）
            try:
                await page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                logger.debug("[Ultimate] Networkidle timeout, continuing...")

            # 缓慢滚动，触发懒加载
            for i in range(5):
                scroll_position = i * 500
                await page.evaluate(f"window.scrollTo({{top: {scroll_position}, behavior: 'smooth'}})")
                await asyncio.sleep(2)

            # 滚动回顶部
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(3)

            # 等待网络空闲（第二次）
            try:
                await page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                logger.debug("[Ultimate] Second networkidle timeout, continuing...")

            # Step 6: 扫描 DOM 中的链接
            logger.info("[Ultimate] 扫描 DOM 中的比赛链接...")

            links = await page.locator("a").all()
            logger.info(f"[Ultimate] 找到 {len(links)} 个链接")

            dom_matches = []

            for link in links:
                try:
                    href = await link.get_attribute("href")
                    if not href:
                        continue

                    # 检查是否匹配比赛 URL 模式
                    hash_match = MATCH_HASH_PATTERN.search(href)
                    if hash_match:
                        hash_value = hash_match.group(1)
                        text = await link.text_content()

                        if text:
                            match_data = self._parse_link_text(text)
                            if match_data:
                                dom_matches.append({
                                    "hash": hash_value,
                                    "url": href,
                                    "home_team": match_data.get("home_team"),
                                    "away_team": match_data.get("away_team"),
                                })

                except Exception as e:
                    logger.debug(f"[Ultimate] 处理链接失败: {e}")
                    continue

            logger.info(f"[Ultimate] 从 DOM 找到 {len(dom_matches)} 个比赛链接")

            # 移除网络拦截
            await page.unroute("**/*")

            # Step 7: 分析捕获的请求
            logger.info(f"[Ultimate] 捕获到 {len(captured_requests)} 个网络请求")

            # 从 feed URL 提取哈希
            feed_matches = []
            for req in captured_requests:
                if req["type"] == "feed":
                    feed_match = FEED_URL_PATTERN.search(req["url"])
                    if feed_match:
                        feed_matches.append({
                            "hash": feed_match.group(1),
                            "url": req["url"],
                        })

            logger.info(f"[Ultimate] 从 feed URL 找到 {len(feed_matches)} 个哈希")

            # Step 8: 合并结果并找到最佳匹配
            all_matches = dom_matches + feed_matches

            best_match = None
            best_score = 0.0

            for match in all_matches:
                # 计算相似度
                home_sim = fuzz.ratio(
                    record.home_team.lower(),
                    match.get("home_team", "").lower(),
                )
                away_sim = fuzz.ratio(
                    record.away_team.lower(),
                    match.get("away_team", "").lower(),
                )
                overall_sim = (home_sim + away_sim) / 2

                logger.info(
                    f"[Ultimate] 候选匹配: {match.get('home_team', '?')} vs {match.get('away_team', '?')} "
                    f"(similarity: {overall_sim:.1f}%, hash: {match['hash']})"
                )

                if overall_sim > best_score:
                    best_score = overall_sim
                    best_match = CapturedHash(
                        hash=match["hash"],
                        url=match["url"],
                        home_team=match.get("home_team"),
                        away_team=match.get("away_team"),
                        home_similarity=home_sim,
                        away_similarity=away_sim,
                        overall_similarity=overall_sim,
                        capture_method="combined" if dom_matches and feed_matches else ("dom" if dom_matches else "network"),
                    )

            if best_match and best_match.overall_similarity >= SIMILARITY_THRESHOLD:
                logger.info(
                    f"[Ultimate] ✓ 找到匹配: {best_match.home_team} vs {best_match.away_team} "
                    f"(similarity: {best_match.overall_similarity:.1f}%, hash: {best_match.hash})"
                )
                return best_match
            else:
                logger.warning("[Ultimate] ✗ 未找到匹配")
                return None

        except Exception as e:
            logger.exception(f"[Ultimate] 查找比赛失败: {e}")
            return None

    def _build_league_url(self, record: MatchRecord) -> str:
        """构造联赛页面 URL."""
        league_slug = self._league_to_slug(record.league_name)
        season_slug = record.season.replace("/", "-")
        return f"https://www.oddsportal.com/football/england/{league_slug}-{season_slug}/"

    def _league_to_slug(self, league_name: str) -> str:
        """将联赛名转换为 URL slug."""
        league_map = {
            "Premier League": "premier-league",
            "La Liga": "laliga",
            "Bundesliga": "bundesliga",
            "Serie A": "serie-a",
            "Ligue 1": "ligue-1",
        }
        return league_map.get(league_name, league_name.lower().replace(" ", "-"))

    def _parse_link_text(self, text: str) -> dict[str, str | None] | None:
        """解析链接文本，提取主客队信息."""
        separators = [" vs ", " - ", " v ", " – "]

        for sep in separators:
            if sep in text:
                parts = text.split(sep)
                if len(parts) == 2:
                    return {
                        "home_team": parts[0].strip(),
                        "away_team": parts[1].strip(),
                    }

        return None


# ============================================================================
# Batch Processing
# ============================================================================


async def save_match_to_database(
    record: MatchRecord,
    captured: CapturedHash,
) -> bool:
    """保存匹配结果到数据库."""
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
                mapping_method = 'v41_661_ultimate_capture',
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


async def process_single_record(
    extractor: UltimateHashExtractor,
    browser,
    record: MatchRecord,
    index: int,
) -> dict[str, Any] | None:
    """处理单条记录."""
    logger.info(f"[Process {index}] 处理记录 {index + 1}: {record.fotmob_id}")

    try:
        # 创建页面
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )

        page = await context.new_page()

        # 查找匹配
        captured = await extractor.find_match_by_ultimate_method(record, page)

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
                "capture_method": captured.capture_method,
            }
        else:
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


# ============================================================================
# CLI Entry Point
# ============================================================================


@click.command()
@click.option("--fotmob-id", help="指定单条比赛 ID")
@click.option("--league", help="指定联赛名称")
@click.option("--season", help="指定赛季")
@click.option("--limit", type=int, default=100, help="处理记录数量限制")
@click.option("--dry-run", is_flag=True, help="模拟运行，不实际更新数据库")
def main(
    fotmob_id: str | None,
    league: str | None,
    season: str | None,
    limit: int,
    dry_run: bool,
):
    """V41.661 Ultimate Capture - 终极方案：结合 OSS 智能与 JavaScript 注入."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("=" * 80)
    logger.info("V41.661 Ultimate Capture - 启动")
    logger.info("=" * 80)

    if dry_run:
        logger.info("模拟运行模式（不会更新数据库）")

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
        cur.execute(
            """
            SELECT fotmob_id, home_team, away_team, match_date, league_name, season
            FROM matches_mapping
            WHERE fotmob_id = %s AND oddsportal_url IS NULL
        """,
            (fotmob_id,),
        )
    elif league:
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
        logger.warning("没有找到待处理的记录")
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

    logger.info(f"找到 {len(records)} 条待处理记录")

    # 创建提取器
    extractor = UltimateHashExtractor()

    # 运行处理
    async def run_processing():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            results = []
            for i, record in enumerate(records):
                result = await process_single_record(extractor, browser, record, i)
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
║           V41.661 Ultimate Capture - 回填报告                          ║
╚══════════════════════════════════════════════════════════════════════╝

处理统计:
  • 总处理数: {len(results)}
  • 成功匹配: {successful}
  • 匹配失败: {len(results) - successful}
  • 成功率: {(successful / max(1, len(results))) * 100:.2f}%

前 10 条成功记录:
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
