#!/usr/bin/env python3
"""
覆盖率基线测试工具
建立稳定、可重现的覆盖率统计方案
"""

import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime


class CoverageBaseline:
    """覆盖率基线测试工具"""

    def __init__(self):
        self.baseline_file = Path("reports/coverage_baseline.json")
        self.baseline_file.parent.mkdir(exist_ok=True)

    def run_baseline_tests(self):
        """运行基线测试套件"""
        print("🔍 运行覆盖率基线测试...")

        # 定义稳定的基线测试套件（只选择确实可运行的测试）
        baseline_tests = [
            "tests/unit/services/test_services_basic.py",
            "tests/unit/adapters/test_registry.py",
            "tests/unit/utils/test_string_utils.py::TestStringUtilsTruncate",
        ]

        # 验证测试文件存在
        existing_tests = []
        for test in baseline_tests:
            if Path(test).exists():
                existing_tests.append(test)
            else:
                print(f"⚠️ 测试文件不存在: {test}")

        if not existing_tests:
            print("❌ 没有找到基线测试文件")
            return None

        print(f"📋 运行 {len(existing_tests)} 个基线测试...")

        # 运行测试并生成覆盖率报告
        cmd = [
            "python",
            "-m",
            "pytest",
            *existing_tests,
            "--cov=src",
            "--cov-report=json",
            "--cov-report=term-missing",
            "--tb=short",
            "-q",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                print("❌ 测试执行失败")
                print("错误输出:")
                print(result.stderr)
                return None

            # 读取覆盖率报告
            try:
                with open("coverage.json", "r") as f:
                    coverage_data = json.load(f)

                totals = coverage_data.get("totals", {})
                coverage_percent = totals.get("percent_covered", 0)
                covered_lines = totals.get("covered_lines", 0)
                total_lines = totals.get("num_statements", 0)

                baseline_data = {
                    "timestamp": datetime.now().isoformat(),
                    "coverage_percent": coverage_percent,
                    "covered_lines": covered_lines,
                    "total_lines": total_lines,
                    "test_files": existing_tests,
                    "test_count": len(existing_tests),
                    "files": coverage_data.get("files", {}),
                }

                # 保存基线数据
                with open(self.baseline_file, "w", encoding="utf-8") as f:
                    json.dump(baseline_data, f, indent=2, ensure_ascii=False)

                self.print_baseline_report(baseline_data)
                return baseline_data

            except Exception as e:
                print(f"❌ 读取覆盖率报告失败: {e}")
                return None

        except subprocess.TimeoutExpired:
            print("❌ 测试超时")
            return None
        except Exception as e:
            print(f"❌ 测试执行异常: {e}")
            return None

    def print_baseline_report(self, data):
        """打印基线报告"""
        print("\n" + "=" * 60)
        print("📊 覆盖率基线报告")
        print("=" * 60)
        print(f"🕐 时间戳: {data['timestamp']}")
        print(f"📈 总体覆盖率: {data['coverage_percent']:.2f}%")
        print(f"📝 覆盖行数: {data['covered_lines']:,}")
        print(f"📄 总代码行数: {data['total_lines']:,}")
        print(f"🧪 测试文件数: {data['test_count']}")
        print("\n📁 测试文件列表:")
        for i, test_file in enumerate(data["test_files"], 1):
            print(f"  {i}. {test_file}")

        # 模块覆盖率Top 10
        if data["files"]:
            print("\n🏆 模块覆盖率 Top 10:")
            sorted_files = sorted(
                [
                    (file_data["name"], file_data["summary"]["percent_covered"])
                    for file_data in data["files"].values()
                ],
                key=lambda x: x[1],
                reverse=True,
            )

            for i, (file_path, percent) in enumerate(sorted_files[:10], 1):
                short_name = file_path.replace("/home/user/projects/FootballPrediction/", "")
                print(f"  {i:2d}. {short_name:<60} {percent:6.2f}%")

        print("=" * 60)

    def compare_with_baseline(self, current_data):
        """与基线数据比较"""
        if not self.baseline_file.exists():
            print("⚠️ 没有找到基线数据，无法比较")
            return False

        try:
            with open(self.baseline_file, "r") as f:
                baseline_data = json.load(f)

            baseline_coverage = baseline_data["coverage_percent"]
            current_coverage = current_data["coverage_percent"]
            difference = current_coverage - baseline_coverage

            print("\n" + "=" * 50)
            print("📊 与基线比较")
            print("=" * 50)
            print(f"基线覆盖率: {baseline_coverage:.2f}%")
            print(f"当前覆盖率: {current_coverage:.2f}%")
            print(f"差异: {difference:+.2f}%")

            if difference > 0:
                print("✅ 覆盖率提升")
            elif difference < 0:
                print("⚠️ 覆盖率下降")
            else:
                print("➡️ 覆盖率持平")

            print("=" * 50)
            return True

        except Exception as e:
            print(f"❌ 比较失败: {e}")
            return False

    def establish_baseline(self):
        """建立基线"""
        print("🚀 建立覆盖率基线...")
        baseline_data = self.run_baseline_tests()

        if baseline_data:
            print(f"✅ 基线建立成功: {baseline_data['coverage_percent']:.2f}%")
            return True
        else:
            print("❌ 基线建立失败")
            return False

    def run_comparison_test(self):
        """运行比较测试"""
        print("🔍 运行覆盖率比较测试...")
        current_data = self.run_baseline_tests()

        if current_data:
            self.compare_with_baseline(current_data)
            return True
        else:
            print("❌ 当前测试失败")
            return False

    def analyze_coverage_stability(self):
        """分析覆盖率稳定性"""
        print("📈 分析覆盖率稳定性...")

        # 运行3次测试来检查稳定性
        results = []
        for i in range(3):
            print(f"\n第 {i+1} 次测试...")
            data = self.run_baseline_tests()
            if data:
                results.append(data["coverage_percent"])
            else:
                print(f"❌ 第 {i+1} 次测试失败")
                return False

        if len(results) < 2:
            print("❌ 测试数据不足")
            return False

        # 计算统计信息
        avg_coverage = sum(results) / len(results)
        max_coverage = max(results)
        min_coverage = min(results)
        variance = max_coverage - min_coverage

        print("\n📊 稳定性分析结果:")
        print(f"   平均覆盖率: {avg_coverage:.2f}%")
        print(f"   最高覆盖率: {max_coverage:.2f}%")
        print(f"   最低覆盖率: {min_coverage:.2f}%")
        print(f"   覆盖率波动: {variance:.2f}%")

        if variance < 0.5:
            print("✅ 覆盖率稳定 (波动 < 0.5%)")
        elif variance < 1.0:
            print("⚠️ 覆盖率基本稳定 (波动 < 1.0%)")
        else:
            print("❌ 覆盖率不稳定 (波动 >= 1.0%)")

        return variance < 1.0


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="覆盖率基线工具")
    parser.add_argument("--establish", action="store_true", help="建立基线")
    parser.add_argument("--compare", action="store_true", help="与基线比较")
    parser.add_argument("--stability", action="store_true", help="分析稳定性")

    args = parser.parse_args()

    tool = CoverageBaseline()

    if args.establish:
        return tool.establish_baseline()
    elif args.compare:
        return tool.run_comparison_test()
    elif args.stability:
        return tool.analyze_coverage_stability()
    else:
        # 默认运行基线测试
        return tool.run_baseline_tests() is not None


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
