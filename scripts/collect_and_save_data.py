#!/usr/bin/env python3
"""
数据采集并保存到数据库脚本
Data Collection and Database Ingestion Script
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataCollectionService:
    """数据采集和保存服务"""

    def __init__(self):
        """初始化服务"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def save_teams_to_database(self, teams_data):
        """保存球队数据到数据库"""
        try:
            from src.database.connection import DatabaseManager

            # 初始化数据库连接
            db_manager = DatabaseManager()
            db_manager.initialize()

            from src.database.models.team import Team
            from sqlalchemy import select

            async with db_manager.get_async_session() as session:
                saved_count = 0

                for team_data in teams_data:
                    # 检查球队是否已存在
                    query = select(Team).where(Team.name == team_data.get('name'))
                    result = await session.execute(query)
                    existing_team = result.scalar_one_or_none()

                    if existing_team:
                        self.logger.debug(f"球队 {team_data.get('name')} 已存在，跳过")
                        continue

                    # 创建新球队记录
                    team = Team(
                        name=team_data.get('name'),
                        short_name=team_data.get('short_name') or team_data.get('shortName')[:50],
                        country=team_data.get('country') or 'Unknown',
                        founded_year=team_data.get('founded') or team_data.get('foundedYear'),
                        venue=team_data.get('venue') or team_data.get('stadium'),
                        website=team_data.get('website') or team_data.get('website'),
                    )

                    session.add(team)
                    saved_count += 1

                await session.commit()
                self.logger.info(f"✅ 成功保存 {saved_count} 支球队到数据库")
                return saved_count

        except Exception as e:
            self.logger.error(f"❌ 保存球队数据失败: {e}")
            raise

    async def ensure_team_exists(self, team_id: int, session) -> bool:
        """确保球队存在于数据库中，如果不存在则采集并保存"""
        try:
            from src.database.models.team import Team
            from sqlalchemy import select

            # 检查球队是否已存在
            query = select(Team).where(Team.id == team_id)
            result = await session.execute(query)
            existing_team = result.scalar_one_or_none()

            if existing_team:
                return True

            self.logger.info(f"发现缺失的球队 ID: {team_id}，正在采集...")

            # 使用采集器获取球队详情
            from src.collectors.football_data_collector import FootballDataCollector
            collector = FootballDataCollector()

            # 采集特定球队信息（这里我们使用一个通用的方法，因为API可能不支持单个球队查询）
            # 作为替代方案，我们创建一个占位符球队记录
            placeholder_team = Team(
                id=team_id,
                name=f"Team {team_id}",
                short_name=f"T{team_id}",
                country="Unknown",
                founded_year=None,
                venue=None,
                website=None,
            )

            session.add(placeholder_team)
            await session.flush()  # 立即保存但不提交
            self.logger.info(f"✅ 创建占位符球队: {placeholder_team.name} (ID: {team_id})")

            return True

        except Exception as e:
            self.logger.error(f"❌ 确保球队存在失败 (ID: {team_id}): {e}")
            return False

    async def save_matches_to_database(self, matches_data):
        """保存比赛数据到数据库"""
        try:
            from src.database.connection import DatabaseManager

            # 初始化数据库连接
            db_manager = DatabaseManager()
            db_manager.initialize()

            from src.database.models.match import Match
            from sqlalchemy import select

            async with db_manager.get_async_session() as session:
                saved_count = 0

                for match_data in matches_data:
                    home_team_id = match_data.get('homeTeam', {}).get('id')
                    away_team_id = match_data.get('awayTeam', {}).get('id')

                    # 确保两支球队都存在
                    if not await self.ensure_team_exists(home_team_id, session):
                        self.logger.warning(f"跳过比赛：无法确保主队存在 (ID: {home_team_id})")
                        continue

                    if not await self.ensure_team_exists(away_team_id, session):
                        self.logger.warning(f"跳过比赛：无法确保客队存在 (ID: {away_team_id})")
                        continue

                    # 检查比赛是否已存在
                    query = select(Match).where(
                        (Match.home_team_id == home_team_id) &
                        (Match.away_team_id == away_team_id)
                    )
                    result = await session.execute(query)
                    existing_match = result.scalar_one_or_none()

                    if existing_match:
                        self.logger.debug(f"比赛 {match_data.get('homeTeam', {}).get('name')} vs {match_data.get('awayTeam', {}).get('name')} 已存在，跳过")
                        continue

                    # 创建新比赛记录
                    from datetime import datetime
                    from dateutil import parser as date_parser

                    # 处理日期字符串
                    match_date_str = match_data.get('utcDate')
                    match_date = None
                    if match_date_str:
                        try:
                            # 解析日期并移除时区信息
                            parsed_date = date_parser.parse(match_date_str)
                            if parsed_date.tzinfo:
                                # 移除时区信息，只保留datetime
                                match_date = parsed_date.replace(tzinfo=None)
                            else:
                                match_date = parsed_date
                        except Exception:
                            match_date = None

                    # 处理season字段
                    season_data = match_data.get('season')
                    season = '2024-2025'
                    if isinstance(season_data, dict):
                        season = str(season_data.get('id', '2024-2025'))
                    elif isinstance(season_data, str):
                        season = season_data
                    elif season_data is not None:
                        season = str(season_data)

                    match = Match(
                        home_team_id=home_team_id,
                        away_team_id=away_team_id,
                        home_score=match_data.get('score', {}).get('fullTime', {}).get('home'),
                        away_score=match_data.get('score', {}).get('fullTime', {}).get('away'),
                        status=match_data.get('status', 'unknown'),
                        match_date=match_date,
                        venue=match_data.get('venue'),
                        season=season,
                    )

                    session.add(match)
                    saved_count += 1

                await session.commit()
                self.logger.info(f"✅ 成功保存 {saved_count} 场比赛到数据库")
                return saved_count

        except Exception as e:
            self.logger.error(f"❌ 保存比赛数据失败: {e}")
            raise


