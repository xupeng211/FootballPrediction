#!/usr/bin/env python3
"""
URL 补全脚本 - The Link Fixer
首席爬虫工程师: 专门为已入库的26,000条记录补全match_report_url

Purpose:
1. 重新访问FBref赛程页面，提取match_report_url
2. 根据date、home_team、away_team匹配现有记录
3. 批量更新数据库，为L2采集器提供工作URL
"""

import asyncio
import json
import logging
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from bs4 import BeautifulSoup
import pandas as pd
from curl_cffi import requests
import time
import random

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class URLBackfiller:
    """URL补全器 - 专门为已入库数据补全match_report_url"""

    def __init__(self):
        # 使用更轻量的HTTP客户端
        self.session = requests.Session(
            impersonate="chrome",
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
        )

        # 数据库连接配置
        self.db_config = {
            'host': 'db',
            'port': 5432,
            'user': 'postgres',
            'password': 'postgres-dev-password',
            'database': 'football_prediction'
        }

    def get_league_seasons_to_process(self) -> List[Tuple[str, str, str]]:
        """
        获取需要处理的联赛-赛季组合

        Returns:
            List of (league_name, fbref_url, season) tuples
        """
        conn = psycopg2.connect(**self.db_config)

        try:
            with conn.cursor() as cur:
                # 查找需要补全URL的联赛-赛季组合 (优先处理历史数据)
                cur.execute("""
                    SELECT DISTINCT
                        l.name as league_name,
                        l.fbref_url,
                        SUBSTRING(m.match_date::text, 1, 4) as season_year
                    FROM matches m
                    JOIN leagues l ON m.league_id = l.id
                    WHERE m.data_completeness = 'partial'
                      AND m.match_metadata->>'match_report_url' IS NULL
                      AND l.fbref_url IS NOT NULL
                      AND m.match_date >= '2019-01-01'
                    ORDER BY l.name, season_year
                """)

                results = cur.fetchall()
                logger.info(f"📊 找到 {len(results)} 个联赛-赛季需要处理")

                # 转换season_year为season格式
                processed_results = []
                for league_name, fbref_url, season_year in results:
                    if season_year:
                        # 构建赛季格式 (如: 2023 -> 2023-2024)
                        season_start = int(season_year)
                        season_end = season_start + 1
                        season = f"{season_start}-{season_end}"
                        processed_results.append((league_name, fbref_url, season))

                return processed_results

        finally:
            conn.close()

    async def fetch_schedule_with_urls(self, league_name: str, fbref_url: str, season: str) -> pd.DataFrame:
        """
        获取包含URL的赛程数据

        Args:
            league_name: 联赛名称
            fbref_url: FBref联赛URL
            season: 赛季 (如: 2023-2024)

        Returns:
            包含match_report_url的DataFrame
        """
        try:
            # 构建赛程页面URL
            if '/history/' in fbref_url:
                # 转换历史URL为赛程URL
                import re
                match = re.search(r'/comps/(\d+)/history/([^/]+)', fbref_url)
                if match:
                    comp_id = match.group(1)
                    comp_name = match.group(2)
                    schedule_url = f"https://fbref.com/en/comps/{comp_id}/schedule/{comp_name}-Scores-and-Fixtures"
                else:
                    logger.error(f"无法解析FBref URL: {fbref_url}")
                    return pd.DataFrame()
            else:
                # 使用现有URL，添加赛季参数
                if '?' in fbref_url:
                    schedule_url = f"{fbref_url}&season={season.replace('-', '')}"
                else:
                    schedule_url = f"{fbref_url}?season={season.replace('-', '')}"

            logger.info(f"🔗 获取赛程: {league_name} {season}")
            logger.info(f"📡 URL: {schedule_url}")

            # 添加随机延迟避免被封
            delay = random.uniform(2.0, 5.0)
            await asyncio.sleep(delay)

            # 获取HTML内容
            response = self.session.get(schedule_url, timeout=30)

            if response.status_code != 200:
                logger.error(f"❌ HTTP {response.status_code}: {schedule_url}")
                return pd.DataFrame()

            html_content = response.text
            logger.info(f"✅ 获取HTML成功，大小: {len(html_content):,} 字节")

            # 解析表格和URL
            from io import StringIO
            tables = pd.read_html(StringIO(html_content))
            if not tables:
                logger.warning("⚠️ 未找到任何表格")
                return pd.DataFrame()

            # 获取第一个表格（通常是赛程表）
            schedule_df = tables[0]

            # 提取match_report_url
            match_report_urls = self._extract_match_report_urls(html_content)

            if match_report_urls:
                # 确保URL数量与表格行数匹配
                url_count = min(len(match_report_urls), len(schedule_df))
                schedule_df = schedule_df.copy()
                schedule_df['match_report_url'] = None
                schedule_df.iloc[:url_count, schedule_df.columns.get_loc('match_report_url')] = match_report_urls[:url_count]

                logger.info(f"✅ 成功提取到 {url_count} 个URL")
                return schedule_df
            else:
                logger.warning("⚠️ 未提取到任何match_report_url")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"❌ 获取赛程失败 {league_name} {season}: {e}")
            return pd.DataFrame()

    def _extract_match_report_urls(self, html_content: str) -> List[str]:
        """
        从HTML中提取match_report_url

        Args:
            html_content: HTML内容

        Returns:
            URL列表
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            urls = []

            # 方法1: 查找data-stat="match_report"的链接
            for td in soup.find_all('td', {'data-stat': 'match_report'}):
                link = td.find('a', href=True)
                if link and '/matches/' in link['href']:
                    full_url = f"https://fbref.com{link['href']}"
                    urls.append(full_url)

            # 方法2: 如果方法1失败，查找所有包含/matches/的链接
            if not urls:
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '/matches/' in href and 'fbref.com' not in href:
                        full_url = f"https://fbref.com{href}"
                        urls.append(full_url)

            # 方法3: 正则表达式匹配
            if not urls:
                pattern = r'href="(/en/matches/[^"]+)"'
                matches = re.findall(pattern, html_content)
                for match in matches:
                    full_url = f"https://fbref.com{match}"
                    urls.append(full_url)

            logger.info(f"🔗 提取到 {len(urls)} 个match_report_url")
            return urls

        except Exception as e:
            logger.error(f"❌ URL提取失败: {e}")
            return []

    def normalize_team_name(self, name: str) -> str:
        """标准化队名"""
        if pd.isna(name) or not name:
            return ""
        return str(name).strip().lower().replace(" ", "").replace("-", "").replace(".", "")

    def find_matching_records(self, conn, league_name: str, season: str,
                            schedule_df: pd.DataFrame) -> List[Tuple[int, str]]:
        """
        根据date和队名匹配数据库记录

        Args:
            conn: 数据库连接
            league_name: 联赛名称
            season: 赛季
            schedule_df: 赛程DataFrame

        Returns:
            List of (match_id, match_report_url) tuples
        """
        if schedule_df.empty:
            return []

        matches_to_update = []

        # 获取league_id
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM leagues WHERE name = %s", (league_name,))
            league_result = cur.fetchone()
            if not league_result:
                logger.warning(f"⚠️ 未找到联赛: {league_name}")
                return []
            league_id = league_result[0]

        # 遍历赛程表中的每场比赛
        for _, row in schedule_df.iterrows():
            try:
                # 提取比赛信息
                raw_date = str(row.get('Date', '')).strip()
                home_team = str(row.get('Home', '')).strip()
                away_team = str(row.get('Away', '')).strip()
                score = str(row.get('Score', '')).strip()
                match_report_url = str(row.get('match_report_url', '')).strip()

                # 处理日期格式 - FBref可能使用不同格式
                if raw_date:
                    # 尝试解析各种日期格式
                    try:
                        from datetime import datetime
                        # 尝试常见格式
                        for fmt in ['%b %d, %Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                            try:
                                date_obj = datetime.strptime(raw_date, fmt)
                                date_str = date_obj.strftime('%Y-%m-%d')
                                break
                            except ValueError:
                                continue
                        else:
                            # 如果所有格式都失败，使用原始字符串
                            date_str = raw_date
                    except:
                        date_str = raw_date
                else:
                    date_str = ''

                # 跳过无效记录
                if not date_str or not home_team or not away_team or not match_report_url:
                    continue

                # 验证日期格式 - 必须是有效的日期字符串
                if date_str in ['nan', 'Date', '', 'None']:
                    continue

                # 验证URL格式 - 必须是有效的FBref URL
                if not match_report_url.startswith('https://fbref.com'):
                    continue

                # 跳过未完成的比赛
                if not score or score in ['', '-']:
                    continue

                # 标准化队名
                home_team_norm = self.normalize_team_name(home_team)
                away_team_norm = self.normalize_team_name(away_team)

                # 查找数据库中匹配的记录（修复SQL JOIN错误）
                with conn.cursor() as cur:
                    # 使用精确匹配的SQL查询，包含teams表JOIN
                    cur.execute("""
                        SELECT m.id, m.home_team_id, m.away_team_id,
                               ht.name as home_team_name, at.name as away_team_name
                        FROM matches m
                        JOIN teams ht ON m.home_team_id = ht.id
                        JOIN teams at ON m.away_team_id = at.id
                        WHERE m.league_id = %s
                          AND m.data_completeness = 'partial'
                          AND m.match_metadata->>'match_report_url' IS NULL
                          AND DATE(m.match_date) = %s
                    """, (league_id, date_str))

                    db_matches = cur.fetchall()

                    # 智能匹配：检查队名相似度
                    for db_match_id, db_home_team_id, db_away_team_id, db_home_name, db_away_name in db_matches:
                        # 标准化数据库中的队名
                        db_home_name_norm = self.normalize_team_name(db_home_name)
                        db_away_name_norm = self.normalize_team_name(db_away_name)

                        # 检查队名匹配（允许一定差异）
                        home_match = (home_team_norm in db_home_name_norm or db_home_name_norm in home_team_norm)
                        away_match = (away_team_norm in db_away_name_norm or db_away_name_norm in away_team_norm)

                        # 额外检查：完全匹配
                        exact_home_match = home_team.lower() == db_home_name.lower()
                        exact_away_match = away_team.lower() == db_away_name.lower()

                        if (home_match and away_match) or (exact_home_match and exact_away_match):
                            matches_to_update.append((db_match_id, match_report_url))
                            logger.info(f"✅ 匹配成功: {home_team} vs {away_team} -> MatchID: {db_match_id} (DB: {db_home_name} vs {db_away_name})")
                            break

            except Exception as e:
                logger.error(f"❌ 处理赛程记录失败: {e}")
                continue

        return matches_to_update

    def update_database_urls(self, matches_to_update: List[Tuple[int, str]]) -> int:
        """
        批量更新数据库中的match_report_url

        Args:
            matches_to_update: List of (match_id, match_report_url) tuples

        Returns:
            成功更新的记录数
        """
        if not matches_to_update:
            return 0

        conn = psycopg2.connect(**self.db_config)
        updated_count = 0

        try:
            with conn.cursor() as cur:
                for match_id, match_report_url in matches_to_update:
                    try:
                        # 更新match_metadata (修复JSONB类型转换)
                        cur.execute("""
                            UPDATE matches
                            SET match_metadata = jsonb_set(
                                jsonb_set(
                                    COALESCE(match_metadata, '{}'),
                                    '{match_report_url}',
                                    %s::jsonb
                                ),
                                '{match_report_url_source}',
                                '"fbref_backfill_v1"'::jsonb
                            ),
                            updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (json.dumps(match_report_url), match_id))

                        updated_count += 1

                        if updated_count % 10 == 0:
                            logger.info(f"📊 已更新 {updated_count} 条记录...")

                    except Exception as e:
                        logger.error(f"❌ 更新记录 {match_id} 失败: {e}")
                        continue

                conn.commit()
                logger.info(f"✅ 成功更新 {updated_count} 条记录的match_report_url")

        except Exception as e:
            conn.rollback()
            logger.error(f"❌ 批量更新失败: {e}")
        finally:
            conn.close()

        return updated_count

    async def run_backfill(self):
        """运行URL补全主流程"""
        logger.info("🚀 启动URL补全程序")
        logger.info("🎯 目标: 为26,000条记录补全match_report_url")

        # 获取需要处理的联赛-赛季组合
        league_seasons = self.get_league_seasons_to_process()

        if not league_seasons:
            logger.info("📋 没有需要处理的联赛-赛季组合")
            return

        total_updated = 0
        total_processed = 0

        for i, (league_name, fbref_url, season) in enumerate(league_seasons, 1):
            logger.info(f"\n🔄 处理第 {i}/{len(league_seasons)} 个联赛: {league_name} {season}")

            try:
                # 1. 获取包含URL的赛程数据
                schedule_df = await self.fetch_schedule_with_urls(league_name, fbref_url, season)

                if schedule_df.empty:
                    logger.warning(f"⚠️ {league_name} {season}: 未获取到赛程数据")
                    continue

                # 2. 匹配数据库记录
                conn = psycopg2.connect(**self.db_config)
                try:
                    matches_to_update = self.find_matching_records(conn, league_name, season, schedule_df)

                    if matches_to_update:
                        logger.info(f"🎯 {league_name} {season}: 找到 {len(matches_to_update)} 条记录需要更新")

                        # 3. 更新数据库
                        updated_count = self.update_database_urls(matches_to_update)
                        total_updated += updated_count

                    else:
                        logger.info(f"📋 {league_name} {season}: 没有找到需要更新的记录")

                finally:
                    conn.close()

                total_processed += 1

                # 请求间延迟
                if i < len(league_seasons):
                    delay = random.uniform(5.0, 10.0)
                    logger.info(f"⏳ 延迟 {delay:.1f} 秒...")
                    await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"❌ 处理 {league_name} {season} 失败: {e}")
                continue

        logger.info(f"\n🎉 URL补全完成!")
        logger.info(f"📊 处理联赛-赛季: {total_processed}/{len(league_seasons)}")
        logger.info(f"🔗 更新记录总数: {total_updated}")

        # 验证结果
        self.verify_results()

    def verify_results(self):
        """验证补全结果"""
        logger.info("\n🔍 验证补全结果...")

        conn = psycopg2.connect(**self.db_config)

        try:
            with conn.cursor() as cur:
                # 检查还有多少记录缺少URL
                cur.execute("""
                    SELECT COUNT(*)
                    FROM matches
                    WHERE data_completeness = 'partial'
                      AND match_metadata->>'match_report_url' IS NULL
                """)
                missing_urls = cur.fetchone()[0]

                # 检查总共多少记录有URL
                cur.execute("""
                    SELECT COUNT(*)
                    FROM matches
                    WHERE match_metadata->>'match_report_url' IS NOT NULL
                """)
                has_urls = cur.fetchone()[0]

                logger.info(f"📊 验证结果:")
                logger.info(f"  ❌ 仍缺少URL: {missing_urls:,} 条记录")
                logger.info(f"  ✅ 已有URL: {has_urls:,} 条记录")

                if missing_urls == 0:
                    logger.info("🎉 所有partial记录都有URL了!")
                else:
                    completion_rate = (has_urls / (has_urls + missing_urls)) * 100
                    logger.info(f"📈 完成率: {completion_rate:.1f}%")

                # 显示一些示例URL
                cur.execute("""
                    SELECT id, match_metadata->>'match_report_url'
                    FROM matches
                    WHERE match_metadata->>'match_report_url' IS NOT NULL
                    LIMIT 5
                """)
                examples = cur.fetchall()

                if examples:
                    logger.info("📋 URL示例:")
                    for match_id, url in examples:
                        logger.info(f"  Match {match_id}: {url}")

        finally:
            conn.close()


async def main():
    """主函数"""
    backfiller = URLBackfiller()

    try:
        await backfiller.run_backfill()
    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断程序")
    except Exception as e:
        logger.error(f"❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())