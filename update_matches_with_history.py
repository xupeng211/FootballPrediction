#!/usr/bin/env python3
"""
更新现有比赛记录为历史完赛数据
Update Existing Matches with Historical Finished Data

这个脚本将更新现有matches表中的记录，用历史完赛数据替换pending状态
"""

import asyncio
import sys
import os
import json
from datetime import datetime
import logging

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 数据库连接配置
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "football_prediction",
    "user": "postgres",
    "password": "postgres"
}

# FotMob API配置
FOTMOB_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Accept-Language': 'en-GB,en;q=0.9',
    'x-mas': 'eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9sZWFndWVzP2lkPTg3IiwiY29kZSI6MTc2NTEyMTc0OTUyNSwiZm9vIjoicHJvZHVjdGlvbjo0MjhmYTAzNTVmMDljYTg4Zjk3YjE3OGViNWE3OWVmMGNmYmQwZGZjIn0sInNpZ25hdHVyZSI6IkIwQzkyMzkxMTM4NTdCNUFBMjk5Rjc5M0QxOTYwRkZCIn0=',
    'x-foo': 'eyJmb28iOiJwcm9kdWN0aW9uOjQyOGZhMDM1NWYwOWNhODhmOTdiMTc4ZWI1YTc5ZWYwY2ZiZDBkZmMiLCJ0aW1lc3RhbXAiOjE3NjUxMjE4MTJ9'
}

# 目标历史赛季
TARGET_SEASONS = [
    "2023-2024",  # 最新完赛季
    "2022-2023",  # 完整历史赛季
    "2021-2022",  # 完整历史赛季
]

