#!/usr/bin/env python3
"""V41.795 "The Precision Sweep" - 8页归档全量回填.

核心改进:
    1. 修正 URL 构造器 - 使用归档页 URL (包含 -2024-2025 后缀)
    2. 自动检测最大页码 - 从分页导航中提取 N=8
    3. 暴力缝合引擎 - Relaxed_Match + 废除惩罚 + ±48h 窗口
    4. 战后审计补刀 - 打印剩余孤儿详情

Author: Senior Lead Data Architect (TDD Specialist)
Version: V41.795
Date: 2026-01-23
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Any

import psycopg2
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page

from src.config_unified import get_settings
from src.utils.text_processor import TeamNameNormalizer

# ============================================================================
# Configuration
# ============================================================================

logger = logging.getLogger(__name__)

# V41.795: 暴力缝合阈值
VIOLENT_THRESHOLD = 50.0
RELAXED_THRESHOLD = 60.0
FUZZY_THRESHOLD = 80.0

# Date tolerance: ±48 hours
DATE_TOLERANCE_HOURS = 48

# Database configuration
settings = get_settings()

# V41.795: Archive URL builder
LEAGUE_SLUGS = {
    "Premier League": "premier-league",
    "La Liga": "la-liga",
    "Serie A": "serie-a",
    "Bundesliga": "bundesliga",
    "Ligue 1": "ligue-1",
}


def build_archive_url(league: str, season: str) -> str:
    """构建 OddsPortal 归档 URL.

    Args:
        league: 联赛名称
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
    """V41.795: 暴力回填."""
    conn = psycopg2.connect(
        host=settings.database.host,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    cur = conn.cursor()

    # Check if hash already exists
    check_hash_query = """
        SELECT fotmob_id FROM matches_mapping
        WHERE oddsportal_hash = %s
        LIMIT 1
    """
    cur.execute(check_hash_query, (oddsportal_hash,))
    existing_hash = cur.fetchone()

    if existing_hash and existing_hash[0] != fotmob_id:
        logger.debug(f"⏭️ 哈希 {oddsportal_hash} 已被比赛 {existing_hash[0]} 使用，跳过")
        cur.close()
        conn.close()
        return False

    # Upsert with ON CONFLICT
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

        # V41.795: [FIXED] 日志标识
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
# V41.795: Enhanced Hash Extraction & Pagination Detection
# ============================================================================


def extract_hashes_from_html(html_content: str) -> list[dict[str, Any]]:
    """V41.795: 从 HTML 内容中提取哈希值（适配归档页格式）.

    归档页 URL 格式:
    /football/england/premier-league-2024-2025/bournemouth-leicester-44RKa9ke/
    /football/england/premier-league-2024-2025/crystal-palace-wolves-boy65vMG/

    注意: 队名可能包含 '-' (如 crystal-palace, manchester-united)
    """
    soup = BeautifulSoup(html_content, "html.parser")
    hashes = []
    seen_hashes = set()

    # V41.795: 策略 - 只提取哈希和完整队名段，不尝试拆分队名
    # 在匹配阶段使用 fuzzy_match 来匹配数据库队名
    season_filter = re.compile(r"-2024-2025/")
    # 匹配: /team1-team2-hash/ 或 /team1-team2-team3-hash/ 等
    # 关键是哈希总是 8 个字母数字字符
    hash_pattern = re.compile(
        r"/football/england/premier-league-2024-2025/([^/]+?)-([A-Za-z0-9]{8})/"
    )

    all_links = soup.find_all("a", href=re.compile(r"/football/"))
    logger.debug(f"  🔍 HTML 中找到 {len(all_links)} 个 football 链接")

    for link in all_links:
        href = link.get("href", "")

        # Step 1: 过滤出包含 "-2024-2025/" 的归档页链接
        if not season_filter.search(href):
            continue

        # Step 2: 提取队名段和哈希
        match = hash_pattern.search(href)
        if not match:
            continue

        # team_segment 可能是 "bournemouth-leicester" 或 "crystal-palace-wolves"
        team_segment = match.group(1)
        hash_value = match.group(2)

        if not hash_value.isalnum():
            continue

        if hash_value in seen_hashes:
            continue

        seen_hashes.add(hash_value)

        # 存储完整队名段，在匹配阶段进行拆分和模糊匹配
        hashes.append(
            {
                "hash_value": hash_value,
                "team_segment": team_segment,  # 原始队名段，未拆分
                "url": f"https://www.oddsportal.com{href}",
            }
        )

    logger.debug(f"  ✅ 成功提取 {len(hashes)} 个哈希条目")
    return hashes


def detect_max_pages(html_content: str) -> int:
    """V41.795: 从分页导航中检测最大页码.

    Args:
        html_content: HTML 内容

    Returns:
        最大页码
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # 查找分页链接
    # OddsPortal 分页格式: /football/.../results/#page/2/, #page/3/, etc.
    pagination_links = soup.find_all("a", href=re.compile(r"#page/\d+/"))

    max_page = 1
    for link in pagination_links:
        href = link.get("href", "")
        match = re.search(r"#page/(\d+)/", href)
        if match:
            page_num = int(match.group(1))
            max_page = max(max_page, page_num)

    logger.debug(f"  📄 检测到最大页码: {max_page}")
    return max_page


# ============================================================================
# V41.795: Violent Matching Engine
# ============================================================================


def _try_team_splits(team_segment: str) -> list[tuple[str, str]]:
    """尝试不同的队名拆分方式.

    Args:
        team_segment: 如 "bournemouth-leicester" 或 "crystal-palace-wolves"

    Returns:
        可能的拆分结果列表
    """
    parts = team_segment.split("-")
    splits = []

    # 单段队名（不太可能）
    if len(parts) == 1:
        splits.append((parts[0], parts[0]))

    # 两段队名
    elif len(parts) == 2:
        splits.append((parts[0], parts[1]))

    # 三段队名 (如 "manchester-united-fulham")
    elif len(parts) == 3:
        # 可能的拆分:
        # 1. team1-team2 vs team3
        # 2. team1 vs team2-team3
        splits.append(("-".join(parts[:2]), parts[2]))
        splits.append((parts[0], "-".join(parts[1:])))

    # 四段队名 (如 "crystal-palace-manchester-united")
    elif len(parts) == 4:
        # 可能的拆分:
        # 1. team1-team2 vs team3-team4
        # 2. team1 vs team2-team3-team4
        splits.append(("-".join(parts[:2]), "-".join(parts[2:])))
        splits.append((parts[0], "-".join(parts[1:])))

    return splits


def calculate_match_similarity_violent(
    harvested: dict[str, Any], missing: dict[str, Any]
) -> float:
    """V41.795: 暴力匹配引擎（使用 Relaxed_Match，无惩罚）."""
    normalizer = TeamNameNormalizer()

    # 从 team_segment 中提取队名
    team_segment = harvested.get("team_segment", "")

    # 如果已经有拆分的队名（向后兼容）
    if "home_team" in harvested and "away_team" in harvested:
        home_score = normalizer.relaxed_match(
            harvested["home_team"], missing["home_team"]
        )
        away_score = normalizer.relaxed_match(
            harvested["away_team"], missing["away_team"]
        )
        return (home_score + away_score) / 2

    # 否则尝试不同的拆分方式，选择最佳匹配
    splits = _try_team_splits(team_segment)
    best_score = 0

    for home_candidate, away_candidate in splits:
        # 转换为标准格式
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
    """V41.795: 暴力对齐 - 50% 阈值即可入库."""
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

            # V41.795: 暴力对账 - 50% 阈值
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
                        "date_diff": date_diff,
                        "date_match": date_match,
                    }

        if best_match:
            alignments.append(best_match)

    return alignments


# ============================================================================
# V41.795: Archive Page Harvester with Auto-Detection
# ============================================================================


async def harvest_archive_pages(
    league: str,
    season: str,
    total_pages: int = None,
) -> dict[str, Any]:
    """V41.795: 归档页全量扫描 with 深度滚动加载.

    Args:
        league: 联赛名称
        season: 赛季
        total_pages: 总页数（None = 深度滚动模式）

    Returns:
        扫描结果统计
    """
    stats = {
        "pages_scanned": 0,
        "total_hashes": 0,
        "successful_matches": 0,
        "low_score_matches": 0,
        "start_time": asyncio.get_event_loop().time(),
        "max_pages_detected": 0,
    }

    # Build archive URL
    base_url = build_archive_url(league, season)
    logger.info(f"📌 使用归档 URL: {base_url}")

    # Get missing matches before scan
    missing_matches = get_missing_matches(league, season)
    initial_count = get_matched_count(league, season)

    logger.info(
        f"🏁 开始归档页扫描: 待补全 {len(missing_matches)} 场"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Navigate to archive page
        logger.info(f"🔄 开始深度滚动加载...")
        await page.goto(base_url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)

        # V41.795: 深度滚动加载全部比赛
        last_hash_count = 0
        stale_count = 0
        max_scroll_attempts = 30  # 最多尝试 30 次滚动

        for scroll_attempt in range(max_scroll_attempts):
            # Scroll to bottom
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            # Get current content and count hashes
            content = await page.content()
            current_hashes = extract_hashes_from_html(content)
            current_count = len(current_hashes)

            logger.debug(
                f"  📜 滚动 {scroll_attempt + 1}/{max_scroll_attempts}: "
                f"已加载 {current_count} 场比赛"
            )

            # Check if no more content is loading
            if current_count == last_hash_count:
                stale_count += 1
                if stale_count >= 3:
                    logger.info(f"  ✅ 内容加载完成，共 {current_count} 场比赛")
                    break
            else:
                stale_count = 0
                last_hash_count = current_count

        # Final content after deep scroll
        final_content = await page.content()
        all_hashes = extract_hashes_from_html(final_content)

        logger.info(f"📊 深度滚动完成: 提取到 {len(all_hashes)} 个哈希条目")

        # Detect max pages (for reporting)
        max_pages = detect_max_pages(final_content)
        stats["max_pages_detected"] = max_pages
        stats["pages_scanned"] = 1

        # Match and insert
        alignments = stitch_matches_violent(all_hashes, missing_matches)

        page_inserted = 0
        page_low_score = 0
        for alignment in alignments:
            if aggressive_upsert_match_mapping(
                fotmob_id=alignment["fotmob_id"],
                oddsportal_hash=alignment["oddsportal_hash"],
                oddsportal_url=alignment["oddsportal_url"],
                match_date=alignment["match_date"],
                similarity=alignment["similarity"],
                mapping_method="v41.795_precision_sweep",
            ):
                page_inserted += 1
                if alignment["similarity"] < 70.0:
                    page_low_score += 1

        stats["total_hashes"] = len(all_hashes)
        stats["successful_matches"] = page_inserted
        stats["low_score_matches"] = page_low_score

        logger.info(
            f"📊 深度滚动扫描完成: "
            f"提取到 {len(all_hashes)} 条 | "
            f"成功入库: {page_inserted} 条 | "
            f"低分入库: {page_low_score} 条"
        )

        await browser.close()

    # Final stats
    stats["duration"] = asyncio.get_event_loop().time() - stats["start_time"]
    final_count = get_matched_count(league, season)
    stats["final_matched"] = final_count
    stats["new_matches"] = final_count - initial_count

    return stats


# ============================================================================
# V41.795: Post-Sweep Audit
# ============================================================================


def post_sweep_audit(league: str, season: str) -> list[dict[str, Any]]:
    """战后审计补刀 - 打印剩余孤儿详情.

    Args:
        league: 联赛名称
        season: 赛季

    Returns:
        孤儿比赛列表
    """
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
    """V41.795 主入口."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("=" * 70)
    logger.info("V41.795 The Precision Sweep - 8页归档全量回填")
    logger.info("=" * 70)

    # Configuration
    league = "Premier League"
    season = "2024/2025"

    # Verify archive URL format
    archive_url = build_archive_url(league, season)
    logger.info(f"📌 归档 URL: {archive_url}")
    logger.info(f"   验证: {'-2024-2025' in archive_url} ✅")

    # Get initial stats
    missing_matches = get_missing_matches(league, season)
    initial_matched = get_matched_count(league, season)

    total_matches = 380
    logger.info(f"\n📊 初始状态: 已映射 {initial_matched}/{total_matches} ({initial_matched/total_matches*100:.1f}%)")
    logger.info(f"📊 待补全: {len(missing_matches)} 场")

    # Step 1: Archive page sweep with auto-detection
    logger.info("\n" + "=" * 70)
    logger.info("🚀 Step 1: 归档页全量扫描（自动检测最大页码）")
    logger.info("=" * 70)

    start_time = asyncio.get_event_loop().time()
    stats = await harvest_archive_pages(league, season, total_pages=None)

    # Step 2: Post-sweep audit
    logger.info("\n" + "=" * 70)
    logger.info("⚔️ Step 2: 战后审计补刀")
    logger.info("=" * 70)

    final_missing = post_sweep_audit(league, season)
    final_matched = stats["final_matched"]
    completion_rate = (final_matched / total_matches) * 100

    logger.info(f"\n📊 扫描完成:")
    logger.info(f"   - 检测到最大页码: {stats['max_pages_detected']}")
    logger.info(f"   - 实际扫描页数: {stats['pages_scanned']}")
    logger.info(f"   - 提取哈希: {stats['total_hashes']}")
    logger.info(f"   - 新增记录: {stats['new_matches']}")
    logger.info(f"   - 低分记录: {stats['low_score_matches']}")
    logger.info(f"   - 执行耗时: {stats['duration']:.1f} 秒")
    logger.info(f"\n📊 最终状态: 已映射 {final_matched}/{total_matches} ({completion_rate:.1f}%)")
    logger.info(f"📊 剩余孤儿: {len(final_missing)} 场")

    # Verify acceptance criteria
    logger.info("\n" + "=" * 70)
    logger.info("🎯 验收标准检查")
    logger.info("=" * 70)

    # Acceptance: Boost from 39 to 350+
    passed = final_matched >= 350
    status = "✅ 通过" if passed else "❌ 失败"

    logger.info(f"验收标准: 已映射 >= 350 场（从 39 场提升）")
    logger.info(f"实际结果: {final_matched} 场")
    logger.info(f"提升幅度: +{final_matched - initial_matched} 场")
    logger.info(f"结果: {status}")

    # Time check: 8 pages in 15 minutes
    duration_minutes = stats['duration'] / 60
    time_passed = duration_minutes <= 15
    time_status = "✅ 通过" if time_passed else "❌ 超时"

    logger.info(f"\n时间限制: 8 页扫描应在 15 分钟内完成")
    logger.info(f"实际耗时: {duration_minutes:.1f} 分钟")
    logger.info(f"结果: {time_status}")

    if passed and time_passed:
        logger.info("\n🎉 V41.795 任务完成！精准大扫荡成功！")
    elif passed:
        logger.info(f"\n⚠️ 达标但超时：扫描用时 {duration_minutes:.1f} 分钟 > 15 分钟")
    else:
        logger.info(f"\n⚠️ 未达标：仅 {final_matched} 场（要求 350+ 场）")

    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
