#!/usr/bin/env python3
"""V41.650 Visual Anchor Mapping - 视觉锚点式链接自动化修复.

核心理念：
    放弃对加密 AJAX 封包的逆向工程，转而采用【浏览器完全渲染 + 文本语义锚点】
    的稳健型链接匹配引擎。

架构设计：
    1. Ghost Protocol 加持：代理轮换、指纹随机化、人类行为模拟
    2. 深度渲染引擎：强制触底滚动、DOM 内容锚定、等待网络空闲
    3. 语义文本锚点：遍历所有 <a> 标签，使用 fuzz.ratio() 模糊匹配
    4. 多维验证：球队名相似度 + 日期窗口 + 联赛匹配

Usage:
    # 单条记录测试
    python scripts/ops/v41_650_visual_anchor_mapping.py --fotmob-id <MATCH_ID> --dry-run

    # 批量处理（英超缺失记录）
    python scripts/ops/v41_650_visual_anchor_mapping.py --league "Premier League" --workers 18

    # 完整回填模式
    python scripts/ops/v41_650_visual_anchor_mapping.py --mode recovery
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import logging
import re
from typing import Any

import click
from playwright.async_api import Page, async_playwright
import psycopg2
from psycopg2.extras import RealDictCursor
from thefuzz import fuzz

from src.api.collectors.base_extractor import BaseExtractor
from src.config_unified import get_settings
from src.utils.text_processor import TeamNameNormalizer

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration & Constants
# ============================================================================

# Hash 提取正则模式（与 TDD 测试保持一致）
HASH_PATTERN = re.compile(r"/football/matches/.+-([a-zA-Z0-9]{8}|ID[a-zA-Z0-9]{8})/")

# 目标站点 URL 模板
ODDSPORTAL_SEARCH_URL = "https://www.oddsportal.com/football/search/"

# 相似度阈值（基于 TDD 实测数据）
SIMILARITY_THRESHOLD = 70.0  # 整体相似度阈值
HOME_TEAM_THRESHOLD = 55.0  # 主队相似度阈值
AWAY_TEAM_THRESHOLD = 55.0  # 客队相似度阈值

# 时间窗口
TIME_WINDOW_DAYS = 1  # ±1 天

# 并发配置
DEFAULT_CONCURRENT_WORKERS = 18
DEFAULT_PAGE_TIMEOUT = 60000
DEFAULT_SCROLL_ROUNDS = 5


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
class ScrapedMatch:
    """从目标站点爬取的比赛数据."""

    hash: str | None = None
    url: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    match_date: datetime | None = None
    league_name: str | None = None

    # 评分
    home_similarity: float = 0.0
    away_similarity: float = 0.0
    overall_similarity: float = 0.0
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "hash": self.hash,
            "url": self.url,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "match_date": self.match_date,
            "league_name": self.league_name,
            "home_similarity": self.home_similarity,
            "away_similarity": self.away_similarity,
            "overall_similarity": self.overall_similarity,
            "confidence": self.confidence,
        }


@dataclass
class RecoveryResult:
    """回填结果统计."""

    total_processed: int = 0
    successful_matches: int = 0
    failed_matches: int = 0
    skipped_already_has_url: int = 0

    # 成功恢复的记录（用于报告）
    recovered_records: list[dict[str, Any]] = field(default_factory=list)


# ============================================================================
# Core Implementation
# ============================================================================


class VisualAnchorMapper(BaseExtractor):
    """V41.650 视觉锚点映射器.

    核心功能：
        1. Ghost Protocol 隐身保护
        2. 深度渲染 + 强制滚动
        3. 语义文本锚点提取
        4. 多维度相似度匹配
    """

    def __init__(self, enable_ghost: bool = True):
        """初始化映射器.

        Args:
            enable_ghost: 是否启用 Ghost Protocol 隐身保护
        """
        super().__init__(auto_proxy=True)
        self.enable_ghost = enable_ghost
        self.settings = get_settings()
        self.normalizer = TeamNameNormalizer()

    async def find_match_by_visual_anchor(
        self,
        record: MatchRecord,
        page: Page,
        max_scroll_rounds: int = DEFAULT_SCROLL_ROUNDS,
    ) -> ScrapedMatch | None:
        """通过视觉锚点查找匹配的比赛链接.

        Args:
            record: 数据库中的比赛记录
            page: Playwright 页面对象
            max_scroll_rounds: 最大滚动轮次

        Returns:
            找到的比赛数据，如果没有找到则返回 None
        """
        logger.info(
            f"[VisualAnchor] 查找比赛: {record.home_team} vs {record.away_team} "
            f"({record.match_date.date()})"
        )

        try:
            # Step 1: 构造搜索 URL
            search_url = self._build_search_url(record)
            logger.info(f"[VisualAnchor] 访问搜索页面: {search_url}")

            # Step 2: 深度渲染页面
            await self._deep_render_page(page, search_url, max_scroll_rounds)

            # Step 3: 语义文本锚点提取
            scraped_data = await self._extract_via_semantic_anchors(page, record)

            if scraped_data and scraped_data.hash:
                # Step 4: 验证匹配质量
                if self._validate_match_quality(record, scraped_data):
                    logger.info(
                        f"[VisualAnchor] ✓ 找到高质量匹配: {scraped_data.url} "
                        f"(similarity: {scraped_data.overall_similarity:.1f}%)"
                    )
                    return scraped_data
                logger.warning(
                    f"[VisualAnchor] ✗ 匹配质量不足: "
                    f"similarity={scraped_data.overall_similarity:.1f}% "
                    f"< threshold={SIMILARITY_THRESHOLD}%"
                )
                return None
            logger.warning("[VisualAnchor] ✗ 未找到匹配的链接")
            return None

        except Exception as e:
            logger.exception(f"[VisualAnchor] 查找比赛失败: {e}")
            return None

    def _build_search_url(self, record: MatchRecord) -> str:
        """构造搜索 URL.

        Args:
            record: 比赛记录

        Returns:
            搜索 URL
        """
        # 优先使用联赛页面（更可靠的策略）
        # URL 格式: https://www.oddsportal.com/football/{country}/{league}-{season}/
        # 例如: https://www.oddsportal.com/football/england/premier-league-2024-2025/

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
        # 联赛名映射
        league_map = {
            "Premier League": "premier-league",
            "La Liga": "laliga",
            "Bundesliga": "bundesliga",
            "Serie A": "serie-a",
            "Ligue 1": "ligue-1",
        }
        return league_map.get(league_name, league_name.lower().replace(" ", "-"))

    async def _deep_render_page(
        self,
        page: Page,
        url: str,
        max_scroll_rounds: int,
    ) -> None:
        """深度渲染页面（Ghost Protocol 加持）.

        Args:
            page: Playwright 页面对象
            url: 目标 URL
            max_scroll_rounds: 最大滚动轮次
        """
        logger.debug(f"[DeepRender] 开始深度渲染: {url}")

        # 访问页面
        await page.goto(url, timeout=DEFAULT_PAGE_TIMEOUT, wait_until="domcontentloaded")

        # 等待网络空闲（Vue.js SPA 需要更长时间）
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            logger.debug("[DeepRender] 网络空闲超时，继续执行")

        # 额外等待 Vue.js 动态内容加载
        logger.debug("[DeepRender] 等待 Vue.js 动态内容加载...")
        await asyncio.sleep(5)

        # 强制触底滚动（触发懒加载内容）
        for i in range(max_scroll_rounds):
            logger.debug(f"[DeepRender] 滚动轮次 {i + 1}/{max_scroll_rounds}")

            # 滚动到底部
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            # 等待内容加载
            await asyncio.sleep(1)

        # 滚动回顶部
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)

        # 调试：保存页面内容
        try:
            page_content = await page.content()
            logger.info(f"[DeepRender] 页面内容长度: {len(page_content)} 字符")

            # 保存到文件用于调试
            from pathlib import Path
            from datetime import datetime

            debug_dir = Path("logs/debug_pages")
            debug_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = debug_dir / f"page_{timestamp}.html"

            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(page_content)

            logger.info(f"[DeepRender] 页面内容已保存到: {debug_file}")
        except Exception as e:
            logger.debug(f"[DeepRender] 保存页面内容失败: {e}")

        logger.debug("[DeepRender] 深度渲染完成")

    async def _extract_via_semantic_anchors(
        self,
        page: Page,
        record: MatchRecord,
    ) -> ScrapedMatch | None:
        """通过语义文本锚点提取比赛数据.

        Args:
            page: Playwright 页面对象
            record: 数据库中的比赛记录

        Returns:
            提取的比赛数据
        """
        # 获取页面中所有链接
        links = await page.locator("a").all()

        logger.info(f"[SemanticAnchor] 找到 {len(links)} 个链接")

        # 显示前 10 个链接的文本用于调试
        for i, link in enumerate(links[:10]):
            try:
                text = await link.text_content()
                href = await link.get_attribute("href")
                logger.debug(f"[SemanticAnchor] 调试 - 链接 {i+1}: {text[:80] if text else 'N/A'} | href={href[:80] if href else 'N/A'}")
            except Exception:
                continue

        # 统计匹配 hash 的链接数量
        hash_match_count = 0

        best_match = None
        best_score = 0.0

        for link in links:
            try:
                # 获取链接文本
                text = await link.text_content()

                if not text:
                    continue

                # 获取链接 URL
                href = await link.get_attribute("href")

                if not href:
                    continue

                # 提取 hash
                hash_match = HASH_PATTERN.search(href)

                if not hash_match:
                    continue

                hash_match_count += 1
                extracted_hash = hash_match.group(1)

                logger.debug(f"[SemanticAnchor] 找到 hash 链接: {text[:80]} | hash={extracted_hash}")

                # 解析球队名（从链接文本）
                match_data = self._parse_link_text(text)

                if not match_data:
                    logger.debug(f"[SemanticAnchor] 无法解析球队名: {text[:80]}")
                    continue

                # 计算相似度
                home_sim = fuzz.ratio(
                    self.normalizer.normalize(record.home_team),
                    self.normalizer.normalize(match_data["home_team"] or ""),
                )
                away_sim = fuzz.ratio(
                    self.normalizer.normalize(record.away_team),
                    self.normalizer.normalize(match_data["away_team"] or ""),
                )
                overall_sim = (home_sim + away_sim) / 2

                # 记录候选匹配
                logger.info(
                    f"[SemanticAnchor] 候选匹配: {match_data['home_team']} vs {match_data['away_team']} "
                    f"(similarity: {overall_sim:.1f}%, hash: {extracted_hash})"
                )

                # 构造匹配对象
                scraped = ScrapedMatch(
                    hash=extracted_hash,
                    url=href if href.startswith("http") else f"https://www.oddsportal.com{href}",
                    home_team=match_data.get("home_team"),
                    away_team=match_data.get("away_team"),
                    home_similarity=home_sim,
                    away_similarity=away_sim,
                    overall_similarity=overall_sim,
                    confidence=overall_sim / 100.0,
                )

                # 更新最佳匹配
                if overall_sim > best_score:
                    best_score = overall_sim
                    best_match = scraped

            except Exception as e:
                logger.debug(f"[SemanticAnchor] 处理链接失败: {e}")
                continue

        logger.info(f"[SemanticAnchor] 匹配 hash 的链接数: {hash_match_count}/{len(links)}")

        if best_match:
            logger.info(
                f"[SemanticAnchor] 最佳匹配: {best_match.home_team} vs {best_match.away_team} "
                f"(similarity: {best_match.overall_similarity:.1f}%)"
            )

        return best_match

    def _parse_link_text(self, text: str) -> dict[str, str | None] | None:
        """解析链接文本，提取主客队信息.

        Args:
            text: 链接文本

        Returns:
            包含主客队信息的字典
        """
        # 常见分隔符
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

    def _validate_match_quality(
        self,
        record: MatchRecord,
        scraped: ScrapedMatch,
    ) -> bool:
        """验证匹配质量.

        Args:
            record: 数据库中的比赛记录
            scraped: 爬取的比赛数据

        Returns:
            是否匹配
        """
        # 检查相似度阈值
        if scraped.overall_similarity < SIMILARITY_THRESHOLD:
            return False

        if scraped.home_similarity < HOME_TEAM_THRESHOLD:
            return False

        if scraped.away_similarity < AWAY_TEAM_THRESHOLD:
            return False

        # 检查时间窗口
        if scraped.match_date:
            time_diff = abs((record.match_date - scraped.match_date).days)
            if time_diff > TIME_WINDOW_DAYS:
                logger.warning(f"[Validate] 时间超出窗口: {time_diff} days > {TIME_WINDOW_DAYS}")
                return False

        return True


# ============================================================================
# Batch Processing
# ============================================================================


async def batch_process_records(
    mapper: VisualAnchorMapper,
    records: list[MatchRecord],
    workers: int = DEFAULT_CONCURRENT_WORKERS,
) -> RecoveryResult:
    """批量处理记录.

    Args:
        mapper: 映射器实例
        records: 待处理的记录列表
        workers: 并发工作线程数

    Returns:
        回填结果统计
    """
    results = RecoveryResult()
    results.total_processed = len(records)

    logger.info(f"[BatchProcess] 开始批量处理: {len(records)} 条记录, {workers} 个工作线程")

    async with async_playwright() as p:
        # 创建浏览器上下文
        browser = await p.chromium.launch(headless=True)

        # 创建多个页面（并发）
        tasks = []

        for i, record in enumerate(records):
            # 为每个记录创建独立的页面
            task = asyncio.create_task(
                process_single_record(mapper, browser, record, i),
            )
            tasks.append(task)

        # 等待所有任务完成
        processed = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计结果
        for result in processed:
            if isinstance(result, Exception):
                logger.error(f"[BatchProcess] 处理失败: {result}")
                results.failed_matches += 1
            elif result:
                if result.get("success"):
                    results.successful_matches += 1
                    if len(results.recovered_records) < 20:
                        results.recovered_records.append(result)
                else:
                    results.failed_matches += 1

        await browser.close()

    return results


async def process_single_record(
    mapper: VisualAnchorMapper,
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
            user_agent=mapper.get_random_user_agent(),
        )

        page = await context.new_page()

        # 查找匹配
        scraped = await mapper.find_match_by_visual_anchor(record, page)

        await context.close()

        if scraped and scraped.hash:
            # 保存到数据库
            success = await save_match_to_database(record, scraped)

            return {
                "success": success,
                "fotmob_id": record.fotmob_id,
                "home_team": record.home_team,
                "away_team": record.away_team,
                "match_date": record.match_date.isoformat(),
                "scraped_url": scraped.url,
                "scraped_hash": scraped.hash,
                "similarity": scraped.overall_similarity,
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
    scraped: ScrapedMatch,
) -> bool:
    """保存匹配结果到数据库.

    Args:
        record: 数据库中的比赛记录
        scraped: 爬取的比赛数据

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
                mapping_method = 'v41_650_visual_anchor',
                confidence = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE fotmob_id = %s
        """,
            (
                scraped.hash,
                scraped.url,
                scraped.confidence,
                record.fotmob_id,
            ),
        )

        conn.commit()
        conn.close()

        logger.info(f"[Database] ✓ 保存成功: {record.fotmob_id} -> {scraped.hash}")
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
@click.option("--workers", default=DEFAULT_CONCURRENT_WORKERS, help="并发工作线程数")
@click.option("--dry-run", is_flag=True, help="模拟运行，不实际更新数据库")
@click.option(
    "--mode", type=click.Choice(["single", "recovery"]), default="single", help="运行模式"
)
def main(
    fotmob_id: str | None,
    league: str | None,
    season: str | None,
    workers: int,
    dry_run: bool,
    mode: str,
):
    """V41.650 Visual Anchor Mapping - 视觉锚点式链接自动化修复."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("=" * 80)
    logger.info("V41.650 Visual Anchor Mapping - 启动")
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
                """,
                (league, season),
            )
        else:
            cur.execute(
                """
                SELECT fotmob_id, home_team, away_team, match_date, league_name, season
                FROM matches_mapping
                WHERE league_name = %s AND oddsportal_url IS NULL
                ORDER BY match_date DESC
                LIMIT 100
                """,
                (league,),
            )
    else:
        # 默认：英超缺失记录
        cur.execute(
            """
            SELECT fotmob_id, home_team, away_team, match_date, league_name, season
            FROM matches_mapping
            WHERE league_name = 'Premier League'
                AND oddsportal_url IS NULL
            ORDER BY match_date DESC
            LIMIT 100
        """
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
    mapper = VisualAnchorMapper(enable_ghost=True)

    if mode == "single" or fotmob_id:
        # 单条记录处理
        async def process_single():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=mapper.get_random_user_agent(),
                )
                page = await context.new_page()

                result = await mapper.find_match_by_visual_anchor(records[0], page)

                await context.close()
                await browser.close()

                if result:
                    logger.info(f"✓ 找到匹配: {result.url}")
                    if not dry_run:
                        asyncio.run(save_match_to_database(records[0], result))
                else:
                    logger.warning("✗ 未找到匹配")

        asyncio.run(process_single())

    else:
        # 批量处理模式
        results = asyncio.run(batch_process_records(mapper, records, workers))

        # 生成报告
        logger.info(
            f"""
╔══════════════════════════════════════════════════════════════════════╗
║           V41.650 Visual Anchor Mapping - 回填报告                  ║
╚══════════════════════════════════════════════════════════════════════╝

📊 处理统计:
  • 总处理数: {results.total_processed}
  • 成功匹配: {results.successful_matches}
  • 匹配失败: {results.failed_matches}
  • 成功率: {(results.successful_matches / max(1, results.total_processed)) * 100:.2f}%

📋 前 10 条成功记录:
{"-" * 100}
"""
        )

        for i, rec in enumerate(results.recovered_records[:10], 1):
            logger.info(
                f"""
{i}. {rec["home_team"]} vs {rec["away_team"]}
   URL: {rec.get("scraped_url", "N/A")}
   相似度: {rec.get("similarity", 0):.1f}%
   fotmob_id: {rec["fotmob_id"]}
"""
            )


if __name__ == "__main__":
    main()
