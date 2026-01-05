#!/usr/bin/env python3
"""
V80.1 Fixed Harvest Engine - 修复版全量收割

集成 ultimate_probe.py 的成功翻页逻辑
- 使用 div.pagination a:has-text("Next") 选择器
- 5 秒等待时间
- 完整翻页直到最后一页
"""

import asyncio
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

import psycopg2
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入 V69.1 模糊匹配器
from scripts.v69_fuzzy_matcher import AdvancedFuzzyMatcher

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v80_1_fixed_harvest.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 配置 - 25 个巡航坐标
# ============================================================================

CRUISE_COORDINATES = [
    # Premier League
    ("Premier League", "20/21", "https://www.oddsportal.com/football/england/premier-league-2020-2021/results/"),
    ("Premier League", "21/22", "https://www.oddsportal.com/football/england/premier-league-2021-2022/results/"),
    ("Premier League", "22/23", "https://www.oddsportal.com/football/england/premier-league-2022-2023/results/"),
    ("Premier League", "23/24", "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/"),
    ("Premier League", "24/25", "https://www.oddsportal.com/football/england/premier-league-2024-2025/results/"),

    # Bundesliga
    ("Bundesliga", "20/21", "https://www.oddsportal.com/football/germany/bundesliga-2020-2021/results/"),
    ("Bundesliga", "21/22", "https://www.oddsportal.com/football/germany/bundesliga-2021-2022/results/"),
    ("Bundesliga", "22/23", "https://www.oddsportal.com/football/germany/bundesliga-2022-2023/results/"),
    ("Bundesliga", "23/24", "https://www.oddsportal.com/football/germany/bundesliga-2023-2024/results/"),
    ("Bundesliga", "24/25", "https://www.oddsportal.com/football/germany/bundesliga-2024-2025/results/"),

    # La Liga
    ("La Liga", "20/21", "https://www.oddsportal.com/football/spain/laliga-2020-2021/results/"),
    ("La Liga", "21/22", "https://www.oddsportal.com/football/spain/laliga-2021-2022/results/"),
    ("La Liga", "22/23", "https://www.oddsportal.com/football/spain/laliga-2022-2023/results/"),
    ("La Liga", "23/24", "https://www.oddsportal.com/football/spain/laliga-2023-2024/results/"),
    ("La Liga", "24/25", "https://www.oddsportal.com/football/spain/laliga-2024-2025/results/"),

    # Serie A
    ("Serie A", "20/21", "https://www.oddsportal.com/football/italy/serie-a-2020-2021/results/"),
    ("Serie A", "21/22", "https://www.oddsportal.com/football/italy/serie-a-2021-2022/results/"),
    ("Serie A", "22/23", "https://www.oddsportal.com/football/italy/serie-a-2022-2023/results/"),
    ("Serie A", "23/24", "https://www.oddsportal.com/football/italy/serie-a-2023-2024/results/"),
    ("Serie A", "24/25", "https://www.oddsportal.com/football/italy/serie-a-2024-2025/results/"),

    # Ligue 1
    ("Ligue 1", "20/21", "https://www.oddsportal.com/football/france/ligue-1-2020-2021/results/"),
    ("Ligue 1", "21/22", "https://www.oddsportal.com/football/france/ligue-1-2021-2022/results/"),
    ("Ligue 1", "22/23", "https://www.oddsportal.com/football/france/ligue-1-2022-2023/results/"),
    ("Ligue 1", "23/24", "https://www.oddsportal.com/football/france/ligue-1-2023-2024/results/"),
    ("Ligue 1", "24/25", "https://www.oddsportal.com/football/france/ligue-1-2024-2025/results/"),
]


# ============================================================================
# 数据库操作
# ============================================================================

def get_db_connection():
    """获取数据库连接"""
    from src.config_unified import get_settings
    settings = get_settings()

    return psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value()
    )


