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
    print("🔧 测试Football-Data.org API连接...")

    # 检查API密钥
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        print("❌ 未找到FOOTBALL_DATA_API_KEY环境变量")
        return False

    print(f"✅ API密钥已配置: {api_key[:10]}...{api_key[-4:]}")

    # 获取Football-Data.org适配器
    adapter = data_source_manager.get_adapter("football_data_org")
    if not adapter:
        print("❌ Football-Data.org适配器不可用")
        return False

    print("✅ Football-Data.org适配器已创建")

    try:
        # 测试获取比赛数据
        print("📊 测试获取比赛数据...")
        date_from = datetime.now()
        date_to = date_from + timedelta(days=7)

        matches = await adapter.get_matches(date_from=date_from, date_to=date_to)
        print(f"✅ 成功获取 {len(matches)} 场比赛")

        # 显示前3场比赛
        if matches:
            print("📊 前3场比赛示例:")
            for i, match in enumerate(matches[:3], 1):
                print(f"  {i}. {match.home_team} vs {match.away_team}")
                print(f"     联赛: {match.league}")
                print(f"     时间: {match.match_date}")
                print(f"     状态: {match.status}")

        # 测试获取球队数据
        print("\n⚽ 测试获取球队数据...")
        teams = await adapter.get_teams()
        print(f"✅ 成功获取 {len(teams)} 支球队")

        # 显示前5支球队
        if teams:
            print("⚽ 前5支球队示例:")
            for i, team in enumerate(teams[:5], 1):
                print(f"  {i}. {team.name} ({team.short_name})")
                if team.venue:
                    print(f"     主场: {team.venue}")

        print(f"\n🎉 Football-Data.org API测试成功！")
        return True

    except Exception as e:
        print(f"❌ Football-Data.org API测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("🚀 开始Football-Data.org API连接测试...")
    print("=" * 50)

    success = await test_football_data_api()

    print("\n" + "=" * 50)
    if success:
        print("🎉 API连接测试成功！系统已准备好使用真实数据源！")
        print("\n📝 下一步:")
        print("✅ 可以通过API端点收集真实比赛数据")
        print("✅ 数据集成系统完全可用")
        print("✅ 前端可以显示真实比赛信息")
    else:
        print("❌ API连接测试失败，请检查配置")
        print("\n🔧 故障排除:")
        print("1. 检查API密钥是否正确")
        print("2. 检查网络连接")
        print("3. 确认Football-Data.org服务状态")


if __name__ == "__main__":
    asyncio.run(main())
