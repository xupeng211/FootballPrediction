#!/usr/bin/env python3
"""验证Football-Data.org API连接脚本
Verify Football-Data.org API Connection Script.

此脚本用于验证API Key配置和网络连接是否正常。
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv

# 尝试加载.env文件
env_files = [
    project_root / ".env",
    project_root / ".env.local",
    project_root / ".env.development",
]

for env_file in env_files:
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ 已加载环境文件: {env_file}")
        break
else:
    print("⚠️  未找到.env文件，将使用系统环境变量")

# 导入适配器
try:
    from src.adapters.football import ApiFootballAdapter, FootballAdapterError, FootballAdapterConnectionError
except ImportError as e:
    print(f"❌ 导入适配器失败: {e}")
    sys.exit(1)


async def test_api_connection():
    """测试API连接."""
    print("=" * 60)
    print("🔗 Football-Data.org API 连接验证")
    print("=" * 60)

    # 检查API Key
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        print("❌ 错误: FOOTBALL_DATA_API_KEY 环境变量未设置")
        print("请设置环境变量或在.env文件中添加:")
        print("FOOTBALL_DATA_API_KEY=your_actual_api_key_here")
        return False

    if api_key == "CHANGE_THIS_FOOTBALL_DATA_API_KEY":
        print("❌ 错误: 使用了默认的占位符API Key")
        print("请替换为真实的Football-Data.org API Key")
        return False

    print(f"✅ API Key已配置 (长度: {len(api_key)})")

    # 初始化适配器
    adapter = ApiFootballAdapter()

    try:
        # 初始化适配器
        print("\n🚀 正在初始化适配器...")
        success = await adapter.initialize()
        if not success:
            print("❌ 适配器初始化失败")
            error_info = adapter.get_error_info()
            print(f"错误信息: {error_info}")
            return False
        print("✅ 适配器初始化成功")

        # 测试获取比赛数据
        print("\n⚽ 正在获取比赛数据 (英超 2024赛季)...")
        try:
            fixtures = await adapter.get_fixtures(league_code="PL", season=2024)

            print(f"✅ API请求成功! HTTP 状态码: 200")
            print(f"📊 获取到 {len(fixtures)} 场比赛数据")

            if fixtures:
                print("\n📋 前3场比赛:")
                for i, fixture in enumerate(fixtures[:3], 1):
                    home_team = fixture.get("homeTeam", {}).get("name", "未知主队")
                    away_team = fixture.get("awayTeam", {}).get("name", "未知客队")
                    utc_date = fixture.get("utcDate", "未知时间")
                    status = fixture.get("status", "未知状态")

                    print(f"  {i}. {home_team} vs {away_team}")
                    print(f"     时间: {utc_date}")
                    print(f"     状态: {status}")
                    print()

                # 打印原始JSON响应的前100个字符
                print("📄 原始JSON响应 (前100字符):")
                json_str = json.dumps(fixtures, ensure_ascii=False, indent=2)
                print(json_str[:100] + "..." if len(json_str) > 100 else json_str)
            else:
                print("⚠️  没有获取到比赛数据，可能是因为赛季没有比赛或API访问限制")

        except FootballAdapterConnectionError as e:
            print(f"❌ API连接错误: {e}")
            return False
        except FootballAdapterError as e:
            print(f"❌ 适配器错误: {e}")
            return False

        # 测试获取联赛列表
        print("\n🏆 正在获取可用联赛列表...")
        try:
            competitions = await adapter.get_competitions()
            print(f"✅ 获取到 {len(competitions)} 个联赛")

            if competitions:
                print("\n📋 前5个联赛:")
                for i, comp in enumerate(competitions[:5], 1):
                    name = comp.get("name", "未知联赛")
                    code = comp.get("code", "未知代码")
                    area = comp.get("area", {}).get("name", "未知地区")
                    print(f"  {i}. {name} ({code}) - {area}")

        except Exception as e:
            print(f"⚠️  获取联赛列表时出错: {e}")

        # 清理适配器
        await adapter.cleanup()
        print("\n✅ 适配器已清理")

        return True

    except Exception as e:
        print(f"❌ 测试过程中发生未预期的错误: {e}")
        return False


async def main():
    """主函数."""
    print("🎯 开始验证Football-Data.org API连接...")

    success = await test_api_connection()

    print("\n" + "=" * 60)
    if success:
        print("🎉 API连接验证成功！真实数据已正常获取。")
        print("🚀 您的适配器现在可以正常工作了！")
        return 0
    else:
        print("💔 API连接验证失败，请检查:")
        print("   1. API Key是否正确设置")
        print("   2. 网络连接是否正常")
        print("   3. API订阅是否有效")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)