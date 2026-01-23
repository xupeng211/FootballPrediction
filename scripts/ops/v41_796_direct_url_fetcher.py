#!/usr/bin/env python3
"""V41.796 Direct URL Fetcher - 针对性获取孤儿比赛哈希.

策略: 对于每个孤儿比赛，直接构造 OddsPortal URL 并提取哈希。
不依赖归档页或分页，而是逐场比赛获取。
"""

import asyncio
import logging
import re
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

# Database configuration
settings = get_settings()

# Team name to URL slug mapping
TEAM_SLUGS = {
    "Arsenal": "arsenal",
    "Aston Villa": "aston-villa",
    "AFC Bournemouth": "bournemouth",
    "Brentford": "brentford",
    "Brighton & Hove Albion": "brighton",
    "Chelsea": "chelsea",
    "Crystal Palace": "crystal-palace",
    "Everton": "everton",
    "Fulham": "fulham",
    "Liverpool": "liverpool",
    "Manchester City": "manchester-city",
    "Manchester United": "manchester-united",
    "Newcastle United": "newcastle-utd",
    "Ipswich Town": "ipswich",
    "Leicester City": "leicester",
    "Nottingham Forest": "nottingham",
    "Tottenham Hotspur": "tottenham",
    "West Ham United": "west-ham",
    "Wolverhampton Wanderers": "wolves",
    "Southampton": "southampton",
}

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

    # Check if hash is already used by another match
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

        logger.info(f"✅ [DIRECT] Saved match: {fotmob_id} -> {oddsportal_hash}")

        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ 插入失败: {e}")
        conn.rollback()
        cur.close()
        conn.close()
        return False


# ============================================================================
# URL Construction
# ============================================================================


def construct_match_url(home_team: str, away_team: str) -> str | None:
    """构造比赛 URL.

    Args:
        home_team: 主队名称
        away_team: 客队名称

    Returns:
        OddsPortal URL 或 None
    """
    # Convert team names to slugs
    home_slug = TEAM_SLUGS.get(home_team)
    away_slug = TEAM_SLUGS.get(away_team)

    if not home_slug or not away_slug:
        return None

    # Construct URL (without hash - we'll fetch it)
    return f"https://www.oddsportal.com/football/england/premier-league/{home_slug}-{away_slug}/"


# ============================================================================
# Hash Extraction from Match Page
# ============================================================================


async def fetch_hash_from_match_page(url: str) -> str | None:
    """从比赛页面提取哈希值.

    Args:
        url: 比赛 URL（可能不包含哈希）

    Returns:
        哈希值或 None
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # Navigate to URL
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000)

            # Get actual URL (might contain hash)
            actual_url = page.url

            # Extract hash from URL
            # Format: .../team1-team2-HASH/ or .../team1-team2-HASH/#page/1/
            hash_match = re.search(r'/([A-Za-z0-9]{8})/', actual_url)
            if hash_match:
                hash_value = hash_match.group(1)
                await browser.close()
                return hash_value

            # If no hash in URL, try to extract from page content
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")

            # Look for canonical link or other indicators
            canonical = soup.find("link", rel="canonical")
            if canonical:
                canonical_url = canonical.get("href", "")
                hash_match = re.search(r'/([A-Za-z0-9]{8})/', canonical_url)
                if hash_match:
                    await browser.close()
                    return hash_match.group(1)

        except Exception as e:
            logger.error(f"❌ 获取哈希失败 {url}: {e}")

        await browser.close()
        return None


# ============================================================================
# Main Entry Point
# ============================================================================


async def main():
    """V41.796 主入口."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("=" * 70)
    logger.info("V41.796 Direct URL Fetcher - 针对性获取孤儿比赛哈希")
    logger.info("=" * 70)

    # Configuration
    league = "Premier League"
    season = "2024/2025"

    # Get missing matches
    missing_matches = get_missing_matches(league, season)
    initial_count = len(missing_matches)

    logger.info(f"📊 待补全: {initial_count} 场")

    if not missing_matches:
        logger.info("🎉 所有比赛已补全！")
        return

    # Process matches in batches
    batch_size = 50
    processed = 0
    success_count = 0

    for i in range(0, len(missing_matches), batch_size):
        batch = missing_matches[i:i + batch_size]
        logger.info(f"🔄 处理批次 {i // batch_size + 1}/{(len(missing_matches) + batch_size - 1) // batch_size}")

        for match in batch:
            processed += 1

            # Construct URL
            url = construct_match_url(match["home_team"], match["away_team"])

            if not url:
                logger.warning(f"⏭️ 跳过（无法构造 URL）: {match['home_team']} vs {match['away_team']}")
                continue

            logger.info(f"  [{processed}/{initial_count}] 获取哈希: {match['home_team']} vs {match['away_team']}")

            # Fetch hash
            hash_value = await fetch_hash_from_match_page(url)

            if hash_value:
                # Save to database
                if aggressive_upsert_match_mapping(
                    fotmob_id=match["match_id"],
                    oddsportal_hash=hash_value,
                    oddsportal_url=url,
                    match_date=match.get("match_date", ""),
                    similarity=100.0,  # Direct URL = 100% confidence
                    mapping_method="v41.796_direct_url",
                ):
                    success_count += 1
            else:
                logger.warning(f"  ⚠️ 未找到哈希: {url}")

            # Rate limiting
            await asyncio.sleep(2)

    logger.info("=" * 70)
    logger.info(f"📊 处理完成:")
    logger.info(f"   - 处理: {processed} 场")
    logger.info(f"   - 成功: {success_count} 场")
    logger.info(f"   - 成功率: {success_count / processed * 100:.1f}%")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
