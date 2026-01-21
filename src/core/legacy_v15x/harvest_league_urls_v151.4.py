#!/usr/bin/env python3
"""
V151.4 西甲列表页批量抓哈希引擎

核心功能：
1. 直接访问 OddsPortal 西甲赛果列表页
2. 从列表页一次性提取所有比赛 URL（含哈希）
3. 批量写入 matches_mapping 表

优势：
- 避免搜索接口的混淆问题
- 列表页数据结构化，成功率接近 100%
- 无需点击，直接解析 HTML

Author: 高级性能优化架构师 (Staff Performance Architect)
Date: 2026-01-11
Version: V151.4 (List Page Harvesting)
"""

import asyncio
import logging
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urljoin

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# V29.0: 加载 .env 文件
from dotenv import load_dotenv

load_dotenv(override=True)

from playwright.async_api import async_playwright
import psycopg2

from src.config_unified import get_settings

# ============================================================================
# 配置
# ============================================================================

# OddsPortal 西甲赛果页 URL
LA_LIGA_RESULTS_URLS = {
    "latest": "https://www.oddsportal.com/football/spain/laliga/results/",
    "23-24": "https://www.oddsportal.com/football/spain/laliga-2023-2024/results/",
    "22-23": "https://www.oddsportal.com/football/spain/laliga-2022-2023/results/",
}

# 代理配置
PROXY_SERVER = "http://172.25.16.1:7890"

# ============================================================================
# 日志配置
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/harvest_league_urls.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# 数据库操作
# ============================================================================

def get_db_connection():
    """获取数据库连接"""
    settings = get_settings()
    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )

def fetch_fotmob_matches(league_name: str) -> list[dict[str, Any]]:
    """从 matches 表获取指定联赛的比赛

    Args:
        league_name: 联赛名称 (如 "La Liga")

    Returns:
        比赛列表
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            match_id as fotmob_id,
            home_team,
            away_team,
            match_date
        FROM matches
        WHERE league_name = %s
        ORDER BY match_date DESC
    """

    cursor.execute(query, (league_name,))
    columns = ["fotmob_id", "home_team", "away_team", "match_date"]

    matches = []
    for row in cursor.fetchall():
        matches.append(dict(zip(columns, row, strict=False)))

    cursor.close()
    conn.close()

    return matches