async def collect_and_save_data():
    """采集并保存数据的主函数"""
    try:
        from src.collectors.football_data_collector import FootballDataCollector

        logger.info("🚀 开始数据采集和保存流程...")

        # 检查API密钥
        api_key = os.getenv('FOOTBALL_DATA_API_KEY')
        if not api_key:
            logger.error("❌ FOOTBALL_DATA_API_KEY 环境变量未设置")
            return False

        logger.info(f"✅ API密钥已配置: {api_key[:8]}...")

        # 初始化采集器和服务
        collector = FootballDataCollector()
        service = DataCollectionService()
        logger.info("✅ 采集器和数据库服务初始化成功")

        # 采集联赛数据
        logger.info("🔄 正在采集联赛数据...")
        leagues_result = await collector.collect_leagues(areas=[2077])  # 2077 = England

        if not leagues_result.success:
            logger.error(f"❌ 采集联赛数据失败: {leagues_result.error}")
            return False

        leagues = leagues_result.data.get("competitions", [])
        logger.info(f"✅ 成功采集 {len(leagues)} 个联赛")

        # 采集球队数据
        logger.info("🔄 正在采集球队数据...")
        teams_result = await collector.collect_teams()

        if not teams_result.success:
            logger.error(f"❌ 采集球队数据失败: {teams_result.error}")
            return False

        teams = teams_result.data.get("teams", [])
        logger.info(f"✅ 成功采集 {len(teams)} 支球队")

        # 保存球队数据到数据库
        logger.info("💾 正在保存球队数据到数据库...")
        saved_teams = await service.save_teams_to_database(teams)

        # 采集比赛数据（选择Premier League，ID=2021）
        premier_league_id = None
        for league in leagues:
            if league.get('name') == 'Premier League':
                premier_league_id = league['id']
                break

        if premier_league_id:
            logger.info(f"🔄 正在采集Premier League比赛数据 (ID: {premier_league_id})...")
            matches_result = await collector.collect_matches(
                league_id=premier_league_id,
                limit=20
            )

            if matches_result.success:
                matches = matches_result.data.get("matches", [])
                logger.info(f"✅ 成功采集 {len(matches)} 场比赛")

                logger.info("💾 正在保存比赛数据到数据库...")
                saved_matches = await service.save_matches_to_database(matches)

                logger.info(f"🎉 数据采集和保存完成!")
                logger.info(f"   - 保存球队: {saved_teams} 支")
                logger.info(f"   - 保存比赛: {saved_matches} 场")
                return True
            else:
                logger.warning(f"⚠️ 采集Premier League比赛数据失败: {matches_result.error}")
                return saved_teams > 0  # 只要球队保存成功就算部分成功

        return saved_teams > 0

    except Exception as e:
        logger.error(f"❌ 数据采集和保存失败: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(collect_and_save_data())