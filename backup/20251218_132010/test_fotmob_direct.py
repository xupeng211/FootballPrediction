#!/usr/bin/env python3
"""
FotMob API 直接连接测试
实弹测试：验证外部API访问能力和数据抓取功能
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime

# FotMob API Headers (Production Headers)
FOTMOB_HEADERS = {
    'X-MAS': 'eyJib2R5Ijp7InVybCI6Ii9hcGkvZGF0YS9sZWFndWVzP2lkPTg3IiwiY29kZSI6MTc2NTEyMTc0OTUyNSwiZm9vIjoicHJvZHVjdGlvbjo0MjhmYTAzNTVmMDljYTg4Zjk3YjE3OGViNWE3OWVmMGNmYmQwZGZjIn0sInNpZ25hdHVyZSI6IkIwQzkyMzkxMTM4NTdCNUFBMjk5Rjc5M0QxOTYwRkZCIn0=',
    'X-FOO': 'eyJmb28iOiJwcm9kdWN0aW9uOjQyOGZhMDM1NWYwOWNhODhmOTdiMTc4ZWI1YTc5ZWYwY2ZiZDBkZmMiLCJ0aW1lc3RhbXAiOjE3NjUxMjE4MTJ9',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

async def test_fotmob_api():
    """测试FotMob API连接和数据抓取"""
    print("🌍 测试FotMob API连接...")

    # 测试英超联赛数据
    premier_league_url = "https://www.fotmob.com/api/leagues?id=87"

    try:
        async with aiohttp.ClientSession() as session:
            # 设置代理
            connector = aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=30)

            print(f"🔗 请求URL: {premier_league_url}")
            print(f"🔧 使用代理: {os.getenv('HTTP_PROXY', 'None')}")

            async with session.get(
                premier_league_url,
                headers=FOTMOB_HEADERS,
                timeout=timeout
            ) as response:

                print(f"📊 响应状态码: {response.status}")

                if response.status == 200:
                    data = await response.json()

                    # 解析关键数据
                    league_name = data.get('name', 'Unknown League')
                    total_matches = data.get('matches', {}).get('allMatchesCount', 0)

                    print(f"✅ API连接成功！")
                    print(f"🏆 联赛名称: {league_name}")
                    print(f"📈 总比赛数: {total_matches}")

                    # 获取一些比赛数据
                    matches = data.get('matches', {}).get('allMatches', [])
                    if matches:
                        print(f"\n⚽ 最近比赛数据 (前3场):")
                        for i, match in enumerate(matches[:3]):
                            home_team = match.get('home', {}).get('name', 'Unknown')
                            away_team = match.get('away', {}).get('name', 'Unknown')
                            status = match.get('status', {}).get('reason', {}).get('short', 'Unknown')
                            print(f"  {i+1}. {home_team} vs {away_team} - 状态: {status}")

                    return True

                else:
                    print(f"❌ API请求失败，状态码: {response.status}")
                    error_text = await response.text()
                    print(f"错误详情: {error_text[:200]}...")
                    return False

    except Exception as e:
        print(f"❌ API连接异常: {e}")
        return False

async def test_basic_connectivity():
    """测试基本网络连接"""
    print("🌐 测试基本网络连接...")

    test_urls = [
        "https://httpbin.org/get",
        "https://www.google.com"
    ]

    for url in test_urls:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    print(f"✅ {url} - 状态码: {response.status}")
        except Exception as e:
            print(f"❌ {url} - 连接失败: {e}")
            return False

    return True

async def main():
    """主测试函数"""
    print("🚀 FotMob API 实弹测试")
    print("=" * 50)
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 代理配置: {os.getenv('HTTP_PROXY', 'None')}")
    print("=" * 50)

    # 基本连接测试
    basic_ok = await test_basic_connectivity()

    if basic_ok:
        print("\n" + "=" * 50)
        # FotMob API测试
        fotmob_ok = await test_fotmob_api()

        print("\n" + "=" * 50)
        if fotmob_ok:
            print("🎉 实弹测试成功！FotMob数据抓取正常工作！")
            print("🥂 香槟时间到了！系统完全就绪！")
            return 0
        else:
            print("❌ FotMob API测试失败")
            return 1
    else:
        print("❌ 基本网络连接测试失败")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))