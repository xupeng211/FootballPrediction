#!/usr/bin/env python3
"""
L1历史数据回溯脚本 - 时光机模式
L1 Historical Data Backfill Script - Time Machine Mode

用于采集历史赛季的完赛数据，为ML模型提供训练数据
"""

import asyncio
import sys
import os
import json
import re
from datetime import datetime
import logging
from pathlib import Path
from typing import list, dict, Any, Optional

# 添加项目根路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

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

# 目标联赛配置
LEAGUE_CONFIG = {
    "premier_league": {
        "id": 47,
        "name": "Premier League",
        "country": "England"
    }
}

# 目标历史赛季 - 使用正确的斜杠格式
TARGET_SEASONS = [
    "2023/2024",  # 最新完赛季
    "2022/2023",  # 完整历史赛季
    "2021/2022",  # 完整历史赛季
    "2020/2021",  # 历史赛季
    "2019/2020",  # 历史赛季
]

class HistoricalDataCollector:
    """历史数据采集器"""

    def __init__(self):
        self.client = None
        self.db_conn = None

    async def initialize(self):
        """初始化连接"""
        self.client = httpx.AsyncClient(timeout=30)
        self.db_conn = psycopg2.connect(**DB_CONFIG)
        logger.info("✅ 历史数据采集器初始化完成")

    async def close(self):
        """关闭连接"""
        if self.client:
            await self.client.aclose()
        if self.db_conn:
            self.db_conn.close()
        logger.info("✅ 历史数据采集器关闭完成")

    async def get_season_data(self, league_id: int, season: str) -> Optional[dict[Any, Any]]:
        """获取指定赛季的数据"""
        # 对赛季参数进行URL编码，确保斜杠正确传递
        import urllib.parse
        encoded_season = urllib.parse.quote(season)
        api_url = f"https://www.fotmob.com/api/leagues?id={league_id}&season={encoded_season}"
        logger.info(f"📡 API URL: {api_url}")

        try:
            logger.info(f"📡 获取赛季数据: {season}")
            response = await self.client.get(api_url, headers=FOTMOB_HEADERS)

            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ 成功获取赛季 {season} 数据，大小: {len(response.text)} 字节")
                return data
            else:
                logger.error(f"❌ 获取赛季 {season} 失败: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ 获取赛季 {season} 异常: {e}")
            return None

    def extract_finished_matches(self, season_data: dict[Any, Any]) -> list[dict[str, Any]]:
        """提取完赛比赛数据"""
        finished_matches = []

        try:
            overview = season_data.get('overview', {})
            matches = overview.get('matches', {})
            all_matches = matches.get('allMatches', [])

            logger.info(f"🔍 分析 {len(all_matches)} 场比赛...")

            for match in all_matches:
                # 检查是否为完赛
                status = match.get('status', {})
                status_reason = status.get('reason', {})
                status_short = status_reason.get('short', '')

                if status_short in ['FT', 'Finished']:
                    # 确保fotmob_id是数字
                    match_id = str(match.get('id', ''))
                    if match_id.isdigit():
                        finished_matches.append(match)

            logger.info(f"✅ 找到 {len(finished_matches)} 场完赛比赛")
            return finished_matches

        except Exception as e:
            logger.error(f"❌ 提取完赛数据异常: {e}")
            return []

    def save_teams_if_not_exists(self, teams_data: list[dict[str, Any]]) -> dict[int, int]:
        """保存球队数据并返回ID映射"""
        team_mapping = {}

        try:
            with self.db_conn.cursor() as cur:
                for team in teams_data:
                    team_id = team.get("id")
                    team_name = team.get("name")

                    if not team_id or not team_name:
                        continue

                    # 检查球队是否已存在
                    cur.execute(
                        "SELECT id FROM teams WHERE external_id = %s",
                        (team_id,)
                    )
                    result = cur.fetchone()

                    if result:
                        team_mapping[team_id] = result[0]
                    else:
                        # 插入新球队
                        cur.execute(
                            """
                            INSERT INTO teams (name, country, external_id, created_at, updated_at)
                            VALUES (%s, %s, %s, NOW(), NOW())
                            RETURNING id
                            """,
                            (team_name, "England", team_id)
                        )
                        new_id = cur.fetchone()[0]
                        team_mapping[team_id] = new_id
                        logger.info(f"💾 新增球队: {team_name} (ID: {team_id})")

                self.db_conn.commit()
                logger.info(f"✅ 球队映射完成: {len(team_mapping)} 支球队")

        except Exception as e:
            logger.error(f"❌ 保存球队数据失败: {e}")
            self.db_conn.rollback()

        return team_mapping

    def save_matches(self, matches_data: list[dict[str, Any]], season: str) -> int:
        """保存比赛数据"""
        saved_count = 0

        try:
            # 提取所有球队数据
            teams_data = []
            for match in matches_data:
                home_team = match.get('home', {})
                away_team = match.get('away', {})

                if home_team.get('id') and home_team.get('name'):
                    teams_data.append({
                        'id': home_team['id'],
                        'name': home_team['name']
                    })

                if away_team.get('id') and away_team.get('name'):
                    teams_data.append({
                        'id': away_team['id'],
                        'name': away_team['name']
                    })

            # 去重
            unique_teams = {team['id']: team for team in teams_data}
            team_list = list(unique_teams.values())

            # 保存球队
            team_mapping = self.save_teams_if_not_exists(team_list)

            with self.db_conn.cursor() as cur:
                for match in matches_data:
                    try:
                        fotmob_id = str(match.get("id", ""))
                        home_team_data = match.get("home", {})
                        away_team_data = match.get("away", {})
                        status_data = match.get("status", {})

                        # 获取球队ID
                        home_fotmob_id = home_team_data.get("id")
                        away_fotmob_id = away_team_data.get("id")

                        home_team_id = team_mapping.get(home_fotmob_id)
                        away_team_id = team_mapping.get(away_fotmob_id)

                        if not home_team_id or not away_team_id:
                            logger.warning(f"⚠️ 跳过比赛（找不到球队）: {fotmob_id}")
                            continue

                        # 获取比分
                        home_score = home_team_data.get("score", 0)
                        away_score = away_team_data.get("score", 0)

                        # 获取比赛状态
                        status_short = status_data.get("reason", {}).get("short", "FT")

                        # 获取比赛时间（从utcTime）
                        match_time = status_data.get("utcTime")
                        if match_time:
                            try:
                                # 转换FotMob时间格式 - 支持新旧两种格式
                                from datetime import datetime

                                # 新格式: "2021-08-13T19:00:00Z" (ISO格式)
                                if 'T' in match_time:
                                    match_datetime = datetime.fromisoformat(match_time.replace('Z', '+00:00'))
                                # 旧格式: "Sat, 25 May 2024, 15:00"
                                else:
                                    match_datetime = datetime.strptime(match_time, "%a, %d %b %Y, %H:%M")

                            except ValueError as e:
                                logger.warning(f"⚠️ 时间解析失败: {match_time} - {e}")
                                match_datetime = None
                        else:
                            match_datetime = None

                        # 插入比赛
                        cur.execute(
                            """
                            INSERT INTO matches (
                                home_team_id, away_team_id,
                                home_score, away_score, status, match_date,
                                fotmob_id, data_source, data_completeness,
                                created_at, updated_at, season
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s,
                                %s, 'fotmob_history', 'complete',
                                NOW(), NOW(), %s
                            )
                        """,
                            (
                                home_team_id, away_team_id,
                                home_score, away_score, status_short, match_datetime,
                                fotmob_id, season
                            ),
                        )

                        if cur.rowcount > 0:
                            saved_count += 1
                            if saved_count <= 10:  # 只显示前10场
                                home_name = home_team_data.get("name", "Unknown")
                                away_name = away_team_data.get("name", "Unknown")
                                logger.info(f"💾 保存比赛: {fotmob_id} - {home_name} {home_score} vs {away_score} {away_name}")

                    except Exception as e:
                        logger.warning(f"⚠️ 保存比赛失败: {match.get('id', 'unknown')} - {e}")

                self.db_conn.commit()
                logger.info(f"✅ 成功保存赛季 {season} 的 {saved_count} 场完赛比赛")

        except Exception as e:
            logger.error(f"❌ 保存比赛数据失败: {e}")
            self.db_conn.rollback()

        return saved_count

