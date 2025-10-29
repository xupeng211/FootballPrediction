#!/usr/bin/env python3
"""
简单的数据源API测试脚本（不依赖数据库）
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# 添加项目根目录到Python路径
sys.path.insert(0, "/home/user/projects/FootballPrediction")

from src.collectors.data_sources import data_source_manager


async def test_data_source_api():
    """测试数据源API功能"""
    print("🔧 测试数据源API功能...")

    try:
        # 检查可用数据源
        available_sources = data_source_manager.get_available_sources()
        print(f"✅ 可用数据源: {available_sources}")

        # 测试Football-Data.org适配器
        print("\n📊 测试Football-Data.org适配器...")
        adapter = data_source_manager.get_adapter("football_data_org")
        if not adapter:
            print("❌ Football-Data.org适配器不可用")
            return False

        print("✅ Football-Data.org适配器可用")

        # 测试获取比赛数据
        from datetime import datetime, timedelta

        date_from = datetime.now()
        date_to = date_from + timedelta(days=7)

        matches = await adapter.get_matches(date_from=date_from, date_to=date_to)
        print(f"✅ 成功获取 {len(matches)} 场比赛")

        # 测试获取球队数据
        teams = await adapter.get_teams()
        print(f"✅ 成功获取 {len(teams)} 支球队")

        # 构造API响应格式
        response = {
            "success": True,
            "data_source": "football_data_org",
            "test_matches": len(matches),
            "test_teams": len(teams),
            "message": f"数据源 football_data_org 测试成功",
            "available_sources": available_sources,
            "timestamp": datetime.now().isoformat(),
        }

        print(f"\n🎉 数据源测试成功！")
        print(f"📋 测试结果:")
        print(f"   数据源: {response['data_source']}")
        print(f"   测试比赛数: {response['test_matches']}")
        print(f"   测试球队数: {response['test_teams']}")
        print(f"   可用数据源: {response['available_sources']}")

        # 显示前3场比赛示例
        if matches:
            print(f"\n📊 前3场比赛示例:")
            for i, match in enumerate(matches[:3], 1):
                print(f"  {i}. {match.home_team} vs {match.away_team}")
                print(f"     联赛: {match.league}")
                print(f"     时间: {match.match_date}")
                print(f"     状态: {match.status}")

        return True

    except Exception as e:
        print(f"❌ 数据源测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_data_source_api())
    if success:
        print(f"\n✅ 数据源API功能验证成功！")
        print(f"📝 状态:")
        print(f"   ✅ Football-Data.org API连接正常")
        print(f"   ✅ 可以获取真实比赛数据")
        print(f"   ✅ 数据适配器工作正常")
        print(f"\n🚀 准备集成到完整API端点！")
    else:
        print(f"\n❌ 数据源API功能验证失败！")
