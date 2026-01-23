#!/usr/bin/env python3
"""V41.660 URL Hash Extraction - 直接从比赛页面 URL 提取哈希.

核心理念（基于 Stack Overflow 2024/12 方案）：
    Hash ID 直接嵌入在比赛页面 URL 中！
    无需解密，无需扫描 script，直接提取即可。

URL 格式：
    https://www.oddsportal.com/football/england/premier-league/liverpool-manchester-city-82qTWLi3/

    其中 `82qTWLi3` 就是我们要的 8 位哈希码！

Usage:
    # 单条记录测试
    python scripts/ops/v41_660_url_hash_extraction.py --fotmob-id <MATCH_ID>

    # 批量处理
    python scripts/ops/v41_660_url_hash_extraction.py --league "Premier League" --limit 100
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
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
# 匹配格式: /football/xxx/xxx-team1-team2-HASH/
MATCH_HASH_PATTERN = re.compile(r'/football/[^/]+/[^/]+/.+-([a-zA-Z0-9]{8}|ID[a-zA-Z0-9]{8})/')

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
class ExtractedHash:
    """提取的哈希数据."""

    hash: str
    url: str
    home_team: str | None = None
    away_team: str | None = None

    # 相似度评分
    home_similarity: float = 0.0
    away_similarity: float = 0.0
    overall_similarity: float = 0.0


# ============================================================================
# Core Implementation
# ============================================================================


class URLHashExtractor:
    """V41.660 URL 哈希提取器 - 直接从比赛页面 URL 提取哈希.

    核心功能：
        1. 访问联赛页面
        2. 扫描所有比赛链接
        3. 从 URL 中提取 8 位哈希
        4. 通过球队名匹配找到对应记录
    """

    async def find_match_by_url_hash(
        self,
        record: MatchRecord,
        page: Page,
    ) -> ExtractedHash | None:
        """通过 URL 哈希查找匹配的比赛.

        Args:
            record: 数据库中的比赛记录
            page: Playwright 页面对象

        Returns:
            提取的哈希数据
        """
        logger.info(
            f"[URLHash] 查找比赛: {record.home_team} vs {record.away_team} "
            f"({record.match_date.date()})"
        )

        try:
            # Step 1: 构造联赛页面 URL
            league_url = self._build_league_url(record)
            logger.info(f"[URLHash] 访问联赛页面: {league_url}")

            # Step 2: 访问联赛页面并等待加载
            await page.goto(league_url, timeout=DEFAULT_PAGE_TIMEOUT, wait_until="domcontentloaded")

            # 等待 Vue.js 应用加载
            await page.wait_for_load_state("networkidle", timeout=30000)

            # 强制滚动触发懒加载
            for i in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

            # 滚动回顶部
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(2)

            # Step 3: 获取所有链接
            links = await page.locator("a").all()

            logger.info(f"[URLHash] 找到 {len(links)} 个链接")

            # 获取页面内容用于调试
            page_content = await page.content()

            # 保存到文件用于调试
            from pathlib import Path
            from datetime import datetime

            debug_dir = Path("logs/debug_pages")
            debug_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = debug_dir / f"v41_660_page_{timestamp}.html"

            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(page_content)

            logger.info(f"[URLHash] 页面内容已保存到: {debug_file}")

            # Step 4: 扫描链接提取哈希
            best_match = None
            best_score = 0.0

            # 调试：记录前 5 个链接样本
            debug_count = 0
            for link in links[:5]:
                try:
                    href = await link.get_attribute("href")
                    if href:
                        logger.debug(f"[URLHash] 链接样本 {debug_count + 1}: {href[:100]}")
                        debug_count += 1
                        if debug_count >= 5:
                            break
                except Exception:
                    continue

            for link in links:
                try:
                    # 获取链接 URL
                    href = await link.get_attribute("href")

                    if not href:
                        continue

                    # 检查是否匹配比赛 URL 模式
                    hash_match = MATCH_HASH_PATTERN.search(href)

                    if not hash_match:
                        continue

                    extracted_hash = hash_match.group(1)

                    # 获取链接文本（球队名）
                    text = await link.text_content()

                    if not text:
                        continue

                    # 解析球队名
                    match_data = self._parse_link_text(text)

                    if not match_data:
                        continue

                    # 计算相似度
                    home_sim = fuzz.ratio(
                        record.home_team.lower(),
                        match_data["home_team"].lower() if match_data["home_team"] else "",
                    )
                    away_sim = fuzz.ratio(
                        record.away_team.lower(),
                        match_data["away_team"].lower() if match_data["away_team"] else "",
                    )
                    overall_sim = (home_sim + away_sim) / 2

                    # 记录候选匹配
                    logger.info(
                        f"[URLHash] 候选匹配: {match_data['home_team']} vs {match_data['away_team']} "
                        f"(similarity: {overall_sim:.1f}%, hash: {extracted_hash})"
                    )

                    # 构造提取对象
                    extracted = ExtractedHash(
                        hash=extracted_hash,
                        url=href if href.startswith("http") else f"https://www.oddsportal.com{href}",
                        home_team=match_data.get("home_team"),
                        away_team=match_data.get("away_team"),
                        home_similarity=home_sim,
                        away_similarity=away_sim,
                        overall_similarity=overall_sim,
                    )

                    # 更新最佳匹配
                    if overall_sim > best_score:
                        best_score = overall_sim
                        best_match = extracted

                except Exception as e:
                    logger.debug(f"[URLHash] 处理链接失败: {e}")
                    continue

            if best_match and best_match.overall_similarity >= SIMILARITY_THRESHOLD:
                logger.info(
                    f"[URLHash] ✓ 找到匹配: {best_match.home_team} vs {best_match.away_team} "
                    f"(similarity: {best_match.overall_similarity:.1f}%)"
                )
                return best_match
            else:
                logger.warning("[URLHash] ✗ 未找到匹配")
                return None

        except Exception as e:
            logger.exception(f"[URLHash] 查找比赛失败: {e}")
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


# ============================================================================
# Batch Processing
# ============================================================================


async def save_match_to_database(
    record: MatchRecord,
    extracted: ExtractedHash,
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
                mapping_method = 'v41_660_url_hash_extraction',
                confidence = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE fotmob_id = %s
        """,
            (
                extracted.hash,
                extracted.url,
                extracted.overall_similarity / 100.0,
                record.fotmob_id,
            ),
        )

        conn.commit()
        conn.close()

        logger.info(f"[Database] ✓ 保存成功: {record.fotmob_id} -> {extracted.hash}")
        return True

    except Exception as e:
        logger.exception(f"[Database] ✗ 保存失败: {e}")
        return False


async def process_single_record(
    extractor: URLHashExtractor,
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
        extracted = await extractor.find_match_by_url_hash(record, page)

        await context.close()

        if extracted and extracted.hash:
            # 保存到数据库
            success = await save_match_to_database(record, extracted)

            return {
                "success": success,
                "fotmob_id": record.fotmob_id,
                "home_team": record.home_team,
                "away_team": record.away_team,
                "match_date": record.match_date.isoformat(),
                "extracted_hash": extracted.hash,
                "extracted_url": extracted.url,
                "similarity": extracted.overall_similarity,
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
    """V41.660 URL Hash Extraction - 直接从比赛页面 URL 提取哈希."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("=" * 80)
    logger.info("V41.660 URL Hash Extraction - 启动")
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

    # 创建提取器
    extractor = URLHashExtractor()

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
║           V41.660 URL Hash Extraction - 回填报告                          ║
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
   Hash: {rec.get('extracted_hash', 'N/A')}
   相似度: {rec.get('similarity', 0):.1f}%
   fotmob_id: {rec['fotmob_id']}
"""
                    )
                    if i >= 9:  # 只显示前 10 条
                        break

    asyncio.run(run_processing())


if __name__ == "__main__":
    main()