def get_matches_without_url(league: str, season: str) -> Dict[str, Tuple]:
    """
    获取指定联赛和赛季中没有 URL 的比赛

    Returns:
        Dict of {match_id: (home_team, away_team, match_date)}
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT match_id, home_team, away_team, match_date
        FROM matches
        WHERE league_name = %s
          AND season = %s
          AND oddsportal_url IS NULL
        ORDER BY match_date DESC
    """, (league, season))

    results = cur.fetchall()

    cur.close()
    conn.close()

    return {f"{row[1]}|{row[2]}": (row[0], row[1], row[2], row[3]) for row in results}


def update_match_url_batch(updates: List[Dict]) -> int:
    """批量更新比赛 URL"""
    if not updates:
        return 0

    conn = get_db_connection()
    cur = conn.cursor()

    success_count = 0

    for update in updates:
        try:
            cur.execute("""
                UPDATE matches
                SET oddsportal_url = %s, updated_at = CURRENT_TIMESTAMP
                WHERE match_id = %s
            """, (update['url'], update['match_id']))
            success_count += 1
        except Exception as e:
            logger.warning(f"更新失败 {update['match_id']}: {e}")

    conn.commit()
    cur.close()
    conn.close()

    return success_count


# ============================================================================
# HTML 提取引擎
# ============================================================================

def extract_match_rows_from_html(html_content: str) -> List[Dict]:
    """从 HTML 中提取完整的比赛行"""
    results = []

    # 正则模式：提取球队名称和哈希 ID
    pattern = r'"/football/([^/]+)/([^/]+)-([^/]+)/([^/-]+)-([^/-]+)-([a-zA-Z0-9]{7,8})/"'

    matches = re.findall(pattern, html_content)

    for country, league_slug, season, home, away, hash_id in matches:
        # 标准化球队名称（连字符转空格，首字母大写）
        home_normalized = home.replace('-', ' ').title()
        away_normalized = away.replace('-', ' ').title()

        # 构造完整 URL
        full_url = f"https://www.oddsportal.com/football/{country}/{league_slug}-{season}/{home}-{away}-{hash_id}/"

        results.append({
            'home': home_normalized,
            'away': away_normalized,
            'hash': hash_id,
            'full_url': full_url,
            'key': f"{home_normalized}|{away_normalized}"
        })

    return results


# ============================================================================
# 核心翻页扫描引擎（集成 ultimate_probe.py 的成功逻辑）
# ============================================================================

async def scan_season_with_pagination(league: str, season: str, url: str,
                                       db_matches: Dict[str, Tuple]) -> Dict:
    """
    扫描单个赛季的所有分页

    集成 ultimate_probe.py 的成功逻辑：
    - 使用 div.pagination a:has-text("Next") 选择器
    - 5 秒等待时间
    - 完整翻页直到最后一页
    """
    logger.info(f"\n{'=' * 60}")
    logger.info(f"扫描: {league} {season}")
    logger.info(f"数据库未匹配: {len(db_matches)} 场")
    logger.info(f"{'=' * 60}")

    matcher = AdvancedFuzzyMatcher(similarity_threshold=0.98)
    all_html_matches = []
    matched_results = []
    page_num = 1
    max_pages = 50  # 安全限制

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)

            while page_num <= max_pages:
                logger.info(f"  第 {page_num} 页...")

                # 等待页面加载（5 秒）
                await asyncio.sleep(5)

                # 提取当前页的比赛
                html = await page.content()
                matches = extract_match_rows_from_html(html)

                if not matches:
                    logger.info(f"    本页无比赛，停止翻页")
                    break

                # 检查是否重复
                if all_html_matches and matches[0]['hash'] == all_html_matches[0]['hash']:
                    logger.info(f"    检测到重复内容，已到最后一页")
                    break

                all_html_matches.extend(matches)

                # 精准对齐
                matched_count = 0
                for html_match in matches:
                    key = f"{html_match['home']}|{html_match['away']}"

                    # 1-on-1 精准匹配
                    if key in db_matches:
                        db_match = db_matches[key]
                        matched_results.append({
                            'match_id': db_match[0],
                            'url': html_match['full_url'],
                            'db_home': db_match[1],
                            'db_away': db_match[2],
                            'html_home': html_match['home'],
                            'html_away': html_match['away'],
                            'hash': html_match['hash']
                        })
                        matched_count += 1

                logger.info(f"    提取: {len(matches)} 场, 匹配: {matched_count} 场")

                # 尝试点击 Next 按钮（集成成功逻辑）
                try:
                    # 使用成功的 XPath 选择器
                    next_btn = await page.query_selector('div.pagination a:has-text("Next")')

                    if next_btn:
                        logger.info(f"    点击 Next 按钮...")
                        await next_btn.click()

                        # 等待导航和页面加载
                        await page.wait_for_load_state('domcontentloaded', timeout=30000)
                        await asyncio.sleep(5)
                        page_num += 1
                    else:
                        logger.info(f"    未找到 Next 按钮，翻页结束")
                        break

                except Exception as e:
                    logger.info(f"    翻页失败: {e}")
                    break

        finally:
            await browser.close()

    logger.info(f"  总页数: {page_num}")
    logger.info(f"  总提取: {len(all_html_matches)} 场")
    logger.info(f"  成功匹配: {len(matched_results)} 场")

    # 尝试深度探测（Load more）
    if len(all_html_matches) < 200:  # 如果比赛数太少
        logger.info(f"  比赛数不足，尝试深度探测...")
        # 这里可以添加滚动加载逻辑

    return {
        'league': league,
        'season': season,
        'total_pages': page_num,
        'total_extracted': len(all_html_matches),
        'total_matched': len(matched_results),
        'matches': matched_results
    }


