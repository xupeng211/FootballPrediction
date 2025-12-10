#!/usr/bin/env python3
"""
手动L2采集测试 - 使用数据库中的真实比赛ID
Manual L2 Collection Test - Using Real Match ID from Database
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "src"))

from collectors.fotmob_api_collector import FotMobAPICollector
from database.async_manager import get_db_session
from sqlalchemy import text

async def test_single_match():
    """测试单个比赛的L2数据采集"""

    # 使用数据库中找到的真实比赛ID
    TEST_MATCH_ID = "87_14_5608"  # 从数据库中获取的ID

    print(f"🚀 开始L2采集测试")
    print(f"📊 测试比赛ID: {TEST_MATCH_ID}")
    print("="*50)

    # 初始化采集器
    collector = FotMobAPICollector(
        max_concurrent=5,
        timeout=30,
        enable_proxy=False,  # 暂时禁用代理以简化测试
        enable_jitter=True
    )

    try:
        print("🔧 初始化采集器...")
        await collector.initialize()
        print("✅ 采集器初始化完成")

        print(f"🌐 开始采集比赛数据: {TEST_MATCH_ID}")
        match_data = await collector.collect_match_details(TEST_MATCH_ID)

        if match_data:
            print("✅ 数据采集成功!")
            print("\n📊 采集到的关键数据:")
            print(f"  主队xG: {match_data.xg_home}")
            print(f"  客队xG: {match_data.xg_away}")
            print(f"  比分: {match_data.home_score}-{match_data.away_score}")
            print(f"  状态: {match_data.status}")

            # 检查JSON数据
            if match_data.stats_json:
                print(f"  技术统计字段数: {len(match_data.stats_json)}")
                if 'xg' in match_data.stats_json:
                    print(f"  xG统计: {match_data.stats_json['xg']}")

            if match_data.lineups_json:
                print(f"  阵容数据部分数: {len(match_data.lineups_json)}")

            if match_data.match_info:
                print(f"  比赛信息部分数: {len(match_data.match_info)}")
                if 'home_team_name' in match_data.match_info:
                    print(f"  主队名称: {match_data.match_info['home_team_name']}")
                if 'away_team_name' in match_data.match_info:
                    print(f"  客队名称: {match_data.match_info['away_team_name']}")

            print(f"\n🎯 Super Greedy Mode 环境数据:")
            if match_data.environment_json:
                env = match_data.environment_json
                print(f"  裁判信息: {bool(env.get('referee'))}")
                print(f"  场地信息: {bool(env.get('venue'))}")
                print(f"  天气信息: {bool(env.get('weather'))}")
                print(f"  主帅信息: {bool(env.get('managers'))}")

            # 显示采集器统计
            stats = collector.get_stats()
            print(f"\n📈 采集器统计:")
            print(f"  请求次数: {stats['requests_made']}")
            print(f"  成功请求: {stats['successful_requests']}")
            print(f"  数据大小: {stats['total_data_size']} 字节")

            return True

        else:
            print("❌ 数据采集失败")
            return False

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await collector.close()

if __name__ == "__main__":
    success = asyncio.run(test_single_match())

    print("\n" + "="*50)
    if success:
        print("🎉 L2采集器冒烟测试: 通过")
        sys.exit(0)
    else:
        print("💥 L2采集器冒烟测试: 失败")
        sys.exit(1)