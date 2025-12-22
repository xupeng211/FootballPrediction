#!/usr/bin/env python3
"""
L1数据采集脚本 - 只采集比赛索引，不进行L2/L3
目标：快速积累1000+场真数据

作者: Claude Code (高级数据采集工程师)
版本: V9.6-StepA-L1Only
日期: 2025-12-22
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 多联赛收割清单
LEAGUES = [
    {"id": 47, "name": "Premier League", "season": "2023/24"},
    {"id": 87, "name": "La Liga", "season": "2023/24"},
    {"id": 54, "name": "Bundesliga", "season": "2023/24"},
    {"id": 47, "name": "Premier League", "season": "2024/25"},
    {"id": 87, "name": "La Liga", "season": "2024/25"},
    {"id": 54, "name": "Bundesliga", "season": "2024/25"},
]

headers = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "referer": "https://www.fotmob.com/",
    "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Linux"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "x-mas": "Q29udGVudC1UeXBlOiBhcHBsaWNhdGlvbi9qc29uOyBjaGFyc2V0PXV0Zi04",
    "x-foo": "aHR0cHM6Ly93d3cuZm90bW9iLmNvbS8=",
}

async def collect_league_l1(league_id: int, league_name: str, season: str) -> int:
    """采集单个联赛的L1数据"""
    print(f"\n🏆 开始采集: {league_name} {season}")

    url = f"https://www.fotmob.com/api/leagues?id={league_id}&type=league&season={season}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()

                    # 获取比赛列表
                    fixtures = data.get("fixtures", {})
                    matches = fixtures.get("allMatches", [])

                    print(f"  📊 找到 {len(matches)} 场比赛")

                    # 保存到JSON文件
                    output_file = f"/home/user/projects/FootballPrediction/data/l1_{league_name.replace(' ', '_').lower()}_{season.replace('/', '_')}.json"

                    with open(output_file, 'w') as f:
                        json.dump({
                            "league_id": league_id,
                            "league_name": league_name,
                            "season": season,
                            "matches": matches,
                            "collected_at": datetime.now().isoformat()
                        }, f, indent=2)

                    print(f"  ✅ 数据已保存: {output_file}")
                    return len(matches)

                else:
                    print(f"  ❌ 采集失败: HTTP {response.status}")
                    return 0

    except Exception as e:
        print(f"  ❌ 采集异常: {e}")
        return 0

async def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("🚀 L1数据采集器 - 只采集比赛索引")
    print("🎯 目标: 快速积累1000+场真数据")
    print("=" * 80)

    total_matches = 0

    for i, league in enumerate(LEAGUES, 1):
        print(f"\n🔄 进度: {i}/{len(LEAGUES)} - {league['name']} {league['season']}")

        count = await collect_league_l1(league['id'], league['name'], league['season'])
        total_matches += count

    print("\n" + "=" * 80)
    print("📊 L1数据采集完成")
    print("=" * 80)
    print(f"✅ 总计采集: {total_matches} 场比赛")
    print(f"📁 数据文件: /home/user/projects/FootballPrediction/data/l1_*.json")

    if total_matches >= 1000:
        print(f"\n🎉 目标达成! 已采集 {total_matches} 场真数据")
    else:
        print(f"\n⚠️  距离1000场目标还需: {max(0, 1000 - total_matches)} 场")

    return total_matches

if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\n✅ L1采集完成，共 {result} 场比赛")