def match_urls_in_database() -> set:
    """获取数据库中已存在的 oddsportal_url 集合"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT oddsportal_url FROM matches_mapping WHERE oddsportal_url IS NOT NULL")
    urls = {row[0] for row in cursor.fetchall()}

    cursor.close()
    conn.close()

    return urls

def batch_insert_urls(match_url_pairs: list[dict[str, Any]]) -> int:
    """批量插入 URL 到 matches_mapping 表

    Args:
        match_url_pairs: [(fotmob_id, oddsportal_url, home_team, away_team, ...), ...]

    Returns:
        成功插入的记录数
    """
    if not match_url_pairs:
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()

    inserted_count = 0
    for pair in match_url_pairs:
        try:
            cursor.execute("""
                INSERT INTO matches_mapping
                (fotmob_id, home_team, away_team, league_name, oddsportal_url,
                 match_date, confidence, mapping_method, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fotmob_id) DO UPDATE SET
                    oddsportal_url = EXCLUDED.oddsportal_url,
                    mapping_method = EXCLUDED.mapping_method,
                    updated_at = NOW()
            """, (
                pair["fotmob_id"],
                pair["home_team"],
                pair["away_team"],
                pair["league_name"],
                pair["oddsportal_url"],
                pair.get("match_date"),
                0.95,  # 列表页置信度较高
                "semantic",  # V151.4: 使用有效枚举值
                "pending"
            ))
            inserted_count += 1
        except Exception as e:
            logger.warning(f"插入失败 {pair['fotmob_id']}: {e}")

    conn.commit()
    cursor.close()
    conn.close()

    return inserted_count

# ============================================================================
# 列表页爬取
# ============================================================================

async def fetch_league_results_page(
    url: str,
    proxy: str | None = None
) -> list[dict[str, Any]]:
    """从联赛赛果页抓取所有比赛 URL

    Args:
        url: 赛果页 URL
        proxy: 代理服务器

    Returns:
        [(fotmob_id, oddsportal_url, home_team, away_team), ...]
    """
    results = []

    logger.info(f"📄 正在访问: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": proxy} if proxy else None
        )
        page = await browser.new_page()

        try:
            # 访问赛果页
            await page.goto(url, wait_until="networkidle", timeout=60000)
            logger.info("✅ 页面加载完成")

            # V151.4: 更长等待时间让 JS 渲染完成
            await asyncio.sleep(5)

            # V151.4: 新版页面结构 - 直接提取所有包含哈希的链接
            # 新格式: /football/spain/laliga-2023-2024/{home}-{away}-{hash}/
            match_pattern = r"/football/[^/]+/[^/]+/[^/]+-[^/]+-([a-zA-Z0-9]{8,12})/"

            # 获取所有链接
            all_links = await page.locator("a").all()
            logger.info(f"🔗 页面总链接数: {len(all_links)}")

            # 过滤出比赛链接
            for link in all_links:
                try:
                    href = await link.get_attribute("href")
                    if not href:
                        continue

                    # 检查是否匹配比赛链接格式
                    hash_match = re.search(match_pattern, href)
                    if not hash_match:
                        continue

                    match_id = hash_match.group(1)
                    full_url = urljoin("https://www.oddsportal.com/", href)

                    # 从 URL 解析队名
                    # URL 格式: /football/spain/laliga-2023-2024/barcelona-rayo-vallecano-4A6T7YOu/
                    url_parts = href.strip("/").split("/")
                    if len(url_parts) >= 4:
                        match_part = url_parts[-1]  # barcelona-rayo-vallecano-4A6T7YOu
                        # 移除哈希部分
                        name_part = "-".join(match_part.split("-")[:-1])  # barcelona-rayo-vallecano
                        teams = name_part.split("-")
                        if len(teams) >= 2:
                            home_team = teams[0].replace("-", " ").title()
                            away_team = teams[1].replace("-", " ").title()
                        else:
                            home_team = ""
                            away_team = ""
                    else:
                        home_team = ""
                        away_team = ""

                    results.append({
                        "oddsportal_url": full_url,
                        "match_id": match_id,
                        "home_team": home_team,
                        "away_team": away_team,
                    })

                    logger.info(f"  🎯 {home_team} vs {away_team} → {match_id}")

                except Exception as e:
                    logger.warning(f"  ⚠️ 链接解析失败: {e}")
                    continue

            logger.info(f"✅ 提取到 {len(results)} 个比赛链接")

        finally:
            await browser.close()

    return results

def match_fotmob_with_oddsportal(
    fotmob_matches: list[dict[str, Any]],
    oddsportal_matches: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """将 FotMob 比赛与 OddsPortal URL 进行模糊匹配

    Args:
        fotmob_matches: FotMatches 表中的比赛
        oddsportal_matches: 从列表页抓取的比赛

    Returns:
        匹配成功的对: [(fotmob_id, oddsportal_url, home_team, away_team, ...), ...]
    """
    matched_pairs = []
    matched_urls = set()

    for op_match in oddsportal_matches:
        op_home = op_match["home_team"].lower().strip()
        op_away = op_match["away_team"].lower().strip()
        op_url = op_match["oddsportal_url"]

        # 如果 URL 已经匹配过，跳过
        if op_url in matched_urls:
            continue

        best_match = None
        best_score = 0

        for fm_match in fotmob_matches:
            fm_home = fm_match["home_team"].lower().strip()
            fm_away = fm_match["away_team"].lower().strip()

            # 简单匹配：两队名称都包含在 URL 中
            score = 0
            if op_home in fm_home or fm_home in op_home:
                score += 1
            if op_away in fm_away or fm_away in op_away:
                score += 1

            if score > best_score:
                best_score = score
                best_match = fm_match

        # 如果两队都匹配成功
        if best_match and best_score >= 2:
            matched_pairs.append({
                "fotmob_id": best_match["fotmob_id"],
                "home_team": best_match["home_team"],
                "away_team": best_match["away_team"],
                "league_name": "La Liga",
                "match_date": best_match.get("match_date"),
                "oddsportal_url": op_url,
            })
            matched_urls.add(op_url)

    return matched_pairs

# ============================================================================
# 主流程
# ============================================================================

async def main(league: str = "La Liga", dry_run: bool = False, limit: int | None = None):
    """主流程

    Args:
        league: 联赛名称 (默认: La Liga)
        dry_run: 干跑模式，不实际写入数据库
        limit: 限制处理数量
    """
    logger.info("=" * 70)
    logger.info("🚀 V151.4 列表页批量抓哈希引擎启动")
    logger.info("=" * 70)
    logger.info(f"目标联赛: {league}")
    logger.info(f"干跑模式: {dry_run}")

    if dry_run:
        logger.info("🔍 干跑模式 - 只验证流程，不写入数据库")

    # 步骤 1: 获取 FotMob 比赛列表
    logger.info("\n📋 步骤 1: 从 FotMob 获取比赛...")
    fotmob_matches = fetch_fotmob_matches(league)
    logger.info(f"✅ 找到 {len(fotmob_matches)} 场比赛")

    if limit:
        fotmob_matches = fotmob_matches[:limit]
        logger.info(f"📊 限制处理: {len(fotmob_matches)} 场")

    # 步骤 2: 从赛果页抓取 OddsPortal URL
    logger.info("\n🎯 步骤 2: 从赛果页抓取 OddsPortal URL...")

    all_oddsportal_matches = []
    for season_name, url in LA_LIGA_RESULTS_URLS.items():
        logger.info(f"\n  📅 处理赛季: {season_name}")
        season_matches = await fetch_league_results_page(url, proxy=PROXY_SERVER)
        all_oddsportal_matches.extend(season_matches)

    logger.info(f"\n✅ 总共抓取到 {len(all_oddsportal_matches)} 个 OddsPortal URL")

    # 步骤 3: 模糊匹配
    logger.info("\n🔗 步骤 3: 执行模糊匹配...")
    matched_pairs = match_fotmob_with_oddsportal(fotmob_matches, all_oddsportal_matches)
    logger.info(f"✅ 成功匹配 {len(matched_pairs)} 场比赛")

    # 步骤 4: 检查已存在的 URL
    logger.info("\n🔍 步骤 4: 检查已存在的 URL...")
    existing_urls = match_urls_in_database()
    new_pairs = [p for p in matched_pairs if p["oddsportal_url"] not in existing_urls]
    logger.info(f"✅ 过滤后待插入: {len(new_pairs)} 场")

    # 步骤 5: 批量插入
    if not dry_run:
        logger.info("\n💾 步骤 5: 批量插入数据库...")
        inserted_count = batch_insert_urls(new_pairs)
        logger.info(f"✅ 成功插入 {inserted_count} 条记录")
    else:
        logger.info("\n🔍 干跑模式 - 跳过数据库插入")
        logger.info(f"📊 将插入 {len(new_pairs)} 条记录")
        # 显示前 5 条预览
        for i, pair in enumerate(new_pairs[:5], 1):
            logger.info(f"  {i}. {pair['home_team']} vs {pair['away_team']}")
            logger.info(f"     URL: {pair['oddsportal_url']}")
        if len(new_pairs) > 5:
            logger.info(f"  ... 还有 {len(new_pairs) - 5} 条")

    # 总结
    logger.info("\n" + "=" * 70)
    logger.info("📊 V151.4 列表页抓取完成")
    logger.info("=" * 70)
    logger.info(f"联赛: {league}")
    logger.info(f"总抓取 URL: {len(all_oddsportal_matches)}")
    logger.info(f"成功匹配: {len(matched_pairs)}")
    if not dry_run:
        logger.info(f"新增记录: {len(new_pairs)}")
    logger.info(f"成功率: {len(matched_pairs)/max(len(fotmob_matches),1)*100:.1f}%")
    logger.info("=" * 70)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="V151.4 列表页批量抓哈希引擎")
    parser.add_argument("--league", type=str, default="La Liga",
                        help="联赛名称 (默认: La Liga)")
    parser.add_argument("--dry-run", action="store_true",
                        help="干跑模式，只验证不写入数据库")
    parser.add_argument("--limit", type=int, default=None,
                        help="限制处理数量")

    args = parser.parse_args()

    asyncio.run(main(league=args.league, dry_run=args.dry_run, limit=args.limit))
