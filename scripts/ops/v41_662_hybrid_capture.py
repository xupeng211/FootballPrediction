#!/usr/bin/env python3
"""V41.662 Hybrid Capture - 混合方案：结合 V41.650 和 OSS 智能.

核心理念：
    鉴于 OddsPortal 使用复杂的加密和 Vue.js SPA 架构，采用混合策略：
    1. 优先使用 V41.650 视觉匹配的已验证结果
    2. 备用方案：深度 DOM 等待 + JavaScript 注入
    3. 最终回退：球队名模糊匹配 + 历史数据关联

关键突破：
    - 发现 ajax-all-events API 返回加密数据
    - 加密方案可能随 app.js 更新而变化
    - 混合策略最大化成功率

Usage:
    # 批量处理英超缺失记录
    python scripts/ops/v41_662_hybrid_capture.py --league "Premier League" --limit 100

    # 使用已验证的 V41.650 结果
    python scripts/ops/v41_662_hybrid_capture.py --mode use-v650-results
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
import logging
import re
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

# Hash 提取正则模式
MATCH_HASH_PATTERN = re.compile(r"/football/[^/]+/[^/]+/.+-([a-zA-Z0-9]{8}|ID[a-zA-Z0-9]{8})/")

# 相似度阈值
SIMILARITY_THRESHOLD = 70.0

DEFAULT_PAGE_TIMEOUT = 90000  # 增加到 90 秒


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
class HybridCapturedHash:
    """混合捕获的哈希数据."""

    hash: str
    url: str
    home_team: str | None = None
    away_team: str | None = None
    overall_similarity: float = 0.0
    capture_method: str = "hybrid"  # 'v650', 'dom', 'fuzzy'


# ============================================================================
# Core Implementation
# ============================================================================


class HybridHashExtractor:
    """V41.662 混合哈希提取器.

    策略优先级：
        1. 检查 V41.650 视觉匹配的已有结果
        2. 深度 DOM 等待 + JavaScript 注入
        3. 球队名模糊匹配
    """

    def __init__(self):
        self.v650_results = {}  # 缓存 V41.650 结果

    async def load_v650_results(self):
        """加载现有的所有已验证结果作为训练数据."""
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

            # 获取所有方法的结果作为训练数据
            cur.execute(
                """
                SELECT
                    m.home_team,
                    m.away_team,
                    m.match_date,
                    m.league_name,
                    mm.oddsportal_hash,
                    mm.oddsportal_url,
                    mm.mapping_method
                FROM matches_mapping mm
                JOIN matches m ON mm.fotmob_id = m.match_id
                WHERE mm.oddsportal_hash IS NOT NULL
                """
            )

            rows = cur.fetchall()
            conn.close()

            # 构建缓存：key = (home_team, away_team, date), value = (hash, url, method)
            for row in rows:
                key = (
                    row["home_team"],
                    row["away_team"],
                    row["match_date"].date(),
                )
                self.v650_results[key] = {
                    "hash": row["oddsportal_hash"],
                    "url": row["oddsportal_url"],
                    "method": row["mapping_method"],
                    "league": row["league_name"],
                }

            logger.info(f"[Hybrid] 加载了 {len(self.v650_results)} 条历史结果作为训练数据")

            # 按方法统计
            method_counts = {}
            for v in self.v650_results.values():
                method_counts[v["method"]] = method_counts.get(v["method"], 0) + 1

            logger.info(f"[Hybrid] 方法分布: {method_counts}")

        except Exception as e:
            logger.exception(f"[Hybrid] 加载历史结果失败: {e}")

    async def find_match_by_hybrid_method(
        self,
        record: MatchRecord,
        page: Page,
    ) -> HybridCapturedHash | None:
        """通过混合方案查找匹配的比赛.

        Args:
            record: 数据库中的比赛记录
            page: Playwright 页面对象

        Returns:
            捕获的哈希数据
        """
        logger.info(
            f"[Hybrid] 查找比赛: {record.home_team} vs {record.away_team} "
            f"({record.match_date.date()})"
        )

        # 策略 1: 检查历史结果缓存（仅限相同日期）
        cache_key = (record.home_team, record.away_team, record.match_date.date())
        if cache_key in self.v650_results:
            cached = self.v650_results[cache_key]
            logger.info(f"[Hybrid] ✓ 从历史缓存找到匹配 (方法: {cached['method']}, 日期: {record.match_date.date()})")
            return HybridCapturedHash(
                hash=cached["hash"],
                url=cached["url"],
                home_team=record.home_team,
                away_team=record.away_team,
                overall_similarity=100.0,
                capture_method=f"legacy_{cached['method']}",
            )

        # 策略 1.5: 模糊搜索历史缓存（仅限相同日期 ±3 天）
        fuzzy_match = self._fuzzy_search_cache(record)
        if fuzzy_match:
            return fuzzy_match

        # 策略 2: 深度 DOM 扫描
        dom_result = await self._try_dom_extraction(record, page)
        if dom_result:
            return dom_result

        # 策略 3: 模糊匹配回退
        return await self._try_fuzzy_match(record, page)

    async def _try_dom_extraction(
        self,
        record: MatchRecord,
        page: Page,
    ) -> HybridCapturedHash | None:
        """尝试从 DOM 提取哈希."""
        try:
            league_url = self._build_league_url(record)
            logger.info(f"[Hybrid] 访问联赛页面: {league_url}")

            await page.goto(league_url, timeout=DEFAULT_PAGE_TIMEOUT, wait_until="domcontentloaded")

            # 深度等待策略
            await self._deep_wait_and_scroll(page)

            # 扫描 DOM
            links = await page.locator("a").all()
            logger.info(f"[Hybrid] 找到 {len(links)} 个链接")

            best_match = None
            best_score = 0.0

            for link in links:
                try:
                    href = await link.get_attribute("href")
                    if not href:
                        continue

                    hash_match = MATCH_HASH_PATTERN.search(href)
                    if not hash_match:
                        continue

                    hash_value = hash_match.group(1)
                    text = await link.text_content()

                    if not text:
                        continue

                    match_data = self._parse_link_text(text)
                    if not match_data:
                        continue

                    # 计算相似度
                    home_sim = fuzz.ratio(
                        record.home_team.lower(),
                        match_data.get("home_team", "").lower(),
                    )
                    away_sim = fuzz.ratio(
                        record.away_team.lower(),
                        match_data.get("away_team", "").lower(),
                    )
                    overall_sim = (home_sim + away_sim) / 2

                    if overall_sim > best_score:
                        best_score = overall_sim
                        best_match = HybridCapturedHash(
                            hash=hash_value,
                            url=href if href.startswith("http") else f"https://www.oddsportal.com{href}",
                            home_team=match_data.get("home_team"),
                            away_team=match_data.get("away_team"),
                            overall_similarity=overall_sim,
                            capture_method="dom",
                        )

                except Exception:
                    continue

            if best_match and best_match.overall_similarity >= SIMILARITY_THRESHOLD:
                logger.info(
                    f"[Hybrid] ✓ DOM 找到匹配: {best_match.home_team} vs {best_match.away_team} "
                    f"(similarity: {best_match.overall_similarity:.1f}%)"
                )
                return best_match

        except Exception as e:
            logger.debug(f"[Hybrid] DOM 提取失败: {e}")

        return None

    async def _try_fuzzy_match(
        self,
        record: MatchRecord,
        page: Page,
    ) -> HybridCapturedHash | None:
        """模糊匹配回退方案."""
        logger.info("[Hybrid] 尝试模糊匹配回退")

        # 这里可以实现更复杂的模糊匹配逻辑
        # 例如：使用历史数据、球队别名等

        return None

    def _fuzzy_search_cache(
        self,
        record: MatchRecord,
    ) -> HybridCapturedHash | None:
        """在历史缓存中进行模糊搜索（仅限相同日期）."""
        logger.info(f"[Hybrid] 在 {len(self.v650_results)} 条历史记录中模糊搜索")

        best_match = None
        best_score = 0.0
        target_date = record.match_date.date()

        for (home_team, away_team, match_date), cached in self.v650_results.items():
            # 只考虑相同日期的记录（允许 ±3 天误差）
            date_diff = abs((target_date - match_date).days)
            if date_diff > 3:
                continue

            # 计算球队名相似度
            home_sim = fuzz.ratio(
                record.home_team.lower(),
                home_team.lower(),
            )
            away_sim = fuzz.ratio(
                record.away_team.lower(),
                away_team.lower(),
            )
            overall_sim = (home_sim + away_sim) / 2

            # 要求至少 85% 相似度才认为是同一比赛
            if overall_sim >= 85.0 and overall_sim > best_score:
                best_score = overall_sim
                best_match = HybridCapturedHash(
                    hash=cached["hash"],
                    url=cached["url"],
                    home_team=home_team,
                    away_team=away_team,
                    overall_similarity=overall_sim,
                    capture_method=f"fuzzy_legacy_{cached['method']}",
                )

        if best_match:
            logger.info(
                f"[Hybrid] ✓ 模糊搜索找到匹配: {best_match.home_team} vs {best_match.away_team} "
                f"(similarity: {best_match.overall_similarity:.1f}%)"
            )
        else:
            logger.info(f"[Hybrid] 未找到相同日期的匹配记录 (目标日期: {target_date})")

        return best_match

    async def _deep_wait_and_scroll(self, page: Page):
        """深度等待和滚动策略."""
        # 等待网络空闲（第一次）
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass

        # JavaScript 注入触发数据加载
        await page.evaluate("""
            // 触发 Vue 更新
            if (window.__vue__) {
                try {
                    window.__vue__.$forceUpdate();
                } catch (e) {}
            }

            // 模拟用户行为
            window.dispatchEvent(new Event('scroll'));
            window.dispatchEvent(new Event('vue-loaded'));
        """)

        # 缓慢滚动触发懒加载
        for i in range(10):
            scroll_position = i * 300
            await page.evaluate(f"window.scrollTo({{top: {scroll_position}, behavior: 'smooth'}})")
            await asyncio.sleep(1)

        # 滚动回顶部
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(3)

        # 再次等待网络空闲
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass

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
    captured: HybridCapturedHash,
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

        # 检查哈希是否已被其他比赛使用
        cur.execute(
            """
            SELECT fotmob_id, home_team, away_team
            FROM matches_mapping
            WHERE oddsportal_hash = %s AND fotmob_id != %s
        """,
            (captured.hash, record.fotmob_id),
        )

        existing = cur.fetchone()

        if existing:
            logger.warning(
                f"[Database] ⚠ 哈希冲突: {captured.hash} 已被 "
                f"{existing['home_team']} vs {existing['away_team']} "
                f"(fotmob_id: {existing['fotmob_id']}) 使用"
            )
            conn.close()
            return False

        # 更新当前记录
        cur.execute(
            """
            UPDATE matches_mapping
            SET oddsportal_hash = %s,
                oddsportal_url = %s,
                mapping_method = 'v41_662_hybrid_capture',
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
    extractor: HybridHashExtractor,
    browser,
    record: MatchRecord,
    index: int,
) -> dict[str, Any] | None:
    """处理单条记录."""
    logger.info(f"[Process {index}] 处理记录 {index + 1}: {record.fotmob_id}")

    try:
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )

        page = await context.new_page()

        captured = await extractor.find_match_by_hybrid_method(record, page)

        await context.close()

        if captured and captured.hash:
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
@click.option("--league", help="指定联赛名称")
@click.option("--season", help="指定赛季")
@click.option("--limit", type=int, default=100, help="处理记录数量限制")
@click.option("--mode", type=click.Choice(["hybrid", "use-v650-results"]), default="hybrid", help="运行模式")
def main(
    league: str | None,
    season: str | None,
    limit: int,
    mode: str,
):
    """V41.662 Hybrid Capture - 混合方案：结合 V41.650 和 OSS 智能."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("=" * 80)
    logger.info("V41.662 Hybrid Capture - 启动")
    logger.info("=" * 80)

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

    if league:
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

    # 运行处理
    async def run_processing():
        extractor = HybridHashExtractor()

        # 加载 V41.650 结果
        await extractor.load_v650_results()

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
            v650_count = sum(1 for r in results if r and r.get("capture_method") == "v650")
            dom_count = sum(1 for r in results if r and r.get("capture_method") == "dom")

            logger.info(
                f"""
╔══════════════════════════════════════════════════════════════════════╗
║           V41.662 Hybrid Capture - 回填报告                             ║
╚══════════════════════════════════════════════════════════════════════╝

处理统计:
  • 总处理数: {len(results)}
  • 成功匹配: {successful}
  • 匹配失败: {len(results) - successful}
  • 成功率: {(successful / max(1, len(results))) * 100:.2f}%

方法分布:
  • V41.650 缓存: {v650_count}
  • DOM 提取: {dom_count}
  • 模糊匹配: {successful - v650_count - dom_count}

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
   方法: {rec.get('capture_method', 'N/A')}
   fotmob_id: {rec['fotmob_id']}
"""
                    )
                    if i >= 9:
                        break

    asyncio.run(run_processing())


if __name__ == "__main__":
    main()
