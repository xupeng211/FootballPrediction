#!/usr/bin/env python3
"""
数据覆盖率验证脚本
Data Coverage Verification Script

目的：验证 fixtures.allMatches 是否包含整个赛季的所有比赛
验证标准：英超一个赛季有380场比赛

Author: Data Coverage Analyst
Date: 2025-12-08
"""

import asyncio
import sys
from pathlib import Path
from collections import Counter

# 添加项目根路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入采集器
from src.collectors.fotmob_api_collector import FotMobAPICollector


class CoverageVerifier:
    """数据覆盖率验证器"""

    def __init__(self):
        self.collector = FotMobAPICollector(max_concurrent=2, timeout=30)

    async def initialize(self):
        """初始化采集器"""
        await self.collector.initialize()

    async def close(self):
        """关闭采集器"""
        await self.collector.close()

    async def get_league_data(self, league_id: int = 47) -> dict:
        """获取联赛数据"""
        url = (
            f"https://www.fotmob.com/api/leagues?id={league_id}&timezone=Europe/London"
        )

        data, status = await self.collector._make_request(url, f"league_{league_id}")

        if status.name != "SUCCESS" or not data:
            raise Exception(f"API请求失败: {status}")

        return data

    def analyze_matches(self, matches: list, season_name: str) -> dict:
        """分析比赛数据"""
        if not matches:
            return {"total": 0, "error": "无比赛数据"}

        analysis = {
            "total": len(matches),
            "status_breakdown": Counter(),
            "has_dates": 0,
            "date_range": {"earliest": None, "latest": None},
            "team_count": set(),
            "sample_matches": [],
        }

        for i, match in enumerate(matches):
            if not isinstance(match, dict):
                continue

            # 状态统计
            status = match.get("status", {}).get("reason", {}).get("short", "Unknown")
            analysis["status_breakdown"][status] += 1

            # 日期统计
            if match.get("utcTime") or match.get("date"):
                analysis["has_dates"] += 1

            # 球队统计
            home_team = match.get("home", {}).get("name")
            away_team = match.get("away", {}).get("name")
            if home_team:
                analysis["team_count"].add(home_team)
            if away_team:
                analysis["team_count"].add(away_team)

            # 保存前5个样本
            if i < 5:
                analysis["sample_matches"].append(
                    {
                        "id": match.get("id"),
                        "home": home_team,
                        "away": away_team,
                        "status": status,
                        "date": match.get("utcTime") or match.get("date"),
                    }
                )

        analysis["unique_teams"] = len(analysis["team_count"])
        del analysis["team_count"]  # 移除set对象

        return analysis

    async def verify_premier_league_coverage(self):
        """验证英超数据覆盖率"""
        print("=" * 80)
        print("🏴󠁧󠁢󠁥󠁮󠁧󠁿 英超数据覆盖率验证")
        print("=" * 80)

        try:
            # 获取英超数据
            print("📊 正在获取英超数据...")
            data = await self.get_league_data(47)

            # 检查基本信息
            details = data.get("details", {})
            league_name = details.get("name", "Unknown")
            current_season = details.get("selectedSeason", "Unknown")

            print(f"🏆 联赛: {league_name}")
            print(f"📅 当前赛季: {current_season}")

            # 分析所有可用赛季
            available_seasons = data.get("allAvailableSeasons", [])
            print(f"📋 可用赛季: {available_seasons}")

            # 分析 fixtures.allMatches
            fixtures = data.get("fixtures", {})
            all_matches = fixtures.get("allMatches", [])

            print("\n🎯 主要分析: fixtures.allMatches")
            print(f"📊 比赛总数: {len(all_matches)}")

            if not all_matches:
                print("❌ 严重问题: fixtures.allMatches 为空")
                return False

            # 详细分析
            analysis = self.analyze_matches(
                all_matches, f"{league_name} {current_season}"
            )

            # 打印分析结果
            print("\n📈 详细分析结果:")
            print(f"   比赛总数: {analysis['total']}")
            print("   状态分布:")
            for status, count in analysis["status_breakdown"].items():
                print(f"     {status}: {count}")
            print(f"   有日期信息的比赛: {analysis['has_dates']}")
            print(f"   涉及球队数: {analysis['unique_teams']}")

            print("\n🔍 前5场比赛样本:")
            for i, match in enumerate(analysis["sample_matches"], 1):
                print(
                    f"   {i}. {match['home']} vs {match['away']} ({match['status']}, ID: {match['id']})"
                )

            # 🎯 关键验证：英超标准赛季应该有380场比赛
            expected_total = 380
            actual_total = analysis["total"]

            print("\n🎯 覆盖率验证:")
            print(f"   期望比赛数 (英超标准): {expected_total}")
            print(f"   实际比赛数: {actual_total}")

            coverage_percentage = (actual_total / expected_total) * 100
            print(f"   覆盖率: {coverage_percentage:.1f}%")

            if actual_total == expected_total:
                print("✅ 完美匹配! fixtures.allMatches 包含完整赛季的所有比赛")
                result = True
            elif actual_total >= expected_total * 0.95:  # 95%以上认为可接受
                print("⚠️ 接近完整，可能包含额外比赛（如杯赛）")
                result = True
            elif actual_total < expected_total * 0.5:
                print("❌ 严重不足! fixtures.allMatches 遗漏了大量比赛")
                print("🚨 建议: 必须添加 finishedMatches 等其他字段的解析逻辑")
                result = False
            else:
                print("⚠️ 部分覆盖，需要进一步调查")
                result = False

            # 检查其他可能的数据源
            print("\n🔍 检查其他可能的数据源:")
            print(f"   fixtures 键: {list(fixtures.keys())}")

            # 检查是否有其他比赛列表
            alternative_sources = []
            if "finishedMatches" in data:
                finished_matches = data.get("finishedMatches", [])
                print(f"   finishedMatches: {len(finished_matches)} 场比赛")
                alternative_sources.append(("finishedMatches", len(finished_matches)))

            if "upcomingMatches" in data:
                upcoming_matches = data.get("upcomingMatches", [])
                print(f"   upcomingMatches: {len(upcoming_matches)} 场比赛")
                alternative_sources.append(("upcomingMatches", len(upcoming_matches)))

            if alternative_sources:
                print("\n📊 发现替代数据源:")
                for source_name, count in alternative_sources:
                    print(f"   {source_name}: {count} 场比赛")

                total_alternative = sum(count for _, count in alternative_sources)
                combined_total = actual_total + total_alternative
                print(f"   替代数据源总计: {total_alternative} 场")
                print(f"   与allMatches合并: {combined_total} 场")

            return result

        except Exception as e:
            print(f"❌ 验证过程中发生错误: {e}")
            import traceback

            print(f"详细错误: {traceback.format_exc()}")
            return False

    async def verify_multiple_seasons(self):
        """验证多个赛季的数据覆盖率"""
        print(f"\n{'='*80}")
        print("📊 多赛季数据覆盖率对比")
        print("=" * 80)

        # 这里可以扩展到其他联赛的验证
        leagues_to_check = [
            {"id": 47, "name": "英超", "expected": 380},
            # 可以添加更多联赛
            # {"id": 48, "name": "英冠", "expected": 552},
        ]

        for league in leagues_to_check:
            print(f"\n🏆 验证 {league['name']} (ID: {league['id']})")
            try:
                data = await self.get_league_data(league["id"])
                fixtures = data.get("fixtures", {})
                all_matches = fixtures.get("allMatches", [])

                actual = len(all_matches)
                expected = league["expected"]
                coverage = (actual / expected) * 100 if expected > 0 else 0

                status = "✅" if coverage >= 95 else "⚠️" if coverage >= 50 else "❌"
                print(f"   {status} 比赛: {actual}/{expected} ({coverage:.1f}%)")

            except Exception as e:
                print(f"   ❌ 验证失败: {e}")


async def main():
    """主函数"""
    verifier = CoverageVerifier()

    try:
        await verifier.initialize()

        # 主要验证：英超数据覆盖率
        success = await verifier.verify_premier_league_coverage()

        # 可选：多赛季对比
        await verifier.verify_multiple_seasons()

        print(f"\n{'='*80}")
        if success:
            print("🎉 验证通过! fixtures.allMatches 提供了完整的数据覆盖")
            print("✅ 可以放心使用当前的L1重构逻辑")
        else:
            print("⚠️ 验证发现问题! 可能需要恢复 finishedMatches 解析逻辑")
            print("🔧 建议检查是否遗漏了历史比赛数据")
        print("=" * 80)

        return success

    finally:
        await verifier.close()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
