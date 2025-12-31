#!/usr/bin/env python3
"""
2025 年历史比分回填脚本 (2025 Results Backfiller)
===================================================

功能:
1. 针对 2025 年 1-5 月状态为 scheduled 的比赛
2. 从 FotMob API 抓取真实比分
3. 更新状态为 finished，设置 home_score 和 away_score

Author: Senior Data Cleaning Expert
Version: 1.0.0
Date: 2025-12-31
"""

import asyncio
import logging
import os
import re
import sys
from datetime import datetime
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

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

# ============================================================================
# 历史比分回填器
# ============================================================================


class ResultsBackfiller:
    """历史比分回填器"""

    def __init__(self):
        """初始化"""
        self.settings = get_settings()
        self._conn = None
        self.stats = {
            "total_to_update": 0,
            "fetched_with_score": 0,
            "fetched_no_score": 0,
            "fetch_failed": 0,
            "updated_finished": 0,
            "updated_postponed": 0,
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

    def fetch_matches_to_update(self, chunk_size: int = 100):
        """
        获取需要更新的比赛列表

        Args:
            chunk_size: 分片大小

        Yields:
            DataFrame: 每个分片的比赛数据
        """
        import pandas as pd

        conn = self.get_connection()
        offset = 0

        while True:
            with conn.cursor() as cursor:
                query = """
                    SELECT match_id, home_team, away_team, match_date, league_name
                    FROM matches
                    WHERE status = 'scheduled'
                      AND match_date >= '2025-01-01'
                      AND match_date < '2026-01-01'
                    ORDER BY match_date DESC
                    LIMIT %s OFFSET %s
                """

                cursor.execute(query, (chunk_size, offset))
                matches_data = cursor.fetchall()

                if not matches_data:
                    break

                chunk_df = pd.DataFrame(matches_data)

                logger.info(f"📦 待更新分片: {len(chunk_df)} 场比赛")

                self.stats["total_to_update"] += len(chunk_df)

                yield chunk_df

                offset += chunk_size

                if len(matches_data) < chunk_size:
                    break

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch_match_result(self, session, match_id: str, league_id: int = None):
        """
        抓取单场比赛的结果

        Args:
            session: aiohttp 会话
            match_id: 比赛 ID
            league_id: 联赛 ID（可选）

        Returns:
            (status, home_score, away_score) 或 None
        """
        # FotMob API 获取比赛详情
        url = f"https://www.fotmob.com/api/matchDetails"
        params = {"matchId": str(match_id)}

        headers = {
            "User-Agent": os.environ.get("CUSTOM_USER_AGENT", USER_AGENTS[0]),
            "Accept": "application/json",
            "Referer": "https://www.fotmob.com/",
        }

        try:
            async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()

                    # 提取比赛状态
                    status_data = data.get("header", {}).get("status", {})
                    match_status = status_data.get("statusStr", "").lower()

                    # 提取比分
                    score_str = status_data.get("scoreStr", "")

                    if score_str and match_status in ["finished", "ft", "ended"]:
                        # 解析比分 "2-1"
                        match = re.search(r"(\d+)\s*-\s*(\d+)", score_str)
                        if match:
                            home_score = int(match.group(1))
                            away_score = int(match.group(2))

                            return ("finished", home_score, away_score)
                    elif match_status in ["postponed", "cancelled", "abandoned"]:
                        return (match_status, None, None)
                    else:
                        # 比赛可能还未开始或进行中
                        return ("scheduled", None, None)

                elif response.status == 404:
                    return (None, None, None)
                else:
                    logger.warning(f"⚠️  比赛 {match_id}: HTTP {response.status}")
                    return (None, None, None)

        except asyncio.TimeoutError:
            logger.warning(f"⚠️  比赛 {match_id}: 请求超时")
            return (None, None, None)
        except Exception as e:
            logger.warning(f"⚠️  比赛 {match_id}: {e}")
            return (None, None, None)

    def update_match_status(self, match_id: str, status: str, home_score: int = None, away_score: int = None):
        """
        更新比赛状态

        Args:
            match_id: 比赛 ID
            status: 新状态
            home_score: 主队得分
            away_score: 客队得分
        """
        conn = self.get_connection()

        with conn.cursor() as cursor:
            if status == "finished" and home_score is not None and away_score is not None:
                # 更新为已完成
                cursor.execute("""
                    UPDATE matches
                    SET status = %s,
                        home_score = %s,
                        away_score = %s,
                        is_finished = true,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE match_id = %s
                """, (status, home_score, away_score, match_id))

                self.stats["updated_finished"] += 1

            elif status in ["postponed", "cancelled", "abandoned"]:
                # 更新为推迟/取消
                actual_result = "POSTP" if status == "postponed" else "CANC"

                cursor.execute("""
                    UPDATE matches
                    SET status = %s,
                        actual_result = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE match_id = %s
                """, (status, actual_result, match_id))

                self.stats["updated_postponed"] += 1

        conn.commit()

    async def process_chunk(self, chunk_df):
        """
        处理单个分片

        Args:
            chunk_df: 分片数据
        """
        import pandas as pd

        async with aiohttp.ClientSession() as session:
            for _, match in chunk_df.iterrows():
                match_id = match["match_id"]

                # 抓取结果
                result = await self.fetch_match_result(session, match_id)

                if result and result[0]:
                    status, home_score, away_score = result

                    if status == "finished":
                        self.update_match_status(match_id, status, home_score, away_score)
                        logger.info(f"✓ {match_id}: {status} {home_score}-{away_score}")
                        self.stats["fetched_with_score"] += 1

                    elif status in ["postponed", "cancelled", "abandoned"]:
                        self.update_match_status(match_id, status)
                        logger.info(f"✓ {match_id}: {status}")
                        self.stats["fetched_no_score"] += 1

                    else:
                        # 仍然是 scheduled，说明比赛还未开始
                        self.stats["fetched_no_score"] += 1

                elif result is None:
                    # 抓取失败，可能是比赛不存在或 API 问题
                    logger.warning(f"✗ {match_id}: 抓取失败")
                    self.stats["fetch_failed"] += 1

                # 添加延迟避免过快请求
                await asyncio.sleep(0.5)

    async def run(self):
        """执行回填"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("2025 年历史比分回填脚本")
        logger.info("=" * 60)
        logger.info("")

        # 处理所有分片
        for chunk_df in self.fetch_matches_to_update():
            await self.process_chunk(chunk_df)

        # 输出统计
        logger.info("")
        logger.info("=" * 60)
        logger.info("回填完成")
        logger.info("=" * 60)
        logger.info(f"待更新: {self.stats['total_to_update']} 场")
        logger.info(f"✓ 有比分更新: {self.stats['updated_finished']} 场")
        logger.info(f"✓ 推迟/取消: {self.stats['updated_postponed']} 场")
        logger.info(f"✗ 抓取失败: {self.stats['fetch_failed']} 场")
        logger.info(f"- 仍需等待: {self.stats['fetched_no_score']} 场")


# ============================================================================
# 主函数
# ============================================================================


async def main():
    """主函数"""
    backfiller = ResultsBackfiller()
    await backfiller.run()


if __name__ == "__main__":
    asyncio.run(main())
