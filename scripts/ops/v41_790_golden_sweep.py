#!/usr/bin/env python3
"""V41.790 "The Golden Sweep" - 废除匹配惩罚与 100% 闭环收割.

核心改进:
    1. V41.35 Similarity Penalty 完全废除
    2. Relaxed_Match 排他模式（核心词相同 + >60% → >=80%）
    3. 暴力对账：50% 相似度即可入库（人工审核兜底）
    4. 深度扫描：40-50 页覆盖 2024-08 数据
    5. 数据库暴力回填：ON CONFLICT DO UPDATE

Author: Senior Lead Data Architect (TDD Specialist)
Version: V41.790
Date: 2026-01-23
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Any

import psycopg2
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from src.config_unified import get_settings
from src.utils.text_processor import TeamNameNormalizer

# ============================================================================
# Configuration
# ============================================================================

logger = logging.getLogger(__name__)

# V41.790: 暴力对账阈值（降低到 50%，人工审核兜底）
VIOLENT_THRESHOLD = 50.0
RELAXED_THRESHOLD = 60.0
FUZZY_THRESHOLD = 80.0

# Date tolerance: ±48 hours
DATE_TOLERANCE_HOURS = 48

# Database configuration
settings = get_settings()

# V41.790: 更宽松的哈希模式（支持更多 URL 变体）
# OddsPortal URL 格式变体:
# - /football/england/premier-league/team1-team2-HASH/
# - /football/england/premier-league/team1-team2-HASH/#page/
HASH_PATTERNS = [
    re.compile(r"/([A-Za-z0-9]{8})/"),  # 8-char hash
    re.compile(r"/([A-Za-z0-9]{10})/"),  # 10-char hash
]

# V41.790: 多层队名提取策略
TEAM_PATTERNS = [
    # 完整模式: /football/england/premier-league/team1-team2-HASH/
    re.compile(r"/football/[^/]+/[^/]+/([^/]+)-([^/]+)-[A-Za-z0-9]{8,10}/"),
    # 简化模式: /football/.../team1-team2/
    re.compile(r"/football/.+?/([^/]+)-([^/]+)/"),
]


# ============================================================================
# Database Operations
# ============================================================================


def get_missing_matches(league: str, season: str) -> list[dict[str, Any]]:
    """获取缺失哈希的比赛列表.

    Args:
        league: 联赛名称
        season: 赛季

    Returns:
        缺失比赛列表
    """
    conn = psycopg2.connect(
        host=settings.database.host,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    cur = conn.cursor()

    query = """
        SELECT
            m.match_id,
            m.home_team,
            m.away_team,
            m.match_date
        FROM matches m
        LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
        WHERE m.league_name = %s
            AND m.season = %s
            AND mm.oddsportal_hash IS NULL
        ORDER BY m.match_date ASC
    """

    cur.execute(query, (league, season))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "match_id": row[0],
            "home_team": row[1],
            "away_team": row[2],
            "match_date": str(row[3]) if row[3] else None,
        }
        for row in rows
    ]


def aggressive_upsert_match_mapping(
    fotmob_id: str,
    oddsportal_hash: str,
    oddsportal_url: str,
    match_date: str,
    similarity: float,
    mapping_method: str,
) -> bool:
    """V41.790: 暴力回填 - 遇到冲突直接覆盖.

    Args:
        fotmob_id: FotMob match ID
        oddsportal_hash: OddsPortal hash
        oddsportal_url: OddsPortal URL
        match_date: 比赛日期
        similarity: 相似度分数
        mapping_method: 映射方法标识

    Returns:
        是否成功插入/更新
    """
    conn = psycopg2.connect(
        host=settings.database.host,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    cur = conn.cursor()

    # V41.790: 检查哈希是否已被其他比赛使用
    check_hash_query = """
        SELECT fotmob_id FROM matches_mapping
        WHERE oddsportal_hash = %s
        LIMIT 1
    """
    cur.execute(check_hash_query, (oddsportal_hash,))
    existing_hash = cur.fetchone()

    if existing_hash and existing_hash[0] != fotmob_id:
        # 哈希已被其他比赛使用，跳过
        logger.debug(f"⏭️ 哈希 {oddsportal_hash} 已被比赛 {existing_hash[0]} 使用，跳过")
        cur.close()
        conn.close()
        return False

    # V41.790: 暴力回填 - 不检查冲突，直接覆盖
    upsert_query = """
        INSERT INTO matches_mapping
            (fotmob_id, oddsportal_hash, oddsportal_url, match_date, mapping_method, confidence)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (fotmob_id) DO UPDATE SET
            oddsportal_hash = EXCLUDED.oddsportal_hash,
            oddsportal_url = EXCLUDED.oddsportal_url,
            match_date = EXCLUDED.match_date,
            mapping_method = EXCLUDED.mapping_method,
            confidence = EXCLUDED.confidence,
            updated_at = CURRENT_TIMESTAMP
    """

    try:
        # V41.790: 根据相似度设置置信度（0.0-1.0）
        # similarity 是 0-100 的百分比，需要转换为 0.0-1.0
        confidence_value = round(similarity / 100.0, 2)

        cur.execute(
            upsert_query,
            (fotmob_id, oddsportal_hash, oddsportal_url, match_date, mapping_method, confidence_value),
        )
        conn.commit()

        # V41.790: 添加 [FIXED] 日志标识
        if similarity >= 80.0:
            logger.info(f"✅ [FIXED] Saved match with relaxed score: {similarity:.1f}% - {fotmob_id} -> {oddsportal_hash}")
        else:
            logger.warning(f"⚠️ [LOW-SCORE] Saved with low similarity: {similarity:.1f}% - {fotmob_id} -> {oddsportal_hash}")

        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ 插入失败: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False


def get_matched_count(league: str, season: str) -> int:
    """获取已映射的比赛数量.

    Args:
        league: 联赛名称
        season: 赛季

    Returns:
        已映射数量
    """
    conn = psycopg2.connect(
        host=settings.database.host,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    cur = conn.cursor()

    query = """
        SELECT COUNT(DISTINCT mm.fotmob_id)
        FROM matches_mapping mm
        JOIN matches m ON mm.fotmob_id = m.match_id
        WHERE m.league_name = %s AND m.season = %s
            AND mm.oddsportal_hash IS NOT NULL
    """

    cur.execute(query, (league, season))
    count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return count


# ============================================================================
# V41.790: Enhanced Hash Extraction
# ============================================================================


def extract_hashes_from_html(html_content: str) -> list[dict[str, Any]]:
    """V41.790: 从 HTML 内容中提取哈希值（多层策略）.

    Args:
        html_content: HTML 内容

    Returns:
        哈希条目列表
    """
    soup = BeautifulSoup(html_content, "html.parser")
    hashes = []
    seen_hashes = set()

    # Find all football links
    all_links = soup.find_all("a", href=re.compile(r"/football/"))
    logger.debug(f"  🔍 HTML 中找到 {len(all_links)} 个 football 链接")

    # V41.790: 完整模式 - 必须包含队名-队名-哈希结构
    # 哈希必须在队名之后
    full_match_pattern = re.compile(
        r"/football/[^/]+/[^/]+/([^/]+)-([^/]+)-([A-Za-z0-9]{8,10})/"
    )

    for link in all_links:
        href = link.get("href", "")

        # 使用完整模式同时匹配队名和哈希
        match = full_match_pattern.search(href)
        if not match:
            continue

        home_team = match.group(1).replace("-", " ").title()
        away_team = match.group(2).replace("-", " ").title()
        hash_value = match.group(3)

        # 验证哈希是字母数字组合（不是目录名）
        if not hash_value.isalnum():
            continue

        if hash_value in seen_hashes:
            continue

        seen_hashes.add(hash_value)

        # Normalize team names
        normalizer = TeamNameNormalizer()
        home_team = normalizer.normalize(home_team)
        away_team = normalizer.normalize(away_team)

        hashes.append(
            {
                "hash_value": hash_value,
                "home_team": home_team,
                "away_team": away_team,
                "url": f"https://www.oddsportal.com{href}",
            }
        )

    logger.debug(f"  ✅ 成功提取 {len(hashes)} 个哈希条目")
    return hashes


# ============================================================================
# V41.790: Violent Matching Engine
# ============================================================================


def calculate_match_similarity_violent(
    harvested: dict[str, Any], missing: dict[str, Any]
) -> float:
    """V41.790: 暴力匹配引擎（使用 Relaxed_Match 排他模式）.

    Args:
        harvested: 采集的比赛数据
        missing: 缺失的比赛数据

    Returns:
        相似度分数 (0-100)
    """
    normalizer = TeamNameNormalizer()

    # V41.790: 排他使用 Relaxed_Match（废除惩罚后）
    home_score = normalizer.relaxed_match(
        harvested["home_team"], missing["home_team"]
    )
    away_score = normalizer.relaxed_match(
        harvested["away_team"], missing["away_team"]
    )

    # Average score
    return (home_score + away_score) / 2


def _calculate_date_diff_hours(date1_str: str, date2_str: str) -> float:
    """计算两个日期之间的小时差.

    Args:
        date1_str: 日期字符串 1
        date2_str: 日期字符串 2

    Returns:
        小时差（带符号）
    """
    try:
        dt1 = datetime.fromisoformat(date1_str.replace("Z", "+00:00"))
        dt2 = datetime.fromisoformat(date2_str.replace("Z", "+00:00"))
        diff = dt2 - dt1
        return diff.total_seconds() / 3600
    except Exception:
        return 999.9


def stitch_matches_violent(
    harvested_hashes: list[dict[str, Any]],
    missing_matches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """V41.790: 暴力对齐 - 50% 阈值即可入库.

    Args:
        harvested_hashes: 采集的哈希列表
        missing_matches: 缺失比赛列表

    Returns:
        对齐结果列表
    """
    alignments = []

    for harvested in harvested_hashes:
        best_match = None
        best_score = 0

        for missing in missing_matches:
            # Calculate team similarity using Relaxed_Match
            similarity = calculate_match_similarity_violent(harvested, missing)

            # Date tolerance check (±48 hours)
            date_diff = _calculate_date_diff_hours(
                harvested.get("match_date", ""), missing.get("match_date", "")
            )
            date_match = abs(date_diff) <= DATE_TOLERANCE_HOURS

            # V41.790: 暴力对账 - 50% 阈值
            if similarity >= VIOLENT_THRESHOLD:
                # Prefer matches with date alignment
                adjusted_score = similarity + (10.0 if date_match else 0)

                if adjusted_score > best_score:
                    best_score = adjusted_score
                    best_match = {
                        "fotmob_id": missing["match_id"],
                        "oddsportal_hash": harvested["hash_value"],
                        "oddsportal_url": harvested["url"],
                        "match_date": missing.get("match_date", ""),
                        "similarity": similarity,
                        "date_diff": date_diff,
                        "date_match": date_match,
                        "confidence": "high" if similarity >= FUZZY_THRESHOLD else "medium" if similarity >= RELAXED_THRESHOLD else "low",
                    }

        if best_match:
            alignments.append(best_match)

    return alignments


# ============================================================================
# V41.790: Deep Page Harvester
# ============================================================================


async def harvest_deep_pages(
    league: str,
    season: str,
    base_url: str,
    total_pages: int = 120,
) -> dict[str, Any]:
    """V41.790: 深度全页扫描（1-120 页）with 实时汇报.

    Args:
        league: 联赛名称
        season: 赛季
        base_url: 基础 URL
        total_pages: 总页数（默认 50 页，覆盖 2024-08 数据）

    Returns:
        扫描结果统计
    """
    stats = {
        "pages_scanned": 0,
        "total_hashes": 0,
        "successful_matches": 0,
        "low_score_matches": 0,
        "start_time": asyncio.get_event_loop().time(),
    }

    # Get missing matches before scan
    missing_matches = get_missing_matches(league, season)
    initial_count = get_matched_count(league, season)

    logger.info(
        f"🏁 开始深度全页扫描: {total_pages} 页, "
        f"待补全: {len(missing_matches)} 场"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for page_num in range(1, total_pages + 1):
            # Construct page URL
            if page_num == 1:
                page_url = base_url
            else:
                page_url = f"{base_url}#page/{page_num}/"

            logger.info(f"🔄 [PAGE {page_num}/{total_pages}] 开始扫描...")

            try:
                # Navigate and wait for Vue.js rendering
                await page.goto(page_url, wait_until="networkidle", timeout=60000)

                # Wait for JavaScript rendering
                await page.wait_for_timeout(8000)

                # Extract hashes
                content = await page.content()
                hashes = extract_hashes_from_html(content)

                if not hashes:
                    logger.debug(f"  [PAGE {page_num}] 无哈希提取，跳过")
                    continue

                # Stitch with missing matches (violent mode)
                alignments = stitch_matches_violent(hashes, missing_matches)

                # Insert matches
                page_inserted = 0
                page_low_score = 0
                for alignment in alignments:
                    if aggressive_upsert_match_mapping(
                        fotmob_id=alignment["fotmob_id"],
                        oddsportal_hash=alignment["oddsportal_hash"],
                        oddsportal_url=alignment["oddsportal_url"],
                        match_date=alignment["match_date"],
                        similarity=alignment["similarity"],
                        mapping_method="v41.790_golden_sweep_violent",
                    ):
                        page_inserted += 1
                        if alignment["similarity"] < 70.0:
                            page_low_score += 1

                # Update stats
                stats["pages_scanned"] += 1
                stats["total_hashes"] += len(hashes)
                stats["successful_matches"] += page_inserted
                stats["low_score_matches"] += page_low_score

                # Real-time reporting (per page)
                logger.info(
                    f"📊 [PAGE {page_num}/{total_pages}] "
                    f"扫描到: {len(hashes)} 条 | "
                    f"成功入库: {page_inserted} 条 | "
                    f"低分入库: {page_low_score} 条"
                )

                # Refresh missing matches for next page
                missing_matches = get_missing_matches(league, season)

                # Early exit if no more missing matches
                if not missing_matches:
                    logger.info("🎉 所有比赛已补全，提前退出扫描！")
                    break

            except Exception as e:
                logger.error(f"❌ [PAGE {page_num}/{total_pages}] 扫描失败: {e}")

        await browser.close()

    # Final stats
    stats["duration"] = asyncio.get_event_loop().time() - stats["start_time"]
    final_count = get_matched_count(league, season)
    stats["final_matched"] = final_count
    stats["new_matches"] = final_count - initial_count

    return stats


# ============================================================================
# Main Entry Point
# ============================================================================


async def main():
    """V41.790 主入口."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("=" * 70)
    logger.info("V41.790 The Golden Sweep - 废除匹配惩罚与 100% 闭环收割")
    logger.info("=" * 70)

    # Configuration
    league = "Premier League"
    season = "2024/2025"
    base_url = "https://www.oddsportal.com/football/england/premier-league/results/"

    # Get initial stats
    missing_matches = get_missing_matches(league, season)
    initial_matched = get_matched_count(league, season)

    total_matches = 380
    logger.info(f"📊 初始状态: 已映射 {initial_matched}/{total_matches} ({initial_matched/total_matches*100:.1f}%)")
    logger.info(f"📊 待补全: {len(missing_matches)} 场")

    # Step 1: Deep page scan (1-50 pages)
    logger.info("\n" + "=" * 70)
    logger.info("🚀 Step 1: 深度全页扫描 (1-120 页)")
    logger.info("=" * 70)

    stats = await harvest_deep_pages(league, season, base_url, total_pages=120)

    # Step 2: Final Audit
    logger.info("\n" + "=" * 70)
    logger.info("⚔️ Step 2: 最终审计")
    logger.info("=" * 70)

    final_missing = get_missing_matches(league, season)
    final_matched = get_matched_count(league, season)
    orphans = [m["match_id"] for m in final_missing]

    completion_rate = (final_matched / total_matches) * 100

    logger.info(f"📊 扫描完成:")
    logger.info(f"   - 扫描页数: {stats['pages_scanned']}")
    logger.info(f"   - 提取哈希: {stats['total_hashes']}")
    logger.info(f"   - 新增记录: {stats['new_matches']}")
    logger.info(f"   - 低分记录: {stats['low_score_matches']}")
    logger.info(f"   - 执行耗时: {stats['duration']:.1f} 秒")
    logger.info(f"\n📊 最终状态: 已映射 {final_matched}/{total_matches} ({completion_rate:.1f}%)")
    logger.info(f"📊 剩余孤儿: {len(orphans)} 场")

    if orphans:
        logger.warning("\n⚠️ 顽固分子列表（需要手动处理）:")
        for i, orphan_id in enumerate(orphans[:10], 1):
            logger.warning(f"   {i}. {orphan_id}")
        if len(orphans) > 10:
            logger.warning(f"   ... 还有 {len(orphans) - 10} 场")

    # Verify acceptance criteria
    logger.info("\n" + "=" * 70)
    logger.info("🎯 验收标准检查")
    logger.info("=" * 70)

    passed = stats['new_matches'] > 300
    status = "✅ 通过" if passed else "❌ 失败"

    logger.info(f"验收标准: 新增记录 > 300 场")
    logger.info(f"实际新增: {stats['new_matches']} 场")
    logger.info(f"结果: {status}")

    if passed:
        logger.info("\n🎉 V41.790 任务完成！黄金大扫荡成功！")
    else:
        logger.info(f"\n⚠️ 仅新增 {stats['new_matches']} 场，未达标")

    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
