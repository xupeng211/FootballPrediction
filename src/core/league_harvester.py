#!/usr/bin/env python3
"""
联赛专用收割器 - Production Harvest Tool
支持按联赛ID收割特定联赛的真实比赛数据
"""

import asyncio
import aiohttp
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import sys
import os

# 添加项目路径
sys.path.append("/app" if os.getenv("DOCKER_ENV") else ".")
from src.config_unified import get_settings
from src.api.fotmob_client import FotMobAPIClient

# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class LeagueHarvester:
    """联赛专用收割器"""

    def __init__(self):
        self.settings = get_settings()
        self.api_client = FotMobAPIClient()

    def get_db_connection(self):
        """获取数据库连接"""
        db = self.settings.database
        return psycopg2.connect(
            host=db.host,
            port=db.port,
            database=db.name,
            user=db.user,
            password=db.password.get_secret_value(),
            cursor_factory=RealDictCursor,
        )

    async def get_league_matches(self, league_id: int, limit: int = 50) -> List[Dict]:
        """获取指定联赛的比赛数据"""
        try:
            logger.info(f"🏆 正在获取联赛ID {league_id} 的比赛数据...")

            # 使用FotMob API获取联赛比赛
            url = f"https://www.fotmob.com/api/leagues?id={league_id}&type=matches"
            matches_data = await self.api_client.get_league_matches(league_id)

            if not matches_data or "matches" not in matches_data:
                logger.error(f"❌ 无法获取联赛 {league_id} 的比赛数据")
                return []

            matches = matches_data["matches"][:limit]
            logger.info(f"📋 获取到 {len(matches)} 场比赛")
            return matches

        except Exception as e:
            logger.error(f"❌ 获取联赛 {league_id} 比赛数据失败: {e}")
            return []

    async def harvest_league(self, league_id: int, league_name: str, limit: int = 50):
        """收割指定联赛的数据"""
        logger.info(f"🚀 开始收割 {league_name} (ID: {league_id}) 数据...")

        # 获取比赛数据
        matches = await self.get_league_matches(league_id, limit)

        if not matches:
            logger.error(f"❌ {league_name} 没有可收割的比赛")
            return 0

        harvested_count = 0
        conn = self.get_db_connection()

        try:
            cursor = conn.cursor()

            for match in matches:
                try:
                    # 提取比赛基本信息
                    match_id = match.get("id", str(match.get("matchId", "")))
                    home_team = match.get("home", {}).get("name", "")
                    away_team = match.get("away", {}).get("name", "")
                    match_time_str = match.get("startTime", "")
                    status = match.get("status", {}).get("statusStr", "Unknown")

                    if not match_id or not home_team or not away_team:
                        logger.warning(f"⚠️ 跳过无效比赛: {match}")
                        continue

                    # 转换时间
                    try:
                        match_time = datetime.fromisoformat(match_time_str.replace("Z", "+00:00"))
                    except:
                        match_time = datetime.now()

                    # 检查是否已存在
                    cursor.execute("SELECT external_id FROM matches WHERE external_id = %s", (match_id,))

                    if cursor.fetchone():
                        logger.debug(f"📋 比赛 {match_id} 已存在，跳过")
                        continue

                    # 插入matches表
                    cursor.execute(
                        """
                        INSERT INTO matches (
                            external_id, match_time, home_team, away_team,
                            league_name, season, status, collection_status,
                            created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (external_id) DO NOTHING
                        """,
                        (
                            match_id,
                            match_time,
                            home_team,
                            away_team,
                            league_name,
                            "2024/2025",
                            status,
                            "pending",
                            datetime.now(),
                            datetime.now(),
                        ),
                    )

                    harvested_count += 1
                    logger.info(f"✅ 已添加比赛: {home_team} vs {away_team} ({match_id})")

                except Exception as e:
                    logger.error(f"❌ 处理比赛失败: {match}, Error: {e}")
                    continue

            conn.commit()
            logger.info(f"🎉 {league_name} 收割完成！新增 {harvested_count} 场比赛")

        finally:
            conn.close()

        return harvested_count

    def get_league_config(self, league_id: int) -> Optional[Dict]:
        """从配置中获取联赛信息"""
        leagues = self.settings.supported_leagues
        for league_key, league_config in leagues.items():
            if league_config["id"] == league_id:
                return league_config
        return None


async def main():
    """主函数 - 生产收割模式"""
    import argparse

    parser = argparse.ArgumentParser(description="联赛专用收割器")
    parser.add_argument("--league-id", type=int, required=True, help="联赛ID")
    parser.add_argument("--league-name", type=str, required=True, help="联赛名称")
    parser.add_argument("--limit", type=int, default=50, help="收割数量上限")

    args = parser.parse_args()

    harvester = LeagueHarvester()

    logger.info(f"🚀 启动联赛收割器: {args.league_name} (ID: {args.league_id})")
    logger.info(f"📊 收割上限: {args.limit} 场比赛")

    # 执行收割
    harvested = await harvester.harvest_league(league_id=args.league_id, league_name=args.league_name, limit=args.limit)

    logger.info(f"✨ 收割完成！总共新增 {harvested} 场比赛")

    # 返回收割数量供脚本使用
    print(harvested)


if __name__ == "__main__":
    asyncio.run(main())
