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

from src.collectors.data_sources import data_source_manager


async def test_data_sources_directly():
    """直接测试数据源管理器"""

    # 检查可用数据源
    data_source_manager.get_available_sources()

    # 测试Football-Data.org适配器
    adapter = data_source_manager.get_adapter("football_data_org")
    if adapter:

        try:
            # 测试获取少量数据
            from datetime import datetime, timedelta

            date_from = datetime.now()
            date_to = date_from + timedelta(days=3)

            matches = await adapter.get_matches(date_from=date_from, date_to=date_to)

            # 显示前2场比赛
            if matches:
                for _i, _match in enumerate(matches[:2], 1):
                    pass  # TODO: Add logger import if needed

        except Exception:
            pass  # TODO: Add logger import if needed
    else:
        pass  # TODO: Add logger import if needed


if __name__ == "__main__":
    asyncio.run(test_data_sources_directly())
