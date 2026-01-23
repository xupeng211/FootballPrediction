#!/usr/bin/env python3
"""V41.810 "Archive Brute Force" - 8页抽屉强行开启计划.

核心战略:
    1. 废除"页码自动检测"，强制执行 1-8 页导航
    2. Deep DOM Scrape - 全量扫描不遗漏
    3. 暴力缝合 - Relaxed Match 100%

Author: Senior Lead Data Systems Architect (HPC Specialist)
Version: V41.810
Date: 2026-01-23
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Any

import psycopg2
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from src.config_unified import get_settings
from src.utils.text_processor import TeamNameNormalizer

# ============================================================================
# Configuration
# ============================================================================

logger = logging.getLogger(__name__)

# V41.790 Golden Sweep settings
VIOLENT_THRESHOLD = 50.0
RELAXED_THRESHOLD = 60.0
FUZZY_THRESHOLD = 80.0
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

# V41.810: 强制配置
FORCE_MAX_PAGES = 8  # 老板指令：强制 8 页
FORCE_RENDER_WAIT_MS = 8000  # 强制等待 8 秒渲染

# ============================================================================
# Archive URL Generator (TDD Verified)
# ============================================================================


def build_archive_url(league: str, season: str) -> str:
    """构建归档 URL."""
    slug = LEAGUE_SLUGS.get(league, league.lower().replace(" ", "-"))
    season_suffix = season.replace("/", "-")
    return f"https://www.oddsportal.com/football/england/{slug}-{season_suffix}/results/"


def generate_page_urls(base_url: str, max_page: int = FORCE_MAX_PAGES) -> list[str]:
    """生成 1-8 页 URL 序列（强行模式）."""
    urls = []
    for page_num in range(1, max_page + 1):
        if page_num == 1:
            urls.append(base_url)
        else:
            url = f"{base_url}#page/{page_num}/"
            urls.append(url)
    return urls


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
    """暴力回填."""
    conn = psycopg2.connect(
        host=settings.database.host,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    cur = conn.cursor()

    check_hash_query = """
        SELECT fotmob_id FROM matches_mapping
        WHERE oddsportal_hash = %s
        LIMIT 1
    """
    cur.execute(check_hash_query, (oddsportal_hash,))
    existing_hash = cur.fetchone()

    if existing_hash and existing_hash[0] != fotmob_id:
        cur.close()
        conn.close()
        return False

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
# V41.810: Deep DOM Scrape - Full Match Pattern
# ============================================================================


def extract_hashes_deep_scrape(html_content: str) -> list[dict[str, Any]]:
    """V41.810: Deep DOM Scrape - 全量哈希提取.

    策略:
        - 不依赖链接解析
        - 直接用 full_match_pattern 扫描整个 HTML
        - 抓取所有包含 -HASH/ 结构的字符串
    """
    hashes = []
    seen_hashes = set()

    # V41.810: Full match pattern - 抓取所有可能的哈希格式
    # 格式: /football/england/premier-league-2024-2025/...-ABC12345/
    full_match_pattern = re.compile(
        r"/football/england/premier-league-2024-2025/([A-Za-z0-9-]+?)-([A-Za-z0-9]{8})/"
    )

    # Find all matches in HTML
    all_matches = full_match_pattern.findall(html_content)

    logger.info(f"  🔍 Deep DOM Scrape: 找到 {len(all_matches)} 个潜在哈希匹配")

    for team_segment, hash_value in all_matches:
        # Validate hash
        if not hash_value.isalnum():
            continue

        if hash_value in seen_hashes:
            continue

        seen_hashes.add(hash_value)

        hashes.append(
            {
                "hash_value": hash_value,
                "team_segment": team_segment,
                "url": f"https://www.oddsportal.com/football/england/premier-league-2024-2025/{team_segment}-{hash_value}/",
            }
        )

    logger.info(f"  ✅ Deep DOM Scrape: 提取 {len(hashes)} 个有效哈希")
    return hashes


# ============================================================================
# V41.810: Violent Matching with Relaxed Match 100%
# ============================================================================


def _try_all_team_splits(team_segment: str) -> list[tuple[str, str]]:
    """穷举所有可能的队名拆分方式."""
    parts = team_segment.split("-")
    splits = []

    if len(parts) == 1:
        splits.append((parts[0], parts[0]))
    elif len(parts) == 2:
        splits.append((parts[0], parts[1]))
    elif len(parts) == 3:
        splits.append(("-".join(parts[:2]), parts[2]))
        splits.append((parts[0], "-".join(parts[1:])))
    elif len(parts) == 4:
        splits.append(("-".join(parts[:2]), "-".join(parts[2:])))
        splits.append((parts[0], "-".join(parts[1:])))
    elif len(parts) == 5:
        splits.append(("-".join(parts[:2]), "-".join(parts[2:])))
        splits.append(("-".join(parts[:3]), "-".join(parts[3:])))
        splits.append((parts[0], "-".join(parts[1:])))

    return splits


def calculate_match_similarity_violent(
    harvested: dict[str, Any], missing: dict[str, Any]
) -> float:
    """V41.810: 暴力匹配引擎（Relaxed Match 100%）."""
    normalizer = TeamNameNormalizer()

    team_segment = harvested.get("team_segment", "")

    # Try all possible splits
    splits = _try_all_team_splits(team_segment)
    best_score = 0

    for home_candidate, away_candidate in splits:
        home_team = home_candidate.replace("-", " ").title()
        away_team = away_candidate.replace("-", " ").title()

        # V41.810: Relaxed Match 100% - 核心词匹配即过关
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
    """V41.810: 暴力缝合 - 50% 阈值."""
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
# V41.810: Brute Force 8-Page Harvester
# ============================================================================


async def brute_force_harvest_all_pages(
    league: str,
    season: str,
    max_pages: int = FORCE_MAX_PAGES,
) -> dict[str, Any]:
    """V41.810: 暴力强行收割 1-8 页."""
    stats = {
        "pages_scanned": 0,
        "page_results": [],  # 记录每页的提取数量
        "total_hashes": 0,
        "successful_matches": 0,
        "start_time": asyncio.get_event_loop().time(),
    }

    base_url = build_archive_url(league, season)
    page_urls = generate_page_urls(base_url, max_pages)

    logger.info(f"📌 归档 URL: {base_url}")
    logger.info(f"🎯 强行扫描 {len(page_urls)} 页（第 1 页无 Fragment）")

    # Get missing matches
    missing_matches = get_missing_matches(league, season)
    initial_count = get_matched_count(league, season)

    logger.info(f"🏁 开始强行收割: 待补全 {len(missing_matches)} 场")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # V41.810: 暴力遍历 1-8 页
        for i, page_url in enumerate(page_urls):
            page_num = i + 1
            logger.info(f"🔄 [PAGE {page_num}/{len(page_urls)}] 强行访问...")

            try:
                # Navigate to page
                await page.goto(page_url, wait_until="networkidle", timeout=60000)

                # V41.810: 强制等待渲染
                await page.wait_for_timeout(FORCE_RENDER_WAIT_MS)

                # Get content
                content = await page.content()

                # V41.810: Deep DOM Scrape
                hashes = extract_hashes_deep_scrape(content)

                # Record page result
                stats["page_results"].append(
                    {"page": page_num, "hashes_extracted": len(hashes)}
                )

                # Stitch and insert
                alignments = stitch_matches_violent(hashes, missing_matches)

                page_inserted = 0
                for alignment in alignments:
                    if aggressive_upsert_match_mapping(
                        fotmob_id=alignment["fotmob_id"],
                        oddsportal_hash=alignment["oddsportal_hash"],
                        oddsportal_url=alignment["oddsportal_url"],
                        match_date=alignment["match_date"],
                        similarity=alignment["similarity"],
                        mapping_method="v41.810_brute_force",
                    ):
                        page_inserted += 1

                stats["pages_scanned"] += 1
                stats["total_hashes"] += len(hashes)
                stats["successful_matches"] += page_inserted

                # V41.810: 强制报告每页结果（哪怕 0 条）
                logger.info(
                    f"  📊 [PAGE {page_num}/{len(page_urls)}] "
                    f"提取: {len(hashes)} 条 | "
                    f"入库: {page_inserted} 条"
                )

                # Refresh missing matches for next page
                missing_matches = get_missing_matches(league, season)

                # Early exit if no more missing
                if not missing_matches:
                    logger.info("  🎉 所有比赛已补全，提前退出！")
                    break

            except Exception as e:
                logger.error(f"  ❌ [PAGE {page_num}] 扫描失败: {e}")
                stats["page_results"].append(
                    {"page": page_num, "hashes_extracted": 0, "error": str(e)}
                )

        await browser.close()

    # Final stats
    stats["duration"] = asyncio.get_event_loop().time() - stats["start_time"]
    final_count = get_matched_count(league, season)
    stats["final_matched"] = final_count
    stats["new_matches"] = final_count - initial_count

    return stats


# ============================================================================
# Post-Harvest Report
# ============================================================================


def print_page_by_page_report(stats: dict[str, Any]):
    """打印每页抓取结果."""
    logger.info("\n📋 V41.810: 逐页抓取报告")
    logger.info("=" * 60)

    for result in stats["page_results"]:
        page_num = result["page"]
        count = result["hashes_extracted"]

        if "error" in result:
            logger.error(f"  页 {page_num}: ❌ 错误 - {result['error']}")
        else:
            status = "✅" if count > 0 else "⚠️"
            logger.info(f"  页 {page_num}: {status} 提取到 {count} 个哈希")

    logger.info("=" * 60)


def post_harvest_audit(league: str, season: str) -> list[dict[str, Any]]:
    """战后审计补刀."""
    missing_matches = get_missing_matches(league, season)

    if not missing_matches:
        logger.info("🎉 完美！所有比赛已补全，无剩余孤儿！")
        return []

    logger.warning(f"\n⚠️ 剩余 {len(missing_matches)} 场孤儿比赛:")

    # 按月份分组统计
    from collections import defaultdict
    by_month = defaultdict(list)

    for match in missing_matches[:50]:  # 只显示前 50 场
        if match.get("match_date"):
            month = match["match_date"][:7]  # YYYY-MM
            by_month[month].append(match)

    for month in sorted(by_month.keys()):
        matches = by_month[month]
        logger.warning(f"  {month}: {len(matches)} 场")

    if len(missing_matches) > 50:
        logger.warning(f"  ... 还有 {len(missing_matches) - 50} 场")

    return missing_matches


# ============================================================================
# Main Entry Point
# ============================================================================


async def main():
    """V41.810 主入口."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("=" * 70)
    logger.info("V41.810 Archive Brute Force - 8页抽屉强行开启")
    logger.info("=" * 70)

    league = "Premier League"
    season = "2024/2025"
    total_matches = 380

    # Get initial stats
    missing_matches = get_missing_matches(league, season)
    initial_matched = get_matched_count(league, season)

    logger.info(f"📊 初始状态: 已映射 {initial_matched}/{total_matches} ({initial_matched/total_matches*100:.1f}%)")
    logger.info(f"📊 待补全: {len(missing_matches)} 场")

    # Brute force harvest
    logger.info("\n" + "=" * 70)
    logger.info("🚀 Step 1: 暴力强行收割（1-8 页）")
    logger.info("=" * 70)

    stats = await brute_force_harvest_all_pages(league, season, max_pages=FORCE_MAX_PAGES)

    # Page by page report
    print_page_by_page_report(stats)

    # Post-harvest audit
    logger.info("\n" + "=" * 70)
    logger.info("⚔️ Step 2: 战后审计")
    logger.info("=" * 70)

    final_missing = post_harvest_audit(league, season)
    final_matched = stats["final_matched"]

    logger.info("\n" + "=" * 70)
    logger.info("📊 扫描完成:")
    logger.info("=" * 70)
    logger.info(f"   - 扫描页数: {stats['pages_scanned']}")
    logger.info(f"   - 总提取哈希: {stats['total_hashes']}")
    logger.info(f"   - 新增记录: {stats['new_matches']}")
    logger.info(f"   - 执行耗时: {stats['duration']/60:.1f} 分钟")
    logger.info(f"\n📊 最终状态: 已映射 {final_matched}/{total_matches} ({final_matched/total_matches*100:.1f}%)")
    logger.info(f"📊 剩余孤儿: {len(final_missing)} 场")

    # Verify acceptance criteria
    logger.info("\n" + "=" * 70)
    logger.info("🎯 验收标准检查")
    logger.info("=" * 70)

    passed_coverage = stats['new_matches'] >= 300
    passed_time = stats['duration'] <= 600  # 10 minutes

    logger.info(f"补全数标准: >= 300 场")
    logger.info(f"实际补全: {stats['new_matches']} 场")
    logger.info(f"结果: {'✅ 通过' if passed_coverage else '❌ 失败'}")

    logger.info(f"\n时间限制: 10 分钟内完成")
    logger.info(f"实际耗时: {stats['duration']/60:.1f} 分钟")
    logger.info(f"结果: {'✅ 通过' if passed_time else '❌ 失败'}")

    if passed_coverage and passed_time:
        logger.info("\n🎉 V41.810 任务完成！8页抽屉强行开启成功！")
    else:
        logger.info("\n⚠️ 部分验收未达标")

    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
