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
import re
import sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# V29.0: 加载 .env 文件
from dotenv import load_dotenv
load_dotenv(override=True)

import psycopg2
from playwright.async_api import async_playwright, Page, Browser
from src.config_unified import get_settings
from thefuzz import fuzz

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
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/harvest_league_urls.log'),
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

def fetch_fotmob_matches(league_name: str) -> List[Dict[str, Any]]:
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
    columns = ['fotmob_id', 'home_team', 'away_team', 'match_date']

    matches = []
    for row in cursor.fetchall():
        matches.append(dict(zip(columns, row)))

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


# ============================================================================
# V32.2: 智能 URL 队名解析 (修复多词队名 Bug)
# ============================================================================

@lru_cache(maxsize=10)
def get_league_team_names(league_name: str) -> Dict[str, str]:
    """从数据库获取联赛的所有合法队名

    Args:
        league_name: 联赛名称

    Returns:
        队名字典 {标准名称: URL slug}
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 获取联赛中的所有唯一队名
    cursor.execute("""
        SELECT DISTINCT home_team FROM matches
        WHERE league_name = %s
        UNION
        SELECT DISTINCT away_team FROM matches
        WHERE league_name = %s
        ORDER BY 1
    """, (league_name, league_name))

    team_names = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    # 构建队名到 URL slug 的映射
    team_slug_map = {}
    for team in team_names:
        # V32.2: 使用 team_name_to_slug 函数处理特殊映射
        slug = team_name_to_slug(team)
        team_slug_map[team] = slug

    return team_slug_map


def team_name_to_slug(team_name: str) -> str:
    """将队名转换为 URL slug 格式

    Args:
        team_name: 队名 (如 "Real Sociedad")

    Returns:
        URL slug (如 "real-sociedad")

    特殊处理西甲常见缩写:
    - Real Sociedad → real-sociedad
    - Atletico Madrid → atl-madrid
    - Athletic Bilbao → ath-bilbao
    """
    # 西甲特殊缩写映射
    special_mappings = {
        "Atletico Madrid": "atl-madrid",
        "Athletic Bilbao": "ath-bilbao",
        "Athletic Club": "ath-bilbao",
        "Real Betis": "betis",  # URL 常省略 'Real'
    }

    if team_name in special_mappings:
        return special_mappings[team_name]

    # 标准转换
    slug = team_name.lower()
    # 空格替换为连字符
    slug = slug.replace(' ', '-')
    # 移除特殊字符
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    # 移除多余连字符
    slug = re.sub(r'-+', '-', slug).strip('-')

    return slug if slug else team_name.lower()


def parse_match_url_with_league_teams(
    url: str,
    league_name: str
) -> Tuple[str, str, float]:
    """V32.2: 智能解析比赛 URL，支持多词队名

    Args:
        url: OddsPortal 比赛 URL
        league_name: 联赛名称

    Returns:
        (home_team, away_team, confidence) 元组
        confidence: 匹配置信度 (0-1)

    算法:
    1. 从 URL 提取 slug 部分 (如 "real-sociedad-almeria")
    2. 获取联赛的所有合法队名
    3. 将队名转换为 slug 格式
    4. 使用 greedy matching 从左到右匹配队名
    5. 返回匹配到的队名和置信度
    """
    # 获取联赛队名
    team_slug_map = get_league_team_names(league_name)

    if not team_slug_map:
        # 回退到简单解析
        return parse_match_url_simple(url)

    # 提取 URL slug
    url_parts = url.strip('/').split('/')
    if len(url_parts) < 2:
        return ("", "", 0.0)

    # 最后部分是 match-{home}-{away}-{hash}
    match_part = url_parts[-1]

    # 移除哈希部分 (最后 8-12 位字母数字)
    match_part = re.sub(r'-[a-zA-Z0-9]{8,12}$', '', match_part)

    # 分割成 slug 列表
    slug_parts = match_part.split('-')

    # 使用 greedy matching 找到最佳队名分割
    best_home = ""
    best_away = ""
    best_score = 0.0

    # 尝试所有可能的分割点
    for split_point in range(1, len(slug_parts)):
        home_slug = '-'.join(slug_parts[:split_point])
        away_slug = '-'.join(slug_parts[split_point:])

        # 匹配主队
        home_match = None
        home_score = 0.0
        for team_name, team_slug in team_slug_map.items():
            # 完全匹配
            if home_slug == team_slug:
                home_match = team_name
                home_score = 1.0
                break
            # 模糊匹配
            score = fuzz.ratio(home_slug, team_slug) / 100.0
            if score > home_score and score > 0.7:  # 70% 相似度阈值
                home_match = team_name
                home_score = score

        # 匹配客队
        away_match = None
        away_score = 0.0
        for team_name, team_slug in team_slug_map.items():
            # 完全匹配
            if away_slug == team_slug:
                away_match = team_name
                away_score = 1.0
                break
            # 模糊匹配
            score = fuzz.ratio(away_slug, team_slug) / 100.0
            if score > away_score and score > 0.7:  # 70% 相似度阈值
                away_match = team_name
                away_score = score

        # 计算总置信度
        if home_match and away_match:
            total_score = (home_score + away_score) / 2.0
            if total_score > best_score:
                best_score = total_score
                best_home = home_match
                best_away = away_match

    if best_home and best_away:
        return (best_home, best_away, best_score)
    else:
        # 回退到简单解析
        return parse_match_url_simple(url)


def parse_match_url_simple(url: str) -> Tuple[str, str, float]:
    """简单 URL 解析（回退方案）

    Args:
        url: OddsPortal 比赛 URL

    Returns:
        (home_team, away_team, confidence) 元组
    """
    url_parts = url.strip('/').split('/')
    if len(url_parts) >= 2:
        match_part = url_parts[-1]
        # 移除哈希部分
        name_part = re.sub(r'-[a-zA-Z0-9]{8,12}$', '', match_part)
        teams = name_part.split('-')
        if len(teams) >= 2:
            # 标题格式化
            home_team = ' '.join(teams[0].split()).title()
            away_team = ' '.join(teams[1].split()).title()
            return (home_team, away_team, 0.5)  # 低置信度
    return ("", "", 0.0)


# ============================================================================

def batch_insert_urls(match_url_pairs: List[Dict[str, Any]]) -> int:
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
                pair['fotmob_id'],
                pair['home_team'],
                pair['away_team'],
                pair['league_name'],
                pair['oddsportal_url'],
                pair.get('match_date'),
                0.95,  # 列表页置信度较高
                'semantic',  # V151.4: 使用有效枚举值
                'pending'
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
    proxy: Optional[str] = None,
    league_name: str = "La Liga"
) -> List[Dict[str, Any]]:
    """V32.2: 从联赛赛果页抓取所有比赛 URL（智能队名解析）

    Args:
        url: 赛果页 URL
        proxy: 代理服务器
        league_name: 联赛名称（用于队名匹配）

    Returns:
        [(fotmob_id, oddsportal_url, home_team, away_team), ...]
    """
    results = []

    logger.info(f"📄 正在访问: {url}")
    logger.info(f"🏆 联赛: {league_name}")

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
            match_pattern = r'/football/[^/]+/[^/]+/[^/]+-[^/]+-([a-zA-Z0-9]{8,12})/'

            # 获取所有链接
            all_links = await page.locator('a').all()
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

                    # V32.2: 使用智能队名解析（支持多词队名）
                    home_team, away_team, confidence = parse_match_url_with_league_teams(
                        full_url,
                        league_name
                    )

                    if not home_team or not away_team:
                        # 智能解析失败，跳过
                        logger.warning(f"  ⚠️ 无法解析队名: {full_url}")
                        continue

                    results.append({
                        "oddsportal_url": full_url,
                        "match_id": match_id,
                        "home_team": home_team,
                        "away_team": away_team,
                        "confidence": confidence,  # V32.2: 添加置信度
                    })

                    logger.info(f"  🎯 {home_team} vs {away_team} → {match_id} (置信度: {confidence:.2f})")

                except Exception as e:
                    logger.warning(f"  ⚠️ 链接解析失败: {e}")
                    continue

            logger.info(f"✅ 提取到 {len(results)} 个比赛链接")

        finally:
            await browser.close()

    return results

def match_fotmob_with_oddsportal(
    fotmob_matches: List[Dict[str, Any]],
    oddsportal_matches: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
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
        op_home = op_match['home_team'].lower().strip()
        op_away = op_match['away_team'].lower().strip()
        op_url = op_match['oddsportal_url']

        # 如果 URL 已经匹配过，跳过
        if op_url in matched_urls:
            continue

        best_match = None
        best_score = 0

        for fm_match in fotmob_matches:
            fm_home = fm_match['home_team'].lower().strip()
            fm_away = fm_match['away_team'].lower().strip()

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
                "fotmob_id": best_match['fotmob_id'],
                "home_team": best_match['home_team'],
                "away_team": best_match['away_team'],
                "league_name": "La Liga",
                "match_date": best_match.get('match_date'),
                "oddsportal_url": op_url,
            })
            matched_urls.add(op_url)

    return matched_pairs

# ============================================================================
# 主流程
# ============================================================================

async def main(league: str = "La Liga", dry_run: bool = False, limit: Optional[int] = None):
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
    new_pairs = [p for p in matched_pairs if p['oddsportal_url'] not in existing_urls]
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
    parser.add_argument('--league', type=str, default='La Liga',
                        help='联赛名称 (默认: La Liga)')
    parser.add_argument('--dry-run', action='store_true',
                        help='干跑模式，只验证不写入数据库')
    parser.add_argument('--limit', type=int, default=None,
                        help='限制处理数量')

    args = parser.parse_args()

    asyncio.run(main(league=args.league, dry_run=args.dry_run, limit=args.limit))
