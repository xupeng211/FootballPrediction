#!/usr/bin/env python3
"""
测试API端点的独立脚本
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# 添加项目根目录到Python路径
sys.path.insert(0, '/home/user/projects/FootballPrediction')

from src.collectors.data_sources import data_source_manager

async def test_data_sources_directly():
    """直接测试数据源管理器"""
    print("🔧 直接测试数据源管理器...")

    # 检查可用数据源
    available_sources = data_source_manager.get_available_sources()
    print(f"✅ 可用数据源: {available_sources}")

    # 测试Football-Data.org适配器
    adapter = data_source_manager.get_adapter("football_data_org")
    if adapter:
        print("✅ Football-Data.org适配器可用")

        try:
            # 测试获取少量数据
            from datetime import datetime, timedelta
            date_from = datetime.now()
            date_to = date_from + timedelta(days=3)

            matches = await adapter.get_matches(date_from=date_from, date_to=date_to)
            print(f"✅ 成功获取 {len(matches)} 场比赛")

            # 显示前2场比赛
            if matches:
                print("📊 前2场比赛:")
                for i, match in enumerate(matches[:2], 1):
                    print(f"  {i}. {match.home_team} vs {match.away_team}")
                    print(f"     联赛: {match.league}")
                    print(f"     时间: {match.match_date}")

        except Exception as e:
            print(f"❌ 获取比赛失败: {e}")
    else:
        print("❌ Football-Data.org适配器不可用")

if __name__ == "__main__":
    asyncio.run(test_data_sources_directly())