#!/usr/bin/env python3
"""
FotMob 比赛详情接口探测脚本
专门用于探测 /api/matchDetails 接口并验证 xG 和阵容数据
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.fotmob_authenticated_client import FotMobAuthenticatedClient


async def probe_match_details():
    """探测比赛详情接口"""
    print("🕵️‍♂️ 开始探测 FotMob 比赛详情接口...")

    client = FotMobAuthenticatedClient()

    try:
        # 初始化会话
        await client.initialize_session()
        print("✅ 客户端初始化成功")

        # 首先获取一些比赛ID
        print("\n📋 获取比赛ID列表...")
        match_ids = await client.get_audio_matches()

        if not match_ids:
            print("❌ 无法获取比赛ID列表")
            return

        print(f"✅ 获取到 {len(match_ids)} 个比赛ID")
        print(f"📝 前5个比赛ID: {match_ids[:5]}")

        # 测试前3个比赛的详情
        test_count = min(3, len(match_ids))
        print(f"\n🔍 测试前 {test_count} 个比赛的详情...")

        for i in range(test_count):
            match_id = match_ids[i]
            print(f"\n--- 测试比赛 {i + 1}/{test_count} (ID: {match_id}) ---")

            # 获取比赛详情
            details = await client.fetch_match_details(match_id, use_signature=True)

            if details:
                print("✅ 成功获取比赛详情!")

                # 分析数据结构
                if isinstance(details, dict):
                    print(f"📊 顶级键: {list(details.keys())}")

                    # 检查是否包含我们想要的数据
                    content = details.get("content", {})
                    if isinstance(content, dict):
                        print(f"📋 content键: {list(content.keys())}")

                        # 检查统计数据
                        stats = content.get("stats", {})
                        if stats:
                            print("🎯 找到统计数据 (stats)!")
                            if isinstance(stats, dict):
                                print(f"   stats键: {list(stats.keys())}")

                                # 寻找xG数据
                                for key, value in stats.items():
                                    if (
                                        "xg" in str(key).lower()
                                        or "expected" in str(key).lower()
                                    ):
                                        print(f"   🔥 发现xG相关数据: {key} = {value}")

                        # 检查阵容数据
                        lineup = content.get("lineup", {})
                        if lineup:
                            print("👥 找到阵容数据 (lineup)!")
                            if isinstance(lineup, dict):
                                print(f"   lineup键: {list(lineup.keys())}")

                                # 寻找主客队阵容
                                for team_key in [
                                    "home",
                                    "away",
                                    "homeTeam",
                                    "awayTeam",
                                ]:
                                    if team_key in lineup:
                                        team_lineup = lineup[team_key]
                                        if (
                                            isinstance(team_lineup, dict)
                                            and "players" in team_lineup
                                        ):
                                            players = team_lineup["players"]
                                            if (
                                                isinstance(players, list)
                                                and len(players) > 0
                                            ):
                                                # 找前锋
                                                for player in players[:3]:  # 只看前3个
                                                    if isinstance(player, dict):
                                                        name = player.get(
                                                            "name", {}
                                                        ).get("fullName", "Unknown")
                                                        position = player.get(
                                                            "position", {}
                                                        ).get("name", "Unknown")
                                                        print(
                                                            f"   ⚽ 找到球员: {name} (位置: {position})"
                                                        )

                        # 检查其他可能包含xG和阵容的位置
                        for key in content.keys():
                            if "stat" in key.lower() or "lineup" in key.lower():
                                print(f"   📈 发现相关字段: {key}")

                    # 检查header中的比赛基本信息
                    header = details.get("header", {})
                    if isinstance(header, dict):
                        teams = header.get("teams", [])
                        if isinstance(teams, list) and len(teams) >= 2:
                            home_team = teams[0].get("name", "Unknown Home")
                            away_team = teams[1].get("name", "Unknown Away")
                            print(f"🏆 比赛: {home_team} vs {away_team}")

                # 保存完整的JSON到文件供分析
                output_file = f"match_details_{match_id}_probe.json"
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(details, f, ensure_ascii=False, indent=2)
                print(f"💾 完整数据已保存到: {output_file}")

            else:
                print("❌ 无法获取比赛详情")

        print("\n🎯 探测完成!")

    except Exception as e:
        print(f"❌ 探测过程中出现错误: {e}")
        import traceback

        traceback.print_exc()


async def test_specific_match(match_id):
    """测试特定比赛的详情"""
    print(f"🎯 测试特定比赛: {match_id}")

    client = FotMobAuthenticatedClient()

    try:
        await client.initialize_session()
        details = await client.fetch_match_details(match_id, use_signature=True)

        if details:
            print("✅ 成功获取比赛详情!")

            # 快速查找关键数据
            content = details.get("content", {})

            # xG数据
            stats = content.get("stats", {})
            print(
                f"\n📊 统计数据键: {list(stats.keys()) if isinstance(stats, dict) else 'None'}"
            )

            # 阵容数据
            lineup = content.get("lineup", {})
            print(
                f"👥 阵容数据键: {list(lineup.keys()) if isinstance(lineup, dict) else 'None'}"
            )

            return True
        else:
            print("❌ 无法获取比赛详情")
            return False

    except Exception as e:
        print(f"❌ 错误: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 测试特定比赛ID
        match_id = sys.argv[1]
        asyncio.run(test_specific_match(match_id))
    else:
        # 自动探测
        asyncio.run(probe_match_details())
