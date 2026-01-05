#!/usr/bin/env python3
"""
V80.0 地毯式收割引擎 - 翻页扫描方案

核心思路：
1. 访问每个联赛的每个赛季 Results 页面
2. 逐页点击"Next"按钮翻页
3. 提取每页的所有比赛 URL
4. 1-on-1 精准对齐到数据库
"""

import asyncio
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional

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
        logging.FileHandler('logs/v80_pagination.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 配置
# ============================================================================

# 25 个巡航坐标
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

    # 返回字典，key 为 home_team|away_team
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
    """
    从 HTML 中提取完整的比赛行

    Returns:
        List of {'home': str, 'away': str, 'hash': str, 'full_url': str}
    """
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
# 第一阶段：翻页逻辑探测
# ============================================================================

async def probe_pagination(league: str, season: str, url: str):
    """
    探测翻页逻辑

    Args:
        league: 联赛名称
        season: 赛季
        url: Results 页面 URL
    """
    logger.info("=" * 60)
    logger.info(f"V80.0 第一阶段：翻页逻辑探测")
    logger.info(f"目标: {league} {season}")
    logger.info("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 使用有头模式便于观察
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)

            all_matches = []
            page_num = 1
            max_pages = 20  # 安全限制

            while page_num <= max_pages:
                logger.info(f"\n--- 第 {page_num} 页 ---")

                # 提取当前页的比赛
                html = await page.content()
                matches = extract_match_rows_from_html(html)

                logger.info(f"  提取到 {len(matches)} 个比赛")

                if not matches:
                    logger.info(f"  本页无比赛，停止翻页")
                    break

                # 检查是否已经重复（到达最后一页）
                if all_matches and matches[0]['hash'] == all_matches[0]['hash']:
                    logger.info(f"  检测到重复内容，已到最后一页")
                    break

                all_matches.extend(matches)

                # 尝试查找并点击"Next"按钮
                next_selectors = [
                    'a.pagination-next:has-text("Next")',
                    'a.pagination-next',
                    'li.next a',
                    'a[aria-label="Next"]',
                    '//a[contains(text(), "Next")]',
                    '//a[contains(@class, "next")]',
                ]

                next_found = False
                for selector in next_selectors:
                    try:
                        if selector.startswith('//'):
                            # XPath selector
                            element = await page.wait_for_selector(f"xpath={selector}", timeout=5000)
                        else:
                            element = await page.wait_for_selector(selector, timeout=5000)

                        if element:
                            logger.info(f"  找到 Next 按钮: {selector}")
                            await element.click()
                            await asyncio.sleep(2)  # 等待页面加载
                            next_found = True
                            page_num += 1
                            break
                    except:
                        continue

                if not next_found:
                    logger.info(f"  未找到 Next 按钮，停止翻页")
                    break

            logger.info(f"\n{'=' * 60}")
            logger.info(f"翻页探测完成")
            logger.info(f"{'=' * 60}")
            logger.info(f"总页数: {page_num}")
            logger.info(f"总提取: {len(all_matches)} 个比赛")
            logger.info(f"预期: 380 场（英超）或 306 场（德甲）")
            logger.info(f"覆盖率: {100 * len(all_matches) / 380:.1f}%")

            # 保存结果用于验证
            with open('audit_temp/v80_pagination_probe.json', 'w') as f:
                import json
                json.dump({
                    'league': league,
                    'season': season,
                    'total_pages': page_num,
                    'total_matches': len(all_matches),
                    'matches': all_matches[:10]  # 保存前 10 条
                }, f, indent=2)

        finally:
            await browser.close()


# ============================================================================
# 第二阶段：全量翻页扫描
# ============================================================================

async def scan_season_with_pagination(league: str, season: str, url: str,
                                       db_matches: Dict[str, Tuple]) -> Dict:
    """
    扫描单个赛季的所有分页

    Args:
        league: 联赛名称
        season: 赛季
        url: Results 页面 URL
        db_matches: 数据库未匹配的比赛

    Returns:
        Dict of 扫描结果
    """
    logger.info(f"\n扫描: {league} {season}")
    logger.info(f"  数据库未匹配: {len(db_matches)} 场")

    matcher = AdvancedFuzzyMatcher(similarity_threshold=0.98)
    all_html_matches = []
    matched_results = []
    page_num = 1
    max_pages = 30  # 安全限制

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        page = await context.new_page()

        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(2)

            while page_num <= max_pages:
                # 提取当前页的比赛
                html = await page.content()
                matches = extract_match_rows_from_html(html)

                if not matches:
                    break

                # 检查是否重复
                if all_html_matches and matches[0]['hash'] == all_html_matches[0]['hash']:
                    break

                all_html_matches.extend(matches)

                # 精准对齐
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

                # 尝试翻页
                try:
                    next_btn = await page.wait_for_selector('a.pagination-next, a[aria-label="Next"]', timeout=3000)
                    if next_btn:
                        await next_btn.click()
                        await asyncio.sleep(2)
                        page_num += 1
                except:
                    break

        finally:
            await browser.close()

    logger.info(f"  总页数: {page_num}")
    logger.info(f"  提取比赛: {len(all_html_matches)}")
    logger.info(f"  成功匹配: {len(matched_results)}")

    return {
        'league': league,
        'season': season,
        'total_pages': page_num,
        'total_extracted': len(all_html_matches),
        'total_matched': len(matched_results),
        'matches': matched_results
    }


# ============================================================================
# 主引擎
# ============================================================================

async def main():
    """主函数"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--probe':
        # 第一阶段：翻页逻辑探测
        await probe_pagination("Premier League", "23/24",
                              "https://www.oddsportal.com/football/england/premier-league-2023-2024/results/")
    else:
        # 第二阶段：全量扫描
        logger.info("=" * 60)
        logger.info("V80.0 地毯式收割引擎 - 全量扫描")
        logger.info("=" * 60)

        total_scanned = 0
        total_matched = 0
        season_reports = []

        for league, season, url in CRUISE_COORDINATES:
            # 获取数据库未匹配的比赛
            db_matches = get_matches_without_url(league, season)

            if not db_matches:
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
        logger.info("V80.0 地毯式收割 - 最终报告")
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


if __name__ == "__main__":
    asyncio.run(main())