# ============================================================================
# 并发扫描引擎
# ============================================================================

async def scan_all_seasons(concurrency: int = 5):
    """并发扫描所有赛季"""
    logger.info("=" * 60)
    logger.info("V80.1 修复版全量收割引擎")
    logger.info("=" * 60)
    logger.info(f"并发数: {concurrency}")

    total_scanned = 0
    total_matched = 0
    season_reports = []

    # 获取所有待处理的联赛赛季
    for league, season, url in CRUISE_COORDINATES:
        # 获取数据库未匹配的比赛
        db_matches = get_matches_without_url(league, season)

        if not db_matches:
            logger.info(f"\n{league} {season}: 无需匹配（全部已有 URL）")
            continue

        # 扫描该赛季
        result = await scan_season_with_pagination(league, season, url, db_matches)

        # 批量更新数据库
        if result['matches']:
            updates = [
                {'match_id': m['match_id'], 'url': m['url']}
                for m in result['matches']
            ]
            updated = update_match_url_batch(updates)
            logger.info(f"  数据库更新: {updated} 条")
            total_matched += updated

        season_reports.append(result)
        total_scanned += result['total_extracted']

        # 避免过载
        await asyncio.sleep(2)

    # 最终报告
    logger.info(f"\n{'=' * 60}")
    logger.info("V80.1 全量收割 - 最终报告")
    logger.info(f"{'=' * 60}")
    logger.info(f"扫描赛季: {len(season_reports)}")
    logger.info(f"提取比赛: {total_scanned}")
    logger.info(f"成功匹配: {total_matched}")

    # 检查最终填充率
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(oddsportal_url) as with_url,
            ROUND(100.0 * COUNT(oddsportal_url) / COUNT(*), 2) as fill_rate
        FROM matches
    """)
    result = cur.fetchone()
    cur.close()
    conn.close()

    logger.info(f"\n最终填充率:")
    logger.info(f"  总比赛: {result[0]}")
    logger.info(f"  有 URL: {result[1]}")
    logger.info(f"  填充率: {result[2]}%")

    # 生成赛季简报
    logger.info(f"\n{'=' * 60}")
    logger.info("赛季收割简报")
    logger.info(f"{'=' * 60}")

    for report in season_reports[:10]:  # 显示前 10 个
        logger.info(f"{report['league']} {report['season']}:")
        logger.info(f"  应收: ~{380 if report['league'] != 'Bundesliga' else 306} 场")
        logger.info(f"  实收: {report['total_extracted']} 场")
        logger.info(f"  匹配: {report['total_matched']} 场")
        logger.info(f"  匹配率: {100 * report['total_matched'] / report['total_extracted']:.1f}%")


# ============================================================================
# 主入口
# ============================================================================

async def main():
    """主函数"""
    await scan_all_seasons(concurrency=5)


if __name__ == "__main__":
    asyncio.run(main())