class MatchUpdater:
    """比赛记录更新器"""

    def __init__(self):
        self.client = None
        self.db_conn = None

    async def initialize(self):
        """初始化连接"""
        self.client = httpx.AsyncClient(timeout=30)
        self.db_conn = psycopg2.connect(**DB_CONFIG)
        logger.info("✅ 比赛记录更新器初始化完成")

    async def close(self):
        """关闭连接"""
        if self.client:
            await self.client.aclose()
        if self.db_conn:
            self.db_conn.close()
        logger.info("✅ 比赛记录更新器关闭完成")

    async def get_season_finished_matches(self, season: str) -> dict:
        """获取指定赛季的完赛比赛数据"""
        api_url = f"https://www.fotmob.com/api/leagues?id=47&season={season}"

        try:
            logger.info(f"📡 获取赛季完赛数据: {season}")
            response = await self.client.get(api_url, headers=FOTMOB_HEADERS)

            if response.status_code == 200:
                data = response.json()
                overview = data.get('overview', {})
                matches = overview.get('matches', {})
                all_matches = matches.get('allMatches', [])

                # 筛选完赛比赛
                finished_matches = {}
                for match in all_matches:
                    status = match.get('status', {})
                    status_short = status.get('reason', {}).get('short', '')

                    if status_short in ['FT', 'Finished']:
                        fotmob_id = str(match.get('id', ''))
                        if fotmob_id.isdigit():
                            finished_matches[fotmob_id] = match

                logger.info(f"✅ 赛季 {season}: 找到 {len(finished_matches)} 场完赛比赛")
                return finished_matches
            else:
                logger.error(f"❌ 获取赛季 {season} 失败: HTTP {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"❌ 获取赛季 {season} 异常: {e}")
            return {}

    def update_matches_in_database(self, finished_matches: dict, season: str) -> int:
        """更新数据库中的比赛记录"""
        updated_count = 0

        try:
            with self.db_conn.cursor() as cur:
                for fotmob_id, match_data in finished_matches.items():
                    # 获取比赛信息
                    home_team_data = match_data.get('home', {})
                    away_team_data = match_data.get('away', {})
                    status_data = match_data.get('status', {})

                    # 获取比分
                    home_score = home_team_data.get('score', 0)
                    away_score = away_team_data.get('score', 0)

                    # 获取比赛状态
                    status_short = status_data.get('reason', {}).get('short', 'FT')

                    # 获取比赛时间
                    match_time = status_data.get('utcTime')
                    match_datetime = None
                    if match_time:
                        try:
                            match_datetime = datetime.strptime(match_time, "%a, %d %b %Y, %H:%M")
                        except ValueError:
                            logger.warning(f"⚠️ 无法解析时间格式: {match_time}")

                    # 更新比赛记录
                    cur.execute(
                        """
                        UPDATE matches SET
                            home_score = %s,
                            away_score = %s,
                            status = %s,
                            match_date = %s,
                            data_completeness = 'complete',
                            updated_at = NOW(),
                            season = %s
                        WHERE fotmob_id = %s
                        """,
                        (
                            home_score, away_score, status_short, match_datetime,
                            season, fotmob_id
                        )
                    )

                    if cur.rowcount > 0:
                        updated_count += 1
                        if updated_count <= 10:  # 只显示前10场
                            home_name = home_team_data.get("name", "Unknown")
                            away_name = away_team_data.get("name", "Unknown")
                            logger.info(f"✅ 更新比赛: {fotmob_id} - {home_name} {home_score} vs {away_score} {away_name}")

                self.db_conn.commit()
                logger.info(f"✅ 成功更新赛季 {season} 的 {updated_count} 场比赛")

        except Exception as e:
            logger.error(f"❌ 更新比赛数据失败: {e}")
            self.db_conn.rollback()

        return updated_count

    def get_existing_fotmob_ids(self) -> set:
        """获取数据库中现有的fotmob_id"""
        try:
            with self.db_conn.cursor() as cur:
                cur.execute("SELECT fotmob_id FROM matches WHERE fotmob_id IS NOT NULL")
                existing_ids = {row[0] for row in cur.fetchall()}
                logger.info(f"📊 数据库中有 {len(existing_ids)} 个现有fotmob_id")
                return existing_ids
        except Exception as e:
            logger.error(f"❌ 获取现有fotmob_id失败: {e}")
            return set()

async def update_season(season: str, existing_fotmob_ids: set) -> dict:
    """更新单个赛季的比赛数据"""
    logger.info(f"🔄 开始更新赛季: {season}")

    updater = MatchUpdater()
    try:
        await updater.initialize()

        # 获取赛季完赛数据
        finished_matches = await updater.get_season_finished_matches(season)
        if not finished_matches:
            return {"success": False, "error": "No finished matches found"}

        # 只更新数据库中存在的比赛
        matches_to_update = {fotmob_id: match_data
                             for fotmob_id, match_data in finished_matches.items()
                             if fotmob_id in existing_fotmob_ids}

        logger.info(f"🎯 目标更新: {len(matches_to_update)}/{len(finished_matches)} 场比赛 (存在于数据库)")

        # 更新数据库
        updated_count = updater.update_matches_in_database(matches_to_update, season)

        return {
            "success": True,
            "season": season,
            "total_finished": len(finished_matches),
            "matches_to_update": len(matches_to_update),
            "updated_matches": updated_count
        }

    finally:
        await updater.close()

async def main():
    """主函数"""
    logger.info("🚀 启动比赛记录更新任务")
    logger.info("🎯 目标：将现有比赛记录更新为历史完赛数据")

    # 获取现有fotmob_id
    updater = MatchUpdater()
    try:
        await updater.initialize()
        existing_fotmob_ids = updater.get_existing_fotmob_ids()
    finally:
        await updater.close()

    results = []

    for season in TARGET_SEASONS:
        result = await update_season(season, existing_fotmob_ids)
        results.append(result)

        if result["success"]:
            logger.info(f"✅ 赛季 {season} 完成: {result['updated_matches']}/{result['matches_to_update']} 场比赛已更新")
        else:
            logger.error(f"❌ 赛季 {season} 失败: {result.get('error', 'Unknown error')}")

        # 添加延迟以避免过快的API请求
        await asyncio.sleep(1)

    # 统计结果
    successful_seasons = [r for r in results if r["success"]]
    total_updated = sum(r.get("updated_matches", 0) for r in successful_seasons)

    logger.info("🎊 **比赛记录更新完成！**")
    logger.info(f"   📊 成功赛季: {len(successful_seasons)}/{len(TARGET_SEASONS)}")
    logger.info(f"   💾 总更新数: {total_updated}")

    # 最终统计
    final_updater = MatchUpdater()
    try:
        await final_updater.initialize()
        with final_updater.db_conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) as total_matches,
                    COUNT(CASE WHEN status = 'Finished' OR status = 'FT' THEN 1 END) as finished_matches,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_matches,
                    ROUND(COUNT(CASE WHEN status = 'Finished' OR status = 'FT' THEN 1 END) * 100.0 / COUNT(*), 2) as finished_percentage
                FROM matches
            """)

            stats = cur.fetchone()
            logger.info(f"📈 最终统计:")
            logger.info(f"   总比赛数: {stats[0]}")
            logger.info(f"   完赛数: {stats[1]}")
            logger.info(f"   未完赛数: {stats[2]}")
            logger.info(f"   完赛率: {stats[3]}%")
    finally:
        await final_updater.close()

    return 0 if successful_seasons and total_updated > 0 else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("⚠️ 用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 程序异常退出: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)