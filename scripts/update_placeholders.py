#!/usr/bin/env python3
"""
更新占位符球队信息
Update Placeholder Team Information

通过重新采集英超所有球队数据来更新占位符球队信息。
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.collectors.football_data_collector import FootballDataCollector
from src.database.connection import DatabaseManager
from src.database.models.team import Team

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def update_teams_from_premier_league():
    """从英超联赛重新采集所有球队数据并更新占位符球队"""

    # 检查API密钥
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        logger.error("❌ 未设置 FOOTBALL_DATA_API_KEY 环境变量")
        sys.exit(1)

    logger.info(f"✅ API密钥已配置: {api_key[:8]}...")

    # 初始化数据库连接和采集器
    db_manager = DatabaseManager()
    db_manager.initialize()

    try:
        async with db_manager.get_async_session() as session:
            # 获取所有占位符球队
            stmt = select(Team).where(Team.name.like('Team %'))
            result = await session.execute(stmt)
            placeholder_teams = result.scalars().all()

            if not placeholder_teams:
                logger.info("🎉 没有发现占位符球队")
                return

            # 创建external_id到数据库ID的映射
            team_mapping = {}
            for team in placeholder_teams:
                team_id_str = team.name.split(' ')[1] if len(team.name.split(' ')) > 1 else None
                if team_id_str and team_id_str.isdigit():
                    external_id = int(team_id_str)
                    team_mapping[external_id] = team.id

            logger.info(f"📋 发现 {len(team_mapping)} 个占位符球队需要更新")
            logger.info(f"🗺️ External IDs映射: {list(team_mapping.keys())}")

        # 使用采集器获取英超所有球队数据
        collector = FootballDataCollector()

        # 英超联赛ID是2021
        logger.info("🔄 正在采集英超球队数据...")
        result = await collector.collect_teams(league_id=2021)

        if not result.success:
            logger.error(f"❌ 采集球队数据失败: {result.error}")
            return

        teams_data = result.data.get("teams", [])
        logger.info(f"✅ 成功采集 {len(teams_data)} 支球队")

        # 更新占位符球队信息
        updated_count = 0
        failed_count = 0

        async with db_manager.get_async_session() as session:
            for team_data in teams_data:
                external_id = team_data.get("id")

                if external_id in team_mapping:
                    team_db_id = team_mapping[external_id]

                    try:
                        # 准备更新数据
                        update_data = {
                            'name': team_data.get('name', f'Team {external_id}'),
                            'short_name': team_data.get('shortName'),
                            'country': team_data.get('area', {}).get('name', 'England'),
                            'venue': team_data.get('venue'),
                            'website': team_data.get('website'),
                            'founded_year': team_data.get('founded')
                        }

                        # 执行数据库更新
                        stmt = update(Team).where(Team.id == team_db_id).values(**update_data)
                        await session.execute(stmt)
                        await session.commit()

                        logger.info(f"✅ 更新成功: {update_data['name']} (ID: {team_db_id})")
                        updated_count += 1

                    except Exception as e:
                        logger.error(f"❌ 更新球队 {external_id} 失败: {e}")
                        await session.rollback()
                        failed_count += 1

                    # 添加延迟以遵守API速率限制
                    await asyncio.sleep(0.5)
                else:
                    logger.debug(f"跳过非占位符球队: {team_data.get('name')} (ID: {external_id})")

        # 输出最终结果
        logger.info("🎉 占位符球队信息更新完成!")
        logger.info(f"   ✅ 成功更新: {updated_count} 个球队")
        logger.info(f"   ❌ 更新失败: {failed_count} 个球队")
        if team_mapping:
            logger.info(f"   📊 成功率: {(updated_count / len(team_mapping) * 100):.1f}%")

    except Exception as e:
        logger.error(f"❌ 更新过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(update_teams_from_premier_league())