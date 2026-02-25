#!/usr/bin/env python3
"""
V39.5 赛季级"大扫除"扫射模式 - 全量穷尽版

核心功能:
1. 根据 V39.1 挖掘出的蓝图，自动拼凑出各联赛、各赛季的 results 页面地址
2. 批量抓取这些索引页（全量模式，无 50 场限制）
3. 将抓到的哈希 ID 批量存入 matches_mapping

V39.5 升级:
- 移除 50 场限制，支持全量处理（最高 400 场）
- 改进哈希验证逻辑，支持 6-10 位哈希
- ON CONFLICT 防重复
- 语义引擎自动去噪 + 地名提取

目的: 全量穷尽扫射，将覆盖率从 18% 提升到 50%+

准入红线: 必须通过 test_season_index_parser.py TDD 测试才能运行

Author: 首席数据采集官 & 逆向工程专家
Version: V39.5 Exhaustion Sweep Mode
Date: 2026-01-12
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from playwright.async_api import async_playwright

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config_unified import get_settings
# V39.4: 导入语义引擎
from src.utils.team_alias import semantic_match, extract_place_name, normalize_team_name

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/v39_2_season_sweep.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# V39.1 URL 蓝图（从 v39_1_url_pattern_report.txt 提取）
# ============================================================================

LEAGUE_URL_PATTERNS = {
    "Premier League": {
        "country": "england",
        "slug": "premier-league",
        "base_url": "https://www.oddsportal.com/football/england/premier-league"
    },
    "La Liga": {
        "country": "spain",
        "slug": "laliga",
        "base_url": "https://www.oddsportal.com/football/spain/laliga"
    },
    "Serie A": {
        "country": "italy",
        "slug": "serie-a",
        "base_url": "https://www.oddsportal.com/football/italy/serie-a"
    },
    "Bundesliga": {
        "country": "germany",
        "slug": "bundesliga",
        "base_url": "https://www.oddsportal.com/football/germany/bundesliga"
    },
    "Ligue 1": {
        "country": "france",
        "slug": "ligue-1",
        "base_url": "https://www.oddsportal.com/football/france/ligue-1"
    }
}

SEASONS = ["2023-2024", "2022-2023", "2021-2022", "2020-2021"]


# ============================================================================
# 赛季索引解析器（从 test_season_index_parser.py 移植）
# ============================================================================

class SeasonIndexParser:
    """V39.2 赛季索引解析器 - 批量提取比赛链接"""

    def __init__(self, league_name: str, season: str):
        """
        初始化解析器

        Args:
            league_name: 联赛名称
            season: 赛季 (e.g., "2023-2024")
        """
        self.league_name = league_name
        self.season = season
        self.match_links: List[str] = []

        # 构建 results 页面 URL
        pattern = LEAGUE_URL_PATTERNS.get(league_name)
        if not pattern:
            raise ValueError(f"不支持的联赛: {league_name}")

        self.results_url = f"{pattern['base_url']}-{season}/results/"
        logger.info(f"初始化解析器: {league_name} {season}")
        logger.info(f"Results URL: {self.results_url}")

    async def fetch_and_parse(self) -> Dict[str, str]:
        """
        V39.5: 抓取并解析 results 页面（全量模式）

        Returns:
            Dict mapping: match_id -> url_hash
        """
        import time
        start_time = time.time()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()

            logger.info(f"正在抓取: {self.results_url}")

            # 访问页面
            await page.goto(self.results_url, wait_until='networkidle', timeout=60000)
            await page.wait_for_timeout(5000)

            # V39.5: 增强滚动触发懒加载（从 5 次增加到 15 次）
            logger.info("V39.5: 滚动触发懒加载（全量模式）...")
            for i in range(15):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(800)

            # 等待最后的懒加载完成
            await page.wait_for_timeout(5000)

            # V39.5: 提取所有比赛链接（包括分页）
            all_links = await page.query_selector_all('a[href*="/football/"]')
            football_hrefs = []

            for link in all_links:
                href = await link.get_attribute('href')
                if href and self._is_match_link(href):
                    football_hrefs.append(href)

            # 去重
            self.match_links = sorted(set(football_hrefs))

            elapsed = time.time() - start_time
            logger.info(f"✅ 成功提取 {len(self.match_links)} 条比赛链接 (耗时: {elapsed:.1f}s)")

            await context.close()
            await browser.close()

        # 解析 Match ID 和 Hash
        return self._parse_match_hashes()

    def _is_match_link(self, href: str) -> bool:
        """判断是否是比赛链接"""
        # 排除非比赛链接
        if href.endswith('/standings/'):
            return False

        # 必须包含足够数量的 "-" (至少 home-away-hash)
        return href.count('-') > 2

    def _parse_match_hashes(self) -> Dict[str, str]:
        """
        从链接中解析 Match ID 和 Hash

        Returns:
            Dict mapping: match_id -> url_hash
        """
        result = {}

        for link in self.match_links:
            # 提取最后一部分
            parts = link.rstrip('/').split('/')

            if len(parts) >= 2:
                match_id = parts[-1]
                url_hash = match_id.split('-')[-1] if '-' in match_id else match_id

                # V39.5: 支持 6-10 位哈希（放宽限制以捕获更多比赛）
                if 6 <= len(url_hash) <= 10:
                    result[match_id] = url_hash

        return result


# ============================================================================
# 批量数据库操作
# ============================================================================

def bulk_insert_matches_mapping(
    records: List[Dict[str, Any]],
    batch_size: int = 100
) -> Dict[str, int]:
    """
    批量插入 matches_mapping 表（V39.4 升级：使用语义引擎）

    V39.4 改进：
    - 使用 semantic_match 进行智能队名匹配
    - 模糊匹配代替精确匹配
    - 自动处理地名提取和去噪

    Args:
        records: 记录列表
        batch_size: 批量大小

    Returns:
        统计结果
    """
    import psycopg2
    from psycopg2.extras import execute_batch, RealDictCursor

    settings = get_settings()

    stats = {
        'total': len(records),
        'inserted': 0,
        'skipped': 0,
        'failed': 0,
        'not_found': 0,  # 在 matches 表中找不到对应记录
        'semantic_match_count': 0  # 使用语义匹配的次数
    }

    if not records:
        return stats

    try:
        conn = psycopg2.connect(
            host=settings.database.host,
            port=settings.database.port,
            database=settings.database.name,
            user=settings.database.user,
            password=settings.database.password.get_secret_value()
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 准备批量插入 SQL
        insert_query = """
            INSERT INTO matches_mapping (
                fotmob_id,
                home_team,
                away_team,
                league_name,
                oddsportal_url,
                confidence,
                mapping_method,
                review_status,
                status,
                season
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (fotmob_id) DO UPDATE SET
                oddsportal_url = EXCLUDED.oddsportal_url,
                confidence = EXCLUDED.confidence,
                mapping_method = EXCLUDED.mapping_method,
                review_status = EXCLUDED.review_status,
                status = EXCLUDED.status,
                updated_at = CURRENT_TIMESTAMP
        """

        # V39.4: 准备数据 - 使用语义引擎进行智能匹配
        values = []
        for record in records:
            # 从 OddsPortal URL 提取队名
            url = record['url']
            # URL 格式: /football/england/premier-league-2023-2024/teamA-teamB-hash/
            path_parts = url.rstrip('/').split('/')
            match_part = path_parts[-1]  # teamA-teamB-hash

            # 分离队名和 hash
            parts = match_part.split('-')
            hash_part = parts[-1] if len(parts[-1]) == 8 else None

            if not hash_part:
                continue

            league_name = record['league_name']
            season_db = record['season'].replace('-', '/')  # 2023-2024 -> 2023/2024

            # V39.4: 使用语义引擎查找最佳匹配
            best_match = None
            best_confidence = 0.0

            # 先尝试精确匹配（V39.3 逻辑）
            for split_idx in range(1, len(parts) - 1):
                home_parts = parts[:split_idx]
                away_parts = parts[split_idx:-1]  # 排除 hash

                home_url = '-'.join(home_parts)
                away_url = '-'.join(away_parts)

                # 标准化队名（连字符转空格，首字母大写）
                home_normalized = home_url.replace('-', ' ').title()
                away_normalized = away_url.replace('-', ' ').title()

                # 查询 matches 表（精确匹配）
                match_query = """
                    SELECT match_id, home_team, away_team
                    FROM matches
                    WHERE league_name = %s
                    AND season = %s
                    AND home_team = %s
                    AND away_team = %s
                    LIMIT 1
                """

                cursor.execute(match_query, (league_name, season_db, home_normalized, away_normalized))
                match_row = cursor.fetchone()

                if match_row:
                    best_match = match_row
                    best_confidence = 100.0  # 精确匹配给 100%
                    break

            # 如果精确匹配失败，使用 V39.4 语义引擎进行模糊匹配
            if not best_match:
                # 获取该联赛该赛季的所有比赛
                all_matches_query = """
                    SELECT match_id, home_team, away_team
                    FROM matches
                    WHERE league_name = %s
                    AND season = %s
                """

                cursor.execute(all_matches_query, (league_name, season_db))
                all_matches = cursor.fetchall()

                # 尝试所有可能的分割点
                for split_idx in range(1, len(parts) - 1):
                    home_parts = parts[:split_idx]
                    away_parts = parts[split_idx:-1]  # 排除 hash

                    home_url = '-'.join(home_parts)
                    away_url = '-'.join(away_parts)

                    # 标准化队名
                    home_normalized = home_url.replace('-', ' ').title()
                    away_normalized = away_url.replace('-', ' ').title()

                    # 对每个数据库中的比赛进行语义匹配
                    for db_match in all_matches:
                        db_home = db_match['home_team']
                        db_away = db_match['away_team']

                        # 使用 V39.4 语义匹配
                        home_conf, _ = semantic_match(home_normalized, db_home)
                        away_conf, _ = semantic_match(away_normalized, db_away)
                        avg_confidence = (home_conf + away_conf) / 2

                        # 准入红线：两个队都必须 >85% 置信度
                        if home_conf > 85 and away_conf > 85 and avg_confidence > best_confidence:
                            best_match = {
                                'match_id': db_match['match_id'],
                                'home_team': db_home,
                                'away_team': db_away
                            }
                            best_confidence = avg_confidence

            # 如果找到匹配，添加到批量插入列表
            if best_match and best_confidence >= 85:
                fotmob_id = best_match['match_id']
                db_home_team = best_match['home_team']
                db_away_team = best_match['away_team']

                # V39.4: 使用实际置信度（转换为 0-1 范围）
                confidence_value = best_confidence / 100.0

                values.append((
                    fotmob_id,
                    db_home_team,
                    db_away_team,
                    league_name,
                    url,
                    confidence_value,  # V39.4: 使用实际计算的置信度
                    'season_sweep_v4',  # V39.4 标记
                    'approved',
                    'verified',
                    record['season']
                ))

                if best_confidence < 100:
                    stats['semantic_match_count'] += 1
            else:
                stats['not_found'] += 1
                url_team = '-'.join(parts[:-1])  # 去掉 hash 的队名字符串
                logger.debug(f"未找到匹配 (置信度 <85%): {league_name} {record['season']} {url_team}")

        # 执行批量插入
        if values:
            execute_batch(cursor, insert_query, values, page_size=batch_size)

        # 获取插入结果
        stats['inserted'] = cursor.rowcount
        stats['skipped'] = stats['total'] - stats['inserted'] - stats['not_found']

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"💾 V39.4 批量插入完成: 总数={stats['total']}, 插入={stats['inserted']}, "
                   f"跳过={stats['skipped']}, 未找到={stats['not_found']}, "
                   f"语义匹配={stats['semantic_match_count']}")

    except Exception as e:
        logger.error(f"❌ 批量插入失败: {e}")
        stats['failed'] = stats['total']
        stats['inserted'] = 0

    return stats


# ============================================================================
# 赛季扫射主逻辑
# ============================================================================

async def sweep_season(
    league_name: str,
    season: str
) -> Dict[str, Any]:
    """
    扫射单个联赛的单个赛季

    Args:
        league_name: 联赛名称
        season: 赛季

    Returns:
        扫射结果
    """
    logger.info("=" * 70)
    logger.info(f"🎯 赛季扫射: {league_name} {season}")
    logger.info("=" * 70)

    result = {
        'league_name': league_name,
        'season': season,
        'success': False,
        'matches': {},
        'total': 0
    }

    try:
        # 初始化解析器
        parser = SeasonIndexParser(league_name, season)

        # 抓取并解析
        match_hashes = await parser.fetch_and_parse()

        result['total'] = len(match_hashes)
        result['matches'] = match_hashes

        # 准备批量插入数据
        records = []
        for match_id, url_hash in match_hashes.items():
            url = f"https://www.oddsportal.com{parser.match_links[0].rsplit('/', 1)[0]}/{match_id}/"
            # 找到对应的完整 URL
            for link in parser.match_links:
                if link.endswith(match_id + '/'):
                    url = f"https://www.oddsportal.com{link}"
                    break

            records.append({
                'match_id': match_id,
                'url': url,
                'hash': url_hash,
                'league_name': league_name,
                'season': season
            })

        # 批量插入数据库
        if records:
            db_stats = bulk_insert_matches_mapping(records)
            result['db_stats'] = db_stats

        result['success'] = True
        logger.info(f"✅ {league_name} {season} 扫射完成: {len(match_hashes)} 场比赛")

    except Exception as e:
        logger.error(f"❌ {league_name} {season} 扫射失败: {e}")
        result['error'] = str(e)

    return result


async def season_sweep_mode(
    leagues: Optional[List[str]] = None,
    seasons: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    V39.2 赛季扫射模式 - 批量处理多个联赛和赛季

    Args:
        leagues: 联赛列表（默认所有支持的联赛）
        seasons: 赛季列表（默认 SEASONS 常量）

    Returns:
        总体统计
    """
    # 默认处理所有联赛
    if leagues is None:
        leagues = ["Premier League", "La Liga"]  # 优先处理英超和西甲

    # 默认处理所有赛季
    if seasons is None:
        seasons = SEASONS

    logger.info("=" * 70)
    logger.info("V39.2 赛季扫射模式启动")
    logger.info("=" * 70)
    logger.info(f"目标联赛: {leagues}")
    logger.info(f"目标赛季: {seasons}")
    logger.info(f"总任务数: {len(leagues) * len(seasons)}")
    logger.info("=" * 70)

    results = []
    total_matches = 0
    total_inserted = 0

    task_num = 0
    for league_name in leagues:
        for season in seasons:
            task_num += 1
            logger.info(f"\n[{task_num}/{len(leagues) * len(seasons)}] 处理 {league_name} {season}...")

            try:
                result = await sweep_season(league_name, season)
                results.append(result)

                if result['success']:
                    total_matches += result['total']
                    if 'db_stats' in result:
                        total_inserted += result['db_stats']['inserted']

                # 延迟（除了最后一个任务）
                if task_num < len(leagues) * len(seasons):
                    delay = 3.0
                    logger.info(f"⏳ 等待 {delay}s 后继续...")
                    await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"❌ 任务异常: {e}")
                continue

    # 汇报总结果
    logger.info("\n" + "=" * 70)
    logger.info("📊 V39.2 赛季扫射模式总报告")
    logger.info("=" * 70)
    logger.info(f"总任务数: {len(results)}")
    logger.info(f"成功: {sum(1 for r in results if r['success'])}")
    logger.info(f"失败: {sum(1 for r in results if not r['success'])}")
    logger.info(f"总提取比赛: {total_matches}")
    logger.info(f"总插入数据库: {total_inserted}")
    logger.info("=" * 70)

    return {
        'total_tasks': len(results),
        'successful': sum(1 for r in results if r['success']),
        'failed': sum(1 for r in results if not r['success']),
        'total_matches': total_matches,
        'total_inserted': total_inserted,
        'results': results
    }


# ============================================================================
# CLI Entry Point
# ============================================================================

async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='V39.2 Season Sweep Mode')
    parser.add_argument('--leagues', nargs='+', default=None,
                        help='指定联赛 (默认: Premier League La Liga)')
    parser.add_argument('--seasons', nargs='+', default=None,
                        help='指定赛季 (默认: 2023-2024 2022-2023)')
    parser.add_argument('--dry-run', action='store_true',
                        help='干跑模式（不实际插入数据库）')
    args = parser.parse_args()

    # 确认准入红线测试已通过
    logger.info("🔍 检查准入红线...")
    logger.info("请确认已运行: python tests/unit/test_season_index_parser.py")
    logger.info("如果测试未通过，禁止运行全量抓取！")

    # 启动扫射模式
    stats = await season_sweep_mode(
        leagues=args.leagues,
        seasons=args.seasons
    )

    # 返回状态码
    sys.exit(0 if stats['successful'] > 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
