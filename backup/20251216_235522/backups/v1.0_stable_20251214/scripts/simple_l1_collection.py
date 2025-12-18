#!/usr/bin/env python3
"""
简单L1数据采集器 - 通过FotMob API获取基础比赛数据
Simple L1 Data Collector - Fetch basic match data via FotMob API
"""

import asyncio
import httpx
import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

# 添加项目根路径
sys.path.append(str(Path(__file__).parent.parent))

from src.database.async_manager import get_db_session, AsyncDatabaseManager
from src.database.definitions import initialize_database

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class SimpleL1Collector:
    """简单L1数据采集器"""

    def __init__(self):
        # 使用修复后的API令牌
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.fotmob.com/',
            'x-mas': 'eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9sZWFndWVzP2lkPTg3IiwiY29kZSI6MTc2NTEyMTc0OTUyNSwiZm9vIjoicHJvZHVjdGlvbjo0MjhmYTAzNTVmMDljYTg4Zjk3YjE3OGViNWE3OWVmMGNmYmQwZGZjIn0sInNpZ25hdHVyZSI6IkIwQzkyMzkxMTM4NTdCNUFBMjk5Rjc5M0QxOTYwRkZCIn0=',
            'x-foo': 'eyJmb28iOiJwcm9kdWN0aW9uOjQyOGZhMDM1NWYwOWNhODhmOTdiMTc4ZWI1YTc5ZWYwY2ZiZGRmYyIsInRpbWVzdGFtcCI6MTc2NTEyMTgxMn0='
        }

        # 目标联赛
        self.target_leagues = [
            {"id": 47, "name": "Premier League"},  # 英超
            {"id": 87, "name": "LaLiga"},         # 西甲
            {"id": 55, "name": "Bundesliga"},     # 德甲
            {"id": 54, "name": "Serie A"},        # 意甲
            {"id": 53, "name": "Ligue 1"},        # 法甲
        ]

    async def fetch_league_matches(self, league_id: int, league_name: str) -> Optional[list[dict]]:
        """
        获取联赛比赛数据

        Args:
            league_id: 联赛ID
            league_name: 联赛名称

        Returns:
            比赛数据列表
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # 获取当前赛季的比赛数据
                url = f"https://www.fotmob.com/api/leagues?id={league_id}"
                logger.info(f"📊 获取{league_name}数据: {url}")

                response = await client.get(url, headers=self.headers)

                if response.status_code != 200:
                    logger.error(f"❌ API请求失败: {response.status_code}")
                    return None

                data = response.json()

                # 提取比赛数据 - 使用验证过的正确路径
                matches = []

                # 从FotMob API的正确路径提取比赛数据
                if 'fixtures' in data and isinstance(data['fixtures'], dict):
                    if 'allMatches' in data['fixtures']:
                        matches = data['fixtures']['allMatches']
                    elif 'matches' in data['fixtures']:
                        matches = data['fixtures']['matches']
                    elif 'events' in data['fixtures']:
                        matches = data['fixtures']['events']

                elif 'matches' in data:
                    matches = data['matches']
                elif 'allMatches' in data:
                    matches = data['allMatches']
                elif 'matches' in data.get('tabs', [{}])[0]:
                    matches = data['tabs'][0]['matches']
                else:
                    # 尝试从深层结构中提取
                    if 'data' in data and 'matches' in data['data']:
                        matches = data['data']['matches']

                # 如果还是没找到，打印详细的调试信息
                if not matches:
                    logger.error(f"🔍 DEBUG - API响应键: {list(data.keys())}")

                    # 检查fixtures字段
                    if 'fixtures' in data:
                        fixtures = data['fixtures']
                        logger.error(f"🔍 DEBUG - fixtures类型: {type(fixtures)}")
                        if isinstance(fixtures, dict):
                            logger.error(f"🔍 DEBUG - fixtures键: {list(fixtures.keys())}")
                            # 打印fixtures内容的前500字符
                            fixtures_str = str(fixtures)[:500]
                            logger.error(f"🔍 DEBUG - fixtures内容(前500字符): {fixtures_str}")
                        elif isinstance(fixtures, list):
                            logger.error(f"🔍 DEBUG - fixtures列表长度: {len(fixtures)}")
                            if fixtures:
                                logger.error(f"🔍 DEBUG - 第一个fixture: {fixtures[0]}")

                    # 检查tabs字段
                    if 'tabs' in data:
                        tabs = data['tabs']
                        logger.error(f"🔍 DEBUG - tabs类型: {type(tabs)}")
                        if isinstance(tabs, list) and tabs:
                            logger.error(f"🔍 DEBUG - tabs数量: {len(tabs)}")
                            for i, tab in enumerate(tabs[:3]):  # 只看前3个tab
                                logger.error(f"🔍 DEBUG - tab[{i}]键: {list(tab.keys()) if isinstance(tab, dict) else type(tab)}")

                    # 检查其他可能的比赛数据字段
                    potential_keys = ['matches', 'allMatches', 'events', 'games', 'fixturesList']
                    for key in potential_keys:
                        if key in data:
                            logger.error(f"🔍 DEBUG - 找到潜在字段 '{key}': {type(data[key])}")

                    # 打印完整响应的前1000字符用于深度分析
                    full_response_str = str(data)[:1000]
                    logger.error(f"🔍 DEBUG - 完整响应前1000字符: {full_response_str}")

                logger.info(f"✅ 找到 {len(matches)} 场比赛")
                return matches

        except Exception as e:
            logger.error(f"❌ 获取{league_name}数据失败: {e}")
            return None

    async def save_league_to_db(self, league_data: dict) -> Optional[int]:
        """保存联赛数据到数据库"""
        try:
            async with get_db_session() as conn:
                # 检查联赛是否已存在
                existing = await conn.fetchval(
                    "SELECT id FROM leagues WHERE fotmob_id = $1",
                    league_data['id']
                )
                if existing:
                    logger.info(f"📝 联赛已存在: {league_data['name']}")
                    return existing

                # 创建新联赛
                league_id = await conn.fetchval(
                    """
                    INSERT INTO leagues (name, country, fotmob_id, data_source, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, NOW(), NOW())
                    RETURNING id
                    """,
                    league_data['name'],
                    league_data.get('country', ''),
                    league_data['id'],
                    'fotmob_api'
                )

                logger.info(f"✅ 创建新联赛: {league_data['name']} (ID: {league_id})")
                return league_id

        except Exception as e:
            logger.error(f"❌ 保存联赛失败: {e}")
            return None

    async def save_match_to_db(self, match_data: dict, league_id: int) -> bool:
        """保存比赛数据到数据库"""
        try:
            async with get_db_session() as conn:
                # 提取比赛信息
                fotmob_id = match_data.get('id')
                home_team = match_data.get('home', {}).get('name', '')
                away_team = match_data.get('away', {}).get('name', '')

                # 提取比赛时间
                status_data = match_data.get('status', {})
                utc_time = status_data.get('utcTime', '')
                is_finished = status_data.get('finished', False)

                # 解析比赛时间
                match_date = datetime.now(timezone.utc)
                if utc_time:
                    try:
                        match_date = datetime.fromisoformat(utc_time.replace('Z', '+00:00'))
                    except:
                        pass

                # 确定比赛状态
                status = 'finished' if is_finished else 'scheduled'
                if status_data.get('started', False) and not is_finished:
                    status = 'live'

                if not fotmob_id or not home_team or not away_team:
                    logger.warning(f"⚠️ 比赛数据不完整: {match_data}")
                    return False

                # 检查比赛是否已存在
                existing = await conn.fetchval(
                    "SELECT id FROM matches WHERE fotmob_id = $1",
                    fotmob_id
                )
                if existing:
                    logger.debug(f"📝 比赛已存在: {fotmob_id}")
                    return True

                # 获取或创建球队
                home_team_id = await self.get_or_create_team(home_team, conn)
                away_team_id = await self.get_or_create_team(away_team, conn)

                if not home_team_id or not away_team_id:
                    logger.warning(f"⚠️ 无法创建球队: {home_team} vs {away_team}")
                    return False

                # 创建比赛记录
                await conn.execute(
                    """
                    INSERT INTO matches (
                        fotmob_id, home_team_id, away_team_id, league_id,
                        status, match_date, data_source, data_completeness,
                        home_score, away_score, created_at, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW(), NOW())
                    """,
                    fotmob_id, home_team_id, away_team_id, league_id,
                    status, match_date, 'fotmob_api', 'partial',
                    0, 0  # 初始比分为0
                )

                logger.info(f"✅ 保存比赛: {home_team} vs {away_team} (ID: {fotmob_id})")
                return True

        except Exception as e:
            logger.error(f"❌ 保存比赛失败: {e}")
            return False

    async def get_or_create_team(self, team_name: str, conn) -> Optional[int]:
        """获取或创建球队"""
        try:
            # 查找现有球队
            team_id = await conn.fetchval(
                "SELECT id FROM teams WHERE name = $1",
                team_name
            )

            if team_id:
                return team_id

            # 创建新球队
            team_id = await conn.fetchval(
                "INSERT INTO teams (name, data_source, created_at, updated_at) VALUES ($1, $2, NOW(), NOW()) RETURNING id",
                team_name, 'fotmob_api'
            )

            return team_id

        except Exception as e:
            logger.error(f"❌ 创建球队失败 {team_name}: {e}")
            return None

    async def run_collection(self):
        """运行数据采集"""
        logger.info("🚀 开始简单L1数据采集")

        total_matches = 0
        successful_leagues = 0

        for league in self.target_leagues:
            logger.info(f"\n🏆 处理联赛: {league['name']}")

            # 获取比赛数据
            matches = await self.fetch_league_matches(league['id'], league['name'])

            if not matches:
                logger.warning(f"⚠️ 无法获取{league['name']}数据")
                continue

            # 保存联赛
            league_id = await self.save_league_to_db({
                'id': league['id'],
                'name': league['name']
            })

            if not league_id:
                logger.warning(f"⚠️ 无法保存{league['name']}联赛")
                continue

            # 保存比赛
            league_matches = 0
            for match in matches:
                if await self.save_match_to_db(match, league_id):
                    league_matches += 1

            logger.info(f"✅ {league['name']}: 保存 {league_matches} 场比赛")
            total_matches += league_matches
            successful_leagues += 1

        logger.info("\n🎉 采集完成!")
        logger.info(f"📊 统计: {successful_leagues} 个联赛, {total_matches} 场比赛")

        return total_matches > 0


async def main():
    """主函数"""
    # 初始化数据库
    try:
        await initialize_database()
        logger.info("✅ 数据库初始化成功")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        return 1

    collector = SimpleL1Collector()

    try:
        success = await collector.run_collection()

        if success:
            logger.info("✅ L1数据采集成功完成")
            return 0
        else:
            logger.error("❌ L1数据采集失败")
            return 1

    except Exception as e:
        logger.error(f"❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
