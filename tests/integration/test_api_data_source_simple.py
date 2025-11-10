#!/usr/bin/env python3
"""
简单的数据源API测试脚本（不依赖数据库）
"""

import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()

# 添加项目根目录到Python路径
sys.path.insert(0, "/home/user/projects/FootballPrediction")

from src.collectors.data_sources import data_source_manager


async def test_data_source_api():
    """测试数据源API功能"""

    try:
        # 检查可用数据源
        available_sources = data_source_manager.get_available_sources()

        # 测试Football-Data.org适配器
        adapter = data_source_manager.get_adapter("football_data_org")
        if not adapter:
            return False

        # 测试获取比赛数据
        from datetime import datetime, timedelta

        date_from = datetime.now()
        date_to = date_from + timedelta(days=7)

        matches = await adapter.get_matches(date_from=date_from, date_to=date_to)

        # 测试获取球队数据
        teams = await adapter.get_teams()

        # 构造API响应格式
        {
            "success": True,
            "data_source": "football_data_org",
            "test_matches": len(matches),
            "test_teams": len(teams),
            "message": "数据源 football_data_org 测试成功",
            "available_sources": available_sources,
            "timestamp": datetime.now().isoformat(),
        }

        # 显示前3场比赛示例
        if matches:
            for _i, _match in enumerate(matches[:3], 1):
                pass  # TODO: Add logger import if needed

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_data_source_api())
    if success:
        pass  # TODO: Add logger import if needed
    else:
        pass  # TODO: Add logger import if needed
