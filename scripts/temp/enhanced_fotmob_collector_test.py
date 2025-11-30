#!/usr/bin/env python3
"""
增强版FotMob详情采集器测试
针对已完场比赛优化数据解析逻辑
"""

import asyncio
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from curl_cffi.requests import AsyncSession


class EnhancedFotmobCollector:
    """增强版FotMob采集器"""

    def __init__(self):
        self.session = None
        self.base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.fotmob.com/",
            "Origin": "https://www.fotmob.com",
        }

    async def init_session(self):
        """初始化会话"""
        if not self.session:
            self.session = AsyncSession(impersonate="chrome120")
            await self.session.get("https://www.fotmob.com/")

    async def get_enhanced_match_details(self, match_id):
        """获取增强的比赛详情"""
        await self.init_session()

        # 测试多种可能的详细数据接口
        detail_endpoints = [
            # 基础接口
            f"https://www.fotmob.com/api/match?id={match_id}",
            # 统计相关接口
            f"https://www.fotmob.com/api/matchStats?matchId={match_id}",
            f"https://www.fotmob.com/api/stats/match?matchId={match_id}",
            f"https://www.fotmob.com/api/matchStatistics?matchId={match_id}",
            # 阵容相关接口
            f"https://www.fotmob.com/api/matchLineup?matchId={match_id}",
            f"https://www.fotmob.com/api/lineup?matchId={match_id}",
            f"https://www.fotmob.com/api/lineups?matchId={match_id}",
            # 复合接口
            f"https://www.fotmob.com/api/matchDetails?matchId={match_id}",
            f"https://www.fotmob.com/api/matchData?matchId={match_id}",
            f"https://www.fotmob.com/api/matchInfo?matchId={match_id}",
            # 带参数的接口
            f"https://www.fotmob.com/api/match?id={match_id}&tab=stats",
            f"https://www.fotmob.com/api/match?id={match_id}&tab=lineup",
            f"https://www.fotmob.com/api/match?id={match_id}&include=stats,lineup,events",
        ]

        all_data = {}
        successful_endpoints = []

        print(f"🔍 测试 {len(detail_endpoints)} 个可能的详情接口...")

        for i, endpoint in enumerate(detail_endpoints):
            print(f"\n[{i + 1}/{len(detail_endpoints)}] 测试: {endpoint}")

            try:
                response = await self.session.get(
                    endpoint, headers=self.base_headers, timeout=8
                )

                if response.status_code == 200:
                    try:
                        data = response.json()
                        all_data[endpoint] = data
                        successful_endpoints.append(endpoint)

                        print(f"   ✅ 成功! 数据类型: {type(data).__name__}")
                        if isinstance(data, dict):
                            keys = list(data.keys())
                            print(f"   📋 顶级键: {keys}")

                            # 检查是否包含目标数据
                            has_xg = self._check_xg_in_data(data)
                            has_lineup = self._check_lineup_in_data(data)
                            has_stats = self._check_stats_in_data(data)

                            if has_xg:
                                print("   🔥 发现xG数据!")
                            if has_lineup:
                                print("   👥 发现阵容数据!")
                            if has_stats:
                                print("   📊 发现统计数据!")

                        elif isinstance(data, list) and data:
                            print(f"   📋 列表数据，长度: {len(data)}")

                    except json.JSONDecodeError:
                        print("   ❌ JSON解析失败")

                elif response.status_code == 401:
                    print("   🔒 需要认证")
                elif response.status_code == 404:
                    print("   ❌ 接口不存在")
                else:
                    print(f"   ❌ 其他错误: {response.status_code}")

            except Exception:
                print(f"   ❌ 请求异常: {e}")

        return successful_endpoints, all_data

    def _check_xg_in_data(self, data):
        """检查数据中是否包含xG信息"""
        data_str = str(data).lower()
        xg_keywords = ["xg", "expected goals", "expectedgoals", "x_goals", "x_goals"]
        return any(keyword in data_str for keyword in xg_keywords)

    def _check_lineup_in_data(self, data):
        """检查数据中是否包含阵容信息"""
        data_str = str(data).lower()
        lineup_keywords = [
            "lineup",
            "player",
            "squad",
            "formation",
            "starting",
            "substitute",
        ]
        return any(keyword in data_str for keyword in lineup_keywords)

    def _check_stats_in_data(self, data):
        """检查数据中是否包含统计信息"""
        data_str = str(data).lower()
        stats_keywords = [
            "statistic",
            "stats",
            "possession",
            "shots",
            "goals",
            "corners",
        ]
        return any(keyword in data_str for keyword in stats_keywords)

    async def analyze_complete_data(self, all_data, match_id):
        """分析所有获取的数据"""
        print(f"\n🔬 完整数据分析 (Match ID: {match_id})")
        print("=" * 60)

        found_xg = False
        found_lineup = False
        found_stats = False

        for endpoint, data in all_data.items():
            print(f"\n📡 接口: {endpoint}")
            print(f"📦 数据类型: {type(data).__name__}")

            if isinstance(data, dict):
                keys = list(data.keys())
                print(f"📋 键: {keys}")

                # 专门检查xG
                xg_value = self._extract_xg_value(data)
                if xg_value:
                    print(f"🔥 xG数据: {xg_value}")
                    found_xg = True

                # 专门检查阵容
                lineup_info = self._extract_lineup_info(data)
                if lineup_info:
                    print(f"👥 阵容信息: {lineup_info}")
                    found_lineup = True

                # 专门检查统计
                stats_info = self._extract_stats_info(data)
                if stats_info:
                    print(f"📊 统计信息: {stats_info}")
                    found_stats = True

            elif isinstance(data, list) and data:
                print(f"📋 列表数据，长度: {len(data)}")

        # 总结
        print("\n🎯 数据获取总结:")
        print(f"   xG数据: {'✅ 找到' if found_xg else '❌ 未找到'}")
        print(f"   阵容数据: {'✅ 找到' if found_lineup else '❌ 未找到'}")
        print(f"   统计数据: {'✅ 找到' if found_stats else '❌ 未找到'}")
        print(f"   总接口数: {len(all_data)}")

        return found_xg, found_lineup, found_stats

    def _extract_xg_value(self, data):
        """提取xG数值"""
        # 这是一个简化的xG提取逻辑
        if isinstance(data, dict):
            # 直接查找xG字段
            for key, value in data.items():
                if "xg" in key.lower() and isinstance(value, (int, float)):
                    return value
                elif (
                    isinstance(value, (int, float)) and 0 <= value <= 10
                ):  # xG通常在0-10之间
                    # 检查上下文是否可能是xG
                    parent_key = key.lower()
                    if any(
                        keyword in parent_key
                        for keyword in ["expected", "goal", "shot"]
                    ):
                        return value
        return None

    def _extract_lineup_info(self, data):
        """提取阵容信息"""
        if isinstance(data, dict):
            for key, value in data.items():
                if "lineup" in key.lower() or "player" in key.lower():
                    if isinstance(value, list):
                        return f"{len(value)} 名球员"
                    elif isinstance(value, dict):
                        return f"字典格式，{len(value)} 个字段"
        return None

    def _extract_stats_info(self, data):
        """提取统计信息"""
        if isinstance(data, dict):
            stats_fields = []
            for key, value in data.items():
                if any(
                    keyword in key.lower()
                    for keyword in ["possession", "shots", "corners", "fouls"]
                ):
                    stats_fields.append(key)

            if stats_fields:
                return f"包含字段: {stats_fields[:3]}..."  # 只显示前3个
        return None


