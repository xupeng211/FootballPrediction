#!/usr/bin/env python3
"""
简单的Football-Data.org API测试
Simple Football-Data.org API Test
"""

import asyncio
import aiohttp
import json
from datetime import datetime

API_KEY = 'ed809154dc1f422da46a18d8961a98a0'
BASE_URL = 'https://api.football-data.org/v4'


async def test_api():
    """测试API基本功能"""
    print("🚀 开始测试 Football-Data.org API")
    print("=" * 50)

    headers = {
        'X-Auth-Token': API_KEY,
        'Content-Type': 'application/json'
    }

    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        try:
            # 测试1: 获取联赛列表
            print("\n1️⃣ 测试获取联赛列表...")
            async with session.get(f"{BASE_URL}/competitions") as response:
                if response.status == 200:
                    data = await response.json()
                    competitions = data.get('competitions', [])
                    print(f"✅ 成功获取 {len(competitions)} 个联赛")

                    # 显示前5个联赛
                    for i, comp in enumerate(competitions[:5]):
                        print(f"   {i+1}. {comp.get('name')} ({comp.get('code')})")
                else:
                    print(f"❌ 获取联赛失败: {response.status}")
                    return False

            # 测试2: 获取英超球队
            print("\n2️⃣ 测试获取英超球队...")
            async with session.get(f"{BASE_URL}/competitions/2021/teams") as response:
                if response.status == 200:
                    data = await response.json()
                    teams = data.get('teams', [])
                    print(f"✅ 成功获取 {len(teams)} 支英超球队")

                    # 显示前5支球队
                    for i, team in enumerate(teams[:5]):
                        print(f"   {i+1}. {team.get('name')} ({team.get('shortName')})")
                else:
                    print(f"❌ 获取球队失败: {response.status}")
                    return False

            # 测试3: 获取即将开始的比赛
            print("\n3️⃣ 测试获取即将开始的比赛...")
            params = {
                'status': 'SCHEDULED',
                'limit': 5
            }
            async with session.get(f"{BASE_URL}/competitions/2021/matches", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    matches = data.get('matches', [])
                    print(f"✅ 成功获取 {len(matches)} 场即将开始的比赛")

                    # 显示比赛信息
                    for i, match in enumerate(matches):
                        home_team = match.get('homeTeam', {}).get('name', 'Unknown')
                        away_team = match.get('awayTeam', {}).get('name', 'Unknown')
                        match_date = match.get('utcDate', 'Unknown')
                        print(f"   {i+1}. {home_team} vs {away_team}")
                        print(f"      时间: {match_date}")
                else:
                    print(f"❌ 获取比赛失败: {response.status}")
                    return False

            # 测试4: 获取最近的比赛结果
            print("\n4️⃣ 测试获取最近的比赛结果...")
            params = {
                'status': 'FINISHED',
                'limit': 3
            }
            async with session.get(f"{BASE_URL}/competitions/2021/matches", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    matches = data.get('matches', [])
                    print(f"✅ 成功获取 {len(matches)} 场最近的比赛结果")

                    # 显示比赛结果
                    for i, match in enumerate(matches):
                        home_team = match.get('homeTeam', {}).get('name', 'Unknown')
                        away_team = match.get('awayTeam', {}).get('name', 'Unknown')
                        score = match.get('score', {})
                        full_time = score.get('fullTime', {})
                        home_score = full_time.get('home', 0)
                        away_score = full_time.get('away', 0)
                        print(f"   {i+1}. {home_team} {home_score} - {away_score} {away_team}")
                else:
                    print(f"❌ 获取比赛结果失败: {response.status}")
                    return False

            print("\n" + "=" * 50)
            print("🎉 所有API测试通过！")
            print("✅ Football-Data.org API 连接正常")
            print("✅ 数据获取功能正常")
            print("✅ 可以开始进行数据集成")

            return True

        except aiohttp.ClientError as e:
            print(f"❌ 网络错误: {e}")
            return False
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析错误: {e}")
            return False
        except Exception as e:
            print(f"❌ 未知错误: {e}")
            return False


async def main():
    """主函数"""
    start_time = datetime.now()

    success = await test_api()

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"\n⏱️  测试耗时: {duration:.2f} 秒")

    if success:
        print("\n🚀 Issue #178 实施状态: ✅ 第一阶段完成")
        print("   - API连接已验证")
        print("   - 数据获取已测试")
        print("   - 可以进入第二阶段：数据采集器实现")
    else:
        print("\n❌ 测试失败，请检查API密钥或网络连接")


if __name__ == "__main__":
    asyncio.run(main())