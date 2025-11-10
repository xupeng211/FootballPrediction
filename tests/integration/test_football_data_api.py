#!/usr/bin/env python3
"""
测试Football-Data.org API连接
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, "/home/user/projects/FootballPrediction")

from dotenv import load_dotenv

load_dotenv()

from src.collectors.data_sources import data_source_manager


async def test_football_data_api():
    """测试Football-Data.org API连接"""

    # 检查API密钥
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        return False

    # 获取Football-Data.org适配器
    adapter = data_source_manager.get_adapter("football_data_org")
    if not adapter:
        return False

    try:
        # 测试获取比赛数据
        date_from = datetime.now()
        date_to = date_from + timedelta(days=7)

        matches = await adapter.get_matches(date_from=date_from, date_to=date_to)

        # 显示前3场比赛
        if matches:
            for _i, _match in enumerate(matches[:3], 1):
                pass  # TODO: Add logger import if needed

        # 测试获取球队数据
        teams = await adapter.get_teams()

        # 显示前5支球队
        if teams:
            for _i, team in enumerate(teams[:5], 1):
                if team.venue:
                    pass  # TODO: Add logger import if needed

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


async def main():
    """主测试函数"""

    success = await test_football_data_api()

    if success:
        pass  # TODO: Add logger import if needed
    else:
        pass  # TODO: Add logger import if needed


if __name__ == "__main__":
    asyncio.run(main())