async def main():
    """主函数"""
    print("🚀 开始增强版FotMob详情采集器测试...\n")

    # 测试多个已完场比赛
    test_matches = [
        ("3785121", "Qashqai vs Pars Jonoubi Jam"),  # 已确认的已完场比赛
        ("3785122", "Shahrdari Hamedan vs Mes Shahr Babak"),
        ("3785123", "Shahrdari Astara vs Qashqai"),
    ]

    collector = EnhancedFotmobCollector()

    for i, (match_id, description) in enumerate(test_matches, 1):
        print(f"\n{'=' * 80}")
        print(f"测试比赛 {i}/{len(test_matches)}: {description} (ID: {match_id})")
        print(f"{'=' * 80}")

        try:
            successful_endpoints, all_data = await collector.get_enhanced_match_details(
                match_id
            )

            if all_data:
                (
                    found_xg,
                    found_lineup,
                    found_stats,
                ) = await collector.analyze_complete_data(all_data, match_id)

                # 保存完整数据
                with open(
                    f"enhanced_match_data_{match_id}.json", "w", encoding="utf-8"
                ) as f:
                    json.dump(
                        {
                            "match_id": match_id,
                            "description": description,
                            "successful_endpoints": successful_endpoints,
                            "all_data": all_data,
                        },
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )

                print(f"\n💾 完整数据已保存到: enhanced_match_data_{match_id}.json")

                # 如果找到了目标数据，就停止测试
                if found_xg or found_lineup:
                    print(f"\n🎉 在比赛 {description} 中找到了目标数据!")
                    break

        except Exception:
            print(f"❌ 测试过程中发生错误: {e}")

    print(f"\n{'=' * 80}")
    print("测试完成")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    asyncio.run(main())