async def backfill_season(league_config: dict[str, Any], season: str) -> dict[str, Any]:
    """回溯单个赛季的数据"""
    logger.info(f"🔄 开始回溯赛季: {season}")

    collector = HistoricalDataCollector()
    try:
        await collector.initialize()

        # 获取赛季数据
        season_data = await collector.get_season_data(league_config['id'], season)
        if not season_data:
            return {"success": False, "error": "Failed to fetch season data"}

        # 提取完赛比赛
        finished_matches = collector.extract_finished_matches(season_data)
        if not finished_matches:
            return {"success": False, "error": "No finished matches found"}

        # 保存比赛数据
        saved_count = collector.save_matches(finished_matches, season)

        return {
            "success": True,
            "season": season,
            "total_matches": len(finished_matches),
            "saved_matches": saved_count
        }

    finally:
        await collector.close()

async def main():
    """主函数"""
    logger.info("🚀 启动L1历史数据回溯任务")
    logger.info("🎯 目标：采集最近3个完整赛季的完赛数据")

    results = []

    for _league_name, league_config in LEAGUE_CONFIG.items():
        logger.info(f"🏆 开始处理联赛: {league_config['name']}")

        for season in TARGET_SEASONS:
            result = await backfill_season(league_config, season)
            results.append(result)

            if result["success"]:
                logger.info(f"✅ 赛季 {season} 完成: {result['saved_matches']}/{result['total_matches']} 场比赛")
            else:
                logger.error(f"❌ 赛季 {season} 失败: {result.get('error', 'Unknown error')}")

            # 添加延迟以避免过快的API请求
            await asyncio.sleep(1)

    # 统计结果
    successful_seasons = [r for r in results if r["success"]]
    total_matches = sum(r.get("saved_matches", 0) for r in successful_seasons)

    logger.info("🎊 **历史数据回溯完成！**")
    logger.info(f"   📊 成功赛季: {len(successful_seasons)}/{len(TARGET_SEASONS)}")
    logger.info(f"   💾 总比赛数: {total_matches}")
    logger.info(f"   🏆 处理联赛: {len(LEAGUE_CONFIG)}")

    return 0 if successful_seasons else 1

def print_help():
    """打印帮助信息"""
    print(
        """
🏆 L1历史数据回溯工具
======================

用法:
  python3 src/jobs/backfill_history.py [选项]

功能:
  采集历史赛季的完赛数据，为ML模型提供训练数据

目标赛季:
  - 2023-2024 (最新完赛季)
  - 2022-2023 (历史赛季)
  - 2021-2022 (历史赛季)

数据库:
  自动保存到matches表，包含完赛比分和时间

输出:
  完整的历史比赛数据，支持机器学习训练
        """
    )

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="英超历史数据回溯工具")

    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print_help()
        sys.exit(0)

    args = parser.parse_args()

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
