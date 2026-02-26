#!/usr/bin/env python3
"""[Genesis.FixSeasonID] 现场采样脚本 - 检查 FotMob API 返回的真实赛季字符串

运行: python scripts/production/check_fotmob_api.py
"""
import asyncio
import aiohttp
import json
from datetime import datetime

async def check_fotmob_api():
    """检查 FotMob API 返回的赛季数据"""
    print("[Genesis.FixSeasonID] ==================== 现场采样开始 ====================")
    print()

    # 英超联赛 ID
    league_id = 47
    url = f"https://www.fotmob.com/api/leagues?id={league_id}"

    print(f"[Genesis.FixSeasonID] 目标 URL: {url}")
    print(f"[Genesis.FixSeasonID] 联赛: 英超 (ID: {league_id})")
    print()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    print(f"[Genesis.FixSeasonID] ❌ HTTP 错误: {response.status}")
                    print(f"[Genesis.FixSeasonID] 响应头: {dict(response.headers)}")
                    return

                data = await response.json()
                print(f"[Genesis.FixSeasonID] ✅ API 响应成功")
                print()

                # 打印完整响应摘要（前 1000 字符）
                response_str = json.dumps(data, ensure_ascii=False)
                print(f"[Genesis.FixSeasonID] API 响应摘要（前 1000 字符）:")
                print("=" * 60)
                print(response_str[:1000])
                if len(response_str) > 1000:
                    print(f"... (截断，总长度: {len(response_str)} 字符)")
                print("=" * 60)
                print()

                # 检查赛季信息
                if "allAvailableSeasons" in data:
                    seasons = data.get("allAvailableSeasons", [])
                    print(f"[Genesis.FixSeasonID] ✅ 发现 allAvailableSeasons，共 {len(seasons)} 个赛季:")
                    print()

                    # 显示最近 5 个赛季
                    for i, season in enumerate(seasons[:5], 1):
                        season_id = season.get("id")
                        season_name = season.get("name")
                        print(f"  {i}. season_id = {season_id}, name = {season_name}")

                    if len(seasons) > 5:
                        print(f"  ... (还有 {len(seasons) - 5} 个赛季)")
                    print()

                    # 显示当前赛季
                    if "currentSeason" in data:
                        current = data.get("currentSeason")
                        if current:
                            print(f"[Genesis.FixSeasonID] 🎯 当前赛季:")
                            print(f"     season_id = {current.get('id')}")
                            print(f"     name = {current.get('name')}")
                        print()

                # 检查最新比赛
                if "matches" in data:
                    matches = data.get("matches", [])
                    print(f"[Genesis.FixSeasonID] ✅ 发现 matches 数据，共 {len(matches)} 场比赛:")
                    print()

                    # 显示前 3 场比赛的赛季信息
                    for i, match in enumerate(matches[:3], 1):
                        match_id = match.get("id")
                        home_team = match.get("home", {}).get("name", "N/A")
                        away_team = match.get("away", {}).get("name", "N/A")
                        season_str = match.get("season", "N/A")

                        print(f"  {i}. 比赛 {match_id}:")
                        print(f"     主队: {home_team} vs 客队: {away_team}")
                        print(f"     赛季: {season_str}")
                        print()

                    if len(matches) > 3:
                        print(f"  ... (还有 {len(matches) - 3} 场比赛)")
                    print()

                # 检查其他可能的赛季字段
                print("[Genesis.FixSeasonID] 🔍 检查其他可能的赛季字段:")
                all_keys = list(data.keys())
                season_keys = [k for k in all_keys if "season" in k.lower()]
                print(f"     包含 'season' 的字段: {season_keys}")
                print()

                # 提取真实赛季字符串
                real_season = None
                if "currentSeason" in data:
                    real_season = data["currentSeason"].get("id", "")

                if not real_season and "allAvailableSeasons" in data:
                    if len(data["allAvailableSeasons"]) > 0:
                        real_season = data["allAvailableSeasons"][0].get("id", "")

                if real_season:
                    print(f"[Genesis.FixSeasonID] 🎯 识别到真实赛季字符串: '{real_season}'")
                    print(f"[Genesis.FixSeasonID] 📝 硬编码的 '2526' 需要更新为: '{real_season}'")
                else:
                    print("[Genesis.FixSeasonID] ⚠️  无法识别赛季字符串！")

    except asyncio.TimeoutError:
        print("[Genesis.FixSeasonID] ❌ 请求超时")
    except json.JSONDecodeError as e:
        print(f"[Genesis.FixSeasonID] ❌ JSON 解析失败: {e}")
    except Exception as e:
        print(f"[Genesis.FixSeasonID] ❌ 未知错误: {e}")

    print()
    print("[Genesis.FixSeasonID] ==================== 现场采样完成 ====================")

if __name__ == "__main__":
    asyncio.run(check_fotmob_api())
