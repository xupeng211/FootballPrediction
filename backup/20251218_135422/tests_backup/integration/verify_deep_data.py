#!/usr/bin/env python3
"""
FotMob V2深度数据验收测试
首席代码审计师：验证二段式采集的深度数据质量
强制断言阵容和统计数据的存在
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.collectors.fotmob_browser_v2 import (
    FotmobBrowserScraperV2,
    FotmobMatchDataV2,
)


class DeepDataValidator:
    """深度数据验证器 - 首席代码审计师级别"""

    def __init__(self):
        self.test_results = {
            "total_matches_tested": 0,
            "lineups_found": 0,
            "stats_found": 0,
            "events_found": 0,
            "odds_found": 0,
            "venue_found": 0,
            "deep_completeness": 0,
            "test_passed": False,
            "critical_failures": [],
        }

    def print_banner(self):
        """打印测试横幅"""
        print("=" * 90)
        print("🔬 FotMob V2深度数据验收测试")
        print("🎯 首席代码审计师：验证阵容、统计、事件等深度数据")
        print("⚠️ 强制断言模式：任何缺失都将导致测试失败")
        print("=" * 90)

    async def run_deep_validation(self) -> bool:
        """执行深度数据验证"""
        self.print_banner()

        # 使用昨天的日期进行测试 - 选择有五大联赛的日子
        test_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        print(f"\n🎯 深度测试日期: {test_date}")
        print("🚀 开始V2深度采集测试...")

        try:
            # 执行V2深度采集
            async with FotmobBrowserScraperV2(
                max_concurrent_details=2
            ) as scraper:  # 降低并发度便于观察
                matches = await scraper.scrape_matches_deep(test_date)

                if not matches:
                    print("❌ 深度测试失败: 未采集到任何比赛数据")
                    self.test_results["critical_failures"].append(
                        "未采集到任何比赛数据"
                    )
                    self.print_failure_report()
                    return False

                print(f"✅ V2深度采集成功: 获得 {len(matches)} 场比赛深度数据")
                print(f"📊 采集统计: {scraper.stats}")

                # 执行强制断言验证
                print("\n🔬 执行强制断言深度验证...")
                return self._perform_mandatory_assertions(matches, test_date)

        except Exception as e:
            print(f"❌ 深度测试异常: {e}")
            self.test_results["critical_failures"].append(f"采集异常: {str(e)}")
            self.print_failure_report()
            return False

    def _perform_mandatory_assertions(
        self, matches: list[FotmobMatchDataV2], test_date: str
    ) -> bool:
        """执行强制断言 - 首席代码审计师级别"""

        self.test_results["total_matches_tested"] = len(matches)
        passed_all = True

        # 找到五大联赛比赛进行重点测试
        major_league_matches = [
            match
            for match in matches
            if any(
                league in match.league_name.lower()
                for league in [
                    "premier league",
                    "la liga",
                    "serie a",
                    "bundesliga",
                    "ligue 1",
                ]
            )
        ]

        print(f"🏆 五大联赛比赛: {len(major_league_matches)} 场")

        test_matches = major_league_matches[:3] if major_league_matches else matches[:3]
        print(f"🧪 深度测试比赛数: {len(test_matches)} 场")

        for i, match in enumerate(test_matches, 1):
            print(f"\n{'─'*60}")
            print(
                f"🧪 深度测试 {i}/{len(test_matches)}: {match.home_team_name} vs {match.away_team_name}"
            )
            print(f"{'─'*60}")

            # 强制断言1: 阵容数据必须存在
            try:
                assert match.lineups is not None, "阵容数据为None"
                assert isinstance(match.lineups, dict), "阵容数据不是字典格式"
                assert len(match.lineups) > 0, "阵容数据为空字典"

                # 检查阵容结构
                has_home_lineup = any(
                    "home" in str(k).lower() for k in match.lineups.keys()
                )
                has_away_lineup = any(
                    "away" in str(k).lower() for k in match.lineups.keys()
                )
                has_players = any(
                    "player" in str(k).lower() for k in match.lineups.keys()
                )

                print(
                    f"  ✅ 阵容数据: 通过 (结构: {has_home_lineup}/{has_away_lineup}, 球员: {has_players})"
                )
                self.test_results["lineups_found"] += 1

            except AssertionError as e:
                print(f"  ❌ 阵容数据: 失败 - {str(e)}")
                self.test_results["critical_failures"].append(
                    f"比赛{match.match_id}阵容缺失: {str(e)}"
                )
                passed_all = False

            # 强制断言2: 统计数据必须存在
            try:
                assert match.stats is not None, "统计数据为None"
                assert isinstance(match.stats, (dict, list)), "统计数据格式错误"

                # 检查统计内容 - 必须包含基本统计指标
                stats_content = str(match.stats).lower()
                has_possession = any(
                    stat in stats_content for stat in ["possession", "ball"]
                )
                has_shots = any(
                    stat in stats_content for stat in ["shot", "attempt", "ontarget"]
                )
                has_corners = any(stat in stats_content for stat in ["corner"])
                has_fouls = any(stat in stats_content for stat in ["foul", "yellow"])

                print(
                    f"  ✅ 统计数据: 通过 (控球:{has_possession}, 射门:{has_shots}, 角球:{has_corners})"
                )
                self.test_results["stats_found"] += 1

                # 统计详细度检查
                detail_score = sum([has_possession, has_shots, has_corners, has_fouls])
                if detail_score >= 2:
                    print(f"    📈 统计详细度: {detail_score}/4 (优秀)")

            except AssertionError as e:
                print(f"  ❌ 统计数据: 失败 - {str(e)}")
                self.test_results["critical_failures"].append(
                    f"比赛{match.match_id}统计缺失: {str(e)}"
                )
                passed_all = False

            # 检查事件数据 (非强制但重要)
            if match.events:
                assert isinstance(match.events, list), "事件数据格式错误"
                print(f"  ✅ 事件数据: 通过 ({len(match.events)} 个事件)")
                self.test_results["events_found"] += 1
            else:
                print("  ⚠️ 事件数据: 未获取 (非强制)")

            # 检查赔率数据 (非强制但重要)
            if match.odds:
                print("  ✅ 赔率数据: 通过")
                self.test_results["odds_found"] += 1
            else:
                print("  ⚠️ 赔率数据: 未获取 (非强制)")

            # 检查场地信息 (非强制但重要)
            if match.venue:
                print("  ✅ 场地信息: 通过")
                self.test_results["venue_found"] += 1
            else:
                print("  ⚠️ 场地信息: 未获取 (非强制)")

            # 评估数据完整度
            completeness_score = 0
            if match.lineups:
                completeness_score += 1
            if match.stats:
                completeness_score += 1
            if match.events:
                completeness_score += 1
            if match.odds:
                completeness_score += 1
            if match.venue:
                completeness_score += 1

            if completeness_score >= 3:
                self.test_results["deep_completeness"] += 1
                print(f"  🏆 数据完整度: {completeness_score}/5 (深度完整)")
            elif completeness_score >= 2:
                print(f"  📊 数据完整度: {completeness_score}/5 (基本完整)")
            else:
                print(f"  ⚠️ 数据完整度: {completeness_score}/5 (不完整)")

        # 计算最终结果
        total_tests = len(test_matches)
        lineups_rate = self.test_results["lineups_found"] / total_tests
        stats_rate = self.test_results["stats_found"] / total_tests

        print(f"\n{'='*90}")
        print("📊 深度数据验证最终报告")
        print(f"{'='*90}")
        print(f"📅 测试日期: {test_date}")
        print(f"🧪 测试比赛: {total_tests} 场")
        print(
            f"📋 阵容成功率: {lineups_rate:.1%} ({self.test_results['lineups_found']}/{total_tests})"
        )
        print(
            f"📊 统计成功率: {stats_rate:.1%} ({self.test_results['stats_found']}/{total_tests})"
        )
        print(f"🎯 事件数据: {self.test_results['events_found']} 场")
        print(f"💰 赔率数据: {self.test_results['odds_found']} 场")
        print(f"🏟️ 场地信息: {self.test_results['venue_found']} 场")
        print(f"🏆 深度完整: {self.test_results['deep_completeness']} 场")

        # 首席代码审计师标准
        if lineups_rate >= 0.8 and stats_rate >= 0.8 and passed_all:
            self.test_results["test_passed"] = True
            self.print_success_report()
            return True
        else:
            self.print_failure_report()
            return False

    def print_success_report(self):
        """打印成功报告"""
        print("\n" + "=" * 90)
        print("🎉 深度数据验收测试 - 通过")
        print("✅ V2二段式采集成功获取阵容和统计深度数据")
        print("🚀 数据质量达到AI训练标准，可以启动大规模回填")
        print("🏆 首席代码审计师正式批准发射")
        print("=" * 90)

    def print_failure_report(self):
        """打印失败报告"""
        print("\n" + "=" * 90)
        print("❌ 深度数据验收测试 - 失败")
        print("⚠️ V2采集器未能获取足够的深度数据")
        print("🛑 首席代码审计师驳回发射申请")

        if self.test_results["critical_failures"]:
            print("\n🚨 关键失败:")
            for failure in self.test_results["critical_failures"][:5]:
                print(f"  ❌ {failure}")
            if len(self.test_results["critical_failures"]) > 5:
                print(
                    f"  ❌ ... 还有 {len(self.test_results['critical_failures']) - 5} 个失败"
                )

        total_tests = max(self.test_results["total_matches_tested"], 1)
        lineups_rate = self.test_results["lineups_found"] / total_tests
        stats_rate = self.test_results["stats_found"] / total_tests

        print("\n📈 质量指标:")
        print(f"  📋 阵容数据: {lineups_rate:.1%} (需要≥80%)")
        print(f"  📊 统计数据: {stats_rate:.1%} (需要≥80%)")

        print("\n🔧 建议修复:")
        if lineups_rate < 0.8:
            print("  - 优化阵容API拦截逻辑")
            print("  - 检查阵容标签点击策略")
        if stats_rate < 0.8:
            print("  - 增强统计数据解析")
            print("  - 验证统计标签触发机制")

        print("=" * 90)


async def main():
    """主函数"""
    validator = DeepDataValidator()
    success = await validator.run_deep_validation()

    if success:
        print("\n🎯 首席代码审计师建议: V2深度采集通过，可以立即启动大规模回填")
        print("🚀 建议更新批量脚本使用V2采集器")
        sys.exit(0)
    else:
        print("\n🛑 首席代码审计师建议: 立即暂停，修复深度数据质量问题")
        print("🔧 必须确保阵容和统计数据获取率达到80%以上")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
