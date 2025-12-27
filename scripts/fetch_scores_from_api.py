#!/usr/bin/env python3
"""
从 FotMob API 获取比分并更新到 matches 表

Author: Data Alignment Expert
Date: 2025-12-27

使用 V50.0 Rich L1 扫描引擎 API 获取比分
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import aiohttp
from src.config_unified import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScoreFetcher:
    """从 FotMob API 获取比分"""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://www.fotmob.com/api"
        self.session = None

        # 统计
        self.total_processed = 0
        self.successful = 0
        self.failed = 0

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def fetch_match_score(self, match_id: str) -> dict | None:
        """
        获取单场比赛的比分

        Args:
            match_id: 比赛 ID (external_id)

        Returns:
            (home_score, away_score, status, actual_result) 或 None
        """
        url = f"{self.base_url}/matchDetails?matchId={match_id}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.fotmob.com/",
        }

        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    # 解析比分
                    header = data.get("header", {})
                    status_obj = header.get("status", {})

                    home_score = status_obj.get("homeScore")
                    away_score = status_obj.get("awayScore")
                    status_str = status_obj.get("status", {}).get("id", "unknown")
                    finished = status_obj.get("finished", False)
                    started = status_obj.get("started", False)

                    # 判定状态
                    if finished:
                        status = "finished"
                    elif started:
                        status = "ongoing"
                    else:
                        status = "scheduled"

                    # 计算结果
                    actual_result = None
                    if home_score is not None and away_score is not None:
                        if home_score > away_score:
                            actual_result = "H"
                        elif home_score < away_score:
                            actual_result = "A"
                        else:
                            actual_result = "D"

                    return {
                        "home_score": home_score,
                        "away_score": away_score,
                        "status": status,
                        "actual_result": actual_result,
                        "is_finished": finished,
                    }
                elif response.status == 404:
                    logger.warning(f"Match {match_id} not found (404)")
                    return None
                else:
                    logger.warning(f"Failed to fetch {match_id}: HTTP {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error fetching {match_id}: {e}")
            return None

    async def fetch_batch(self, match_ids: list[str]) -> list[dict]:
        """批量获取比分"""
        results = []

        for match_id in match_ids:
            self.total_processed += 1

            score_data = await self.fetch_match_score(match_id)

            if score_data:
                results.append({
                    "match_id": match_id,
                    **score_data
                })
                self.successful += 1

                if score_data["home_score"] is not None:
                    logger.info(f"✓ {match_id}: {score_data['home_score']}-{score_data['away_score']}")
                else:
                    logger.info(f"✓ {match_id}: No score yet (status={score_data['status']})")
            else:
                self.failed += 1

            # 每 100 条输出进度
            if self.total_processed % 100 == 0:
                logger.info(f"Progress: {self.total_processed} processed, {self.successful} success, {self.failed} failed")

            # 简单的速率限制
            await asyncio.sleep(0.1)

        return results

    def print_summary(self):
        """打印统计摘要"""
        print("\n" + "=" * 60)
        print("比分获取统计")
        print("=" * 60)
        print(f"总处理: {self.total_processed}")
        print(f"成功: {self.successful}")
        print(f"失败: {self.failed}")
        if self.total_processed > 0:
            print(f"成功率: {self.successful / self.total_processed * 100:.1f}%")
        print("=" * 60)


async def main():
    """主函数"""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    # 连接数据库
    settings = get_settings()
    db = settings.database

    conn = psycopg2.connect(
        host=db.host,
        port=db.port,
        database=db.name,
        user=db.user,
        password=db.password.get_secret_value()
    )

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # 获取所有需要比分的比赛
    logger.info("获取比赛列表...")
    cursor.execute("""
        SELECT match_id, external_id, home_team, away_team
        FROM matches
        WHERE home_score IS NULL
        ORDER BY match_id
        LIMIT 50
    """)

    matches = cursor.fetchall()
    match_ids = [m["external_id"] for m in matches]

    logger.info(f"需要获取比分的比赛数量: {len(match_ids)}")

    if not match_ids:
        logger.info("所有比赛已有比分数据!")
        cursor.close()
        conn.close()
        return

    # 获取比分
    async with ScoreFetcher() as fetcher:
        score_results = await fetcher.fetch_batch(match_ids)
        fetcher.print_summary()

    # 更新数据库
    logger.info("\n更新数据库...")
    update_sql = """
        UPDATE matches
        SET home_score = %s,
            away_score = %s,
            status = %s,
            actual_result = %s,
            is_finished = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE external_id = %s
    """

    updated_count = 0
    for result in score_results:
        cursor.execute(update_sql, (
            result["home_score"],
            result["away_score"],
            result["status"],
            result["actual_result"],
            result["is_finished"],
            str(result["match_id"])  # external_id 是字符串
        ))
        updated_count += cursor.rowcount

    conn.commit()

    # 验证
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(home_score) as with_score
        FROM matches
    """)
    stats = cursor.fetchone()

    logger.info(f"\n更新完成!")
    logger.info(f"更新的比赛数: {updated_count}")
    logger.info(f"数据库中的比赛总数: {stats['total']}")
    logger.info(f"有比分的比赛数: {stats['with_score']}")
    logger.info(f"比分覆盖率: {stats['with_score'] / stats['total'] * 100:.1f}%")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
