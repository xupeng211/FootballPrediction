#!/usr/bin/env python3
"""
测试API端点的独立脚本
"""

import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()

# 添加项目根目录到Python路径
sys.path.insert(0, "/home/user/projects/FootballPrediction")

import logging

from src.collectors.data_sources import data_source_manager

logger = logging.getLogger(__name__)


async def test_data_sources_directly():
    """直接测试数据源管理器"""
    logger.debug("🔧 直接测试数据源管理器...")  # TODO: Add logger import if needed

    # 检查可用数据源
    available_sources = data_source_manager.get_available_sources()
    logger.debug(
        f"✅ 可用数据源: {available_sources}"
    )  # TODO: Add logger import if needed

    # 测试Football-Data.org适配器
    adapter = data_source_manager.get_adapter("football_data_org")
    if adapter:
        logger.debug(
            "✅ Football-Data.org适配器可用"
        )  # TODO: Add logger import if needed

        try:
            # 测试获取少量数据
            from datetime import datetime, timedelta

            date_from = datetime.now()
            date_to = date_from + timedelta(days=3)

            matches = await adapter.get_matches(date_from=date_from, date_to=date_to)
            logger.debug(
                f"✅ 成功获取 {len(matches)} 场比赛"
            )  # TODO: Add logger import if needed

            # 显示前2场比赛
            if matches:
                logger.debug("📊 前2场比赛:")  # TODO: Add logger import if needed
                for i, match in enumerate(matches[:2], 1):
                    logger.debug(
                        f"  {i}. {match.home_team} vs {match.away_team}"
                    )  # TODO: Add logger import if needed
                    logger.debug(
                        f"     联赛: {match.league}"
                    )  # TODO: Add logger import if needed
                    logger.debug(
                        f"     时间: {match.match_date}"
                    )  # TODO: Add logger import if needed

        except Exception as e:
            logger.debug(f"❌ 获取比赛失败: {e}")  # TODO: Add logger import if needed
    else:
        logger.debug(
            "❌ Football-Data.org适配器不可用"
        )  # TODO: Add logger import if needed


if __name__ == "__main__":
    asyncio.run(test_data_sources_directly())
