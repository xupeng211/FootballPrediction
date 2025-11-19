#!/usr/bin/env python3
"""
测试API端点的独立脚本
"""

import pytest

import asyncio
import sys
from datetime import datetime, timedelta

# 环境变量和路径设置
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# 添加项目根目录到Python路径
sys.path.insert(0, "/home/user/projects/FootballPrediction")

# 在路径设置后导入项目模块
try:
    from src.collectors.data_sources import data_source_manager
except ImportError:
    # Mock data_source_manager if import fails
    class MockDataSourceManager:
        def get_all_sources(self):
            return []

    data_source_manager = MockDataSourceManager()

# 添加项目根目录到Python路径
sys.path.insert(0, "/home/user/projects/FootballPrediction")


@pytest.mark.asyncio


async def test_data_sources_directly():
    """直接测试数据源管理器"""

    # 检查可用数据源
    data_source_manager.get_available_sources()

    # 测试Football-Data.org适配器
    adapter = data_source_manager.get_adapter("football_data_org")
    if adapter:
        try:
            # 测试获取少量数据

            date_from = datetime.now()
            date_to = date_from + timedelta(days=3)

            matches = await adapter.get_matches(date_from=date_from, date_to=date_to)

            # 显示前2场比赛
            if matches:
                for _i, _match in enumerate(matches[:2], 1):
                    pass

        except Exception:
            pass
    else:
        pass


if __name__ == "__main__":
    asyncio.run(test_data_sources_directly())
