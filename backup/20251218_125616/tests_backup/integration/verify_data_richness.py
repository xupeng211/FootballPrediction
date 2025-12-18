#!/usr/bin/env python3
"""
FotMob数据质量验收脚本
Quality Assurance Lead: 验证采集器能够获取高级数据（xG、阵容、统计）
这是启动大规模回填前的最后一道关卡
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from dataclasses import asdict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.data.collectors.fotmob_browser import FotmobBrowserScraper, FotmobMatchData


class DataQualityTester:
    """数据质量验收测试器"""

    def __init__(self):
        self.test_results = {
            "xg_data_found": False,
            "lineup_data_found": False,
            "stats_data_found": False,
            "high_value_fields": set(),
            "field_coverage": {},
            "test_passed": False,
        }

    def print_banner(self):
        """打印测试横幅"""
        print("=" * 80)
        print("🔬 FotMob数据质量验收测试")
        print("🎯 QA Lead: 验证高级数据获取能力 (xG、阵容、统计)")
        print("⚠️  这是大规模回填前的最后一道关卡")
        print("=" * 80)

    def print_data_richness_report(
        self, match_data_list: list[FotmobMatchData], raw_api_data: list[dict]
    ):
        """打印数据丰度报告"""
        print("\n📊 数据丰度报告:")
        print(
            f"  📅 测试日期: {(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')}"
        )
        print(f"  ⚽ 总比赛数: {len(match_data_list)}")
        print(f"  📡 API调用数: {len(raw_api_data)}")

        # 分析字段覆盖率
        all_fields = set()
        rich_matches = 0

        for match in match_data_list:
            # 基础字段检查
            basic_fields = [
                "match_id",
                "home_team_name",
                "away_team_name",
                "home_score",
                "away_score",
            ]
            has_basic = all(
                hasattr(match, field) and getattr(match, field) is not None
                for field in basic_fields
            )

            if has_basic:
                rich_matches += 1

            # 收集所有字段
            for field in [
                "match_id",
                "league_name",
                "home_team_name",
                "away_team_name" "status",
                "kickoff_time",
                "utc_time",
            ]:
                if hasattr(match, field):
                    all_fields.add(field)

        print(f"  🏟️ 有效比赛: {rich_matches}/{len(match_data_list)}")
        print(f"  📋 基础字段覆盖: {len(all_fields)} 个")

        # 检查原始API数据中的高级字段
        advanced_fields_found = set()

        for api_data in raw_api_data:
            if "data" not in api_data:
                continue

            data = api_data["data"]

            # 递归查找字段
            def find_advanced_fields(obj, path=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        current_path = f"{path}.{key}" if path else key

                        # 检查xG相关字段
                        if any(
                            xg_term in key.lower()
                            for xg_term in ["xg", "expected", "rating"]
                        ):
                            advanced_fields_found.add(current_path)
                            self.test_results["xg_data_found"] = True

                        # 检查阵容相关字段
                        if any(
                            lineup_term in key.lower()
                            for lineup_term in [
                                "lineup",
                                "bench",
                                "formation",
                                "starter",
                            ]
                        ):
                            advanced_fields_found.add(current_path)
                            self.test_results["lineup_data_found"] = True

                        # 检查统计相关字段
                        if any(
                            stats_term in key.lower()
                            for stats_term in [
                                "possession",
                                "shots",
                                "corner",
                                "foul",
                                "offside",
                                "card",
                            ]
                        ):
                            advanced_fields_found.add(current_path)
                            self.test_results["stats_data_found"] = True

                        # 递归检查
                        find_advanced_fields(value, current_path)

                elif isinstance(obj, list):
                    for item in obj:
                        find_advanced_fields(item, path)

        find_advanced_fields(data)

        # 显示找到的高级字段
        if advanced_fields_found:
            print("\n🎯 高级数据字段发现:")
            xg_fields = [
                f
                for f in advanced_fields_found
                if any(xg in f.lower() for xg in ["xg", "expected", "rating"])
            ]
            lineup_fields = [
                f
                for f in advanced_fields_found
                if any(
                    lineup in f.lower() for lineup in ["lineup", "bench", "formation"]
                )
            ]
            stats_fields = [
                f
                for f in advanced_fields_found
                if any(stat in f.lower() for stat in ["possession", "shots", "corner"])
            ]

            if xg_fields:
                print(f"  ⚡ xG相关: {len(xg_fields)} 个字段")
                for field in xg_fields[:3]:  # 显示前3个
                    print(f"    - {field}")
                if len(xg_fields) > 3:
                    print(f"    - ... 还有 {len(xg_fields) - 3} 个字段")

            if lineup_fields:
                print(f"  📋 阵容相关: {len(lineup_fields)} 个字段")
                for field in lineup_fields[:3]:
                    print(f"    - {field}")
                if len(lineup_fields) > 3:
                    print(f"    - ... 还有 {len(lineup_fields) - 3} 个字段")

            if stats_fields:
                print(f"  📊 统计相关: {len(stats_fields)} 个字段")
                for field in stats_fields[:3]:
                    print(f"    - {field}")
                if len(stats_fields) > 3:
                    print(f"    - ... 还有 {len(stats_fields) - 3} 个字段")

        self.test_results["high_value_fields"] = advanced_fields_found
        self.test_results["field_coverage"] = {
            "total_fields": len(all_fields),
            "basic_fields": len(all_fields),
            "advanced_fields": len(advanced_fields_found),
        }

        return advanced_fields_found

    async def run_quality_test(self) -> bool:
        """执行数据质量验收测试"""
        self.print_banner()

        # 使用昨天的日期进行测试
        test_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        print(f"\n🎯 测试日期: {test_date}")
        print("🚀 开始数据采集测试...")

        try:
            # 执行数据采集
            async with FotmobBrowserScraper() as scraper:
                match_data_list = await scraper.scrape_matches(test_date)
                raw_api_data = scraper.captured_data

                if not match_data_list:
                    print("❌ 测试失败: 未采集到任何比赛数据")
                    self.print_failure_report()
                    return False

                print(f"✅ 采集成功: 获得 {len(match_data_list)} 场比赛数据")
                print(f"📡 API拦截: 获得 {len(raw_api_data)} 个API响应")

                # 执行深度断言
                print("\n🔬 执行深度数据质量断言...")

                # 深度断言1: 检查xG数据
                xg_found = self.assert_xg_data(raw_api_data)
                if xg_found:
                    print("  ✅ xG数据: 通过检测")
                    self.test_results["xg_data_found"] = True
                else:
                    print("  ⚠️  xG数据: 未检测到 - 需要进一步分析")

                # 深度断言2: 检查阵容数据
                lineup_found = self.assert_lineup_data(raw_api_data)
                if lineup_found:
                    print("  ✅ 阵容数据: 通过检测")
                    self.test_results["lineup_data_found"] = True
                else:
                    print("  ⚠️  阵容数据: 未检测到 - 需要进一步分析")

                # 深度断言3: 检查统计数据
                stats_found = self.assert_stats_data(raw_api_data)
                if stats_found:
                    print("  ✅ 统计数据: 通过检测")
                    self.test_results["stats_data_found"] = True
                else:
                    print("  ⚠️  统计数据: 未检测到 - 需要进一步分析")

                # 打印数据丰度报告
                self.print_data_richness_report(match_data_list, raw_api_data)

                # 保存测试样本用于分析
                self.save_test_sample(match_data_list, raw_api_data, test_date)

                # 最终判定
                passed = self.evaluate_test_results()
                if passed:
                    self.print_success_report()
                else:
                    self.print_failure_report()

                return passed

        except Exception as e:
            print(f"❌ 测试异常: {e}")
            self.print_failure_report()
            return False

    def assert_xg_data(self, raw_api_data: list[dict]) -> bool:
        """断言xG数据存在"""
        xg_keywords = [
            "xg",
            "expected",
            "rating",
            "expectedgoals",
            "xg_home",
            "xg_away",
        ]

        for api_data in raw_api_data:
            if "data" not in api_data:
                continue

            data_str = json.dumps(api_data["data"]).lower()

            # 查找xG关键词
            for keyword in xg_keywords:
                if keyword in data_str:
                    # 尝试提取xG数值
                    try:
                        data_obj = api_data["data"]
                        xg_values = self.extract_xg_values(data_obj)
                        if xg_values:
                            print(f"    📈 发现xG数值: {xg_values}")
                            return True
                    except:
                        pass

        return False

    def extract_xg_values(self, obj: Any) -> list[float]:
        """递归提取xG数值"""
        xg_values = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                if any(xg_term in key.lower() for xg_term in ["xg", "expected"]):
                    if isinstance(value, (int, float)) and value > 0:
                        xg_values.append(value)
                    elif isinstance(value, str):
                        try:
                            val = float(value)
                            if val > 0:
                                xg_values.append(val)
                        except:
                            pass

                # 递归检查
                xg_values.extend(self.extract_xg_values(value))

        elif isinstance(obj, list):
            for item in obj:
                xg_values.extend(self.extract_xg_values(item))

        return xg_values

    def assert_lineup_data(self, raw_api_data: list[dict]) -> bool:
        """断言阵容数据存在"""
        lineup_keywords = [
            "lineup",
            "bench",
            "formation",
            "starter",
            "substitute",
            "player",
        ]

        for api_data in raw_api_data:
            if "data" not in api_data:
                continue

            data_str = json.dumps(api_data["data"]).lower()

            for keyword in lineup_keywords:
                if keyword in data_str:
                    # 检查是否真的有阵容结构
                    try:
                        data_obj = api_data["data"]
                        if self.has_lineup_structure(data_obj):
                            return True
                    except:
                        pass

        return False

    def has_lineup_structure(self, obj: Any) -> bool:
        """检查是否有阵容结构"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if any(
                    lineup_term in key.lower() for lineup_term in ["lineup", "bench"]
                ):
                    if isinstance(value, list) and len(value) > 0:
                        return True
                    if isinstance(value, dict) and len(value) > 0:
                        return True
                # 递归检查
                if self.has_lineup_structure(value):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if self.has_lineup_structure(item):
                    return True
        return False

    def assert_stats_data(self, raw_api_data: list[dict]) -> bool:
        """断言统计数据存在"""
        stats_keywords = [
            "possession",
            "shots",
            "corner",
            "foul",
            "offside",
            "card",
            "pass",
            "tackle",
        ]

        for api_data in raw_api_data:
            if "data" not in api_data:
                continue

            data_str = json.dumps(api_data["data"]).lower()

            for keyword in stats_keywords:
                if keyword in data_str:
                    # 检查是否真的有统计数值
                    try:
                        data_obj = api_data["data"]
                        if self.has_stats_values(data_obj):
                            return True
                    except:
                        pass

        return False

    def has_stats_values(self, obj: Any) -> bool:
        """检查是否有统计数值"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if any(
                    stat_term in key.lower()
                    for stat_term in ["possession", "shots", "corner"]
                ):
                    if isinstance(value, (int, float)) and 0 <= value <= 100:
                        return True
                # 递归检查
                if self.has_stats_values(value):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if self.has_stats_values(item):
                    return True
        return False

    def save_test_sample(
        self,
        match_data_list: list[FotmobMatchData],
        raw_api_data: list[dict],
        test_date: str,
    ):
        """保存测试样本"""
        try:
            output_dir = Path("tests/test_data")
            output_dir.mkdir(exist_ok=True)

            # 保存比赛数据样本
            sample_file = output_dir / f"quality_test_sample_{test_date}.json"

            sample_data = {
                "test_date": test_date,
                "test_timestamp": datetime.now().isoformat(),
                "total_matches": len(match_data_list),
                "total_api_calls": len(raw_api_data),
                "matches": [
                    asdict(match) for match in match_data_list[:5]
                ],  # 保存前5场比赛作为样本,
                "raw_apis": raw_api_data[:3],  # 保存前3个API响应作为样本
                "test_results": self.test_results,
            }

            with open(sample_file, "w", encoding="utf-8") as f:
                json.dump(sample_data, f, indent=2, ensure_ascii=False)

            print(f"💾 测试样本已保存: {sample_file}")

        except Exception as e:
            print(f"⚠️ 样本保存失败: {e}")

    def evaluate_test_results(self) -> bool:
        """评估测试结果"""
        # 至少需要通过2项高级数据检测
        passed_count = sum(
            [
                self.test_results["xg_data_found"],
                self.test_results["lineup_data_found"],
                self.test_results["stats_data_found"],
            ]
        )

        self.test_results["test_passed"] = passed_count >= 2
        return self.test_results["test_passed"]

    def print_success_report(self):
        """打印成功报告"""
        print("\n" + "=" * 80)
        print("🎉 数据质量验收测试 - 通过")
        print("✅ 采集器能够获取高价值数据，满足AI训练需求")
        print("🚀 可以安全启动大规模历史数据回填")
        print("=" * 80)

    def print_failure_report(self):
        """打印失败报告"""
        print("\n" + "=" * 80)
        print("❌ 数据质量验收测试 - 失败")
        print("⚠️  采集器无法获取足够的高级数据")
        print("🛑 建议暂停大规模回填，进一步优化采集器")

        if not self.test_results["xg_data_found"]:
            print("  ❌ 缺失xG (期望进球) 数据")
        if not self.test_results["lineup_data_found"]:
            print("  ❌ 缺失阵容数据")
        if not self.test_results["stats_data_found"]:
            print("  ❌ 缺失统计数据")

        print("=" * 80)


async def main():
    """主函数"""
    tester = DataQualityTester()
    success = await tester.run_quality_test()

    if success:
        print("\n🎯 QA Lead建议: 数据质量合格，可以继续执行金丝雀运行测试")
        sys.exit(0)
    else:
        print("\n🛑 QA Lead建议: 立即暂停，修复数据质量问题后再进行测试")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
