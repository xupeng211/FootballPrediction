#!/usr/bin/env python3
"""
2026 年赛程抓取脚本 (2026 Fixtures Fetcher)
=============================================

功能:
1. 抓取 2026-01-01 至 2026-01-15 的五大联赛赛程
2. 确保这些未来比赛状态为 scheduled
3. 支持增量入库，避免重复

Author: Senior Crawler Engineer
Version: 1.0.0
Date: 2025-12-31
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp
import psycopg2
from psycopg2.extras import RealDictCursor
from tenacity import retry, stop_after_attempt, wait_exponential

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config_unified import get_settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================================
# 配置
# ============================================================================

TARGET_LEAGUES = [
    (47, "Premier League", "英超"),
    (87, "La Liga", "西甲"),
    (82, "Bundesliga", "德甲"),
    (73, "Serie A", "意甲"),
    (71, "Ligue 1", "法甲"),
]

SEASON_2026 = "2526"  # 2025/2026 赛季

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

# ============================================================================
# 2026 赛程抓取器
# ============================================================================


class Fixture2026Fetcher:
    """2026 年赛程抓取器"""

    BASE_URL = "https://www.fotmob.com/api/leagues"

    def __init__(self):
        """初始化"""
        self.settings = get_settings()
        self._conn = None
        self.stats = {
            "total_fetched": 0,
            "total_saved": 0,
            "total_skipped": 0,
            "by_league": {},
        }

    def get_connection(self):
        """获取数据库连接"""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
        return self._conn

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch_league_matches(self, session, league_id: int, league_name: str):
        """
        抓取单个联赛的比赛数据

        Args:
            session: aiohttp 会话
            league_id: 联赛 ID
            league_name: 联赛名称

        Returns:
            比赛列表
        """
        url = f"{self.BASE_URL}"
        params = {
            "id": str(league_id),
            "season": SEASON_2026,
        }

        headers = {
            "User-Agent": os.environ.get("CUSTOM_USER_AGENT", USER_AGENTS[0]),
            "Accept": "application/json",
            "Referer": "https://www.fotmob.com/",
        }

        try:
            async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    matches = data.get("matches", [])

                    # 过滤 2026-01-01 至 2026-01-15 的比赛
                    filtered_matches = []
                    for match in matches:
                        match_date_str = match.get("status", {}).get("starttimeStr")
                        if match_date_str:
                            try:
                                # 解析日期: "2026-01-10T19:45:00+00:00"
                                match_date = datetime.fromisoformat(match_date_str.replace("+00:00", "+00:00"))
                                target_start = datetime(2026, 1, 1)
                                target_end = datetime(2026, 1, 16)

                                if target_start <= match_date < target_end:
                                    filtered_matches.append(match)
                            except ValueError as e:
                                logger.warning(f"日期解析失败: {match_date_str}, {e}")
                                continue

                    logger.info(f"✓ {league_name}: 抓取到 {len(matches)} 场比赛，其中 {len(filtered_matches)} 场在目标范围内")
                    return filtered_matches

                elif response.status == 404:
                    logger.warning(f"⚠️  {league_name}: 赛季 {SEASON_2026} 尚未开放")
                    return []
                else:
                    logger.error(f"❌ {league_name}: HTTP {response.status}")
                    return []

        except asyncio.TimeoutError:
            logger.error(f"❌ {league_name}: 请求超时")
            return []
        except Exception as e:
            logger.error(f"❌ {league_name}: {e}")
            return []

    def save_matches(self, league_name: str, matches: list):
        """
        保存比赛到数据库

        Args:
            league_name: 联赛名称
            matches: 比赛列表

        Returns:
            保存统计
        """
        conn = self.get_connection()
        saved_count = 0
        skipped_count = 0

        with conn.cursor() as cursor:
            for match in matches:
                try:
                    # 提取数据
                    match_id = str(match.get("id", ""))
                    home_team = match.get("home", {}).get("name", "")
                    away_team = match.get("away", {}).get("name", "")
                    start_time_str = match.get("status", {}).get("starttimeStr", "")

                    if not all([match_id, home_team, away_team, start_time_str]):
                        continue

                    # 解析日期
                    match_date = datetime.fromisoformat(start_time_str.replace("+00:00", "+00:00"))

                    # 检查是否已存在
                    cursor.execute("SELECT match_id FROM matches WHERE match_id = %s", (match_id,))
                    if cursor.fetchone():
                        skipped_count += 1
                        continue

                    # 插入比赛
                    cursor.execute("""
                        INSERT INTO matches (
                            match_id, external_id, league_name, season,
                            home_team, away_team, match_date, status,
                            league_id, collection_date, data_version, data_source
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (match_id) DO NOTHING
                    """, (
                        match_id,
                        match_id,
                        league_name,
                        SEASON_2026,
                        home_team,
                        away_team,
                        match_date,
                        "scheduled",
                        next((lid for lid, ln, _ in TARGET_LEAGUES if ln == league_name), None),
                        datetime.now(),
                        "V51.0",
                        "FotMob",
                    ))

                    saved_count += 1

                except Exception as e:
                    logger.warning(f"保存比赛失败 {match.get('id')}: {e}")
                    continue

            conn.commit()

        self.stats["total_saved"] += saved_count
        self.stats["total_skipped"] += skipped_count
        self.stats["by_league"][league_name] = {"saved": saved_count, "skipped": skipped_count}

        logger.info(f"  保存: {saved_count}, 跳过: {skipped_count}")

    async def run(self):
        """执行抓取"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("2026 年赛程抓取脚本")
        logger.info("=" * 60)
        logger.info(f"目标日期范围: 2026-01-01 至 2026-01-15")
        logger.info(f"目标联赛: {[ln for _, ln, _ in TARGET_LEAGUES]}")
        logger.info("")

        async with aiohttp.ClientSession() as session:
            tasks = []
            for league_id, league_name, cn_name in TARGET_LEAGUES:
                task = self.fetch_league_matches(session, league_id, league_name)
                tasks.append((league_name, task))

            for league_name, task in tasks:
                matches = await task
                self.stats["total_fetched"] += len(matches)

                if matches:
                    self.save_matches(league_name, matches)

        # 输出统计
        logger.info("")
        logger.info("=" * 60)
        logger.info("抓取完成")
        logger.info("=" * 60)
        logger.info(f"总抓取: {self.stats['total_fetched']} 场")
        logger.info(f"总保存: {self.stats['total_saved']} 场")
        logger.info(f"总跳过: {self.stats['total_skipped']} 场")
        logger.info("")
        logger.info("按联赛统计:")
        for league, stats_data in self.stats["by_league"].items():
            logger.info(f"  {league}: +{stats_data['saved']}, 跳过 {stats_data['skipped']}")


# ============================================================================
# 主函数
# ============================================================================


async def main():
    """主函数"""
    fetcher = Fixture2026Fetcher()
    await fetcher.run()


if __name__ == "__main__":
    asyncio.run(main())
