#!/usr/bin/env python3
"""
FotMob 综合接口探测
寻找包含xG和阵容数据的详细接口
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from curl_cffi.requests import AsyncSession


class FotMobComprehensiveProbe:
    """FotMob综合探测"""

    def __init__(self):
        self.session = None
        self.base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
        }

    async def init_session(self):
        """初始化会话"""
        if not self.session:
            self.session = AsyncSession(impersonate="chrome120")
            await self.session.get("https://www.fotmob.com/")

    async def test_detailed_endpoints(self, match_id):
        """测试详细的端点变体"""
        # 包含统计和阵容的可能的端点
        detailed_endpoints = [
            # 最有可能的详细端点
            f"/api/matchDetails?matchId={match_id}",
            f"/api/match/{match_id}/details",
            f"/api/match/{match_id}/stats",
            f"/api/match/{match_id}/lineup",
            # 带参数的变体
            f"/api/match?matchId={match_id}&tab=stats",
            f"/api/match?matchId={match_id}&tab=lineup",
            f"/api/match?matchId={match_id}&include=stats,lineup",
            f"/api/match?matchId={match_id}&details=true",
            # 统计相关
            f"/api/matchStats?matchId={match_id}",
            f"/api/stats/match?matchId={match_id}",
            f"/api/statistics/match?matchId={match_id}",
            # 阵容相关
            f"/api/matchLineup?matchId={match_id}",
            f"/api/lineup/match?matchId={match_id}",
            f"/api/lineups?matchId={match_id}",
            # 数据接口
            f"/api/data/matchDetails?matchId={match_id}",
            f"/api/data/match?matchId={match_id}",
            f"/api/data/matchStats?matchId={match_id}",
            # 移动端或版本化接口
            f"/api/v2/matchDetails?matchId={match_id}",
            f"/api/v1/match?matchId={match_id}",
            f"/api/mobile/matchDetails?matchId={match_id}",
            # 复合接口
            f"/api/match?matchId={match_id}&expand=stats,lineup",
            f"/api/match/{match_id}?expand=statistics,lineups",
        ]

        await self.init_session()

        successful_endpoints = []

        for endpoint in detailed_endpoints:
            print(f"🔍 测试: {endpoint}")

            try:
                url = f"https://www.fotmob.com{endpoint}"
                response = await self.session.get(
                    url, headers=self.base_headers, timeout=8
                )

                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"   ✅ 成功! 数据类型: {type(data).__name__}")

                        if isinstance(data, dict):
                            keys = list(data.keys())
                            print(f"   📋 键: {keys[:10]}...")  # 只显示前10个键

                            # 检查是否包含我们想要的数据
                            has_stats = any("stat" in key.lower() for key in keys)
                            has_lineup = any("lineup" in key.lower() for key in keys)
                            has_xg = any(
                                "xg" in key.lower() or "expected" in key.lower()
                                for key in keys
                            )

                            if has_stats:
                                print("   📊 发现统计数据!")
                            if has_lineup:
                                print("   👥 发现阵容数据!")
                            if has_xg:
                                print("   🔥 发现xG数据!")

                            # 深入检查content字段
                            if "content" in data and isinstance(data["content"], dict):
                                content_keys = list(data["content"].keys())
                                if "stats" in content_keys:
                                    print("   📈 Content中有stats!")
                                if "lineup" in content_keys:
                                    print("   🏟️ Content中有lineup!")

                            if has_stats or has_lineup or has_xg:
                                successful_endpoints.append(
                                    {
                                        "endpoint": endpoint,
                                        "data": data,
                                        "has_stats": has_stats,
                                        "has_lineup": has_lineup,
                                        "has_xg": has_xg,
                                    }
                                )
                                print("   🎯 这个端点包含我们想要的数据!")

                                # 保存这个端点的数据
                                filename = f"endpoint_data_{endpoint.replace('/', '_').replace('?', '_')}.json"
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(data, f, ensure_ascii=False, indent=2)
                                print(f"   💾 数据已保存到: {filename}")

                                return successful_endpoints  # 返回第一个成功的

                        elif isinstance(data, list) and len(data) > 0:
                            print(f"   📋 列表数据，长度: {len(data)}")
                            if isinstance(data[0], dict):
                                keys = list(data[0].keys())
                                print(f"   📋 第一项键: {keys[:10]}...")

                    except json.JSONDecodeError:
                        print("   ❌ 非JSON响应")
                else:
                    print(f"   ❌ 状态码: {response.status_code}")

            except Exception as e:
                print(f"   ❌ 异常: {e}")

        return successful_endpoints

    async def test_premier_league_matches(self):
        """测试一些英超比赛ID"""
        # 英超比赛通常使用的ID格式（这些是已知的英超比赛ID）
        premier_league_matches = [
            "4017263",
            "4017264",
            "4017265",
            "4017266",
            "4017267",
            "4017268",
            "4017269",
            "4017270",
            "4017271",
            "4017272",
        ]

        print("🏆 测试英超比赛ID...")

        for i, match_id in enumerate(premier_league_matches):
            print(
                f"\n--- 测试英超比赛 {i + 1}/{len(premier_league_matches)} (ID: {match_id}) ---"
            )

            successful = await self.test_detailed_endpoints(match_id)

            if successful:
                print(f"🎉 英超比赛 {match_id} 成功找到详细数据!")
                return match_id, successful

        return None, []

    async def test_specific_match_with_content(self, match_id):
        """专门测试特定比赛的完整内容"""
        print(f"🎯 深度测试比赛: {match_id}")

        # 首先获取基本信息
        basic_url = f"https://www.fotmob.com/api/match?id={match_id}"

        try:
            await self.init_session()
            response = await self.session.get(
                basic_url, headers=self.base_headers, timeout=10
            )

            if response.status_code == 200:
                basic_data = response.json()
                print("✅ 获取基本信息成功")

                # 获取比赛基本信息
                home_team = basic_data.get("home", {}).get("name", "Unknown")
                away_team = basic_data.get("away", {}).get("name", "Unknown")
                status = basic_data.get("status", {})

                print(f"🏆 比赛: {home_team} vs {away_team}")
                print(f"📅 状态: {status}")

                # 现在尝试获取详细数据
                detailed = await self.test_detailed_endpoints(match_id)

                if detailed:
                    print("✅ 找到详细数据!")
                    return basic_data, detailed

        except Exception as e:
            print(f"❌ 错误: {e}")

        return None, []


async def main():
    """主函数"""
    print("🚀 开始FotMob综合接口探测...")

    probe = FotMobComprehensiveProbe()

    # 先测试英超比赛（更可能有详细数据）
    print("\n🏆 第一阶段：测试英超比赛")
    pl_match_id, pl_results = await probe.test_premier_league_matches()

    if pl_results:
        print(f"\n🎉 英超比赛成功! ID: {pl_match_id}")
        return pl_match_id, pl_results

    # 如果英超失败，测试之前的比赛
    print("\n⚽ 第二阶段：测试之前的比赛ID")
    basic_data, detailed_results = await probe.test_specific_match_with_content(
        "4721983"
    )

    if detailed_results:
        print("\n🎉 找到详细数据!")
        return "4721983", detailed_results

    print("\n❌ 未能找到包含xG和阵容数据的接口")
    return None, []


if __name__ == "__main__":
    asyncio.run(main())
