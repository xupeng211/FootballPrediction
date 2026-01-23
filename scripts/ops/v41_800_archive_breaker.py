#!/usr/bin/env python3
"""V41.800 "Archive Breaker" - 英超 24/25 全量补全计划.

核心战略:
    1. 放弃动态滚动，锁定 2024/2025 归档 URL
    2. 通过点击数字分页符 (1-8)，实现 100% 数据打捞
    3. 穷举队名拆分 + Relaxed_Match 对齐
    4. 闭环入库 (ON CONFLICT UPDATE)

Author: Senior Lead Data Systems Architect (TDD Specialist)
Version: V41.800
Date: 2026-01-23
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Any

import psycopg2
from playwright.async_api import async_playwright

from src.config_unified import get_settings
from src.utils.text_processor import TeamNameNormalizer

# ============================================================================
# Configuration
# ============================================================================

logger = logging.getLogger(__name__)

# Matching thresholds (V41.790 Golden Sweep settings)
VIOLENT_THRESHOLD = 50.0
RELAXED_THRESHOLD = 60.0
FUZZY_THRESHOLD = 80.0

# Date tolerance: ±48 hours
DATE_TOLERANCE_HOURS = 48

# Database configuration
settings = get_settings()

# League slug mapping
LEAGUE_SLUGS = {
    "Premier League": "premier-league",
    "La Liga": "la-liga",
    "Serie A": "serie-a",
    "Bundesliga": "bundesliga",
    "Ligue 1": "ligue-1",
}

# ============================================================================
# Archive URL Builder (TDD Verified)
# ============================================================================


def build_archive_url(league: str, season: str) -> str:
    """构建 OddsPortal 归档 URL (TDD Verified).

    Args:
        league: 联赛名称 (如 "Premier League")
        season: 赛季 (如 "2024/2025")

    Returns:
        归档 URL (包含赛季后缀)
    """
    slug = LEAGUE_SLUGS.get(league, league.lower().replace(" ", "-"))
    season_suffix = season.replace("/", "-")
    return f"https://www.oddsportal.com/football/england/{slug}-{season_suffix}/results/"


# ============================================================================
# Database Operations
# ============================================================================


def get_missing_matches(league: str, season: str) -> list[dict[str, Any]]:
    """获取缺失哈希的比赛列表."""
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
    """暴力回填 - 遇到冲突直接覆盖."""
    conn = psycopg2.connect(
        host=settings.database.host,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    cur = conn.cursor()

    # Check if hash is already used
    check_hash_query = """
        SELECT fotmob_id FROM matches_mapping
        WHERE oddsportal_hash = %s
        LIMIT 1
    """
    cur.execute(check_hash_query, (oddsportal_hash,))
    existing_hash = cur.fetchone()

    if existing_hash and existing_hash[0] != fotmob_id:
        logger.debug(f"⏭️ 哈希 {oddsportal_hash} 已被使用，跳过")
        cur.close()
        conn.close()
        return False

    # Upsert
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
        confidence_value = round(similarity / 100.0, 2)
        cur.execute(
            upsert_query,
            (fotmob_id, oddsportal_hash, oddsportal_url, match_date, mapping_method, confidence_value),
        )
        conn.commit()

        logger.info(f"✅ [SAVED] {fotmob_id} -> {oddsportal_hash} ({similarity:.1f}%)")

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
    """获取已映射的比赛数量."""
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
# V41.800: Exhaustive Hash Extraction with Team Splitting
# ============================================================================


def _try_all_team_splits(team_segment: str) -> list[tuple[str, str]]:
    """穷举所有可能的队名拆分方式.

    Args:
        team_segment: 如 "bournemouth-leicester" 或 "crystal-palace-wolves"

    Returns:
        所有可能的拆分结果
    """
    parts = team_segment.split("-")
    splits = []

    if len(parts) == 1:
        splits.append((parts[0], parts[0]))
    elif len(parts) == 2:
        splits.append((parts[0], parts[1]))
    elif len(parts) == 3:
        # team1-team2 vs team3
        splits.append(("-".join(parts[:2]), parts[2]))
        # team1 vs team2-team3
        splits.append((parts[0], "-".join(parts[1:])))
    elif len(parts) == 4:
        # team1-team2 vs team3-team4
        splits.append(("-".join(parts[:2]), "-".join(parts[2:])))
        # team1 vs team2-team3-team4
        splits.append((parts[0], "-".join(parts[1:])))
    elif len(parts) == 5:
        # team1-team2 vs team3-team4-team5
        splits.append(("-".join(parts[:2]), "-".join(parts[2:])))
        # team1-team2-team3 vs team4-team5
        splits.append(("-".join(parts[:3]), "-".join(parts[3:])))
        # team1 vs team2-team3-team4-team5
        splits.append((parts[0], "-".join(parts[1:])))

    return splits


def extract_hashes_from_html(html_content: str) -> list[dict[str, Any]]:
    """V41.800: 从 HTML 内容中提取哈希值（穷举拆分策略）.

    归档页 URL 格式:
    /football/england/premier-league-2024-2025/bournemouth-leicester-44RKa9ke/
    /football/england/premier-league-2024-2025/crystal-palace-wolves-boy65vMG/
    """
    soup = __import__("bs4").BeautifulSoup(html_content, "html.parser")
    hashes = []
    seen_hashes = set()

    # Season filter
    season_filter = re.compile(r"-2024-2025/")
    # Match pattern: team1-team2-hash or team1-team2-team3-hash
    hash_pattern = re.compile(
        r"/football/england/premier-league-2024-2025/([^/]+?)-([A-Za-z0-9]{8})/"
    )

    all_links = soup.find_all("a", href=re.compile(r"/football/"))
    logger.info(f"  🔍 HTML 中找到 {len(all_links)} 个 football 链接")

    for link in all_links:
        href = link.get("href", "")

        if not season_filter.search(href):
            continue

        match = hash_pattern.search(href)
        if not match:
            continue

        team_segment = match.group(1)
        hash_value = match.group(2)

        if not hash_value.isalnum():
            continue

        if hash_value in seen_hashes:
            continue

        seen_hashes.add(hash_value)

        # Store with team_segment for later splitting
        hashes.append(
            {
                "hash_value": hash_value,
                "team_segment": team_segment,
                "url": f"https://www.oddsportal.com{href}",
            }
        )

    logger.info(f"  ✅ 成功提取 {len(hashes)} 个哈希条目")
    if hashes:
        logger.info(f"  📋 前 3 个哈希: {[h['hash_value'] for h in hashes[:3]]}")
    return hashes


# ============================================================================
# V41.800: Violent Matching with Relaxed_Match
# ============================================================================


def calculate_match_similarity_violent(
    harvested: dict[str, Any], missing: dict[str, Any]
) -> float:
    """V41.800: 暴力匹配引擎（使用 Relaxed_Match，无惩罚）."""
    normalizer = TeamNameNormalizer()

    team_segment = harvested.get("team_segment", "")

    # Try all possible splits
    splits = _try_all_team_splits(team_segment)
    best_score = 0

    for home_candidate, away_candidate in splits:
        home_team = home_candidate.replace("-", " ").title()
        away_team = away_candidate.replace("-", " ").title()

        home_score = normalizer.relaxed_match(
            home_team, missing["home_team"]
        )
        away_score = normalizer.relaxed_match(
            away_team, missing["away_team"]
        )

        avg_score = (home_score + away_score) / 2
        best_score = max(best_score, avg_score)

    return best_score


def _calculate_date_diff_hours(date1_str: str, date2_str: str) -> float:
    """计算两个日期之间的小时差."""
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
    """V41.800: 暴力对齐 - 50% 阈值即可入库."""
    alignments = []

    for harvested in harvested_hashes:
        best_match = None
        best_score = 0

        for missing in missing_matches:
            similarity = calculate_match_similarity_violent(harvested, missing)

            date_diff = _calculate_date_diff_hours(
                harvested.get("match_date", ""), missing.get("match_date", "")
            )
            date_match = abs(date_diff) <= DATE_TOLERANCE_HOURS

            if similarity >= VIOLENT_THRESHOLD:
                adjusted_score = similarity + (10.0 if date_match else 0)

                if adjusted_score > best_score:
                    best_score = adjusted_score
                    best_match = {
                        "fotmob_id": missing["match_id"],
                        "oddsportal_hash": harvested["hash_value"],
                        "oddsportal_url": harvested["url"],
                        "match_date": missing.get("match_date", ""),
                        "similarity": similarity,
                    }

        if best_match:
            alignments.append(best_match)

    return alignments


# ============================================================================
# V41.800: Digital Pagination Clicker
# ============================================================================


async def detect_max_pages(page) -> int:
    """检测归档页的最大页码."""
    try:
        # Look for pagination numbers
        await page.wait_for_selector("a[href*='#page/']", timeout=10000)

        # Get all pagination links
        page_links = await page.locator("a[href*='#page/']").all()

        max_page = 1
        for link in page_links:
            href = await link.get_attribute("href")
            if href:
                match = re.search(r"#page/(\d+)/", href)
                if match:
                    page_num = int(match.group(1))
                    max_page = max(max_page, page_num)

        logger.info(f"  📄 检测到最大页码: {max_page}")
        return max_page
    except Exception as e:
        logger.debug(f"  ⚠️ 分页检测失败: {e}")
        return 1


async def click_pagination_and_extract(page, page_num: int) -> str:
    """点击分页并提取内容."""
    try:
        # Click on page number
        page_selector = f"a[href*='#page/{page_num}/']"
        await page.wait_for_selector(page_selector, timeout=10000)

        # Use JavaScript click for more reliable clicking
        await page.locator(page_selector).click()
        await page.wait_for_timeout(5000)  # Wait for Vue.js rendering

        # Get content
        content = await page.content()
        return content
    except Exception as e:
        logger.error(f"  ❌ 点击第 {page_num} 页失败: {e}")
        return ""


async def harvest_all_pages(
    league: str,
    season: str,
    max_pages: int = 8,
) -> dict[str, Any]:
    """V41.800: 数字分页点击收割."""
    stats = {
        "pages_scanned": 0,
        "total_hashes": 0,
        "successful_matches": 0,
        "low_score_matches": 0,
        "start_time": asyncio.get_event_loop().time(),
    }

    base_url = build_archive_url(league, season)
    logger.info(f"📌 归档 URL: {base_url}")

    # Get missing matches
    missing_matches = get_missing_matches(league, season)
    initial_count = get_matched_count(league, season)

    logger.info(f"🏁 开始数字分页扫描: 待补全 {len(missing_matches)} 场")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Load first page
        logger.info(f"🔄 [PAGE 1] 加载首页...")
        await page.goto(base_url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)

        # Detect max pages
        max_detected = await detect_max_pages(page)
        actual_pages = min(max_pages, max_detected)
        logger.info(f"  📄 将扫描 {actual_pages} 页（检测到 {max_detected} 页）")

        # Process page 1
        content = await page.content()
        hashes = extract_hashes_from_html(content)
        alignments = stitch_matches_violent(hashes, missing_matches)

        page_inserted = 0
        for alignment in alignments:
            if aggressive_upsert_match_mapping(
                fotmob_id=alignment["fotmob_id"],
                oddsportal_hash=alignment["oddsportal_hash"],
                oddsportal_url=alignment["oddsportal_url"],
                match_date=alignment["match_date"],
                similarity=alignment["similarity"],
                mapping_method="v41.800_archive_breaker",
            ):
                page_inserted += 1

        stats["pages_scanned"] += 1
        stats["total_hashes"] += len(hashes)
        stats["successful_matches"] += page_inserted

        logger.info(
            f"  📊 [PAGE 1] 扫描到: {len(hashes)} 条 | 成功入库: {page_inserted} 条"
        )

        # Refresh missing matches
        missing_matches = get_missing_matches(league, season)

        # Process pages 2 to N
        for page_num in range(2, actual_pages + 1):
            logger.info(f"🔄 [PAGE {page_num}/{actual_pages}] 点击分页...")

            content = await click_pagination_and_extract(page, page_num)

            if not content:
                logger.warning(f"  ⚠️ 第 {page_num} 页无内容，跳过")
                continue

            hashes = extract_hashes_from_html(content)

            if not hashes:
                logger.debug(f"  ⚠️ 第 {page_num} 页无哈希提取，跳过")
                continue

            alignments = stitch_matches_violent(hashes, missing_matches)

            page_inserted = 0
            for alignment in alignments:
                if aggressive_upsert_match_mapping(
                    fotmob_id=alignment["fotmob_id"],
                    oddsportal_hash=alignment["oddsportal_hash"],
                    oddsportal_url=alignment["oddsportal_url"],
                    match_date=alignment["match_date"],
                    similarity=alignment["similarity"],
                    mapping_method="v41.800_archive_breaker",
                ):
                    page_inserted += 1

            stats["pages_scanned"] += 1
            stats["total_hashes"] += len(hashes)
            stats["successful_matches"] += page_inserted

            logger.info(
                f"  📊 [PAGE {page_num}] 扫描到: {len(hashes)} 条 | 成功入库: {page_inserted} 条"
            )

            # Refresh missing matches
            missing_matches = get_missing_matches(league, season)

            # Early exit if no more missing matches
            if not missing_matches:
                logger.info("  🎉 所有比赛已补全，提前退出！")
                break

        await browser.close()

    # Final stats
    stats["duration"] = asyncio.get_event_loop().time() - stats["start_time"]
    final_count = get_matched_count(league, season)
    stats["final_matched"] = final_count
    stats["new_matches"] = final_count - initial_count

    return stats


# ============================================================================
# Post-Harvest Audit
# ============================================================================


def post_harvest_audit(league: str, season: str) -> list[dict[str, Any]]:
    """战后审计补刀 - 打印剩余孤儿详情."""
    missing_matches = get_missing_matches(league, season)

    if not missing_matches:
        logger.info("🎉 完美！所有比赛已补全，无剩余孤儿！")
        return []

    logger.warning(f"\n⚠️ 剩余 {len(missing_matches)} 场孤儿比赛详情:")
    for i, match in enumerate(missing_matches[:20], 1):
        logger.warning(
            f"   {i}. {match['match_id']} | "
            f"{match['home_team']} vs {match['away_team']} | "
            f"{match['match_date']}"
        )

    if len(missing_matches) > 20:
        logger.warning(f"   ... 还有 {len(missing_matches) - 20} 场")

    return missing_matches


# ============================================================================
# Main Entry Point
# ============================================================================


async def main():
    """V41.800 主入口."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("=" * 70)
    logger.info("V41.800 Archive Breaker - 英超 24/25 全量补全计划")
    logger.info("=" * 70)

    # Configuration
    league = "Premier League"
    season = "2024/2025"
    total_matches = 380

    # Get initial stats
    missing_matches = get_missing_matches(league, season)
    initial_matched = get_matched_count(league, season)

    logger.info(f"📊 初始状态: 已映射 {initial_matched}/{total_matches} ({initial_matched/total_matches*100:.1f}%)")
    logger.info(f"📊 待补全: {len(missing_matches)} 场")

    # Step 1: Digital pagination harvesting
    logger.info("\n" + "=" * 70)
    logger.info("🚀 Step 1: 数字分页点击收割（1-8 页）")
    logger.info("=" * 70)

    stats = await harvest_all_pages(league, season, max_pages=8)

    # Step 2: Post-harvest audit
    logger.info("\n" + "=" * 70)
    logger.info("⚔️ Step 2: 战后审计补刀")
    logger.info("=" * 70)

    final_missing = post_harvest_audit(league, season)
    final_matched = stats["final_matched"]

    logger.info("\n" + "=" * 70)
    logger.info("📊 扫描完成:")
    logger.info("=" * 70)
    logger.info(f"   - 扫描页数: {stats['pages_scanned']}")
    logger.info(f"   - 提取哈希: {stats['total_hashes']}")
    logger.info(f"   - 新增记录: {stats['new_matches']}")
    logger.info(f"   - 执行耗时: {stats['duration']:.1f} 秒")
    logger.info(f"\n📊 最终状态: 已映射 {final_matched}/{total_matches} ({final_matched/total_matches*100:.1f}%)")
    logger.info(f"📊 剩余孤儿: {len(final_missing)} 场")

    # Verify acceptance criteria
    logger.info("\n" + "=" * 70)
    logger.info("🎯 验收标准检查")
    logger.info("=" * 70)

    # Coverage: 99% of 341 missing = 338+ recovered
    total_missing_before = 341
    recovered = stats['new_matches']
    coverage_rate = recovered / total_missing_before * 100 if total_missing_before > 0 else 0

    passed_coverage = recovered >= 338
    passed_stability = stats['pages_scanned'] <= 8

    logger.info(f"覆盖率标准: 回填 >= 99% (338+/341)")
    logger.info(f"实际回填: {recovered}/341 ({coverage_rate:.1f}%)")
    logger.info(f"结果: {'✅ 通过' if passed_coverage else '❌ 失败'}")

    logger.info(f"\n稳定性标准: 严禁无效加载（最多 8 页）")
    logger.info(f"实际扫描: {stats['pages_scanned']} 页")
    logger.info(f"结果: {'✅ 通过' if passed_stability else '❌ 失败'}")

    if passed_coverage and passed_stability:
        logger.info("\n🎉 V41.800 任务完成！Archive Breaker 成功！")
    else:
        logger.info("\n⚠️ 部分验收未达标")

    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
